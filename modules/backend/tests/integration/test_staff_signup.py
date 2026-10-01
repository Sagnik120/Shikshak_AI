"""Staff (admin / teacher) sign-up is a separate form gated by an access code."""
import uuid


def _body(**over):
    body = {"full_name": "Staff Person", "email": f"s_{uuid.uuid4().hex[:6]}@example.com",
            "password": "Staff#12345", "role": "admin", "access_code": "SHIKSHAK-ADMIN"}
    body.update(over)
    return body


def test_wrong_code_is_refused(client):
    r = client.post("/api/v1/auth/signup-staff", json=_body(access_code="guess"))
    assert r.status_code == 403


def test_staff_signup_creates_an_admin_who_can_open_the_portal(client, monkeypatch):
    monkeypatch.delenv("ADMIN_SIGNUP_CODE", raising=False)
    body = _body()
    r = client.post("/api/v1/auth/signup-staff", json=body)
    assert r.status_code == 201, r.text
    tok = client.post("/api/v1/auth/verify-email", json={"email": body["email"], "code": r.json()["dev_otp"]}).json()
    assert tok["user"]["role"] == "admin"
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    assert client.get("/api/v1/admin/overview", headers=h).status_code == 200


def test_teacher_role_and_configured_code(client, monkeypatch):
    monkeypatch.setenv("ADMIN_SIGNUP_CODE", "school-42")
    assert client.post("/api/v1/auth/signup-staff", json=_body(role="teacher")).status_code == 403
    r = client.post("/api/v1/auth/signup-staff", json=_body(role="teacher", access_code="school-42"))
    assert r.status_code == 201


def test_student_signup_can_never_choose_a_role(client):
    body = {"full_name": "Sneaky", "email": f"x_{uuid.uuid4().hex[:6]}@example.com",
            "password": "Sneaky#12345", "role": "admin"}
    r = client.post("/api/v1/auth/signup", json=body)
    tok = client.post("/api/v1/auth/verify-email", json={"email": body["email"], "code": r.json()["dev_otp"]}).json()
    assert tok["user"]["role"] == "student"


def test_closed_in_production_without_a_code(client, monkeypatch):
    from modules.backend.src.config import settings
    monkeypatch.delenv("ADMIN_SIGNUP_CODE", raising=False)
    monkeypatch.setattr(type(settings), "environment", "production", raising=False)
    assert settings.admin_signup_code == ""
    r = client.post("/api/v1/auth/signup-staff", json=_body())
    assert r.status_code == 403
