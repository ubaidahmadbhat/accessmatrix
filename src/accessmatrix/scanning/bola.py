"""Automatic broken object-level authorization scan execution."""

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from accessmatrix.authorization.models import AuthorizationDataset
from accessmatrix.execution.executor import ExecutionResult, RequestExecutionError
from accessmatrix.execution.protocols import RequestExecutor
from accessmatrix.execution.safety import TargetSafetyError
from accessmatrix.openapi.operations import OpenAPIOperation
from accessmatrix.persistence.models import IdentityProfile, Project
from accessmatrix.scanning.models import (
    BOLACaseResult,
    BOLAFinding,
    BOLAScan,
    FindingConfidence,
    FindingSeverity,
    ResponseEvidence,
    ScanStatus,
)
from accessmatrix.security.credentials import CredentialResolutionError

DEFAULT_EVIDENCE_EXCERPT_CHARACTERS = 16 * 1024

DEFAULT_EXPECTED_DENIAL_STATUS_CODES = (
    401,
    403,
    404,
)

PATH_PARAMETER_PATTERN = re.compile(r"\{([^{}]+)\}")

EXECUTION_FAILURES = (
    RequestExecutionError,
    TargetSafetyError,
    CredentialResolutionError,
)


def read_attribute(
    value: object,
    *names: str,
    default: Any = None,
) -> Any:
    """Read the first available object or mapping attribute."""

    if isinstance(value, Mapping):
        mapping_value = cast(Mapping[str, Any], value)

        for name in names:
            if name in mapping_value:
                return mapping_value[name]

        return default

    for name in names:
        if hasattr(value, name):
            return getattr(value, name)

    return default


def optional_string(
    value: Any,
) -> str | None:
    """Convert a value to a non-empty string when available."""

    if value is None:
        return None

    normalized = str(value).strip()

    return normalized if normalized else None


def required_string(
    value: Any,
    *,
    fallback: str,
) -> str:
    """Return a non-empty string or a fallback value."""

    return optional_string(value) or fallback


def string_list(
    value: Any,
) -> list[str]:
    """Normalize an arbitrary value to a list of strings."""

    if value is None:
        return []

    if isinstance(value, str):
        normalized = value.strip()

        return [normalized] if normalized else []

    if isinstance(value, Sequence):
        return [str(item) for item in value if str(item).strip()]

    return [str(value)]


def integer_list(
    value: Any,
) -> list[int]:
    """Normalize status-code values."""

    if value is None:
        return list(DEFAULT_EXPECTED_DENIAL_STATUS_CODES)

    raw_values: list[Any]

    if isinstance(value, Sequence) and not isinstance(
        value,
        (
            str,
            bytes,
            bytearray,
        ),
    ):
        raw_values = list(value)

    else:
        raw_values = [value]

    normalized: list[int] = []

    for raw_value in raw_values:
        try:
            status_code = int(raw_value)

        except (
            TypeError,
            ValueError,
        ):
            continue

        if 100 <= status_code <= 599:
            normalized.append(status_code)

    if not normalized:
        return list(DEFAULT_EXPECTED_DENIAL_STATUS_CODES)

    return list(dict.fromkeys(normalized))


def object_collection(
    dataset: AuthorizationDataset,
) -> list[Any]:
    """Return authorization object records."""

    value = read_attribute(
        dataset,
        "objects",
        "object_records",
        default=[],
    )

    if isinstance(value, Sequence):
        return list(value)

    return []


def binding_collection(
    dataset: AuthorizationDataset,
) -> list[Any]:
    """Return operation/object bindings."""

    value = read_attribute(
        dataset,
        "bindings",
        "operation_bindings",
        default=[],
    )

    if isinstance(value, Sequence):
        return list(value)

    return []


def plan_case_collection(
    plan: object,
) -> list[Any]:
    """Return generated BOLA plan cases."""

    value = read_attribute(
        plan,
        "cases",
        "items",
        default=[],
    )

    if isinstance(value, Sequence):
        return list(value)

    return []


def object_identifier(
    object_record: object,
) -> str | None:
    """Return an authorization object identifier."""

    return optional_string(
        read_attribute(
            object_record,
            "object_id",
            "id",
        )
    )


def object_resource_type(
    object_record: object,
) -> str | None:
    """Return an authorization object resource type."""

    return optional_string(
        read_attribute(
            object_record,
            "resource_type",
            "type",
        )
    )


def object_owner_identity_id(
    object_record: object,
) -> str | None:
    """Return the identity that owns an object."""

    return optional_string(
        read_attribute(
            object_record,
            "owner_identity_id",
            "owner_id",
        )
    )


def object_tenant(
    object_record: object,
) -> str | None:
    """Return an object's tenant value."""

    return optional_string(
        read_attribute(
            object_record,
            "tenant",
            "tenant_id",
        )
    )


def find_object_record(
    dataset: AuthorizationDataset,
    *,
    object_id: str,
    resource_type: str | None,
) -> Any | None:
    """Find one authorization object record."""

    for object_record in object_collection(dataset):
        if object_identifier(object_record) != object_id:
            continue

        record_resource_type = object_resource_type(object_record)

        if resource_type and record_resource_type and record_resource_type != resource_type:
            continue

        return object_record

    return None


def find_binding(
    dataset: AuthorizationDataset,
    *,
    operation_key: str,
    resource_type: str | None,
) -> Any | None:
    """Find an operation-to-object binding."""

    fallback_binding: Any | None = None

    for binding in binding_collection(dataset):
        binding_operation_key = optional_string(
            read_attribute(
                binding,
                "operation_key",
            )
        )

        if binding_operation_key != operation_key:
            continue

        binding_resource_type = optional_string(
            read_attribute(
                binding,
                "resource_type",
            )
        )

        if resource_type and binding_resource_type == resource_type:
            return binding

        if fallback_binding is None:
            fallback_binding = binding

    return fallback_binding


def find_identity(
    identities: Sequence[IdentityProfile],
    identity_id: str,
) -> IdentityProfile | None:
    """Find one identity by identifier."""

    for identity in identities:
        if identity.id == identity_id:
            return identity

    return None


def find_operation(
    operations: Sequence[OpenAPIOperation],
    operation_key: str,
) -> OpenAPIOperation | None:
    """Find one imported operation."""

    for operation in operations:
        if operation.key == operation_key:
            return operation

    return None


def binding_path_parameter_name(
    binding: object | None,
    operation: OpenAPIOperation,
) -> str | None:
    """Determine the operation path parameter holding the object ID."""

    if binding is not None:
        configured_name = optional_string(
            read_attribute(
                binding,
                "path_parameter_name",
                "path_parameter",
                "object_id_parameter",
                "object_id_parameter_name",
            )
        )

        if configured_name:
            return configured_name

    path_matches = PATH_PARAMETER_PATTERN.findall(operation.path)

    if path_matches:
        return path_matches[0]

    for parameter in operation.parameters:
        parameter_location = optional_string(
            read_attribute(
                parameter,
                "location",
                "in_",
            )
        )

        if parameter_location == "path":
            return optional_string(
                read_attribute(
                    parameter,
                    "name",
                )
            )

    return None


def normalized_parameter_mapping(
    value: Any,
) -> dict[str, str]:
    """Normalize a parameter mapping to strings."""

    if not isinstance(value, Mapping):
        return {}

    return {str(key): str(item) for key, item in value.items() if item is not None}


def case_path_parameters(
    case: object,
    *,
    prefix: str,
    object_id: str,
    binding: object | None,
    operation: OpenAPIOperation,
) -> dict[str, str]:
    """Build path parameters for a baseline or probe request."""

    configured_parameters = normalized_parameter_mapping(
        read_attribute(
            case,
            ("baseline_path_parameters" if prefix == "baseline" else "probe_path_parameters"),
            default={},
        )
    )

    if configured_parameters:
        return configured_parameters

    generic_parameters = normalized_parameter_mapping(
        read_attribute(
            case,
            "path_parameters",
            default={},
        )
    )

    parameter_name = binding_path_parameter_name(
        binding,
        operation,
    )

    if parameter_name:
        generic_parameters[parameter_name] = object_id

    return generic_parameters


def execute_plan_request(
    executor: RequestExecutor,
    *,
    project: Project,
    identity: IdentityProfile,
    operation: OpenAPIOperation,
    path_parameters: dict[str, str],
) -> ExecutionResult:
    """Execute one read-only scan request."""

    return executor.execute(
        project=project,
        identity=identity,
        operation=operation,
        path_parameters=path_parameters,
        query_parameters={},
        headers={},
        json_body=None,
        timeout_seconds=10.0,
        allow_unsafe=False,
        confirmation=None,
    )


def response_evidence(
    result: ExecutionResult,
) -> ResponseEvidence:
    """Create redacted scan evidence from an execution result."""

    body_excerpt: str | None = None
    body_sha256: str | None = None

    if result.body_text is not None:
        body_excerpt = result.body_text[:DEFAULT_EVIDENCE_EXCERPT_CHARACTERS]

        body_sha256 = hashlib.sha256(result.body_text.encode("utf-8")).hexdigest()

    return ResponseEvidence(
        request_url=result.request_url,
        status_code=result.status_code,
        reason_phrase=result.reason_phrase,
        elapsed_ms=result.elapsed_ms,
        response_headers=dict(result.response_headers),
        body_excerpt=body_excerpt,
        body_sha256=body_sha256,
        body_bytes_captured=result.body_bytes_captured,
        body_truncated=(
            result.body_truncated
            or (
                result.body_text is not None
                and len(result.body_text) > DEFAULT_EVIDENCE_EXCERPT_CHARACTERS
            )
        ),
        declared_content_length=result.declared_content_length,
        redirect_blocked=result.redirect_blocked,
    )


def response_json_object(
    result: ExecutionResult,
) -> Mapping[str, Any] | None:
    """Parse a JSON object from a textual response."""

    if result.body_text is None:
        return None

    try:
        parsed = json.loads(result.body_text)

    except (
        json.JSONDecodeError,
        TypeError,
    ):
        return None

    if isinstance(parsed, Mapping):
        return cast(Mapping[str, Any], parsed)

    return None


def nested_response_value(
    response_data: Mapping[str, Any],
    field_name: str,
) -> Any:
    """Read a dot-separated response field."""

    current: Any = response_data

    for segment in field_name.split("."):
        if not isinstance(current, Mapping):
            return None

        current_mapping = cast(Mapping[str, Any], current)

        if segment not in current_mapping:
            return None

        current = current_mapping[segment]

    return current


def configured_response_fields(
    binding: object | None,
) -> list[tuple[str, str]]:
    """Return configured response fields and their semantic role."""

    if binding is None:
        return []

    configured_fields: list[tuple[str, str]] = []

    field_definitions = (
        (
            (
                "response_id_field",
                "response_object_id_field",
            ),
            "id",
        ),
        (
            (
                "response_owner_field",
                "response_owner_id_field",
            ),
            "owner",
        ),
        (
            (
                "response_tenant_field",
                "response_tenant_id_field",
            ),
            "tenant",
        ),
    )

    for field_names, semantic_role in field_definitions:
        configured_name = optional_string(
            read_attribute(
                binding,
                *field_names,
            )
        )

        if configured_name:
            configured_fields.append(
                (
                    configured_name,
                    semantic_role,
                )
            )

    return configured_fields


def compare_probe_response(
    *,
    result: ExecutionResult,
    binding: object | None,
    probe_object: object | None,
    probe_object_id: str,
) -> dict[str, bool]:
    """Compare configured object fields with the cross-owner probe."""

    response_data = response_json_object(result)

    if response_data is None:
        return {}

    expected_values = {
        "id": probe_object_id,
        "owner": (object_owner_identity_id(probe_object) if probe_object is not None else None),
        "tenant": (object_tenant(probe_object) if probe_object is not None else None),
    }

    comparisons: dict[str, bool] = {}

    for field_name, semantic_role in configured_response_fields(binding):
        expected_value = expected_values[semantic_role]

        actual_value = nested_response_value(
            response_data,
            field_name,
        )

        comparisons[field_name] = (
            expected_value is not None
            and actual_value is not None
            and str(actual_value) == str(expected_value)
        )

    return comparisons


def finding_confidence(
    comparisons: Mapping[str, bool],
) -> FindingConfidence:
    """Calculate confidence for a successful cross-owner authorization bypass."""

    # This function is called only after the selected identity successfully
    # accesses its owned baseline object and then receives a 2xx response for
    # an object known to belong to another identity. Those conditions are
    # sufficient for a high-confidence BOLA finding. Response-field matches
    # remain supporting evidence and must not downgrade that confirmed bypass.
    _ = comparisons

    return "high"


def finding_severity(
    *,
    identity: IdentityProfile,
    probe_object: object | None,
) -> FindingSeverity:
    """Calculate BOLA finding severity."""

    identity_tenant = optional_string(identity.tenant)

    probe_tenant = object_tenant(probe_object) if probe_object is not None else None

    if identity_tenant and probe_tenant and identity_tenant != probe_tenant:
        return "high"

    return "medium"


def blocked_case_result(
    *,
    case_id: str,
    case_name: str,
    operation_key: str,
    identity_id: str,
    identity_name: str,
    resource_type: str,
    baseline_object_id: str | None,
    probe_object_id: str,
    expected_status_codes: list[int],
    explanation: str,
    issues: list[str],
    baseline_evidence: ResponseEvidence | None = None,
) -> BOLACaseResult:
    """Create a blocked BOLA case result."""

    return BOLACaseResult(
        case_id=case_id,
        case_name=case_name,
        operation_key=operation_key,
        identity_id=identity_id,
        identity_name=identity_name,
        resource_type=resource_type,
        baseline_object_id=baseline_object_id,
        probe_object_id=probe_object_id,
        expected_probe_status_codes=expected_status_codes,
        outcome="blocked",
        explanation=explanation,
        matching_response_fields={},
        issues=issues,
        baseline_evidence=baseline_evidence,
        probe_evidence=None,
    )


class BOLAScanRunner:
    """Execute generated BOLA plans using the controlled executor."""

    def __init__(
        self,
        executor: RequestExecutor,
    ) -> None:
        """Initialize the scan runner."""

        self._executor = executor

    def _execute_case(
        self,
        *,
        project: Project,
        case: object,
        dataset: AuthorizationDataset,
        operations: Sequence[OpenAPIOperation],
        identities: Sequence[IdentityProfile],
    ) -> tuple[BOLACaseResult, BOLAFinding | None]:
        """Execute one baseline and cross-owner probe case."""

        case_id = required_string(
            read_attribute(
                case,
                "case_id",
                "id",
            ),
            fallback=str(uuid4()),
        )

        case_name = required_string(
            read_attribute(
                case,
                "case_name",
                "name",
                "title",
            ),
            fallback="BOLA authorization case",
        )

        operation_key = required_string(
            read_attribute(
                case,
                "operation_key",
            ),
            fallback="unknown operation",
        )

        identity_id = required_string(
            read_attribute(
                case,
                "identity_id",
            ),
            fallback="unknown identity",
        )

        resource_type = required_string(
            read_attribute(
                case,
                "resource_type",
            ),
            fallback="object",
        )

        baseline_object_id = optional_string(
            read_attribute(
                case,
                "baseline_object_id",
                "owned_object_id",
                "source_object_id",
            )
        )

        probe_object_id = required_string(
            read_attribute(
                case,
                "probe_object_id",
                "foreign_object_id",
                "target_object_id",
            ),
            fallback="unknown object",
        )

        expected_status_codes = integer_list(
            read_attribute(
                case,
                "expected_probe_status_codes",
                "expected_denial_status_codes",
                "expected_status_codes",
            )
        )

        case_issues = string_list(
            read_attribute(
                case,
                "issues",
                "readiness_issues",
                default=[],
            )
        )

        ready_value = read_attribute(
            case,
            "ready",
            "is_ready",
            default=True,
        )

        identity = find_identity(
            identities,
            identity_id,
        )

        operation = find_operation(
            operations,
            operation_key,
        )

        identity_name = (
            identity.name
            if identity is not None
            else required_string(
                read_attribute(
                    case,
                    "identity_name",
                ),
                fallback=identity_id,
            )
        )

        if ready_value is False and not case_issues:
            case_issues.append("The generated BOLA case is not ready.")

        if identity is None:
            case_issues.append("The case identity does not exist.")

        if operation is None:
            case_issues.append("The case operation does not exist.")

        if baseline_object_id is None:
            case_issues.append("The case has no owned baseline object.")

        if not probe_object_id or probe_object_id == "unknown object":
            case_issues.append("The case has no cross-owner probe object.")

        if case_issues:
            return (
                blocked_case_result(
                    case_id=case_id,
                    case_name=case_name,
                    operation_key=operation_key,
                    identity_id=identity_id,
                    identity_name=identity_name,
                    resource_type=resource_type,
                    baseline_object_id=baseline_object_id,
                    probe_object_id=probe_object_id,
                    expected_status_codes=expected_status_codes,
                    explanation=(
                        "The BOLA case could not be executed because its context is incomplete."
                    ),
                    issues=case_issues,
                ),
                None,
            )

        assert identity is not None
        assert operation is not None
        assert baseline_object_id is not None

        binding = find_binding(
            dataset,
            operation_key=operation_key,
            resource_type=resource_type,
        )

        baseline_object = find_object_record(
            dataset,
            object_id=baseline_object_id,
            resource_type=resource_type,
        )

        probe_object = find_object_record(
            dataset,
            object_id=probe_object_id,
            resource_type=resource_type,
        )

        if baseline_object is None:
            return (
                blocked_case_result(
                    case_id=case_id,
                    case_name=case_name,
                    operation_key=operation_key,
                    identity_id=identity_id,
                    identity_name=identity_name,
                    resource_type=resource_type,
                    baseline_object_id=baseline_object_id,
                    probe_object_id=probe_object_id,
                    expected_status_codes=expected_status_codes,
                    explanation=(
                        "The owned baseline object does not exist in the authorization dataset."
                    ),
                    issues=[(f"Baseline object {baseline_object_id} was not found.")],
                ),
                None,
            )

        if probe_object is None:
            return (
                blocked_case_result(
                    case_id=case_id,
                    case_name=case_name,
                    operation_key=operation_key,
                    identity_id=identity_id,
                    identity_name=identity_name,
                    resource_type=resource_type,
                    baseline_object_id=baseline_object_id,
                    probe_object_id=probe_object_id,
                    expected_status_codes=expected_status_codes,
                    explanation=(
                        "The cross-owner probe object does not exist in the authorization dataset."
                    ),
                    issues=[(f"Probe object {probe_object_id} was not found.")],
                ),
                None,
            )

        baseline_path_parameters = case_path_parameters(
            case,
            prefix="baseline",
            object_id=baseline_object_id,
            binding=binding,
            operation=operation,
        )

        probe_path_parameters = case_path_parameters(
            case,
            prefix="probe",
            object_id=probe_object_id,
            binding=binding,
            operation=operation,
        )

        if not baseline_path_parameters and PATH_PARAMETER_PATTERN.search(operation.path):
            return (
                blocked_case_result(
                    case_id=case_id,
                    case_name=case_name,
                    operation_key=operation_key,
                    identity_id=identity_id,
                    identity_name=identity_name,
                    resource_type=resource_type,
                    baseline_object_id=baseline_object_id,
                    probe_object_id=probe_object_id,
                    expected_status_codes=expected_status_codes,
                    explanation=(
                        "The object identifier could not be mapped to the operation path."
                    ),
                    issues=["No object-ID path parameter could be determined."],
                ),
                None,
            )

        try:
            baseline_result = execute_plan_request(
                self._executor,
                project=project,
                identity=identity,
                operation=operation,
                path_parameters=baseline_path_parameters,
            )

        except EXECUTION_FAILURES as exc:
            return (
                blocked_case_result(
                    case_id=case_id,
                    case_name=case_name,
                    operation_key=operation_key,
                    identity_id=identity_id,
                    identity_name=identity_name,
                    resource_type=resource_type,
                    baseline_object_id=baseline_object_id,
                    probe_object_id=probe_object_id,
                    expected_status_codes=expected_status_codes,
                    explanation=("The owned-object baseline request could not be executed."),
                    issues=[str(exc)],
                ),
                None,
            )

        baseline_evidence = response_evidence(baseline_result)

        if not 200 <= baseline_result.status_code < 300:
            return (
                blocked_case_result(
                    case_id=case_id,
                    case_name=case_name,
                    operation_key=operation_key,
                    identity_id=identity_id,
                    identity_name=identity_name,
                    resource_type=resource_type,
                    baseline_object_id=baseline_object_id,
                    probe_object_id=probe_object_id,
                    expected_status_codes=expected_status_codes,
                    explanation=(
                        "The identity could not successfully access its owned baseline object."
                    ),
                    issues=[(f"The baseline returned HTTP {baseline_result.status_code}.")],
                    baseline_evidence=baseline_evidence,
                ),
                None,
            )

        try:
            probe_result = execute_plan_request(
                self._executor,
                project=project,
                identity=identity,
                operation=operation,
                path_parameters=probe_path_parameters,
            )

        except EXECUTION_FAILURES as exc:
            return (
                blocked_case_result(
                    case_id=case_id,
                    case_name=case_name,
                    operation_key=operation_key,
                    identity_id=identity_id,
                    identity_name=identity_name,
                    resource_type=resource_type,
                    baseline_object_id=baseline_object_id,
                    probe_object_id=probe_object_id,
                    expected_status_codes=expected_status_codes,
                    explanation=("The cross-owner probe request could not be executed."),
                    issues=[str(exc)],
                    baseline_evidence=baseline_evidence,
                ),
                None,
            )

        probe_evidence = response_evidence(probe_result)

        matching_fields = compare_probe_response(
            result=probe_result,
            binding=binding,
            probe_object=probe_object,
            probe_object_id=probe_object_id,
        )

        if probe_result.status_code in expected_status_codes:
            case_result = BOLACaseResult(
                case_id=case_id,
                case_name=case_name,
                operation_key=operation_key,
                identity_id=identity_id,
                identity_name=identity_name,
                resource_type=resource_type,
                baseline_object_id=baseline_object_id,
                probe_object_id=probe_object_id,
                expected_probe_status_codes=expected_status_codes,
                outcome="pass",
                explanation=(
                    "The API rejected the cross-owner object request with an "
                    "expected authorization-denial status."
                ),
                matching_response_fields=matching_fields,
                issues=[],
                baseline_evidence=baseline_evidence,
                probe_evidence=probe_evidence,
            )

            return (
                case_result,
                None,
            )

        if 200 <= probe_result.status_code < 300:
            confidence = finding_confidence(matching_fields)

            severity = finding_severity(
                identity=identity,
                probe_object=probe_object,
            )

            finding = BOLAFinding(
                finding_id=str(uuid4()),
                case_id=case_id,
                title="Broken object-level authorization detected",
                description=(
                    f"{identity_name} successfully accessed cross-owner "
                    f"{resource_type} object {probe_object_id} using "
                    f"{operation_key}."
                ),
                severity=severity,
                confidence=confidence,
                operation_key=operation_key,
                identity_id=identity_id,
                identity_name=identity_name,
                resource_type=resource_type,
                baseline_object_id=baseline_object_id,
                probe_object_id=probe_object_id,
                observed_status_code=probe_result.status_code,
                matching_response_fields=matching_fields,
            )

            case_result = BOLACaseResult(
                case_id=case_id,
                case_name=case_name,
                operation_key=operation_key,
                identity_id=identity_id,
                identity_name=identity_name,
                resource_type=resource_type,
                baseline_object_id=baseline_object_id,
                probe_object_id=probe_object_id,
                expected_probe_status_codes=expected_status_codes,
                outcome="finding",
                explanation=(
                    "The API returned a successful response for a cross-owner object request."
                ),
                matching_response_fields=matching_fields,
                issues=[],
                baseline_evidence=baseline_evidence,
                probe_evidence=probe_evidence,
            )

            return (
                case_result,
                finding,
            )

        case_result = BOLACaseResult(
            case_id=case_id,
            case_name=case_name,
            operation_key=operation_key,
            identity_id=identity_id,
            identity_name=identity_name,
            resource_type=resource_type,
            baseline_object_id=baseline_object_id,
            probe_object_id=probe_object_id,
            expected_probe_status_codes=expected_status_codes,
            outcome="inconclusive",
            explanation=(
                "The cross-owner request returned an unexpected non-success "
                "status that was not configured as an expected authorization "
                "denial."
            ),
            matching_response_fields=matching_fields,
            issues=[(f"Unexpected probe response: HTTP {probe_result.status_code}.")],
            baseline_evidence=baseline_evidence,
            probe_evidence=probe_evidence,
        )

        return (
            case_result,
            None,
        )

    def run(
        self,
        *,
        project: Project,
        plan: object,
        dataset: AuthorizationDataset,
        operations: Sequence[OpenAPIOperation],
        identities: Sequence[IdentityProfile],
        max_cases: int = 100,
    ) -> BOLAScan:
        """Execute and summarize a generated BOLA plan."""

        if not 1 <= max_cases <= 100:
            raise ValueError("The scan case limit must be between 1 and 100.")

        started_at = datetime.now(UTC)

        results: list[BOLACaseResult] = []
        findings: list[BOLAFinding] = []

        selected_cases = plan_case_collection(plan)[:max_cases]

        for case in selected_cases:
            case_result, finding = self._execute_case(
                project=project,
                case=case,
                dataset=dataset,
                operations=operations,
                identities=identities,
            )

            results.append(case_result)

            if finding is not None:
                findings.append(finding)

        completed_at = datetime.now(UTC)

        pass_count = sum(result.outcome == "pass" for result in results)

        finding_count = sum(result.outcome == "finding" for result in results)

        inconclusive_count = sum(result.outcome == "inconclusive" for result in results)

        blocked_count = sum(result.outcome == "blocked" for result in results)

        scan_status: ScanStatus

        if not results:
            scan_status = "failed"

        elif inconclusive_count or blocked_count:
            scan_status = "partial"

        else:
            scan_status = "completed"

        return BOLAScan(
            scan_id=str(uuid4()),
            project_id=project.id,
            started_at=started_at,
            completed_at=completed_at,
            status=scan_status,
            total_count=len(results),
            pass_count=pass_count,
            finding_count=finding_count,
            inconclusive_count=inconclusive_count,
            blocked_count=blocked_count,
            results=results,
            findings=findings,
        )
