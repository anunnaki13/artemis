from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.runtime_settings import get_runtime_setting
from app.db import AsyncSessionLocal
from app.models import AiAnalystRun, Candle, DailyDigestRun, ExecutionIntent, ExecutionVenueEvent, RecoveryEvent
from app.schemas.recovery import RecoverySeverity, RecoveryStatus
from services.ai.openrouter import current_budget_spend_usd, resolve_openrouter_runtime
from services.execution.intent_queue import ExecutionIntentQueueService
from services.notification.telegram import TelegramConfig, TelegramNotifier


@dataclass(slots=True)
class RecoverySnapshot:
    status: RecoveryStatus
    severity: RecoverySeverity
    flags: list[str]
    summary_payload: dict[str, Any]


def assess_recovery_status(
    *,
    market_stream_running: bool,
    candle_age_minutes: Decimal | None,
    live_transport_enabled: bool,
    user_stream_running: bool,
    stale_dispatching_count: int,
    high_severity_incidents: int,
    digest_anomaly_score: int,
    ai_budget_utilization: Decimal | None,
) -> RecoverySnapshot:
    flags: list[str] = []
    if not market_stream_running:
        flags.append("market_stream_stopped")
    if candle_age_minutes is None or candle_age_minutes > Decimal("10"):
        flags.append("candle_feed_stale")
    if live_transport_enabled and not user_stream_running:
        flags.append("user_stream_inactive")
    if stale_dispatching_count > 0:
        flags.append("stale_dispatching_intents")
    if high_severity_incidents >= 3:
        flags.append("high_severity_venue_incidents")
    if digest_anomaly_score > 0:
        flags.append("digest_anomaly_active")
    if ai_budget_utilization is not None and ai_budget_utilization >= Decimal("0.9"):
        flags.append("ai_budget_hot")

    critical_flags = {"market_stream_stopped", "stale_dispatching_intents"}
    warning_flags = {
        "candle_feed_stale",
        "user_stream_inactive",
        "high_severity_venue_incidents",
        "digest_anomaly_active",
        "ai_budget_hot",
    }

    if any(flag in critical_flags for flag in flags):
        status: RecoveryStatus = "critical"
        severity: RecoverySeverity = "high"
    elif any(flag in warning_flags for flag in flags):
        status = "warn"
        severity = "medium"
    else:
        status = "ok"
        severity = "low"

    return RecoverySnapshot(
        status=status,
        severity=severity,
        flags=flags,
        summary_payload={
            "market_stream_running": market_stream_running,
            "candle_age_minutes": str(candle_age_minutes) if candle_age_minutes is not None else None,
            "live_transport_enabled": live_transport_enabled,
            "user_stream_running": user_stream_running,
            "stale_dispatching_count": stale_dispatching_count,
            "high_severity_incidents": high_severity_incidents,
            "digest_anomaly_score": digest_anomaly_score,
            "ai_budget_utilization": str(ai_budget_utilization) if ai_budget_utilization is not None else None,
        },
    )


def should_send_critical_alert(
    previous_event: RecoveryEvent | None,
    snapshot: RecoverySnapshot,
    cooldown_minutes: int,
) -> bool:
    if snapshot.status != "critical":
        return False
    if previous_event is None:
        return True
    previous_flags = list(previous_event.flags or [])
    if previous_event.status != "critical":
        return True
    if sorted(previous_flags) != sorted(snapshot.flags):
        return True
    previous_created_at = previous_event.created_at
    if previous_created_at.tzinfo is None:
        previous_created_at = previous_created_at.replace(tzinfo=UTC)
    return datetime.now(UTC) - previous_created_at >= timedelta(minutes=cooldown_minutes)


class RecoveryMonitorService:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run_loop(self) -> None:
        settings = get_settings()
        while True:
            try:
                await self.run_check()
            except Exception:
                pass
            await asyncio.sleep(max(settings.recovery_check_interval_seconds, 10))

    async def list_events(
        self,
        session: AsyncSession,
        *,
        limit: int = 20,
        status: str | None = None,
        severity: str | None = None,
    ) -> list[RecoveryEvent]:
        query = select(RecoveryEvent).order_by(RecoveryEvent.created_at.desc())
        if status is not None:
            query = query.where(RecoveryEvent.status == status)
        if severity is not None:
            query = query.where(RecoveryEvent.severity == severity)
        return list((await session.scalars(query.limit(limit))).all())

    async def latest_event(self, session: AsyncSession) -> RecoveryEvent | None:
        row: RecoveryEvent | None = await session.scalar(
            select(RecoveryEvent).order_by(RecoveryEvent.created_at.desc()).limit(1)
        )
        return row

    async def run_check(self) -> RecoveryEvent:
        async with AsyncSessionLocal() as session:
            previous_event = await self.latest_event(session)
            snapshot = await self._build_snapshot(session)
            event = RecoveryEvent(
                status=snapshot.status,
                severity=snapshot.severity,
                flags=snapshot.flags,
                summary_payload=snapshot.summary_payload,
            )
            session.add(event)
            await session.flush()
            await self._deliver_side_effects(session, event, previous_event)
            await session.commit()
            await session.refresh(event)
            return event

    async def _build_snapshot(self, session: AsyncSession) -> RecoverySnapshot:
        from app.routers.execution import user_stream_service
        from app.routers.market_data import ensure_market_stream_running, stream_service

        await ensure_market_stream_running()

        settings = get_settings()
        now = datetime.now(UTC)
        latest_candle = await session.scalar(
            select(Candle)
            .where(Candle.symbol == "BTCUSDT", Candle.timeframe == "1m")
            .order_by(Candle.open_time.desc())
            .limit(1)
        )
        candle_age_minutes: Decimal | None = None
        if latest_candle is not None:
            open_time = latest_candle.open_time
            if open_time.tzinfo is None:
                open_time = open_time.replace(tzinfo=UTC)
            candle_age_minutes = Decimal(str((now - open_time).total_seconds() / 60))

        digest_run = await session.scalar(
            select(DailyDigestRun).order_by(DailyDigestRun.generated_at.desc()).limit(1)
        )
        digest_anomaly_score = int(digest_run.anomaly_score) if digest_run is not None else 0

        timeout_cutoff = now - timedelta(seconds=settings.execution_dispatch_timeout_seconds)
        stale_dispatching = list(
            (
                await session.scalars(
                    select(ExecutionIntent).where(
                        ExecutionIntent.status == "dispatching",
                        ExecutionIntent.dispatched_at.is_not(None),
                        ExecutionIntent.dispatched_at < timeout_cutoff,
                    )
                )
            ).all()
        )

        venue_events = list(
            (
                await session.scalars(
                    select(ExecutionVenueEvent)
                    .order_by(ExecutionVenueEvent.created_at.desc())
                    .limit(100)
                )
            ).all()
        )
        queue_service = ExecutionIntentQueueService()
        one_hour_ago = now - timedelta(hours=1)
        high_severity_incidents = 0
        for event in venue_events:
            created_at = event.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            if created_at < one_hour_ago:
                continue
            payload = event.payload if isinstance(event.payload, dict) else {}
            incident_type, severity, _, _ = queue_service.classify_venue_incident(
                venue_status=event.venue_status,
                ret_code=payload.get("retCode"),
                ret_msg=payload.get("retMsg"),
                status_code=queue_service.extract_http_status_code(payload),
            )
            if incident_type and severity == "high":
                high_severity_incidents += 1

        ai_budget_utilization: Decimal | None = None
        try:
            runtime = await resolve_openrouter_runtime(session)
            spent = await current_budget_spend_usd(session)
            if runtime.max_cost_usd_per_day > Decimal("0"):
                ai_budget_utilization = spent / runtime.max_cost_usd_per_day
        except Exception:
            ai_budget_utilization = None

        return assess_recovery_status(
            market_stream_running=stream_service.status().running,
            candle_age_minutes=candle_age_minutes,
            live_transport_enabled=bool(await get_runtime_setting(session, "EXECUTION_LIVE_TRANSPORT_ENABLED", "false") == "true"),
            user_stream_running=user_stream_service.status().running,
            stale_dispatching_count=len(stale_dispatching),
            high_severity_incidents=high_severity_incidents,
            digest_anomaly_score=digest_anomaly_score,
            ai_budget_utilization=ai_budget_utilization,
        )

    async def _deliver_side_effects(
        self,
        session: AsyncSession,
        event: RecoveryEvent,
        previous_event: RecoveryEvent | None,
    ) -> None:
        heartbeat_url = await get_runtime_setting(session, "HEALTHCHECK_PING_URL")
        dead_man_url = await get_runtime_setting(session, "DEAD_MAN_SWITCH_WEBHOOK")
        telegram_token = await get_runtime_setting(session, "TELEGRAM_BOT_TOKEN")
        telegram_chat_id = await get_runtime_setting(session, "TELEGRAM_CHAT_ID")
        settings = get_settings()

        if heartbeat_url:
            event.heartbeat_ping_ok = await self._ping_url(heartbeat_url)

        send_critical = should_send_critical_alert(previous_event, self._snapshot_from_event(event), settings.recovery_alert_cooldown_minutes)
        if send_critical and dead_man_url:
            event.dead_man_delivered = await self._post_dead_man(dead_man_url, event)
        if send_critical and telegram_token and telegram_chat_id:
            event.telegram_delivered = await self._send_telegram_alert(telegram_token, telegram_chat_id, event)

    def _snapshot_from_event(self, event: RecoveryEvent) -> RecoverySnapshot:
        return RecoverySnapshot(
            status=cast(RecoveryStatus, event.status),
            severity=cast(RecoverySeverity, event.severity),
            flags=list(event.flags or []),
            summary_payload=dict(event.summary_payload or {}),
        )

    async def _ping_url(self, url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
            return True
        except Exception:
            return False

    async def _post_dead_man(self, url: str, event: RecoveryEvent) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json={
                        "status": event.status,
                        "severity": event.severity,
                        "flags": list(event.flags or []),
                        "summary": event.summary_payload,
                        "created_at": event.created_at.isoformat() if event.created_at else None,
                    },
                )
                response.raise_for_status()
            return True
        except Exception:
            return False

    async def _send_telegram_alert(self, bot_token: str, chat_id: str, event: RecoveryEvent) -> bool:
        flags = ", ".join(event.flags or []) or "none"
        message = (
            f"AIQ-BOT recovery alert\n"
            f"status: {event.status}\n"
            f"severity: {event.severity}\n"
            f"flags: {flags}\n"
            f"summary: {event.summary_payload}"
        )
        try:
            notifier = TelegramNotifier(TelegramConfig(bot_token=bot_token, chat_id=chat_id))
            return await notifier.send_message(message)
        except Exception:
            return False
