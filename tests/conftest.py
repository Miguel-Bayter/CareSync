"""Shared pytest fixtures for unit and integration tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db

# Import all models so SQLAlchemy mapper registry resolves all string-based
# relationship references before any fixture creates tables or model instances.
import app.models.alert  # noqa: F401
import app.models.caregiver  # noqa: F401
import app.models.dose  # noqa: F401
import app.models.medication  # noqa: F401
import app.models.patient  # noqa: F401

from app.main import app as fastapi_app  # alias avoids shadowing the 'app' package

# ---------------------------------------------------------------------------
# In-memory SQLite engine — shared across the test session
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///:memory:"

_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables() -> None:
    """Create all database tables once before any test runs."""
    Base.metadata.create_all(bind=_engine)


@pytest.fixture()
def db_session() -> Session:
    """Provide a transactional database session that rolls back after each test.

    Yields:
        A SQLAlchemy Session connected to the in-memory SQLite database.
    """
    connection = _engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """Provide a TestClient with the DB dependency overridden.

    Args:
        db_session: The transactional test session.

    Yields:
        A FastAPI TestClient.
    """

    def _override_get_db() -> Session:
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c
    fastapi_app.dependency_overrides.clear()
