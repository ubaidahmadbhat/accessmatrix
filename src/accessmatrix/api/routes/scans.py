"""Automatic BOLA scan API routes."""

from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from accessmatrix.api.routes.execution import (
    RequestExecutorDependency,
)
from accessmatrix.api.routes.projects import (
    load_project_openapi_document,
    project_or_404,
)
from accessmatrix.api.schemas.scans import (
    DeleteBOLAScanRequest,
    PruneBOLAScansRequest,
    RunBOLAScanRequest,
)
from accessmatrix.application.identities import (
    list_identities,
)
from accessmatrix.authorization.bola import (
    build_bola_test_plan,
)
from accessmatrix.authorization.storage import (
    AuthorizationDatasetRepository,
    AuthorizationDatasetStorageError,
)
from accessmatrix.authorization.validation import (
    validate_authorization_dataset,
)
from accessmatrix.findings.storage import (
    FindingRepository,
    FindingStorageError,
)
from accessmatrix.openapi.operations import (
    discover_operations,
)
from accessmatrix.persistence.database import (
    get_session,
)
from accessmatrix.persistence.storage import (
    get_storage_root,
)
from accessmatrix.scanning.bola import (
    BOLAScanRunner,
)
from accessmatrix.scanning.models import (
    BOLAScan,
    BOLAScanList,
    ScanDeletionResult,
    ScanRetentionResult,
)
from accessmatrix.scanning.storage import (
    BOLAScanRepository,
    ScanStorageError,
)
from accessmatrix.settings.models import (
    ApplicationSettings,
)
from accessmatrix.settings.storage import (
    ApplicationSettingsRepository,
    SettingsStorageError,
)

BOLA_SCAN_CONFIRMATION = "RUN BOLA SCAN"

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/bola-scans",
    tags=["BOLA Scans"],
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
    """Load the effective persistent application settings."""

    repository = ApplicationSettingsRepository(storage_root)

    try:
        return repository.load()

    except SettingsStorageError as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=str(exc),
        ) from exc


def build_scan_repository(
    storage_root: Path,
    settings: ApplicationSettings | None = None,
) -> BOLAScanRepository:
    """Create a settings-aware project scan repository."""

    effective_settings = settings if settings is not None else load_effective_settings(storage_root)

    return BOLAScanRepository(
        storage_root,
        max_scan_bytes=(effective_settings.evidence.max_scan_bytes),
    )


def scan_storage_error(
    exc: ScanStorageError,
) -> HTTPException:
    """Convert a scan storage failure to an API error."""

    error_status = (
        status.HTTP_404_NOT_FOUND
        if "does not exist" in str(exc)
        else status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    return HTTPException(
        status_code=error_status,
        detail=str(exc),
    )


@router.get(
    "",
    response_model=BOLAScanList,
)
def list_project_bola_scans(
    project_id: str,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> BOLAScanList:
    """List persisted BOLA scans for a project."""

    project_or_404(
        session,
        project_id,
    )

    repository = build_scan_repository(storage_root)

    try:
        scans = repository.list_summaries(project_id)

    except ScanStorageError as exc:
        raise scan_storage_error(exc) from exc

    return BOLAScanList(
        project_id=project_id,
        items=scans,
    )


@router.post(
    "",
    response_model=BOLAScan,
    status_code=status.HTTP_201_CREATED,
)
def run_project_bola_scan(
    project_id: str,
    payload: RunBOLAScanRequest,
    session: SessionDependency,
    storage_root: StorageDependency,
    executor: RequestExecutorDependency,
) -> BOLAScan:
    """Execute and persist the project's current BOLA plan."""

    if (
        not payload.acknowledge_authorization
        or payload.confirmation.strip() != BOLA_SCAN_CONFIRMATION
    ):
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=(
                "Running a BOLA scan requires "
                "authorization acknowledgement and "
                "the exact confirmation phrase: "
                f"{BOLA_SCAN_CONFIRMATION}"
            ),
        )

    project = project_or_404(
        session,
        project_id,
    )

    application_settings = load_effective_settings(storage_root)

    document, _ = load_project_openapi_document(
        project,
        storage_root,
    )

    operations = discover_operations(document)

    identities = list_identities(
        session,
        project_id,
    )

    dataset_repository = AuthorizationDatasetRepository(storage_root)

    try:
        dataset = dataset_repository.load(project_id)

    except AuthorizationDatasetStorageError as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=str(exc),
        ) from exc

    dataset_issues = validate_authorization_dataset(
        dataset,
        operations=operations,
        identity_ids={identity.id for identity in identities},
    )

    if dataset_issues:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail={
                "message": ("The authorization dataset must be valid before scanning."),
                "issues": dataset_issues,
            },
        )

    plan = build_bola_test_plan(
        project_id=project_id,
        dataset=dataset,
        operations=operations,
        identities=identities,
    )

    if plan.total_count == 0:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=("The current dataset does not generate any BOLA test cases."),
        )

    runner = BOLAScanRunner(executor)

    scan = runner.run(
        project=project,
        plan=plan,
        dataset=dataset,
        operations=operations,
        identities=identities,
        max_cases=payload.max_cases,
    )

    scan_repository = build_scan_repository(
        storage_root,
        application_settings,
    )

    finding_repository = FindingRepository(storage_root)

    try:
        saved_scan = scan_repository.save(scan)

    except ScanStorageError as exc:
        raise scan_storage_error(exc) from exc

    try:
        finding_repository.upsert_scan(saved_scan)

    except FindingStorageError as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=(f"The scan was saved, but its findings could not be indexed: {exc}"),
        ) from exc

    try:
        scan_repository.prune(
            project_id,
            keep_latest=(application_settings.evidence.scan_retention_keep_latest),
        )

    except ScanStorageError as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=(
                "The scan was saved and its findings "
                "were indexed, but automatic scan "
                "retention could not be applied: "
                f"{exc}"
            ),
        ) from exc

    return saved_scan


@router.post(
    "/retention",
    response_model=ScanRetentionResult,
)
def apply_project_scan_retention(
    project_id: str,
    payload: PruneBOLAScansRequest,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> ScanRetentionResult:
    """Retain only the newest requested project scans."""

    project_or_404(
        session,
        project_id,
    )

    required_confirmation = f"PRUNE BOLA SCANS {project_id}"

    if (
        not payload.acknowledge_evidence_loss
        or payload.confirmation.strip() != required_confirmation
    ):
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=(
                "Applying scan retention requires "
                "evidence-loss acknowledgement and "
                "the exact confirmation phrase: "
                f"{required_confirmation}"
            ),
        )

    repository = build_scan_repository(storage_root)

    try:
        before_count = len(repository.list_summaries(project_id))

        deleted_scan_ids = repository.prune(
            project_id,
            keep_latest=(payload.keep_latest),
        )

    except ScanStorageError as exc:
        raise scan_storage_error(exc) from exc

    after_count = before_count - len(deleted_scan_ids)

    return ScanRetentionResult(
        project_id=project_id,
        keep_latest=(payload.keep_latest),
        before_count=before_count,
        after_count=after_count,
        deleted_count=len(deleted_scan_ids),
        deleted_scan_ids=(deleted_scan_ids),
        retained_finding_history=True,
    )


@router.get(
    "/{scan_id}",
    response_model=BOLAScan,
)
def read_project_bola_scan(
    project_id: str,
    scan_id: str,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> BOLAScan:
    """Read one persisted BOLA scan."""

    project_or_404(
        session,
        project_id,
    )

    repository = build_scan_repository(storage_root)

    try:
        return repository.load(
            project_id,
            scan_id,
        )

    except ScanStorageError as exc:
        raise scan_storage_error(exc) from exc


@router.delete(
    "/{scan_id}",
    response_model=ScanDeletionResult,
)
def delete_project_bola_scan(
    project_id: str,
    scan_id: str,
    payload: DeleteBOLAScanRequest,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> ScanDeletionResult:
    """Delete raw scan evidence while retaining finding history."""

    project_or_404(
        session,
        project_id,
    )

    required_confirmation = f"DELETE BOLA SCAN {scan_id}"

    if (
        not payload.acknowledge_evidence_loss
        or payload.confirmation.strip() != required_confirmation
    ):
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=(
                "Deleting scan evidence requires "
                "evidence-loss acknowledgement and "
                "the exact confirmation phrase: "
                f"{required_confirmation}"
            ),
        )

    repository = build_scan_repository(storage_root)

    try:
        repository.delete(
            project_id,
            scan_id,
        )

    except ScanStorageError as exc:
        raise scan_storage_error(exc) from exc

    return ScanDeletionResult(
        project_id=project_id,
        scan_id=scan_id,
        deleted=True,
        retained_finding_history=True,
    )
