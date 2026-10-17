"""Credential readiness API schemas."""

from pydantic import BaseModel

from accessmatrix.api.schemas.identities import (
    AuthType,
    SecretSource,
)


class CredentialReferenceStatusRead(BaseModel):
    """Availability of one stored credential reference."""

    field_name: str
    reference: str | None
    source: SecretSource
    available: bool


class IdentityCredentialStatusRead(BaseModel):
    """Safe credential status returned by the API."""

    identity_id: str
    identity_name: str
    role: str
    enabled: bool
    auth_type: AuthType
    secret_source: SecretSource
    ready: bool
    references: list[CredentialReferenceStatusRead]
    message: str


class ProjectCredentialStatusesRead(BaseModel):
    """Credential readiness summary for a project."""

    project_id: str
    total_count: int
    ready_count: int
    unready_count: int
    disabled_count: int
    statuses: list[IdentityCredentialStatusRead]
