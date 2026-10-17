"""Unit tests for controlled request execution."""

from collections.abc import Callable

import httpx
import pytest

from accessmatrix.execution.executor import (
    ControlledRequestExecutor,
    ExecutionResult,
    SensitiveHeaderError,
    UnsafeMethodConfirmationError,
)
from accessmatrix.execution.rate_limit import (
    RequestRateLimitError,
    SlidingWindowRateLimiter,
)
from accessmatrix.execution.safety import (
    TargetSafetyError,
    prepare_operation_target,
)
from accessmatrix.openapi.operations import (
    OpenAPIOperation,
)
from accessmatrix.persistence.models import (
    IdentityProfile,
    Project,
)
from accessmatrix.security.credentials import (
    CredentialResolver,
)

MockHandler = Callable[
    [httpx.Request],
    httpx.Response,
]


def build_project(
    *,
    base_url: str = "https://api.example.test/v1",
) -> Project:
    """Create a project model for testing."""

    return Project(
        id="project-1",
        name="Executor Project",
        base_url=base_url,
    )


def build_identity(
    *,
    auth_type: str = "none",
    secret_reference: str | None = None,
    enabled: bool = True,
) -> IdentityProfile:
    """Create an identity model for testing."""

    return IdentityProfile(
        id="identity-1",
        project_id="project-1",
        name="Customer Alice",
        role="customer",
        auth_type=auth_type,
        secret_source="environment",
        secret_reference=secret_reference,
        auth_prefix=("Bearer" if auth_type == "bearer" else None),
        enabled=enabled,
    )


def build_operation(
    *,
    method: str = "GET",
    path: str = "/invoices/{invoice_id}",
) -> OpenAPIOperation:
    """Create an OpenAPI operation for testing."""

    return OpenAPIOperation(
        key=f"{method} {path}",
        method=method,
        path=path,
        operation_id="testOperation",
        summary=None,
        description=None,
        tags=(),
        deprecated=False,
        security_required=(method != "GET"),
        parameters=(),
        request_content_types=(),
        response_codes=("200",),
    )


def build_executor(
    handler: MockHandler,
    *,
    environment: dict[str, str] | None = None,
    max_response_bytes: int = 1024,
    rate_limiter: SlidingWindowRateLimiter | None = None,
) -> ControlledRequestExecutor:
    """Create an executor with a mock transport."""

    return ControlledRequestExecutor(
        resolver=CredentialResolver(environment=(environment if environment is not None else {})),
        rate_limiter=(rate_limiter if rate_limiter is not None else SlidingWindowRateLimiter()),
        transport=httpx.MockTransport(handler),
        max_response_bytes=max_response_bytes,
    )


def test_prepare_target_encodes_path_parameter() -> None:
    """Path values should not be able to inject slash segments."""

    target = prepare_operation_target(
        "https://api.example.test/v1",
        build_operation(),
        {
            "invoice_id": "INV/1001",
        },
    )

    assert target.url == ("https://api.example.test/v1/invoices/INV%2F1001")

    assert target.origin == ("https://api.example.test:443")


def test_missing_path_parameter_is_rejected() -> None:
    """All OpenAPI path placeholders must be supplied."""

    with pytest.raises(
        TargetSafetyError,
        match="Missing required",
    ):
        prepare_operation_target(
            "https://api.example.test",
            build_operation(),
            {},
        )


def test_bearer_secret_is_redacted_from_result() -> None:
    """Authentication values must not appear in execution output."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        authorization = request.headers["Authorization"]

        assert authorization == ("Bearer secret-token")

        return httpx.Response(
            200,
            headers={
                "Content-Type": ("application/json"),
                "X-Echo-Secret": authorization,
                "Set-Cookie": ("session=secret-token"),
            },
            json={
                "authorization": authorization,
            },
        )

    executor = build_executor(
        handler,
        environment={"ACCESSMATRIX_TOKEN": ("secret-token")},
    )

    result = executor.execute(
        project=build_project(),
        identity=build_identity(
            auth_type="bearer",
            secret_reference=("ACCESSMATRIX_TOKEN"),
        ),
        operation=build_operation(),
        path_parameters={
            "invoice_id": "INV-1001",
        },
        query_parameters={},
        headers={},
        json_body=None,
        timeout_seconds=10.0,
        allow_unsafe=False,
        confirmation=None,
    )

    assert result.status_code == 200
    assert result.body_text is not None

    assert "secret-token" not in result.body_text

    assert "[REDACTED]" in result.body_text

    assert result.response_headers["set-cookie"] == "[REDACTED]"

    assert "secret-token" not in str(result.response_headers)


def test_redirect_is_not_followed() -> None:
    """Redirect responses should be returned without following them."""

    request_count = 0

    def handler(
        _: httpx.Request,
    ) -> httpx.Response:
        nonlocal request_count

        request_count += 1

        return httpx.Response(
            302,
            headers={"Location": ("https://different.example/?token=secret")},
        )

    executor = build_executor(handler)

    result = executor.execute(
        project=build_project(),
        identity=build_identity(),
        operation=build_operation(),
        path_parameters={
            "invoice_id": "INV-1001",
        },
        query_parameters={},
        headers={},
        json_body=None,
        timeout_seconds=10.0,
        allow_unsafe=False,
        confirmation=None,
    )

    assert request_count == 1
    assert result.status_code == 302
    assert result.redirect_blocked is True

    assert result.response_headers["location"] == "[REDIRECT TARGET REDACTED]"


def test_unsafe_method_requires_exact_confirmation() -> None:
    """Unsafe methods must require explicit confirmation."""

    def handler(
        _: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(200)

    executor = build_executor(handler)

    operation = build_operation(method="DELETE")

    with pytest.raises(
        UnsafeMethodConfirmationError,
        match="exact confirmation",
    ):
        executor.execute(
            project=build_project(),
            identity=build_identity(),
            operation=operation,
            path_parameters={
                "invoice_id": "INV-1001",
            },
            query_parameters={},
            headers={},
            json_body=None,
            timeout_seconds=10.0,
            allow_unsafe=True,
            confirmation="DELETE IT",
        )


def test_unsafe_method_executes_after_confirmation() -> None:
    """An exactly confirmed unsafe operation may execute."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "DELETE"

        return httpx.Response(204)

    executor = build_executor(handler)

    operation = build_operation(method="DELETE")

    result = executor.execute(
        project=build_project(),
        identity=build_identity(),
        operation=operation,
        path_parameters={
            "invoice_id": "INV-1001",
        },
        query_parameters={},
        headers={},
        json_body=None,
        timeout_seconds=10.0,
        allow_unsafe=True,
        confirmation=("EXECUTE DELETE /invoices/{invoice_id}"),
    )

    assert result.status_code == 204


def test_sensitive_user_header_is_rejected() -> None:
    """Users must not override managed authentication headers."""

    def handler(
        _: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(200)

    executor = build_executor(handler)

    with pytest.raises(
        SensitiveHeaderError,
        match="managed internally",
    ):
        executor.execute(
            project=build_project(),
            identity=build_identity(),
            operation=build_operation(),
            path_parameters={
                "invoice_id": "INV-1001",
            },
            query_parameters={},
            headers={"Authorization": ("manually-supplied")},
            json_body=None,
            timeout_seconds=10.0,
            allow_unsafe=False,
            confirmation=None,
        )


def test_response_is_truncated_at_limit() -> None:
    """Responses larger than the configured limit should be truncated."""

    def handler(
        _: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": ("text/plain")},
            content=b"A" * 100,
        )

    executor = build_executor(
        handler,
        max_response_bytes=32,
    )

    result = executor.execute(
        project=build_project(),
        identity=build_identity(),
        operation=build_operation(),
        path_parameters={
            "invoice_id": "INV-1001",
        },
        query_parameters={},
        headers={},
        json_body=None,
        timeout_seconds=10.0,
        allow_unsafe=False,
        confirmation=None,
    )

    assert result.body_truncated is True
    assert result.body_bytes_captured == 32
    assert result.body_text == "A" * 32


def test_rate_limiter_blocks_excess_requests() -> None:
    """The executor should enforce per-identity request limits."""

    current_time = [0.0]

    def clock() -> float:
        return current_time[0]

    rate_limiter = SlidingWindowRateLimiter(
        limit=1,
        window_seconds=60.0,
        clock=clock,
    )

    def handler(
        _: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(200)

    executor = build_executor(
        handler,
        rate_limiter=rate_limiter,
    )

    project = build_project()
    identity = build_identity()
    operation = build_operation()

    def execute_once() -> ExecutionResult:
        return executor.execute(
            project=project,
            identity=identity,
            operation=operation,
            path_parameters={
                "invoice_id": "INV-1001",
            },
            query_parameters={},
            headers={},
            json_body=None,
            timeout_seconds=10.0,
            allow_unsafe=False,
            confirmation=None,
        )

    first_result = execute_once()

    assert first_result.rate_limit_remaining == 0

    with pytest.raises(RequestRateLimitError):
        execute_once()

    current_time[0] = 61.0

    second_result = execute_once()

    assert second_result.status_code == 200
