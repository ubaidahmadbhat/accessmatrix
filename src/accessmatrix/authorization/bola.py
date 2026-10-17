"""Automatic cross-owner BOLA test-plan generation."""

from collections import defaultdict

from accessmatrix.authorization.models import (
    AuthorizationCase,
    AuthorizationDataset,
    BOLATestPlan,
    BOLATestPlanItem,
    ObjectRecord,
)
from accessmatrix.openapi.operations import (
    OpenAPIOperation,
)
from accessmatrix.persistence.models import (
    IdentityProfile,
)

SUPPORTED_BOLA_METHODS = frozenset(
    {
        "GET",
        "HEAD",
    }
)

DEFAULT_DENIAL_STATUS_CODES = (
    401,
    403,
    404,
)


def build_bola_test_plan(
    *,
    project_id: str,
    dataset: AuthorizationDataset,
    operations: list[OpenAPIOperation],
    identities: list[IdentityProfile],
) -> BOLATestPlan:
    """Generate comparative BOLA cases from deny expectations."""

    operation_map = {operation.key: operation for operation in operations}

    identity_map = {identity.id: identity for identity in identities}

    object_map = {
        (
            object_record.resource_type,
            object_record.object_id,
        ): object_record
        for object_record in dataset.objects
    }

    binding_map = {binding.operation_key: binding for binding in dataset.bindings}

    allow_cases: defaultdict[
        tuple[
            str,
            str,
            str,
        ],
        list[AuthorizationCase],
    ] = defaultdict(list)

    for authorization_case in dataset.cases:
        if authorization_case.enabled and authorization_case.expectation == "allow":
            allow_cases[
                (
                    authorization_case.identity_id,
                    authorization_case.operation_key,
                    authorization_case.resource_type,
                )
            ].append(authorization_case)

    plan_items: list[BOLATestPlanItem] = []

    deny_cases = [
        authorization_case
        for authorization_case in dataset.cases
        if authorization_case.enabled and authorization_case.expectation == "deny"
    ]

    for deny_case in deny_cases:
        issues: list[str] = []

        identity = identity_map.get(deny_case.identity_id)

        operation = operation_map.get(deny_case.operation_key)

        binding = binding_map.get(deny_case.operation_key)

        probe_object = object_map.get(
            (
                deny_case.resource_type,
                deny_case.object_id,
            )
        )

        identity_name = identity.name if identity is not None else deny_case.identity_id

        if identity is None:
            issues.append("The testing identity does not exist.")

        elif not identity.enabled:
            issues.append("The testing identity is disabled.")

        if operation is None:
            issues.append("The imported operation does not exist.")

        elif operation.method.upper() not in SUPPORTED_BOLA_METHODS:
            issues.append("The operation method is not enabled for automatic BOLA execution.")

        if binding is None:
            issues.append("The operation does not have an object binding.")

        elif binding.resource_type != deny_case.resource_type:
            issues.append("The case resource does not match the operation binding.")

        if probe_object is None:
            issues.append("The cross-owner probe object does not exist.")

        elif probe_object.owner_identity_id is None:
            issues.append("The cross-owner probe object has no owner.")

        elif probe_object.owner_identity_id == deny_case.identity_id:
            issues.append("The probe object is owned by the testing identity.")

        baseline_candidates = sorted(
            allow_cases.get(
                (
                    deny_case.identity_id,
                    deny_case.operation_key,
                    deny_case.resource_type,
                ),
                [],
            ),
            key=lambda item: item.case_id,
        )

        baseline_case: AuthorizationCase | None = None

        baseline_object: ObjectRecord | None = None

        for candidate in baseline_candidates:
            candidate_object = object_map.get(
                (
                    candidate.resource_type,
                    candidate.object_id,
                )
            )

            if (
                candidate_object is not None
                and candidate_object.owner_identity_id == deny_case.identity_id
            ):
                baseline_case = candidate
                baseline_object = candidate_object
                break

        if baseline_case is None:
            issues.append("No enabled owned-object allow case is available as the baseline.")

        path_parameter = binding.path_parameter if binding is not None else None

        baseline_path_parameters: dict[
            str,
            str,
        ] = {}

        probe_path_parameters: dict[
            str,
            str,
        ] = {}

        if path_parameter is not None:
            probe_path_parameters[path_parameter] = deny_case.object_id

            if baseline_case is not None:
                baseline_path_parameters[path_parameter] = baseline_case.object_id

        expected_status_codes = sorted(
            set(deny_case.expected_status_codes or DEFAULT_DENIAL_STATUS_CODES)
        )

        probe_owner_identity = (
            identity_map.get(probe_object.owner_identity_id)
            if (probe_object is not None and probe_object.owner_identity_id is not None)
            else None
        )

        plan_items.append(
            BOLATestPlanItem(
                case_id=deny_case.case_id,
                case_name=deny_case.name,
                operation_key=(deny_case.operation_key),
                identity_id=(deny_case.identity_id),
                identity_name=identity_name,
                resource_type=(deny_case.resource_type),
                path_parameter=(path_parameter),
                baseline_object_id=(
                    baseline_object.object_id if baseline_object is not None else None
                ),
                probe_object_id=(deny_case.object_id),
                probe_owner_identity_id=(
                    probe_object.owner_identity_id if probe_object is not None else None
                ),
                probe_owner_identity_name=(
                    probe_owner_identity.name if probe_owner_identity is not None else None
                ),
                baseline_path_parameters=(baseline_path_parameters),
                probe_path_parameters=(probe_path_parameters),
                expected_probe_status_codes=(expected_status_codes),
                ready=not issues,
                issues=issues,
            )
        )

    plan_items.sort(
        key=lambda item: (
            item.operation_key,
            item.identity_name.lower(),
            item.probe_object_id,
        )
    )

    ready_count = sum(plan_item.ready for plan_item in plan_items)

    return BOLATestPlan(
        project_id=project_id,
        total_count=len(plan_items),
        ready_count=ready_count,
        blocked_count=(len(plan_items) - ready_count),
        items=plan_items,
    )
