"""Integration tests for the AccessMatrix health API and React GUI."""

from fastapi.testclient import TestClient

from accessmatrix.api.app import create_app


def test_health_endpoint_returns_operational_status() -> None:
    """The health endpoint should report a working application."""

    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["application"] == "AccessMatrix"
    assert payload["version"]
    assert payload["python_version"]
    assert payload["platform"]
    assert payload["data_directory"]


def test_root_page_loads() -> None:
    """The root route should return the React application shell."""

    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>AccessMatrix</title>" in response.text
    assert '<div id="root"></div>' in response.text
    assert "/assets/" in response.text


def test_frontend_routes_return_single_page_application() -> None:
    """React routes should return the same frontend application shell."""

    client = TestClient(create_app())

    response = client.get("/projects")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>AccessMatrix</title>" in response.text
    assert '<div id="root"></div>' in response.text
    assert "/assets/" in response.text


def test_unknown_api_routes_return_not_found() -> None:
    """Unknown API routes must not return the React application."""

    client = TestClient(create_app())

    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"


def test_gui_javascript_asset_is_available() -> None:
    """The compiled JavaScript bundle should be served by FastAPI."""

    client = TestClient(create_app())

    root_response = client.get("/")

    assert root_response.status_code == 200

    html = root_response.text
    asset_marker = 'src="/assets/'

    assert asset_marker in html

    asset_start = html.index(asset_marker) + len('src="')
    asset_end = html.index('"', asset_start)
    asset_path = html[asset_start:asset_end]

    asset_response = client.get(asset_path)

    assert asset_response.status_code == 200
    assert "javascript" in asset_response.headers["content-type"]


def test_gui_css_asset_is_available() -> None:
    """The compiled CSS bundle should be served by FastAPI."""

    client = TestClient(create_app())

    root_response = client.get("/")

    assert root_response.status_code == 200

    html = root_response.text
    asset_marker = 'href="/assets/'

    assert asset_marker in html

    asset_start = html.index(asset_marker) + len('href="')
    asset_end = html.index('"', asset_start)
    asset_path = html[asset_start:asset_end]

    asset_response = client.get(asset_path)

    assert asset_response.status_code == 200
    assert "text/css" in asset_response.headers["content-type"]
