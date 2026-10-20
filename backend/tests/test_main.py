"""
Unit and integration test suite for the core backend entrypoint (app/main.py).

This module validates:
- The health/root check endpoint ('/').
- Application metadata (API title, version, and description).
- Cross-Origin Resource Sharing (CORS) header configuration for trusted origins.
- Correct mounting and prefix registration of domain API routers.
- Proper handling of non-existent endpoints (404 Not Found).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """
    FastAPI TestClient fixture to perform synchronous HTTP requests against the app instance.
    """
    return TestClient(app)


def test_read_root_returns_200_and_message(client):
    """
    Verify that the root GET / endpoint returns an HTTP 200 status code
    and the expected health-check welcome payload confirming the backend is running.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data == {"message": "NIDiKo backend is running."}


def test_app_metadata():
    """
    Verify that the FastAPI application metadata is correctly configured
    with the expected service title, version, and project description.
    """
    assert app.title == "NIDiKo API"
    assert app.version == "0.1.0"
    assert "NIDiKo" in app.description


def test_cors_middleware_allows_configured_origins(client):
    """
    Ensure the CORS middleware properly responds to preflight OPTIONS requests
    from whitelisted local origins (e.g., http://localhost:5173 for Vite dev server)
    and includes appropriate access-control headers.
    """
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_registered_api_routes():
    """
    Validate that all essential domain routers and AI assistant endpoints
    are properly mounted with the '/api' route prefix on the FastAPI application instance.
    """
    routes = [route.path for route in app.routes]

    # Verify that all required domain endpoints are registered in the routing table
    expected_paths = [
        "/",
        "/api/search",
        "/api/learning-paths",
        "/api/modules",
        "/api/learning-units",
        "/api/users",
        "/api/user-progress",
    ]
    for path in expected_paths:
        assert any(r.startswith(path) for r in routes), f"Missing registered route for prefix: {path}"


def test_not_found_returns_404(client):
    """
    Verify that requesting an unregistered endpoint returns an HTTP 404 Not Found error.
    """
    response = client.get("/api/non-existent-endpoint-12345")
    assert response.status_code == 404
