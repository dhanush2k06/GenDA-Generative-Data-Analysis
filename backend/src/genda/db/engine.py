"""
SQLAlchemy engine and session factory for GenDA.
Hardened configuration:
- Connection pooling with recycle
- Strict SQL mode on MySQL
- Multi-statement execution disabled
- Bounded timeouts
- Clean healthcheck reporting (no connection strings or secrets)
"""

from __future__ import annotations
import os
import logging
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session

logger = logging.getLogger("genda.db")

# Base URL from environment or default to local MySQL
# Can be set to sqlite:///./genda_test.db or mysql+pymysql://...
DEFAULT_DB_URL = "mysql+pymysql://genda_app:genda_secret@127.0.0.1:3306/genda?charset=utf8mb4"
DATABASE_URL = os.environ.get("GENDA_DATABASE_URL", DEFAULT_DB_URL)

Base = declarative_base()

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    url = os.environ.get("GENDA_DATABASE_URL", DEFAULT_DB_URL)
    is_sqlite = url.startswith("sqlite")
    is_mysql = "mysql" in url

    connect_args = {}
    if is_mysql:
        connect_args = {
            "charset": "utf8mb4",
            "connect_timeout": 5,
            "read_timeout": 15,
            "write_timeout": 15,
        }
    elif is_sqlite:
        connect_args = {
            "check_same_thread": False,
        }

    engine_kwargs = {
        "pool_pre_ping": True,
        "future": True,
    }

    if not is_sqlite:
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 5
        engine_kwargs["pool_recycle"] = 1800
        engine_kwargs["pool_timeout"] = 10

    _engine = create_engine(url, connect_args=connect_args, **engine_kwargs)

    # Enforce strict SQL mode and foreign keys
    if is_mysql:
        @event.listens_for(_engine, "connect")
        def set_mysql_strict_mode(dbapi_connection, connection_record):
            with dbapi_connection.cursor() as cursor:
                cursor.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'")
    elif is_sqlite:
        @event.listens_for(_engine, "connect")
        def set_sqlite_foreign_keys(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


def get_db_session() -> Generator[Session, None, None]:
    """Dependency for obtaining a scoped SQLAlchemy session."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def check_db_health() -> dict[str, str | bool]:
    """
    Health check helper: reports connectivity status without exposing credentials or hostnames.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "connected": True}
    except Exception as e:
        logger.warning(f"Database health check failed: {type(e).__name__}")
        return {"status": "error", "connected": False}


def init_db(engine=None):
    """Initializes tables in database."""
    if engine is None:
        engine = get_engine()
    # Import all models to register with Base
    import genda.db.models  # noqa
    Base.metadata.create_all(bind=engine)


def reset_engine():
    """Reset engine and session factory (used in tests or URL changes)."""
    global _engine, _session_factory
    if _engine:
        _engine.dispose()
    _engine = None
    _session_factory = None

