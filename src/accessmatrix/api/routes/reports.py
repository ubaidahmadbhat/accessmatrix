"""Project authorization report API routes."""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session

from accessmatrix.api.routes.projects import project_or_404
from accessmatrix.api.schemas.reports import GenerateReportRequest
from accessmatrix.findings.storage import (
    FindingRepository,
    FindingStorageError,
)
from accessmatrix.persistence.database import get_session
from accessmatrix.persistence.storage import get_storage_root
from accessmatrix.reports.generator import (
    build_report_snapshot,
    render_report,
)
from accessmatrix.reports.models import (
    ReportArtifactList,
    ReportArtifactMetadata,
)
from accessmatrix.reports.storage import (
    ReportArtifactInput,
    ReportRepository,
    ReportStorageError,
)
from accessmatrix.scanning.storage import (
    BOLAScanRepository,
    ScanStorageError,
)
from accessmatrix.settings.models import ApplicationSettings
from accessmatrix.settings.storage import (
    ApplicationSettingsRepository,
    SettingsStorageError,
)

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/reports",
    tags=["Reports"],
)

SessionDependency = Annotated[
    Session,
    Depends(get_session),
]

StorageDependency = Annotated[
    Path,
    Depends(get_storage_root),
]


def load_effective_settings(
    storage_root: Path,
) -> ApplicationSettings:
    """Load effective persistent application settings."""

    repository = ApplicationSettingsRepository(storage_root)

    try:
        return repository.load()

    except SettingsStorageError as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=str(exc),
        ) from exc


def build_report_repository(
    storage_root: Path,
    settings: ApplicationSettings | None = None,
) -> ReportRepository:
    """Create a settings-aware report repository."""

    effective_settings = settings if settings is not None else load_effective_settings(storage_root)

    return ReportRepository(
        storage_root,
        max_report_bytes=(effective_settings.evidence.max_report_bytes),
    )


def build_scan_repository(
    storage_root: Path,
    settings: ApplicationSettings,
) -> BOLAScanRepository:
    """Create a settings-aware scan repository for reporting."""

    return BOLAScanRepository(
        storage_root,
        max_scan_bytes=(settings.evidence.max_scan_bytes),
    )


def report_storage_error(
    exc: ReportStorageError,
) -> HTTPException:
    """Convert report storage failures to API responses."""

    error_status = (
        status.HTTP_404_NOT_FOUND
        if ("does not exist" in str(exc) or "missing" in str(exc))
        else status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    return HTTPException(
        status_code=error_status,
        detail=str(exc),
    )


def slugify(
    value: str,
) -> str:
    """Build a safe report filename component."""

    normalized = (
        re.sub(
            r"[^A-Za-z0-9]+",
            "-",
            value.strip(),
        )
        .strip("-")
        .lower()
    )

    if not normalized:
        return "project"

    return normalized[:60]


@router.get(
    "",
    response_model=ReportArtifactList,
)
def list_project_reports(
    project_id: str,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> ReportArtifactList:
    """List locally generated project reports."""

    project_or_404(
        session,
        project_id,
    )

    repository = build_report_repository(storage_root)

    try:
        reports = repository.list_metadata(project_id)

    except ReportStorageError as exc:
        raise report_storage_error(exc) from exc

    return ReportArtifactList(
        project_id=project_id,
        items=reports,
    )


@router.post(
    "",
    response_model=ReportArtifactMetadata,
    status_code=status.HTTP_201_CREATED,
)
def generate_project_report(
    project_id: str,
    payload: GenerateReportRequest,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> ReportArtifactMetadata:
    """Generate and persist a project report."""

    project = project_or_404(
        session,
        project_id,
    )

    application_settings = load_effective_settings(storage_root)

    finding_repository = FindingRepository(storage_root)

    scan_repository = build_scan_repository(
        storage_root,
        application_settings,
    )

    try:
        findings = finding_repository.list_all(project_id)

    except FindingStorageError as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=str(exc),
        ) from exc

    try:
        scans = scan_repository.list_summaries(project_id)

    except ScanStorageError as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=str(exc),
        ) from exc

    report_id = str(uuid4())

    generated_at = datetime.now(UTC)

    normalized_title = payload.title.strip() if payload.title else ""

    title = normalized_title or (f"AccessMatrix Authorization Report — {project.name}")

    snapshot = build_report_snapshot(
        report_id=report_id,
        report_format=(payload.report_format),
        project=project,
        title=title,
        generated_at=generated_at,
        findings=findings,
        scans=scans,
        include_statuses=set(payload.include_statuses),
        include_scan_history=(payload.include_scan_history),
    )

    rendered = render_report(snapshot)

    timestamp = generated_at.strftime("%Y%m%d-%H%M%S")

    filename = (
        f"accessmatrix-{slugify(project.name)}-{timestamp}-{report_id[:8]}.{rendered.extension}"
    )

    repository = build_report_repository(
        storage_root,
        application_settings,
    )

    try:
        return repository.save(
            ReportArtifactInput(
                report_id=report_id,
                project_id=project_id,
                project_name=(project.name),
                title=title,
                report_format=(payload.report_format),
                generated_at=(generated_at),
                finding_count=(snapshot.summary.finding_count),
                scan_count=(snapshot.summary.scan_count),
                filename=filename,
                media_type=(rendered.media_type),
                content=(rendered.content),
            )
        )

    except ReportStorageError as exc:
        raise report_storage_error(exc) from exc


@router.get(
    "/{report_id}/preview",
    response_class=PlainTextResponse,
)
def preview_project_report(
    project_id: str,
    report_id: str,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> PlainTextResponse:
    """Return report source as non-executable plain text."""

    project_or_404(
        session,
        project_id,
    )

    repository = build_report_repository(storage_root)

    try:
        preview = repository.read_preview(
            project_id,
            report_id,
        )

    except ReportStorageError as exc:
        raise report_storage_error(exc) from exc

    return PlainTextResponse(
        content=preview,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": ("nosniff"),
            "Content-Security-Policy": ("default-src 'none'"),
        },
    )


@router.get(
    "/{report_id}/download",
    response_class=FileResponse,
)
def download_project_report(
    project_id: str,
    report_id: str,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> FileResponse:
    """Download one validated local report artifact."""

    project_or_404(
        session,
        project_id,
    )

    repository = build_report_repository(storage_root)

    try:
        metadata = repository.load_metadata(
            project_id,
            report_id,
        )

        artifact_path = repository.artifact_path(
            project_id,
            report_id,
        )

    except ReportStorageError as exc:
        raise report_storage_error(exc) from exc

    return FileResponse(
        path=artifact_path,
        media_type=(metadata.media_type),
        filename=(metadata.filename),
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": ("nosniff"),
        },
    )


@router.get(
    "/{report_id}",
    response_model=ReportArtifactMetadata,
)
def read_project_report_metadata(
    project_id: str,
    report_id: str,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> ReportArtifactMetadata:
    """Read report artifact metadata."""

    project_or_404(
        session,
        project_id,
    )

    repository = build_report_repository(storage_root)

    try:
        return repository.load_metadata(
            project_id,
            report_id,
        )

    except ReportStorageError as exc:
        raise report_storage_error(exc) from exc
