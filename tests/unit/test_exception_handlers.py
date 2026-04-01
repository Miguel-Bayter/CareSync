"""Unit tests for FastAPI exception handlers.

Each test triggers a specific handler by calling a dedicated route on a
minimal test application that raises the target exception type.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exception_handlers import register_exception_handlers
from app.core.exceptions import (
    ConflictError,
    DomainValidationError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
)


def _make_app() -> FastAPI:
    """Build a minimal app with all exception handlers registered."""
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/not-found")
    def raise_not_found():
        raise NotFoundError("Thing not found")

    @test_app.get("/conflict")
    def raise_conflict():
        raise ConflictError("Already exists")

    @test_app.get("/domain-validation")
    def raise_domain_validation():
        raise DomainValidationError("Rule violated")

    @test_app.get("/forbidden")
    def raise_forbidden():
        raise ForbiddenError("No access")

    @test_app.get("/external-service")
    def raise_external_service():
        raise ExternalServiceError(service="TestService")

    @test_app.get("/unhandled")
    def raise_unhandled():
        raise RuntimeError("Something went very wrong")

    return test_app


@pytest.fixture(scope="module")
def handler_client() -> TestClient:
    return TestClient(_make_app(), raise_server_exceptions=False)


class TestNotFoundHandler:
    def test_returns_404(self, handler_client: TestClient) -> None:
        r = handler_client.get("/not-found")
        assert r.status_code == 404

    def test_error_body_code(self, handler_client: TestClient) -> None:
        r = handler_client.get("/not-found")
        assert r.json()["error"]["code"] == "NOT_FOUND"

    def test_error_body_message(self, handler_client: TestClient) -> None:
        r = handler_client.get("/not-found")
        assert "Thing not found" in r.json()["error"]["message"]


class TestConflictHandler:
    def test_returns_409(self, handler_client: TestClient) -> None:
        r = handler_client.get("/conflict")
        assert r.status_code == 409

    def test_error_body_code(self, handler_client: TestClient) -> None:
        r = handler_client.get("/conflict")
        assert r.json()["error"]["code"] == "CONFLICT"

    def test_error_body_message(self, handler_client: TestClient) -> None:
        r = handler_client.get("/conflict")
        assert "Already exists" in r.json()["error"]["message"]


class TestDomainValidationHandler:
    def test_returns_422(self, handler_client: TestClient) -> None:
        r = handler_client.get("/domain-validation")
        assert r.status_code == 422

    def test_error_body_code(self, handler_client: TestClient) -> None:
        r = handler_client.get("/domain-validation")
        assert r.json()["error"]["code"] == "DOMAIN_VALIDATION_ERROR"


class TestForbiddenHandler:
    def test_returns_403(self, handler_client: TestClient) -> None:
        r = handler_client.get("/forbidden")
        assert r.status_code == 403

    def test_error_body_code(self, handler_client: TestClient) -> None:
        r = handler_client.get("/forbidden")
        assert r.json()["error"]["code"] == "FORBIDDEN"


class TestExternalServiceHandler:
    def test_returns_503(self, handler_client: TestClient) -> None:
        r = handler_client.get("/external-service")
        assert r.status_code == 503

    def test_error_body_code(self, handler_client: TestClient) -> None:
        r = handler_client.get("/external-service")
        assert r.json()["error"]["code"] == "EXTERNAL_SERVICE_ERROR"

    def test_service_name_in_message(self, handler_client: TestClient) -> None:
        r = handler_client.get("/external-service")
        assert "TestService" in r.json()["error"]["message"]


class TestGenericHandler:
    def test_returns_500(self, handler_client: TestClient) -> None:
        r = handler_client.get("/unhandled")
        assert r.status_code == 500

    def test_error_body_code(self, handler_client: TestClient) -> None:
        r = handler_client.get("/unhandled")
        assert r.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"

    def test_error_body_safe_message(self, handler_client: TestClient) -> None:
        # Internal details must NOT leak to the client
        r = handler_client.get("/unhandled")
        assert "unexpected error" in r.json()["error"]["message"].lower()
        assert "Something went very wrong" not in r.json()["error"]["message"]
