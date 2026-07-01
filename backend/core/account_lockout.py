from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from model.models import User
from db.db import get_db_session


#$ How long an account stays locked after too many failed logins (seconds).
LOCKOUT_TIMER = 300


def account_lockout(username):
    #* Returns True while the account should stay locked, False once it's free to try again.
    current_time = datetime.now(timezone.utc)

    with get_db_session() as session:
        user = session.scalar(select(User).where(User.username == username))

        #^ Unknown user: nothing to lock, let the caller fall through to the normal "bad creds" path.
        if not user:
            return False

        #! First time over the limit: stamp the lockout start and lock them out now.
        if not user.lockout_timestamp:
            user.lockout_timestamp = current_time
            session.commit()
            return True

        #! Still inside the lockout window -> keep them locked.
        if current_time < (user.lockout_timestamp + timedelta(seconds=LOCKOUT_TIMER)):
            return True

        #* Window has elapsed: clear the lockout and reset the failed-attempt counter so they can retry.
        user.lockout_timestamp = None
        user.auth_attempts = 0
        session.commit()

    return False
