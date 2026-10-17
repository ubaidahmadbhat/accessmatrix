"""Authorization dataset validation rules."""

from collections import Counter

from accessmatrix.authorization.models import (
    AuthorizationDataset,
)
from accessmatrix.openapi.operations import (
    OpenAPIOperation,
)

MAX_RESOURCES = 100
MAX_OBJECTS = 5000
MAX_BINDINGS = 1000
MAX_CASES = 10000
MAX_OBJECT_ATTRIBUTES = 50
MAX_ATTRIBUTE_NAME_LENGTH = 128
MAX_ATTRIBUTE_VALUE_LENGTH = 4096


def find_duplicates(
    values: list[str],
) -> list[str]:
    """Return duplicate values in sorted order."""

    counts = Counter(values)

    return sorted(value for value, count in counts.items() if count > 1)


def validate_dataset_limits(
    dataset: AuthorizationDataset,
) -> list[str]:
    """Validate overall dataset size limits."""

    issues: list[str] = []

    if len(dataset.resources) > MAX_RESOURCES:
        issues.append(f"The dataset contains more than {MAX_RESOURCES} resources.")

    if len(dataset.objects) > MAX_OBJECTS:
        issues.append(f"The dataset contains more than {MAX_OBJECTS} objects.")

    if len(dataset.bindings) > MAX_BINDINGS:
        issues.append(f"The dataset contains more than {MAX_BINDINGS} operation bindings.")

    if len(dataset.cases) > MAX_CASES:
        issues.append(f"The dataset contains more than {MAX_CASES} authorization cases.")

    return issues


def validate_resources(
    dataset: AuthorizationDataset,
) -> list[str]:
    """Validate resource definitions."""

    issues: list[str] = []

    duplicate_names = find_duplicates([resource.name for resource in dataset.resources])

    for resource_name in duplicate_names:
        issues.append(f"Resource name {resource_name!r} is duplicated.")

    return issues


def validate_objects(
    dataset: AuthorizationDataset,
    *,
    resource_names: set[str],
    identity_ids: set[str],
) -> list[str]:
    """Validate object records and ownership."""

    issues: list[str] = []

    object_keys = [
        (
            object_record.resource_type,
            object_record.object_id,
        )
        for object_record in dataset.objects
    ]

    duplicate_object_keys = {
        object_key for object_key, count in Counter(object_keys).items() if count > 1
    }

    for (
        resource_type,
        object_id,
    ) in sorted(duplicate_object_keys):
        issues.append(f"Object {resource_type}:{object_id} is duplicated.")

    for object_record in dataset.objects:
        object_label = f"{object_record.resource_type}:{object_record.object_id}"

        if object_record.resource_type not in resource_names:
            issues.append(f"Object {object_label} references an undefined resource.")

        if (
            object_record.owner_identity_id is not None
            and object_record.owner_identity_id not in identity_ids
        ):
            issues.append(f"Object {object_label} references an unknown owner identity.")

        if len(object_record.attributes) > MAX_OBJECT_ATTRIBUTES:
            issues.append(f"Object {object_label} contains too many attributes.")

        for (
            attribute_name,
            attribute_value,
        ) in object_record.attributes.items():
            if not attribute_name.strip():
                issues.append(f"Object {object_label} contains an empty attribute name.")

            if len(attribute_name) > MAX_ATTRIBUTE_NAME_LENGTH:
                issues.append(f"Object {object_label} contains an attribute name that is too long.")

            if len(attribute_value) > MAX_ATTRIBUTE_VALUE_LENGTH:
                issues.append(
                    f"Object {object_label} contains an attribute value that is too long."
                )

    return issues


def validate_bindings(
    dataset: AuthorizationDataset,
    *,
    resource_names: set[str],
    operation_map: dict[
        str,
        OpenAPIOperation,
    ],
) -> list[str]:
    """Validate operation-to-resource bindings."""

    issues: list[str] = []

    duplicate_operations = find_duplicates([binding.operation_key for binding in dataset.bindings])

    for operation_key in duplicate_operations:
        issues.append(f"Operation {operation_key!r} has more than one object binding.")

    for binding in dataset.bindings:
        operation = operation_map.get(binding.operation_key)

        if operation is None:
            issues.append(f"Binding references unknown operation {binding.operation_key!r}.")

            continue

        if binding.resource_type not in resource_names:
            issues.append(
                f"Binding for operation {binding.operation_key!r} references an undefined resource."
            )

        path_parameter_names = {
            parameter.name for parameter in operation.parameters if parameter.location == "path"
        }

        if binding.path_parameter not in path_parameter_names:
            issues.append(
                "Binding for operation "
                f"{binding.operation_key!r} "
                "references path parameter "
                f"{binding.path_parameter!r}, "
                "but that parameter is not declared "
                "by the operation."
            )

    return issues


def validate_cases(
    dataset: AuthorizationDataset,
    *,
    identity_ids: set[str],
    operation_map: dict[
        str,
        OpenAPIOperation,
    ],
) -> list[str]:
    """Validate expected authorization cases."""

    issues: list[str] = []

    object_keys = {
        (
            object_record.resource_type,
            object_record.object_id,
        )
        for object_record in dataset.objects
    }

    binding_by_operation = {binding.operation_key: binding for binding in dataset.bindings}

    duplicate_case_ids = find_duplicates(
        [authorization_case.case_id for authorization_case in dataset.cases]
    )

    for case_id in duplicate_case_ids:
        issues.append(f"Authorization case identifier {case_id!r} is duplicated.")

    for authorization_case in dataset.cases:
        case_label = f"{authorization_case.name} ({authorization_case.case_id})"

        if authorization_case.operation_key not in operation_map:
            issues.append(f"Case {case_label} references an unknown operation.")

        if authorization_case.identity_id not in identity_ids:
            issues.append(f"Case {case_label} references an unknown identity.")

        object_key = (
            authorization_case.resource_type,
            authorization_case.object_id,
        )

        if object_key not in object_keys:
            issues.append(f"Case {case_label} references an unknown object.")

        binding = binding_by_operation.get(authorization_case.operation_key)

        if binding is None:
            issues.append(f"Case {case_label} has no operation-object binding.")

        elif binding.resource_type != authorization_case.resource_type:
            issues.append(
                f"Case {case_label} uses resource "
                f"{authorization_case.resource_type!r}, "
                "but its operation is bound to "
                f"{binding.resource_type!r}."
            )

        duplicate_status_codes = {
            status_code
            for status_code, count in Counter(authorization_case.expected_status_codes).items()
            if count > 1
        }

        if duplicate_status_codes:
            issues.append(f"Case {case_label} contains duplicate expected status codes.")

        for status_code in authorization_case.expected_status_codes:
            if not (100 <= status_code <= 599):
                issues.append(f"Case {case_label} contains invalid HTTP status code {status_code}.")

    return issues


def validate_authorization_dataset(
    dataset: AuthorizationDataset,
    *,
    operations: list[OpenAPIOperation],
    identity_ids: set[str],
) -> list[str]:
    """Validate a complete authorization dataset."""

    resource_names = {resource.name for resource in dataset.resources}

    operation_map = {operation.key: operation for operation in operations}

    issues = [
        *validate_dataset_limits(dataset),
        *validate_resources(dataset),
        *validate_objects(
            dataset,
            resource_names=(resource_names),
            identity_ids=identity_ids,
        ),
        *validate_bindings(
            dataset,
            resource_names=(resource_names),
            operation_map=operation_map,
        ),
        *validate_cases(
            dataset,
            identity_ids=identity_ids,
            operation_map=operation_map,
        ),
    ]

    return issues
