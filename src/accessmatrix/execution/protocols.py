"""Shared request-executor protocol."""

from typing import (
    Any,
    Protocol,
)

from accessmatrix.execution.executor import (
    ExecutionResult,
)
from accessmatrix.openapi.operations import (
    OpenAPIOperation,
)
from accessmatrix.persistence.models import (
    IdentityProfile,
    Project,
)


class RequestExecutor(Protocol):
    """Interface implemented by controlled request executors."""

    def execute(
        self,
        *,
        project: Project,
        identity: IdentityProfile,
        operation: OpenAPIOperation,
        path_parameters: dict[str, str],
        query_parameters: dict[str, str],
        headers: dict[str, str],
        json_body: Any,
        timeout_seconds: float,
        allow_unsafe: bool,
        confirmation: str | None,
    ) -> ExecutionResult:
        """Execute one controlled API request."""
