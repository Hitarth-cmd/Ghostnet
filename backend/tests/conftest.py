from __future__ import annotations

import os
import tempfile

# Set the test database URL BEFORE any `app.*` module is imported anywhere
# in the test session, so the engine created at import time in
# app/database.py points at this isolated file for the whole run.
_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "ghostnet_pytest.db")
if os.path.exists(_TEST_DB_PATH):
    os.remove(_TEST_DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ["JOB_BACKEND"] = "inline"
os.environ["DATA_MODE"] = "demo"
os.environ["MODEL_PROVIDER"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["VECTOR_STORE"] = "memory"
os.environ["EMBEDDING_PROVIDER"] = "hashing"

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def db_session():
    """A session-scoped SQLAlchemy session bound to the shared test database."""
    from app.database import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def client():
    """A TestClient for the full FastAPI app, bound to the shared test database."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
