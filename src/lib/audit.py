from sqlalchemy.ext.asyncio import AsyncSession

from src.core.context import actor_id_var, ip_var
from src.core.logging import get_logger
from src.models import AuditLog

log = get_logger(__name__)


async def record(
    session: AsyncSession,
    action: str,
    target_type: str,
    target_id: str | int,
    meta: dict | None = None,
) -> None:
    actor_id = actor_id_var.get()
    ip = ip_var.get()
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        meta=meta,
        ip=ip,
    )
    session.add(entry)
    await session.flush()
    log.info(
        "audit action=%s target=%s:%s actor=%s ip=%s",
        action,
        target_type,
        target_id,
        actor_id,
        ip,
    )
