import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment database before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SKYOPS_ENV"] = "testing"

import cloud.app.database as db_module
import cloud.app.models  # Ensure all ORM models are registered on Base.metadata
from cloud.app.database import Base, get_db
from cloud.app.auth import get_current_identity
from cloud.app.main import app


@pytest.fixture(scope="function", autouse=True)
def setup_test_db():
    # Use static pool for SQLite in-memory so all connections share the same DB in tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Override engine in db_module
    db_module.engine = engine
    db_module.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_identity] = lambda: {"type": "agent", "sub": "agent", "role": "agent"}

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client():
    with TestClient(app) as test_client:
        yield test_client
