"""Local audit-event API routes."""

from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from accessmatrix.audit.models import (
    AuditEventList,
)
from accessmatrix.audit.storage import (
    AuditEventRepository,
    AuditStorageError,
)
from accessmatrix.persistence.storage import (
    get_storage_root,
)

router = APIRouter(
    prefix="/api/v1/audit-events",
    tags=["Audit"],
)

StorageDependency = Annotated[
    Path,
    Depends(get_storage_root),
]


@router.get(
    "",
    response_model=AuditEventList,
)
def list_audit_events(
    storage_root: StorageDependency,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=500,
        ),
    ] = 100,
) -> AuditEventList:
    """List recent local audit events."""

    repository = AuditEventRepository(storage_root)

    try:
        events = repository.list_latest(limit=limit)

    except (
        AuditStorageError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=str(exc),
        ) from exc

    return AuditEventList(
        total_count=len(events),
        items=events,
    )
