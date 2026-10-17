"""Integration tests for the local demonstration API."""

from collections.abc import (
    Iterator,
)

import pytest
from fastapi.testclient import (
    TestClient,
)

from accessmatrix.demo_api.app import (
    create_demo_app,
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Create a fresh demonstration API client."""

    with TestClient(create_demo_app()) as test_client:
        yield test_client


def bearer_headers(
    token: str,
) -> dict[str, str]:
    """Build demonstration Bearer authentication."""

    return {"Authorization": (f"Bearer {token}")}


def test_health_is_public(
    client: TestClient,
) -> None:
    """The local health endpoint should be public."""

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "service": ("accessmatrix-demo-api"),
    }


def test_customer_list_contains_only_owned_invoices(
    client: TestClient,
) -> None:
    """The invoice listing should enforce ownership."""

    response = client.get(
        "/invoices",
        headers=bearer_headers("demo-alice-token"),
    )

    assert response.status_code == 200

    invoice_ids = {invoice["invoice_id"] for invoice in response.json()}

    assert invoice_ids == {
        "INV-1001",
        "INV-1002",
    }


def test_invoice_detail_contains_intentional_bola(
    client: TestClient,
) -> None:
    """Alice can intentionally retrieve Bob's invoice."""

    response = client.get(
        "/invoices/INV-2001",
        headers=bearer_headers("demo-alice-token"),
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["invoice_id"] == "INV-2001"

    assert payload["owner_id"] == "bob"

    assert payload["tenant_id"] == "tenant-b"


def test_customer_cannot_access_admin_report(
    client: TestClient,
) -> None:
    """Customer identities should be denied administrative reports."""

    customer_response = client.get(
        "/admin/reports",
        headers=bearer_headers("demo-alice-token"),
    )

    assert customer_response.status_code == 403

    admin_response = client.get(
        "/admin/reports",
        headers=bearer_headers("demo-admin-token"),
    )

    assert admin_response.status_code == 200

    assert admin_response.json()["invoice_count"] == 4


def test_customer_cannot_update_another_customer_invoice(
    client: TestClient,
) -> None:
    """The update endpoint should enforce invoice ownership."""

    response = client.patch(
        "/invoices/INV-2001",
        headers=bearer_headers("demo-alice-token"),
        json={"description": ("Unauthorized modification.")},
    )

    assert response.status_code == 403


def test_only_admin_can_delete_invoice(
    client: TestClient,
) -> None:
    """Delete should be restricted to the administrator role."""

    customer_response = client.delete(
        "/invoices/INV-1001",
        headers=bearer_headers("demo-alice-token"),
    )

    assert customer_response.status_code == 403

    admin_response = client.delete(
        "/invoices/INV-1001",
        headers=bearer_headers("demo-admin-token"),
    )

    assert admin_response.status_code == 204
