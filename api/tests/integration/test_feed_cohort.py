"""Feed Basic 코호트 로더 — PIGOS-F-0011.

핵심은 하나: load_feed_cohort 의 FCR 이 build_herd_kpis 의 FCR 과 **같은 값**이어야 한다.
같은 CLOSED 그룹, 같은 귀속 사료. 어긋나면 산식이 둘이 된다.
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.health import FeedRecord
from app.db.models.ops import FinisherGroup
from app.db.models.platform import Farm
from app.engine import feed_metrics as fm
from app.services import feed_service
from app.services.kpi_service import build_herd_kpis

pytestmark = pytest.mark.anyio

START, END = date(2026, 1, 1), date(2026, 12, 31)


async def _closed_group(db, farm) -> FinisherGroup:
    g = FinisherGroup(farm_id=farm.id, group_code=f"FG-{uuid.uuid4().hex[:5]}",
                      start_date=date(2026, 1, 10), end_date=date(2026, 3, 20),
                      head_count_in=100, head_count_out=95,
                      avg_entry_weight_kg=25.0, avg_exit_weight_kg=115.0)
    db.add(g)
    await db.flush()
    return g


async def test_cohort_fcr_equals_kpi_service_fcr(db: AsyncSession, test_farm: Farm):
    g = await _closed_group(db, test_farm)                       # gain = 90 * 95 = 8550
    for d, q, c in ((date(2026, 1, 20), 7255, "0.50"), (date(2026, 2, 15), 9234, "0.50"),
                    (date(2026, 3, 10), 6596, "0.50")):
        db.add(FeedRecord(farm_id=test_farm.id, group_id=g.id, record_date=d,
                          quantity_kg=q, unit_cost=Decimal(c), currency="USD"))
    # 미태깅 사료 — 두 경로 모두에서 제외되어야 한다
    db.add(FeedRecord(farm_id=test_farm.id, group_id=None, record_date=date(2026, 2, 1),
                      quantity_kg=5000, unit_cost=Decimal("0.50"), currency="USD"))
    await db.flush()

    cohort = await feed_service.load_feed_cohort(db, test_farm.id, START, END)
    r = fm.compute(cohort)
    kpis = await build_herd_kpis(db, test_farm)

    assert kpis["FCR"] is not None
    assert r.fcr == kpis["FCR"] == pytest.approx(2.7, abs=0.001)
    assert cohort.costed_rows == 3 and cohort.uncosted_rows == 0
    assert r.feed_cost_per_pig == pytest.approx(23085 * 0.5 / 95, abs=0.01)
    assert r.feed_cost_per_kg_gain == pytest.approx(23085 * 0.5 / 8550, abs=0.0001)
    assert r.currency == "USD"


async def test_cohort_counts_uncosted_rows_instead_of_filling(db: AsyncSession, test_farm: Farm):
    g = await _closed_group(db, test_farm)
    db.add(FeedRecord(farm_id=test_farm.id, group_id=g.id, record_date=date(2026, 2, 1),
                      quantity_kg=1000, unit_cost=Decimal("0.40"), currency="USD"))
    db.add(FeedRecord(farm_id=test_farm.id, group_id=g.id, record_date=date(2026, 2, 2),
                      quantity_kg=1000))                           # 단가 없음
    await db.flush()

    cohort = await feed_service.load_feed_cohort(db, test_farm.id, START, END)
    assert cohort.feed_kg == Decimal("2000")
    assert cohort.costed_rows == 1 and cohort.uncosted_rows == 1
    assert cohort.feed_cost == Decimal("400.0000")                # 부분합은 보존, 판정은 compute 가
    r = fm.compute(cohort)
    assert r.fcr is not None
    assert r.feed_cost_per_pig is None and r.withheld["FEED_COST_PER_PIG"] == fm.COST_INCOMPLETE


async def test_cohort_is_empty_without_closed_groups(db: AsyncSession, test_farm: Farm):
    cohort = await feed_service.load_feed_cohort(db, test_farm.id, START, END)
    assert cohort.feed_kg == 0 and cohort.gain_kg == 0 and cohort.head_out == 0
    assert cohort.feed_cost is None and cohort.currencies == frozenset()
    r = fm.compute(cohort)
    assert r.fcr is None and r.withheld["FCR"] == fm.NO_GAIN
    assert r.withheld["FEED_COST_PER_PIG"] == fm.NO_COST


# ── 제외 집합 동치 ──────────────────────────────────────────────────────────────
# 값이 같은 것만으로는 부족하다. feed_metrics 가 FCR 을 유보하는 그룹을 kpi_service 가
# 보고하면 산식이 둘이다. 반대로 원가만 유보하는 경우는 FCR 이 뜨는 게 맞고, 그 상태가
# 어떻게 보이는지를 여기서 고정한다 (D-16 두 맵 교훈 — parity 는 fallback 까지).


async def test_no_gain_is_withheld_on_both_sides(db: AsyncSession, test_farm: Farm):
    """CLOSED 그룹이 없다 → feed_metrics NO_GAIN, kpi_service 도 None."""
    db.add(FeedRecord(farm_id=test_farm.id, group_id=None, record_date=date(2026, 2, 1),
                      quantity_kg=5000, unit_cost=Decimal("0.5"), currency="USD"))
    await db.flush()
    r = fm.compute(await feed_service.load_feed_cohort(db, test_farm.id, START, END))
    kpis = await build_herd_kpis(db, test_farm)
    assert r.withheld["FCR"] == fm.NO_GAIN
    assert kpis["FCR"] is None


async def test_no_feed_is_withheld_on_both_sides(db: AsyncSession, test_farm: Farm):
    """CLOSED 그룹은 있으나 귀속 사료 0 → feed_metrics NO_FEED, kpi_service 도 None."""
    await _closed_group(db, test_farm)
    db.add(FeedRecord(farm_id=test_farm.id, group_id=None, record_date=date(2026, 2, 1),
                      quantity_kg=5000))
    await db.flush()
    r = fm.compute(await feed_service.load_feed_cohort(db, test_farm.id, START, END))
    kpis = await build_herd_kpis(db, test_farm)
    assert r.withheld["FCR"] == fm.NO_FEED
    assert kpis["FCR"] is None


async def test_cost_withheld_does_not_withhold_fcr_anywhere(db: AsyncSession, test_farm: Farm):
    """원가만 유보(단가 누락) → 양쪽 다 FCR 은 보고한다. 화면에서 FCR 은 뜨고 Feed Cost 만 비는
    상태이며, 그 이유는 feed_metrics.withheld 에만 있다 — KPI 응답에는 아직 없다 (F-0011 (나))."""
    g = await _closed_group(db, test_farm)
    db.add(FeedRecord(farm_id=test_farm.id, group_id=g.id, record_date=date(2026, 2, 1),
                      quantity_kg=8550, unit_cost=Decimal("0.5"), currency="USD"))
    db.add(FeedRecord(farm_id=test_farm.id, group_id=g.id, record_date=date(2026, 2, 2),
                      quantity_kg=8550))
    await db.flush()
    r = fm.compute(await feed_service.load_feed_cohort(db, test_farm.id, START, END))
    kpis = await build_herd_kpis(db, test_farm)
    assert r.fcr == kpis["FCR"] == pytest.approx(2.0, abs=0.001)
    assert "FCR" not in r.withheld
    assert r.withheld == {"FEED_COST_PER_PIG": fm.COST_INCOMPLETE,
                          "FEED_COST_PER_KG_GAIN": fm.COST_INCOMPLETE}
