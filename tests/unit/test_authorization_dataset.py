"""Unit tests for authorization datasets."""

from pathlib import Path

import pytest

from accessmatrix.authorization.models import (
    AuthorizationCase,
    AuthorizationDataset,
    ObjectRecord,
    OperationObjectBinding,
    ResourceDefinition,
)
from accessmatrix.authorization.storage import (
    AuthorizationDatasetRepository,
    AuthorizationDatasetStorageError,
)
from accessmatrix.authorization.validation import (
    validate_authorization_dataset,
)
from accessmatrix.openapi.operations import (
    OpenAPIOperation,
    OpenAPIParameter,
)


def build_invoice_operation() -> OpenAPIOperation:
    """Create an invoice detail operation."""

    return OpenAPIOperation(
        key=("GET /invoices/{invoice_id}"),
        method="GET",
        path=("/invoices/{invoice_id}"),
        operation_id="getInvoice",
        summary="Read an invoice",
        description=None,
        tags=("Invoices",),
        deprecated=False,
        security_required=True,
        parameters=(
            OpenAPIParameter(
                name="invoice_id",
                location="path",
                required=True,
                schema_type="string",
                description=None,
            ),
        ),
        request_content_types=(),
        response_codes=(
            "200",
            "401",
            "404",
        ),
    )


def build_valid_dataset() -> AuthorizationDataset:
    """Create a valid demonstration dataset."""

    return AuthorizationDataset(
        resources=[
            ResourceDefinition(
                name="invoice",
                display_name="Invoice",
                description=("Customer-owned invoice."),
            ),
        ],
        objects=[
            ObjectRecord(
                resource_type="invoice",
                object_id="INV-1001",
                display_name=("Alice invoice"),
                owner_identity_id=("identity-alice"),
                tenant="tenant-a",
            ),
            ObjectRecord(
                resource_type="invoice",
                object_id="INV-2001",
                display_name=("Bob invoice"),
                owner_identity_id=("identity-bob"),
                tenant="tenant-b",
            ),
        ],
        bindings=[
            OperationObjectBinding(
                operation_key=("GET /invoices/{invoice_id}"),
                resource_type="invoice",
                path_parameter=("invoice_id"),
                response_id_field=("invoice_id"),
                response_owner_field=("owner_id"),
                response_tenant_field=("tenant_id"),
            ),
        ],
        cases=[
            AuthorizationCase(
                case_id=("alice-own-invoice"),
                name=("Alice reads her invoice"),
                operation_key=("GET /invoices/{invoice_id}"),
                identity_id=("identity-alice"),
                resource_type="invoice",
                object_id="INV-1001",
                expectation="allow",
                expected_status_codes=[
                    200,
                ],
            ),
            AuthorizationCase(
                case_id=("alice-bob-invoice"),
                name=("Alice cannot read Bob invoice"),
                operation_key=("GET /invoices/{invoice_id}"),
                identity_id=("identity-alice"),
                resource_type="invoice",
                object_id="INV-2001",
                expectation="deny",
                expected_status_codes=[
                    403,
                    404,
                ],
            ),
        ],
    )


def test_valid_dataset_has_no_issues() -> None:
    """A complete dataset should pass validation."""

    issues = validate_authorization_dataset(
        build_valid_dataset(),
        operations=[build_invoice_operation()],
        identity_ids={
            "identity-alice",
            "identity-bob",
        },
    )

    assert issues == []


def test_unknown_object_owner_is_rejected() -> None:
    """Object owners must be configured identities."""

    dataset = build_valid_dataset()

    dataset.objects[0].owner_identity_id = "missing-identity"

    issues = validate_authorization_dataset(
        dataset,
        operations=[build_invoice_operation()],
        identity_ids={
            "identity-alice",
            "identity-bob",
        },
    )

    assert any("unknown owner identity" in issue for issue in issues)


def test_unknown_path_parameter_is_rejected() -> None:
    """Bindings must reference declared path parameters."""

    dataset = build_valid_dataset()

    dataset.bindings[0].path_parameter = "object_id"

    issues = validate_authorization_dataset(
        dataset,
        operations=[build_invoice_operation()],
        identity_ids={
            "identity-alice",
            "identity-bob",
        },
    )

    assert any("not declared" in issue for issue in issues)


def test_case_resource_must_match_binding() -> None:
    """A case resource must match its operation binding."""

    dataset = build_valid_dataset()

    dataset.cases[0].resource_type = "customer"

    issues = validate_authorization_dataset(
        dataset,
        operations=[build_invoice_operation()],
        identity_ids={
            "identity-alice",
            "identity-bob",
        },
    )

    assert any("unknown object" in issue for issue in issues)

    assert any("operation is bound" in issue for issue in issues)


def test_repository_round_trip(
    tmp_path: Path,
) -> None:
    """Saved datasets should load without data loss."""

    repository = AuthorizationDatasetRepository(tmp_path)

    dataset = build_valid_dataset()

    repository.save(
        "project-123",
        dataset,
    )

    loaded = repository.load("project-123")

    assert loaded == dataset


def test_repository_returns_empty_dataset(
    tmp_path: Path,
) -> None:
    """Missing project datasets should be empty."""

    repository = AuthorizationDatasetRepository(tmp_path)

    loaded = repository.load("project-123")

    assert loaded == (AuthorizationDataset())


def test_repository_rejects_unsafe_project_id(
    tmp_path: Path,
) -> None:
    """Project identifiers must not permit path traversal."""

    repository = AuthorizationDatasetRepository(tmp_path)

    with pytest.raises(
        AuthorizationDatasetStorageError,
        match="identifier",
    ):
        repository.load("../../outside")


def test_repository_rejects_corrupted_dataset(
    tmp_path: Path,
) -> None:
    """Corrupted persisted JSON should fail safely."""

    dataset_directory = tmp_path / "authorization-datasets"

    dataset_directory.mkdir(parents=True)

    (dataset_directory / "project-123.json").write_text(
        "{not valid json",
        encoding="utf-8",
    )

    repository = AuthorizationDatasetRepository(tmp_path)

    with pytest.raises(
        AuthorizationDatasetStorageError,
        match="corrupted",
    ):
        repository.load("project-123")
