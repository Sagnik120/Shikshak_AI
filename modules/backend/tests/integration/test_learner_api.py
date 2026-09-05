import pytest
from modules.backend.src.persistence.in_memory import learner_repo, report_repo
from modules.backend.src.schemas.contract import LearnerProfile, AssessmentReport


def test_get_learner_profile_success(client):
    """Verifies retrieval of an existing LearnerProfile (Contract §13)."""
    profile = LearnerProfile(
        learner_id="learner_007",
        history=[],
        strong_concepts=["Calculus", "Linear Algebra"],
        weak_concepts=["Probability"],
        current_learning_path=["Advanced Physics"],
        preferred_language="en",
        preferred_level="advanced"
    )
    learner_repo.save_profile(profile)

    headers = {"Authorization": "Bearer any_token"}
    resp = client.get("/api/v1/learners/learner_007/profile", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["learner_id"] == "learner_007"
    assert "Calculus" in data["strong_concepts"]


def test_get_learner_profile_not_found(client):
    """Verifies 404 returned for unknown learner_id."""
    headers = {"Authorization": "Bearer any_token"}
    resp = client.get("/api/v1/learners/unknown_learner/profile", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Learner profile not found"


def test_get_assessment_report_success(client):
    """Verifies retrieval of an existing AssessmentReport (Contract §12)."""
    report = AssessmentReport(
        lesson_id="lesson_thermo_1",
        score_pct=85.0,
        strong_areas=["First Law of Thermodynamics"],
        weak_areas=["Carnot Engine Efficiency"],
        recommended_next=["Entropy & Second Law"],
        narrative_feedback="Solid grasp of heat transfer basics. Review Carnot cycle derivations."
    )
    report_repo.save_report("learner_007", report)

    headers = {"Authorization": "Bearer any_token"}
    resp = client.get("/api/v1/learners/learner_007/report/lesson_thermo_1", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["lesson_id"] == "lesson_thermo_1"
    assert data["score_pct"] == 85.0


def test_get_assessment_report_not_found(client):
    """Verifies 404 returned for unknown lesson report."""
    headers = {"Authorization": "Bearer any_token"}
    resp = client.get("/api/v1/learners/learner_007/report/nonexistent_lesson", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Assessment report not found"


def test_learner_endpoints_require_auth(client):
    """Verifies 401 when Authorization header is absent."""
    resp = client.get("/api/v1/learners/learner_007/profile")
    assert resp.status_code == 401
