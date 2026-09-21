"""Feed Basic 산식 — PIGOS-F-0011. 순수 함수. 추정 0 — 모자라면 이유가 나온다."""
import dataclasses
from decimal import Decimal

import pytest

from app.engine import feed_metrics as fm


def _cohort(**kw) -> fm.FeedCohort:
    base = dict(
        feed_kg=Decimal("23085"), gain_kg=Decimal("8550"), head_out=95,
        feed_cost=Decimal("11542.5"), costed_rows=3, uncosted_rows=0,
        currencies=frozenset({"USD"}),
    )
    base.update(kw)
    return fm.FeedCohort(**base)


def test_full_cohort_yields_all_three():
    r = fm.compute(_cohort())
    assert r.formula_version == fm.FORMULA_VERSION
    assert r.fcr == 2.7                                     # 23085 / 8550 — kpi_service 와 동일 값
    assert r.feed_cost_per_pig == 121.5                     # 11542.5 / 95
    assert r.feed_cost_per_kg_gain == 1.35                  # 11542.5 / 8550
    assert r.currency == "USD"
    assert r.withheld == {}


def test_fcr_matches_kpi_service_rounding():
    """kpi_service:535 는 round(feed/gain, 3). 같은 자리수."""
    assert fm.fcr(Decimal("10000"), Decimal("3333")) == 3.0
    assert fm.fcr(Decimal("1"), Decimal("3")) == 0.333


def test_no_gain_withholds_fcr_and_per_kg():
    r = fm.compute(_cohort(gain_kg=Decimal("0"), head_out=0))
    assert r.fcr is None and r.withheld["FCR"] == fm.NO_GAIN
    assert r.feed_cost_per_kg_gain is None and r.withheld["FEED_COST_PER_KG_GAIN"] == fm.NO_GAIN
    assert r.feed_cost_per_pig is None and r.withheld["FEED_COST_PER_PIG"] == fm.NO_HEAD_OUT
    assert r.currency is None


def test_no_feed_withholds_fcr_only():
    r = fm.compute(_cohort(feed_kg=Decimal("0"), feed_cost=None, costed_rows=0, uncosted_rows=0))
    assert r.withheld["FCR"] == fm.NO_FEED
    assert r.withheld["FEED_COST_PER_PIG"] == fm.NO_COST


def test_partial_unit_cost_is_not_a_cost():
    """unit_cost 없는 행이 하나라도 있으면 부분합을 원가로 내지 않는다. FCR 은 그대로 나온다."""
    r = fm.compute(_cohort(uncosted_rows=1))
    assert r.fcr == 2.7
    assert r.feed_cost_per_pig is None and r.feed_cost_per_kg_gain is None
    assert r.withheld == {
        "FEED_COST_PER_PIG": fm.COST_INCOMPLETE,
        "FEED_COST_PER_KG_GAIN": fm.COST_INCOMPLETE,
    }
    assert r.currency is None


def test_mixed_currency_is_not_converted():
    r = fm.compute(_cohort(currencies=frozenset({"USD", "BRL"})))
    assert r.feed_cost_per_pig is None
    assert r.withheld["FEED_COST_PER_PIG"] == fm.CURRENCY_MIXED
    assert r.fcr == 2.7


def test_cost_without_currency_still_computes_but_names_none():
    """currency 컬럼이 비어 있어도 값은 나온다 — 통화 라벨만 None. 만들어 붙이지 않는다."""
    r = fm.compute(_cohort(currencies=frozenset()))
    assert r.feed_cost_per_pig == 121.5
    assert r.currency is None


def test_pure_functions_refuse_zero_denominators():
    assert fm.fcr(Decimal("10"), Decimal("0")) is None
    assert fm.fcr(Decimal("0"), Decimal("10")) is None
    assert fm.feed_cost_per_pig(Decimal("10"), 0) is None
    assert fm.feed_cost_per_kg_gain(Decimal("10"), Decimal("0")) is None


def test_result_is_immutable():
    r = fm.compute(_cohort())
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.fcr = 1.0  # type: ignore[misc]
