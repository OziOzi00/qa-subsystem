"""Test fixtures for QA subsystem integration tests.

These tests run against a live server (http://127.0.0.1:8000).
Start the server first:
    uvicorn app.main:app --host 127.0.0.1 --port 8000
"""

from uuid import uuid4

import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000/api"


@pytest.fixture(scope="session")
def client():
    """Provide an httpx client pointed at the running server."""
    with httpx.Client(base_url=BASE_URL) as c:
        yield c


@pytest.fixture
def new_qa_log_uuid() -> str:
    """Return a fresh UUID for each test that needs a unique qaLogId."""
    return str(uuid4())


@pytest.fixture
def valid_user_id() -> int:
    """Return a user_id that exists in the public MySQL users table."""
    return 9


@pytest.fixture
def valid_admin_id() -> int:
    """Return an admin_user id that exists in the public MySQL admin_users table."""
    return 1
