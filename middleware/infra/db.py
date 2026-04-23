from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from middleware.infra.models import Base
from middleware.infra.settings import settings

_engine: Engine | None = None
_session_local: sessionmaker[Session] | None = None


def configure_engine(database_url: str) -> None:
    global _engine, _session_local
    if _engine is not None:
        _engine.dispose()
    _engine = create_engine(database_url, pool_pre_ping=True, future=True)
    _session_local = sessionmaker(
        bind=_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        configure_engine(settings.database_url)
    assert _engine is not None
    return _engine


def get_session_local() -> sessionmaker[Session]:
    global _session_local
    if _session_local is None:
        configure_engine(settings.database_url)
    assert _session_local is not None
    return _session_local


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_local()()
    try:
        yield session
    finally:
        session.close()
