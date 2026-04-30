from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    action: Mapped[str] = mapped_column(String(128))
    entity: Mapped[str] = mapped_column(String(128))
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


def serialize_audit_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): serialize_audit_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_audit_value(item) for item in value]
    if hasattr(value, "model_dump"):
        return serialize_audit_value(value.model_dump())
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            pass
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
