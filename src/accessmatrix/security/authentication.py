"""Secure request-authentication construction."""

from dataclasses import dataclass, field

from accessmatrix.persistence.models import IdentityProfile
from accessmatrix.security.credentials import CredentialResolver


class IdentityAuthenticationError(RuntimeError):
    """Base identity authentication error."""


class IdentityDisabledError(IdentityAuthenticationError):
    """Raised when a disabled identity is used."""


class InvalidIdentityConfigurationError(IdentityAuthenticationError):
    """Raised when identity authentication is incomplete."""


@dataclass(frozen=True)
class RequestAuthentication:
    """Authentication values prepared for an HTTP request."""

    headers: dict[str, str] = field(
        default_factory=dict,
        repr=False,
    )

    query_parameters: dict[str, str] = field(
        default_factory=dict,
        repr=False,
    )

    cookies: dict[str, str] = field(
        default_factory=dict,
        repr=False,
    )

    basic_auth: tuple[str, str] | None = field(
        default=None,
        repr=False,
    )

    def __repr__(self) -> str:
        """Return a representation that never includes secret values."""

        return (
            "RequestAuthentication("
            f"header_names={list(self.headers)}, "
            "query_parameter_names="
            f"{list(self.query_parameters)}, "
            f"cookie_names={list(self.cookies)}, "
            f"basic_auth_configured="
            f"{self.basic_auth is not None}"
            ")"
        )


def require_text(
    value: str | None,
    field_name: str,
) -> str:
    """Require a non-empty identity configuration field."""

    normalized = value.strip() if isinstance(value, str) else ""

    if not normalized:
        raise InvalidIdentityConfigurationError(
            f"{field_name} is required for the selected authentication type."
        )

    return normalized


def reject_header_control_characters(
    value: str,
    field_name: str,
) -> None:
    """Reject newline characters in HTTP header data."""

    if "\r" in value or "\n" in value:
        raise InvalidIdentityConfigurationError(
            f"{field_name} must not contain carriage-return or newline characters."
        )


def compose_authentication_value(
    secret: str,
    prefix: str | None,
) -> str:
    """Combine an optional prefix and a secret value."""

    normalized_prefix = prefix.strip() if isinstance(prefix, str) else ""

    if not normalized_prefix:
        return secret

    return f"{normalized_prefix} {secret}"


def build_request_authentication(
    identity: IdentityProfile,
    resolver: CredentialResolver,
) -> RequestAuthentication:
    """Build request authentication for an identity."""

    if not identity.enabled:
        raise IdentityDisabledError(f"Identity {identity.name!r} is disabled.")

    if identity.auth_type == "none":
        return RequestAuthentication()

    if identity.auth_type == "bearer":
        secret = resolver.resolve(
            identity.secret_source,
            identity.secret_reference,
        ).get_secret_value()

        prefix = identity.auth_prefix if identity.auth_prefix else "Bearer"

        authorization_value = compose_authentication_value(
            secret,
            prefix,
        )

        reject_header_control_characters(
            authorization_value,
            "Authorization value",
        )

        return RequestAuthentication(
            headers={
                "Authorization": (authorization_value),
            }
        )

    if identity.auth_type == "api_key":
        secret = resolver.resolve(
            identity.secret_source,
            identity.secret_reference,
        ).get_secret_value()

        auth_name = require_text(
            identity.auth_name,
            "auth_name",
        )

        auth_location = require_text(
            identity.auth_location,
            "auth_location",
        )

        value = compose_authentication_value(
            secret,
            identity.auth_prefix,
        )

        if auth_location == "header":
            reject_header_control_characters(
                auth_name,
                "Authentication header name",
            )

            reject_header_control_characters(
                value,
                "Authentication header value",
            )

            return RequestAuthentication(
                headers={
                    auth_name: value,
                }
            )

        if auth_location == "query":
            return RequestAuthentication(
                query_parameters={
                    auth_name: value,
                }
            )

        if auth_location == "cookie":
            return RequestAuthentication(
                cookies={
                    auth_name: value,
                }
            )

        raise InvalidIdentityConfigurationError(
            f"API-key authentication location {auth_location!r} is not supported."
        )

    if identity.auth_type == "basic":
        username = resolver.resolve(
            identity.secret_source,
            identity.username_reference,
        ).get_secret_value()

        password = resolver.resolve(
            identity.secret_source,
            identity.password_reference,
        ).get_secret_value()

        return RequestAuthentication(
            basic_auth=(
                username,
                password,
            )
        )

    if identity.auth_type == "cookie":
        secret = resolver.resolve(
            identity.secret_source,
            identity.secret_reference,
        ).get_secret_value()

        cookie_name = require_text(
            identity.auth_name,
            "auth_name",
        )

        reject_header_control_characters(
            cookie_name,
            "Cookie name",
        )

        return RequestAuthentication(
            cookies={
                cookie_name: secret,
            }
        )

    if identity.auth_type == "custom_header":
        secret = resolver.resolve(
            identity.secret_source,
            identity.secret_reference,
        ).get_secret_value()

        header_name = require_text(
            identity.auth_name,
            "auth_name",
        )

        header_value = compose_authentication_value(
            secret,
            identity.auth_prefix,
        )

        reject_header_control_characters(
            header_name,
            "Authentication header name",
        )

        reject_header_control_characters(
            header_value,
            "Authentication header value",
        )

        return RequestAuthentication(
            headers={
                header_name: header_value,
            }
        )

    raise InvalidIdentityConfigurationError(
        f"Unsupported identity authentication type: {identity.auth_type!r}."
    )
