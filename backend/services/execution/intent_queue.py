from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExecutionIntent, ExecutionVenueEvent, User
from app.schemas.execution import ExecutionIntentRead, ExecutionVenueEventRead, VenueEventState
from app.schemas.risk import SignalRiskEvaluateRequest, SignalRiskEvaluateResponse
from app.schemas.risk import SignalRiskEvaluateResponse as RiskResponseSchema
from services.audit import write_audit_log
from strategies.base import Signal

IntentStatus = Literal["queued", "approved", "rejected", "cancelled", "dispatching", "executed", "failed"]


class ExecutionIntentQueueService:
    async def find_by_order_id(
        self,
        session: AsyncSession,
        *,
        client_order_id: str | None,
        venue_order_id: str | None,
    ) -> ExecutionIntent | None:
        if client_order_id is None and venue_order_id is None:
            raise ValueError("client_order_id or venue_order_id is required")

        query = select(ExecutionIntent)
        if client_order_id is not None and venue_order_id is not None:
            query = query.where(
                and_(
                    ExecutionIntent.client_order_id == client_order_id,
                    ExecutionIntent.venue_order_id == venue_order_id,
                )
            )
        elif client_order_id is not None:
            query = query.where(ExecutionIntent.client_order_id == client_order_id)
        else:
            query = query.where(ExecutionIntent.venue_order_id == venue_order_id)
        return (await session.scalars(query.limit(1))).first()

    def build_intent(
        self,
        *,
        user: User,
        risk_request: SignalRiskEvaluateRequest,
        risk_response: SignalRiskEvaluateResponse,
        notes: str | None,
    ) -> ExecutionIntent:
        approved_notional = min(
            risk_request.proposed_notional,
            risk_response.recommended_max_notional,
        )
        return ExecutionIntent(
            symbol=risk_request.signal.symbol.upper(),
            side=risk_request.signal.side,
            status="queued",
            source_strategy=risk_request.signal.source,
            requested_notional=risk_request.proposed_notional,
            approved_notional=approved_notional,
            entry_price=risk_request.entry_price,
            owner_user_id=str(user.id),
            signal_payload=risk_request.signal.model_dump(),
            risk_payload=risk_response.model_dump(),
            notes=notes,
        )

    async def enqueue(
        self,
        session: AsyncSession,
        *,
        user: User,
        risk_request: SignalRiskEvaluateRequest,
        risk_response: SignalRiskEvaluateResponse,
        notes: str | None,
    ) -> ExecutionIntent:
        intent = self.build_intent(
            user=user,
            risk_request=risk_request,
            risk_response=risk_response,
            notes=notes,
        )
        session.add(intent)
        await session.flush()
        await write_audit_log(
            session,
            action="execution_intent.created",
            entity="execution_intent",
            entity_id=str(intent.id),
            before_state=None,
            after_state=self.to_read(intent).model_dump(),
        )
        return intent

    async def update_status(
        self,
        session: AsyncSession,
        *,
        intent: ExecutionIntent,
        status: IntentStatus,
        notes: str | None,
        execution_payload: dict[str, Any] | None = None,
        client_order_id: str | None = None,
        venue_order_id: str | None = None,
        execution_venue: str | None = None,
    ) -> ExecutionIntent:
        before_state = self.to_read(intent).model_dump()
        intent.status = status
        if notes is not None:
            intent.notes = notes
        if client_order_id is not None:
            intent.client_order_id = client_order_id
        if venue_order_id is not None:
            intent.venue_order_id = venue_order_id
        if execution_venue is not None:
            intent.execution_venue = execution_venue
        if status == "dispatching":
            intent.dispatched_at = datetime.now(tz=timezone.utc)
        if status == "executed":
            intent.executed_at = datetime.now(tz=timezone.utc)
        if execution_payload is not None:
            intent.execution_payload = execution_payload
        await session.flush()
        await write_audit_log(
            session,
            action="execution_intent.status_updated",
            entity="execution_intent",
            entity_id=str(intent.id),
            before_state=before_state,
            after_state=self.to_read(intent).model_dump(),
        )
        return intent

    async def update_execution_metadata(
        self,
        session: AsyncSession,
        *,
        intent: ExecutionIntent,
        notes: str | None = None,
        execution_payload: dict[str, Any] | None = None,
        client_order_id: str | None = None,
        venue_order_id: str | None = None,
        execution_venue: str | None = None,
    ) -> ExecutionIntent:
        before_state = self.to_read(intent).model_dump()
        if notes is not None:
            intent.notes = notes
        if client_order_id is not None:
            intent.client_order_id = client_order_id
        if venue_order_id is not None:
            intent.venue_order_id = venue_order_id
        if execution_venue is not None:
            intent.execution_venue = execution_venue
        if execution_payload is not None:
            intent.execution_payload = execution_payload
        await session.flush()
        await write_audit_log(
            session,
            action="execution_intent.metadata_updated",
            entity="execution_intent",
            entity_id=str(intent.id),
            before_state=before_state,
            after_state=self.to_read(intent).model_dump(),
        )
        return intent

    async def record_venue_event(
        self,
        session: AsyncSession,
        *,
        execution_intent_id: int | None,
        venue: str,
        event_type: str,
        venue_status: str,
        symbol: str | None,
        client_order_id: str | None,
        venue_order_id: str | None,
        reconcile_state: VenueEventState,
        payload: dict[str, Any],
    ) -> ExecutionVenueEvent:
        reconciled_at = datetime.now(tz=timezone.utc) if reconcile_state in {"applied", "ignored"} else None
        event = ExecutionVenueEvent(
            execution_intent_id=execution_intent_id,
            venue=venue,
            event_type=event_type,
            venue_status=venue_status,
            symbol=symbol,
            client_order_id=client_order_id,
            venue_order_id=venue_order_id,
            reconcile_state=reconcile_state,
            reconciled_at=reconciled_at,
            payload=payload,
        )
        session.add(event)
        await session.flush()
        return event

    def validate_status_transition(self, current_status: str, new_status: str) -> bool:
        allowed_transitions: dict[str, set[str]] = {
            "queued": {"approved", "rejected", "cancelled"},
            "approved": {"dispatching", "cancelled"},
            "dispatching": {"executed", "failed", "cancelled"},
            "rejected": set(),
            "cancelled": set(),
            "executed": set(),
            "failed": set(),
        }
        return new_status in allowed_transitions.get(current_status, set())

    def to_read(self, intent: ExecutionIntent) -> ExecutionIntentRead:
        return ExecutionIntentRead(
            id=int(intent.id),
            created_at=intent.created_at,
            updated_at=intent.updated_at,
            symbol=intent.symbol,
            side=intent.side,
            status=intent.status,
            source_strategy=intent.source_strategy,
            requested_notional=intent.requested_notional,
            approved_notional=intent.approved_notional,
            entry_price=intent.entry_price,
            client_order_id=intent.client_order_id,
            venue_order_id=intent.venue_order_id,
            execution_venue=intent.execution_venue,
            dispatched_at=intent.dispatched_at,
            executed_at=intent.executed_at,
            owner_user_id=intent.owner_user_id,
            signal=Signal.model_validate(intent.signal_payload),
            risk=RiskResponseSchema.model_validate(intent.risk_payload),
            execution_payload=intent.execution_payload,
            notes=intent.notes,
        )

    def to_venue_event_read(self, event: ExecutionVenueEvent) -> ExecutionVenueEventRead:
        return ExecutionVenueEventRead(
            id=int(event.id),
            created_at=event.created_at,
            reconciled_at=event.reconciled_at,
            execution_intent_id=int(event.execution_intent_id) if event.execution_intent_id is not None else None,
            venue=event.venue,
            event_type=event.event_type,
            venue_status=event.venue_status,
            symbol=event.symbol,
            client_order_id=event.client_order_id,
            venue_order_id=event.venue_order_id,
            reconcile_state=event.reconcile_state,
            payload=event.payload,
        )
