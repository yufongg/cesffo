from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AttachmentResponse(BaseModel):
    attachment_id: str
    file_name: str
    file_url: str
    mime_type: str
    file_size: Optional[int] = None
    uploaded_at: datetime

class CreatePostRequest(BaseModel):
    content: str
    parent_id: Optional[str] = None

class PostResponse(BaseModel):
    post_id: str
    thread_id: str
    creator_id: Optional[str]
    creator_name: Optional[str] = None
    content: str
    is_edited: bool
    created_at: datetime
    updated_at: datetime
    attachments: List[AttachmentResponse] = []


class ThreadResponse(BaseModel):
    thread_id: str
    category_id: str
    creator_id: Optional[str]
    creator_name: Optional[str] = None
    title: str
    slug: str
    view_count: int
    is_locked: bool
    created_at: datetime
    updated_at: datetime
    post_count: int
    like_count: int = 0
    is_liked: bool = False


class CategoryResponse(BaseModel):
    category_id: str
    name: str
    slug: str
    description: Optional[str] = None
    display_order: int
    created_at: datetime
    threads: List[ThreadResponse] = []


class NotificationResponse(BaseModel):
    notification_id: str
    recipient_id: str
    actor_id: Optional[str]
    thread_id: Optional[str]
    post_id: Optional[str]
    notification_type: str
    message: str
    is_read: bool
    created_at: datetime


class UpdatePostRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class UpdateThreadRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=1, max_length=10000)


class MarkNotificationReadRequest(BaseModel):
    is_read: bool = True


class ThreadLikeResponse(BaseModel):
    thread_id: str
    user_id: str
    created_at: datetime

class CreateReportRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)

class ReportResponse(BaseModel):
    report_id: str
    reporter_id: str
    thread_id: Optional[str] = None
    post_id: Optional[str] = None
    reason: str
    description: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserReportResponse(BaseModel):
    report_id: str
    type: str
    title: str
    reason: str
    description: Optional[str]
    status: str
    created_at: datetime
    thread_id: Optional[str]
    category_id: Optional[str]
    reported_content: Optional[str] = None

    class Config:
        from_attributes = True