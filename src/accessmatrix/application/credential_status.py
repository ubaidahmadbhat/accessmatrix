"""Credential readiness evaluation."""

from dataclasses import dataclass

from accessmatrix.persistence.models import IdentityProfile
from accessmatrix.security.credentials import CredentialResolver

SUPPORTED_AUTH_TYPES = frozenset(
    {
        "none",
        "bearer",
        "api_key",
        "basic",
        "cookie",
        "custom_header",
    }
)


@dataclass(frozen=True)
class CredentialReferenceCheck:
    """Availability of one credential reference."""

    field_name: str
    reference: str | None
    source: str
    available: bool


@dataclass(frozen=True)
class IdentityCredentialStatus:
    """Credential readiness for an identity."""

    identity_id: str
    enabled: bool
    auth_type: str
    secret_source: str
    ready: bool
    references: tuple[
        CredentialReferenceCheck,
        ...,
    ]
    message: str


def get_required_references(
    identity: IdentityProfile,
) -> tuple[
    tuple[str, str | None],
    ...,
]:
    """Return credential fields required by an identity."""

    if identity.auth_type == "none":
        return ()

    if identity.auth_type == "basic":
        return (
            (
                "username_reference",
                identity.username_reference,
            ),
            (
                "password_reference",
                identity.password_reference,
            ),
        )

    return (
        (
            "secret_reference",
            identity.secret_reference,
        ),
    )


def build_identity_credential_status(
    identity: IdentityProfile,
    resolver: CredentialResolver,
) -> IdentityCredentialStatus:
    """Evaluate whether an identity can resolve its credentials."""

    if identity.auth_type not in SUPPORTED_AUTH_TYPES:
        return IdentityCredentialStatus(
            identity_id=identity.id,
            enabled=identity.enabled,
            auth_type=identity.auth_type,
            secret_source=identity.secret_source,
            ready=False,
            references=(),
            message=("The identity uses an unsupported authentication type."),
        )

    required_references = get_required_references(identity)

    references = tuple(
        CredentialReferenceCheck(
            field_name=field_name,
            reference=reference,
            source=identity.secret_source,
            available=resolver.is_available(
                identity.secret_source,
                reference,
            ),
        )
        for field_name, reference in required_references
    )

    if not identity.enabled:
        return IdentityCredentialStatus(
            identity_id=identity.id,
            enabled=False,
            auth_type=identity.auth_type,
            secret_source=identity.secret_source,
            ready=False,
            references=references,
            message="The identity is disabled.",
        )

    if identity.auth_type == "none":
        return IdentityCredentialStatus(
            identity_id=identity.id,
            enabled=True,
            auth_type=identity.auth_type,
            secret_source=identity.secret_source,
            ready=True,
            references=(),
            message=("No authentication credentials are required."),
        )

    ready = len(references) > 0 and all(reference.available for reference in references)

    if ready:
        message = "All required credential references are available."
    else:
        message = "One or more required credential references are unavailable."

    return IdentityCredentialStatus(
        identity_id=identity.id,
        enabled=True,
        auth_type=identity.auth_type,
        secret_source=identity.secret_source,
        ready=ready,
        references=references,
        message=message,
    )
