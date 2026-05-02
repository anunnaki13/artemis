from datetime import datetime, timezone
from typing import Any, Literal, cast

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExecutionIntent, ExecutionVenueEvent, User
from app.schemas.execution import (
    ExecutionIntentRead,
    ExecutionVenueEventRead,
    LifecycleStatus,
    VenueIncidentAction,
    VenueIncidentSeverity,
    VenueEventState,
    VenueStatusBucket,
)
from app.schemas.risk import SignalRiskEvaluateRequest, SignalRiskEvaluateResponse
from app.schemas.risk import SignalRiskEvaluateResponse as RiskResponseSchema
from services.audit import write_audit_log
from strategies.base import Signal

IntentStatus = Literal[
    "queued",
    "approved",
    "rejected",
    "cancel_requested",
    "cancelled",
    "dispatching",
    "executed",
    "failed",
]


class ExecutionIntentQueueService:
    def classify_venue_incident(
        self,
        *,
        venue_status: str,
        ret_code: int | None,
        ret_msg: str | None,
        status_code: int | None = None,
    ) -> tuple[str | None, VenueIncidentSeverity | None, bool, VenueIncidentAction | None]:
        normalized_status = venue_status.strip().upper()
        normalized_msg = (ret_msg or "").strip().lower()
        if normalized_status in {"FILLED", "NEW", "ACCEPTED"} and ret_code in {None, 0}:
            return None, None, False, None
        if ret_code in {10001} or "insufficient balance" in normalized_msg:
            return "insufficient_balance", "high", False, "reduce_size"
        if ret_code in {10002, 10003, 10004} or "invalid" in normalized_msg or "parameter" in normalized_msg:
            return "invalid_request", "high", False, "fix_request"
        if ret_code in {10006, 10016, 429} or status_code == 429 or "rate limit" in normalized_msg or "too many" in normalized_msg:
            return "rate_limited", "medium", True, "retry_later"
        if ret_code in {10000, 10017} or "timeout" in normalized_msg or "temporar" in normalized_msg:
            return "transient_transport", "medium", True, "retry_later"
        if ret_code in {110001} or "order not exists" in normalized_msg or "order not found" in normalized_msg:
            return "order_state_mismatch", "medium", False, "refresh_order_state"
        if normalized_status in {"REJECTED", "FAILED"}:
            return "venue_rejected", "high", False, "manual_review"
        if normalized_status in {"CANCELED", "CANCELLED", "EXPIRED"}:
            return "cancelled_or_expired", "low", False, "manual_review"
        if normalized_status in {"PARTIALLY_FILLED", "PARTIALFILLED"}:
            return "partial_fill", "medium", False, "manual_review"
        return "unknown_incident", "medium", False, "manual_review"

    def classify_venue_status(self, venue_status: str) -> VenueStatusBucket:
        normalized = venue_status.strip().upper()
        if normalized in {"NEW", "CREATED", "ACCEPTED", "PARTIALLY_FILLED", "PARTIALFILLED"}:
            if "PARTIAL" in normalized:
                return "partial"
            return "accepted"
        if normalized in {"FILLED"}:
            return "filled"
        if normalized in {"CANCELED", "CANCELLED", "CANCELLED_BY_USER", "DEACTIVATED", "EXPIRED"}:
            return "cancelled"
        if normalized in {"REJECTED", "FAILED"}:
            return "rejected"
        if normalized in {"PENDING", "TRIGGERED", "ACTIVE"}:
            return "pending"
        return "unknown"

    def extract_venue_diagnostics(self, payload: dict[str, Any]) -> tuple[int | None, str | None]:
        details = payload.get("details")
        if isinstance(details, dict):
            if isinstance(details.get("response_body"), dict):
                body = details["response_body"]
                ret_code = body.get("retCode")
                ret_msg = body.get("retMsg")
                return self._parse_ret_code(ret_code), str(ret_msg) if ret_msg is not None else None
            raw_event = details.get("raw_event")
            if isinstance(raw_event, dict):
                ret_code = raw_event.get("retCode") or raw_event.get("rejectReasonCode")
                ret_msg = raw_event.get("retMsg") or raw_event.get("rejectReason")
                return self._parse_ret_code(ret_code), str(ret_msg) if ret_msg is not None else None
        ret_code = payload.get("retCode")
        ret_msg = payload.get("retMsg")
        return self._parse_ret_code(ret_code), str(ret_msg) if ret_msg is not None else None

    def extract_http_status_code(self, payload: dict[str, Any]) -> int | None:
        details = payload.get("details")
        if isinstance(details, dict):
            raw = details.get("status_code")
            try:
                return int(str(raw)) if raw is not None else None
            except (TypeError, ValueError):
                return None
        raw = payload.get("status_code")
        try:
            return int(str(raw)) if raw is not None else None
        except (TypeError, ValueError):
            return None

    def _parse_ret_code(self, value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None

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
        parent_intent_id: int | None = None,
    ) -> ExecutionIntent:
        intent = self.build_intent(
            user=user,
            risk_request=risk_request,
            risk_response=risk_response,
            notes=notes,
        )
        intent.parent_intent_id = parent_intent_id
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
        if status == "cancelled":
            intent.cancelled_at = datetime.now(tz=timezone.utc)
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

    async def link_replacement(
        self,
        session: AsyncSession,
        *,
        intent: ExecutionIntent,
        replacement_intent: ExecutionIntent,
    ) -> ExecutionIntent:
        before_state = self.to_read(intent).model_dump()
        intent.replaced_by_intent_id = int(replacement_intent.id) if intent.id is not None else None
        await session.flush()
        await write_audit_log(
            session,
            action="execution_intent.replaced",
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
            "dispatching": {"executed", "failed", "cancel_requested", "cancelled"},
            "cancel_requested": {"cancelled", "failed", "executed"},
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
            status=cast(LifecycleStatus, intent.status),
            source_strategy=intent.source_strategy,
            requested_notional=intent.requested_notional,
            approved_notional=intent.approved_notional,
            entry_price=intent.entry_price,
            client_order_id=intent.client_order_id,
            venue_order_id=intent.venue_order_id,
            execution_venue=intent.execution_venue,
            dispatched_at=intent.dispatched_at,
            executed_at=intent.executed_at,
            cancelled_at=intent.cancelled_at,
            parent_intent_id=int(intent.parent_intent_id) if intent.parent_intent_id is not None else None,
            replaced_by_intent_id=(
                int(intent.replaced_by_intent_id) if intent.replaced_by_intent_id is not None else None
            ),
            owner_user_id=intent.owner_user_id,
            signal=Signal.model_validate(intent.signal_payload),
            risk=RiskResponseSchema.model_validate(intent.risk_payload),
            execution_payload=intent.execution_payload,
            notes=intent.notes,
        )

    def to_venue_event_read(self, event: ExecutionVenueEvent) -> ExecutionVenueEventRead:
        ret_code, ret_msg = self.extract_venue_diagnostics(event.payload)
        status_code = self.extract_http_status_code(event.payload)
        incident_type, severity, retryable, suggested_action = self.classify_venue_incident(
            venue_status=event.venue_status,
            ret_code=ret_code,
            ret_msg=ret_msg,
            status_code=status_code,
        )
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
            reconcile_state=cast(VenueEventState, event.reconcile_state),
            status_bucket=self.classify_venue_status(event.venue_status),
            ret_code=ret_code,
            ret_msg=ret_msg,
            incident_type=incident_type,
            severity=severity,
            retryable=retryable,
            suggested_action=suggested_action,
            payload=event.payload,
        )
