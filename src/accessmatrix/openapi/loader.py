"""OpenAPI document parsing and validation."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from openapi_spec_validator import validate
from ruamel.yaml import YAML

HTTP_METHODS = frozenset(
    {
        "get",
        "put",
        "post",
        "delete",
        "options",
        "head",
        "patch",
        "trace",
        "query",
    }
)


class OpenAPIImportError(ValueError):
    """Raised when an OpenAPI document cannot be imported."""


@dataclass(frozen=True)
class OpenAPIMetadata:
    """Metadata discovered from an OpenAPI specification."""

    version: str
    title: str
    operation_count: int


def parse_openapi_document(
    content: bytes,
    filename: str,
) -> tuple[dict[str, Any], OpenAPIMetadata]:
    """Parse and validate an OpenAPI YAML or JSON document."""

    suffix = Path(filename).suffix.lower()

    if suffix not in {".yaml", ".yml", ".json"}:
        raise OpenAPIImportError("Only .yaml, .yml and .json OpenAPI files are supported.")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise OpenAPIImportError("The OpenAPI document must use UTF-8 encoding.") from exc

    try:
        if suffix == ".json":
            raw_document = json.loads(text)
        else:
            yaml = YAML(typ="safe")
            raw_document = yaml.load(text)
    except Exception as exc:
        raise OpenAPIImportError(f"The OpenAPI document could not be parsed: {exc}") from exc

    if not isinstance(raw_document, dict):
        raise OpenAPIImportError("The OpenAPI document root must be an object.")

    document = cast(dict[str, Any], raw_document)
    version = document.get("openapi")

    if not isinstance(version, str):
        raise OpenAPIImportError("The document does not contain an OpenAPI version.")

    if not version.startswith(("3.0.", "3.1.", "3.2.")):
        raise OpenAPIImportError(f"OpenAPI version {version!r} is not currently supported.")

    try:
        validate(document)
    except Exception as exc:
        message = str(exc).strip() or exc.__class__.__name__

        raise OpenAPIImportError(f"OpenAPI validation failed: {message[:1000]}") from exc

    info = document.get("info")
    title = "Untitled API"

    if isinstance(info, dict):
        discovered_title = info.get("title")

        if isinstance(discovered_title, str) and discovered_title.strip():
            title = discovered_title.strip()

    operation_count = count_operations(document)

    return (
        document,
        OpenAPIMetadata(
            version=version,
            title=title,
            operation_count=operation_count,
        ),
    )


def count_operations(document: dict[str, Any]) -> int:
    """Count executable operations in an OpenAPI document."""

    paths = document.get("paths")

    if not isinstance(paths, dict):
        return 0

    operation_count = 0

    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue

        for method, operation in path_item.items():
            if (
                isinstance(method, str)
                and method.lower() in HTTP_METHODS
                and isinstance(operation, dict)
            ):
                operation_count += 1

    return operation_count
