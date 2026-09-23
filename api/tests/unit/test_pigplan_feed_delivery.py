"""PigPlan 사료 입고 adapter — 분류·매핑 계약 (docs/feed/reports/PIGPLAN_ORACLE_FEED_PREFLIGHT_20260922.md · D-FEED-01/02/03).

합성 행만. Oracle 없음. PigOS DB 없음.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.engine.feed import metrics as m
from app.engine.feed.types import INSUFFICIENT, Period
from app.harvest import pigplan_feed_delivery as pf

TODAY = date(2026, 9, 22)
AUG = Period(date(2026, 8, 1), date(2026, 8, 31))


def row(**kw) -> pf.PigPlanFeedDeliveryRow:
    base = dict(source_farm_no=4372, seq=1, wk_dt=date(2026, 8, 10), wk_dt_raw="2026-08-10",
                total_kg=Decimal("4400"), fper_price=Decimal("582"), total_price=Decimal("2560800"),
                feed_stage_cd="100005", feed_stage_name="비육돈", feed_cd=17, feed_name="비육 후기 A",
                use_yn="Y", account_cd="410002", gain_yn="M", country_code="KOR", has_supplier=True)
    base.update(kw)
    return pf.PigPlanFeedDeliveryRow(**base)


class TestContract:
    def test_contract_is_explicit_and_conservative(self):
        c = pf.SOURCE_CONTRACT
        assert c["quantity_basis"] == "DELIVERED"
        assert c["source_currency"] == "KRW" and c["pigos_farm_currency_fallback"] == "FORBIDDEN"
        assert c["source_filter_status"] == "EVIDENCE_SUPPORTED_LABEL_UNVERIFIED"
        assert "TRG_TM_FEED_01" in c["label_evidence"]
        assert "943001" in c["currency_evidence"]
        # 금지어: 이 소스를 소비/급여로 부르지 않는다
        for word in ("CONSUMED", "FED", "USED"):
            assert word not in c["quantity_basis"]


class TestClassify:
    def test_normal_row_accepted_with_unit_price(self):
        c = pf.classify(row(), today=TODAY)
        assert (c.quantity, c.cost, c.unit_cost, c.reasons) == ("ACCEPTED", "ACCEPTED", Decimal("582"), ())

    def test_out_of_filter_rows_never_enter(self):
        assert pf.classify(row(account_cd="512001"), today=TODAY).reasons == ("OUT_OF_FILTER",)
        assert pf.classify(row(gain_yn="B"), today=TODAY).reasons == ("OUT_OF_FILTER",)

    def test_inactive_and_bad_dates_and_nonpositive_kg_are_excluded_not_corrected(self):
        assert pf.classify(row(use_yn="N"), today=TODAY).reasons == (pf.INACTIVE_SOURCE_ROW,)
        assert pf.classify(row(wk_dt=None, wk_dt_raw="3020-04-29"), today=TODAY).reasons == (pf.INVALID_DATE,)
        assert pf.classify(row(wk_dt=date(3020, 4, 29)), today=TODAY).reasons == (pf.INVALID_DATE,)
        assert pf.classify(row(wk_dt=date(1985, 1, 1)), today=TODAY).reasons == (pf.INVALID_DATE,)
        assert pf.classify(row(total_kg=Decimal("0")), today=TODAY).reasons == (pf.NON_POSITIVE_QUANTITY,)
        assert pf.classify(row(total_kg=None), today=TODAY).quantity == "EXCLUDED"

    def test_cost_identity_mismatch_drops_cost_but_keeps_quantity(self):
        c = pf.classify(row(total_price=Decimal("9999")), today=TODAY)
        assert (c.quantity, c.cost, c.unit_cost, c.reasons) == ("ACCEPTED", "INSUFFICIENT", None, (pf.COST_IDENTITY_MISMATCH,))

    def test_cost_missing_is_insufficient_not_zero(self):
        c = pf.classify(row(fper_price=None, total_price=None), today=TODAY)
        assert (c.quantity, c.cost, c.unit_cost, c.reasons) == ("ACCEPTED", "INSUFFICIENT", None, (pf.COST_INCOMPLETE,))
        c0 = pf.classify(row(fper_price=Decimal("0"), total_price=Decimal("0")), today=TODAY)
        assert c0.cost == "INSUFFICIENT"

    def test_cost_derived_from_total_only_when_unit_price_absent(self):
        c = pf.classify(row(fper_price=None, total_price=Decimal("2560800")), today=TODAY)
        assert c.cost == "ACCEPTED" and c.unit_cost == Decimal("582") and c.reasons == (pf.COST_DERIVED_FROM_TOTAL,)

    def test_non_kor_farm_blocks_cost_only(self):
        c = pf.classify(row(country_code="VNM"), today=TODAY)
        assert (c.quantity, c.cost, c.unit_cost, c.reasons) == ("ACCEPTED", "EXCLUDED", None, (pf.BLOCKED_CURRENCY_EVIDENCE,))


class TestMapping:
    def test_engine_row_carries_krw_and_stage_not_product(self):
        r = row()
        raw = pf.to_raw_feed_row(r, pf.classify(r, today=TODAY))
        assert (raw.currency, raw.feed_type, raw.quantity_kg, raw.unit_cost) == ("KRW", "비육돈", Decimal("4400"), Decimal("582"))
        assert raw.group_id is None and raw.sow_id is None
        assert "비육 후기 A" not in (raw.feed_type or "")          # 제품명은 feed_type 에 섞이지 않는다
        assert r.feed_name == "비육 후기 A"                          # 소스 행에는 남아 있다

    def test_excluded_rows_cannot_become_engine_rows(self):
        r = row(total_kg=Decimal("0"))
        with pytest.raises(ValueError):
            pf.to_raw_feed_row(r, pf.classify(r, today=TODAY))

    def test_batch_feed_input_is_delivered_krw_and_reconciles_by_hand(self):
        rows = [row(seq=1), row(seq=2, wk_dt=date(2026, 8, 20), total_kg=Decimal("3000"), fper_price=Decimal("600"),
                                total_price=Decimal("1800000"), feed_stage_cd="100004", feed_stage_name="육성돈"),
                row(seq=3, wk_dt=date(2026, 8, 25), fper_price=None, total_price=None),        # 원가 없음
                row(seq=4, use_yn="N"),                                                          # 제외
                row(seq=5, wk_dt=date(2026, 7, 30))]                                             # 창 밖
        b = pf.build_batch(4372, AUG, rows, today=TODAY)
        assert b.counts()["source_rows"] == 4 and b.counts()["quantity_accepted"] == 3 and b.counts()["excluded"] == 1
        assert b.counts()["cost_accepted"] == 2 and b.counts()["cost_insufficient"] == 1
        assert b.counts()["reasons"] == {pf.COST_INCOMPLETE: 1, pf.INACTIVE_SOURCE_ROW: 1}
        assert b.counts()["feed_products"] == 1 and b.counts()["feed_stages"] == 2
        inp = b.feed_input()
        assert inp.quantity_basis == "DELIVERED" and inp.farm_currency == "KRW"
        assert {r.currency for r in inp.rows} == {"KRW"}
        q, c, u, s = m.feed_qty(inp), m.feed_cost(inp), m.feed_unit_price(inp), m.feed_mix_share(inp)
        assert q.value == 4400 + 3000 + 4400 and q.quantity_basis == "DELIVERED"
        assert (c.provenance, c.reason) == (INSUFFICIENT, "cost_incomplete")            # partial ≠ complete
        assert c.evidence["partial_cost"] == 4400 * 582 + 3000 * 600
        assert u.value == round((4400 * 582 + 3000 * 600) / (4400 + 3000), 4)
        assert s.evidence["shares"] == {"비육돈": round(8800 / 11800, 4), "육성돈": round(3000 / 11800, 4)}

    def test_dateless_rows_stay_in_classification_but_not_in_engine(self):
        b = pf.build_batch(4372, AUG, [row(), row(seq=9, wk_dt=None, wk_dt_raw="0410-01-01")], today=TODAY)
        assert b.counts()["source_rows"] == 2 and b.counts()["reasons"] == {pf.INVALID_DATE: 1}
        assert len(b.feed_input().rows) == 1

    def test_cohort_metrics_never_computed_from_this_source(self):
        b = pf.build_batch(4372, AUG, [row()], today=TODAY)
        out = m.compute_all(b.feed_input())
        assert set(out) == {m.FEED_QTY, m.FEED_COST, m.FEED_UNIT_PRICE, m.FEED_MIX_SHARE}      # cohort=None
        assert m.fcr(b.feed_input()).reason == "basis_unsupported"
