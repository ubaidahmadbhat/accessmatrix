"""OpenAPI operation response schemas."""

from pydantic import BaseModel


class OperationParameterRead(BaseModel):
    """A parameter accepted by an OpenAPI operation."""

    name: str
    location: str
    required: bool
    schema_type: str | None
    description: str | None


class OperationRead(BaseModel):
    """A normalized OpenAPI operation."""

    key: str
    method: str
    path: str
    operation_id: str
    summary: str | None
    description: str | None
    tags: list[str]
    deprecated: bool
    security_required: bool
    parameters: list[OperationParameterRead]
    request_content_types: list[str]
    response_codes: list[str]


class ProjectOperationsRead(BaseModel):
    """OpenAPI operations discovered for a project."""

    project_id: str
    openapi_title: str
    openapi_version: str
    operation_count: int
    operations: list[OperationRead]
