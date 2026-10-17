"""Authorization dataset API routes."""

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
    load_project_openapi_document,
    project_or_404,
)
from accessmatrix.application.identities import (
    list_identities,
)
from accessmatrix.authorization.bola import (
    build_bola_test_plan,
)
from accessmatrix.authorization.demo_seed import (
    DemoAuthorizationSeedError,
    build_demo_authorization_dataset,
)
from accessmatrix.authorization.models import (
    AuthorizationDataset,
    AuthorizationDatasetValidation,
    BOLATestPlan,
)
from accessmatrix.authorization.storage import (
    AuthorizationDatasetRepository,
    AuthorizationDatasetStorageError,
)
from accessmatrix.authorization.validation import (
    validate_authorization_dataset,
)
from accessmatrix.openapi.operations import (
    OpenAPIOperation,
    discover_operations,
)
from accessmatrix.persistence.database import (
    get_session,
)
from accessmatrix.persistence.models import (
    IdentityProfile,
)
from accessmatrix.persistence.storage import (
    get_storage_root,
)

router = APIRouter(
    prefix=("/api/v1/projects/{project_id}/authorization-dataset"),
    tags=["Authorization Dataset"],
)

SessionDependency = Annotated[
    Session,
    Depends(get_session),
]

StorageDependency = Annotated[
    Path,
    Depends(get_storage_root),
]


def build_repository(
    storage_root: Path,
) -> AuthorizationDatasetRepository:
    """Create an authorization dataset repository."""

    return AuthorizationDatasetRepository(storage_root)


def load_authorization_context(
    *,
    session: Session,
    storage_root: Path,
    project_id: str,
) -> tuple[
    list[OpenAPIOperation],
    list[IdentityProfile],
]:
    """Load imported operations and project identities."""

    project = project_or_404(
        session,
        project_id,
    )

    document, _ = load_project_openapi_document(
        project,
        storage_root,
    )

    operations = discover_operations(document)

    identities = list_identities(
        session,
        project_id,
    )

    return (
        operations,
        identities,
    )


def validate_dataset(
    *,
    dataset: AuthorizationDataset,
    operations: list[OpenAPIOperation],
    identities: list[IdentityProfile],
) -> list[str]:
    """Validate a dataset against project context."""

    return validate_authorization_dataset(
        dataset,
        operations=operations,
        identity_ids={identity.id for identity in identities},
    )


def save_dataset(
    *,
    repository: AuthorizationDatasetRepository,
    project_id: str,
    dataset: AuthorizationDataset,
) -> AuthorizationDataset:
    """Save a dataset with normalized API error handling."""

    try:
        return repository.save(
            project_id,
            dataset,
        )

    except AuthorizationDatasetStorageError as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=AuthorizationDataset,
)
def read_authorization_dataset(
    project_id: str,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> AuthorizationDataset:
    """Read a project's authorization dataset."""

    project_or_404(
        session,
        project_id,
    )

    repository = build_repository(storage_root)

    try:
        return repository.load(project_id)

    except AuthorizationDatasetStorageError as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=str(exc),
        ) from exc


@router.post(
    "/validate",
    response_model=AuthorizationDatasetValidation,
)
def validate_project_authorization_dataset(
    project_id: str,
    payload: AuthorizationDataset,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> AuthorizationDatasetValidation:
    """Validate a dataset without saving it."""

    (
        operations,
        identities,
    ) = load_authorization_context(
        session=session,
        storage_root=storage_root,
        project_id=project_id,
    )

    issues = validate_dataset(
        dataset=payload,
        operations=operations,
        identities=identities,
    )

    return AuthorizationDatasetValidation(
        valid=not issues,
        issue_count=len(issues),
        issues=issues,
    )


@router.post(
    "/demo-seed",
    response_model=AuthorizationDataset,
)
def seed_demo_authorization_dataset(
    project_id: str,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> AuthorizationDataset:
    """Build and save the local invoice demonstration dataset."""

    (
        operations,
        identities,
    ) = load_authorization_context(
        session=session,
        storage_root=storage_root,
        project_id=project_id,
    )

    try:
        dataset = build_demo_authorization_dataset(identities)

    except DemoAuthorizationSeedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    issues = validate_dataset(
        dataset=dataset,
        operations=operations,
        identities=identities,
    )

    if issues:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": (
                    "The current project is not compatible with the invoice demonstration dataset."
                ),
                "issues": issues,
            },
        )

    repository = build_repository(storage_root)

    return save_dataset(
        repository=repository,
        project_id=project_id,
        dataset=dataset,
    )


@router.get(
    "/bola-plan",
    response_model=BOLATestPlan,
)
def read_bola_test_plan(
    project_id: str,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> BOLATestPlan:
    """Generate the current automatic BOLA test plan."""

    (
        operations,
        identities,
    ) = load_authorization_context(
        session=session,
        storage_root=storage_root,
        project_id=project_id,
    )

    repository = build_repository(storage_root)

    try:
        dataset = repository.load(project_id)

    except AuthorizationDatasetStorageError as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=str(exc),
        ) from exc

    return build_bola_test_plan(
        project_id=project_id,
        dataset=dataset,
        operations=operations,
        identities=identities,
    )


@router.put(
    "",
    response_model=AuthorizationDataset,
)
def replace_authorization_dataset(
    project_id: str,
    payload: AuthorizationDataset,
    session: SessionDependency,
    storage_root: StorageDependency,
) -> AuthorizationDataset:
    """Validate and replace a project's dataset."""

    (
        operations,
        identities,
    ) = load_authorization_context(
        session=session,
        storage_root=storage_root,
        project_id=project_id,
    )

    issues = validate_dataset(
        dataset=payload,
        operations=operations,
        identities=identities,
    )

    if issues:
        raise HTTPException(
            status_code=422,
            detail={
                "message": ("The authorization dataset contains validation issues."),
                "issues": issues,
            },
        )

    repository = build_repository(storage_root)

    return save_dataset(
        repository=repository,
        project_id=project_id,
        dataset=payload,
    )
