"""Feed Engine 세로 슬라이스 — DB 행 → 로더 → 정규화 → FeedInput → compute_all (F2.5).

★ 라우터 없음. 여기서 증명하는 것:
  T-EQ1  로더 코호트 == feed_service.load_feed_cohort · 엔진 FCR == build_herd_kpis["FCR"] (하나의 산식)
  달력 지표는 record_date 창, 코호트 지표는 그룹 전생애 — 같은 농장에서 두 값이 다르다
  legacy 리포트(build_grow_finish_rows, open 그룹 head_in 대체)와의 차이를 **고정**한다 (CONFLICT-1, 수정 안 함)
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.health import FeedRecord
from app.db.models.ops import FinisherGroup
from app.db.models.platform import Farm
from app.engine.feed import metrics as m
from app.engine.feed.types import ACTUAL, DERIVED, INSUFFICIENT
from app.services import feed_engine_service as svc
from app.services import feed_service
from app.services.kpi_service import build_herd_kpis
from app.services.report_service import build_grow_finish_rows

pytestmark = pytest.mark.anyio

START, END = date(2026, 1, 1), date(2026, 12, 31)


async def _closed_group(db, farm, **kw) -> FinisherGroup:
    base = dict(farm_id=farm.id, group_code=f"FG-{uuid.uuid4().hex[:5]}",
                start_date=date(2026, 1, 10), end_date=date(2026, 3, 20),
                head_count_in=100, head_count_out=95,
                avg_entry_weight_kg=25.0, avg_exit_weight_kg=115.0)
    base.update(kw)
    g = FinisherGroup(**base)
    db.add(g)
    await db.flush()
    return g


def _feed(farm, d, q, c="0.50", group=None, ft="Grower", ccy="USD"):
    return FeedRecord(farm_id=farm.id, group_id=group, record_date=d, quantity_kg=q,
                      unit_cost=Decimal(c) if c is not None else None, currency=ccy, feed_type=ft)


async def test_vertical_slice_matches_legacy_cohort_and_kpi_fcr(db: AsyncSession, test_farm: Farm):   # T-EQ1
    g = await _closed_group(db, test_farm)                                   # gain 90*95 = 8550
    for d, q in ((date(2026, 1, 20), 7255), (date(2026, 2, 15), 9234), (date(2026, 3, 10), 6596)):
        db.add(_feed(test_farm, d, q, group=g.id))
    db.add(_feed(test_farm, date(2026, 2, 1), 5000, group=None, ft="Sow "))  # 미귀속 — 코호트 밖
    await db.flush()

    inp = await svc.load_feed_input(db, test_farm, START, END)
    legacy = await feed_service.load_feed_cohort(db, test_farm.id, START, END)
    kpis = await build_herd_kpis(db, test_farm)

    assert inp.cohort is not None and inp.cohort.groups == 1
    assert (inp.cohort.feed_kg, inp.cohort.gain_kg, inp.cohort.head_out) == (legacy.feed_kg, legacy.gain_kg, legacy.head_out)
    res = m.compute_all(inp)
    assert res["FCR"].value == kpis["FCR"] == pytest.approx(2.7, abs=0.001)
    # 달력(전 행 28,085 kg) ≠ 코호트(귀속 23,085 kg) — 두 시간 기준은 섞이지 않는다
    assert res["FEED_QTY"].value == 28085.0 and Decimal(res["FCR"].evidence["cohort"]["feed_kg"]) == 23085
    assert res["FEED_QTY"].evidence["unattributed_share"] == pytest.approx(5000 / 28085, abs=1e-4)
    assert res["FEED_COST"].provenance == ACTUAL and res["FEED_COST"].value == pytest.approx(28085 * 0.5, abs=0.01)
    assert res["FEED_MIX_SHARE"].evidence["shares"].keys() == {"grower", "sow"}
    assert res["FEED_COST_PER_PIG"].value == pytest.approx(23085 * 0.5 / 95, abs=0.01)


async def test_loader_flags_orphan_group_and_falls_back_currency(db: AsyncSession, test_farm: Farm):
    db.add(_feed(test_farm, date(2026, 2, 1), 100, group=uuid.uuid4(), ccy=None))   # FK 없는 group_id
    await db.flush()
    inp = await svc.load_feed_input(db, test_farm, START, END)
    assert "orphan_group" in inp.rows[0].flags
    assert inp.rows[0].currency == (test_farm.currency or "USD").upper()
    assert m.compute_all(inp)["FCR"].reason == "no_cohort"


async def test_compute_feed_metrics_builds_previous_period_of_same_length(db: AsyncSession, test_farm: Farm):
    db.add(_feed(test_farm, date(2026, 8, 10), 100))
    db.add(_feed(test_farm, date(2026, 9, 10), 150))
    await db.flush()
    res = await svc.compute_feed_metrics(db, test_farm, date(2026, 9, 1), date(2026, 9, 30))
    assert res["FEED_QTY_CHANGE"].provenance == DERIVED and res["FEED_QTY_CHANGE"].value == 50.0
    assert res["FEED_QTY_CHANGE"].evidence["prev"] == {"start": "2026-08-02", "end": "2026-08-31", "days": 30}
    # 8월 행이 없으면 0% 가 아니라 prior_insufficient
    res2 = await svc.compute_feed_metrics(db, test_farm, date(2026, 11, 1), date(2026, 11, 30))
    assert res2["FEED_QTY"].reason == "no_data" and res2["FEED_QTY_CHANGE"].provenance == INSUFFICIENT


async def test_characterization_legacy_report_uses_head_in_for_open_groups_engine_does_not(db: AsyncSession, test_farm: Farm):
    """CONFLICT-1 고정. open 그룹(end_date NULL): 리포트는 head_in 으로 gain 을 만들어 fcr 을 내고,
    엔진은 코호트에서 제외한다(no_cohort). 이 차이는 EXPECTED_SEMANTIC_DIFFERENCE — 여기서 고치지 않는다."""
    g = await _closed_group(db, test_farm, end_date=None, head_count_out=None)
    db.add(_feed(test_farm, date(2026, 2, 1), 9000, group=g.id))
    await db.flush()

    legacy_rows = build_grow_finish_rows(
        [{"group_code": g.group_code, "start_date": g.start_date, "end_date": None, "head_in": 100,
          "head_out": None, "entry_w": 25.0, "exit_w": 115.0}],
        {g.group_code: 9000.0})
    assert legacy_rows[0]["fcr"] == 1.0                        # 9000 / (90 * 100)  ← head_in 대체

    inp = await svc.load_feed_input(db, test_farm, START, END)
    assert m.compute_all(inp)["FCR"].reason == "no_cohort"       # 엔진: CLOSED 가 아니면 값을 만들지 않는다
    assert (await build_herd_kpis(db, test_farm))["FCR"] is None  # kpi_service 도 엔진과 같은 쪽
