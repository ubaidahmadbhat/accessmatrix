"""Integration tests for identity profile management."""

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
    """Create an isolated identity API test client."""

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


def create_project(
    client: TestClient,
    name: str = "Identity API",
) -> str:
    """Create a project and return its identifier."""

    response = client.post(
        "/api/v1/projects",
        json={
            "name": name,
        },
    )

    assert response.status_code == 201

    return str(response.json()["id"])


def test_create_and_list_bearer_identity(
    client: TestClient,
) -> None:
    """A bearer identity should persist."""

    project_id = create_project(client)

    create_response = client.post(
        (f"/api/v1/projects/{project_id}/identities"),
        json={
            "name": "Customer Alice",
            "description": ("Customer identity owning invoice INV-1001."),
            "role": "customer",
            "tenant": "tenant-a",
            "department": "sales",
            "auth_type": "bearer",
            "secret_source": "environment",
            "secret_reference": ("ACCESSMATRIX_ALICE_TOKEN"),
            "enabled": True,
        },
    )

    assert create_response.status_code == 201

    identity = create_response.json()

    assert identity["name"] == "Customer Alice"
    assert identity["role"] == "customer"
    assert identity["tenant"] == "tenant-a"
    assert identity["auth_type"] == "bearer"

    assert identity["secret_reference"] == "ACCESSMATRIX_ALICE_TOKEN"

    assert identity["auth_prefix"] == "Bearer"
    assert identity["enabled"] is True

    list_response = client.get(f"/api/v1/projects/{project_id}/identities")

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    assert list_response.json()[0]["id"] == identity["id"]


def test_create_api_key_identity(
    client: TestClient,
) -> None:
    """An API-key identity should retain its location and name."""

    project_id = create_project(client)

    response = client.post(
        (f"/api/v1/projects/{project_id}/identities"),
        json={
            "name": "Automation Client",
            "role": "service",
            "auth_type": "api_key",
            "secret_source": "environment",
            "secret_reference": ("ACCESSMATRIX_AUTOMATION_KEY"),
            "auth_location": "header",
            "auth_name": "X-API-Key",
            "enabled": True,
        },
    )

    assert response.status_code == 201

    identity = response.json()

    assert identity["auth_type"] == "api_key"
    assert identity["auth_location"] == "header"
    assert identity["auth_name"] == "X-API-Key"


def test_invalid_bearer_identity_is_rejected(
    client: TestClient,
) -> None:
    """Bearer authentication requires a secret reference."""

    project_id = create_project(client)

    response = client.post(
        (f"/api/v1/projects/{project_id}/identities"),
        json={
            "name": "Invalid Bearer",
            "role": "customer",
            "auth_type": "bearer",
            "secret_source": "environment",
            "enabled": True,
        },
    )

    assert response.status_code == 422

    response_text = response.text.lower()

    assert "secret_reference" in response_text
    assert "required" in response_text


def test_invalid_environment_reference_is_rejected(
    client: TestClient,
) -> None:
    """Environment references must be valid variable names."""

    project_id = create_project(client)

    response = client.post(
        (f"/api/v1/projects/{project_id}/identities"),
        json={
            "name": "Invalid Reference",
            "role": "customer",
            "auth_type": "bearer",
            "secret_source": "environment",
            "secret_reference": ("this is not an environment variable"),
            "enabled": True,
        },
    )

    assert response.status_code == 422

    assert "environment-variable" in response.text.lower()


def test_duplicate_identity_name_is_rejected(
    client: TestClient,
) -> None:
    """Identity names must be unique within a project."""

    project_id = create_project(client)

    payload = {
        "name": "Customer Alice",
        "role": "customer",
        "auth_type": "none",
        "secret_source": "environment",
        "enabled": True,
    }

    first_response = client.post(
        (f"/api/v1/projects/{project_id}/identities"),
        json=payload,
    )

    second_response = client.post(
        (f"/api/v1/projects/{project_id}/identities"),
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    assert "already exists" in second_response.json()["detail"]


def test_replace_identity(
    client: TestClient,
) -> None:
    """An identity profile should be replaceable."""

    project_id = create_project(client)

    create_response = client.post(
        (f"/api/v1/projects/{project_id}/identities"),
        json={
            "name": "Anonymous User",
            "role": "guest",
            "auth_type": "none",
            "secret_source": "environment",
            "enabled": True,
        },
    )

    identity_id = create_response.json()["id"]

    update_response = client.put(
        (f"/api/v1/projects/{project_id}/identities/{identity_id}"),
        json={
            "name": "Customer Bob",
            "description": ("Authenticated customer identity."),
            "role": "customer",
            "tenant": "tenant-b",
            "department": "finance",
            "auth_type": "bearer",
            "secret_source": "environment",
            "secret_reference": ("ACCESSMATRIX_BOB_TOKEN"),
            "enabled": False,
        },
    )

    assert update_response.status_code == 200

    identity = update_response.json()

    assert identity["name"] == "Customer Bob"
    assert identity["role"] == "customer"
    assert identity["tenant"] == "tenant-b"
    assert identity["department"] == "finance"
    assert identity["auth_type"] == "bearer"

    assert identity["secret_reference"] == "ACCESSMATRIX_BOB_TOKEN"

    assert identity["enabled"] is False


def test_identity_cannot_be_read_from_another_project(
    client: TestClient,
) -> None:
    """Identity access must remain scoped to its project."""

    first_project_id = create_project(
        client,
        "First Project",
    )

    second_project_id = create_project(
        client,
        "Second Project",
    )

    create_response = client.post(
        (f"/api/v1/projects/{first_project_id}/identities"),
        json={
            "name": "Scoped Identity",
            "role": "customer",
            "auth_type": "none",
            "secret_source": "environment",
            "enabled": True,
        },
    )

    identity_id = create_response.json()["id"]

    response = client.get(f"/api/v1/projects/{second_project_id}/identities/{identity_id}")

    assert response.status_code == 404


def test_delete_identity(
    client: TestClient,
) -> None:
    """An identity profile should be removable."""

    project_id = create_project(client)

    create_response = client.post(
        (f"/api/v1/projects/{project_id}/identities"),
        json={
            "name": "Temporary Identity",
            "role": "temporary",
            "auth_type": "none",
            "secret_source": "environment",
            "enabled": True,
        },
    )

    identity_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/projects/{project_id}/identities/{identity_id}")

    assert delete_response.status_code == 204

    read_response = client.get(f"/api/v1/projects/{project_id}/identities/{identity_id}")

    assert read_response.status_code == 404
