import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException, Request,
    UploadFile, WebSocket, WebSocketDisconnect, status,
)
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.db import get_db_session
from model.models import Category, Notification, Post, PostAttachment, Thread, User,ThreadLike, Report
from user.auth import ROLE_ADMIN, SCOPE_ACCESS, decode_access_token
from user.auth_router import get_current_user
from common.audit import log_action
from common.security import parse_uid as _parse_uid, client_ip as _client_ip
from core.rate_limit import limiter
from .schemas import (
    CategoryResponse,
    MarkNotificationReadRequest,
    NotificationResponse,
    PostResponse,
    ThreadResponse,
    UpdatePostRequest,
    UpdateThreadRequest,
    # CreatePostRequest,
    CreateReportRequest,
    ReportResponse,
    UserReportResponse
)
from .utils import (
    notification_to_response,
    post_to_response,
    sanitize_content,
    save_attachments,
    thread_to_response,
)
from .websocket import manager

router = APIRouter(prefix="/api/v1/forum", tags=["Discussion Forum"])

MAX_TITLE_LEN = 255
MAX_CONTENT_LEN = 10000


# --- Auth / ownership helpers -----------------------------------------------
def _is_admin(current_user: dict) -> bool:
    return current_user.get("role") == ROLE_ADMIN


def _require_owner_or_admin(owner_id: Optional[UUID], current_user: dict) -> None:
    """Authorization gate: only the resource's author (or an admin) may mutate it.
    Anonymous/legacy rows with no owner are admin-only to be safe."""
    if _is_admin(current_user):
        return
    if owner_id is None or owner_id != _parse_uid(current_user):
        raise HTTPException(status_code=403, detail="You can only modify your own content")


def make_slug(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
    return slug or f"thread-{uuid.uuid4().hex[:8]}"


def get_original_post(session, thread_id: uuid.UUID) -> Optional[Post]:
    return session.scalar(
        select(Post)
        .where(Post.thread_id == thread_id, Post.parent_id.is_(None))
        .options(selectinload(Post.attachments))
        .order_by(Post.created_at.asc())
    )


# --- Read endpoints (auth required, consistent with the rest of the app) -----
@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    current_user: dict = Depends(get_current_user),
) -> List[CategoryResponse]:
    with get_db_session() as session:
        uid = _parse_uid(current_user)
        
        categories = session.scalars(
            select(Category)
            .options(selectinload(Category.threads).selectinload(Thread.posts),
                     selectinload(Category.threads).selectinload(Thread.likes),)
            .order_by(Category.display_order, Category.name)
        ).all()

        return [
            CategoryResponse(
                category_id=category.category_id.hex,
                name=category.name,
                slug=category.slug,
                description=category.description,
                display_order=category.display_order,
                created_at=category.created_at,
                threads=[
                    thread_to_response(
                        thread,
                        session,
                        like_count=len(thread.likes),
                        is_liked=any(
                            like.user_id == uid
                            for like in thread.likes
                        ),
                    )
                    for thread in sorted(
                        [
                            t for t in category.threads
                            if not t.is_deleted
                        ],
                        key=lambda item: item.updated_at or item.created_at,
                        reverse=True,
                    )
                ],
            )
            for category in categories
        ]


@router.get("/threads/{thread_id}/posts", response_model=List[PostResponse])
async def list_thread_posts(
    thread_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
) -> List[PostResponse]:
    with get_db_session() as session:
        thread = session.get(Thread, thread_id)
        if not thread or thread.is_deleted:
            raise HTTPException(status_code=404, detail="Thread not found")

        posts = session.scalars(
            select(Post)
            .where(
                Post.thread_id == thread_id,
                Post.is_deleted.is_(False),
            )
            .options(
                selectinload(Post.attachments),
                selectinload(Post.child_posts)
            )
            .order_by(Post.created_at.asc())
        ).all()

        return [post_to_response(post, session) for post in posts]


# --- Thread CRUD -------------------------------------------------------------
@router.post("/categories/{category_id}/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_thread(
    request: Request,
    category_id: uuid.UUID,
    title: str = Form(..., min_length=3, max_length=MAX_TITLE_LEN),
    content: str = Form(..., min_length=1, max_length=MAX_CONTENT_LEN),
    files: Optional[List[UploadFile]] = File(default=None),
    current_user: dict = Depends(get_current_user),
) -> ThreadResponse:
    uid = _parse_uid(current_user)
    title = title.strip()
    if len(title) < 3:
        raise HTTPException(status_code=400, detail="Thread title must be at least 3 characters")

    with get_db_session() as session:
        category = session.get(Category, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        base_slug = make_slug(title)
        slug = base_slug
        counter = 1
        while session.scalar(select(Thread).where(Thread.slug == slug)):
            counter += 1
            slug = f"{base_slug}-{counter}"

        thread = Thread(
            category_id=category.category_id,
            creator_id=uid,
            title=title,
            slug=slug,
        )
        session.add(thread)
        session.flush()

        original_post = Post(
            thread_id=thread.thread_id,
            creator_id=uid,
            parent_id=None,
            content=sanitize_content(content),
        )
        session.add(original_post)
        session.flush()

        await save_attachments(session, original_post, files)

        now = datetime.now(timezone.utc)
        thread.updated_at = now
        original_post.updated_at = now
        session.flush()

        response = thread_to_response(thread, session)

    await manager.broadcast({
        "event": "thread_created",
        "thread": response.model_dump(mode="json"),
    })
    return response


@router.put("/threads/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: uuid.UUID,
    request: UpdateThreadRequest,
    current_user: dict = Depends(get_current_user),
) -> ThreadResponse:
    title = request.title.strip()
    if len(title) < 3:
        raise HTTPException(status_code=400, detail="Thread title must be at least 3 characters")

    with get_db_session() as session:
        thread = session.scalar(
            select(Thread)
            .where(
                Thread.thread_id == thread_id,
                Thread.is_deleted.is_(False),
            )
            .options(selectinload(Thread.posts).selectinload(Post.attachments))
        )
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        _require_owner_or_admin(thread.creator_id, current_user)

        if thread.is_locked:
            raise HTTPException(status_code=403, detail="Thread is locked")

        original_post = get_original_post(session, thread.thread_id)
        if not original_post:
            raise HTTPException(status_code=404, detail="Original post not found")

        now = datetime.now(timezone.utc)
        thread.title = title
        thread.updated_at = now

        original_post.content = sanitize_content(request.content)
        original_post.is_edited = True
        original_post.updated_at = now
        session.flush()

        response = thread_to_response(thread, session)
        post_response = post_to_response(original_post)

    await manager.broadcast({
        "event": "thread_updated",
        "thread": response.model_dump(mode="json"),
    })
    await manager.broadcast({
        "event": "post_updated",
        "thread_id": response.thread_id,
        "post": post_response.model_dump(mode="json"),
    })
    return response


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: uuid.UUID,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> None:
    with get_db_session() as session:
        thread = session.scalar(
    select(Thread).where(
        Thread.thread_id == thread_id,
    )
)
        if not thread or thread.is_deleted:
            raise HTTPException(status_code=404, detail="Thread not found")

        _require_owner_or_admin(thread.creator_id, current_user)

        deleted_thread_id = thread.thread_id.hex
        session.delete(thread)
        log_action(
            session, user_id=_parse_uid(current_user), action="delete_thread",
            resource_type="thread", resource_id=thread_id, ip_address=_client_ip(request),
        )

    await manager.broadcast({
        "event": "thread_deleted",
        "thread_id": deleted_thread_id,
    })


# --- Post (reply) CRUD -------------------------------------------------------
@router.post("/threads/{thread_id}/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_post(
    request: Request,
    thread_id: uuid.UUID,
    content: str = Form(..., min_length=1, max_length=MAX_CONTENT_LEN),
    parent_id: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(default=None),
    current_user: dict = Depends(get_current_user),
) -> PostResponse:
    uid = _parse_uid(current_user)
    with get_db_session() as session:
        thread = session.get(Thread, thread_id)
        if not thread or thread.is_deleted:
            raise HTTPException(status_code=404, detail="Thread not found")
        if thread.is_locked:
            raise HTTPException(status_code=403, detail="Thread is locked")

        parent_uuid = None

        if parent_id:
                parent_uuid = UUID(parent_id)

                parent_post = session.get(Post, parent_uuid)

                if not parent_post or parent_post.is_deleted:
                    raise HTTPException(
                        status_code=404,
                        detail="Parent post not found"
                    )

                # Prevent replying to a reply (max depth = 1)
                if parent_post.parent_id is not None:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot reply to a reply"
                    )

            # Existing post creation
        post = Post(
                thread_id=thread.thread_id,
                creator_id=uid,
                parent_id=parent_uuid,
                content=sanitize_content(content),
            )

        session.add(post)
        session.flush()

        await save_attachments(session, post, files)

        now = datetime.now(timezone.utc)
        post.updated_at = now
        thread.updated_at = now
        session.flush()

        response = post_to_response(post, session)

        notification_response = None

        # Notify the thread owner when another user replies to their thread.
        if thread.creator_id and thread.creator_id != uid:
            actor = session.get(User, uid)
            actor_name = actor.username if actor else "Someone"

            notification = Notification(
                recipient_id=thread.creator_id,
                actor_id=uid,
                thread_id=thread.thread_id,
                post_id=post.post_id,
                notification_type="thread_reply",
                message=f"{actor_name} replied to your thread: {thread.title}",
            )
            session.add(notification)
            session.flush()

            notification_response = notification_to_response(notification)

    await manager.broadcast({
        "event": "post_created",
        "thread_id": response.thread_id,
        "post": response.model_dump(mode="json"),
    })

    if notification_response:
        await manager.broadcast({
            "event": "notification_created",
            "recipient_id": notification_response.recipient_id,
            "notification": notification_response.model_dump(mode="json"),
        })

    return response


@router.put("/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: uuid.UUID,
    request: UpdatePostRequest,
    current_user: dict = Depends(get_current_user),
) -> PostResponse:
    with get_db_session() as session:
        post = session.scalar(
            select(Post)
            .where(
                Post.post_id == post_id,
                Post.is_deleted.is_(False),
            )
            .options(selectinload(Post.attachments))
        )
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        _require_owner_or_admin(post.creator_id, current_user)

        post.content = sanitize_content(request.content)
        post.is_edited = True
        post.updated_at = datetime.now(timezone.utc)
        session.flush()

        response = post_to_response(post, session)

    await manager.broadcast({
        "event": "post_updated",
        "thread_id": response.thread_id,
        "post": response.model_dump(mode="json"),
    })
    return response


@router.post("/posts/{post_id}/attachments", response_model=PostResponse)
@limiter.limit("30/minute")
async def add_post_attachments(
    request: Request,
    post_id: uuid.UUID,
    files: Optional[List[UploadFile]] = File(default=None),
    current_user: dict = Depends(get_current_user),
) -> PostResponse:
    with get_db_session() as session:
        post = session.scalar(
            select(Post)
            .where(
    Post.post_id == post_id,
    Post.is_deleted.is_(False),
)
            .options(selectinload(Post.attachments))
        )
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        _require_owner_or_admin(post.creator_id, current_user)

        await save_attachments(session, post, files)

        post.updated_at = datetime.now(timezone.utc)
        session.flush()
        session.refresh(post)
        response = post_to_response(post, session)

    await manager.broadcast({
        "event": "post_updated",
        "thread_id": response.thread_id,
        "post": response.model_dump(mode="json"),
    })
    return response


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post_attachment(
    attachment_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
) -> None:
    with get_db_session() as session:
        attachment = session.scalar(
            select(PostAttachment).where(PostAttachment.attachment_id == attachment_id)
        )
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")

        post = session.get(Post, attachment.post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        _require_owner_or_admin(post.creator_id, current_user)

        thread_id = post.thread_id.hex
        post_id = post.post_id

        session.delete(attachment)
        session.flush()

        updated_post = session.scalar(
            select(Post)
            .where(
    Post.post_id == post_id,
    Post.is_deleted.is_(False),
)
            .options(selectinload(Post.attachments))
        )
        response = post_to_response(updated_post)

    await manager.broadcast({
        "event": "post_updated",
        "thread_id": thread_id,
        "post": response.model_dump(mode="json"),
    })


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: uuid.UUID,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> None:
    with get_db_session() as session:
        post = session.scalar(
    select(Post).where(
        Post.post_id == post_id,
        Post.is_deleted.is_(False),
    )
)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        _require_owner_or_admin(post.creator_id, current_user)

        thread_id = post.thread_id.hex
        children = session.scalars(
            select(Post)
            .where(
                Post.parent_id == post.post_id,
                Post.is_deleted.is_(False),
            )
        ).all()

        for child in children:
            session.delete(child)

        session.delete(post)
        log_action(
            session, user_id=_parse_uid(current_user), action="delete_post",
            resource_type="post", resource_id=post_id, ip_address=_client_ip(request),
        )

    await manager.broadcast({
        "event": "post_deleted",
        "thread_id": thread_id,
        "post_id": post_id.hex,
    })


# --- Notifications (recipient-scoped) ---------------------------------------
@router.get("/notifications", response_model=List[NotificationResponse])
async def list_notifications(current_user: dict = Depends(get_current_user)) -> List[NotificationResponse]:
    uid = _parse_uid(current_user)
    with get_db_session() as session:
        rows = session.scalars(
            select(Notification)
            .where(Notification.recipient_id == uid)
            .order_by(Notification.created_at.desc())
        ).all()
        return [notification_to_response(n) for n in rows]


@router.patch("/notifications/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: uuid.UUID,
    request: MarkNotificationReadRequest,
    current_user: dict = Depends(get_current_user),
) -> NotificationResponse:
    uid = _parse_uid(current_user)
    with get_db_session() as session:
        notification = session.get(Notification, notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        # IDOR guard: a user may only update notifications addressed to them.
        if notification.recipient_id != uid and not _is_admin(current_user):
            raise HTTPException(status_code=403, detail="Not your notification")

        notification.is_read = request.is_read
        session.flush()
        return notification_to_response(notification)
    
# --- Like Threads ---------------------------
@router.post("/threads/{thread_id}/like")
@limiter.limit("30/minute")
async def like_thread(
    request: Request,
    thread_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    uid = _parse_uid(current_user)

    with get_db_session() as session:
        thread = session.get(Thread, thread_id)

        if not thread or thread.is_deleted:
            raise HTTPException(
                status_code=404,
                detail="Thread not found",
            )
        existing = session.scalar(
            select(ThreadLike).where(
                ThreadLike.user_id == uid,
                ThreadLike.thread_id == thread_id,
            )
        )

        if existing:
            return {
                "liked": True,
                "message": "already liked",
            }

        like = ThreadLike(
            user_id=uid,
            thread_id=thread_id,
        )

        session.add(like)
        session.commit()

        return {
            "liked": True,
            "message": "liked",
        }
    
@router.delete("/threads/{thread_id}/like")
@limiter.limit("30/minute")
async def unlike_thread(
    request: Request,
    thread_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    uid = _parse_uid(current_user)

    with get_db_session() as session:
        thread = session.get(Thread, thread_id)

        if not thread or thread.is_deleted:
            raise HTTPException(
                status_code=404,
                detail="Thread not found",
            )
        existing = session.scalar(
            select(ThreadLike).where(
                ThreadLike.user_id == uid,
                ThreadLike.thread_id == thread_id,
            )
        )

        if not existing:
            raise HTTPException(
                status_code=404,
                detail="Thread is not liked",
            )

        session.delete(existing)
        session.commit()

        return {
            "liked": False,
            "message": "unliked",
        }

# --- Filter Liked Threads ---------------------------
@router.get("/users/liked-threads", response_model=List[ThreadResponse])
async def list_liked_threads(
    current_user: dict = Depends(get_current_user),
) -> List[ThreadResponse]:

    uid = _parse_uid(current_user)

    with get_db_session() as session:

        threads = session.scalars(
            select(Thread)
            .where(Thread.is_deleted.is_(False))
            .join(ThreadLike, Thread.thread_id == ThreadLike.thread_id)
            .where(ThreadLike.user_id == uid)
            .options(
                selectinload(Thread.posts),
                selectinload(Thread.likes),
            )
            .order_by(Thread.updated_at.desc())
        ).all()

        return [
            thread_to_response(
                thread,
                session,
                like_count=len(thread.likes),
                is_liked=True,
            )
            for thread in threads
        ]
    
# --- Last Viewed Thread ---------------------------
@router.post("/threads/{thread_id}/view")
@limiter.limit("60/minute")
async def mark_thread_viewed(
    request: Request,
    thread_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    with get_db_session() as session:

        user = session.get(
            User,
            _parse_uid(current_user)
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        thread = session.get(Thread, thread_id)

        if not thread or thread.is_deleted:
            raise HTTPException(
                status_code=404,
                detail="Thread not found",
            )
        user.last_viewed_thread_id = thread_id
        user.last_viewed_at = datetime.now(timezone.utc)

        session.commit()

        return {
            "success": True
        }
    
@router.get("/users/last-viewed")
@limiter.limit("60/minute")
async def get_last_viewed_thread(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    with get_db_session() as session:
        user = session.get(
            User,
            _parse_uid(current_user)
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not user.last_viewed_thread_id:
            return None

        thread = session.get(
            Thread,
            user.last_viewed_thread_id
        )

        if not thread or thread.is_deleted:
            return None

        return {
            "thread_id": thread.thread_id.hex,
            "title": thread.title,
            "viewed_at": user.last_viewed_at,
        }

# --- Reporting Thread/Post ---------------------------
@router.post(
    "/threads/{thread_id}/report",
    response_model=ReportResponse,
)
@limiter.limit("10/minute")
async def report_thread(
    request: Request,
    thread_id: uuid.UUID,
    payload: CreateReportRequest,
    current_user: dict = Depends(get_current_user),
):
    uid = _parse_uid(current_user)

    with get_db_session() as session:

        thread = session.get(Thread, thread_id)

        if not thread or thread.is_deleted:
            raise HTTPException(
                status_code=404,
                detail="Thread not found",
            )

        if thread.creator_id == uid:
            raise HTTPException(
                status_code=400,
                detail="You cannot report your own thread.",
            )

        existing = session.scalar(
            select(Report).where(
                Report.reporter_id == uid,
                Report.thread_id == thread_id,
                Report.status == "Pending",
            )
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="You have already reported this thread.",
            )

        report = Report(
            reporter_id=uid,
            thread_id=thread_id,
            reason=payload.reason,
            description=payload.description,
        )

        session.add(report)
        session.commit()
        session.refresh(report)

        return ReportResponse(
            report_id=report.report_id.hex,
            reporter_id=report.reporter_id.hex,
            thread_id=report.thread_id.hex,
            post_id=None,
            reason=report.reason,
            description=report.description,
            status=report.status,
            created_at=report.created_at,
        )

@router.post(
    "/posts/{post_id}/report",
    response_model=ReportResponse,
)
@limiter.limit("10/minute")
async def report_post(
    request: Request,
    post_id: uuid.UUID,
    payload: CreateReportRequest,
    current_user: dict = Depends(get_current_user),
):
    uid = _parse_uid(current_user)

    with get_db_session() as session:

        post = session.get(Post, post_id)

        if not post or post.is_deleted:
            raise HTTPException(
                status_code=404,
                detail="Reply not found",
            )

        if post.creator_id == uid:
            raise HTTPException(
                status_code=400,
                detail="You cannot report your own reply.",
            )

        existing = session.scalar(
            select(Report).where(
                Report.reporter_id == uid,
                Report.post_id == post_id,
                Report.status == "Pending",
            )
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="You have already reported this reply.",
            )

        report = Report(
            reporter_id=uid,
            post_id=post_id,
            reason=payload.reason,
            description=payload.description,
        )

        session.add(report)
        session.commit()
        session.refresh(report)

        return ReportResponse(
            report_id=report.report_id.hex,
            reporter_id=report.reporter_id.hex,
            thread_id=None,
            post_id=report.post_id.hex,
            reason=report.reason,
            description=report.description,
            status=report.status,
            created_at=report.created_at,
        )
    
@router.get(
    "/users/reports",
    response_model=List[UserReportResponse],
)
async def list_my_reports(
    current_user: dict = Depends(get_current_user),
):
    uid = _parse_uid(current_user)

    with get_db_session() as session:

        reports = session.scalars(
            select(Report)
            .where(Report.reporter_id == uid)
            .order_by(Report.created_at.desc())
        ).all()

        results = []

        for report in reports:

            if report.thread_id:

                thread = session.get(Thread, report.thread_id)

                original_post = None

                if thread:
                    original_post = session.scalar(
                        select(Post)
                        .where(
                            Post.thread_id == thread.thread_id,
                            Post.parent_id.is_(None)
                        )
                    )

                results.append(
                    UserReportResponse(
                        report_id=report.report_id.hex,
                        type="thread",
                        title=thread.title if thread else "(Deleted thread)",

                        reported_content=(
                            "Content removed by moderator."
                            if thread and thread.is_deleted
                            else (
                                original_post.content
                                if original_post
                                else None
                            )
                        ),
                        reason=report.reason,
                        description=report.description,
                        status=report.status,
                        created_at=report.created_at,

                        thread_id=thread.thread_id.hex if thread else None,
                        category_id=thread.category_id.hex if thread else None,
                    )
                )

            elif report.post_id:

                post = session.get(Post, report.post_id)

                thread = (
                    session.get(Thread, post.thread_id)
                    if post
                    else None
                )

                results.append(
                    UserReportResponse(
                        report_id=report.report_id.hex,
                        type="reply",
                        title=thread.title if thread else "(Deleted thread)",

                        reported_content=(
                            "Content removed by moderator."
                            if post and post.is_deleted
                            else (
                                post.content
                                if post
                                else None
                            )
                        ),
                        reason=report.reason,
                        description=report.description,
                        status=report.status,
                        created_at=report.created_at,

                        thread_id=thread.thread_id.hex if thread else None,
                        category_id=thread.category_id.hex if thread else None,
                    )
                )

        return results

# --- Threads Posted ---------------------------
@router.get(
    "/users/my-threads",
    response_model=List[ThreadResponse],
)
async def list_my_threads(
    current_user: dict = Depends(get_current_user),
):
    uid = _parse_uid(current_user)

    with get_db_session() as session:

        threads = session.scalars(
            select(Thread)
            .where(
                Thread.creator_id == uid,
                Thread.is_deleted.is_(False),
            )
            .options(
                selectinload(Thread.posts),
                selectinload(Thread.likes),
            )
            .order_by(Thread.updated_at.desc())
        ).all()

        return [
            thread_to_response(
                thread,
                session,
                like_count=len(thread.likes),
                is_liked=any(
                    like.user_id == uid
                    for like in thread.likes
                ),
            )
            for thread in threads
        ]
    
# --- WebSocket (token-authenticated live updates) ---------------------------
def _authenticate_ws_token(token: Optional[str]) -> bool:
    """Validate the JWT taken from the session cookie on the WS handshake.
    Returns True only for a live access-scope token of an active, non-deleted
    user."""
    if not token:
        return False
    try:
        payload = decode_access_token(token)
    except JWTError:
        return False
    if payload.get("scope") != SCOPE_ACCESS:
        return False
    sub = payload.get("sub")
    if not sub:
        return False
    try:
        uid = UUID(sub)
    except (ValueError, TypeError):
        return False
    with get_db_session() as session:
        user = session.scalar(select(User).where(User.user_id == uid))
        return bool(user and user.is_active and not user.is_deleted)


@router.websocket("/ws")
async def forum_websocket(websocket: WebSocket) -> None:
    # The JWT now lives in an httpOnly cookie, which the browser sends on the
    # same-origin WS handshake — so read it from there instead of a query param
    # (that also keeps the token out of URLs / server logs).
    token = websocket.cookies.get("access_token")
    if not _authenticate_ws_token(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
