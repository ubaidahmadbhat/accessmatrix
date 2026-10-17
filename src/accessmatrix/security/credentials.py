"""Secure credential-reference resolution."""

import os
from collections.abc import Callable, Mapping

import keyring
from keyring.errors import KeyringError
from pydantic import SecretStr

KEYRING_SERVICE_NAME = "AccessMatrix"

KeyringGetter = Callable[
    [str, str],
    str | None,
]


class CredentialResolutionError(RuntimeError):
    """Base error raised while resolving credential references."""


class CredentialReferenceMissingError(CredentialResolutionError):
    """Raised when a required credential reference is missing."""


class CredentialUnavailableError(CredentialResolutionError):
    """Raised when a configured credential cannot be resolved."""


class CredentialBackendError(CredentialResolutionError):
    """Raised when a credential backend cannot be used."""


class CredentialResolver:
    """Resolve credentials from supported secret backends."""

    def __init__(
        self,
        *,
        environment: Mapping[str, str] | None = None,
        keyring_getter: KeyringGetter | None = None,
    ) -> None:
        """Initialize the credential resolver."""

        self._environment = environment if environment is not None else os.environ

        self._keyring_getter = (
            keyring_getter if keyring_getter is not None else keyring.get_password
        )

    def resolve(
        self,
        secret_source: str,
        reference: str | None,
    ) -> SecretStr:
        """Resolve one credential reference."""

        normalized_reference = reference.strip() if isinstance(reference, str) else ""

        if not normalized_reference:
            raise CredentialReferenceMissingError(
                "A required credential reference has not been configured."
            )

        if secret_source == "environment":
            value = self._environment.get(normalized_reference)

        elif secret_source == "keyring":
            try:
                value = self._keyring_getter(
                    KEYRING_SERVICE_NAME,
                    normalized_reference,
                )
            except KeyringError as exc:
                raise CredentialBackendError(
                    "The operating-system keyring could not be accessed."
                ) from exc

        else:
            raise CredentialBackendError(f"Unsupported credential source: {secret_source!r}.")

        if value is None or value == "":
            raise CredentialUnavailableError(
                "Credential reference "
                f"{normalized_reference!r} "
                "could not be resolved from "
                f"{secret_source!r}."
            )

        return SecretStr(value)

    def is_available(
        self,
        secret_source: str,
        reference: str | None,
    ) -> bool:
        """Return whether a credential reference can be resolved."""

        try:
            self.resolve(
                secret_source,
                reference,
            )
        except CredentialResolutionError:
            return False

        return True
