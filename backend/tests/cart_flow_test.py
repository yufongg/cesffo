import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from course import cart_router, learn_router


# Minimal request object needed by route functions with rate-limit decorators
def _request(method="POST"):
    return Request({
        "type": "http",
        "method": method,
        "path": "/",
        "headers": [],
        "client": ("testclient", 50000),
    })


# Small wrappers that mimic the SQLAlchemy result objects used by the router
class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _ExecuteResult(_ScalarResult):
    pass


# Context manager returned when tests patch get_db_session
class _SessionCtx:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, *_args):
        return False


# Fake DB session that returns controlled cart, course, and enrollment rows
class _FakeCartSession:
    def __init__(self, *, course, cart=None, enrolled=False, user=None):
        self.course = course
        self.cart = cart
        self.enrolled = enrolled
        self.user = user
        self.added = []
        self.flushed = 0

    def scalar(self, stmt):
        text = str(stmt).lower()
        if "from course_enrollments" in text:
            return SimpleNamespace(dropped=False) if self.enrolled else None
        if "from carts" in text:
            return self.cart
        if "from course" in text:
            return self.course
        return None

    def scalars(self, stmt):
        text = str(stmt).lower()
        if "from course_enrollments" in text:
            return _ScalarResult([self.course.course_id] if self.enrolled else [])
        if "from course" in text:
            return _ScalarResult([self.course])
        return _ScalarResult([])

    def execute(self, *_args, **_kwargs):
        return _ExecuteResult([])

    def get(self, model, ident):
        if model.__name__ == "User":
            return self.user
        return None

    def add(self, obj):
        self.added.append(obj)
        if obj.__class__.__name__ == "Cart":
            self.cart = obj

    def flush(self):
        self.flushed += 1

    def commit(self):
        pass


# Helpers for building course and cart objects without a real database
def _course(*, price_cents=1299):
    cid = uuid4()
    return SimpleNamespace(
        course_id=cid,
        instructor_id=uuid4(),
        course_name="Paid Course",
        content={"summary": "Server-owned summary"},
        prerequirements={"level": "Beginner"},
        tags=["Budgeting"],
        xp_reward=500,
        price_cents=price_cents,
        currency="SGD",
    )


def _cart(user_id, items=None):
    return SimpleNamespace(user_id=user_id, cart_items=list(items or []))


# Adding to cart should persist once, and removing a missing item should be safe
def test_add_course_to_cart_is_persistent_and_idempotent(monkeypatch):
    user_id = uuid4()
    course = _course()
    cart = _cart(user_id)
    session = _FakeCartSession(course=course, cart=cart)
    monkeypatch.setattr(cart_router, "get_db_session", lambda: _SessionCtx(session))

    current_user = {"user_id": user_id.hex, "role": "student"}
    first = asyncio.run(cart_router.add_cart_item(course.course_id.hex, _request(), current_user))
    second = asyncio.run(cart_router.add_cart_item(course.course_id.hex, _request(), current_user))

    assert cart.cart_items == [course.course_id.hex]
    assert first.item_count == 1
    assert second.item_count == 1
    assert second.subtotal_cents == course.price_cents


def test_remove_course_from_cart_is_safe_when_missing(monkeypatch):
    user_id = uuid4()
    course = _course()
    cart = _cart(user_id, [course.course_id.hex])
    session = _FakeCartSession(course=course, cart=cart)
    monkeypatch.setattr(cart_router, "get_db_session", lambda: _SessionCtx(session))

    current_user = {"user_id": user_id.hex, "role": "student"}
    response = asyncio.run(cart_router.remove_cart_item(uuid4().hex, current_user))

    assert cart.cart_items == [course.course_id.hex]
    assert response.item_count == 1


# Cart responses should recalculate price from Course and drop enrolled courses
def test_cart_response_hydrates_current_course_price_and_drops_enrolled():
    user_id = uuid4()
    course = _course(price_cents=2499)
    cart = _cart(user_id, [course.course_id.hex])
    session = _FakeCartSession(course=course, cart=cart, enrolled=True)

    response = cart_router._cart_response(session, cart, user_id)

    assert response.items == []
    assert response.subtotal_cents == 0
    assert cart.cart_items == []


# Checkout should enroll cart courses, clear the cart, and reject empty checkout
def test_checkout_enrolls_courses_and_clears_cart(monkeypatch):
    user_id = uuid4()
    course = _course(price_cents=1999)
    cart = _cart(user_id, [course.course_id.hex])
    fake_user = SimpleNamespace(user_id=user_id, email="test@example.com")
    session = _FakeCartSession(course=course, cart=cart, enrolled=False, user=fake_user)
    monkeypatch.setattr(cart_router, "get_db_session", lambda: _SessionCtx(session))
    monkeypatch.setattr(cart_router, "create_checkout_session",
                        lambda details, user: {"id": "cs_test_123", "url": "https://checkout.example.com/pay"})

    current_user = {"user_id": user_id.hex, "role": "student"}
    response = asyncio.run(cart_router.checkout_cart(_request(), current_user))

    assert response.enrolled == []
    assert response.total_cents == 1999
    assert cart.cart_items == []
    assert any(obj.__class__.__name__ == "CourseEnrollment" for obj in session.added)


def test_checkout_rejects_empty_cart(monkeypatch):
    user_id = uuid4()
    fake_user = SimpleNamespace(user_id=user_id, email="test@example.com")
    session = _FakeCartSession(course=_course(), cart=_cart(user_id), user=fake_user)
    monkeypatch.setattr(cart_router, "get_db_session", lambda: _SessionCtx(session))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(cart_router.checkout_cart(_request(), {"user_id": user_id.hex, "role": "student"}))

    assert exc.value.status_code == 400


# Direct enrollment should stay available for free courses only
def test_paid_course_direct_enrollment_is_rejected(monkeypatch):
    user_id = uuid4()
    course = _course(price_cents=1299)
    session = _FakeCartSession(course=course)
    monkeypatch.setattr(learn_router, "get_db_session", lambda: _SessionCtx(session))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(learn_router.enroll_course(course.course_id.hex, _request(), {"user_id": user_id.hex, "role": "student"}))

    assert exc.value.status_code == 402


def test_free_course_direct_enrollment_still_works(monkeypatch):
    user_id = uuid4()
    course = _course(price_cents=0)
    session = _FakeCartSession(course=course)
    monkeypatch.setattr(learn_router, "get_db_session", lambda: _SessionCtx(session))

    response = asyncio.run(
        learn_router.enroll_course(course.course_id.hex, _request(), {"user_id": user_id.hex, "role": "student"})
    )

    assert response.enrolled is True
    assert response.course_id == course.course_id.hex
    assert any(obj.__class__.__name__ == "CourseEnrollment" for obj in session.added)
