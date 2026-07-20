from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Connection-pool tuning notes:
# - MySQL's wait_timeout on this machine is 120s. Any idle connection older
#   than that will be closed by the server. pool_pre_ping detects dead
#   connections at borrow time; pool_recycle proactively recycles them
#   before the server does (set well below wait_timeout for safety margin).
# - pool_size=5 + max_overflow=5 is plenty for a single-machine backend
#   where each request/stage opens a short session.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=60,        # < MySQL wait_timeout (120s)
    pool_size=5,
    max_overflow=5,
    pool_timeout=30,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()