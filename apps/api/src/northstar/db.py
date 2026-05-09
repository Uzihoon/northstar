from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from northstar.config import get_settings

class Base(DeclarativeBase):
  pass

@lru_cache
def get_engine():
  settings = get_settings()
  return create_engine(settings.database_url, future=True)

@lru_cache
def get_session_factory():
  return sessionmaker(
    bind=get_engine(),
    class_=Session,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
  )

def get_session() -> Session:
  return get_session_factory()()
