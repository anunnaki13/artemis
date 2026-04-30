from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog
from app.models.audit import serialize_audit_value


async def write_audit_log(
    session: AsyncSession,
    *,
    action: str,
    entity: str,
    entity_id: str | None,
    before_state: object | None,
    after_state: object | None,
) -> None:
    session.add(
        AuditLog(
            action=action,
            entity=entity,
            entity_id=entity_id,
            before_state=serialize_audit_value(before_state),
            after_state=serialize_audit_value(after_state),
        )
    )
