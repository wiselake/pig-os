"""snapshot 직렬화·해시·scope 와 reconcile 의 기대 집계 — 합성 행, DB 없음 (L0-B / L1 도구 자체의 정확성)."""
from __future__ import annotations

import random
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.harvest import feed_source_reconcile as rc
from app.harvest import feed_source_snapshot as snap
from app.harvest import pigplan_feed_delivery as pf

T = date(2026, 9, 22)


def row(farm, seq, d="2026-08-10", kg="100", price="500", use="Y", acct="410002"):
    return pf.PigPlanFeedDeliveryRow(source_farm_no=farm, seq=seq, wk_dt=date.fromisoformat(d) if d else None, wk_dt_raw=d,
                                     total_kg=Decimal(kg), fper_price=Decimal(price), total_price=Decimal(price) * Decimal(kg),
                                     feed_stage_cd="100005", feed_stage_name="비육돈", feed_cd=1, feed_name="P", use_yn=use,
                                     account_cd=acct, gain_yn="M", country_code="KOR", has_supplier=True,
                                     source_inserted_at=datetime(2026, 8, 11, tzinfo=UTC), source_updated_at=datetime(2026, 8, 11, tzinfo=UTC))


def test_snapshot_roundtrip_and_order_independent_hash(tmp_path):
    rows = [row(1, 1), row(1, 2, d="2026-07-05"), row(2, 1, use="N"), row(2, 2, d=None)]
    meta = snap.summarize(rows, [1, 2], date(2026, 7, 1), date(2026, 8, 31), extracted_at=datetime(2026, 9, 22, tzinfo=UTC))
    p = tmp_path / "s.json"
    snap.save(p, rows, meta)
    back, m2 = snap.load(p)
    assert back == rows and m2["row_count"] == 4 and m2["farm_count"] == 2 and m2["dateless_rows"] == 1
    assert m2["use_yn_distribution"] == {"Y": 3, "non-Y": 1}
    shuffled = rows[:]
    random.Random(7).shuffle(shuffled)
    assert snap.content_hash(shuffled) == snap.content_hash(rows) == m2["content_hash"]
    assert snap.scope_hash([2, 1], date(2026, 7, 1), date(2026, 8, 31)) == snap.scope_hash([1, 2], date(2026, 7, 1), date(2026, 8, 31))
    assert snap.scope_hash([1], date(2026, 7, 1), date(2026, 8, 31)) != m2["source_scope_hash"]


def test_snapshot_source_applies_window_and_farm_filters(tmp_path):
    rows = [row(1, 1), row(1, 2, d="2026-06-05"), row(3, 1)]
    src = snap.SnapshotSource(rows, {})
    got = src.fetch_rows([1], date(2026, 7, 1), date(2026, 8, 31))
    assert [r.seq for r in got] == [1]
    assert src.farms_with_rows([1, 3], date(2026, 7, 1), date(2026, 8, 31)) == [1, 3]


def test_expected_counts_by_grain_and_status():
    rows = [row(1, 1), row(1, 2, d="2026-07-05"), row(1, 3, use="N"), row(1, 4, kg="0"), row(2, 1, acct="512001"),
            row(2, 2, d="2026-09-30"),      # 창 밖
            row(9, 1)]                      # scope 밖 농장
    e = rc.expected_from_rows(rows, {1, 2}, date(2026, 7, 1), date(2026, 8, 31), today=T)
    assert e.total == 4                                             # 1:1, 1:2, 1:3(inactive), 1:4(kg 0) — 2:1 은 필터 밖
    assert e.source_status == {"ACTIVE": 3, "INACTIVE": 1}
    assert e.quantity_status == {"ACCEPTED": 2, "EXCLUDED": 2}
    assert e.by_month == {"2026-08": 3, "2026-07": 1}
    assert set(e.by_farm) == {rc.mask(1)} and rc.mask(1) != "1" and len(rc.mask(1)) == 12


def test_duplicate_identity_in_snapshot_is_source_anomaly():
    with pytest.raises(ValueError, match="SOURCE_ANOMALY"):
        rc.expected_from_rows([row(1, 1), row(1, 1, kg="200")], {1}, date(2026, 7, 1), date(2026, 8, 31), today=T)


def test_diff_reports_only_differences():
    a = rc.Expected(total=2)
    a.by_farm["x"] = 2
    b = rc.Expected(total=2)
    b.by_farm["x"] = 1
    b.by_farm["y"] = 1
    assert rc.diff(a, a) == {}
    assert rc.diff(a, b) == {"by_farm": {"x": (2, 1), "y": (0, 1)}}


def test_indep_serialization_masks_farm_keys_and_lookup_accepts_both():
    indep = {(2807, "2026-08"): {"kg": Decimal("1.5"), "cost": None, "priced_kg": None, "rows_accepted": 2, "rows_costed": 0, "stages": {}}}
    masked = rc.serialize_indep(indep, masked=True)
    raw = rc.serialize_indep(indep, masked=False)
    assert list(masked) == [f"{rc.mask(2807)}|2026-08"] and "2807" not in next(iter(masked))
    assert list(raw) == ["2807|2026-08"]
    assert masked[f"{rc.mask(2807)}|2026-08"]["kg"] == "1.5" and masked[f"{rc.mask(2807)}|2026-08"]["rows_accepted"] == 2
    assert rc.indep_get(masked, 2807, "2026-08") == rc.indep_get(raw, 2807, "2026-08")
    assert rc.indep_get(masked, 2807, "2026-07") is None and rc.indep_get(masked, 1, "2026-08") is None
