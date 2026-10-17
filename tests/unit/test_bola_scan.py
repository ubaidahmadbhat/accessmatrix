"""Unit tests for automatic BOLA scan execution."""

from collections.abc import (
    Callable,
)
from pathlib import Path

import httpx

from accessmatrix.authorization.bola import (
    build_bola_test_plan,
)
from accessmatrix.authorization.demo_seed import (
    build_demo_authorization_dataset,
)
from accessmatrix.execution.executor import (
    ControlledRequestExecutor,
)
from accessmatrix.execution.rate_limit import (
    SlidingWindowRateLimiter,
)
from accessmatrix.openapi.operations import (
    OpenAPIOperation,
    OpenAPIParameter,
)
from accessmatrix.persistence.models import (
    IdentityProfile,
    Project,
)
from accessmatrix.scanning.bola import (
    BOLAScanRunner,
)
from accessmatrix.scanning.models import (
    BOLAScan,
)
from accessmatrix.scanning.storage import (
    BOLAScanRepository,
)
from accessmatrix.security.credentials import (
    CredentialResolver,
)

MockHandler = Callable[
    [httpx.Request],
    httpx.Response,
]


def build_identity(
    *,
    identity_id: str,
    name: str,
    tenant: str,
    secret_reference: str,
) -> IdentityProfile:
    """Create a demonstration identity."""

    return IdentityProfile(
        id=identity_id,
        project_id="project-1",
        name=name,
        role="customer",
        tenant=tenant,
        auth_type="bearer",
        secret_source="environment",
        secret_reference=(secret_reference),
        auth_prefix="Bearer",
        enabled=True,
    )


def build_identities() -> list[IdentityProfile]:
    """Create Alice and Bob identities."""

    return [
        build_identity(
            identity_id="alice-id",
            name="Customer Alice",
            tenant="tenant-a",
            secret_reference=("ACCESSMATRIX_ALICE_TOKEN"),
        ),
        build_identity(
            identity_id="bob-id",
            name="Customer Bob",
            tenant="tenant-b",
            secret_reference=("ACCESSMATRIX_BOB_TOKEN"),
        ),
    ]


def build_operation(
    *,
    path: str,
    parameter_name: str,
) -> OpenAPIOperation:
    """Create a protected object operation."""

    return OpenAPIOperation(
        key=f"GET {path}",
        method="GET",
        path=path,
        operation_id=parameter_name,
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


def build_operations() -> list[OpenAPIOperation]:
    """Create invoice and customer-profile operations."""

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


def build_executor(
    handler: MockHandler,
) -> ControlledRequestExecutor:
    """Create an executor using a mock transport."""

    return ControlledRequestExecutor(
        resolver=CredentialResolver(
            environment={
                "ACCESSMATRIX_ALICE_TOKEN": ("demo-alice-token"),
                "ACCESSMATRIX_BOB_TOKEN": ("demo-bob-token"),
            }
        ),
        rate_limiter=(
            SlidingWindowRateLimiter(
                limit=100,
                window_seconds=60.0,
            )
        ),
        transport=httpx.MockTransport(handler),
    )


def identity_from_request(
    request: httpx.Request,
) -> str:
    """Resolve the demonstration user from the bearer token."""

    authorization = request.headers["Authorization"]

    if authorization == ("Bearer demo-alice-token"):
        return "alice"

    if authorization == ("Bearer demo-bob-token"):
        return "bob"

    raise AssertionError("Unexpected demonstration token.")


def object_response(
    request: httpx.Request,
    *,
    enforce_ownership: bool,
) -> httpx.Response:
    """Return a demonstration object response."""

    user_id = identity_from_request(request)

    path = request.url.path

    invoice_owners = {
        "INV-1001": (
            "alice",
            "tenant-a",
        ),
        "INV-1002": (
            "alice",
            "tenant-a",
        ),
        "INV-2001": (
            "bob",
            "tenant-b",
        ),
        "INV-2002": (
            "bob",
            "tenant-b",
        ),
    }

    if path.startswith("/invoices/"):
        invoice_id = path.rsplit(
            "/",
            1,
        )[1]

        owner_id, tenant = invoice_owners[invoice_id]

        if enforce_ownership and owner_id != user_id:
            return httpx.Response(
                403,
                json={
                    "detail": "Forbidden",
                },
            )

        return httpx.Response(
            200,
            headers={"X-Echo-Authorization": (request.headers["Authorization"])},
            json={
                "invoice_id": invoice_id,
                "owner_id": owner_id,
                "tenant_id": tenant,
            },
        )

    if path.startswith("/customers/"):
        customer_id = path.split("/")[2]

        tenant = "tenant-a" if customer_id == "alice" else "tenant-b"

        if enforce_ownership and customer_id != user_id:
            return httpx.Response(
                404,
                json={
                    "detail": "Not found",
                },
            )

        return httpx.Response(
            200,
            headers={"X-Echo-Authorization": (request.headers["Authorization"])},
            json={
                "customer_id": customer_id,
                "tenant_id": tenant,
            },
        )

    raise AssertionError(f"Unexpected request path: {path}")


def run_scan(
    handler: MockHandler,
) -> BOLAScan:
    """Build and execute the demonstration BOLA scan."""

    identities = build_identities()

    operations = build_operations()

    dataset = build_demo_authorization_dataset(identities)

    plan = build_bola_test_plan(
        project_id="project-1",
        dataset=dataset,
        operations=operations,
        identities=identities,
    )

    runner = BOLAScanRunner(build_executor(handler))

    return runner.run(
        project=Project(
            id="project-1",
            name="BOLA Test Project",
            base_url=("https://api.example.test"),
        ),
        plan=plan,
        dataset=dataset,
        operations=operations,
        identities=identities,
        max_cases=100,
    )


def test_vulnerable_api_produces_four_findings() -> None:
    """Successful cross-owner responses should become findings."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return object_response(
            request,
            enforce_ownership=False,
        )

    scan = run_scan(handler)

    assert scan.status == "completed"
    assert scan.total_count == 4
    assert scan.finding_count == 4
    assert scan.pass_count == 0

    assert all(finding.severity == "high" for finding in scan.findings)

    assert all(finding.confidence == "high" for finding in scan.findings)

    serialized = scan.model_dump_json()

    assert "demo-alice-token" not in serialized

    assert "demo-bob-token" not in serialized

    assert "[REDACTED]" in serialized


def test_secure_api_passes_four_probes() -> None:
    """Expected authorization denials should pass."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return object_response(
            request,
            enforce_ownership=True,
        )

    scan = run_scan(handler)

    assert scan.status == "completed"
    assert scan.total_count == 4
    assert scan.pass_count == 4
    assert scan.finding_count == 0
    assert scan.findings == []


def test_scan_repository_round_trip(
    tmp_path: Path,
) -> None:
    """Persisted scans should load without data loss."""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return object_response(
            request,
            enforce_ownership=False,
        )

    scan = run_scan(handler)

    repository = BOLAScanRepository(tmp_path)

    repository.save(scan)

    loaded = repository.load(
        scan.project_id,
        scan.scan_id,
    )

    assert loaded == scan

    summaries = repository.list_summaries(scan.project_id)

    assert len(summaries) == 1

    assert summaries[0].scan_id == scan.scan_id

    assert summaries[0].finding_count == 4
