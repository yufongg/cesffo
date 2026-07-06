import os

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST", "db")  
DB_PORT = os.getenv("DB_PORT", "5432")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL,
    pool_size=10,          #$ baseline pooled connections
    max_overflow=20,       #$ extra connections opened under load (so 30 total max)
    pool_pre_ping=True     #* test a connection's health before use, so stale ones are recycled not handed out
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

@contextmanager
def get_db_session():
    #* One transaction per `with` block: commit on clean exit, roll back on any error.
    #^ So callers normally only need session.flush() (to get generated ids) — not commit().
    session = SessionLocal()
    try:
        yield session
        session.commit()    #* success path: persist everything done in the block
    except Exception:
        session.rollback()  #! any unhandled error: undo the whole block, then re-raise
        raise
    finally:
        session.close()     #* always return the connection to the pool
