from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import ExecutionIntent
from services.execution.adapter import (
    BinanceExecutionAdapter,
    ExecutionCancel,
    ExecutionAdapter,
    ExecutionTransportError,
    PaperExecutionAdapter,
)
from services.execution.intent_queue import ExecutionIntentQueueService


class ExecutionWorkerService:
    def __init__(
        self,
        queue_service: ExecutionIntentQueueService,
        adapter: ExecutionAdapter | None = None,
        dispatch_timeout_seconds: int | None = None,
    ) -> None:
        self.queue_service = queue_service
        settings = get_settings()
        if adapter is not None:
            self.adapter = adapter
        elif settings.mode in {"live_micro", "live_scaled"}:
            self.adapter = BinanceExecutionAdapter()
        else:
            self.adapter = PaperExecutionAdapter()
        self.dispatch_timeout_seconds = (
            dispatch_timeout_seconds or settings.execution_dispatch_timeout_seconds
        )

    async def dispatch_next(self, session: AsyncSession) -> ExecutionIntent | None:
        query = (
            select(ExecutionIntent)
            .where(ExecutionIntent.status == "approved")
            .order_by(ExecutionIntent.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        intent = (await session.scalars(query)).first()
        if intent is None:
            return None

        try:
            dispatch = await self.adapter.dispatch(intent)
            intent = await self.queue_service.update_status(
                session,
                intent=intent,
                status="dispatching",
                notes=intent.notes,
                client_order_id=dispatch.client_order_id,
                venue_order_id=dispatch.venue_order_id,
                execution_venue=dispatch.venue,
                execution_payload={
                    "status": "dispatching",
                    "venue_status": dispatch.venue_status,
                    "accepted_at": dispatch.accepted_at.isoformat(),
                    "venue": dispatch.venue,
                    "client_order_id": dispatch.client_order_id,
                    "venue_order_id": dispatch.venue_order_id,
                    "details": dispatch.details,
                    "source": "dispatch",
                },
            )
            result = await self.adapter.execute(intent, dispatch)
        except ExecutionTransportError as exc:
            return await self.queue_service.update_status(
                session,
                intent=intent,
                status="failed",
                notes=intent.notes,
                execution_payload={
                    "status": "failed",
                    "reason": str(exc),
                    "venue": exc.venue,
                    "status_code": exc.status_code,
                    "response_body": exc.response_body,
                    "source": "dispatch_error",
                },
                execution_venue=exc.venue,
            )
        execution_payload = {
            "status": result.status,
            "filled_notional": str(result.filled_notional),
            "average_price": str(result.average_price),
            "executed_at": result.executed_at.isoformat(),
            "venue": result.venue,
            "venue_status": result.venue_status,
            "client_order_id": result.client_order_id,
            "venue_order_id": result.venue_order_id,
            "details": result.details,
        }
        intent = await self.queue_service.update_status(
            session,
            intent=intent,
            status="executed" if result.status == "executed" else "failed",
            notes=intent.notes,
            execution_payload=execution_payload,
            client_order_id=result.client_order_id,
            venue_order_id=result.venue_order_id,
            execution_venue=result.venue,
        )
        return intent

    async def reconcile(
        self,
        session: AsyncSession,
        *,
        intent: ExecutionIntent,
        status: Literal["executed", "failed", "cancelled"],
        filled_notional: str,
        average_price: str,
        venue: str,
        venue_order_id: str | None,
        client_order_id: str | None,
        details: dict[str, object],
    ) -> ExecutionIntent:
        execution_payload = {
            "status": status,
            "filled_notional": filled_notional,
            "average_price": average_price,
            "executed_at": datetime.now(tz=timezone.utc).isoformat(),
            "venue": venue,
            "venue_order_id": venue_order_id,
            "client_order_id": client_order_id,
            "details": details,
            "source": "reconciliation",
        }
        return await self.queue_service.update_status(
            session,
            intent=intent,
            status=status,
            notes=intent.notes,
            execution_payload=execution_payload,
            venue_order_id=venue_order_id,
            client_order_id=client_order_id,
            execution_venue=venue,
        )

    async def apply_venue_event(
        self,
        session: AsyncSession,
        *,
        intent: ExecutionIntent,
        venue: str,
        event_type: str,
        venue_status: str,
        filled_notional: str | None,
        average_price: str | None,
        venue_order_id: str | None,
        client_order_id: str | None,
        details: dict[str, object],
    ) -> tuple[ExecutionIntent, Literal["applied", "ignored"]]:
        if intent.status not in {"dispatching", "cancel_requested"}:
            return intent, "ignored"

        terminal_status = self.map_terminal_venue_status(venue_status)
        if terminal_status is not None:
            updated = await self.reconcile(
                session,
                intent=intent,
                status=terminal_status,
                filled_notional=filled_notional or "0",
                average_price=average_price or str(intent.entry_price),
                venue=venue,
                venue_order_id=venue_order_id,
                client_order_id=client_order_id,
                details={
                    **details,
                    "event_type": event_type,
                    "venue_status": venue_status,
                },
            )
            return updated, "applied"

        execution_payload = {
            "status": intent.status,
            "venue": venue,
            "venue_status": venue_status,
            "client_order_id": client_order_id or intent.client_order_id,
            "venue_order_id": venue_order_id or intent.venue_order_id,
            "filled_notional": filled_notional,
            "average_price": average_price,
            "details": details,
            "event_type": event_type,
            "source": "venue_event",
            "observed_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        updated = await self.queue_service.update_execution_metadata(
            session,
            intent=intent,
            notes=intent.notes,
            execution_payload=execution_payload,
            client_order_id=client_order_id,
            venue_order_id=venue_order_id,
            execution_venue=venue,
        )
        return updated, "applied"

    def map_terminal_venue_status(
        self,
        venue_status: str,
    ) -> Literal["executed", "failed", "cancelled"] | None:
        normalized = venue_status.strip().upper()
        if normalized == "FILLED":
            return "executed"
        if normalized in {"CANCELED", "CANCELLED", "EXPIRED"}:
            return "cancelled"
        if normalized in {"REJECTED", "EXPIRED_IN_MATCH"}:
            return "failed"
        return None

    async def request_cancel(
        self,
        session: AsyncSession,
        *,
        intent: ExecutionIntent,
        reason: str | None,
    ) -> ExecutionIntent:
        cancel_reason = reason or "cancel requested by operator"
        if intent.status in {"queued", "approved"}:
            return await self.queue_service.update_status(
                session,
                intent=intent,
                status="cancelled",
                notes=cancel_reason,
                execution_payload={
                    "status": "cancelled",
                    "reason": cancel_reason,
                    "cancelled_at": datetime.now(tz=timezone.utc).isoformat(),
                    "venue": intent.execution_venue,
                    "client_order_id": intent.client_order_id,
                    "venue_order_id": intent.venue_order_id,
                    "source": "cancel_request",
                },
            )
        if intent.status != "dispatching":
            raise ValueError(f"cancel requires queued, approved, or dispatching status, got {intent.status}")

        pending = await self.queue_service.update_status(
            session,
            intent=intent,
            status="cancel_requested",
            notes=cancel_reason,
            execution_payload={
                "status": "cancel_requested",
                "reason": cancel_reason,
                "requested_at": datetime.now(tz=timezone.utc).isoformat(),
                "venue": intent.execution_venue,
                "client_order_id": intent.client_order_id,
                "venue_order_id": intent.venue_order_id,
                "source": "cancel_request",
            },
        )
        try:
            cancel = await self.adapter.cancel(pending)
        except ExecutionTransportError as exc:
            return await self.queue_service.update_execution_metadata(
                session,
                intent=pending,
                notes=cancel_reason,
                execution_payload={
                    "status": "cancel_requested",
                    "reason": cancel_reason,
                    "venue": exc.venue,
                    "status_code": exc.status_code,
                    "response_body": exc.response_body,
                    "requested_at": datetime.now(tz=timezone.utc).isoformat(),
                    "source": "cancel_request_error",
                },
                execution_venue=exc.venue,
            )
        return await self._apply_cancel_result(
            session,
            intent=pending,
            cancel=cancel,
            reason=cancel_reason,
        )

    async def _apply_cancel_result(
        self,
        session: AsyncSession,
        *,
        intent: ExecutionIntent,
        cancel: ExecutionCancel,
        reason: str | None,
    ) -> ExecutionIntent:
        return await self.queue_service.update_status(
            session,
            intent=intent,
            status="cancelled",
            notes=reason or intent.notes,
            execution_payload={
                "status": cancel.status,
                "reason": reason,
                "cancelled_at": cancel.cancelled_at.isoformat(),
                "venue": cancel.venue,
                "venue_status": cancel.venue_status,
                "client_order_id": cancel.client_order_id,
                "venue_order_id": cancel.venue_order_id,
                "details": cancel.details,
                "source": "venue_cancel",
            },
            client_order_id=cancel.client_order_id,
            venue_order_id=cancel.venue_order_id,
            execution_venue=cancel.venue,
        )

    async def fail_stale_dispatches(self, session: AsyncSession) -> list[ExecutionIntent]:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(seconds=self.dispatch_timeout_seconds)
        query = (
            select(ExecutionIntent)
            .where(
                ExecutionIntent.status == "dispatching",
                ExecutionIntent.dispatched_at.is_not(None),
                ExecutionIntent.dispatched_at < cutoff,
            )
            .order_by(ExecutionIntent.dispatched_at.asc())
            .with_for_update(skip_locked=True)
        )
        intents = list((await session.scalars(query)).all())
        updated: list[ExecutionIntent] = []
        for intent in intents:
            timed_out = await self.queue_service.update_status(
                session,
                intent=intent,
                status="failed",
                notes=intent.notes,
                execution_payload={
                    "status": "failed",
                    "reason": "dispatch timeout",
                    "timed_out_at": datetime.now(tz=timezone.utc).isoformat(),
                    "venue": intent.execution_venue,
                    "client_order_id": intent.client_order_id,
                    "venue_order_id": intent.venue_order_id,
                    "source": "timeout_sweep",
                },
            )
            updated.append(timed_out)
        return updated
