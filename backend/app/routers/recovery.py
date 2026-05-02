from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import RecoveryEvent, User
from app.schemas.recovery import RecoveryEventRead
from services.recovery.monitor import RecoveryMonitorService

router = APIRouter(prefix="/recovery", tags=["recovery"])
recovery_monitor_service = RecoveryMonitorService()


def build_recovery_event_read(event: RecoveryEvent) -> RecoveryEventRead:
    return RecoveryEventRead(
        id=int(event.id),
        created_at=event.created_at,
        status=event.status,
        severity=event.severity,
        flags=list(event.flags or []),
        summary_payload=dict(event.summary_payload or {}),
        heartbeat_ping_ok=event.heartbeat_ping_ok,
        dead_man_delivered=event.dead_man_delivered,
        telegram_delivered=event.telegram_delivered,
    )


@router.get("/status", response_model=RecoveryEventRead | None)
async def recovery_status(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RecoveryEventRead | None:
    event = await recovery_monitor_service.latest_event(session)
    return build_recovery_event_read(event) if event is not None else None


@router.get("/events", response_model=list[RecoveryEventRead])
async def list_recovery_events(
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None, pattern="^(ok|warn|critical)$"),
    severity: str | None = Query(default=None, pattern="^(low|medium|high)$"),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[RecoveryEventRead]:
    events = await recovery_monitor_service.list_events(session, limit=limit, status=status, severity=severity)
    return [build_recovery_event_read(event) for event in events]


@router.post("/checks/run", response_model=RecoveryEventRead)
async def run_recovery_check(
    _: User = Depends(get_current_user),
) -> RecoveryEventRead:
    event = await recovery_monitor_service.run_check()
    return build_recovery_event_read(event)
