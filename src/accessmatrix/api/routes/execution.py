"""Controlled API request-execution routes."""

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from accessmatrix.api.routes.projects import (
    load_project_openapi_document,
    project_or_404,
)
from accessmatrix.execution.executor import ExecutionResult, RequestExecutionError
from accessmatrix.execution.protocols import RequestExecutor
from accessmatrix.execution.runtime import build_runtime_request_executor
from accessmatrix.execution.safety import TargetSafetyError
from accessmatrix.openapi.operations import OpenAPIOperation, discover_operations
from accessmatrix.persistence.database import get_session
from accessmatrix.persistence.models import IdentityProfile
from accessmatrix.persistence.storage import get_storage_root
from accessmatrix.security.credentials import CredentialResolutionError

router = APIRouter(
    prefix="/api/v1/projects/{project_id}",
    tags=["Execution"],
)

SessionDependency = Annotated[Session, Depends(get_session)]
StorageDependency = Annotated[Path, Depends(get_storage_root)]


class ExecuteOperationRequest(BaseModel):
    """Input used to execute one imported OpenAPI operation."""

    operation_key: str | None = Field(
        default=None,
        max_length=1000,
    )
    identity_id: str = Field(
        min_length=1,
        max_length=128,
    )
    path_parameters: dict[str, str] = Field(default_factory=dict)
    query_parameters: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    json_body: Any = None
    timeout_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=30.0,
    )
    allow_unsafe: bool = False
    confirmation: str | None = Field(
        default=None,
        max_length=500,
    )


class ExecutionResultRead(BaseModel):
    """Serializable controlled-execution result."""

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


def get_request_executor(
    storage_root: StorageDependency,
) -> RequestExecutor:
    """Return the effective settings-aware request executor."""

    return build_runtime_request_executor(storage_root)


RequestExecutorDependency = Annotated[
    RequestExecutor,
    Depends(get_request_executor),
]


def identity_or_404(
    session: Session,
    *,
    project_id: str,
    identity_id: str,
) -> IdentityProfile:
    """Return a project identity or raise HTTP 404."""

    identity = session.get(
        IdentityProfile,
        identity_id,
    )

    if identity is None or identity.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested identity does not exist.",
        )

    if not identity.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected identity is disabled.",
        )

    return identity


def operation_or_404(
    operations: list[OpenAPIOperation],
    operation_key: str,
) -> OpenAPIOperation:
    """Return an imported operation or raise HTTP 404."""

    for operation in operations:
        if operation.key == operation_key:
            return operation

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="The requested OpenAPI operation does not exist.",
    )


def execution_result_read(
    result: ExecutionResult,
) -> ExecutionResultRead:
    """Convert an internal execution result to an API response."""

    return ExecutionResultRead(
        operation_key=result.operation_key,
        identity_id=result.identity_id,
        identity_name=result.identity_name,
        method=result.method,
        request_url=result.request_url,
        request_header_names=result.request_header_names,
        status_code=result.status_code,
        reason_phrase=result.reason_phrase,
        elapsed_ms=result.elapsed_ms,
        response_headers=result.response_headers,
        body_text=result.body_text,
        body_bytes_captured=result.body_bytes_captured,
        body_truncated=result.body_truncated,
        declared_content_length=result.declared_content_length,
        redirect_blocked=result.redirect_blocked,
        rate_limit_remaining=result.rate_limit_remaining,
    )


def request_execution_error_status(
    exc: RequestExecutionError,
) -> int:
    """Select an HTTP status for a controlled-execution failure."""

    normalized_message = str(exc).lower()

    policy_phrases = (
        "confirmation",
        "unsafe",
        "not allowed",
        "not permitted",
        "blocked",
        "trace",
        "state-changing",
        "size limit",
        "parallel-request",
        "rate limit",
        "too many requests",
    )

    if any(phrase in normalized_message for phrase in policy_phrases):
        return status.HTTP_409_CONFLICT

    return status.HTTP_502_BAD_GATEWAY


def execute_operation_internal(
    *,
    project_id: str,
    operation_key: str,
    payload: ExecuteOperationRequest,
    session: Session,
    storage_root: Path,
    executor: RequestExecutor,
) -> ExecutionResultRead:
    """Resolve context and execute one operation."""

    project = project_or_404(
        session,
        project_id,
    )

    document, _ = load_project_openapi_document(
        project,
        storage_root,
    )

    operations = discover_operations(document)

    operation = operation_or_404(
        operations,
        operation_key,
    )

    identity = identity_or_404(
        session,
        project_id=project_id,
        identity_id=payload.identity_id,
    )

    try:
        result = executor.execute(
            project=project,
            identity=identity,
            operation=operation,
            path_parameters=payload.path_parameters,
            query_parameters=payload.query_parameters,
            headers=payload.headers,
            json_body=payload.json_body,
            timeout_seconds=payload.timeout_seconds,
            allow_unsafe=payload.allow_unsafe,
            confirmation=payload.confirmation,
        )

    except (
        TargetSafetyError,
        CredentialResolutionError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except RequestExecutionError as exc:
        raise HTTPException(
            status_code=request_execution_error_status(exc),
            detail=str(exc),
        ) from exc

    return execution_result_read(result)


@router.post(
    "/execute",
    response_model=ExecutionResultRead,
)
def execute_project_operation(
    project_id: str,
    payload: ExecuteOperationRequest,
    session: SessionDependency,
    storage_root: StorageDependency,
    executor: RequestExecutorDependency,
) -> ExecutionResultRead:
    """Execute an imported project operation."""

    operation_key = payload.operation_key.strip() if payload.operation_key else ""

    if not operation_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An operation key is required.",
        )

    return execute_operation_internal(
        project_id=project_id,
        operation_key=operation_key,
        payload=payload,
        session=session,
        storage_root=storage_root,
        executor=executor,
    )


@router.post(
    "/operations/execute",
    response_model=ExecutionResultRead,
    include_in_schema=False,
)
def execute_project_operation_alias(
    project_id: str,
    payload: ExecuteOperationRequest,
    session: SessionDependency,
    storage_root: StorageDependency,
    executor: RequestExecutorDependency,
) -> ExecutionResultRead:
    """Support the operation-oriented execution URL."""

    operation_key = payload.operation_key.strip() if payload.operation_key else ""

    if not operation_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An operation key is required.",
        )

    return execute_operation_internal(
        project_id=project_id,
        operation_key=operation_key,
        payload=payload,
        session=session,
        storage_root=storage_root,
        executor=executor,
    )


@router.post(
    "/operations/{operation_key:path}/execute",
    response_model=ExecutionResultRead,
    include_in_schema=False,
)
def execute_project_operation_by_path(
    project_id: str,
    operation_key: str,
    payload: ExecuteOperationRequest,
    session: SessionDependency,
    storage_root: StorageDependency,
    executor: RequestExecutorDependency,
) -> ExecutionResultRead:
    """Support clients that place the operation key in the URL."""

    normalized_operation_key = operation_key.strip()

    if not normalized_operation_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An operation key is required.",
        )

    return execute_operation_internal(
        project_id=project_id,
        operation_key=normalized_operation_key,
        payload=payload,
        session=session,
        storage_root=storage_root,
        executor=executor,
    )
