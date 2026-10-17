"""Integration tests for identity credential readiness."""

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
from accessmatrix.api.routes.identities import (
    get_credential_resolver,
)
from accessmatrix.persistence.database import (
    Base,
    get_session,
)
from accessmatrix.persistence.storage import (
    get_storage_root,
)
from accessmatrix.security.credentials import (
    CredentialResolver,
)

AVAILABLE_SECRET_VALUE = "integration-secret-value"


@pytest.fixture
def client(
    tmp_path: Path,
) -> Iterator[TestClient]:
    """Create an isolated credential-status API client."""

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

    def override_credential_resolver() -> CredentialResolver:
        return CredentialResolver(
            environment={
                "ACCESSMATRIX_AVAILABLE_TOKEN": (AVAILABLE_SECRET_VALUE),
            }
        )

    application = create_app(
        initialize_storage=False,
    )

    application.dependency_overrides[get_session] = override_session

    application.dependency_overrides[get_storage_root] = override_storage

    application.dependency_overrides[get_credential_resolver] = override_credential_resolver

    with TestClient(application) as test_client:
        yield test_client

    engine.dispose()


def create_project(
    client: TestClient,
) -> str:
    """Create a project and return its identifier."""

    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Credential Status API",
        },
    )

    assert response.status_code == 201

    return str(response.json()["id"])


def create_identity(
    client: TestClient,
    project_id: str,
    *,
    name: str,
    auth_type: str,
    secret_reference: str | None = None,
    enabled: bool = True,
) -> str:
    """Create an identity and return its identifier."""

    response = client.post(
        (f"/api/v1/projects/{project_id}/identities"),
        json={
            "name": name,
            "role": "tester",
            "auth_type": auth_type,
            "secret_source": "environment",
            "secret_reference": (secret_reference),
            "enabled": enabled,
        },
    )

    assert response.status_code == 201

    return str(response.json()["id"])


def test_available_credential_is_ready(
    client: TestClient,
) -> None:
    """An available reference should produce a ready status."""

    project_id = create_project(client)

    identity_id = create_identity(
        client,
        project_id,
        name="Ready Identity",
        auth_type="bearer",
        secret_reference=("ACCESSMATRIX_AVAILABLE_TOKEN"),
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/identities/{identity_id}/credential-status"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["identity_id"] == identity_id
    assert payload["identity_name"] == "Ready Identity"
    assert payload["role"] == "tester"
    assert payload["enabled"] is True
    assert payload["ready"] is True

    assert payload["references"] == [
        {
            "field_name": "secret_reference",
            "reference": ("ACCESSMATRIX_AVAILABLE_TOKEN"),
            "source": "environment",
            "available": True,
        }
    ]

    assert AVAILABLE_SECRET_VALUE not in response.text


def test_missing_credential_is_not_ready(
    client: TestClient,
) -> None:
    """An unavailable reference should not be ready."""

    project_id = create_project(client)

    identity_id = create_identity(
        client,
        project_id,
        name="Missing Identity",
        auth_type="bearer",
        secret_reference=("ACCESSMATRIX_MISSING_TOKEN"),
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/identities/{identity_id}/credential-status"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["ready"] is False

    assert payload["references"][0]["available"] is False

    assert "unavailable" in (payload["message"].lower())


def test_anonymous_identity_is_ready(
    client: TestClient,
) -> None:
    """Anonymous identities should require no credential."""

    project_id = create_project(client)

    identity_id = create_identity(
        client,
        project_id,
        name="Anonymous",
        auth_type="none",
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/identities/{identity_id}/credential-status"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["ready"] is True
    assert payload["references"] == []

    assert "no authentication credentials" in payload["message"].lower()


def test_disabled_identity_is_not_ready(
    client: TestClient,
) -> None:
    """Disabled identities should never be scan-ready."""

    project_id = create_project(client)

    identity_id = create_identity(
        client,
        project_id,
        name="Disabled Identity",
        auth_type="bearer",
        secret_reference=("ACCESSMATRIX_AVAILABLE_TOKEN"),
        enabled=False,
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/identities/{identity_id}/credential-status"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["enabled"] is False
    assert payload["ready"] is False

    assert payload["message"] == "The identity is disabled."

    assert AVAILABLE_SECRET_VALUE not in response.text


def test_project_credential_status_summary(
    client: TestClient,
) -> None:
    """The project endpoint should summarize every identity."""

    project_id = create_project(client)

    create_identity(
        client,
        project_id,
        name="Anonymous",
        auth_type="none",
    )

    create_identity(
        client,
        project_id,
        name="Ready Customer",
        auth_type="bearer",
        secret_reference=("ACCESSMATRIX_AVAILABLE_TOKEN"),
    )

    create_identity(
        client,
        project_id,
        name="Missing Customer",
        auth_type="bearer",
        secret_reference=("ACCESSMATRIX_MISSING_TOKEN"),
    )

    create_identity(
        client,
        project_id,
        name="Disabled Customer",
        auth_type="bearer",
        secret_reference=("ACCESSMATRIX_AVAILABLE_TOKEN"),
        enabled=False,
    )

    response = client.get(f"/api/v1/projects/{project_id}/identities/credential-statuses")

    assert response.status_code == 200

    payload = response.json()

    assert payload["project_id"] == project_id
    assert payload["total_count"] == 4
    assert payload["ready_count"] == 2
    assert payload["unready_count"] == 2
    assert payload["disabled_count"] == 1
    assert len(payload["statuses"]) == 4

    status_names = {credential_status["identity_name"] for credential_status in payload["statuses"]}

    assert status_names == {
        "Anonymous",
        "Ready Customer",
        "Missing Customer",
        "Disabled Customer",
    }

    assert AVAILABLE_SECRET_VALUE not in response.text
