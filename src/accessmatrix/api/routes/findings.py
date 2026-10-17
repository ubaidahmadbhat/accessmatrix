"""Central project finding API routes."""

from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from accessmatrix.api.routes.projects import (
    project_or_404,
)
from accessmatrix.api.schemas.findings import (
    UpdateFindingRequest,
)
from accessmatrix.findings.models import (
    FindingCategory,
    FindingList,
    FindingRecord,
    FindingStatus,
)
from accessmatrix.findings.storage import (
    FindingRepository,
    FindingStorageError,
)
from accessmatrix.persistence.database import (
    get_session,
)
from accessmatrix.persistence.storage import (
    get_storage_root,
)
from accessmatrix.scanning.models import (
    FindingSeverity,
)
from accessmatrix.scanning.storage import (
    BOLAScanRepository,
    ScanStorageError,
)

router = APIRouter(
    prefix=("/api/v1/projects/{project_id}/findings"),
    tags=["Findings"],
)

SessionDependency = Annotated[
    Session,
    Depends(get_session),
]

StorageDependency = Annotated[
    Path,
    Depends(get_storage_root),
]


def build_finding_repository(
    storage_root: Path,
) -> FindingRepository:
    """Create a finding repository."""

    return FindingRepository(storage_root)


def build_finding_list(
    *,
    project_id: str,
    findings: list[FindingRecord],
) -> FindingList:
    """Build finding counts and results."""

    return FindingList(
        project_id=project_id,
        total_count=len(findings),
        open_count=sum(finding.status == "open" for finding in findings),
        resolved_count=sum(finding.status == "resolved" for finding in findings),
        false_positive_count=sum(finding.status == "false_positive" for finding in findings),
        accepted_risk_count=sum(finding.status == "accepted_risk" for finding in findings),
        items=findings,
    )


def finding_storage_error(
    exc: FindingStorageError,
) -> HTTPException:
    """Convert a finding storage error to an API error."""

    error_status = (
        status.HTTP_404_NOT_FOUND
        if "does not exist" in str(exc)
        else (status.HTTP_500_INTERNAL_SERVER_ERROR)
    )

    return HTTPException(
        status_code=error_status,
        detail=str(exc),
    )


@router.get(
    "",
    response_model=FindingList,
)
def list_project_findings(
    project_id: str,
    session: SessionDependency,
    storage_root: StorageDependency,
    status_filter: FindingStatus | None = None,
    severity_filter: FindingSeverity | None = None,
    category_filter: FindingCategory | None = None,
) -> FindingList:
    """List and filter deduplicated project findings."""

    project_or_404(
        session,
        project_id,
    )

    repository = build_finding_repository(storage_root)

    try:
        findings = repository.list_all(project_id)

    except FindingStorageError as exc:
        raise finding_storage_error(exc) from exc

    if status_filter is not None:
        findings = [finding for finding in findings if finding.status == status_filter]

    if severity_filter is not None:
        findings = [finding for finding in findings if finding.severity == severity_filter]

    if category_filter is not None:
        findings = [finding for finding in findings if finding.category == category_filter]

    return build_finding_list(
        project_id=project_id,
        findings=findings,
    )


@router.post(
    "/rebuild",
    response_model=FindingList,
)
def rebuild_project_findings(
    project_id: str,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> FindingList:
    """Idempotently ingest all persisted project scans."""

    project_or_404(
        session,
        project_id,
    )

    scan_repository = BOLAScanRepository(storage_root)

    finding_repository = build_finding_repository(storage_root)

    try:
        summaries = scan_repository.list_summaries(project_id)

        scans = [
            scan_repository.load(
                project_id,
                summary.scan_id,
            )
            for summary in summaries
        ]

        scans.sort(key=lambda scan: scan.completed_at)

        for scan in scans:
            finding_repository.upsert_scan(scan)

        findings = finding_repository.list_all(project_id)

    except ScanStorageError as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=str(exc),
        ) from exc

    except FindingStorageError as exc:
        raise finding_storage_error(exc) from exc

    return build_finding_list(
        project_id=project_id,
        findings=findings,
    )


@router.get(
    "/{fingerprint}",
    response_model=FindingRecord,
)
def read_project_finding(
    project_id: str,
    fingerprint: str,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> FindingRecord:
    """Read one deduplicated finding."""

    project_or_404(
        session,
        project_id,
    )

    repository = build_finding_repository(storage_root)

    try:
        return repository.load(
            project_id,
            fingerprint,
        )

    except FindingStorageError as exc:
        raise finding_storage_error(exc) from exc


@router.patch(
    "/{fingerprint}",
    response_model=FindingRecord,
)
def update_project_finding(
    project_id: str,
    fingerprint: str,
    payload: UpdateFindingRequest,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> FindingRecord:
    """Change a finding lifecycle status."""

    project_or_404(
        session,
        project_id,
    )

    normalized_note = payload.note.strip() if payload.note is not None else None

    if payload.status != "open" and not normalized_note:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_ENTITY),
            detail=(
                "A note is required when resolving, "
                "accepting, or marking a finding "
                "as a false positive."
            ),
        )

    repository = build_finding_repository(storage_root)

    try:
        return repository.update_status(
            project_id=project_id,
            fingerprint=fingerprint,
            status=payload.status,
            note=normalized_note,
        )

    except FindingStorageError as exc:
        raise finding_storage_error(exc) from exc
