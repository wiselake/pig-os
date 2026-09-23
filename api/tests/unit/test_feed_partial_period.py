"""B-1 (2026-09-23): a month is complete only when its last day has passed in the FARM's timezone. The last day itself is
still partial (entries for it keep arriving). An unknown timezone falls back to the earliest date on earth (UTC-12)."""
from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.routers.base import feed_summary as fs

SEP_END = date(2026, 9, 30)


@pytest.mark.parametrize("now_utc,tz,expect_today,sep_partial", [
    # first minute of 1 Oct in Seoul = still 30 Sep in UTC
    (datetime(2026, 9, 30, 15, 0, 30, tzinfo=UTC), "Asia/Seoul", date(2026, 10, 1), False),
    (datetime(2026, 9, 30, 15, 0, 30, tzinfo=UTC), "UTC", date(2026, 9, 30), True),
    # exactly midnight 1 Oct Seoul — the boundary itself counts as complete
    (datetime(2026, 9, 30, 15, 0, 0, tzinfo=UTC), "Asia/Seoul", date(2026, 10, 1), False),
    # one second before that — last day still in progress
    (datetime(2026, 9, 30, 14, 59, 59, tzinfo=UTC), "Asia/Seoul", date(2026, 9, 30), True),
    # the last day, midday
    (datetime(2026, 9, 30, 12, 0, tzinfo=UTC), "UTC", date(2026, 9, 30), True),
    # first day of the month (UTC farm): the previous month is complete, the new one partial
    (datetime(2026, 10, 1, 0, 0, 1, tzinfo=UTC), "UTC", date(2026, 10, 1), False),
    # Americas: 1 Oct 02:00 UTC is still 30 Sep in Mexico City
    (datetime(2026, 10, 1, 2, 0, tzinfo=UTC), "America/Mexico_City", date(2026, 9, 30), True),
])
def test_farm_local_completion(monkeypatch, now_utc, tz, expect_today, sep_partial):
    monkeypatch.setattr(fs, "_now", lambda: now_utc)
    today, used = fs.farm_today(tz)
    assert (today, used) == (expect_today, tz)
    assert fs.period_is_partial(SEP_END, today) is sep_partial


@pytest.mark.parametrize("bad", ["Not/AZone", "", None, "../etc/passwd"])
def test_unknown_timezone_falls_back_to_earliest_date(monkeypatch, bad):
    # 1 Oct 05:00 UTC: already 1 Oct in UTC and Seoul, still 30 Sep at UTC-12 → September must not be declared complete
    monkeypatch.setattr(fs, "_now", lambda: datetime(2026, 10, 1, 5, 0, tzinfo=UTC))
    today, used = fs.farm_today(bad)
    assert today == date(2026, 9, 30) and used == "UTC-12(fallback)"
    assert fs.period_is_partial(SEP_END, today) is True


def test_future_month_is_partial():
    assert fs.period_is_partial(date(2026, 11, 30), date(2026, 9, 23)) is True
