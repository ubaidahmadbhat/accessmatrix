"""Security utilities for AccessMatrix."""

from accessmatrix.security.authentication import (
    IdentityAuthenticationError,
    IdentityDisabledError,
    InvalidIdentityConfigurationError,
    RequestAuthentication,
    build_request_authentication,
)
from accessmatrix.security.credentials import (
    KEYRING_SERVICE_NAME,
    CredentialBackendError,
    CredentialReferenceMissingError,
    CredentialResolutionError,
    CredentialResolver,
    CredentialUnavailableError,
)

__all__ = [
    "KEYRING_SERVICE_NAME",
    "CredentialBackendError",
    "CredentialReferenceMissingError",
    "CredentialResolutionError",
    "CredentialResolver",
    "CredentialUnavailableError",
    "IdentityAuthenticationError",
    "IdentityDisabledError",
    "InvalidIdentityConfigurationError",
    "RequestAuthentication",
    "build_request_authentication",
]
