"""Test fixtures: an isolated SQLite database per test, plus a signed-in client."""
import os
import tempfile
from pathlib import Path

import pytest

# Point every setting at a throwaway location BEFORE the app imports settings.
_TMP = Path(tempfile.mkdtemp(prefix="shikshak_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["SECRET_KEY"] = "test-secret-key-not-used-in-production"
os.environ["MEDIA_ROOT"] = str(_TMP / "media")
os.environ["UPLOAD_ROOT"] = str(_TMP / "uploads")
os.environ["EMAIL_DEV_FALLBACK"] = "true"
os.environ["EXPOSE_DEV_OTP"] = "true"
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["OTP_RESEND_COOLDOWN_SEC"] = "0"
os.environ["SEED_DEFAULT_USERS"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from modules.backend.src.db.base import Base, SessionLocal, engine, init_db  # noqa: E402
from modules.backend.src.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_database():
    """Recreate every table so tests never observe each other's rows."""
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


DEFAULT_PASSWORD = "Shikshak2026"


@pytest.fixture
def signup_payload():
    return {
        "full_name": "Test Learner",
        "email": "learner@example.com",
        "password": DEFAULT_PASSWORD,
        "grade": "Class 10",
        "board": "CBSE",
    }


@pytest.fixture
def verified_user(client, signup_payload):
    """Register and verify an account, returning its tokens and profile."""
    signup = client.post("/api/v1/auth/signup", json=signup_payload)
    assert signup.status_code == 201, signup.text
    code = signup.json()["dev_otp"]
    assert code, "dev_otp must be exposed while SMTP is unconfigured"

    verified = client.post(
        "/api/v1/auth/verify-email",
        json={"email": signup_payload["email"], "code": code},
    )
    assert verified.status_code == 200, verified.text
    return verified.json()


@pytest.fixture
def auth_headers(verified_user):
    return {"Authorization": f"Bearer {verified_user['access_token']}"}
