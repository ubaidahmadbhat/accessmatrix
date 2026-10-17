"""Unit tests for secure credential resolution and authentication."""

import pytest
from keyring.errors import KeyringError

from accessmatrix.persistence.models import IdentityProfile
from accessmatrix.security.authentication import (
    IdentityDisabledError,
    RequestAuthentication,
    build_request_authentication,
)
from accessmatrix.security.credentials import (
    KEYRING_SERVICE_NAME,
    CredentialBackendError,
    CredentialResolver,
    CredentialUnavailableError,
)


def build_identity(
    *,
    auth_type: str,
    enabled: bool = True,
    secret_source: str = "environment",
    secret_reference: str | None = None,
    username_reference: str | None = None,
    password_reference: str | None = None,
    auth_location: str | None = None,
    auth_name: str | None = None,
    auth_prefix: str | None = None,
) -> IdentityProfile:
    """Create an identity model for unit testing."""

    return IdentityProfile(
        id="identity-1",
        project_id="project-1",
        name="Test Identity",
        role="tester",
        auth_type=auth_type,
        enabled=enabled,
        secret_source=secret_source,
        secret_reference=secret_reference,
        username_reference=username_reference,
        password_reference=password_reference,
        auth_location=auth_location,
        auth_name=auth_name,
        auth_prefix=auth_prefix,
    )


def test_resolve_environment_credential() -> None:
    """Environment references should resolve securely."""

    resolver = CredentialResolver(
        environment={
            "ACCESSMATRIX_TEST_TOKEN": "secret-token-value",
        }
    )

    secret = resolver.resolve(
        "environment",
        "ACCESSMATRIX_TEST_TOKEN",
    )

    assert secret.get_secret_value() == "secret-token-value"

    assert "secret-token-value" not in repr(secret)


def test_missing_environment_credential_is_rejected() -> None:
    """Missing environment credentials should fail."""

    resolver = CredentialResolver(environment={})

    with pytest.raises(CredentialUnavailableError):
        resolver.resolve(
            "environment",
            "ACCESSMATRIX_MISSING_TOKEN",
        )


def test_resolve_keyring_credential() -> None:
    """Keyring references should use the AccessMatrix service."""

    calls: list[tuple[str, str]] = []

    def fake_keyring_getter(
        service_name: str,
        username: str,
    ) -> str | None:
        calls.append(
            (
                service_name,
                username,
            )
        )

        return "keyring-secret-value"

    resolver = CredentialResolver(
        environment={},
        keyring_getter=fake_keyring_getter,
    )

    secret = resolver.resolve(
        "keyring",
        "customer-alice-token",
    )

    assert secret.get_secret_value() == "keyring-secret-value"

    assert calls == [
        (
            KEYRING_SERVICE_NAME,
            "customer-alice-token",
        )
    ]


def test_keyring_backend_error_is_redacted() -> None:
    """Keyring backend failures should be normalized."""

    def failing_keyring_getter(
        _: str,
        __: str,
    ) -> str | None:
        raise KeyringError("backend failure")

    resolver = CredentialResolver(
        environment={},
        keyring_getter=failing_keyring_getter,
    )

    with pytest.raises(
        CredentialBackendError,
        match=("operating-system keyring could not be accessed"),
    ):
        resolver.resolve(
            "keyring",
            "customer-alice-token",
        )


def test_build_bearer_authentication() -> None:
    """Bearer authentication should create an Authorization header."""

    resolver = CredentialResolver(
        environment={
            "ACCESSMATRIX_BEARER_TOKEN": "bearer-secret",
        }
    )

    identity = build_identity(
        auth_type="bearer",
        secret_reference=("ACCESSMATRIX_BEARER_TOKEN"),
        auth_prefix="Bearer",
    )

    authentication = build_request_authentication(
        identity,
        resolver,
    )

    assert authentication.headers == {
        "Authorization": "Bearer bearer-secret",
    }

    assert "bearer-secret" not in repr(authentication)


def test_build_query_api_key_authentication() -> None:
    """API keys should support query parameters."""

    resolver = CredentialResolver(
        environment={
            "ACCESSMATRIX_QUERY_KEY": "query-secret",
        }
    )

    identity = build_identity(
        auth_type="api_key",
        secret_reference=("ACCESSMATRIX_QUERY_KEY"),
        auth_location="query",
        auth_name="api_key",
        auth_prefix="Token",
    )

    authentication = build_request_authentication(
        identity,
        resolver,
    )

    assert authentication.query_parameters == {
        "api_key": "Token query-secret",
    }

    assert authentication.headers == {}
    assert authentication.cookies == {}


def test_build_basic_authentication() -> None:
    """Basic authentication should resolve both references."""

    resolver = CredentialResolver(
        environment={
            "ACCESSMATRIX_BASIC_USERNAME": "alice",
            "ACCESSMATRIX_BASIC_PASSWORD": "basic-secret",
        }
    )

    identity = build_identity(
        auth_type="basic",
        username_reference=("ACCESSMATRIX_BASIC_USERNAME"),
        password_reference=("ACCESSMATRIX_BASIC_PASSWORD"),
    )

    authentication = build_request_authentication(
        identity,
        resolver,
    )

    assert authentication.basic_auth == (
        "alice",
        "basic-secret",
    )

    assert "basic-secret" not in repr(authentication)


def test_build_cookie_authentication() -> None:
    """Cookie authentication should create a cookie value."""

    resolver = CredentialResolver(
        environment={
            "ACCESSMATRIX_COOKIE": "cookie-secret",
        }
    )

    identity = build_identity(
        auth_type="cookie",
        secret_reference=("ACCESSMATRIX_COOKIE"),
        auth_location="cookie",
        auth_name="session_id",
    )

    authentication = build_request_authentication(
        identity,
        resolver,
    )

    assert authentication.cookies == {
        "session_id": "cookie-secret",
    }


def test_build_anonymous_authentication() -> None:
    """Anonymous identities should have no credentials."""

    resolver = CredentialResolver(environment={})

    identity = build_identity(
        auth_type="none",
    )

    authentication = build_request_authentication(
        identity,
        resolver,
    )

    assert authentication == (RequestAuthentication())


def test_disabled_identity_is_rejected() -> None:
    """Disabled identities must not be used for requests."""

    resolver = CredentialResolver(environment={})

    identity = build_identity(
        auth_type="none",
        enabled=False,
    )

    with pytest.raises(
        IdentityDisabledError,
        match="disabled",
    ):
        build_request_authentication(
            identity,
            resolver,
        )
