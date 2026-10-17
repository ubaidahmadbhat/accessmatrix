"""Database engine and session management."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from accessmatrix.core.settings import get_settings


class Base(DeclarativeBase):
    """Base class for AccessMatrix database models."""


@lru_cache
def get_engine() -> Engine:
    """Create and cache the local SQLite engine."""

    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    database_path = (settings.data_dir / "accessmatrix.db").resolve()

    return create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return the application session factory."""

    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


def initialize_database() -> None:
    """Create the initial database tables."""

    import accessmatrix.persistence.models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def get_session() -> Generator[Session]:
    """Provide one database session."""

    factory = get_session_factory()

    with factory() as session:
        yield session
