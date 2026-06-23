import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Boolean, Float, DateTime, JSON, ForeignKey,
    PrimaryKeyConstraint, UniqueConstraint, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.db import Base

# --- USER MODEL ---
class User(Base):
    __tablename__ = "user"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(150), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    auth_attempts = Column(Integer, default=0, nullable=False)
    lockout_timestamp = Column(DateTime(timezone=True), nullable=True)
    role = Column(String(50), default="student", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    force_password_reset = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    #? Gamification / leaderboard fields
    xp = Column(Integer, default=0, nullable=False)                 # lifetime XP earned (drives leaderboards)
    level = Column(Integer, default=1, nullable=False)              # derived from xp; stored for fast ranking

    # Relationships
    # enrollments = relationship("CourseEnrollment", back_populates="student", cascade="all, delete-orphan")
    cart = relationship("Cart", back_populates="user", uselist=False, cascade="all, delete-orphan")
    liked_posts = relationship("PostLikes", back_populates="user", cascade="all, delete-orphan")


# --- CATEGORY MODEL ---
class Category(Base):
    __tablename__ = "category"

    category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    description = Column(String(500))
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)

    # Relationships
    threads = relationship("Thread", back_populates="category", cascade="all, delete-orphan")


# -- THREAD MODEL --- 
class Thread(Base):
    __tablename__ = "thread"

    thread_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys with cascading enforcement
    category_id = Column(UUID(as_uuid=True), ForeignKey("category.category_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)
    view_count = Column(Integer, default=0, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), onupdate=lambda:datetime.now(timezone.utc), nullable=False)

    # Relationships
    category = relationship("Category", back_populates="threads")
    posts = relationship("Post", back_populates="thread", cascade="all, delete-orphan")


# --- POST MODEL ---
class Post(Base):
    __tablename__ = "post"

    post_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("thread.thread_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    
    # Self-referential loop for nested parent-child comment threads
    parent_id = Column(UUID(as_uuid=True), ForeignKey('post.post_id', ondelete='SET NULL', onupdate="CASCADE"), nullable=True)
    
    content = Column(Text, nullable=False)
    is_edited = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), onupdate=lambda:datetime.now(timezone.utc), nullable=False)

    # Relationships
    thread = relationship("Thread", back_populates="posts")
    parent = relationship("Post", remote_side=[post_id], back_populates="replies")
    replies = relationship("Post", back_populates="parent")
    
    # Hierarchy mappings
    likes = relationship("PostLikes", back_populates="post", cascade="all, delete-orphan")

    attachments = relationship("PostAttachment", back_populates="post", cascade="all, delete-orphan")
    reports = relationship("PostReport", back_populates="post", cascade="all, delete-orphan")

# --- POST LIKES MODEL ---
class PostLikes(Base):
    __tablename__ = "post_likes"

    post_id = Column(UUID(as_uuid=True), ForeignKey("post.post_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    liked_time = Column(DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)

    # Table-level composite primary key constraint
    __table_args__ = (
        PrimaryKeyConstraint("post_id", "user_id"),
    )

    # Relationships
    post = relationship("Post", back_populates="likes")
    user = relationship("User", back_populates="liked_posts")


# --- COURSE MODEL ---
class Course(Base):
    __tablename__ = "course"

    course_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instructor_id = Column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    course_name = Column(String(255), nullable=False)
    xp_reward = Column(Integer, default=0, nullable=False)        # XP awarded to a learner on completion

    content = Column(JSON, nullable=False, default=dict)          # Maps structure JSON block
    tags = Column(JSON, nullable=False, default=list)             # Maps str[] as JSON Array array list
    prerequirements = Column(JSON, nullable=False, default=dict)  # Maps dict parameters
    
    created_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), onupdate=lambda:datetime.now(timezone.utc), nullable=False)

    # Relationships
    enrollments = relationship("CourseEnrollment", back_populates="course", cascade="all, delete-orphan")
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan", order_by="Module.order_index")


# --- MODULE MODEL ---
class Module(Base):
    __tablename__ = "module"

    module_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.course_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)  # sanitized (nh3) HTML/rich text
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), onupdate=lambda:datetime.now(timezone.utc), nullable=False)

    # Relationships
    course = relationship("Course", back_populates="modules")
    reading_materials = relationship("ReadingMaterial", back_populates="module", cascade="all, delete-orphan", order_by="ReadingMaterial.order_index")
    media_contents = relationship("MediaContent", back_populates="module", cascade="all, delete-orphan", order_by="MediaContent.order_index")
    activities = relationship("InteractiveActivity", back_populates="module", cascade="all, delete-orphan", order_by="InteractiveActivity.order_index")


# --- READING MATERIAL MODEL ---
class ReadingMaterial(Base):
    __tablename__ = "reading_material"

    material_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey("module.module_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)  # sanitized (nh3) HTML/rich text
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), onupdate=lambda:datetime.now(timezone.utc), nullable=False)

    # Relationships
    module = relationship("Module", back_populates="reading_materials")


# --- MEDIA CONTENT MODEL ---
class MediaContent(Base):
    __tablename__ = "media_content"

    media_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey("module.module_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    media_url = Column(String(2048), nullable=False)
    media_type = Column(String(50), nullable=False)  # "video" | "image" | "audio" | "document"
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), onupdate=lambda:datetime.now(timezone.utc), nullable=False)

    # Relationships
    module = relationship("Module", back_populates="media_contents")


# --- INTERACTIVE ACTIVITY MODEL ---
class InteractiveActivity(Base):
    __tablename__ = "interactive_activity"

    activity_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey("module.module_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    activity_type = Column(String(30), nullable=False)  # "mcq_single" | "mcq_multi" | "short_answer"
    prompt = Column(Text, nullable=False)  # sanitized (nh3) HTML/rich text

    # Grading key for short-answer questions — server-side only, NEVER serialized
    # to a student response. MCQ correctness lives on ActivityOption.is_correct.
    correct_answers = Column(JSON, nullable=True)  # list[str], case/whitespace-insensitive match
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), onupdate=lambda:datetime.now(timezone.utc), nullable=False)

    # Relationships
    module = relationship("Module", back_populates="activities")
    options = relationship("ActivityOption", back_populates="activity", cascade="all, delete-orphan", order_by="ActivityOption.order_index")
    submissions = relationship("ActivitySubmission", back_populates="activity", cascade="all, delete-orphan")


# --- ACTIVITY OPTION MODEL (MCQ choices) ---
class ActivityOption(Base):
    __tablename__ = "activity_option"

    option_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id = Column(UUID(as_uuid=True), ForeignKey("interactive_activity.activity_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    option_text = Column(String(1000), nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)  # NEVER serialize to a student
    order_index = Column(Integer, default=0, nullable=False)

    # Relationships
    activity = relationship("InteractiveActivity", back_populates="options")


# --- ACTIVITY SUBMISSION MODEL ---
class ActivitySubmission(Base):
    __tablename__ = "activity_submission"

    submission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id = Column(UUID(as_uuid=True), ForeignKey("interactive_activity.activity_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    response = Column(JSON, nullable=False)  # {"option_ids": [hex,...]} or {"text": "..."}
    is_correct = Column(Boolean, nullable=False)
    score = Column(Float, default=0.0, nullable=False)
    attempt_number = Column(Integer, default=1, nullable=False)
    submitted_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)

    # Relationships
    activity = relationship("InteractiveActivity", back_populates="submissions")


# --- MODULE PROGRESS MODEL (per student) ---
class ModuleProgress(Base):
    __tablename__ = "module_progress"

    progress_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey("module.module_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("module_id", "student_id", name="uq_module_progress_module_student"),
    )


# --- AUDIT LOG MODEL (append-only; SR-11) ---
class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    action = Column(String(100), nullable=False)            # e.g. "delete_course", "delete_module"
    resource_type = Column(String(50), nullable=True)       # e.g. "course", "module", "activity"
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    outcome = Column(String(20), nullable=False, default="success")  # "success" | "failure"
    ip_address = Column(String(64), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)

# --- POST ATTACHMENT MODEL ---
class PostAttachment(Base):
    __tablename__ = "post_attachment"

    attachment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("post.post_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)

    file_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=True)

    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    post = relationship("Post", back_populates="attachments")


# --- POST REPORT MODEL ---
class PostReport(Base):
    __tablename__ = "post_report"

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("post.post_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)

    reason = Column(String(500), nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)

    post = relationship("Post", back_populates="reports")

# --- COURSE ENROLLMENT MODEL ---
class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"

    enrollment_id = Column(Integer, primary_key=True, autoincrement=True) # serial id, do not use on client side
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.course_id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="SET NULL"), nullable=True)
    progress = Column(Float, default=0.0, nullable=False)
    enrolled_date = Column(DateTime, default=lambda:datetime.now(timezone.utc), nullable=False)
    dropped = Column(Boolean, default=False, nullable=False)

    
    # Relationships
    course = relationship("Course", back_populates="enrollments")
    # student = relationship("User", back_populates="enrollments")

# --- NOTIFICATION MODEL ---
class Notification(Base):
    __tablename__ = "notification"

    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    recipient_id = Column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)

    thread_id = Column(UUID(as_uuid=True), ForeignKey("thread.thread_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("post.post_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=True)

    notification_type = Column(String(50), nullable=False)
    message = Column(String(500), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
# --- CART MODEL --- 
class Cart(Base):
    __tablename__ = "carts"

    cart_id = Column(Integer, primary_key=True, autoincrement=True) # serial id, do not use on client side
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.user_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, unique=True)
    
    cart_items = Column(JSON, nullable=False, default=list) # array representation of course objects stored as json

    user = relationship("User", back_populates="cart")