"""Controlled request execution API schemas."""

from typing import Any

from pydantic import (
    BaseModel,
    Field,
)


class ExecuteOperationRequest(BaseModel):
    """Input for one controlled operation execution."""

    operation_key: str = Field(
        min_length=3,
        max_length=4096,
    )

    identity_id: str = Field(
        min_length=1,
        max_length=128,
    )

    path_parameters: dict[
        str,
        str,
    ] = Field(
        default_factory=dict,
        max_length=100,
    )

    query_parameters: dict[
        str,
        str,
    ] = Field(
        default_factory=dict,
        max_length=100,
    )

    headers: dict[
        str,
        str,
    ] = Field(
        default_factory=dict,
        max_length=50,
    )

    json_body: Any | None = None

    timeout_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=30.0,
    )

    allow_unsafe: bool = False

    confirmation: str | None = Field(
        default=None,
        max_length=4096,
    )


class ExecuteOperationResponse(BaseModel):
    """Safe result from one controlled request."""

    operation_key: str
    identity_id: str
    identity_name: str
    method: str
    request_url: str
    request_header_names: list[str]
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
