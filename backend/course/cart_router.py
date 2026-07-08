from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from core.rate_limit import limiter
from common.security import parse_uid as _parse_uid, to_uuid as _to_uuid
from common.course_fields import (
    course_summary, course_level, course_tags, instructor_names as _instructor_names,
)
from db.db import get_db_session
from model.models import Cart, Course, CourseEnrollment, User
from model.constants import PaymentStatus

from user.auth_router import get_current_user
from stripe_integration.service import create_checkout_session


router = APIRouter(prefix="/api/v1/cart", tags=["Cart"])
DEFAULT_CURRENCY = "SGD"


# --- Data structures ---
class CartItem(BaseModel):
    course_id: str
    course_name: str
    instructor: Optional[str] = None
    summary: Optional[str] = None
    level: Optional[str] = None
    tags: List[str] = []
    xp_reward: int = 0
    price_cents: int = 0
    currency: str = DEFAULT_CURRENCY


class CartResponse(BaseModel):
    items: List[CartItem]
    item_count: int
    subtotal_cents: int
    currency: str = DEFAULT_CURRENCY


class CheckoutResponse(BaseModel):
    enrolled: List[str]
    skipped_already_enrolled: List[str]
    item_count: int
    total_cents: int
    currency: str = DEFAULT_CURRENCY
    redirect_url: str
    session_id: Optional[str] = None



# --- Helpers ---
def _safe_cart_ids(value) -> List[str]:
    if not isinstance(value, list):
        return []
    result = []
    seen = set()
    for raw in value:
        try:
            cid = UUID(str(raw)).hex
        except (TypeError, ValueError):
            continue
        if cid not in seen:
            seen.add(cid)
            result.append(cid)
    return result


def _get_or_create_cart(session, user_id: UUID) -> Cart:
    cart = session.scalar(select(Cart).where(Cart.user_id == user_id))
    if cart is None:
        cart = Cart(user_id=user_id, cart_items=[])
        session.add(cart)
        session.flush()
    return cart


def _active_enrolled_ids(session, user_id: UUID) -> set[UUID]:
    rows = session.scalars(
        select(CourseEnrollment.course_id).where(
            CourseEnrollment.student_id == user_id,
            CourseEnrollment.dropped.is_(False),
        )
    ).all()
    return set(rows)


def _cart_response(session, cart: Cart, user_id: UUID) -> CartResponse:
    cart_ids = _safe_cart_ids(cart.cart_items)
    if cart_ids != (cart.cart_items or []):
        cart.cart_items = cart_ids

    enrolled_ids = _active_enrolled_ids(session, user_id)
    course_ids = [UUID(raw) for raw in cart_ids]
    courses = session.scalars(select(Course).where(Course.course_id.in_(course_ids))).all() if course_ids else []
    by_id = {course.course_id: course for course in courses}

    # Keep only existing courses that the user has not already enrolled in.
    kept_ids = [
        raw for raw in cart_ids
        if UUID(raw) in by_id and UUID(raw) not in enrolled_ids
    ]
    if kept_ids != cart_ids:
        cart.cart_items = kept_ids

    ordered_courses = [by_id[UUID(raw)] for raw in kept_ids]
    names = _instructor_names(session, ordered_courses)
    items = [
        CartItem(
            course_id=course.course_id.hex,
            course_name=course.course_name,
            instructor=names.get(course.instructor_id),
            summary=course_summary(course),
            level=course_level(course),
            tags=course_tags(course),
            xp_reward=course.xp_reward or 0,
            price_cents=course.price_cents or 0,
            currency=course.currency or DEFAULT_CURRENCY,
        )
        for course in ordered_courses
    ]
    subtotal = sum(item.price_cents for item in items)
    currency = items[0].currency if items else DEFAULT_CURRENCY
    return CartResponse(items=items, item_count=len(items), subtotal_cents=subtotal, currency=currency)


# --- Routes ---
@router.get("", response_model=CartResponse)
@router.get("/", response_model=CartResponse)
async def get_cart(current_user: dict = Depends(get_current_user)):
    user_id = _parse_uid(current_user)
    with get_db_session() as session:
        cart = _get_or_create_cart(session, user_id)
        return _cart_response(session, cart, user_id)


@router.post("/items/{course_id}", response_model=CartResponse)
@limiter.limit("30/minute")
async def add_cart_item(course_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    user_id = _parse_uid(current_user)
    cid = _to_uuid(course_id)
    with get_db_session() as session:
        course = session.scalar(select(Course).where(Course.course_id == cid))
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        if (course.price_cents or 0) <= 0:
            raise HTTPException(status_code=400, detail="Free courses can be enrolled directly")

        if cid in _active_enrolled_ids(session, user_id):
            raise HTTPException(status_code=409, detail="You are already enrolled in this course")

        cart = _get_or_create_cart(session, user_id)
        items = _safe_cart_ids(cart.cart_items)
        if cid.hex not in items:
            items.append(cid.hex)
            cart.cart_items = items
            session.flush()
        return _cart_response(session, cart, user_id)


@router.delete("/items/{course_id}", response_model=CartResponse)
async def remove_cart_item(course_id: str, current_user: dict = Depends(get_current_user)):
    user_id = _parse_uid(current_user)
    cid = _to_uuid(course_id)
    with get_db_session() as session:
        cart = _get_or_create_cart(session, user_id)
        cart.cart_items = [raw for raw in _safe_cart_ids(cart.cart_items) if raw != cid.hex]
        session.flush()
        return _cart_response(session, cart, user_id)


@router.post("/checkout", response_model=CheckoutResponse)
@limiter.limit("10/minute")
async def checkout_cart(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = _parse_uid(current_user)
    with get_db_session() as session:
        checkout_user = session.get(User, user_id)
        if not checkout_user:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        
        cart = _get_or_create_cart(session, user_id)
        cart_ids = _safe_cart_ids(cart.cart_items)
        if not cart_ids:
            raise HTTPException(status_code=400, detail="Your cart is empty")

        course_ids = [UUID(raw) for raw in cart_ids]
        courses = session.scalars(select(Course).where(Course.course_id.in_(course_ids))).all()
        by_id = {course.course_id: course for course in courses}
        ordered_courses = [by_id[UUID(raw)] for raw in cart_ids if UUID(raw) in by_id]
        if not ordered_courses:
            cart.cart_items = []
            raise HTTPException(status_code=400, detail="Your cart is empty")

        enrolled = []
        skipped = []
        await_payment = []  # Store course objects here, not just IDs
        pending_enrollments = [] # Store new course enrollments that are waiting for user payment
        total = 0
        currency = ordered_courses[0].currency or DEFAULT_CURRENCY
        course_details = []  # Build course details for Stripe line items

        for course in ordered_courses:
            total += course.price_cents or 0
            existing = session.scalar(
                select(CourseEnrollment).where(
                    CourseEnrollment.course_id == course.course_id,
                    CourseEnrollment.student_id == user_id,
                )
            )
            if existing:
                if existing.payment_status == PaymentStatus.PAID:
                    if existing.dropped:
                        # Dropped after a completed purchase: reactivate
                        # without charging again.
                        existing.dropped = False
                        enrolled.append(course.course_id.hex)
                    else:
                        skipped.append(course.course_id.hex)
                    continue
                if not existing.dropped and existing.payment_status == PaymentStatus.PENDING:
                    # A checkout for this course is already in flight.
                    skipped.append(course.course_id.hex)
                    continue
                # Any other row never had a successful payment (failed,
                # refunded, or dropped mid-checkout): it must go through
                # Stripe again — reuse the row below, don't grant access here.


            # Build course details for Stripe line items from database
            content = course.content if isinstance(course.content, dict) else {}
            summary = content.get("summary", "")
            course_details.append({
                "id": course.course_id,
                "name": course.course_name,
                "price_cents": course.price_cents or 0,
                "currency": course.currency or DEFAULT_CURRENCY,
                "description": summary
            })

            if course.price_cents == 0:
                if existing is not None:
                    existing.dropped = False
                    existing.payment_status = PaymentStatus.PAID
                else:
                    session.add(CourseEnrollment(
                        course_id=course.course_id,
                        student_id=user_id,
                        progress=0.0,
                        dropped=False,
                        payment_status = PaymentStatus.PAID
                    ))
                enrolled.append(course.course_id.hex)
            elif existing is not None:
                # Reuse the never-paid row instead of inserting a duplicate.
                existing.dropped = False
                existing.payment_status = PaymentStatus.PENDING
                existing.stripe_payment_id = None  # replaced with the new session id below
                pending_enrollments.append(existing)
                await_payment.append(course)
            else:
                new_pending_enrollment = CourseEnrollment(
                    course_id=course.course_id,
                    student_id=user_id,
                    progress=0.0,
                    dropped=False,
                    payment_status = PaymentStatus.PENDING
                )
                session.add(new_pending_enrollment)
                pending_enrollments.append(new_pending_enrollment)
                await_payment.append(course)  # Store course object, not just ID

        
        # Clear cart and flush before redirect
        cart.cart_items = []
        session.flush()
        # Pass course details to create_checkout_session
        stripe_session = create_checkout_session(course_details, checkout_user)
        session_id = stripe_session.get("id")

        if session_id:
            for enrollment in pending_enrollments:
                enrollment.stripe_payment_id = session_id
            
            # Flush changes so they're sent to the database state engine
            session.flush()
        
        return CheckoutResponse(
            enrolled=enrolled,
            skipped_already_enrolled=skipped,
            item_count=len(ordered_courses),
            total_cents=total,
            currency=currency,
            redirect_url=stripe_session.get("url")
        )
