"""app/core/database/db.py

Database connection and session management.
"""

import os
from pathlib import Path
from typing import Generator

# ── Imports ─────────────────────────────────────────────────────────────────────────────
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

DB_PATH = Path(__file__).parent / "app_data.db"
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "SQLALCHEMY_DATABASE_URL", f"sqlite:///{DB_PATH}"
)

# Configure engine based on database type
connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    # Postgres closes idle pooled connections (seen in prod as
    # "SSL SYSCALL error: EOF detected"); pre-ping validates a
    # connection at checkout instead of failing the request.
    pool_pre_ping=True,
)

# Enable foreign key support for SQLite only
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine
)

def get_test_database_url() -> str:
    """
    Return the database URL for tests.

    Reads the SQLALCHEMY_DATABASE_URL environment variable if set,
    otherwise defaults to an in-memory SQLite database.
    """
    return os.environ.get("SQLALCHEMY_DATABASE_URL", "sqlite+pysqlite:///:memory:")


def get_session() -> Generator[Session, None, None]:
    """
    Dependency function to get a database session.

    Yields:
        Session: SQLAlchemy database session.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_session() -> Session:
    """
    Create a new database session.

    Returns:
        Session: New SQLAlchemy database session.

    Note:
        Remember to close the session when done:
        session = create_session()
        try:
            # use session
        finally:
            session.close()
    """
    return SessionLocal()


class DatabaseSession:
    """Context manager for database sessions."""

    def __init__(self):
        self.session = None

    def __enter__(self) -> Session:
        self.session = create_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            try:
                if exc_type is None:
                    self.session.commit()
                else:
                    self.session.rollback()
            finally:
                self.session.close()
