"""Identity profile application services."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from accessmatrix.api.schemas.identities import (
    IdentityCreate,
    IdentityUpdate,
)
from accessmatrix.persistence.models import (
    IdentityProfile,
)


class IdentityNotFoundError(LookupError):
    """Raised when an identity profile does not exist."""


class IdentityConflictError(ValueError):
    """Raised when an identity conflicts with an existing record."""


def list_identities(
    session: Session,
    project_id: str,
) -> list[IdentityProfile]:
    """Return all identities belonging to a project."""

    statement = (
        select(IdentityProfile)
        .where(IdentityProfile.project_id == project_id)
        .order_by(IdentityProfile.name.asc())
    )

    return list(session.scalars(statement).all())


def get_identity(
    session: Session,
    project_id: str,
    identity_id: str,
) -> IdentityProfile:
    """Return one identity belonging to a project."""

    statement = select(IdentityProfile).where(
        IdentityProfile.id == identity_id,
        IdentityProfile.project_id == project_id,
    )

    identity = session.scalar(statement)

    if identity is None:
        raise IdentityNotFoundError(f"Identity {identity_id!r} was not found.")

    return identity


def create_identity(
    session: Session,
    project_id: str,
    payload: IdentityCreate,
) -> IdentityProfile:
    """Create and persist an identity profile."""

    identity = IdentityProfile(
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        role=payload.role,
        tenant=payload.tenant,
        department=payload.department,
        auth_type=payload.auth_type,
        secret_source=payload.secret_source,
        secret_reference=(payload.secret_reference),
        username_reference=(payload.username_reference),
        password_reference=(payload.password_reference),
        auth_location=payload.auth_location,
        auth_name=payload.auth_name,
        auth_prefix=payload.auth_prefix,
        enabled=payload.enabled,
    )

    session.add(identity)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()

        raise IdentityConflictError(
            "An identity with this name already exists in the project."
        ) from exc

    session.refresh(identity)

    return identity


def update_identity(
    session: Session,
    project_id: str,
    identity_id: str,
    payload: IdentityUpdate,
) -> IdentityProfile:
    """Replace an existing identity profile."""

    identity = get_identity(
        session,
        project_id,
        identity_id,
    )

    identity.name = payload.name
    identity.description = payload.description
    identity.role = payload.role
    identity.tenant = payload.tenant
    identity.department = payload.department
    identity.auth_type = payload.auth_type
    identity.secret_source = payload.secret_source
    identity.secret_reference = payload.secret_reference
    identity.username_reference = payload.username_reference
    identity.password_reference = payload.password_reference
    identity.auth_location = payload.auth_location
    identity.auth_name = payload.auth_name
    identity.auth_prefix = payload.auth_prefix
    identity.enabled = payload.enabled

    session.add(identity)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()

        raise IdentityConflictError(
            "An identity with this name already exists in the project."
        ) from exc

    session.refresh(identity)

    return identity


def delete_identity(
    session: Session,
    project_id: str,
    identity_id: str,
) -> IdentityProfile:
    """Delete an identity profile."""

    identity = get_identity(
        session,
        project_id,
        identity_id,
    )

    session.delete(identity)
    session.commit()

    return identity
