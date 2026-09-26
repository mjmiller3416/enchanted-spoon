#!/usr/bin/env python3
"""
Add (or remove) the onboarding starter pack for an existing account.

New accounts get it automatically on first sign-in; use this for accounts
that pre-date it, the AUTH_DISABLED dev user, or to reset a test account.

Usage:
    python scripts/seed_sample_data.py --user-id 1
    python scripts/seed_sample_data.py --email someone@example.com
    python scripts/seed_sample_data.py --user-id 1 --remove
    python scripts/seed_sample_data.py --user-id 1 --database-url "postgresql://..."
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker


def create_db_session(database_url: str | None = None) -> Session:
    """Create a session against the given URL, or the app's configured database."""
    if database_url:
        is_sqlite = database_url.startswith("sqlite")
        engine = create_engine(
            database_url, connect_args={"check_same_thread": False} if is_sqlite else {}
        )
        if is_sqlite:
            # Removal relies on ON DELETE CASCADE, which SQLite only enforces with this on
            @event.listens_for(engine, "connect")
            def _enable_foreign_keys(dbapi_connection, _record):
                dbapi_connection.execute("PRAGMA foreign_keys=ON")

        return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    from app.database.db import SessionLocal

    return SessionLocal()


def main() -> None:
    parser = argparse.ArgumentParser(description="Add or remove the onboarding starter pack")
    who = parser.add_mutually_exclusive_group(required=True)
    who.add_argument("--user-id", type=int, help="Target user ID")
    who.add_argument("--email", type=str, help="Target user email")
    parser.add_argument("--remove", action="store_true", help="Remove untouched sample content instead")
    parser.add_argument("--database-url", type=str, default=None, help="Database URL (defaults to app config)")
    args = parser.parse_args()

    import app.models  # noqa: F401 – register all models
    from app.models.user import User
    from app.services.sample_data import SampleDataAlreadyPresentError, SampleDataService

    session = create_db_session(args.database_url)
    try:
        stmt = (
            select(User).where(User.id == args.user_id)
            if args.user_id is not None
            else select(User).where(User.email == args.email)
        )
        user = session.execute(stmt).scalars().first()
        if not user:
            print("Error: user not found.")
            sys.exit(1)

        service = SampleDataService(session, user.id)
        print(f"User: {user.name or ''} <{user.email}> (id={user.id})")

        if args.remove:
            result = service.remove()
            print(
                f"Removed {result.recipes_removed} recipes and {result.meals_removed} meals "
                f"(kept {result.recipes_kept} recipes the user's own meals use)."
            )
            return

        try:
            result = service.seed()
        except SampleDataAlreadyPresentError:
            print("Sample data is already in this account. Use --remove first to reset it.")
            sys.exit(1)
        print(
            f"Added {result.recipes_created} recipes, {result.meals_created} meals, "
            f"and {result.planner_entries_created} planner entries."
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
