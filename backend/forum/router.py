import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.db import get_db_session
from model.models import Category, Notification, Post, PostAttachment, Thread
from .schemas import (
    CategoryResponse,
    MarkNotificationReadRequest,
    NotificationResponse,
    PostResponse,
    ThreadResponse,
    UpdatePostRequest,
    UpdateThreadRequest,
)
from .seed import seed_forum_demo_data
from .utils import (
    notification_to_response,
    post_to_response,
    sanitize_content,
    save_attachments,
    thread_to_response,
    validate_thread_title,
)
from .websocket import manager

router = APIRouter(prefix="/api/v1/forum", tags=["Discussion Forum"])


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


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories() -> List[CategoryResponse]:
    seed_forum_demo_data()

    with get_db_session() as session:
        categories = session.scalars(
            select(Category)
            .options(selectinload(Category.threads).selectinload(Thread.posts))
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
                    thread_to_response(thread)
                    for thread in sorted(
                        category.threads,
                        key=lambda item: item.updated_at or item.created_at,
                        reverse=True,
                    )
                ],
            )
            for category in categories
        ]


@router.get("/threads/{thread_id}/posts", response_model=List[PostResponse])
async def list_thread_posts(thread_id: uuid.UUID) -> List[PostResponse]:
    with get_db_session() as session:
        thread = session.get(Thread, thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        posts = session.scalars(
            select(Post)
            .where(Post.thread_id == thread_id, Post.parent_id.is_(None))
            .options(selectinload(Post.attachments))
            .order_by(Post.created_at.asc())
        ).all()

        return [post_to_response(post) for post in posts]


@router.post("/categories/{category_id}/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(
    category_id: uuid.UUID,
    title: str = Form(...),
    content: str = Form(...),
    files: Optional[List[UploadFile]] = File(default=None),
) -> ThreadResponse:
    title = validate_thread_title(title)

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
            creator_id=None,
            title=title,
            slug=slug,
        )
        session.add(thread)
        session.flush()

        original_post = Post(
            thread_id=thread.thread_id,
            creator_id=None,
            parent_id=None,
            content=sanitize_content(content),
        )
        session.add(original_post)
        session.flush()

        await save_attachments(session, original_post, files)

        now = datetime.now(timezone.utc)
        thread.updated_at = now
        original_post.updated_at = now

        session.add(thread)
        session.add(original_post)
        session.flush()

        response = thread_to_response(thread)

    await manager.broadcast({
        "event": "thread_created",
        "thread": response.model_dump(mode="json"),
    })

    return response


@router.put("/threads/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: uuid.UUID,
    request: UpdateThreadRequest,
) -> ThreadResponse:
    title = validate_thread_title(request.title)

    with get_db_session() as session:
        thread = session.scalar(
            select(Thread)
            .where(Thread.thread_id == thread_id)
            .options(selectinload(Thread.posts).selectinload(Post.attachments))
        )

        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

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

        session.add(thread)
        session.add(original_post)
        session.flush()

        response = thread_to_response(thread)
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
async def delete_thread(thread_id: uuid.UUID) -> None:
    with get_db_session() as session:
        thread = session.get(Thread, thread_id)

        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        deleted_thread_id = thread.thread_id.hex
        session.delete(thread)

    await manager.broadcast({
        "event": "thread_deleted",
        "thread_id": deleted_thread_id,
    })


# Kept for teammate/backward compatibility. Your scope should use thread CRUD above, not replies.
@router.post("/threads/{thread_id}/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    thread_id: uuid.UUID,
    content: str = Form(...),
    files: Optional[List[UploadFile]] = File(default=None),
) -> PostResponse:
    with get_db_session() as session:
        thread = session.get(Thread, thread_id)

        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        if thread.is_locked:
            raise HTTPException(status_code=403, detail="Thread is locked")

        post = Post(
            thread_id=thread.thread_id,
            creator_id=None,
            parent_id=None,
            content=sanitize_content(content),
        )
        session.add(post)
        session.flush()

        await save_attachments(session, post, files)

        now = datetime.now(timezone.utc)
        post.updated_at = now
        thread.updated_at = now

        session.add(post)
        session.add(thread)
        session.flush()

        response = post_to_response(post)

    await manager.broadcast({
        "event": "post_created",
        "thread_id": response.thread_id,
        "post": response.model_dump(mode="json"),
    })

    return response


@router.put("/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: uuid.UUID,
    request: UpdatePostRequest,
) -> PostResponse:
    with get_db_session() as session:
        post = session.scalar(
            select(Post)
            .where(Post.post_id == post_id)
            .options(selectinload(Post.attachments))
        )

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        post.content = sanitize_content(request.content)
        post.is_edited = True
        post.updated_at = datetime.now(timezone.utc)

        session.add(post)
        session.flush()

        response = post_to_response(post)

    await manager.broadcast({
        "event": "post_updated",
        "thread_id": response.thread_id,
        "post": response.model_dump(mode="json"),
    })

    return response


@router.post("/posts/{post_id}/attachments", response_model=PostResponse)
async def add_post_attachments(
    post_id: uuid.UUID,
    files: Optional[List[UploadFile]] = File(default=None),
) -> PostResponse:
    with get_db_session() as session:
        post = session.scalar(
            select(Post)
            .where(Post.post_id == post_id)
            .options(selectinload(Post.attachments))
        )

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        await save_attachments(session, post, files)

        post.updated_at = datetime.now(timezone.utc)
        session.add(post)
        session.flush()

        updated_post = session.scalar(
            select(Post)
            .where(Post.post_id == post_id)
            .options(selectinload(Post.attachments))
        )

        response = post_to_response(updated_post)

    await manager.broadcast({
        "event": "post_updated",
        "thread_id": response.thread_id,
        "post": response.model_dump(mode="json"),
    })

    return response


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post_attachment(attachment_id: uuid.UUID) -> None:
    with get_db_session() as session:
        attachment = session.scalar(
            select(PostAttachment).where(PostAttachment.attachment_id == attachment_id)
        )

        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")

        post = session.get(Post, attachment.post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        thread_id = post.thread_id.hex
        post_id = post.post_id

        session.delete(attachment)
        session.flush()

        updated_post = session.scalar(
            select(Post)
            .where(Post.post_id == post_id)
            .options(selectinload(Post.attachments))
        )

        response = post_to_response(updated_post)

    await manager.broadcast({
        "event": "post_updated",
        "thread_id": thread_id,
        "post": response.model_dump(mode="json"),
    })


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: uuid.UUID) -> None:
    with get_db_session() as session:
        post = session.get(Post, post_id)

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        thread_id = post.thread_id.hex
        session.delete(post)

    await manager.broadcast({
        "event": "post_deleted",
        "thread_id": thread_id,
        "post_id": post_id.hex,
    })


@router.get("/notifications", response_model=List[NotificationResponse])
async def list_notifications() -> List[NotificationResponse]:
    # Notifications are kept for future login/RBAC integration.
    # Since forum user identity is removed for now, return an empty list.
    return []


@router.patch("/notifications/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: uuid.UUID,
    request: MarkNotificationReadRequest,
) -> NotificationResponse:
    with get_db_session() as session:
        notification = session.get(Notification, notification_id)

        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        notification.is_read = request.is_read
        session.add(notification)
        session.flush()

        return notification_to_response(notification)


@router.websocket("/ws")
async def forum_websocket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
