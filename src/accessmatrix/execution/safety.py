"""Target URL construction and exact-origin safety controls."""

import re
from dataclasses import dataclass
from urllib.parse import (
    quote,
    unquote,
    urlsplit,
    urlunsplit,
)

from accessmatrix.openapi.operations import (
    OpenAPIOperation,
)

PATH_PARAMETER_PATTERN = re.compile(r"\{([^{}]+)\}")

ALLOWED_SCHEMES = frozenset(
    {
        "http",
        "https",
    }
)


class TargetSafetyError(ValueError):
    """Raised when a request target violates safety controls."""


@dataclass(frozen=True)
class PreparedTarget:
    """A validated request target."""

    operation_key: str
    method: str
    operation_path: str
    rendered_path: str
    url: str
    origin: str


def normalize_origin(
    scheme: str,
    hostname: str,
    port: int | None,
) -> str:
    """Return a normalized HTTP origin."""

    normalized_scheme = scheme.lower()
    normalized_hostname = hostname.lower().rstrip(".")

    default_port = 80 if normalized_scheme == "http" else 443

    effective_port = port if port is not None else default_port

    return f"{normalized_scheme}://{normalized_hostname}:{effective_port}"


def validate_base_url(
    base_url: str | None,
) -> tuple[
    str,
    str,
    str,
    str,
]:
    """Validate a project base URL.

    Returns the scheme, network location, base path,
    and normalized origin.
    """

    normalized_base_url = base_url.strip() if isinstance(base_url, str) else ""

    if not normalized_base_url:
        raise TargetSafetyError("The project does not have a target base URL.")

    try:
        parsed = urlsplit(normalized_base_url)

        port = parsed.port
    except ValueError as exc:
        raise TargetSafetyError("The project base URL contains an invalid port.") from exc

    scheme = parsed.scheme.lower()

    if scheme not in ALLOWED_SCHEMES:
        raise TargetSafetyError("Only HTTP and HTTPS target URLs are supported.")

    if parsed.hostname is None:
        raise TargetSafetyError("The project base URL must include a hostname.")

    if parsed.username is not None or parsed.password is not None:
        raise TargetSafetyError("Credentials must not be embedded in the project base URL.")

    if parsed.query:
        raise TargetSafetyError("The project base URL must not contain a query string.")

    if parsed.fragment:
        raise TargetSafetyError("The project base URL must not contain a fragment.")

    if "\\" in parsed.path:
        raise TargetSafetyError("The project base URL path must not contain backslashes.")

    origin = normalize_origin(
        scheme,
        parsed.hostname,
        port,
    )

    base_path = parsed.path.rstrip("/")

    return (
        scheme,
        parsed.netloc,
        base_path,
        origin,
    )


def render_operation_path(
    operation_path: str,
    path_parameters: dict[str, str],
) -> str:
    """Render encoded values into an OpenAPI path template."""

    if not operation_path.startswith("/"):
        raise TargetSafetyError("The OpenAPI operation path must begin with '/'.")

    if "\\" in operation_path:
        raise TargetSafetyError("The OpenAPI operation path must not contain backslashes.")

    if any(ord(character) < 32 for character in operation_path):
        raise TargetSafetyError("The OpenAPI operation path contains control characters.")

    placeholder_names = set(PATH_PARAMETER_PATTERN.findall(operation_path))

    supplied_names = set(path_parameters)

    missing_names = placeholder_names - supplied_names

    extra_names = supplied_names - placeholder_names

    if missing_names:
        missing_list = ", ".join(sorted(missing_names))

        raise TargetSafetyError(f"Missing required path parameters: {missing_list}.")

    if extra_names:
        extra_list = ", ".join(sorted(extra_names))

        raise TargetSafetyError(f"Unexpected path parameters were supplied: {extra_list}.")

    def replace_parameter(
        match: re.Match[str],
    ) -> str:
        parameter_name = match.group(1)
        parameter_value = path_parameters[parameter_name]

        if not isinstance(
            parameter_value,
            str,
        ):
            raise TargetSafetyError("Path parameter values must be strings.")

        if len(parameter_value) > 2048:
            raise TargetSafetyError("A path parameter exceeds the 2048-character limit.")

        return quote(
            parameter_value,
            safe="",
        )

    rendered_path = PATH_PARAMETER_PATTERN.sub(
        replace_parameter,
        operation_path,
    )

    decoded_segments = [unquote(segment) for segment in rendered_path.split("/")]

    if any(segment in {".", ".."} for segment in decoded_segments):
        raise TargetSafetyError("Dot path segments are not permitted.")

    return rendered_path


def prepare_operation_target(
    base_url: str | None,
    operation: OpenAPIOperation,
    path_parameters: dict[str, str],
) -> PreparedTarget:
    """Build a request target on the project's exact origin."""

    (
        scheme,
        network_location,
        base_path,
        allowed_origin,
    ) = validate_base_url(base_url)

    rendered_operation_path = render_operation_path(
        operation.path,
        path_parameters,
    )

    combined_path = f"{base_path}/{rendered_operation_path.lstrip('/')}"

    if not combined_path.startswith("/"):
        combined_path = f"/{combined_path}"

    target_url = urlunsplit(
        (
            scheme,
            network_location,
            combined_path,
            "",
            "",
        )
    )

    try:
        parsed_target = urlsplit(target_url)

        target_port = parsed_target.port
    except ValueError as exc:
        raise TargetSafetyError("The generated target URL is invalid.") from exc

    if parsed_target.hostname is None:
        raise TargetSafetyError("The generated target URL does not contain a hostname.")

    target_origin = normalize_origin(
        parsed_target.scheme,
        parsed_target.hostname,
        target_port,
    )

    if target_origin != allowed_origin:
        raise TargetSafetyError(
            "The generated request target does not match the configured project origin."
        )

    return PreparedTarget(
        operation_key=operation.key,
        method=operation.method,
        operation_path=operation.path,
        rendered_path=combined_path,
        url=target_url,
        origin=allowed_origin,
    )
