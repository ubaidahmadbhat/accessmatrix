"""Settings-aware controlled request execution."""

import json
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path
from threading import (
    BoundedSemaphore,
)
from typing import Any
from uuid import uuid4

from accessmatrix.audit.models import (
    AuditDetailValue,
    AuditEvent,
    AuditOutcome,
)
from accessmatrix.audit.storage import (
    AuditEventRepository,
    AuditStorageError,
)
from accessmatrix.execution.executor import (
    ExecutionResult,
    RequestExecutionError,
)
from accessmatrix.execution.protocols import (
    RequestExecutor,
)
from accessmatrix.execution.safety import (
    TargetSafetyError,
)
from accessmatrix.openapi.operations import (
    OpenAPIOperation,
)
from accessmatrix.persistence.models import (
    IdentityProfile,
    Project,
)
from accessmatrix.security.target_validation import (
    TargetValidationResult,
    validate_target_url,
)
from accessmatrix.settings.models import (
    ApplicationSettings,
)


def validation_message(
    result: TargetValidationResult,
) -> str:
    """Build a normalized target-policy error message."""

    messages = [
        *result.issues,
        *result.policy_violations,
    ]

    if not messages:
        return "The target was rejected by the application network policy."

    return " ".join(messages)


def resolved_address_set(
    result: TargetValidationResult,
) -> set[str]:
    """Return the resolved addresses in a validation result."""

    return {address.address for address in result.addresses}


def serialized_json_size(
    json_body: Any,
) -> int:
    """Return the serialized UTF-8 request-body size."""

    if json_body is None:
        return 0

    try:
        serialized = json.dumps(
            json_body,
            ensure_ascii=False,
            separators=(
                ",",
                ":",
            ),
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise RequestExecutionError("The request JSON body could not be serialized.") from exc

    return len(serialized.encode("utf-8"))


def limit_body_text(
    body_text: str | None,
    *,
    max_bytes: int,
    max_characters: int,
) -> tuple[
    str | None,
    bool,
]:
    """Apply configured byte and character retention limits."""

    if body_text is None:
        return (
            None,
            False,
        )

    if max_bytes < 1 or max_characters < 1:
        return (
            None,
            bool(body_text),
        )

    encoded_body = body_text.encode("utf-8")

    byte_truncated = len(encoded_body) > max_bytes

    retained_body = encoded_body[:max_bytes].decode(
        "utf-8",
        errors="replace",
    )

    character_truncated = len(retained_body) > max_characters

    retained_body = retained_body[:max_characters]

    return (
        retained_body,
        (byte_truncated or character_truncated),
    )


class SettingsAwareRequestExecutor:
    """Enforce persistent settings around a controlled executor."""

    def __init__(
        self,
        *,
        inner: RequestExecutor,
        settings: ApplicationSettings,
        storage_root: Path,
    ) -> None:
        """Initialize the settings-aware executor."""

        self._inner = inner
        self._settings = settings
        self._storage_root = storage_root

        self._semaphore = BoundedSemaphore(value=(settings.execution.max_parallel_requests))

    def _record_audit(
        self,
        *,
        outcome: AuditOutcome,
        message: str,
        project_id: str,
        resource_id: str,
        details: dict[
            str,
            AuditDetailValue,
        ],
    ) -> None:
        """Best-effort persistence of one execution audit event."""

        if not self._settings.audit.enabled:
            return

        repository = AuditEventRepository(self._storage_root)

        try:
            repository.save(
                AuditEvent(
                    event_id=str(uuid4()),
                    occurred_at=datetime.now(UTC),
                    event_type=("execution.request"),
                    outcome=outcome,
                    message=message,
                    project_id=project_id,
                    resource_id=resource_id,
                    details=details,
                )
            )

            repository.prune(
                retention_days=(self._settings.audit.retention_days),
                max_events=(self._settings.audit.max_events),
            )

        except (
            AuditStorageError,
            ValueError,
        ):
            # Audit storage must never expose secrets
            # or replace the original execution result.
            return

    def _validate_target(
        self,
        project: Project,
        operation: OpenAPIOperation,
        identity: IdentityProfile,
    ) -> TargetValidationResult:
        """Validate target policy and DNS stability."""

        if not project.base_url:
            self._record_audit(
                outcome="denied",
                message=("Request denied because the project has no target base URL."),
                project_id=project.id,
                resource_id=(operation.key),
                details={
                    "identity_id": (identity.id),
                    "operation_key": (operation.key),
                    "network_access_mode": (self._settings.network.access_mode),
                },
            )

            raise TargetSafetyError("The project has no target base URL.")

        first_validation = validate_target_url(
            project.base_url,
            settings=(self._settings.network),
        )

        if not first_validation.permitted:
            self._record_audit(
                outcome="denied",
                message=("Request denied by the target network policy."),
                project_id=project.id,
                resource_id=(operation.key),
                details={
                    "identity_id": (identity.id),
                    "operation_key": (operation.key),
                    "hostname": (first_validation.hostname),
                    "address_count": len(first_validation.addresses),
                    "network_access_mode": (self._settings.network.access_mode),
                },
            )

            raise TargetSafetyError(validation_message(first_validation))

        if first_validation.resolution_performed:
            second_validation = validate_target_url(
                project.base_url,
                settings=(self._settings.network),
            )

            first_addresses = resolved_address_set(first_validation)

            second_addresses = resolved_address_set(second_validation)

            if not second_validation.permitted or first_addresses != second_addresses:
                self._record_audit(
                    outcome="denied",
                    message=(
                        "Request denied because "
                        "hostname resolution changed "
                        "during preflight validation."
                    ),
                    project_id=(project.id),
                    resource_id=(operation.key),
                    details={
                        "identity_id": (identity.id),
                        "operation_key": (operation.key),
                        "hostname": (first_validation.hostname),
                        "first_address_count": len(first_addresses),
                        "second_address_count": len(second_addresses),
                    },
                )

                raise TargetSafetyError(
                    "The hostname resolved to a different address set during preflight validation."
                )

        return first_validation

    def _shape_result(
        self,
        result: ExecutionResult,
    ) -> ExecutionResult:
        """Apply response evidence and header settings."""

        (
            retained_body,
            retention_truncated,
        ) = limit_body_text(
            result.body_text,
            max_bytes=(self._settings.execution.max_response_bytes),
            max_characters=(self._settings.evidence.body_excerpt_characters),
        )

        response_headers = (
            result.response_headers if (self._settings.evidence.store_response_headers) else {}
        )

        return ExecutionResult(
            operation_key=(result.operation_key),
            identity_id=(result.identity_id),
            identity_name=(result.identity_name),
            method=result.method,
            request_url=(result.request_url),
            request_header_names=(result.request_header_names),
            status_code=(result.status_code),
            reason_phrase=(result.reason_phrase),
            elapsed_ms=(result.elapsed_ms),
            response_headers=(response_headers),
            body_text=retained_body,
            body_bytes_captured=(result.body_bytes_captured),
            body_truncated=(result.body_truncated or retention_truncated),
            declared_content_length=(result.declared_content_length),
            redirect_blocked=(result.redirect_blocked),
            rate_limit_remaining=(result.rate_limit_remaining),
        )

    def execute(
        self,
        *,
        project: Project,
        identity: IdentityProfile,
        operation: OpenAPIOperation,
        path_parameters: dict[
            str,
            str,
        ],
        query_parameters: dict[
            str,
            str,
        ],
        headers: dict[
            str,
            str,
        ],
        json_body: Any,
        timeout_seconds: float,
        allow_unsafe: bool,
        confirmation: str | None,
    ) -> ExecutionResult:
        """Execute one policy-controlled request."""

        validation = self._validate_target(
            project,
            operation,
            identity,
        )

        try:
            request_bytes = serialized_json_size(json_body)

        except RequestExecutionError:
            self._record_audit(
                outcome="failure",
                message=("Request body validation failed."),
                project_id=project.id,
                resource_id=(operation.key),
                details={
                    "identity_id": (identity.id),
                    "operation_key": (operation.key),
                },
            )

            raise

        if request_bytes > self._settings.execution.max_request_bytes:
            self._record_audit(
                outcome="denied",
                message=("Request denied because its body exceeded the configured size limit."),
                project_id=project.id,
                resource_id=(operation.key),
                details={
                    "identity_id": (identity.id),
                    "operation_key": (operation.key),
                    "request_bytes": (request_bytes),
                    "maximum_request_bytes": (self._settings.execution.max_request_bytes),
                },
            )

            raise RequestExecutionError(
                "The request body exceeds the configured application size limit."
            )

        effective_timeout = min(
            max(
                timeout_seconds,
                1.0,
            ),
            (self._settings.execution.default_timeout_seconds),
        )

        acquired = self._semaphore.acquire(timeout=effective_timeout)

        if not acquired:
            self._record_audit(
                outcome="failure",
                message=("Request could not acquire an execution concurrency slot."),
                project_id=project.id,
                resource_id=(operation.key),
                details={
                    "identity_id": (identity.id),
                    "operation_key": (operation.key),
                    "max_parallel_requests": (self._settings.execution.max_parallel_requests),
                },
            )

            raise RequestExecutionError(
                "The configured parallel-request limit is currently exhausted."
            )

        try:
            result = self._inner.execute(
                project=project,
                identity=identity,
                operation=operation,
                path_parameters=(path_parameters),
                query_parameters=(query_parameters),
                headers=headers,
                json_body=json_body,
                timeout_seconds=(effective_timeout),
                allow_unsafe=(allow_unsafe),
                confirmation=(confirmation),
            )

        except Exception as exc:
            self._record_audit(
                outcome="failure",
                message=("Controlled request execution failed."),
                project_id=project.id,
                resource_id=(operation.key),
                details={
                    "identity_id": (identity.id),
                    "operation_key": (operation.key),
                    "method": (operation.method),
                    "hostname": (validation.hostname),
                    "error_type": (type(exc).__name__),
                },
            )

            raise

        finally:
            self._semaphore.release()

        shaped_result = self._shape_result(result)

        self._record_audit(
            outcome="success",
            message=("Controlled request execution completed."),
            project_id=project.id,
            resource_id=(operation.key),
            details={
                "identity_id": (identity.id),
                "operation_key": (operation.key),
                "method": (operation.method),
                "hostname": (validation.hostname),
                "http_status": (shaped_result.status_code),
                "elapsed_ms": (shaped_result.elapsed_ms),
                "request_bytes": (request_bytes),
                "body_bytes_captured": (shaped_result.body_bytes_captured),
                "body_truncated": (shaped_result.body_truncated),
            },
        )

        return shaped_result
