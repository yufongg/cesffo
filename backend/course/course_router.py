from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func, or_, and_

from db.db import get_db_session
from model.models import Course, CourseEnrollment, User
from common.security import parse_uid as _parse_uid
from common.course_fields import (
    course_summary, course_level, course_tags, instructor_names as _instructor_names,
)
from user.auth_router import get_current_user

router = APIRouter(prefix="/api/v1/courses", tags=["Courses"])

ALLOWED_SORTS = frozenset({"popular", "newest", "name"})
MAX_SEARCH_LEN = 80
MAX_TAG_LEN = 50
RECOMMENDED_LIMIT = 6
LEADERBOARD_LIMIT = 10

class CourseCard(BaseModel):
    course_id: str
    course_name: str
    instructor: Optional[str] = None
    tags: List[str] = []
    summary: Optional[str] = None
    level: Optional[str] = None
    xp_reward: int = 0
    price_cents: int = 0
    currency: str = "SGD"
    enrollment_count: int = 0
    is_enrolled: bool = False
    progress: Optional[float] = None

class OverviewResponse(BaseModel):
    enrolled: List[CourseCard]
    recommended: List[CourseCard]



class UserScore(BaseModel):
    rank: int
    username: str
    xp: int
    level: int
    is_you: bool = False


class ScoresResponse(BaseModel):
    leaderboard: List[UserScore]  # top N learners on the same level


# --- Helpers ---
def _like_escape(term: str) -> str:
    """Escape LIKE/ILIKE wildcards so user input is matched literally."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _enrollment_counts(session) -> dict:
    rows = session.execute(
        select(CourseEnrollment.course_id, func.count())
        .where(CourseEnrollment.dropped.is_(False))
        .group_by(CourseEnrollment.course_id)
    ).all()
    return {course_id: count for course_id, count in rows}


def _my_enrollments(session, uid: UUID):
    rows = session.execute(
        select(CourseEnrollment.course_id, CourseEnrollment.progress)
        .where(
            CourseEnrollment.student_id == uid,
            CourseEnrollment.dropped.is_(False),
        )
    ).all()
    enrolled = {course_id for course_id, _ in rows}
    progress = {course_id: prog for course_id, prog in rows}
    return enrolled, progress


def _current_user_row(session, uid: UUID) -> User:
    """Load the authenticated user from the DB (also validates they still exist)."""
    user = session.scalars(select(User).where(User.user_id == uid)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _rank_at_level(session, user: User) -> int:
    """1-based rank of `user` among non-deleted learners on the same level,
    ordered by XP desc then username asc (matches the leaderboard ordering)."""
    ahead = session.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.level == user.level,
            User.is_deleted.is_(False),
            or_(
                User.xp > user.xp,
                and_(User.xp == user.xp, User.username < user.username),
            ),
        )
    )
    return (ahead or 0) + 1


def _build_card(course, *, counts, enrolled_ids, progress_map, instructor_name) -> CourseCard:
    cid = course.course_id
    return CourseCard(
        course_id=cid.hex,
        course_name=course.course_name,
        instructor=instructor_name,
        tags=course_tags(course),
        summary=course_summary(course),
        level=course_level(course),
        xp_reward=getattr(course, "xp_reward", 0) or 0,
        price_cents=getattr(course, "price_cents", 0) or 0,
        currency=getattr(course, "currency", "SGD") or "SGD",
        enrollment_count=counts.get(cid, 0),
        is_enrolled=cid in enrolled_ids,
        progress=progress_map.get(cid),
    )


# --- Endpoints ---
@router.get("/overview", response_model=OverviewResponse)
async def overview(request: Request, current_user: dict = Depends(get_current_user)):
    """Data for the post-login landing page: the user's enrolled (owned) courses
    plus popular courses they are *not* enrolled in."""
    uid = _parse_uid(current_user)
    with get_db_session() as session:
        courses = session.scalars(select(Course)).all()
        counts = _enrollment_counts(session)
        enrolled_ids, progress_map = _my_enrollments(session, uid)
        names = _instructor_names(session, courses)

        enrolled_cards, rec_pool = [], []
        for course in courses:
            card = _build_card(
                course,
                counts=counts,
                enrolled_ids=enrolled_ids,
                progress_map=progress_map,
                instructor_name=names.get(course.instructor_id),
            )
            (enrolled_cards if card.is_enrolled else rec_pool).append(card)

        rec_pool.sort(key=lambda c: c.enrollment_count, reverse=True)
        recommended = rec_pool[:RECOMMENDED_LIMIT]

    return OverviewResponse(enrolled=enrolled_cards, recommended=recommended)


@router.get("/scores", response_model=ScoresResponse)
async def scores(request: Request, current_user: dict = Depends(get_current_user)):
    """Leaderboard for the current user: the top learners on their level, plus
    the user's own standing so they always know where they rank."""
    uid = _parse_uid(current_user)
    with get_db_session() as session:
        me = _current_user_row(session, uid)

        top = session.scalars(
            select(User)
            .where(User.level == me.level, User.is_deleted.is_(False))
            .order_by(User.xp.desc(), User.username.asc())
            .limit(LEADERBOARD_LIMIT)
        ).all()

        leaderboard = [
            UserScore(
                rank=i + 1,
                username=u.username,
                xp=u.xp or 0,
                level=u.level or 1,
                is_you=(u.user_id == uid),
            )
            for i, u in enumerate(top)
        ]
        # If the user didn't make the visible top N, append their own standing
        # so they always know where they rank.
        my_rank = _rank_at_level(session, me)
        if my_rank > LEADERBOARD_LIMIT:
            leaderboard.append(
                UserScore(
                    rank=my_rank,
                    username=me.username,
                    xp=me.xp or 0,
                    level=me.level or 1,
                    is_you=True,
                )
            )

    return ScoresResponse(leaderboard=leaderboard)



@router.get("", response_model=List[CourseCard])
@router.get("/", response_model=List[CourseCard])
async def list_courses(
    request: Request,
    search: Optional[str] = Query(None, max_length=MAX_SEARCH_LEN),
    tag: Optional[str] = Query(None, max_length=MAX_TAG_LEN),
    sort: str = Query("popular"),
    current_user: dict = Depends(get_current_user),
):
    """Marketplace catalogue with safe, parameterised search / tag / sort."""
    uid = _parse_uid(current_user)
    term = (search or "").strip()[:MAX_SEARCH_LEN]
    sort = sort if sort in ALLOWED_SORTS else "popular"

    with get_db_session() as session:
        stmt = select(Course)
        if term:
            pattern = f"%{_like_escape(term)}%"
            stmt = stmt.where(Course.course_name.ilike(pattern, escape="\\"))
        courses = list(session.scalars(stmt).all())

        counts = _enrollment_counts(session)
        enrolled_ids, progress_map = _my_enrollments(session, uid)
        names = _instructor_names(session, courses)

        if sort == "newest":
            courses.sort(key=lambda c: c.created_at, reverse=True)
        elif sort == "name":
            courses.sort(key=lambda c: c.course_name.lower())
        else:  # popular
            courses.sort(key=lambda c: counts.get(c.course_id, 0), reverse=True)

        cards = [
            _build_card(
                course,
                counts=counts,
                enrolled_ids=enrolled_ids,
                progress_map=progress_map,
                instructor_name=names.get(course.instructor_id),
            )
            for course in courses
        ]

    if tag:
        wanted = tag.strip().lower()
        cards = [c for c in cards if any(t.lower() == wanted for t in c.tags)]

    return cards
