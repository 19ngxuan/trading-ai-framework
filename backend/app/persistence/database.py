from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def normalize_sqlalchemy_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def get_database_url(database_url: str | None = None) -> str:
    resolved_url = database_url or get_settings().database_url
    if not resolved_url:
        raise RuntimeError("DATABASE_URL is required for database access.")
    return normalize_sqlalchemy_url(resolved_url)


def get_engine(database_url: str | None = None):
    return create_engine(get_database_url(database_url), pool_pre_ping=True)


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(database_url),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

def get_session() -> Generator[Session, None, None]:
    session_factory = create_session_factory()
    with session_factory() as session:
        yield session
