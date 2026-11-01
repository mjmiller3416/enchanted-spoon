"""Run the free-tier sunset migration and reminder hooks.

    python -m app.scripts.free_tier_sunset

Before the configured sunset date the migration changes nothing. Reminders
fire 30, 7, and 1 days before that date. Schedule this daily. It does not
call Stripe.
"""

from app.database.db import SessionLocal
from app.services.free_tier_sunset import apply_free_tier_sunset, send_due_reminders


def main() -> None:
    session = SessionLocal()
    try:
        migrated = apply_free_tier_sunset(session)
        reminded = send_due_reminders(session)
        session.commit()
        print(f"read_only_migrated={migrated} reminders_sent={reminded}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
