"""Trial nudge times are day 5 and day 6 after the trial starts."""

from datetime import datetime, timedelta, timezone

from app.services.push_service import nudge_schedule


def test_nudges_are_five_and_six_days_out():
    start = datetime(2026, 11, 1, 15, 0, tzinfo=timezone.utc)
    schedule = dict(nudge_schedule(start))
    assert schedule["trial_day_5"] == start + timedelta(days=5)
    assert schedule["trial_day_6"] == start + timedelta(days=6)
