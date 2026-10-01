"""Journey maths: streak runs, levels and when a threshold was reached."""
from datetime import date, datetime, timedelta, timezone

from modules.backend.src.services.journey_service import _level, _nth, _runs


def test_runs_track_current_longest_and_when_each_length_was_reached():
    today = datetime.now(timezone.utc).date()
    days = {today - timedelta(days=i) for i in range(3)} | {date(2026, 1, 1), date(2026, 1, 2)}
    current, longest, reached = _runs(days)
    assert current == 3 and longest == 3
    assert reached[2] == "2026-01-02" and reached[3] == today.isoformat()


def test_a_gap_of_two_days_breaks_the_current_streak():
    today = datetime.now(timezone.utc).date()
    current, longest, _ = _runs({today - timedelta(days=2), today - timedelta(days=3)})
    assert current == 0 and longest == 2


def test_levels_grow_and_titles_change():
    assert _level(0)["level"] == 1 and _level(0)["title"] == "curious"
    assert _level(100)["level"] == 2 and _level(299)["level"] == 2 and _level(300)["level"] == 3
    lv = _level(650)
    assert lv["floor"] <= 650 < lv["next"] and lv["title"] == "scholar"


def test_nth_returns_the_date_of_the_nth_event():
    stamps = [datetime(2026, 5, d, tzinfo=timezone.utc) for d in (9, 1, 5)]
    assert _nth(stamps, 2) == "2026-05-05" and _nth(stamps, 4) is None
