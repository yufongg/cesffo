from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from db.db import get_db_session
from model.models import (
    Course, CourseEnrollment, Module,
    InteractiveActivity, ActivitySubmission, ModuleProgress,
)
from user.auth_router import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Learning"])


# --- Helpers ---
def _parse_uid(current_user: dict) -> UUID:
    try:
        return UUID(current_user["user_id"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token subject")


def _to_uuid(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resource id")


def _require_enrolled_course(session, course_id: UUID, student_id: UUID) -> Course:
    """AS-05: enrollment must be re-checked server-side on every request that
    reads content or submits an activity — never only at enrollment time."""
    course = session.scalar(select(Course).where(Course.course_id == course_id))
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    enrolled = session.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == student_id,
            CourseEnrollment.dropped.is_(False),
        )
    )
    if not enrolled:
        raise HTTPException(status_code=403, detail="You are not enrolled in this course")
    return course


def _module_with_enrollment_check(session, module_id: UUID, student_id: UUID) -> Module:
    module = session.scalar(select(Module).where(Module.module_id == module_id))
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    _require_enrolled_course(session, module.course_id, student_id)
    return module


def _activity_with_enrollment_check(session, activity_id: UUID, student_id: UUID) -> InteractiveActivity:
    activity = session.scalar(select(InteractiveActivity).where(InteractiveActivity.activity_id == activity_id))
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    _module_with_enrollment_check(session, activity.module_id, student_id)
    return activity


def _recompute_course_progress(session, course_id: UUID, student_id: UUID) -> None:
    module_ids = session.scalars(select(Module.module_id).where(Module.course_id == course_id)).all()
    if not module_ids:
        return
    completed_count = len(
        session.scalars(
            select(ModuleProgress.module_id).where(
                ModuleProgress.module_id.in_(module_ids),
                ModuleProgress.student_id == student_id,
                ModuleProgress.completed.is_(True),
            )
        ).all()
    )
    enrollment = session.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == student_id,
        )
    )
    if enrollment:
        enrollment.progress = round(completed_count / len(module_ids), 4)


def _mark_module_complete(session, module_id: UUID, student_id: UUID) -> None:
    progress = session.scalar(
        select(ModuleProgress).where(ModuleProgress.module_id == module_id, ModuleProgress.student_id == student_id)
    )
    if progress is None:
        progress = ModuleProgress(module_id=module_id, student_id=student_id, completed=False)
        session.add(progress)
        session.flush()
    if not progress.completed:
        progress.completed = True
        progress.completed_at = datetime.now(timezone.utc)
        session.flush()


def _module_fully_correct(session, module_id: UUID, student_id: UUID) -> bool:
    activity_ids = session.scalars(
        select(InteractiveActivity.activity_id).where(InteractiveActivity.module_id == module_id)
    ).all()
    if not activity_ids:
        return True
    for aid in activity_ids:
        has_correct = session.scalar(
            select(ActivitySubmission).where(
                ActivitySubmission.activity_id == aid,
                ActivitySubmission.student_id == student_id,
                ActivitySubmission.is_correct.is_(True),
            )
        )
        if not has_correct:
            return False
    return True


# --- Schemas ---
class ReadingMaterialView(BaseModel):
    material_id: str
    title: str
    body: str
    order_index: int


class MediaContentView(BaseModel):
    media_id: str
    title: str
    media_url: str
    media_type: str
    order_index: int


class ActivityOptionView(BaseModel):
    """Student-facing option — never includes is_correct (answer-key protection)."""
    option_id: str
    option_text: str
    order_index: int


class ActivityView(BaseModel):
    activity_id: str
    title: str
    activity_type: str
    prompt: str
    order_index: int
    options: List[ActivityOptionView] = []


class ModuleView(BaseModel):
    module_id: str
    title: str
    description: Optional[str] = None
    order_index: int
    completed: bool = False
    reading_materials: List[ReadingMaterialView] = []
    media_contents: List[MediaContentView] = []
    activities: List[ActivityView] = []


class CourseLearnView(BaseModel):
    course_id: str
    course_name: str
    progress: float
    modules: List[ModuleView]


class SubmitActivityRequest(BaseModel):
    option_ids: Optional[List[str]] = Field(None, max_length=20)
    text: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def _one_of(self):
        if not self.option_ids and self.text is None:
            raise ValueError("Provide either option_ids or text")
        return self


class SubmissionResult(BaseModel):
    submission_id: str
    is_correct: bool
    score: float
    attempt_number: int


class SubmissionHistoryEntry(BaseModel):
    submission_id: str
    is_correct: bool
    score: float
    attempt_number: int
    submitted_at: str


# --- Mapping helpers ---
def _module_progress_map(session, module_ids, student_id: UUID) -> Dict[UUID, bool]:
    if not module_ids:
        return {}
    rows = session.execute(
        select(ModuleProgress.module_id, ModuleProgress.completed).where(
            ModuleProgress.module_id.in_(module_ids), ModuleProgress.student_id == student_id
        )
    ).all()
    return {mid: completed for mid, completed in rows}


def _to_module_view(module: Module, completed: bool) -> ModuleView:
    return ModuleView(
        module_id=module.module_id.hex,
        title=module.title,
        description=module.description,
        order_index=module.order_index,
        completed=completed,
        reading_materials=[
            ReadingMaterialView(material_id=m.material_id.hex, title=m.title, body=m.body, order_index=m.order_index)
            for m in module.reading_materials
        ],
        media_contents=[
            MediaContentView(media_id=m.media_id.hex, title=m.title, media_url=m.media_url,
                              media_type=m.media_type, order_index=m.order_index)
            for m in module.media_contents
        ],
        activities=[
            ActivityView(
                activity_id=a.activity_id.hex, title=a.title, activity_type=a.activity_type,
                prompt=a.prompt, order_index=a.order_index,
                options=[
                    ActivityOptionView(option_id=o.option_id.hex, option_text=o.option_text, order_index=o.order_index)
                    for o in a.options
                ],
            )
            for a in module.activities
        ],
    )


# --- Endpoints ---
@router.get("/courses/{course_id}/learn", response_model=CourseLearnView)
async def learn_course(course_id: str, current_user: dict = Depends(get_current_user)):
    student_id = _parse_uid(current_user)
    cid = _to_uuid(course_id)
    with get_db_session() as session:
        course = _require_enrolled_course(session, cid, student_id)
        modules = session.scalars(
            select(Module).where(Module.course_id == cid).order_by(Module.order_index)
        ).all()
        progress_map = _module_progress_map(session, [m.module_id for m in modules], student_id)

        # Reading-only modules (no activities) are considered complete once viewed.
        touched = False
        for m in modules:
            if not m.activities and not progress_map.get(m.module_id):
                _mark_module_complete(session, m.module_id, student_id)
                progress_map[m.module_id] = True
                touched = True
        if touched:
            _recompute_course_progress(session, cid, student_id)
            session.commit()

        enrollment = session.scalar(
            select(CourseEnrollment).where(CourseEnrollment.course_id == cid, CourseEnrollment.student_id == student_id)
        )

        return CourseLearnView(
            course_id=course.course_id.hex,
            course_name=course.course_name,
            progress=enrollment.progress if enrollment else 0.0,
            modules=[_to_module_view(m, progress_map.get(m.module_id, False)) for m in modules],
        )


@router.get("/modules/{module_id}/materials", response_model=ModuleView)
async def module_materials(module_id: str, current_user: dict = Depends(get_current_user)):
    student_id = _parse_uid(current_user)
    mid = _to_uuid(module_id)
    with get_db_session() as session:
        module = _module_with_enrollment_check(session, mid, student_id)
        progress_map = _module_progress_map(session, [mid], student_id)
        if not module.activities and not progress_map.get(mid):
            _mark_module_complete(session, mid, student_id)
            progress_map[mid] = True
            _recompute_course_progress(session, module.course_id, student_id)
            session.commit()
        return _to_module_view(module, progress_map.get(mid, False))


@router.post("/activities/{activity_id}/submit", response_model=SubmissionResult)
async def submit_activity(activity_id: str, request: SubmitActivityRequest, current_user: dict = Depends(get_current_user)):
    student_id = _parse_uid(current_user)
    aid = _to_uuid(activity_id)
    with get_db_session() as session:
        activity = _activity_with_enrollment_check(session, aid, student_id)

        # Grade server-side only — the answer key never leaves this function.
        if activity.activity_type in ("mcq_single", "mcq_multi"):
            if not request.option_ids:
                raise HTTPException(status_code=400, detail="option_ids required for this activity")
            try:
                submitted_ids = {UUID(o) for o in request.option_ids}
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid option id")
            valid_ids = {o.option_id for o in activity.options}
            if not submitted_ids.issubset(valid_ids):
                raise HTTPException(status_code=400, detail="Unknown option id for this activity")
            correct_ids = {o.option_id for o in activity.options if o.is_correct}
            is_correct = submitted_ids == correct_ids
            response_payload = {"option_ids": [i.hex for i in submitted_ids]}
        else:  # short_answer
            if request.text is None:
                raise HTTPException(status_code=400, detail="text required for this activity")
            submitted = request.text.strip().lower()
            accepted = {a.strip().lower() for a in (activity.correct_answers or [])}
            is_correct = submitted in accepted
            response_payload = {"text": request.text}

        prior_attempts = session.scalar(
            select(ActivitySubmission).where(
                ActivitySubmission.activity_id == aid, ActivitySubmission.student_id == student_id
            ).order_by(ActivitySubmission.attempt_number.desc())
        )
        attempt_number = (prior_attempts.attempt_number + 1) if prior_attempts else 1

        submission = ActivitySubmission(
            activity_id=aid,
            student_id=student_id,
            response=response_payload,
            is_correct=is_correct,
            score=1.0 if is_correct else 0.0,
            attempt_number=attempt_number,
        )
        session.add(submission)
        session.flush()

        if is_correct and _module_fully_correct(session, activity.module_id, student_id):
            _mark_module_complete(session, activity.module_id, student_id)
            _recompute_course_progress(session, activity.module.course_id, student_id)

        session.commit()
        return SubmissionResult(
            submission_id=submission.submission_id.hex,
            is_correct=submission.is_correct,
            score=submission.score,
            attempt_number=submission.attempt_number,
        )


@router.get("/activities/{activity_id}/submissions", response_model=List[SubmissionHistoryEntry])
async def my_submissions(activity_id: str, current_user: dict = Depends(get_current_user)):
    student_id = _parse_uid(current_user)
    aid = _to_uuid(activity_id)
    with get_db_session() as session:
        _activity_with_enrollment_check(session, aid, student_id)
        rows = session.scalars(
            select(ActivitySubmission).where(
                ActivitySubmission.activity_id == aid, ActivitySubmission.student_id == student_id
            ).order_by(ActivitySubmission.attempt_number)
        ).all()
        return [
            SubmissionHistoryEntry(
                submission_id=s.submission_id.hex, is_correct=s.is_correct, score=s.score,
                attempt_number=s.attempt_number, submitted_at=s.submitted_at.isoformat(),
            )
            for s in rows
        ]
