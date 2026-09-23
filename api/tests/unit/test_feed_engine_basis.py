"""Feed Engine — quantity_basis 계약 (D-FEED-01, 2026-09-22).

DELIVERED(입고) 입력은 CORE·CHANGE·VARIANCE 를 같은 산식으로 계산하되 결과가 자기 basis 를 잃지 않는다.
코호트 효율 지표(FCR 계열)는 DELIVERED 에서 계산하지 않는다. basis 가 다른 두 기간은 섞지 않는다.
기존 AS_RECORDED 경로는 한 글자도 바뀌지 않는다(기본값).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.engine.feed import metrics as m
from app.engine.feed.normalize import RawFeedRow, normalize
from app.engine.feed.types import (
    ACTUAL,
    INSUFFICIENT,
    QUANTITY_BASIS,
    QUANTITY_BASIS_DELIVERED,
    R_BASIS_UNSUPPORTED,
    R_CONTEXT_MISSING,
    Cohort,
    FeedInput,
    FeedMetricResult,
)
from app.engine.feed.variance import VarianceResult, decompose_cost_change

P = (date(2026, 8, 1), date(2026, 8, 31))
P0 = (date(2026, 7, 1), date(2026, 7, 31))


def raw(d, qty, cost, ft="비육돈"):
    return RawFeedRow(record_date=date.fromisoformat(d), quantity_kg=qty, unit_cost=cost, currency="KRW",
                      feed_type=ft, sow_id=None, group_id=None, building_id=None)


def delivered(rows, period=P, cohort=None) -> FeedInput:
    from app.engine.feed.types import Period
    return normalize(rows, period=Period(*period), farm_currency="KRW", cohort=cohort,
                     quantity_basis=QUANTITY_BASIS_DELIVERED)


def recorded(rows, period=P) -> FeedInput:
    from app.engine.feed.types import Period
    return normalize(rows, period=Period(*period), farm_currency="KRW")


CUR = [raw("2026-08-05", "4400", "582"), raw("2026-08-19", "3000", "600", ft="육성돈")]
PREV = [raw("2026-07-06", "4000", "570"), raw("2026-07-20", "3000", "600", ft="육성돈")]


class TestBasisDefault:
    def test_default_is_as_recorded_everywhere(self):
        i = recorded(CUR)
        assert i.quantity_basis == QUANTITY_BASIS == "AS_RECORDED"
        assert FeedMetricResult.__dataclass_fields__["quantity_basis"].default == "AS_RECORDED"
        assert VarianceResult.__dataclass_fields__["quantity_basis"].default == "AS_RECORDED"
        for r in m.compute_all(i, recorded(PREV, P0)).values():
            assert r.quantity_basis == "AS_RECORDED"


class TestDelivered:
    def test_core_values_identical_but_basis_is_carried(self):
        d, a = delivered(CUR), recorded(CUR)
        for f in (m.feed_qty, m.feed_cost, m.feed_unit_price, m.feed_mix_share):
            rd, ra = f(d), f(a)
            assert (rd.value, rd.unit, rd.provenance) == (ra.value, ra.unit, ra.provenance)   # 산식은 같다
            assert rd.quantity_basis == "DELIVERED" and ra.quantity_basis == "AS_RECORDED"    # 이름은 다르다
            assert rd.evidence["quantity_basis"] == "DELIVERED"
        assert m.feed_qty(d).value == 7400.0
        assert m.feed_cost(d).value == 4400 * 582 + 3000 * 600
        assert m.feed_cost(d).provenance == ACTUAL

    def test_change_metrics_carry_delivered_and_require_same_basis(self):
        d0, d1 = delivered(PREV, P0), delivered(CUR)
        q = m.feed_qty_change(d0, d1)
        assert q.value == 400.0 and q.quantity_basis == "DELIVERED" and q.evidence["quantity_basis"] == "DELIVERED"
        c = m.feed_cost_change(d0, d1)
        assert c.quantity_basis == "DELIVERED" and c.provenance != INSUFFICIENT
        # basis 가 다른 두 기간은 섞지 않는다 — 0% 도 아니고 값도 아니다
        mixed = m.feed_qty_change(recorded(PREV, P0), d1)
        assert (mixed.provenance, mixed.reason) == (INSUFFICIENT, R_CONTEXT_MISSING)
        assert mixed.evidence["basis_mismatch"] == ["AS_RECORDED", "DELIVERED"]
        assert mixed.quantity_basis == "DELIVERED"       # 결과의 basis = cur
        mixed_c = m.feed_cost_change(recorded(PREV, P0), d1)
        assert (mixed_c.provenance, mixed_c.reason) == (INSUFFICIENT, R_CONTEXT_MISSING)

    def test_variance_carries_basis_and_refuses_mixed(self):
        v = decompose_cost_change(delivered(PREV, P0), delivered(CUR))
        assert v.provenance != INSUFFICIENT and v.quantity_basis == "DELIVERED"
        assert round(v.price + v.volume + v.mix, 2) == round(v.total, 2)
        vm = decompose_cost_change(recorded(PREV, P0), delivered(CUR))
        assert (vm.provenance, vm.reason) == (INSUFFICIENT, R_CONTEXT_MISSING)
        assert vm.evidence["basis_mismatch"] == ["AS_RECORDED", "DELIVERED"]

    def test_cohort_efficiency_metrics_are_refused_for_delivered(self):
        c = Cohort(groups=1, head_out=100, gain_kg=Decimal("8000"), pig_days=Decimal("12000"), feed_kg=Decimal("24000"),
                   feed_cost=Decimal("7200"), costed_rows=3, uncosted_rows=0, currencies=frozenset({"KRW"}))
        d = delivered(CUR, cohort=c)
        out = m.compute_all(d)
        for k in (m.FCR, m.FEED_COST_PER_KG_GAIN, m.FEED_COST_PER_PIG, m.FEED_QTY_PER_HEAD, m.ADG):
            assert (out[k].provenance, out[k].reason) == (INSUFFICIENT, R_BASIS_UNSUPPORTED), k
            assert out[k].quantity_basis == "DELIVERED"
        # 같은 코호트를 AS_RECORDED 로 주면 예전처럼 계산된다 — 기존 경로 무변경
        a = recorded(CUR)
        a = FeedInput(period=a.period, farm_currency=a.farm_currency, rows=a.rows, cohort=c)
        assert m.fcr(a).value == 3.0

    def test_compute_all_stamps_every_result(self):
        out = m.compute_all(delivered(CUR), delivered(PREV, P0))
        assert {r.quantity_basis for r in out.values()} == {"DELIVERED"}
        assert set(out) == {m.FEED_QTY, m.FEED_COST, m.FEED_UNIT_PRICE, m.FEED_MIX_SHARE, m.FEED_QTY_CHANGE, m.FEED_COST_CHANGE}
