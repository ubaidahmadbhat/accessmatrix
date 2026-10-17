"""Integration tests for project management."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from accessmatrix.api.app import create_app
from accessmatrix.persistence.database import (
    Base,
    get_session,
)
from accessmatrix.persistence.storage import (
    get_storage_root,
)


@pytest.fixture
def client(
    tmp_path: Path,
) -> Iterator[TestClient]:
    """Create an isolated API test client."""

    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    def override_storage() -> Path:
        return tmp_path

    application = create_app(
        initialize_storage=False,
    )

    application.dependency_overrides[get_session] = override_session

    application.dependency_overrides[get_storage_root] = override_storage

    with TestClient(application) as test_client:
        yield test_client

    engine.dispose()


def test_create_and_list_projects(
    client: TestClient,
) -> None:
    """A project should persist and appear in the list."""

    create_response = client.post(
        "/api/v1/projects",
        json={
            "name": "Invoice API",
            "description": ("Authorization tests for invoices."),
            "base_url": ("http://127.0.0.1:9000"),
        },
    )

    assert create_response.status_code == 201

    created = create_response.json()

    assert created["name"] == "Invoice API"
    assert created["operation_count"] == 0
    assert created["openapi_version"] is None

    list_response = client.get("/api/v1/projects")

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == created["id"]


def test_upload_openapi_document(
    client: TestClient,
) -> None:
    """A valid OpenAPI file should be imported."""

    create_response = client.post(
        "/api/v1/projects",
        json={
            "name": "Invoice API",
        },
    )

    project_id = create_response.json()["id"]

    specification = b"""
openapi: 3.1.0
info:
  title: Invoice Demonstration API
  version: 1.0.0
paths:
  /invoices/{invoice_id}:
    get:
      operationId: getInvoice
      parameters:
        - name: invoice_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Invoice returned
"""

    response = client.post(
        (f"/api/v1/projects/{project_id}/openapi"),
        files={
            "file": (
                "openapi.yaml",
                specification,
                "application/yaml",
            )
        },
    )

    assert response.status_code == 200

    project = response.json()

    assert project["openapi_version"] == "3.1.0"

    assert project["openapi_title"] == "Invoice Demonstration API"

    assert project["operation_count"] == 1
    assert project["spec_filename"] == "openapi.yaml"


def test_invalid_openapi_document_is_rejected(
    client: TestClient,
) -> None:
    """An invalid specification should not be accepted."""

    create_response = client.post(
        "/api/v1/projects",
        json={
            "name": "Invalid API",
        },
    )

    project_id = create_response.json()["id"]

    response = client.post(
        (f"/api/v1/projects/{project_id}/openapi"),
        files={
            "file": (
                "openapi.yaml",
                b"openapi: 3.1.0",
                "application/yaml",
            )
        },
    )

    assert response.status_code == 422

    assert "validation failed" in response.json()["detail"].lower()


def test_delete_project(
    client: TestClient,
) -> None:
    """A project should be removable."""

    create_response = client.post(
        "/api/v1/projects",
        json={
            "name": "Temporary API",
        },
    )

    project_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/projects/{project_id}")

    assert delete_response.status_code == 204

    read_response = client.get(f"/api/v1/projects/{project_id}")

    assert read_response.status_code == 404


def test_operations_require_an_imported_document(
    client: TestClient,
) -> None:
    """Operation discovery requires an imported specification."""

    create_response = client.post(
        "/api/v1/projects",
        json={
            "name": "Empty API",
        },
    )

    project_id = create_response.json()["id"]

    response = client.get(f"/api/v1/projects/{project_id}/operations")

    assert response.status_code == 409

    assert response.json()["detail"] == ("This project does not have an OpenAPI document.")


def test_discover_openapi_operations(
    client: TestClient,
) -> None:
    """Imported operations should be normalized."""

    create_response = client.post(
        "/api/v1/projects",
        json={
            "name": "Operations API",
        },
    )

    project_id = create_response.json()["id"]

    specification = b"""
openapi: 3.1.0
info:
  title: Operations Demonstration API
  version: 1.0.0
security:
  - bearerAuth: []
paths:
  /invoices/{invoice_id}:
    parameters:
      - name: invoice_id
        in: path
        required: true
        description: Invoice identifier
        schema:
          type: string
    get:
      operationId: getInvoice
      summary: Read one invoice
      tags:
        - Invoices
      parameters:
        - name: expand
          in: query
          required: false
          schema:
            type: string
      responses:
        "200":
          description: Invoice returned
        "403":
          description: Access denied
    patch:
      operationId: updateInvoice
      summary: Update one invoice
      security: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
      responses:
        "200":
          description: Invoice updated
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
"""

    upload_response = client.post(
        (f"/api/v1/projects/{project_id}/openapi"),
        files={
            "file": (
                "openapi.yaml",
                specification,
                "application/yaml",
            )
        },
    )

    assert upload_response.status_code == 200

    response = client.get(f"/api/v1/projects/{project_id}/operations")

    assert response.status_code == 200

    payload = response.json()

    assert payload["project_id"] == project_id

    assert payload["openapi_title"] == "Operations Demonstration API"

    assert payload["openapi_version"] == "3.1.0"

    assert payload["operation_count"] == 2
    assert len(payload["operations"]) == 2

    get_operation = next(
        operation for operation in payload["operations"] if operation["method"] == "GET"
    )

    assert get_operation["path"] == "/invoices/{invoice_id}"

    assert get_operation["operation_id"] == "getInvoice"

    assert get_operation["security_required"] is True

    assert get_operation["tags"] == ["Invoices"]

    assert get_operation["response_codes"] == [
        "200",
        "403",
    ]

    assert len(get_operation["parameters"]) == 2

    parameter_names = {parameter["name"] for parameter in get_operation["parameters"]}

    assert parameter_names == {
        "invoice_id",
        "expand",
    }

    path_parameter = next(
        parameter for parameter in get_operation["parameters"] if parameter["name"] == "invoice_id"
    )

    assert path_parameter["location"] == "path"

    assert path_parameter["required"] is True

    assert path_parameter["schema_type"] == "string"

    patch_operation = next(
        operation for operation in payload["operations"] if operation["method"] == "PATCH"
    )

    assert patch_operation["security_required"] is False

    assert patch_operation["request_content_types"] == ["application/json"]

    assert patch_operation["response_codes"] == ["200"]
