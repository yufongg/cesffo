import os
import pytest
from sqlalchemy import text

from db.db import SessionLocal, get_db_session
from model.models import User, Cart
from common.encryption import blind_index

def test_database_connection_direct():
    #* Smoke test: open a raw session and run the simplest possible query.
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1, "Database returned unexpected response value."
    except Exception as e:
        pytest.fail(f"Failed to connect to the database: {e}")
    finally:
        db.close()

def test_context_manager_session():
    #* Confirm get_db_session() yields a working session and runs a query end to end.
    with get_db_session() as session:
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1
    #^ The context manager's finally block guarantees the session is closed by here.

def test_database():
    #* Verify we're connected to the database named by the DB_NAME env var, not some other one.
    expected_db = os.getenv("DB_NAME", "db")

    with get_db_session() as session:
        current_db_name = session.execute(text("SELECT current_database()")).scalar()
        assert current_db_name == expected_db, (f"Database mismatch! Connected to '{current_db_name}' but expected '{expected_db}'")
    
def test_db_models():
    #* End-to-end ORM check: create a User + Cart, then read the relationship back.
    try:
        with get_db_session() as session:
            email = "test@example.com"
            session.query(User).filter(User.email_bidx == blind_index(email)).delete()
            session.commit()

            test_user = User(
                username="test_runner",
                password="hashed_secure_password_string",
                email=email,
                email_bidx=blind_index(email),  #? required companion blind index for the encrypted email
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

            #* Clean up the rows this test created.
            session.delete(test_user)
            session.commit()
    except Exception as e:
        pytest.fail(f"Model integrity test failed: {e}")
