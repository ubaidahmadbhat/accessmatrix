"""Identity profile API routes."""

from typing import Annotated, cast

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.orm import Session

from accessmatrix.api.schemas.credentials import (
    CredentialReferenceStatusRead,
    IdentityCredentialStatusRead,
    ProjectCredentialStatusesRead,
)
from accessmatrix.api.schemas.identities import (
    AuthType,
    IdentityCreate,
    IdentityRead,
    IdentityUpdate,
    SecretSource,
)
from accessmatrix.application.credential_status import (
    build_identity_credential_status,
)
from accessmatrix.application.identities import (
    IdentityConflictError,
    IdentityNotFoundError,
    create_identity,
    delete_identity,
    get_identity,
    list_identities,
    update_identity,
)
from accessmatrix.application.projects import (
    ProjectNotFoundError,
    get_project,
)
from accessmatrix.persistence.database import (
    get_session,
)
from accessmatrix.persistence.models import (
    IdentityProfile,
    Project,
)
from accessmatrix.security.credentials import (
    CredentialResolver,
)

router = APIRouter(
    prefix=("/api/v1/projects/{project_id}/identities"),
    tags=["Identities"],
)

SessionDependency = Annotated[
    Session,
    Depends(get_session),
]


def get_credential_resolver() -> CredentialResolver:
    """Create the application credential resolver."""

    return CredentialResolver()


CredentialResolverDependency = Annotated[
    CredentialResolver,
    Depends(get_credential_resolver),
]


def project_or_404(
    session: Session,
    project_id: str,
) -> Project:
    """Return a project or raise an HTTP 404 response."""

    try:
        return get_project(
            session,
            project_id,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


def identity_or_404(
    session: Session,
    project_id: str,
    identity_id: str,
) -> IdentityProfile:
    """Return an identity or raise an HTTP 404 response."""

    try:
        return get_identity(
            session,
            project_id,
            identity_id,
        )
    except IdentityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


def build_credential_status_response(
    identity: IdentityProfile,
    resolver: CredentialResolver,
) -> IdentityCredentialStatusRead:
    """Build a safe credential-readiness response."""

    credential_status = build_identity_credential_status(
        identity,
        resolver,
    )

    return IdentityCredentialStatusRead(
        identity_id=credential_status.identity_id,
        identity_name=identity.name,
        role=identity.role,
        enabled=credential_status.enabled,
        auth_type=cast(
            AuthType,
            credential_status.auth_type,
        ),
        secret_source=cast(
            SecretSource,
            credential_status.secret_source,
        ),
        ready=credential_status.ready,
        references=[
            CredentialReferenceStatusRead(
                field_name=reference.field_name,
                reference=reference.reference,
                source=cast(
                    SecretSource,
                    reference.source,
                ),
                available=reference.available,
            )
            for reference in credential_status.references
        ],
        message=credential_status.message,
    )


@router.get(
    "",
    response_model=list[IdentityRead],
)
def read_identities(
    project_id: str,
    session: SessionDependency,
) -> list[IdentityRead]:
    """List identity profiles belonging to a project."""

    project_or_404(
        session,
        project_id,
    )

    identities = list_identities(
        session,
        project_id,
    )

    return [IdentityRead.model_validate(identity) for identity in identities]


@router.post(
    "",
    response_model=IdentityRead,
    status_code=status.HTTP_201_CREATED,
)
def create_new_identity(
    project_id: str,
    payload: IdentityCreate,
    session: SessionDependency,
) -> IdentityRead:
    """Create an identity profile."""

    project_or_404(
        session,
        project_id,
    )

    try:
        identity = create_identity(
            session,
            project_id,
            payload,
        )
    except IdentityConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return IdentityRead.model_validate(identity)


@router.get(
    "/credential-statuses",
    response_model=ProjectCredentialStatusesRead,
)
def read_project_credential_statuses(
    project_id: str,
    session: SessionDependency,
    resolver: CredentialResolverDependency,
) -> ProjectCredentialStatusesRead:
    """Return credential readiness for all project identities."""

    project_or_404(
        session,
        project_id,
    )

    identities = list_identities(
        session,
        project_id,
    )

    statuses = [
        build_credential_status_response(
            identity,
            resolver,
        )
        for identity in identities
    ]

    ready_count = sum(credential_status.ready for credential_status in statuses)

    disabled_count = sum(not credential_status.enabled for credential_status in statuses)

    return ProjectCredentialStatusesRead(
        project_id=project_id,
        total_count=len(statuses),
        ready_count=ready_count,
        unready_count=(len(statuses) - ready_count),
        disabled_count=disabled_count,
        statuses=statuses,
    )


@router.get(
    "/{identity_id}/credential-status",
    response_model=IdentityCredentialStatusRead,
)
def read_identity_credential_status(
    project_id: str,
    identity_id: str,
    session: SessionDependency,
    resolver: CredentialResolverDependency,
) -> IdentityCredentialStatusRead:
    """Return credential readiness without exposing secrets."""

    project_or_404(
        session,
        project_id,
    )

    identity = identity_or_404(
        session,
        project_id,
        identity_id,
    )

    return build_credential_status_response(
        identity,
        resolver,
    )


@router.get(
    "/{identity_id}",
    response_model=IdentityRead,
)
def read_identity(
    project_id: str,
    identity_id: str,
    session: SessionDependency,
) -> IdentityRead:
    """Read one identity profile."""

    project_or_404(
        session,
        project_id,
    )

    identity = identity_or_404(
        session,
        project_id,
        identity_id,
    )

    return IdentityRead.model_validate(identity)


@router.put(
    "/{identity_id}",
    response_model=IdentityRead,
)
def replace_identity(
    project_id: str,
    identity_id: str,
    payload: IdentityUpdate,
    session: SessionDependency,
) -> IdentityRead:
    """Replace an identity profile."""

    project_or_404(
        session,
        project_id,
    )

    try:
        identity = update_identity(
            session,
            project_id,
            identity_id,
            payload,
        )
    except IdentityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except IdentityConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return IdentityRead.model_validate(identity)


@router.delete(
    "/{identity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_identity(
    project_id: str,
    identity_id: str,
    session: SessionDependency,
) -> Response:
    """Delete an identity profile."""

    project_or_404(
        session,
        project_id,
    )

    try:
        delete_identity(
            session,
            project_id,
            identity_id,
        )
    except IdentityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
