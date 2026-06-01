import os
import pytest
from sqlalchemy import text


from db.db import SessionLocal, get_db_session
from model.models import User

def test_database_connection_direct():
    """
    Directly tests if SQLAlchemy can initiate a session, communicate 
    with the database socket, and execute a basic query expression.
    """
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1, "Database returned unexpected response value."
    except Exception as e:
        pytest.fail(f"Failed to connect to the database engine layout: {e}")
    finally:
        db.close()

def test_context_manager_session():
    """
    Tests that the 'get_db_session' context manager functions as 
    intended and successfully commits or handles operational logic loops.
    """
    with get_db_session() as session:
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1
    # Session is guaranteed closed here by the context manager's finally block

def test_database():
    """Verify application connects to the correct database expected by system configurations(environment variables)."""

    expected_db = os.getenv("DB_NAME", "db")

    with get_db_session() as session:
        current_db_name = session.execute(text("SELECT current_database()")).scalar()
        assert current_db_name == expected_db, (f"Database mismatch! Connected to '{current_db_name}' but expected '{expected_db}'")
    
def test_db_models():
    try:
        with get_db_session as session:
            session.query(User).filter(User.email == "test@example.com").delete()
            session.commit()

            test_user = User(
                username="test_runner",
                password="hashed_secure_password_string",
                email="test@example.com"
            )
            session.add(test_user)
            session.commit()
            session.refresh(test_user)

            user_cart = Cart(user_id=test_user.user_id, cart_items=["course_id_1", "course_id_2"])
            session.add(user_cart)
            session.commit()
            session.refresh(test_user)

            assert test_user.cart is not None
            assert test_user.cart.cart_items == ["course_id_1", "course_id_2"]

            # Cleanup test data
            session.delete(test_user)
            session.commit()
    except Exception as e:
        pytest.fail("Model integrity test faulted {e}")