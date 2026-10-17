"""Controlled HTTP request execution."""

import base64
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from accessmatrix.execution.rate_limit import (
    SlidingWindowRateLimiter,
)
from accessmatrix.execution.safety import (
    PreparedTarget,
    prepare_operation_target,
)
from accessmatrix.openapi.operations import (
    OpenAPIOperation,
)
from accessmatrix.persistence.models import (
    IdentityProfile,
    Project,
)
from accessmatrix.security.authentication import (
    RequestAuthentication,
    build_request_authentication,
)
from accessmatrix.security.credentials import (
    CredentialResolver,
)

SAFE_METHODS = frozenset(
    {
        "GET",
        "HEAD",
        "OPTIONS",
    }
)

UNSAFE_METHODS = frozenset(
    {
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    }
)

COMPLETELY_BLOCKED_METHODS = frozenset(
    {
        "TRACE",
    }
)

BLOCKED_USER_HEADERS = frozenset(
    {
        "authorization",
        "connection",
        "content-length",
        "cookie",
        "host",
        "proxy-authorization",
        "te",
        "transfer-encoding",
        "upgrade",
    }
)

SENSITIVE_RESPONSE_HEADERS = frozenset(
    {
        "authorization",
        "cookie",
        "proxy-authenticate",
        "proxy-authorization",
        "set-cookie",
    }
)

DEFAULT_MAX_RESPONSE_BYTES = 1024 * 1024

DEFAULT_MAX_REQUEST_BODY_BYTES = 256 * 1024


class RequestExecutionError(RuntimeError):
    """Base controlled-execution error."""


class UnsafeMethodConfirmationError(RequestExecutionError):
    """Raised when unsafe execution has not been confirmed."""


class SensitiveHeaderError(RequestExecutionError):
    """Raised when a protected request header is supplied."""


class RequestBodyTooLargeError(RequestExecutionError):
    """Raised when a request body exceeds the configured limit."""


class RequestExecutionTimeoutError(RequestExecutionError):
    """Raised when the target does not respond within the timeout."""


class RequestTransportError(RequestExecutionError):
    """Raised when the HTTP transport fails."""


@dataclass(frozen=True)
class ExecutionResult:
    """Safe result returned by the controlled executor."""

    operation_key: str
    identity_id: str
    identity_name: str
    method: str
    request_url: str
    request_header_names: tuple[str, ...]
    status_code: int
    reason_phrase: str
    elapsed_ms: float
    response_headers: dict[str, str]
    body_text: str | None
    body_bytes_captured: int
    body_truncated: bool
    declared_content_length: int | None
    redirect_blocked: bool
    rate_limit_remaining: int


def validate_mapping(
    mapping_name: str,
    values: dict[str, str],
    *,
    maximum_items: int,
    maximum_name_length: int,
    maximum_value_length: int,
) -> None:
    """Validate user-controlled string mappings."""

    if len(values) > maximum_items:
        raise RequestExecutionError(f"{mapping_name} contains too many entries.")

    for name, value in values.items():
        if not isinstance(name, str):
            raise RequestExecutionError(f"{mapping_name} names must be strings.")

        if not isinstance(value, str):
            raise RequestExecutionError(f"{mapping_name} values must be strings.")

        if not name.strip():
            raise RequestExecutionError(f"{mapping_name} contains an empty name.")

        if len(name) > maximum_name_length:
            raise RequestExecutionError(
                f"A {mapping_name} name exceeds the {maximum_name_length}-character limit."
            )

        if len(value) > maximum_value_length:
            raise RequestExecutionError(
                f"A {mapping_name} value exceeds the {maximum_value_length}-character limit."
            )

        if "\r" in name or "\n" in name or "\r" in value or "\n" in value:
            raise RequestExecutionError(
                f"{mapping_name} must not contain carriage-return or newline characters."
            )


def validate_user_headers(
    headers: dict[str, str],
) -> None:
    """Validate and protect request header input."""

    validate_mapping(
        "Request headers",
        headers,
        maximum_items=50,
        maximum_name_length=256,
        maximum_value_length=8192,
    )

    for header_name in headers:
        if header_name.strip().lower() in BLOCKED_USER_HEADERS:
            raise SensitiveHeaderError(
                f"Header {header_name!r} is managed internally and cannot be supplied."
            )


def merge_authentication(
    user_headers: dict[str, str],
    user_query_parameters: dict[str, str],
    authentication: RequestAuthentication,
) -> tuple[
    dict[str, str],
    dict[str, str],
]:
    """Merge authentication without allowing collisions."""

    merged_headers = {
        "Accept": ("application/json, text/plain;q=0.9, */*;q=0.8"),
        "User-Agent": "AccessMatrix",
        **user_headers,
    }

    existing_header_names = {header_name.lower() for header_name in merged_headers}

    for (
        auth_header_name,
        auth_header_value,
    ) in authentication.headers.items():
        if auth_header_name.lower() in existing_header_names:
            raise SensitiveHeaderError(
                "An authentication header conflicts with a configured request header."
            )

        merged_headers[auth_header_name] = auth_header_value

        existing_header_names.add(auth_header_name.lower())

    merged_query_parameters = dict(user_query_parameters)

    for (
        parameter_name,
        parameter_value,
    ) in authentication.query_parameters.items():
        if parameter_name in merged_query_parameters:
            raise RequestExecutionError(
                "An authentication query parameter conflicts with a configured query parameter."
            )

        merged_query_parameters[parameter_name] = parameter_value

    return (
        merged_headers,
        merged_query_parameters,
    )


def collect_secret_values(
    authentication: RequestAuthentication,
) -> tuple[str, ...]:
    """Collect resolved values used only for output redaction."""

    candidates: list[str] = []

    configured_values = [
        *authentication.headers.values(),
        *authentication.query_parameters.values(),
        *authentication.cookies.values(),
    ]

    for value in configured_values:
        if value:
            candidates.append(value)

        if " " in value:
            _, possible_secret = value.split(
                " ",
                1,
            )

            if possible_secret:
                candidates.append(possible_secret)

    if authentication.basic_auth is not None:
        username, password = authentication.basic_auth

        candidates.extend(
            [
                username,
                password,
            ]
        )

        basic_value = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")

        candidates.extend(
            [
                basic_value,
                f"Basic {basic_value}",
            ]
        )

    unique_values = {value for value in candidates if value}

    return tuple(
        sorted(
            unique_values,
            key=len,
            reverse=True,
        )
    )


def redact_text(
    value: str,
    secret_values: tuple[str, ...],
) -> str:
    """Redact resolved credential values from text."""

    redacted = value

    for secret_value in secret_values:
        redacted = redacted.replace(
            secret_value,
            "[REDACTED]",
        )

    return redacted


def redact_response_headers(
    headers: httpx.Headers,
    secret_values: tuple[str, ...],
) -> dict[str, str]:
    """Return safe response headers."""

    redacted_headers: dict[
        str,
        str,
    ] = {}

    for (
        header_name,
        header_value,
    ) in headers.multi_items():
        normalized_name = header_name.lower()

        if normalized_name in SENSITIVE_RESPONSE_HEADERS:
            safe_value = "[REDACTED]"

        elif normalized_name == "location":
            safe_value = "[REDIRECT TARGET REDACTED]"

        else:
            safe_value = redact_text(
                header_value,
                secret_values,
            )

        if header_name in redacted_headers:
            redacted_headers[header_name] = f"{redacted_headers[header_name]}, {safe_value}"
        else:
            redacted_headers[header_name] = safe_value

    return redacted_headers


def is_textual_response(
    content_type: str,
) -> bool:
    """Return whether a response body can be displayed as text."""

    normalized_content_type = content_type.lower()

    return (
        normalized_content_type.startswith("text/")
        or "json" in normalized_content_type
        or "xml" in normalized_content_type
        or "javascript" in normalized_content_type
        or ("application/x-www-form-urlencoded" in normalized_content_type)
    )


def parse_declared_content_length(
    headers: httpx.Headers,
) -> int | None:
    """Parse the declared response length."""

    raw_content_length = headers.get("content-length")

    if raw_content_length is None:
        return None

    try:
        parsed_length = int(raw_content_length)
    except ValueError:
        return None

    if parsed_length < 0:
        return None

    return parsed_length


def build_basic_auth(
    authentication: RequestAuthentication,
) -> httpx.BasicAuth | None:
    """Build HTTPX Basic authentication when configured."""

    if authentication.basic_auth is None:
        return None

    username, password = authentication.basic_auth

    return httpx.BasicAuth(
        username,
        password,
    )


class ControlledRequestExecutor:
    """Execute one OpenAPI operation with strict safety controls."""

    def __init__(
        self,
        *,
        resolver: CredentialResolver,
        rate_limiter: SlidingWindowRateLimiter,
        transport: httpx.BaseTransport | None = None,
        max_response_bytes: int = (DEFAULT_MAX_RESPONSE_BYTES),
        max_request_body_bytes: int = (DEFAULT_MAX_REQUEST_BODY_BYTES),
    ) -> None:
        """Initialize the executor."""

        if max_response_bytes < 1:
            raise ValueError("The response limit must be positive.")

        if max_request_body_bytes < 1:
            raise ValueError("The request-body limit must be positive.")

        self._resolver = resolver
        self._rate_limiter = rate_limiter
        self._transport = transport
        self._max_response_bytes = max_response_bytes
        self._max_request_body_bytes = max_request_body_bytes

    def execute(
        self,
        *,
        project: Project,
        identity: IdentityProfile,
        operation: OpenAPIOperation,
        path_parameters: dict[str, str],
        query_parameters: dict[str, str],
        headers: dict[str, str],
        json_body: Any | None,
        timeout_seconds: float,
        allow_unsafe: bool,
        confirmation: str | None,
    ) -> ExecutionResult:
        """Execute a controlled HTTP request."""

        target = prepare_operation_target(
            project.base_url,
            operation,
            path_parameters,
        )

        method = target.method.upper()

        self._validate_method_confirmation(
            operation,
            allow_unsafe,
            confirmation,
        )

        if not (1.0 <= timeout_seconds <= 30.0):
            raise RequestExecutionError("The request timeout must be between 1 and 30 seconds.")

        validate_user_headers(headers)

        validate_mapping(
            "Query parameters",
            query_parameters,
            maximum_items=100,
            maximum_name_length=256,
            maximum_value_length=4096,
        )

        authentication = build_request_authentication(
            identity,
            self._resolver,
        )

        secret_values = collect_secret_values(authentication)

        (
            merged_headers,
            merged_query_parameters,
        ) = merge_authentication(
            headers,
            query_parameters,
            authentication,
        )

        body_content = self._serialize_body(json_body)

        if body_content is not None and not any(
            header_name.lower() == "content-type" for header_name in merged_headers
        ):
            merged_headers["Content-Type"] = "application/json"

        rate_limit_key = f"{project.id}:{identity.id}"

        rate_limit_remaining = self._rate_limiter.consume(rate_limit_key)

        return self._send_request(
            target=target,
            identity=identity,
            method=method,
            headers=merged_headers,
            query_parameters=(merged_query_parameters),
            cookies=authentication.cookies,
            basic_auth=build_basic_auth(authentication),
            body_content=body_content,
            timeout_seconds=(timeout_seconds),
            secret_values=secret_values,
            rate_limit_remaining=(rate_limit_remaining),
        )

    def _validate_method_confirmation(
        self,
        operation: OpenAPIOperation,
        allow_unsafe: bool,
        confirmation: str | None,
    ) -> None:
        """Enforce blocked and unsafe method controls."""

        method = operation.method.upper()

        if method in COMPLETELY_BLOCKED_METHODS:
            raise UnsafeMethodConfirmationError(f"{method} requests are blocked by AccessMatrix.")

        if method in SAFE_METHODS:
            return

        if method not in UNSAFE_METHODS:
            raise UnsafeMethodConfirmationError(
                f"HTTP method {method!r} is not supported by the controlled executor."
            )

        expected_confirmation = f"EXECUTE {method} {operation.path}"

        normalized_confirmation = (
            confirmation.strip()
            if isinstance(
                confirmation,
                str,
            )
            else ""
        )

        if not allow_unsafe or normalized_confirmation != expected_confirmation:
            raise UnsafeMethodConfirmationError(
                "Unsafe execution requires allow_unsafe=true "
                "and the exact confirmation phrase: "
                f"{expected_confirmation}"
            )

    def _serialize_body(
        self,
        json_body: Any | None,
    ) -> bytes | None:
        """Serialize and enforce the request-body limit."""

        if json_body is None:
            return None

        try:
            serialized = json.dumps(
                json_body,
                ensure_ascii=False,
                separators=(
                    ",",
                    ":",
                ),
            ).encode("utf-8")
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise RequestExecutionError("The request body is not valid JSON data.") from exc

        if len(serialized) > self._max_request_body_bytes:
            raise RequestBodyTooLargeError(
                "The serialized JSON request body exceeds the 256 KiB limit."
            )

        return serialized

    def _send_request(
        self,
        *,
        target: PreparedTarget,
        identity: IdentityProfile,
        method: str,
        headers: dict[str, str],
        query_parameters: dict[str, str],
        cookies: dict[str, str],
        basic_auth: httpx.BasicAuth | None,
        body_content: bytes | None,
        timeout_seconds: float,
        secret_values: tuple[str, ...],
        rate_limit_remaining: int,
    ) -> ExecutionResult:
        """Send and safely capture an HTTP response."""

        timeout = httpx.Timeout(
            timeout_seconds,
            connect=min(
                timeout_seconds,
                10.0,
            ),
            read=timeout_seconds,
            write=timeout_seconds,
            pool=min(
                timeout_seconds,
                5.0,
            ),
        )

        limits = httpx.Limits(
            max_connections=10,
            max_keepalive_connections=5,
            keepalive_expiry=5.0,
        )

        started_at = time.perf_counter()

        try:
            with (
                httpx.Client(
                    timeout=timeout,
                    limits=limits,
                    follow_redirects=False,
                    trust_env=False,
                    transport=self._transport,
                ) as client,
                client.stream(
                    method,
                    target.url,
                    params=(query_parameters or None),
                    headers=headers,
                    cookies=(cookies or None),
                    auth=basic_auth,
                    content=body_content,
                ) as response,
            ):
                (
                    captured_body,
                    body_truncated,
                ) = self._capture_body(response)

                elapsed_ms = round(
                    (time.perf_counter() - started_at) * 1000,
                    2,
                )

                content_type = response.headers.get(
                    "content-type",
                    "",
                )

                body_text: str | None

                if is_textual_response(content_type):
                    encoding = response.encoding or "utf-8"

                    body_text = captured_body.decode(
                        encoding,
                        errors="replace",
                    )

                    body_text = redact_text(
                        body_text,
                        secret_values,
                    )
                else:
                    body_text = None

                redirect_blocked = (
                    300 <= response.status_code < 400 and "location" in response.headers
                )

                return ExecutionResult(
                    operation_key=(target.operation_key),
                    identity_id=(identity.id),
                    identity_name=(identity.name),
                    method=method,
                    request_url=target.url,
                    request_header_names=tuple(
                        sorted(
                            headers,
                            key=str.lower,
                        )
                    ),
                    status_code=(response.status_code),
                    reason_phrase=(response.reason_phrase),
                    elapsed_ms=elapsed_ms,
                    response_headers=(
                        redact_response_headers(
                            response.headers,
                            secret_values,
                        )
                    ),
                    body_text=body_text,
                    body_bytes_captured=len(captured_body),
                    body_truncated=(body_truncated),
                    declared_content_length=(parse_declared_content_length(response.headers)),
                    redirect_blocked=(redirect_blocked),
                    rate_limit_remaining=(rate_limit_remaining),
                )

        except httpx.TimeoutException as exc:
            raise RequestExecutionTimeoutError(
                "The target API did not respond within the configured timeout."
            ) from exc

        except httpx.InvalidURL as exc:
            raise RequestExecutionError("The generated request URL is invalid.") from exc

        except httpx.RequestError as exc:
            raise RequestTransportError(
                "The request could not be completed because the target transport failed."
            ) from exc

    def _capture_body(
        self,
        response: httpx.Response,
    ) -> tuple[
        bytes,
        bool,
    ]:
        """Capture at most the configured number of bytes."""

        captured = bytearray()
        truncated = False

        for chunk in response.iter_bytes():
            if not chunk:
                continue

            remaining_with_marker = self._max_response_bytes + 1 - len(captured)

            if remaining_with_marker <= 0:
                truncated = True
                break

            captured.extend(chunk[:remaining_with_marker])

            if len(captured) > self._max_response_bytes:
                truncated = True

                del captured[self._max_response_bytes :]

                break

        return (
            bytes(captured),
            truncated,
        )
