import re
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, UploadFile

from model.models import Notification, Post, PostAttachment, Thread, User
from common.sanitize import sanitize_html
from .schemas import AttachmentResponse, NotificationResponse, PostResponse, ThreadResponse

# Uploads live under a single, server-owned directory. Resolve it once so we can
# verify every write stays inside it (defence-in-depth against path traversal).
UPLOAD_DIR = (Path("uploads") / "forum").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

#! Allow-list keyed by the MIME we detect from the file's ACTUAL bytes -> the extension we assign.
#! The client-supplied content-type and filename are never trusted for storage (both are trivially forged).
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}
MAX_FILE_SIZE = 5 * 1024 * 1024   # 5 MB per image (matches the client validator)
MAX_FILES_PER_POST = 5
MAX_FILENAME_LENGTH = 120


def sanitize_content(content: str) -> str:
    """Strip to the project-wide SR-09 allow-list and reject empty content.

    Uses the same nh3 sanitizer as the course-authoring surface so forum posts
    can never carry script/style/event-handler/iframe payloads.
    """
    content = (content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Post content cannot be empty")
    cleaned = sanitize_html(content)
    # nh3 can legitimately reduce a markup-only payload (e.g. "<script>..</script>")
    # to nothing — treat that as empty rather than storing a blank post.
    if not cleaned.strip():
        raise HTTPException(status_code=400, detail="Post content cannot be empty")
    return cleaned


def safe_display_name(raw: Optional[str]) -> str:
    """A clean, human-readable name for display/logging only — never used for the
    on-disk path. Drops directories, control chars and anything exotic."""
    if not raw:
        return "image"
    base = re.split(r"[\\/]", raw)[-1]
    base = re.sub(r"[\x00-\x1f\x7f]", "", base)        # control chars
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)       # collapse exotic chars
    base = base.lstrip(".")                             # no leading dots (hidden files)
    base = base[:MAX_FILENAME_LENGTH].strip()
    return base or "image"


def detect_image_mime(data: bytes) -> Optional[str]:
    """Identify an image strictly from its magic bytes. Returns the canonical
    MIME for an allow-listed type, or None for anything else."""
    if len(data) < 12:
        return None
    if data[0:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[0:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[0:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None



def get_creator_name(session, creator_id) -> Optional[str]:
    """Return the display name for forum authors when a DB session is available."""
    if not session or not creator_id:
        return None
    user = session.get(User, creator_id)
    return user.username if user else None

def attachment_to_response(attachment: PostAttachment) -> AttachmentResponse:
    return AttachmentResponse(
        attachment_id=attachment.attachment_id.hex,
        file_name=attachment.file_name,
        file_url=attachment.file_url,
        mime_type=attachment.mime_type,
        file_size=attachment.file_size,
        uploaded_at=attachment.uploaded_at,
    )


def post_to_response(post: Post, session=None) -> PostResponse:
    return PostResponse(
        post_id=post.post_id.hex,
        thread_id=post.thread_id.hex,
        creator_id=post.creator_id.hex if post.creator_id else None,
        creator_name=get_creator_name(session, post.creator_id),
        content=post.content,
        is_edited=post.is_edited,
        created_at=post.created_at,
        updated_at=post.updated_at,
        attachments=[attachment_to_response(item) for item in post.attachments],
    )


def thread_to_response(thread: Thread, session=None, like_count: int = 0, is_liked: bool = False,) -> ThreadResponse:
    top_level_posts = [post for post in thread.posts if post.parent_id is None]
    return ThreadResponse(
        thread_id=thread.thread_id.hex,
        category_id=thread.category_id.hex,
        creator_id=thread.creator_id.hex if thread.creator_id else None,
        creator_name=get_creator_name(session, thread.creator_id),
        title=thread.title,
        slug=thread.slug,
        view_count=thread.view_count,
        is_locked=thread.is_locked,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        post_count=len(top_level_posts),
        like_count=like_count,
        is_liked=is_liked,
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
    """Validate and persist image attachments for a post.

    Security: the file type is decided by its magic bytes (not the client-sent
    content-type), the on-disk name is a server-generated UUID with an extension
    derived from the detected type, and the write target is verified to stay
    inside UPLOAD_DIR. Count and per-file size are both capped.
    """
    if not files:
        return

    real_files = [f for f in files if f and f.filename]
    if not real_files:
        return
    if len(real_files) > MAX_FILES_PER_POST:
        raise HTTPException(
            status_code=400, detail=f"At most {MAX_FILES_PER_POST} images may be attached"
        )

    for file in real_files:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Empty file is not allowed")
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Image exceeds the {MAX_FILE_SIZE // (1024 * 1024)} MB limit",
            )

        detected_mime = detect_image_mime(data)
        if detected_mime is None:
            raise HTTPException(
                status_code=400,
                detail="Only JPEG, PNG, GIF or WebP images are allowed",
            )

        extension = ALLOWED_IMAGE_TYPES[detected_mime]
        stored_name = f"{uuid.uuid4().hex}.{extension}"
        target_path = (UPLOAD_DIR / stored_name).resolve()
        #! Defence-in-depth path-traversal check: a generated UUID name can't escape the
        #! upload dir, but verify the resolved parent is exactly UPLOAD_DIR before writing.
        if target_path.parent != UPLOAD_DIR:
            raise HTTPException(status_code=400, detail="Invalid upload path")

        target_path.write_bytes(data)

        session.add(PostAttachment(
            post_id=post.post_id,
            file_name=safe_display_name(file.filename),
            file_url=f"/uploads/forum/{stored_name}",
            mime_type=detected_mime,   # store the detected type, not the client's
            file_size=len(data),
        ))
