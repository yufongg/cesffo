from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from db.db import get_db_session
from model.models import (
    Course, Module, ReadingMaterial, MediaContent,
    InteractiveActivity, ActivityOption,
)
from common.sanitize import sanitize_html, strip_tags
from common.audit import log_action
from common.security import parse_uid as _parse_uid, to_uuid as _to_uuid, client_ip as _client_ip
from user.auth import ROLE_ADMIN
from user.auth_router import require_instructor

router = APIRouter(prefix="/api/v1/instructor", tags=["Instructor - Course Authoring"])

MAX_TITLE_LEN = 255
MAX_BODY_LEN = 20000
ALLOWED_MEDIA_TYPES = frozenset({"video", "image", "audio", "document"})
ACTIVITY_TYPES = Literal["mcq_single", "mcq_multi", "short_answer"]


# --- Helpers ---
def _require_owned_course(session, course_id: UUID, current_user: dict) -> Course:
    """AS-04: an instructor may only act on their own courses. Never trust an
    instructor_id from the request body — always re-derive from the JWT and
    re-check ownership against the DB row on every write."""
    course = session.scalar(select(Course).where(Course.course_id == course_id))
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    uid = _parse_uid(current_user)
    if current_user["role"] != ROLE_ADMIN and course.instructor_id != uid:
        raise HTTPException(status_code=403, detail="You do not own this course")
    return course


def _require_owned_module(session, module_id: UUID, current_user: dict) -> Module:
    module = session.scalar(select(Module).where(Module.module_id == module_id))
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    _require_owned_course(session, module.course_id, current_user)
    return module


def _require_owned_activity(session, activity_id: UUID, current_user: dict) -> InteractiveActivity:
    activity = session.scalar(select(InteractiveActivity).where(InteractiveActivity.activity_id == activity_id))
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    _require_owned_module(session, activity.module_id, current_user)
    return activity


# --- Schemas: Course ---
class CourseCreate(BaseModel):
    course_name: str = Field(..., min_length=1, max_length=MAX_TITLE_LEN)
    summary: Optional[str] = Field(None, max_length=MAX_BODY_LEN)
    level: Optional[str] = Field(None, max_length=50)
    tags: List[str] = Field(default_factory=list, max_length=20)
    xp_reward: int = Field(0, ge=0, le=100000)
    price_cents: int = Field(0, ge=0, le=1_000_000)
    currency: str = Field("SGD", min_length=3, max_length=3)


class CourseUpdate(BaseModel):
    course_name: Optional[str] = Field(None, min_length=1, max_length=MAX_TITLE_LEN)
    summary: Optional[str] = Field(None, max_length=MAX_BODY_LEN)
    level: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = Field(None, max_length=20)
    xp_reward: Optional[int] = Field(None, ge=0, le=100000)
    price_cents: Optional[int] = Field(None, ge=0, le=1_000_000)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)


class CourseRead(BaseModel):
    course_id: str
    course_name: str
    summary: Optional[str] = None
    level: Optional[str] = None
    tags: List[str] = []
    xp_reward: int = 0
    price_cents: int = 0
    currency: str = "SGD"


# --- Schemas: Module ---
class ModuleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=MAX_TITLE_LEN)
    description: Optional[str] = Field(None, max_length=MAX_BODY_LEN)
    order_index: int = Field(0, ge=0, le=100000)


class ModuleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=MAX_TITLE_LEN)
    description: Optional[str] = Field(None, max_length=MAX_BODY_LEN)
    order_index: Optional[int] = Field(None, ge=0, le=100000)


class ModuleRead(BaseModel):
    module_id: str
    course_id: str
    title: str
    description: Optional[str] = None
    order_index: int


# --- Schemas: Reading material ---
class ReadingMaterialCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=MAX_TITLE_LEN)
    body: str = Field(..., min_length=1, max_length=MAX_BODY_LEN)
    order_index: int = Field(0, ge=0, le=100000)


class ReadingMaterialUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=MAX_TITLE_LEN)
    body: Optional[str] = Field(None, min_length=1, max_length=MAX_BODY_LEN)
    order_index: Optional[int] = Field(None, ge=0, le=100000)


class ReadingMaterialRead(BaseModel):
    material_id: str
    module_id: str
    title: str
    body: str
    order_index: int


# --- Schemas: Media content ---
class MediaContentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=MAX_TITLE_LEN)
    media_url: str = Field(..., min_length=1, max_length=2048)
    media_type: str
    order_index: int = Field(0, ge=0, le=100000)

    @model_validator(mode="after")
    def _check_type(self):
        if self.media_type not in ALLOWED_MEDIA_TYPES:
            raise ValueError(f"media_type must be one of {sorted(ALLOWED_MEDIA_TYPES)}")
        if not (self.media_url.startswith("http://") or self.media_url.startswith("https://") or self.media_url.startswith("/static/")):
            raise ValueError("media_url must be an http(s) URL or a /static/ path")
        return self


class MediaContentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=MAX_TITLE_LEN)
    media_url: Optional[str] = Field(None, min_length=1, max_length=2048)
    media_type: Optional[str] = None
    order_index: Optional[int] = Field(None, ge=0, le=100000)


class MediaContentRead(BaseModel):
    media_id: str
    module_id: str
    title: str
    media_url: str
    media_type: str
    order_index: int


# --- Schemas: Interactive activity (instructor view includes the answer key) ---
class ActivityOptionInput(BaseModel):
    option_text: str = Field(..., min_length=1, max_length=1000)
    is_correct: bool = False


class ActivityOptionRead(BaseModel):
    option_id: str
    option_text: str
    is_correct: bool
    order_index: int


class InteractiveActivityCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=MAX_TITLE_LEN)
    activity_type: ACTIVITY_TYPES
    prompt: str = Field(..., min_length=1, max_length=MAX_BODY_LEN)
    order_index: int = Field(0, ge=0, le=100000)
    options: Optional[List[ActivityOptionInput]] = None
    correct_answers: Optional[List[str]] = Field(None, max_length=20)

    @model_validator(mode="after")
    def _check_answer_key(self):
        if self.activity_type in ("mcq_single", "mcq_multi"):
            if not self.options or len(self.options) < 2:
                raise ValueError("MCQ activities need at least 2 options")
            correct_count = sum(1 for o in self.options if o.is_correct)
            if self.activity_type == "mcq_single" and correct_count != 1:
                raise ValueError("mcq_single requires exactly one correct option")
            if self.activity_type == "mcq_multi" and correct_count < 1:
                raise ValueError("mcq_multi requires at least one correct option")
        else:  # short_answer
            if not self.correct_answers or not any(a.strip() for a in self.correct_answers):
                raise ValueError("short_answer requires at least one accepted answer")
        return self


class InteractiveActivityUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=MAX_TITLE_LEN)
    prompt: Optional[str] = Field(None, min_length=1, max_length=MAX_BODY_LEN)
    order_index: Optional[int] = Field(None, ge=0, le=100000)
    options: Optional[List[ActivityOptionInput]] = None
    correct_answers: Optional[List[str]] = Field(None, max_length=20)


class InteractiveActivityRead(BaseModel):
    activity_id: str
    module_id: str
    title: str
    activity_type: str
    prompt: str
    order_index: int
    options: List[ActivityOptionRead] = []
    correct_answers: Optional[List[str]] = None


# --- Mapping helpers ---
def _course_to_read(course: Course) -> CourseRead:
    content = course.content if isinstance(course.content, dict) else {}
    prereq = course.prerequirements if isinstance(course.prerequirements, dict) else {}
    return CourseRead(
        course_id=course.course_id.hex,
        course_name=course.course_name,
        summary=content.get("summary"),
        level=prereq.get("level"),
        tags=list(course.tags) if isinstance(course.tags, list) else [],
        xp_reward=course.xp_reward or 0,
        price_cents=course.price_cents or 0,
        currency=course.currency or "SGD",
    )


def _module_to_read(module: Module) -> ModuleRead:
    return ModuleRead(
        module_id=module.module_id.hex,
        course_id=module.course_id.hex,
        title=module.title,
        description=module.description,
        order_index=module.order_index,
    )


def _material_to_read(m: ReadingMaterial) -> ReadingMaterialRead:
    return ReadingMaterialRead(
        material_id=m.material_id.hex, module_id=m.module_id.hex,
        title=m.title, body=m.body, order_index=m.order_index,
    )


def _media_to_read(m: MediaContent) -> MediaContentRead:
    return MediaContentRead(
        media_id=m.media_id.hex, module_id=m.module_id.hex,
        title=m.title, media_url=m.media_url, media_type=m.media_type,
        order_index=m.order_index,
    )


def _activity_to_read(a: InteractiveActivity) -> InteractiveActivityRead:
    return InteractiveActivityRead(
        activity_id=a.activity_id.hex, module_id=a.module_id.hex,
        title=a.title, activity_type=a.activity_type, prompt=a.prompt,
        order_index=a.order_index,
        options=[
            ActivityOptionRead(option_id=o.option_id.hex, option_text=o.option_text,
                                is_correct=o.is_correct, order_index=o.order_index)
            for o in a.options
        ],
        correct_answers=a.correct_answers,
    )


# --- Endpoints: Courses ---
@router.post("/courses", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(request: CourseCreate, current_user: dict = Depends(require_instructor)):
    uid = _parse_uid(current_user)
    with get_db_session() as session:
        course = Course(
            instructor_id=uid,  # never trust a caller-supplied instructor_id
            course_name=strip_tags(request.course_name),
            xp_reward=request.xp_reward,
            price_cents=request.price_cents,
            currency=request.currency.upper(),
            content={"summary": sanitize_html(request.summary) if request.summary else ""},
            tags=[strip_tags(t)[:50] for t in request.tags],
            prerequirements={"level": strip_tags(request.level)} if request.level else {},
        )
        session.add(course)
        session.commit()
        session.refresh(course)
        return _course_to_read(course)


@router.get("/courses", response_model=List[CourseRead])
async def list_my_courses(current_user: dict = Depends(require_instructor)):
    uid = _parse_uid(current_user)
    with get_db_session() as session:
        stmt = select(Course)
        if current_user["role"] != ROLE_ADMIN:
            stmt = stmt.where(Course.instructor_id == uid)
        courses = session.scalars(stmt).all()
        return [_course_to_read(c) for c in courses]


@router.get("/courses/{course_id}", response_model=CourseRead)
async def get_my_course(course_id: str, current_user: dict = Depends(require_instructor)):
    with get_db_session() as session:
        course = _require_owned_course(session, _to_uuid(course_id), current_user)
        return _course_to_read(course)


@router.patch("/courses/{course_id}", response_model=CourseRead)
async def update_course(course_id: str, request: CourseUpdate, current_user: dict = Depends(require_instructor)):
    with get_db_session() as session:
        course = _require_owned_course(session, _to_uuid(course_id), current_user)
        if request.course_name is not None:
            course.course_name = strip_tags(request.course_name)
        if request.summary is not None:
            content = dict(course.content) if isinstance(course.content, dict) else {}
            content["summary"] = sanitize_html(request.summary)
            course.content = content
        if request.level is not None:
            course.prerequirements = {"level": strip_tags(request.level)}
        if request.tags is not None:
            course.tags = [strip_tags(t)[:50] for t in request.tags]
        if request.xp_reward is not None:
            course.xp_reward = request.xp_reward
        if request.price_cents is not None:
            course.price_cents = request.price_cents
        if request.currency is not None:
            course.currency = request.currency.upper()
        session.commit()
        session.refresh(course)
        return _course_to_read(course)


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(course_id: str, request: Request, current_user: dict = Depends(require_instructor)):
    uid = _parse_uid(current_user)
    cid = _to_uuid(course_id)
    with get_db_session() as session:
        course = _require_owned_course(session, cid, current_user)
        session.delete(course)
        log_action(
            session, user_id=uid, action="delete_course", resource_type="course",
            resource_id=cid, ip_address=_client_ip(request),
        )
        session.commit()


# --- Endpoints: Modules ---
@router.post("/courses/{course_id}/modules", response_model=ModuleRead, status_code=status.HTTP_201_CREATED)
async def create_module(course_id: str, request: ModuleCreate, current_user: dict = Depends(require_instructor)):
    with get_db_session() as session:
        course = _require_owned_course(session, _to_uuid(course_id), current_user)
        module = Module(
            course_id=course.course_id,
            title=strip_tags(request.title),
            description=sanitize_html(request.description) if request.description else None,
            order_index=request.order_index,
        )
        session.add(module)
        session.commit()
        session.refresh(module)
        return _module_to_read(module)


@router.get("/courses/{course_id}/modules", response_model=List[ModuleRead])
async def list_modules(course_id: str, current_user: dict = Depends(require_instructor)):
    with get_db_session() as session:
        course = _require_owned_course(session, _to_uuid(course_id), current_user)
        modules = session.scalars(
            select(Module).where(Module.course_id == course.course_id).order_by(Module.order_index)
        ).all()
        return [_module_to_read(m) for m in modules]


@router.get("/modules/{module_id}/materials", response_model=List[ReadingMaterialRead])
async def list_materials(module_id: str, current_user: dict = Depends(require_instructor)):
    with get_db_session() as session:
        module = _require_owned_module(session, _to_uuid(module_id), current_user)
        materials = session.scalars(
            select(ReadingMaterial).where(ReadingMaterial.module_id == module.module_id).order_by(ReadingMaterial.order_index)
        ).all()
        return [_material_to_read(m) for m in materials]


@router.get("/modules/{module_id}/media", response_model=List[MediaContentRead])
async def list_media(module_id: str, current_user: dict = Depends(require_instructor)):
    with get_db_session() as session:
        module = _require_owned_module(session, _to_uuid(module_id), current_user)
        media = session.scalars(
            select(MediaContent).where(MediaContent.module_id == module.module_id).order_by(MediaContent.order_index)
        ).all()
        return [_media_to_read(m) for m in media]


@router.get("/modules/{module_id}/activities", response_model=List[InteractiveActivityRead])
async def list_activities(module_id: str, current_user: dict = Depends(require_instructor)):
    with get_db_session() as session:
        module = _require_owned_module(session, _to_uuid(module_id), current_user)
        activities = session.scalars(
            select(InteractiveActivity).where(InteractiveActivity.module_id == module.module_id).order_by(InteractiveActivity.order_index)
        ).all()
        return [_activity_to_read(a) for a in activities]


@router.patch("/modules/{module_id}", response_model=ModuleRead)
async def update_module(module_id: str, request: ModuleUpdate, current_user: dict = Depends(require_instructor)):
    with get_db_session() as session:
        module = _require_owned_module(session, _to_uuid(module_id), current_user)
        if request.title is not None:
            module.title = strip_tags(request.title)
        if request.description is not None:
            module.description = sanitize_html(request.description)
        if request.order_index is not None:
            module.order_index = request.order_index
        session.commit()
        session.refresh(module)
        return _module_to_read(module)


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(module_id: str, request: Request, current_user: dict = Depends(require_instructor)):
    uid = _parse_uid(current_user)
    mid = _to_uuid(module_id)
    with get_db_session() as session:
        module = _require_owned_module(session, mid, current_user)
        session.delete(module)
        log_action(
            session, user_id=uid, action="delete_module", resource_type="module",
            resource_id=mid, ip_address=_client_ip(request),
        )
        session.commit()


# --- Endpoints: Reading materials ---
@router.post("/modules/{module_id}/materials", response_model=ReadingMaterialRead, status_code=status.HTTP_201_CREATED)
async def create_material(module_id: str, request: ReadingMaterialCreate, current_user: dict = Depends(require_instructor)):
    with get_db_session() as session:
        module = _require_owned_module(session, _to_uuid(module_id), current_user)
        material = ReadingMaterial(
            module_id=module.module_id,
            title=strip_tags(request.title),
            body=sanitize_html(request.body),
            order_index=request.order_index,
        )
        session.add(material)
        session.commit()
        session.refresh(material)
        return _material_to_read(material)


@router.patch("/materials/{material_id}", response_model=ReadingMaterialRead)
async def update_material(material_id: str, request: ReadingMaterialUpdate, current_user: dict = Depends(require_instructor)):
    mid = _to_uuid(material_id)
    with get_db_session() as session:
        material = session.scalar(select(ReadingMaterial).where(ReadingMaterial.material_id == mid))
        if not material:
            raise HTTPException(status_code=404, detail="Reading material not found")
        _require_owned_module(session, material.module_id, current_user)
        if request.title is not None:
            material.title = strip_tags(request.title)
        if request.body is not None:
            material.body = sanitize_html(request.body)
        if request.order_index is not None:
            material.order_index = request.order_index
        session.commit()
        session.refresh(material)
        return _material_to_read(material)


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(material_id: str, request: Request, current_user: dict = Depends(require_instructor)):
    uid = _parse_uid(current_user)
    mid = _to_uuid(material_id)
    with get_db_session() as session:
        material = session.scalar(select(ReadingMaterial).where(ReadingMaterial.material_id == mid))
        if not material:
            raise HTTPException(status_code=404, detail="Reading material not found")
        _require_owned_module(session, material.module_id, current_user)
        session.delete(material)
        log_action(
            session, user_id=uid, action="delete_reading_material", resource_type="reading_material",
            resource_id=mid, ip_address=_client_ip(request),
        )
        session.commit()


# --- Endpoints: Media content ---
@router.post("/modules/{module_id}/media", response_model=MediaContentRead, status_code=status.HTTP_201_CREATED)
async def create_media(module_id: str, request: MediaContentCreate, current_user: dict = Depends(require_instructor)):
    with get_db_session() as session:
        module = _require_owned_module(session, _to_uuid(module_id), current_user)
        media = MediaContent(
            module_id=module.module_id,
            title=strip_tags(request.title),
            media_url=request.media_url,
            media_type=request.media_type,
            order_index=request.order_index,
        )
        session.add(media)
        session.commit()
        session.refresh(media)
        return _media_to_read(media)


@router.patch("/media/{media_id}", response_model=MediaContentRead)
async def update_media(media_id: str, request: MediaContentUpdate, current_user: dict = Depends(require_instructor)):
    mid = _to_uuid(media_id)
    with get_db_session() as session:
        media = session.scalar(select(MediaContent).where(MediaContent.media_id == mid))
        if not media:
            raise HTTPException(status_code=404, detail="Media content not found")
        _require_owned_module(session, media.module_id, current_user)
        if request.title is not None:
            media.title = strip_tags(request.title)
        if request.media_url is not None:
            media.media_url = request.media_url
        if request.media_type is not None:
            if request.media_type not in ALLOWED_MEDIA_TYPES:
                raise HTTPException(status_code=400, detail="Invalid media_type")
            media.media_type = request.media_type
        if request.order_index is not None:
            media.order_index = request.order_index
        session.commit()
        session.refresh(media)
        return _media_to_read(media)


@router.delete("/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(media_id: str, request: Request, current_user: dict = Depends(require_instructor)):
    uid = _parse_uid(current_user)
    mid = _to_uuid(media_id)
    with get_db_session() as session:
        media = session.scalar(select(MediaContent).where(MediaContent.media_id == mid))
        if not media:
            raise HTTPException(status_code=404, detail="Media content not found")
        _require_owned_module(session, media.module_id, current_user)
        session.delete(media)
        log_action(
            session, user_id=uid, action="delete_media_content", resource_type="media_content",
            resource_id=mid, ip_address=_client_ip(request),
        )
        session.commit()


# --- Endpoints: Interactive activities ---
@router.post("/modules/{module_id}/activities", response_model=InteractiveActivityRead, status_code=status.HTTP_201_CREATED)
async def create_activity(module_id: str, request: InteractiveActivityCreate, current_user: dict = Depends(require_instructor)):
    with get_db_session() as session:
        module = _require_owned_module(session, _to_uuid(module_id), current_user)
        activity = InteractiveActivity(
            module_id=module.module_id,
            title=strip_tags(request.title),
            activity_type=request.activity_type,
            prompt=sanitize_html(request.prompt),
            order_index=request.order_index,
            correct_answers=(
                [strip_tags(a) for a in request.correct_answers] if request.correct_answers else None
            ),
        )
        if request.options:
            activity.options = [
                ActivityOption(option_text=strip_tags(o.option_text), is_correct=o.is_correct, order_index=i)
                for i, o in enumerate(request.options)
            ]
        session.add(activity)
        session.commit()
        session.refresh(activity)
        return _activity_to_read(activity)


@router.patch("/activities/{activity_id}", response_model=InteractiveActivityRead)
async def update_activity(activity_id: str, request: InteractiveActivityUpdate, current_user: dict = Depends(require_instructor)):
    aid = _to_uuid(activity_id)
    with get_db_session() as session:
        activity = _require_owned_activity(session, aid, current_user)

        # The update schema is partial and carries no activity_type, so the
        # answer-key invariants enforced at creation must be re-checked here
        # against the stored type — otherwise a PATCH could corrupt the key
        # (e.g. an MCQ left with zero correct options).
        if request.options is not None:
            if activity.activity_type not in ("mcq_single", "mcq_multi"):
                raise HTTPException(status_code=400, detail="Options apply only to MCQ activities")
            if len(request.options) < 2:
                raise HTTPException(status_code=400, detail="MCQ activities need at least 2 options")
            correct_count = sum(1 for o in request.options if o.is_correct)
            if activity.activity_type == "mcq_single" and correct_count != 1:
                raise HTTPException(status_code=400, detail="mcq_single requires exactly one correct option")
            if activity.activity_type == "mcq_multi" and correct_count < 1:
                raise HTTPException(status_code=400, detail="mcq_multi requires at least one correct option")
        if request.correct_answers is not None:
            if activity.activity_type != "short_answer":
                raise HTTPException(status_code=400, detail="Accepted answers apply only to short-answer activities")
            if not any(a.strip() for a in request.correct_answers):
                raise HTTPException(status_code=400, detail="short_answer requires at least one accepted answer")

        if request.title is not None:
            activity.title = strip_tags(request.title)
        if request.prompt is not None:
            activity.prompt = sanitize_html(request.prompt)
        if request.order_index is not None:
            activity.order_index = request.order_index
        if request.correct_answers is not None:
            activity.correct_answers = [strip_tags(a) for a in request.correct_answers]
        if request.options is not None:
            activity.options = [
                ActivityOption(option_text=strip_tags(o.option_text), is_correct=o.is_correct, order_index=i)
                for i, o in enumerate(request.options)
            ]
        session.commit()
        session.refresh(activity)
        return _activity_to_read(activity)


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(activity_id: str, request: Request, current_user: dict = Depends(require_instructor)):
    uid = _parse_uid(current_user)
    aid = _to_uuid(activity_id)
    with get_db_session() as session:
        activity = _require_owned_activity(session, aid, current_user)
        session.delete(activity)
        log_action(
            session, user_id=uid, action="delete_interactive_activity", resource_type="interactive_activity",
            resource_id=aid, ip_address=_client_ip(request),
        )
        session.commit()
