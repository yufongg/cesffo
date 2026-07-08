from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from model.models import User
from db.db import get_db_session


LOCKOUT_TIMER = 300


def account_lockout(username):
    current_time = datetime.now(timezone.utc)

    with get_db_session() as session:
        user = session.scalar(select(User).where(User.username == username))

        if not user:
            return False

        if not user.lockout_timestamp:
            user.lockout_timestamp = current_time
            session.commit()
            return True
        if current_time < (user.lockout_timestamp + timedelta(seconds=LOCKOUT_TIMER)):
            return True
    
        user.lockout_timestamp = None
        user.auth_attempts = 0
        session.commit()

    return False
