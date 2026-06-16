"""End-to-end test for the FR-06/FR-07 demo-content seed (seed_course_content.py).

Requires a live database (same convention as tests/database_test.py) — run via
the dockerized integration suite: `docker compose exec -T backend pytest tests`.
Assumes seed.py has already populated the base courses/users/enrollments.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from main import app
from db.db import get_db_session
from model.models import Course, Module, User
from seed_course_content import seed_course_content

client = TestClient(app)

DEMO_COURSE_NAME = "Budgeting 101: Take Control of Your Money"
DEMO_STUDENT_EMAIL = "student@cesffo.io"
DEMO_STUDENT_PASSWORD = "LearnMoney#2026"


@pytest.fixture(scope="module", autouse=True)
def ensure_seeded():
    with get_db_session() as session:
        if not session.scalar(select(User).where(User.username == "prof_lena")):
            pytest.skip("base seed.py data not present — run `python seed.py` first")
    seed_course_content()


def test_seed_is_idempotent():
    with get_db_session() as session:
        before = len(session.scalars(select(Module.module_id)).all())
    seed_course_content()  # run again
    with get_db_session() as session:
        after = len(session.scalars(select(Module.module_id)).all())
    assert before == after


def test_enrolled_student_can_open_seeded_course_and_see_quiz():
    login = client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_STUDENT_EMAIL, "password": DEMO_STUDENT_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with get_db_session() as session:
        course = session.scalar(select(Course).where(Course.course_name == DEMO_COURSE_NAME))
        assert course is not None
        course_id_hex = course.course_id.hex

    response = client.get(f"/api/v1/courses/{course_id_hex}/learn", headers=headers)
    assert response.status_code == 200
    body = response.json()

    module_titles = [m["title"] for m in body["modules"]]
    assert "What Is a Budget?" in module_titles
    assert "Budgeting Quiz" in module_titles

    quiz = next(m for m in body["modules"] if m["title"] == "Budgeting Quiz")
    assert len(quiz["activities"]) == 3
    activity_types = {a["activity_type"] for a in quiz["activities"]}
    assert activity_types == {"mcq_single", "mcq_multi", "short_answer"}

    # Answer-key protection: no option in the response carries is_correct,
    # and no activity exposes correct_answers.
    for activity in quiz["activities"]:
        assert "correct_answers" not in activity
        for option in activity.get("options", []):
            assert "is_correct" not in option
