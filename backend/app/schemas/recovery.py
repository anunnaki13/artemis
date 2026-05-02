from datetime import datetime
from typing import Literal

from pydantic import BaseModel


RecoverySeverity = Literal["low", "medium", "high"]
RecoveryStatus = Literal["ok", "warn", "critical"]


class RecoveryEventRead(BaseModel):
    id: int
    created_at: datetime
    status: RecoveryStatus
    severity: RecoverySeverity
    flags: list[str]
    summary_payload: dict[str, object]
    heartbeat_ping_ok: bool | None
    dead_man_delivered: bool | None
    telegram_delivered: bool | None
