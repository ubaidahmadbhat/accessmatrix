"""Unit tests for BOLA test-plan generation."""

from accessmatrix.authorization.bola import (
    build_bola_test_plan,
)
from accessmatrix.authorization.demo_seed import (
    DemoAuthorizationSeedError,
    build_demo_authorization_dataset,
)
from accessmatrix.openapi.operations import (
    OpenAPIOperation,
    OpenAPIParameter,
)
from accessmatrix.persistence.models import (
    IdentityProfile,
)


def build_identity(
    *,
    identity_id: str,
    name: str,
    tenant: str,
    enabled: bool = True,
) -> IdentityProfile:
    """Create a demonstration customer identity."""

    return IdentityProfile(
        id=identity_id,
        project_id="project-1",
        name=name,
        role="customer",
        tenant=tenant,
        auth_type="bearer",
        secret_source="environment",
        secret_reference=(f"ACCESSMATRIX_{identity_id.upper()}_TOKEN"),
        auth_prefix="Bearer",
        enabled=enabled,
    )


def build_operation(
    *,
    path: str,
    parameter_name: str,
) -> OpenAPIOperation:
    """Create a protected GET operation."""

    return OpenAPIOperation(
        key=f"GET {path}",
        method="GET",
        path=path,
        operation_id=(parameter_name),
        summary=None,
        description=None,
        tags=(),
        deprecated=False,
        security_required=True,
        parameters=(
            OpenAPIParameter(
                name=parameter_name,
                location="path",
                required=True,
                schema_type="string",
                description=None,
            ),
        ),
        request_content_types=(),
        response_codes=(
            "200",
            "403",
            "404",
        ),
    )


def build_identities() -> list[IdentityProfile]:
    """Create Alice and Bob identities."""

    return [
        build_identity(
            identity_id="alice-id",
            name="Customer Alice",
            tenant="tenant-a",
        ),
        build_identity(
            identity_id="bob-id",
            name="Customer Bob",
            tenant="tenant-b",
        ),
    ]


def build_operations() -> list[OpenAPIOperation]:
    """Create the demonstration object operations."""

    return [
        build_operation(
            path=("/invoices/{invoice_id}"),
            parameter_name="invoice_id",
        ),
        build_operation(
            path=("/customers/{customer_id}/profile"),
            parameter_name="customer_id",
        ),
    ]


def test_demo_seed_builds_expected_dataset() -> None:
    """The seed should create all demonstration records."""

    dataset = build_demo_authorization_dataset(build_identities())

    assert len(dataset.resources) == 2
    assert len(dataset.objects) == 6
    assert len(dataset.bindings) == 2
    assert len(dataset.cases) == 8

    deny_cases = [
        authorization_case
        for authorization_case in dataset.cases
        if (authorization_case.expectation == "deny")
    ]

    assert len(deny_cases) == 4


def test_demo_seed_requires_alice_and_bob() -> None:
    """The seed requires both configured customer tenants."""

    identities = [
        build_identity(
            identity_id="alice-id",
            name="Customer Alice",
            tenant="tenant-a",
        )
    ]

    try:
        build_demo_authorization_dataset(identities)

    except DemoAuthorizationSeedError as exc:
        assert "Customer Bob" in str(exc)

    else:
        raise AssertionError("Expected demonstration seed failure.")


def test_bola_plan_contains_four_ready_cases() -> None:
    """The demonstration dataset should produce four probes."""

    identities = build_identities()

    dataset = build_demo_authorization_dataset(identities)

    plan = build_bola_test_plan(
        project_id="project-1",
        dataset=dataset,
        operations=build_operations(),
        identities=identities,
    )

    assert plan.total_count == 4
    assert plan.ready_count == 4
    assert plan.blocked_count == 0

    assert all(plan_item.ready for plan_item in plan.items)

    assert {plan_item.case_id for plan_item in plan.items} == {
        "alice-bob-invoice",
        "bob-alice-invoice",
        "alice-bob-profile",
        "bob-alice-profile",
    }


def test_bola_plan_contains_baseline_and_probe_values() -> None:
    """A BOLA plan should pair owned and cross-owner objects."""

    identities = build_identities()

    dataset = build_demo_authorization_dataset(identities)

    plan = build_bola_test_plan(
        project_id="project-1",
        dataset=dataset,
        operations=build_operations(),
        identities=identities,
    )

    alice_invoice_case = next(
        plan_item for plan_item in plan.items if plan_item.case_id == "alice-bob-invoice"
    )

    assert alice_invoice_case.baseline_object_id == "INV-1001"

    assert alice_invoice_case.probe_object_id == "INV-2001"

    assert alice_invoice_case.baseline_path_parameters == {
        "invoice_id": "INV-1001",
    }

    assert alice_invoice_case.probe_path_parameters == {
        "invoice_id": "INV-2001",
    }


def test_bola_plan_blocks_missing_baseline() -> None:
    """A deny case without an owned baseline should be blocked."""

    identities = build_identities()

    dataset = build_demo_authorization_dataset(identities)

    dataset.cases = [
        authorization_case
        for authorization_case in dataset.cases
        if authorization_case.case_id != "alice-own-invoice"
    ]

    plan = build_bola_test_plan(
        project_id="project-1",
        dataset=dataset,
        operations=build_operations(),
        identities=identities,
    )

    alice_invoice_case = next(
        plan_item for plan_item in plan.items if plan_item.case_id == "alice-bob-invoice"
    )

    assert alice_invoice_case.ready is False

    assert any("baseline" in issue.lower() for issue in alice_invoice_case.issues)
