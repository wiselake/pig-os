"""Feed Engine V1 — F1/F2 계약 테스트 (docs/feed/FEED_ENGINE_IMPLEMENTATION_MAP.md §3 T-*).

전부 합성 입력. DB 없음. 기대값은 손으로 계산한다 — 엔진을 다시 돌려 기대값을 만들지 않는다.
"""
from __future__ import annotations

import random
from dataclasses import replace
from datetime import date
from decimal import Decimal
from fractions import Fraction

import pytest

from app.engine.feed import metrics as m
from app.engine.feed.normalize import RawFeedRow, feed_type_key, normalize, normalize_row
from app.engine.feed.status import FCR_UNAVAILABLE, FEED_COST_INCOMPLETE, deterministic_findings, to_kpi_status
from app.engine.feed.types import (
    ACTUAL,
    DERIVED,
    INSUFFICIENT,
    QUANTITY_BASIS,
    Cohort,
    FeedInput,
    FeedMetricResult,
    Period,
    insufficient,
)
from app.engine.feed.variance import POPULATION_EFFECT, decompose_cost_change
from app.engine.rule_engine import Severity

P = Period(date(2026, 9, 1), date(2026, 9, 30))
P0 = Period(date(2026, 8, 2), date(2026, 8, 31))   # 같은 길이(30일)


def raw(d="2026-09-10", qty="100", cost="1.0", ccy="USD", ft="Grower", group=None, sow=None, bld=None, gexists=None):
    return RawFeedRow(record_date=date.fromisoformat(d), quantity_kg=qty, unit_cost=cost, currency=ccy,
                      feed_type=ft, sow_id=sow, group_id=group, building_id=bld, group_exists=gexists)


def praw(**kw):
    """이전 기간(P0 = 8월) 행."""
    return raw(d="2026-08-10", **kw)


def inp(rows, period=P, ccy="USD", cohort=None) -> FeedInput:
    return normalize(rows, period=period, farm_currency=ccy, cohort=cohort)


def cohort(groups=1, head_out=100, gain="8000", feed="24000", cost="7200", costed=3, uncosted=0, ccy=("USD",)):
    return Cohort(groups=groups, head_out=head_out, gain_kg=Decimal(gain), pig_days=Decimal("12000"),
                  feed_kg=Decimal(feed), feed_cost=Decimal(cost) if cost is not None else None,
                  costed_rows=costed, uncosted_rows=uncosted, currencies=frozenset(ccy))


# ── F1 정규화 ────────────────────────────────────────────────────────────────
class TestNormalize:
    def test_feed_type_key_absorbs_spelling_variants_and_keeps_raw(self):
        assert feed_type_key("Grower ") == feed_type_key("grower") == feed_type_key("  GROWER  x".replace(" x", "")) == "grower"
        assert feed_type_key("Tăng  trọng") == "tăng trọng"
        assert feed_type_key(None) == feed_type_key("   ") == "UNSPECIFIED"
        r = normalize_row(raw(ft="Grower "), "USD")
        assert (r.feed_type_raw, r.feed_type_key) == ("Grower ", "grower")

    def test_currency_null_falls_back_to_farm_currency(self):        # T-C1
        assert normalize_row(raw(ccy=None), "krw").currency == "KRW"

    def test_scope_classification(self):
        assert normalize_row(raw(group="g1", gexists=True), "USD").scope == "GROUP"
        assert normalize_row(raw(sow="s1"), "USD").scope == "SOW"
        assert normalize_row(raw(bld="b1"), "USD").scope == "BUILDING"
        assert normalize_row(raw(), "USD").scope == "FARM_UNATTRIBUTED"

    def test_quality_flags_do_not_change_values(self):                 # T-Z2 · T-Z3 · T-P2
        z = normalize_row(raw(qty="0"), "USD")
        assert "zero_qty" in z.flags and z.quantity_kg == 0
        c = normalize_row(raw(cost="0"), "USD")
        assert "zero_cost" in c.flags and c.unit_cost == 0 and c.costed
        o = normalize_row(raw(group="gone", gexists=False), "USD")
        assert "orphan_group" in o.flags
        n = normalize_row(raw(cost=None), "USD")
        assert n.unit_cost is None and not n.costed and not n.flags

    def test_period_is_closed_on_both_ends(self):                      # T-B1
        i = inp([raw(d="2026-09-01"), raw(d="2026-09-30"), raw(d="2026-10-01"), raw(d="2026-08-31")])
        assert [r.record_date.isoformat() for r in i.rows] == ["2026-09-01", "2026-09-30"]

    def test_decimal_from_float_goes_through_string(self):
        assert normalize_row(raw(qty=0.1, cost=0.3), "USD").quantity_kg == Decimal("0.1")

    def test_quantity_basis_is_as_recorded_not_promoted(self):         # §8 quantity semantics
        assert QUANTITY_BASIS == "AS_RECORDED"
        assert m.feed_qty(inp([raw()])).evidence["quantity_basis"] == "AS_RECORDED"


# ── 결과 계약 ────────────────────────────────────────────────────────────────
class TestResultContract:
    def test_insufficient_cannot_carry_a_value_and_values_cannot_carry_a_reason(self):
        with pytest.raises(ValueError):
            FeedMetricResult("X", 1.0, "kg", INSUFFICIENT, reason="no_data")
        with pytest.raises(ValueError):
            FeedMetricResult("X", None, "kg", ACTUAL)
        with pytest.raises(ValueError):
            FeedMetricResult("X", 1.0, "kg", DERIVED, reason="no_data")
        assert insufficient("X", "kg", "no_data").value is None


# ── F2 CORE ─────────────────────────────────────────────────────────────────
class TestCore:
    def test_normal_case(self):                                        # T-N1
        i = inp([raw(qty="100", cost="1.0"), raw(qty="200", cost="1.5"), raw(qty="300", cost="2.0", ft="Finisher")])
        q, c, u = m.feed_qty(i), m.feed_cost(i), m.feed_unit_price(i)
        assert (q.value, q.unit, q.provenance) == (600.0, "kg", ACTUAL)
        assert (c.value, c.unit, c.provenance, c.evidence["currency"]) == (1000.0, "currency", ACTUAL, "USD")
        assert (u.value, u.provenance) == (round(1000 / 600, 4), DERIVED)
        assert u.evidence["by_feed_type"] == {"finisher": 2.0, "grower": round(400 / 300, 4)}

    def test_no_rows_is_no_data_not_zero(self):                        # T-Z1
        for f in (m.feed_qty, m.feed_cost, m.feed_unit_price, m.feed_mix_share):
            r = f(inp([]))
            assert (r.provenance, r.reason, r.value) == (INSUFFICIENT, "no_data", None)

    def test_partial_cost_is_evidence_not_a_cost(self):                # T-M1 · §18
        i = inp([raw(qty="100", cost="1.0"), raw(qty="200", cost="1.5"), raw(qty="300", cost=None)])
        c = m.feed_cost(i)
        assert (c.provenance, c.reason, c.value) == (INSUFFICIENT, "cost_incomplete", None)
        assert c.evidence["partial_cost"] == 400.0
        assert c.evidence["priced_qty_kg"] == 300.0 and c.evidence["unpriced_qty_kg"] == 300.0
        assert c.evidence["coverage_rows"] == round(2 / 3, 4) and c.evidence["coverage_kg"] == 0.5
        # 단가는 costed 행만으로 정상 — 부분원가와 독립
        assert m.feed_unit_price(i).value == round(400 / 300, 4)

    def test_no_costed_rows(self):                                     # T-M2
        i = inp([raw(cost=None), raw(cost=None)])
        assert m.feed_cost(i).reason == "no_cost" and m.feed_unit_price(i).reason == "no_cost"

    def test_unit_price_is_quantity_weighted_not_simple_mean(self):    # §19
        i = inp([raw(qty="900", cost="1.0"), raw(qty="100", cost="10.0")])
        assert m.feed_unit_price(i).value == 1.9            # (900+1000)/1000, 단순 평균 5.5 아님

    def test_mixed_currency_withholds_cost_not_quantity(self):         # T-C2
        i = inp([raw(ccy="USD"), raw(ccy="KRW", cost="1300")])
        assert m.feed_qty(i).provenance == ACTUAL
        c = m.feed_cost(i)
        assert c.reason == "currency_mixed" and c.evidence["partial_cost_by_currency"] == {"KRW": 130000.0, "USD": 100.0}
        assert m.feed_unit_price(i).reason == "currency_mixed"

    def test_mix_share_sums_to_one_exactly_before_rounding(self):      # T-… Σshare
        i = inp([raw(qty="1", ft="a"), raw(qty="1", ft="b"), raw(qty="1", ft="c")])
        s = m.feed_mix_share(i)
        assert sum(Fraction(v) for v in s.evidence["exact_shares"].values()) == 1
        assert s.evidence["shares"] == {"a": 0.3333, "b": 0.3333, "c": 0.3333}   # 표시 합 0.9999 — 보정하지 않는다
        assert s.evidence["kg_by_feed_type"] == {"a": 1.0, "b": 1.0, "c": 1.0}
        # 스칼라 value = 최대 구성비(ratio). 동률이면 키 사전순 뒤가 dominant — 결정론
        assert (s.value, s.unit, s.evidence["dominant_type"], s.evidence["feed_type_count"]) == (0.3333, "ratio", "c", 3)

    def test_mix_share_scalar_is_the_dominant_share_not_a_count(self):   # Codex 2026-09-22 MAJOR
        s = m.feed_mix_share(inp([raw(qty="50", ft="a"), raw(qty="50", ft="b")]))
        assert s.value == 0.5 and 0.0 <= s.value <= 1.0
        s2 = m.feed_mix_share(inp([raw(qty="90", ft="a"), raw(qty="10", ft="b")]))
        assert (s2.value, s2.evidence["dominant_type"]) == (0.9, "a")

    def test_unknown_feed_type_is_kept_as_unspecified_not_dropped(self):   # §9
        i = inp([raw(ft=None, qty="40"), raw(ft="Grower", qty="60")])
        assert m.feed_mix_share(i).evidence["shares"] == {"UNSPECIFIED": 0.4, "grower": 0.6}
        assert m.feed_qty(i).value == 100.0
        assert m.feed_qty(i).evidence["quality"]["unspecified_feed_type_rows"] == 1

    def test_zero_quantity_row_no_divide_by_zero(self):                # T-Z2
        i = inp([raw(qty="0", cost="1.0")])
        assert m.feed_qty(i).value == 0.0 and m.feed_qty(i).evidence["quality"]["zero_qty_rows"] == 1
        assert m.feed_unit_price(i).reason == "no_cost"          # priced_qty 0 → 분모 없음
        assert m.feed_mix_share(i).reason == "no_data"

    def test_unattributed_share_is_evidence(self):                     # T-P1
        i = inp([raw(qty="75", group="g", gexists=True), raw(qty="25")])
        assert m.feed_qty(i).evidence["unattributed_share"] == 0.25


class TestChange:
    def test_change_and_rate(self):
        c = m.feed_qty_change(inp([praw(qty="100")], P0), inp([raw(qty="150")], P))
        assert (c.value, c.evidence["rate"], c.provenance) == (50.0, 0.5, DERIVED)
        k = m.feed_cost_change(inp([praw(qty="100", cost="2")], P0), inp([raw(qty="100", cost="3")], P))
        assert (k.value, k.evidence["rate"]) == (100.0, 0.5)

    def test_previous_missing_is_insufficient_not_zero_percent(self):  # §21
        c = m.feed_qty_change(inp([], P0), inp([raw()], P))
        assert (c.provenance, c.reason, c.evidence["prior_reason"]) == (INSUFFICIENT, "prior_insufficient", "no_data")

    def test_previous_zero_does_not_hide_division(self):
        c = m.feed_qty_change(inp([praw(qty="0")], P0), inp([raw(qty="10")], P))
        assert c.value == 10.0 and c.evidence["rate"] is None

    def test_period_length_mismatch(self):                             # T-B2 (P-6: 임의 구간은 길이가 같아야 한다)
        c = m.feed_qty_change(inp([praw()], Period(date(2026, 8, 1), date(2026, 8, 20))), inp([raw()], P))
        assert c.reason == "context_missing" and c.evidence["period_days"] == [20, 30]

    def test_calendar_months_compare_regardless_of_length(self):       # P-6 (2026-09-22): 달력월 ↔ 달력월은 28~31일이어도 비교
        aug, sep = Period(date(2026, 8, 1), date(2026, 8, 31)), P
        c = m.feed_qty_change(inp([praw(qty="90")], aug), inp([raw(qty="100")], sep))
        assert (c.value, c.evidence["comparison_grain"]) == (10.0, "calendar_month")
        assert Period(date(2026, 2, 1), date(2026, 2, 28)).is_calendar_month and not Period(date(2026, 2, 1), date(2026, 2, 27)).is_calendar_month
        assert not Period(date(2026, 8, 2), date(2026, 8, 31)).is_calendar_month
        assert aug.comparison_grain(Period(date(2026, 9, 1), date(2026, 9, 30))) == "calendar_month"
        assert Period(date(2026, 8, 2), date(2026, 8, 31)).comparison_grain(sep) == "equal_days"   # 30 == 30
        assert Period(date(2026, 8, 1), date(2026, 8, 20)).comparison_grain(sep) is None

    def test_cost_change_requires_both_complete_and_same_currency(self):   # T-C3
        assert m.feed_cost_change(inp([praw(cost=None)], P0), inp([raw()], P)).reason == "prior_insufficient"
        assert m.feed_cost_change(inp([praw(ccy="KRW", cost="1")], P0), inp([raw()], P)).reason == "currency_mixed"


# ── CONDITIONAL (코호트) ─────────────────────────────────────────────────────
class TestCohort:
    def test_fcr_and_costs_from_cohort(self):
        i = inp([raw(group="g", gexists=True)], cohort=cohort())
        assert m.fcr(i).value == 3.0                                    # 24000/8000
        assert m.feed_cost_per_pig(i).value == 72.0                     # 7200/100
        assert m.feed_cost_per_kg_gain(i).value == 0.9                  # 7200/8000
        assert m.feed_qty_per_head(i).value == 240.0 and m.feed_qty_per_head(i).evidence["denominator"] == "head_count_out"
        assert m.fcr(i).evidence["time_basis"] == "GROUP_LIFECYCLE"
        assert (m.adg(i).value, m.adg(i).unit) == (round(8000 / 12000 * 1000, 1), "g/day")     # 666.7
        assert m.adg(inp([raw()], cohort=None)).reason == "no_cohort"
        assert m.adg(inp([raw()], cohort=cohort(gain="0"))).reason == "no_gain"
        assert set(m.compute_all(i)) >= {"ADG", "FCR", "FEED_COST_PER_PIG", "FEED_COST_PER_KG_GAIN", "FEED_QTY_PER_HEAD"}

    def test_no_cohort_is_not_no_data(self):                           # T-F1
        assert m.fcr(inp([raw()], cohort=cohort(groups=0, feed="0", gain="0", head_out=0))).reason == "no_cohort"
        assert m.fcr(inp([raw()], cohort=None)).reason == "no_cohort"

    def test_attribution_missing_vs_no_data(self):
        assert m.fcr(inp([raw()], cohort=cohort(feed="0"))).reason == "attribution_missing"
        assert m.fcr(inp([], cohort=cohort(feed="0"))).reason == "no_data"

    def test_denominators(self):                                       # T-D1 · T-D2
        assert m.fcr(inp([raw()], cohort=cohort(gain="0"))).reason == "no_gain"
        assert m.feed_cost_per_kg_gain(inp([raw()], cohort=cohort(gain="-5"))).reason == "no_gain"
        assert m.feed_cost_per_pig(inp([raw()], cohort=cohort(head_out=0))).reason == "no_head_out"
        assert m.feed_qty_per_head(inp([raw()], cohort=cohort(head_out=0))).reason == "no_head_out"

    def test_cohort_cost_incomplete_and_mixed(self):
        assert m.feed_cost_per_pig(inp([raw()], cohort=cohort(uncosted=1))).reason == "cost_incomplete"
        assert m.feed_cost_per_pig(inp([raw()], cohort=cohort(ccy=("USD", "KRW")))).reason == "currency_mixed"
        assert m.feed_cost_per_pig(inp([raw()], cohort=cohort(cost=None, costed=0))).reason == "no_cost"

    def test_calendar_and_lifecycle_are_different_quantities(self):    # T-G3
        i = inp([raw(qty="100", group="g", gexists=True)], cohort=cohort(feed="24000"))
        assert m.feed_qty(i).value == 100.0 and Decimal(m.fcr(i).evidence["cohort"]["feed_kg"]) == 24000

    def test_withheld_code_mapping(self):
        assert m.withheld_to_reason("NO_GAIN") == "no_gain" and m.withheld_to_reason("CURRENCY_MIXED") == "currency_mixed"


# ── Variance ────────────────────────────────────────────────────────────────
class TestVariance:
    def _pair(self, prev_rows, cur_rows):
        prev_rows = [replace(r, record_date=date(2026, 8, 10)) for r in prev_rows]
        return decompose_cost_change(inp(prev_rows, P0), inp(cur_rows, P))

    def test_identity_holds_exactly(self):                             # T-V1
        v = self._pair([raw(qty="100", cost="1.0", ft="a"), raw(qty="100", cost="2.0", ft="b")],
                       [raw(qty="150", cost="1.2", ft="a"), raw(qty="50", cost="2.5", ft="b")])
        assert v.provenance == DERIVED and v.population == POPULATION_EFFECT == "NOT_SUPPORTED"
        e = {k: Fraction(x) for k, x in v.exact.items()}
        assert e["price"] + e["volume"] + e["mix"] == e["total"]
        assert e["total"] == Fraction("150") * Fraction("1.2") + Fraction("50") * Fraction("2.5") - Fraction("300")
        # 손계산: total = 180+125−300 = 5 ; price = (1.2−1.0)·100 + (2.5−2.0)·100 = 70 ; Q 200→200 → volume 0 ;
        #         mix = 200·[1.2·(0.75−0.5) + 2.5·(0.25−0.5)] = 200·(0.3−0.625) = −65 ; 70+0−65 = 5 ✓
        assert (v.price, v.volume, v.mix, v.total) == (70.0, 0.0, -65.0, 5.0)

    def test_new_and_vanished_feed_types(self):                        # T-V2
        v = self._pair([raw(qty="100", cost="1.0", ft="a")], [raw(qty="100", cost="1.0", ft="b")])
        e = {k: Fraction(x) for k, x in v.exact.items()}
        assert e["price"] + e["volume"] + e["mix"] == e["total"] == 0

    def test_partial_cost_blocks_the_whole_decomposition(self):        # T-V3
        assert self._pair([raw(cost=None)], [raw()]).reason == "prior_insufficient"
        assert self._pair([raw()], [raw(), raw(cost=None)]).reason == "cost_incomplete"
        assert self._pair([raw()], [raw(cost=None)]).reason == "no_cost"
        assert self._pair([raw(ccy="KRW", cost="1")], [raw()]).reason == "currency_mixed"

    def test_random_inputs_keep_the_identity(self):
        rng = random.Random(20260921)
        for _ in range(200):
            types = ["a", "b", "c", "d"]
            prev = [raw(qty=str(rng.randint(1, 500)), cost=str(rng.randint(1, 50) / 10), ft=t) for t in rng.sample(types, rng.randint(1, 4))]
            cur = [raw(qty=str(rng.randint(1, 500)), cost=str(rng.randint(1, 50) / 10), ft=t) for t in rng.sample(types, rng.randint(1, 4))]
            v = self._pair(prev, cur)
            e = {k: Fraction(x) for k, x in v.exact.items()}
            assert e["price"] + e["volume"] + e["mix"] == e["total"]


# ── 불변식 ───────────────────────────────────────────────────────────────────
class TestInvariants:
    def _rich(self):
        rows = [raw(qty="100", cost="1.0", ft="Grower"), raw(qty="200", cost=None, ft="finisher"),
                raw(qty="50", ft="Grower ", ccy=None), raw(qty="0", cost="0"), raw(qty="10", group="x", gexists=False)]
        return rows

    def test_same_input_same_output_and_row_order_independent(self):   # T-I1
        rows = self._rich()
        prev_rows = [replace(r, record_date=date(2026, 8, 10)) for r in rows]
        a = m.compute_all(inp(rows, cohort=cohort()), inp(prev_rows, P0))
        shuffled = list(rows)
        random.Random(1).shuffle(shuffled)
        b = m.compute_all(inp(shuffled, cohort=cohort()), inp(list(reversed(prev_rows)), P0))
        assert a == b

    def test_no_estimated_provenance_anywhere(self):                   # T-I3
        for rows in ([], self._rich(), [raw()]):
            for r in m.compute_all(inp(rows, cohort=cohort()), inp([replace(x, record_date=date(2026, 8, 10)) for x in rows], P0)).values():
                assert r.provenance in (ACTUAL, DERIVED, INSUFFICIENT)
                assert (r.value is None) == (r.provenance == INSUFFICIENT)

    def test_type_quantities_sum_to_total_and_priced_plus_unpriced(self):
        i = inp(self._rich())
        q = m.feed_qty(i); c = m.feed_cost(i); s = m.feed_mix_share(i)
        assert sum(Decimal(str(v)) for v in s.evidence["kg_by_feed_type"].values()) == Decimal(str(q.value))
        assert c.evidence["priced_qty_kg"] + c.evidence["unpriced_qty_kg"] == q.value

    def test_country_and_display_unit_do_not_enter_calculation(self):  # T-K1 · T-U1 · T-I4
        rows = self._rich()
        base = m.compute_all(inp(rows, ccy="USD"))
        # 엔진에는 국가·unit_system 입력 자체가 없다 — farm_currency 만 있고 그것도 NULL 통화 귀속에만 쓰인다
        assert m.compute_all(inp(rows, ccy="USD")) == base
        # quantity_basis 는 2026-09-22 D-FEED-01 로 추가된 계약 필드 — 국가·표시단위가 아니라 "이 양이 무엇인가" 다
        assert FeedInput.__dataclass_fields__.keys() == {"period", "farm_currency", "rows", "cohort", "unattributed_rows", "quantity_basis"}
        assert not {"country", "unit_system"} & FeedInput.__dataclass_fields__.keys()

    def test_rounding_happens_once_at_the_end(self):                   # T-R1
        i = inp([raw(qty="1", cost="1"), raw(qty="1", cost="1"), raw(qty="1", cost="1")])
        assert m.feed_unit_price(i).value == 1.0
        assert m.feed_mix_share(inp([raw(qty="1", ft="a"), raw(qty="2", ft="b")])).evidence["shares"] == {"a": 0.3333, "b": 0.6667}


# ── F3 SAFE: 임계값 없는 상태/finding ───────────────────────────────────────
class TestStatus:
    def test_cost_incomplete_finding_is_info_and_carries_coverage(self):
        res = m.compute_all(inp([raw(cost=None), raw()]))
        f = deterministic_findings(res)
        assert [x.rule_id for x in f] == [FEED_COST_INCOMPLETE]
        assert f[0].severity == Severity.INFO and f[0].detail["uncosted_rows"] == 1 and f[0].current_value is None

    def test_fcr_unavailable_only_when_something_was_there(self):
        res = m.compute_all(inp([raw()], cohort=cohort(gain="0")))
        assert [x.rule_id for x in deterministic_findings(res)] == [FCR_UNAVAILABLE]
        assert deterministic_findings(m.compute_all(inp([raw()], cohort=None))) == []     # no_cohort 는 finding 아님
        assert deterministic_findings(m.compute_all(inp([]))) == []

    def test_status_reuses_kpi_status_and_never_claims_normal_without_policy(self):   # T-S1
        res = m.compute_all(inp([raw(cost=None), raw()]))
        st = to_kpi_status(res, deterministic_findings(res))
        assert st["FEED_COST"].status == "insufficient" and st["FEED_COST"].reason == "cost_incomplete"
        assert st["FEED_QTY"].status == "insufficient" and st["FEED_QTY"].reason == "no_policy"   # 정책 없이 normal 금지
        assert {s.status for s in st.values()} == {"insufficient"}
        # 호출자가 정책을 넘긴 metric 만 normal 이 될 수 있다 (WARNING/CRITICAL finding 없음 = normal)
        st2 = to_kpi_status(res, [], policy_kpis={"FEED_QTY"})
        assert st2["FEED_QTY"].status == "normal"

    def test_no_threshold_or_grade_words_in_feed_engine(self):
        import pathlib
        src = "".join(p.read_text(encoding="utf-8") for p in pathlib.Path("app/engine/feed").glob("*.py"))
        for word in ("Severity.WARNING", "Severity.CRITICAL", "warning=", "critical=", "COST_BAD", "poor", "good"):
            assert word not in src.replace("Severity.WARNING, Severity.CRITICAL, Severity.OK", ""), word
