"""Demonstration authorization dataset generation."""

from accessmatrix.authorization.models import (
    AuthorizationCase,
    AuthorizationDataset,
    ObjectRecord,
    OperationObjectBinding,
    ResourceDefinition,
)
from accessmatrix.persistence.models import (
    IdentityProfile,
)


class DemoAuthorizationSeedError(RuntimeError):
    """Raised when demonstration identities cannot be resolved."""


def normalize_optional_text(
    value: str | None,
) -> str:
    """Normalize an optional comparison value."""

    return value.strip().lower() if isinstance(value, str) else ""


def find_demo_identity(
    identities: list[IdentityProfile],
    *,
    role: str,
    tenant: str,
    label: str,
) -> IdentityProfile:
    """Find one enabled identity using role and tenant."""

    matching_identities = [
        identity
        for identity in identities
        if identity.enabled
        and normalize_optional_text(identity.role) == role.lower()
        and normalize_optional_text(identity.tenant) == tenant.lower()
    ]

    if not matching_identities:
        raise DemoAuthorizationSeedError(
            f"An enabled {label} identity was not found. "
            f"Expected role {role!r} and tenant {tenant!r}."
        )

    if len(matching_identities) > 1:
        raise DemoAuthorizationSeedError(
            f"More than one enabled {label} identity matches role {role!r} and tenant {tenant!r}."
        )

    return matching_identities[0]


def build_demo_authorization_dataset(
    identities: list[IdentityProfile],
) -> AuthorizationDataset:
    """Build the invoice demonstration authorization dataset."""

    alice = find_demo_identity(
        identities,
        role="customer",
        tenant="tenant-a",
        label="Customer Alice",
    )

    bob = find_demo_identity(
        identities,
        role="customer",
        tenant="tenant-b",
        label="Customer Bob",
    )

    invoice_operation = "GET /invoices/{invoice_id}"

    customer_profile_operation = "GET /customers/{customer_id}/profile"

    return AuthorizationDataset(
        resources=[
            ResourceDefinition(
                name="invoice",
                display_name="Invoice",
                description=("A customer-owned invoice protected by object-level authorization."),
            ),
            ResourceDefinition(
                name="customer_profile",
                display_name="Customer profile",
                description=(
                    "A customer-owned profile containing personal and internal properties."
                ),
            ),
        ],
        objects=[
            ObjectRecord(
                resource_type="invoice",
                object_id="INV-1001",
                display_name="Alice invoice 1001",
                owner_identity_id=alice.id,
                tenant="tenant-a",
                attributes={
                    "owner_user_id": "alice",
                },
            ),
            ObjectRecord(
                resource_type="invoice",
                object_id="INV-1002",
                display_name="Alice invoice 1002",
                owner_identity_id=alice.id,
                tenant="tenant-a",
                attributes={
                    "owner_user_id": "alice",
                },
            ),
            ObjectRecord(
                resource_type="invoice",
                object_id="INV-2001",
                display_name="Bob invoice 2001",
                owner_identity_id=bob.id,
                tenant="tenant-b",
                attributes={
                    "owner_user_id": "bob",
                },
            ),
            ObjectRecord(
                resource_type="invoice",
                object_id="INV-2002",
                display_name="Bob invoice 2002",
                owner_identity_id=bob.id,
                tenant="tenant-b",
                attributes={
                    "owner_user_id": "bob",
                },
            ),
            ObjectRecord(
                resource_type="customer_profile",
                object_id="alice",
                display_name="Alice customer profile",
                owner_identity_id=alice.id,
                tenant="tenant-a",
                attributes={
                    "customer_id": "alice",
                },
            ),
            ObjectRecord(
                resource_type="customer_profile",
                object_id="bob",
                display_name="Bob customer profile",
                owner_identity_id=bob.id,
                tenant="tenant-b",
                attributes={
                    "customer_id": "bob",
                },
            ),
        ],
        bindings=[
            OperationObjectBinding(
                operation_key=invoice_operation,
                resource_type="invoice",
                path_parameter="invoice_id",
                response_id_field="invoice_id",
                response_owner_field="owner_id",
                response_tenant_field="tenant_id",
            ),
            OperationObjectBinding(
                operation_key=customer_profile_operation,
                resource_type="customer_profile",
                path_parameter="customer_id",
                response_id_field="customer_id",
                response_owner_field=None,
                response_tenant_field="tenant_id",
            ),
        ],
        cases=[
            AuthorizationCase(
                case_id="alice-own-invoice",
                name="Alice reads her own invoice",
                operation_key=invoice_operation,
                identity_id=alice.id,
                resource_type="invoice",
                object_id="INV-1001",
                expectation="allow",
                expected_status_codes=[
                    200,
                ],
            ),
            AuthorizationCase(
                case_id="alice-bob-invoice",
                name="Alice must not read Bob's invoice",
                operation_key=invoice_operation,
                identity_id=alice.id,
                resource_type="invoice",
                object_id="INV-2001",
                expectation="deny",
                expected_status_codes=[
                    403,
                    404,
                ],
            ),
            AuthorizationCase(
                case_id="bob-own-invoice",
                name="Bob reads his own invoice",
                operation_key=invoice_operation,
                identity_id=bob.id,
                resource_type="invoice",
                object_id="INV-2001",
                expectation="allow",
                expected_status_codes=[
                    200,
                ],
            ),
            AuthorizationCase(
                case_id="bob-alice-invoice",
                name="Bob must not read Alice's invoice",
                operation_key=invoice_operation,
                identity_id=bob.id,
                resource_type="invoice",
                object_id="INV-1001",
                expectation="deny",
                expected_status_codes=[
                    403,
                    404,
                ],
            ),
            AuthorizationCase(
                case_id="alice-own-profile",
                name="Alice reads her own profile",
                operation_key=customer_profile_operation,
                identity_id=alice.id,
                resource_type="customer_profile",
                object_id="alice",
                expectation="allow",
                expected_status_codes=[
                    200,
                ],
            ),
            AuthorizationCase(
                case_id="alice-bob-profile",
                name="Alice must not read Bob's profile",
                operation_key=customer_profile_operation,
                identity_id=alice.id,
                resource_type="customer_profile",
                object_id="bob",
                expectation="deny",
                expected_status_codes=[
                    403,
                    404,
                ],
            ),
            AuthorizationCase(
                case_id="bob-own-profile",
                name="Bob reads his own profile",
                operation_key=customer_profile_operation,
                identity_id=bob.id,
                resource_type="customer_profile",
                object_id="bob",
                expectation="allow",
                expected_status_codes=[
                    200,
                ],
            ),
            AuthorizationCase(
                case_id="bob-alice-profile",
                name="Bob must not read Alice's profile",
                operation_key=customer_profile_operation,
                identity_id=bob.id,
                resource_type="customer_profile",
                object_id="alice",
                expectation="deny",
                expected_status_codes=[
                    403,
                    404,
                ],
            ),
        ],
    )
