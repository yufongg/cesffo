import html
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status

from model.models import Notification, Post, PostAttachment, Thread, User
from .schemas import AttachmentResponse, NotificationResponse, PostResponse, ThreadResponse

try:
    import nh3
except Exception:  # pragma: no cover - fallback if dependency was not installed yet
    nh3 = None

UPLOAD_DIR = Path("uploads/forum")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIME_PREFIXES = ("image/",)
MAX_FILE_SIZE = 3 * 1024 * 1024  # 3 MB


def sanitize_content(content: str) -> str:
    """Allow limited rich-text HTML while reducing stored XSS risk."""
    content = content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Post content cannot be empty")

    allowed_tags = {
        "b", "strong", "i", "em", "u", "p", "br", "ul", "ol", "li",
        "blockquote", "code", "pre", "a", "span"
    }
    allowed_attributes = {
        "a": {"href", "title", "target", "rel"},
        "span": {"class"},
    }

    if nh3 is not None:
        return nh3.clean(content, tags=allowed_tags, attributes=allowed_attributes)

    # Safe fallback: escape everything if nh3 is unavailable.
    return html.escape(content)


def get_current_user(session, user_id: Optional[str]) -> User:
    """Temporary auth helper for the forum module until group auth integration is completed."""
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-User-ID header")
    try:
        parsed_user_id = uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid X-User-ID header") from exc

    user = session.get(User, parsed_user_id)
    if not user or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return user


def attachment_to_response(attachment: PostAttachment) -> AttachmentResponse:
    return AttachmentResponse(
        attachment_id=attachment.attachment_id.hex,
        file_name=attachment.file_name,
        file_url=attachment.file_url,
        mime_type=attachment.mime_type,
        file_size=attachment.file_size,
        uploaded_at=attachment.uploaded_at,
    )


def post_to_response(post: Post) -> PostResponse:
    return PostResponse(
        post_id=post.post_id.hex,
        thread_id=post.thread_id.hex,
        creator_id=post.creator_id.hex if post.creator_id else None,
        content=post.content,
        is_edited=post.is_edited,
        created_at=post.created_at,
        updated_at=post.updated_at,
        attachments=[attachment_to_response(item) for item in post.attachments],
    )


def thread_to_response(thread: Thread) -> ThreadResponse:
    top_level_posts = [post for post in thread.posts if post.parent_id is None]
    return ThreadResponse(
        thread_id=thread.thread_id.hex,
        category_id=thread.category_id.hex,
        creator_id=thread.creator_id.hex if thread.creator_id else None,
        title=thread.title,
        slug=thread.slug,
        view_count=thread.view_count,
        is_locked=thread.is_locked,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        post_count=len(top_level_posts),
    )


def notification_to_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        notification_id=notification.notification_id.hex,
        recipient_id=notification.recipient_id.hex,
        actor_id=notification.actor_id.hex if notification.actor_id else None,
        thread_id=notification.thread_id.hex if notification.thread_id else None,
        post_id=notification.post_id.hex if notification.post_id else None,
        notification_type=notification.notification_type,
        message=notification.message,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


async def save_attachments(session, post: Post, files: Optional[List[UploadFile]]) -> None:
    if not files:
        return

    for file in files:
        if not file.filename:
            continue
        if not file.content_type or not file.content_type.startswith(ALLOWED_MIME_PREFIXES):
            raise HTTPException(status_code=400, detail="Only image uploads are allowed")

        data = await file.read()
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Image file exceeds 3 MB limit")

        suffix = Path(file.filename).suffix.lower()
        safe_file_name = f"{uuid.uuid4().hex}{suffix}"
        target_path = UPLOAD_DIR / safe_file_name
        target_path.write_bytes(data)

        session.add(PostAttachment(
            post_id=post.post_id,
            file_name=file.filename,
            file_url=f"/uploads/forum/{safe_file_name}",
            mime_type=file.content_type,
            file_size=len(data),
        ))
