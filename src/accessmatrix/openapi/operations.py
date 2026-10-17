"""OpenAPI operation discovery and normalization."""

from dataclasses import dataclass
from typing import Any, cast

from accessmatrix.openapi.loader import HTTP_METHODS

METHOD_ORDER = {
    "GET": 0,
    "POST": 1,
    "PUT": 2,
    "PATCH": 3,
    "DELETE": 4,
    "HEAD": 5,
    "OPTIONS": 6,
    "TRACE": 7,
    "QUERY": 8,
}


@dataclass(frozen=True)
class OpenAPIParameter:
    """A normalized OpenAPI parameter."""

    name: str
    location: str
    required: bool
    schema_type: str | None
    description: str | None


@dataclass(frozen=True)
class OpenAPIOperation:
    """A normalized OpenAPI operation."""

    key: str
    method: str
    path: str
    operation_id: str
    summary: str | None
    description: str | None
    tags: tuple[str, ...]
    deprecated: bool
    security_required: bool
    parameters: tuple[OpenAPIParameter, ...]
    request_content_types: tuple[str, ...]
    response_codes: tuple[str, ...]


def decode_json_pointer_part(
    value: str,
) -> str:
    """Decode one JSON Pointer path component."""

    return value.replace(
        "~1",
        "/",
    ).replace(
        "~0",
        "~",
    )


def resolve_local_reference(
    document: dict[str, Any],
    candidate: Any,
) -> dict[str, Any] | None:
    """Resolve a local OpenAPI reference or return an inline object."""

    if not isinstance(candidate, dict):
        return None

    candidate_object = cast(
        dict[str, Any],
        candidate,
    )

    reference = candidate_object.get("$ref")

    if not isinstance(reference, str):
        return candidate_object

    if not reference.startswith("#/"):
        return None

    current: Any = document

    for raw_part in reference[2:].split("/"):
        part = decode_json_pointer_part(raw_part)

        if not isinstance(current, dict):
            return None

        current = current.get(part)

    if not isinstance(current, dict):
        return None

    return cast(
        dict[str, Any],
        current,
    )


def get_schema_type(
    document: dict[str, Any],
    schema_candidate: Any,
) -> str | None:
    """Return a readable schema type."""

    schema = resolve_local_reference(
        document,
        schema_candidate,
    )

    if schema is None:
        return None

    raw_type = schema.get("type")

    if isinstance(raw_type, str):
        return raw_type

    if isinstance(raw_type, list):
        type_names = [item for item in raw_type if isinstance(item, str)]

        if type_names:
            return " | ".join(type_names)

    if "allOf" in schema:
        return "allOf"

    if "oneOf" in schema:
        return "oneOf"

    if "anyOf" in schema:
        return "anyOf"

    return None


def extract_parameters(
    document: dict[str, Any],
    path_item: dict[str, Any],
    operation: dict[str, Any],
) -> tuple[OpenAPIParameter, ...]:
    """Combine path-level and operation-level parameters."""

    discovered: dict[
        tuple[str, str],
        OpenAPIParameter,
    ] = {}

    for source in (
        path_item,
        operation,
    ):
        raw_parameters = source.get("parameters")

        if not isinstance(
            raw_parameters,
            list,
        ):
            continue

        for raw_parameter in raw_parameters:
            parameter = resolve_local_reference(
                document,
                raw_parameter,
            )

            if parameter is None:
                continue

            name = parameter.get("name")
            location = parameter.get("in")

            if not isinstance(name, str):
                continue

            if not isinstance(
                location,
                str,
            ):
                location = "unknown"

            required = parameter.get("required") is True

            if location == "path":
                required = True

            raw_description = parameter.get("description")

            description = (
                raw_description.strip()
                if isinstance(
                    raw_description,
                    str,
                )
                and raw_description.strip()
                else None
            )

            normalized = OpenAPIParameter(
                name=name,
                location=location,
                required=required,
                schema_type=get_schema_type(
                    document,
                    parameter.get("schema"),
                ),
                description=description,
            )

            discovered[
                (
                    name,
                    location,
                )
            ] = normalized

    return tuple(discovered.values())


def extract_request_content_types(
    document: dict[str, Any],
    operation: dict[str, Any],
) -> tuple[str, ...]:
    """Return request-body media types."""

    request_body = resolve_local_reference(
        document,
        operation.get("requestBody"),
    )

    if request_body is None:
        return ()

    content = request_body.get("content")

    if not isinstance(content, dict):
        return ()

    return tuple(
        sorted(
            content_type
            for content_type in content
            if isinstance(
                content_type,
                str,
            )
        )
    )


def extract_response_codes(
    operation: dict[str, Any],
) -> tuple[str, ...]:
    """Return documented response status codes."""

    responses = operation.get("responses")

    if not isinstance(responses, dict):
        return ()

    return tuple(sorted(str(response_code) for response_code in responses))


def extract_tags(
    operation: dict[str, Any],
) -> tuple[str, ...]:
    """Return operation tags."""

    raw_tags = operation.get("tags")

    if not isinstance(raw_tags, list):
        return ()

    return tuple(tag.strip() for tag in raw_tags if isinstance(tag, str) and tag.strip())


def has_security_requirement(
    document: dict[str, Any],
    operation: dict[str, Any],
) -> bool:
    """Determine whether an operation requires authentication."""

    security = operation.get("security") if "security" in operation else document.get("security")

    return isinstance(security, list) and len(security) > 0


def normalize_optional_text(
    value: Any,
) -> str | None:
    """Normalize an optional OpenAPI text field."""

    if not isinstance(value, str):
        return None

    normalized = value.strip()

    return normalized or None


def discover_operations(
    document: dict[str, Any],
) -> list[OpenAPIOperation]:
    """Discover all executable OpenAPI operations."""

    paths = document.get("paths")

    if not isinstance(paths, dict):
        return []

    operations: list[OpenAPIOperation] = []

    for path in sorted(paths):
        if not isinstance(path, str):
            continue

        path_item = resolve_local_reference(
            document,
            paths[path],
        )

        if path_item is None:
            continue

        for (
            raw_method,
            raw_operation,
        ) in path_item.items():
            if not isinstance(
                raw_method,
                str,
            ):
                continue

            method = raw_method.lower()

            if method not in HTTP_METHODS:
                continue

            operation = resolve_local_reference(
                document,
                raw_operation,
            )

            if operation is None:
                continue

            normalized_method = method.upper()

            raw_operation_id = operation.get("operationId")

            operation_id = (
                raw_operation_id.strip()
                if isinstance(
                    raw_operation_id,
                    str,
                )
                and raw_operation_id.strip()
                else f"{method}:{path}"
            )

            operations.append(
                OpenAPIOperation(
                    key=(f"{normalized_method} {path}"),
                    method=normalized_method,
                    path=path,
                    operation_id=(operation_id),
                    summary=(normalize_optional_text(operation.get("summary"))),
                    description=(normalize_optional_text(operation.get("description"))),
                    tags=extract_tags(operation),
                    deprecated=(operation.get("deprecated") is True),
                    security_required=(
                        has_security_requirement(
                            document,
                            operation,
                        )
                    ),
                    parameters=(
                        extract_parameters(
                            document,
                            path_item,
                            operation,
                        )
                    ),
                    request_content_types=(
                        extract_request_content_types(
                            document,
                            operation,
                        )
                    ),
                    response_codes=(extract_response_codes(operation)),
                )
            )

    operations.sort(
        key=lambda operation: (
            operation.path,
            METHOD_ORDER.get(
                operation.method,
                99,
            ),
            operation.method,
        )
    )

    return operations
