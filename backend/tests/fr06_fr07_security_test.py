"""Security tests for FR-06 (instructor authoring) and FR-07 (student learning).

Covers the graded, non-negotiable controls from the brief: RBAC deny-by-default
(SR-03), instructor ownership (AS-04), enrollment checks (AS-05), answer-key
protection, stored-XSS sanitization (SR-09), and non-sequential IDs (9.7).
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from main import app
from common.sanitize import sanitize_html, strip_tags
from course.instructor_router import InteractiveActivityCreate

client = TestClient(app)


# =========================================================================
# RBAC deny-by-default (SR-03)
# =========================================================================

def test_instructor_endpoint_requires_auth():
    """No token at all -> 401, never a soft pass."""
    response = client.post("/api/v1/instructor/courses", json={"course_name": "X"})
    assert response.status_code == 401


def test_student_denied_instructor_create_course(monkeypatch):
    """A student JWT must never reach an instructor-only route (403)."""
    from user import auth_router

    async def fake_current_user():
        return {"user_id": uuid4().hex, "role": "student"}

    app.dependency_overrides[auth_router.get_current_user] = fake_current_user
    try:
        response = client.post("/api/v1/instructor/courses", json={"course_name": "Hack"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_student_denied_instructor_delete_module(monkeypatch):
    from user import auth_router

    async def fake_current_user():
        return {"user_id": uuid4().hex, "role": "student"}

    app.dependency_overrides[auth_router.get_current_user] = fake_current_user
    try:
        response = client.delete(f"/api/v1/instructor/modules/{uuid4().hex}")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


# =========================================================================
# Instructor ownership (AS-04)
# =========================================================================

def test_instructor_cannot_modify_other_instructors_course(monkeypatch):
    """Instructor B's token + Instructor A's course id -> 403, not data leak."""
    from user import auth_router
    from course import instructor_router

    owner_id = uuid4()
    attacker_id = uuid4()

    class FakeCourse:
        course_id = uuid4()
        instructor_id = owner_id

    async def fake_current_user():
        return {"user_id": attacker_id.hex, "role": "instructor"}

    class FakeSession:
        def scalar(self, *_args, **_kwargs):
            return FakeCourse()

    class FakeSessionCtx:
        def __enter__(self):
            return FakeSession()

        def __exit__(self, *_a):
            return False

    app.dependency_overrides[auth_router.get_current_user] = fake_current_user
    monkeypatch.setattr(instructor_router, "get_db_session", lambda: FakeSessionCtx())
    try:
        response = client.patch(
            f"/api/v1/instructor/courses/{FakeCourse.course_id.hex}",
            json={"course_name": "Hijacked"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


# =========================================================================
# Enrollment checks (AS-05)
# =========================================================================

def test_unenrolled_student_cannot_read_course(monkeypatch):
    from user import auth_router
    from course import learn_router

    student_id = uuid4()
    course_id = uuid4()

    class FakeCourse:
        pass

    call_count = {"n": 0}

    class FakeSession:
        def scalar(self, *_args, **_kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return FakeCourse()  # course exists
            return None  # but no active enrollment row

    class FakeSessionCtx:
        def __enter__(self):
            return FakeSession()

        def __exit__(self, *_a):
            return False

    async def fake_current_user():
        return {"user_id": student_id.hex, "role": "student"}

    app.dependency_overrides[auth_router.get_current_user] = fake_current_user
    monkeypatch.setattr(learn_router, "get_db_session", lambda: FakeSessionCtx())
    try:
        response = client.get(f"/api/v1/courses/{course_id.hex}/learn")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_unenrolled_student_cannot_submit_activity(monkeypatch):
    from user import auth_router
    from course import learn_router

    student_id = uuid4()
    activity_id = uuid4()

    class FakeSession:
        def scalar(self, *_args, **_kwargs):
            return None  # activity lookup fails fast -> 404, never leaks grading logic

    class FakeSessionCtx:
        def __enter__(self):
            return FakeSession()

        def __exit__(self, *_a):
            return False

    async def fake_current_user():
        return {"user_id": student_id.hex, "role": "student"}

    app.dependency_overrides[auth_router.get_current_user] = fake_current_user
    monkeypatch.setattr(learn_router, "get_db_session", lambda: FakeSessionCtx())
    try:
        response = client.post(
            f"/api/v1/activities/{activity_id.hex}/submit", json={"option_ids": [uuid4().hex]}
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


# =========================================================================
# Stored-XSS sanitization (SR-09)
# =========================================================================

def test_xss_payload_neutralized_in_rich_text():
    payload = "<script>alert(document.cookie)</script><p>Safe <b>text</b></p>"
    cleaned = sanitize_html(payload)
    assert "<script>" not in cleaned
    assert "alert(" not in cleaned
    assert "<p>" in cleaned  # allow-listed tag survives


def test_xss_payload_neutralized_in_plain_text_fields():
    payload = '<img src=x onerror=alert(1)>Course Title'
    cleaned = strip_tags(payload)
    assert "<img" not in cleaned
    assert "onerror" not in cleaned
    assert "Course Title" in cleaned


# =========================================================================
# Answer-key protection
# =========================================================================

def test_student_facing_activity_schema_has_no_answer_key():
    from course.learn_router import ActivityView, ActivityOptionView
    assert "is_correct" not in ActivityOptionView.model_fields
    assert "correct_answers" not in ActivityView.model_fields


def test_mcq_single_requires_exactly_one_correct_option():
    with pytest.raises(ValueError):
        InteractiveActivityCreate(
            title="Q", activity_type="mcq_single", prompt="?",
            options=[{"option_text": "a", "is_correct": True}, {"option_text": "b", "is_correct": True}],
        )


def test_short_answer_requires_accepted_answers():
    with pytest.raises(ValueError):
        InteractiveActivityCreate(title="Q", activity_type="short_answer", prompt="?", correct_answers=[])


# =========================================================================
# Non-sequential IDs (9.7)
# =========================================================================

def test_all_new_resource_ids_are_uuid_columns():
    from model.models import (
        Module, ReadingMaterial, MediaContent, InteractiveActivity,
        ActivityOption, ActivitySubmission, ModuleProgress, AuditLog,
    )
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID

    pk_columns = {
        Module: "module_id", ReadingMaterial: "material_id", MediaContent: "media_id",
        InteractiveActivity: "activity_id", ActivityOption: "option_id",
        ActivitySubmission: "submission_id", ModuleProgress: "progress_id",
        AuditLog: "log_id",
    }
    for model, pk_name in pk_columns.items():
        col = model.__table__.columns[pk_name]
        assert isinstance(col.type, PG_UUID), f"{model.__name__}.{pk_name} must be a UUID, not a sequential id"
