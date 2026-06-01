from fastapi import APIRouter, Query

from src.lib.deps import AuditLogServiceDep, require_permission
from src.lib.pagination import MAX_PAGE_LIMIT
from src.schemas.audit_log import AuditLogResponse
from src.schemas.common import PaginatedResponse


router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogResponse],
    dependencies=[require_permission("iam.audit.read")],
)
async def list_audit_logs(
    service: AuditLogServiceDep,
    limit: int = Query(default=10, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None, min_length=1, max_length=64),
    target_type: str | None = Query(default=None, min_length=1, max_length=32),
    actor_id: str | None = Query(default=None, min_length=1, max_length=36),
):
    items, total = await service.get_all_paginated(
        limit, offset, action, target_type, actor_id
    )
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
