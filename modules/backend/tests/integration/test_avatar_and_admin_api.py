"""Profile photos / avatars, and the admin portal's access rules and shapes."""
from modules.backend.src.db.base import SessionLocal
from modules.backend.src.db.models import User

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def test_upload_photo_then_pick_avatar_replaces_it(client, auth_headers):
    r = client.post("/api/v1/account/avatar", headers=auth_headers,
                    files={"file": ("me.png", PNG, "image/png")})
    assert r.status_code == 200, r.text
    url = r.json()["avatar_url"]
    assert url and url.endswith(".png")
    # Public, cacheable, no auth needed for <img>.
    served = client.get(url)
    assert served.status_code == 200 and served.content == PNG
    assert "immutable" in served.headers.get("cache-control", "")

    r = client.patch("/api/v1/account/profile", headers=auth_headers, json={"avatar_choice": "kite-blue"})
    assert r.status_code == 200
    assert r.json()["avatar_choice"] == "kite-blue" and r.json()["avatar_url"] is None
    assert client.get(url).status_code == 404  # old photo file removed


def test_photo_must_really_be_an_image_and_small(client, auth_headers):
    fake = client.post("/api/v1/account/avatar", headers=auth_headers,
                       files={"file": ("x.png", b"<script>alert(1)</script>", "image/png")})
    assert fake.status_code == 415
    big = client.post("/api/v1/account/avatar", headers=auth_headers,
                      files={"file": ("big.png", PNG + b"\x00" * (4 * 1024 * 1024), "image/png")})
    assert big.status_code == 413


def test_avatar_file_names_cannot_traverse(client):
    assert client.get("/api/v1/account/avatar/file/..%2F..%2Fsecret.png").status_code == 404
    assert client.get("/api/v1/account/avatar/file/abc.png").status_code == 404


def test_admin_portal_is_closed_to_students(client, auth_headers):
    assert client.get("/api/v1/admin/overview", headers=auth_headers).status_code == 403


def test_admin_endpoints_answer_for_an_admin(client, auth_headers, verified_user):
    with SessionLocal() as db:
        user = db.get(User, verified_user["user"]["id"])
        user.role = "admin"
        db.commit()
    for path, key in [
        ("/api/v1/admin/overview", "daily"),
        ("/api/v1/admin/live", "sessions"),
        ("/api/v1/admin/escalations", "escalations"),
        ("/api/v1/admin/insights", "hardest_concepts"),
        ("/api/v1/admin/quality", "llm"),
        ("/api/v1/admin/pipeline", "renders"),
        ("/api/v1/admin/learners", "learners"),
    ]:
        r = client.get(path, headers=auth_headers)
        assert r.status_code == 200, f"{path}: {r.text}"
        assert key in r.json()
    me = verified_user["user"]["id"]
    detail = client.get(f"/api/v1/admin/learners/{me}", headers=auth_headers)
    assert detail.status_code == 200 and detail.json()["learner"]["id"] == me


def test_teachers_see_teaching_views_but_not_system_ones(client, auth_headers, verified_user):
    with SessionLocal() as db:
        user = db.get(User, verified_user["user"]["id"])
        user.role = "teacher"
        db.commit()
    for path in ("overview", "live", "escalations", "insights", "learners"):
        assert client.get(f"/api/v1/admin/{path}", headers=auth_headers).status_code == 200, path
    for path in ("quality", "pipeline"):
        assert client.get(f"/api/v1/admin/{path}", headers=auth_headers).status_code == 403, path


def test_overview_tells_first_time_rescued_and_human(client, auth_headers, verified_user):
    with SessionLocal() as db:
        db.get(User, verified_user["user"]["id"]).role = "admin"
        db.commit()
    body = client.get("/api/v1/admin/overview?days=30", headers=auth_headers).json()
    assert len(body["daily"]) == 30
    assert {"right", "wrong", "rescued", "escalations", "completed", "learners"} <= set(body["daily"][0])
    f = body["funnel"]
    assert f["first_time"] + f["rescued"] + f["still_stuck"] == f["concepts_checked"]
    assert client.get("/api/v1/admin/overview?days=3", headers=auth_headers).status_code == 422


def test_journey_for_a_new_learner(client, auth_headers):
    j = client.get("/api/v1/journey", headers=auth_headers).json()
    assert j["days"] and j["days"][-1]["date"] == j["today"]
    assert j["streak"]["current"] == 0 and j["level"]["level"] == 1
    groups = {b["group"] for b in j["badges"]}
    assert {"streak", "lessons_completed", "answers", "first_lesson"} <= groups
    assert not any(b["earned"] for b in j["badges"])
    assert j["months"][-1]["month"] == j["today"][:7]
