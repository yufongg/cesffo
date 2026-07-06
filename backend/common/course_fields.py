"""Shared accessors for the loosely-typed JSON fields on a Course.

summary and level live inside the ``content`` / ``prerequirements`` JSON blobs,
and ``tags`` is a free-form JSON list. These helpers were previously copy-pasted
into the course, cart and learn routers; centralising them keeps the "be strict
about what the DB might hold" behaviour identical everywhere.
"""

from typing import List, Optional

from sqlalchemy import select

from model.models import User


def instructor_names(session, courses) -> dict:
    #* Map instructor_id -> username for a batch of courses in one query (avoids N+1 lookups).
    ids = {course.instructor_id for course in courses if course.instructor_id}
    if not ids:
        return {}
    rows = session.execute(select(User.user_id, User.username).where(User.user_id.in_(ids))).all()
    return {user_id: username for user_id, username in rows}


def course_summary(course) -> Optional[str]:
    #* content is JSON: only return summary when it's actually a dict holding a string.
    content = course.content if isinstance(course.content, dict) else {}
    summary = content.get("summary")
    return summary if isinstance(summary, str) else None


def course_level(course) -> Optional[str]:
    #* prerequirements is JSON: only return level when it's actually a dict holding a string.
    prereq = course.prerequirements if isinstance(course.prerequirements, dict) else {}
    level = prereq.get("level")
    return level if isinstance(level, str) else None


def course_tags(course) -> List[str]:
    #* tags is a free-form JSON list; coerce scalar entries to str and drop anything exotic.
    if not isinstance(course.tags, list):
        return []
    return [str(t) for t in course.tags if isinstance(t, (str, int, float))]
