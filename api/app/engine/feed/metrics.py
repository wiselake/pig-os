"""F2 — 결정론적 계산 (SPEC §5 CORE 6 + CONDITIONAL 4). 순수 함수, Decimal 산술, 반올림은 결과 생성 시 한 번.

각 함수는 FeedInput 을 받아 FeedMetricResult 를 돌려준다. 값이 없으면 INSUFFICIENT + reason.
   missing → 0 없음 · 부분 원가 → evidence 만 · 분모 0 → 비율 없음 · 통화 혼합 → 환산 없음.
CONDITIONAL(코호트) 4식은 PR #2 의 engine/feed_metrics.py 를 REUSE 한다 — 산식을 두 벌 두지 않는다.
"""
from __future__ import annotations

import functools
from collections import defaultdict
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from typing import Any

from app.engine import feed_metrics as legacy
from app.engine.feed.normalize import quality_summary
from app.engine.feed.types import (
    ACTUAL,
    DERIVED,
    QUANTITY_BASIS,
    R_ATTRIBUTION_MISSING,
    R_BASIS_UNSUPPORTED,
    R_CONTEXT_MISSING,
    R_COST_INCOMPLETE,
    R_CURRENCY_MIXED,
    R_NO_COHORT,
    R_NO_COST,
    R_NO_DATA,
    R_NO_GAIN,
    R_NO_HEAD_OUT,
    R_PRIOR_INSUFFICIENT,
    FeedInput,
    FeedMetricResult,
    insufficient,
)

# ── metric ids · 단위 · 반올림 자리수 (SPEC §5) ─────────────────────────────
FEED_QTY = "FEED_QTY"
FEED_COST = "FEED_COST"
FEED_UNIT_PRICE = "FEED_UNIT_PRICE"
FEED_MIX_SHARE = "FEED_MIX_SHARE"
FEED_QTY_CHANGE = "FEED_QTY_CHANGE"
FEED_COST_CHANGE = "FEED_COST_CHANGE"
FEED_QTY_PER_HEAD = "FEED_QTY_PER_HEAD"
FEED_COST_PER_PIG = "FEED_COST_PER_PIG"
FCR = "FCR"
FEED_COST_PER_KG_GAIN = "FEED_COST_PER_KG_GAIN"
ADG = "ADG"

CORE_METRICS = (FEED_QTY, FEED_COST, FEED_UNIT_PRICE, FEED_MIX_SHARE)
CHANGE_METRICS = (FEED_QTY_CHANGE, FEED_COST_CHANGE)
COHORT_METRICS = (FEED_QTY_PER_HEAD, FEED_COST_PER_PIG, FCR, FEED_COST_PER_KG_GAIN, ADG)

_PLACES = {"kg": 1, "currency": 2, "currency/kg": 4, "ratio": 4, "kg/kg": 3,
           "kg/head": 2, "currency/head": 2, "g/day": 1}


def _r(v: Decimal, unit: str) -> float:
    q = Decimal(1).scaleb(-_PLACES[unit])
    return float(v.quantize(q, rounding=ROUND_HALF_UP))


def _base_evidence(inp: FeedInput) -> dict[str, Any]:
    return {"period": {"start": inp.period.start.isoformat(), "end": inp.period.end.isoformat(),
                       "days": inp.period.days},
            "quantity_basis": inp.quantity_basis, "quality": quality_summary(inp)}


def _stamped(fn):
    """모든 공개 지표 함수의 결과에 입력의 quantity_basis 를 찍는다 — 입고량을 급여량처럼 읽히게 두지 않는다.
    CHANGE 지표는 (prev, cur) 를 받으므로 마지막 인자(cur)의 basis 가 결과의 basis 다 (불일치는 함수 안에서 INSUFFICIENT)."""
    @functools.wraps(fn)
    def w(*args: FeedInput) -> FeedMetricResult:
        return replace(fn(*args), quantity_basis=args[-1].quantity_basis)
    return w


# ── 내부 집계 (한 번 계산해 재사용) ─────────────────────────────────────────
def _sums(inp: FeedInput) -> dict[str, Any]:
    qty = sum((r.quantity_kg for r in inp.rows), Decimal(0))
    priced_qty = sum((r.quantity_kg for r in inp.rows if r.costed), Decimal(0))
    cost = sum((r.quantity_kg * r.unit_cost for r in inp.rows if r.costed), Decimal(0))
    costed = sum(1 for r in inp.rows if r.costed)
    uncosted = len(inp.rows) - costed
    currencies = sorted({r.currency for r in inp.rows if r.costed})
    return {"qty": qty, "priced_qty": priced_qty, "unpriced_qty": qty - priced_qty, "cost": cost,
            "costed_rows": costed, "uncosted_rows": uncosted, "currencies": currencies}


# ── CORE ────────────────────────────────────────────────────────────────────
@_stamped
def feed_qty(inp: FeedInput) -> FeedMetricResult:
    """Σ quantity_kg, record_date ∈ period. 행 0 = no_data (0 이 아니다)."""
    ev = _base_evidence(inp)
    if not inp.rows:
        return insufficient(FEED_QTY, "kg", R_NO_DATA, **ev)
    s = _sums(inp)
    ev["unattributed_share"] = _r(_share(sum((r.quantity_kg for r in inp.rows
                                                if r.scope == "FARM_UNATTRIBUTED"), Decimal(0)), s["qty"]), "ratio")
    return FeedMetricResult(FEED_QTY, _r(s["qty"], "kg"), "kg", ACTUAL, evidence=ev)


@_stamped
def feed_cost(inp: FeedInput) -> FeedMetricResult:
    """Σ qty×unit_cost — unit_cost 가 **전 행** 에 있고 통화가 하나일 때만 값. 아니면 INSUFFICIENT + evidence(부분합·coverage)."""
    ev = _base_evidence(inp)
    if not inp.rows:
        return insufficient(FEED_COST, "currency", R_NO_DATA, **ev)
    s = _sums(inp)
    ev.update(costed_rows=s["costed_rows"], uncosted_rows=s["uncosted_rows"],
              priced_qty_kg=_r(s["priced_qty"], "kg"), unpriced_qty_kg=_r(s["unpriced_qty"], "kg"),
              coverage_rows=_r(_share(Decimal(s["costed_rows"]), Decimal(len(inp.rows))), "ratio"),
              coverage_kg=_r(_share(s["priced_qty"], s["qty"]), "ratio") if s["qty"] else None,
              currencies=s["currencies"])
    if s["costed_rows"] == 0:
        return insufficient(FEED_COST, "currency", R_NO_COST, **ev)
    if len(s["currencies"]) > 1:
        ev["partial_cost_by_currency"] = _cost_by_currency(inp)
        return insufficient(FEED_COST, "currency", R_CURRENCY_MIXED, **ev)
    if s["uncosted_rows"] > 0:
        ev["partial_cost"] = _r(s["cost"], "currency")       # 원가가 아니라 증거다
        ev["currency"] = s["currencies"][0]
        return insufficient(FEED_COST, "currency", R_COST_INCOMPLETE, **ev)
    ev["currency"] = s["currencies"][0]
    return FeedMetricResult(FEED_COST, _r(s["cost"], "currency"), "currency", ACTUAL, evidence=ev)


@_stamped
def feed_unit_price(inp: FeedInput) -> FeedMetricResult:
    """수량 가중 평균 단가 = Σ(qty×cost)/Σqty — **costed 행만**. 단순 평균 금지. priced_qty 0 → no_cost."""
    ev = _base_evidence(inp)
    if not inp.rows:
        return insufficient(FEED_UNIT_PRICE, "currency/kg", R_NO_DATA, **ev)
    s = _sums(inp)
    ev.update(costed_rows=s["costed_rows"], priced_qty_kg=_r(s["priced_qty"], "kg"), currencies=s["currencies"])
    if s["costed_rows"] == 0 or s["priced_qty"] == 0:
        return insufficient(FEED_UNIT_PRICE, "currency/kg", R_NO_COST, **ev)
    if len(s["currencies"]) > 1:
        return insufficient(FEED_UNIT_PRICE, "currency/kg", R_CURRENCY_MIXED, **ev)
    ev["currency"] = s["currencies"][0]
    ev["by_feed_type"] = {k: _r(v, "currency/kg") for k, v in _unit_price_by_type(inp).items()}
    return FeedMetricResult(FEED_UNIT_PRICE, _r(s["cost"] / s["priced_qty"], "currency/kg"),
                            "currency/kg", DERIVED, evidence=ev)


@_stamped
def feed_mix_share(inp: FeedInput) -> FeedMetricResult:
    """feed_type key 별 수량 구성비 (evidence.shares 가 본체). 스칼라 value = **최대 구성비**(dominant share, ratio)
    — evidence.dominant_type 이 그 항목. (2026-09-22 정정: 이전 판은 항목 수를 ratio 단위로 돌려줬다.)
    반올림 전 Σshare == 1 (불변식) — 표시가 100% 가 안 되는 것은 계산층이 보정하지 않는다."""
    ev = _base_evidence(inp)
    if not inp.rows:
        return insufficient(FEED_MIX_SHARE, "ratio", R_NO_DATA, **ev)
    qty_by = _qty_by_type(inp)
    total = sum(qty_by.values(), Decimal(0))
    if total == 0:
        return insufficient(FEED_MIX_SHARE, "ratio", R_NO_DATA, **ev)
    ev["shares"] = {k: _r(v / total, "ratio") for k, v in sorted(qty_by.items())}
    ev["kg_by_feed_type"] = {k: _r(v, "kg") for k, v in sorted(qty_by.items())}
    # 불변식 검증용 — Decimal 나눗셈은 1/3 을 정확히 못 적으므로 유리수 문자열("1/3")로 남긴다
    ev["exact_shares"] = {k: str(Fraction(v) / Fraction(total)) for k, v in sorted(qty_by.items())}
    dominant = max(sorted(qty_by), key=lambda k: (qty_by[k], k))   # 동률이면 키 사전순 뒤 — 결정론
    ev["dominant_type"] = dominant
    ev["feed_type_count"] = len(qty_by)
    return FeedMetricResult(FEED_MIX_SHARE, _r(qty_by[dominant] / total, "ratio"), "ratio", DERIVED, evidence=ev)


# ── CHANGE (period-over-period) ────────────────────────────────────────────
@_stamped
def feed_qty_change(prev: FeedInput, cur: FeedInput) -> FeedMetricResult:
    """cur − prev (kg) + rate. 이전 기간 no_data → prior_insufficient (0% 가 아니다). 기간 길이 불일치 → context_missing."""
    ev = {"prev": _base_evidence(prev)["period"], "cur": _base_evidence(cur)["period"], "quantity_basis": cur.quantity_basis}
    if prev.quantity_basis != cur.quantity_basis:
        return insufficient(FEED_QTY_CHANGE, "kg", R_CONTEXT_MISSING, basis_mismatch=[prev.quantity_basis, cur.quantity_basis], **ev)
    if prev.period.days != cur.period.days:
        return insufficient(FEED_QTY_CHANGE, "kg", R_CONTEXT_MISSING, **ev)
    p, c = feed_qty(prev), feed_qty(cur)
    if c.provenance == "INSUFFICIENT":
        return insufficient(FEED_QTY_CHANGE, "kg", c.reason or R_NO_DATA, **ev)
    if p.provenance == "INSUFFICIENT":
        return insufficient(FEED_QTY_CHANGE, "kg", R_PRIOR_INSUFFICIENT, prior_reason=p.reason, **ev)
    pq, cq = _sums(prev)["qty"], _sums(cur)["qty"]
    delta = cq - pq
    ev.update(prev_kg=_r(pq, "kg"), cur_kg=_r(cq, "kg"),
              rate=_r(delta / pq, "ratio") if pq != 0 else None)   # prev 0 이면 비율 없음(숨기지 않음)
    return FeedMetricResult(FEED_QTY_CHANGE, _r(delta, "kg"), "kg", DERIVED, evidence=ev)


@_stamped
def feed_cost_change(prev: FeedInput, cur: FeedInput) -> FeedMetricResult:
    """cur − prev (currency). 두 기간 모두 FEED_COST 가 값이어야 하고 같은 통화여야 한다."""
    ev = {"prev": _base_evidence(prev)["period"], "cur": _base_evidence(cur)["period"], "quantity_basis": cur.quantity_basis}
    if prev.quantity_basis != cur.quantity_basis:
        return insufficient(FEED_COST_CHANGE, "currency", R_CONTEXT_MISSING, basis_mismatch=[prev.quantity_basis, cur.quantity_basis], **ev)
    if prev.period.days != cur.period.days:
        return insufficient(FEED_COST_CHANGE, "currency", R_CONTEXT_MISSING, **ev)
    p, c = feed_cost(prev), feed_cost(cur)
    if c.provenance == "INSUFFICIENT":
        return insufficient(FEED_COST_CHANGE, "currency", c.reason or R_NO_DATA, **ev)
    if p.provenance == "INSUFFICIENT":
        return insufficient(FEED_COST_CHANGE, "currency", R_PRIOR_INSUFFICIENT, prior_reason=p.reason, **ev)
    if p.evidence["currency"] != c.evidence["currency"]:
        return insufficient(FEED_COST_CHANGE, "currency", R_CURRENCY_MIXED,
                            currencies=[p.evidence["currency"], c.evidence["currency"]], **ev)
    pc, cc = _sums(prev)["cost"], _sums(cur)["cost"]
    delta = cc - pc
    ev.update(currency=c.evidence["currency"], prev_cost=_r(pc, "currency"), cur_cost=_r(cc, "currency"),
              rate=_r(delta / pc, "ratio") if pc != 0 else None)
    return FeedMetricResult(FEED_COST_CHANGE, _r(delta, "currency"), "currency", DERIVED, evidence=ev)


# ── CONDITIONAL (코호트) — legacy feed_metrics REUSE ───────────────────────
def _cohort_or_reason(inp: FeedInput, metric: str, unit: str) -> tuple[legacy.FeedCohort | None, FeedMetricResult | None]:
    if inp.quantity_basis != QUANTITY_BASIS:
        # 입고량은 소비량이 아니다 — 코호트 효율 지표는 AS_RECORDED(수기 급이 경로)에서만 (D-FEED-01 §11)
        return None, insufficient(metric, unit, R_BASIS_UNSUPPORTED, quantity_basis=inp.quantity_basis)
    ev = _base_evidence(inp)
    if inp.cohort is None or inp.cohort.groups == 0:
        return None, insufficient(metric, unit, R_NO_COHORT, **ev)
    c = inp.cohort
    if c.feed_kg <= 0:
        # 사료는 있는데 그룹 귀속이 없는 경우와, 사료 자체가 없는 경우를 구분한다
        reason = R_ATTRIBUTION_MISSING if inp.rows else R_NO_DATA
        return None, insufficient(metric, unit, reason, groups=c.groups, **ev)
    return legacy.FeedCohort(feed_kg=c.feed_kg, gain_kg=c.gain_kg, head_out=c.head_out, feed_cost=c.feed_cost,
                             costed_rows=c.costed_rows, uncosted_rows=c.uncosted_rows, currencies=c.currencies), None


_LEGACY_REASON = {legacy.NO_GAIN: R_NO_GAIN, legacy.NO_FEED: R_NO_DATA, legacy.NO_HEAD_OUT: R_NO_HEAD_OUT,
                  legacy.COST_INCOMPLETE: R_COST_INCOMPLETE, legacy.CURRENCY_MIXED: R_CURRENCY_MIXED,
                  legacy.NO_COST: R_NO_COST}


def withheld_to_reason(code: str) -> str:
    """PR #2 feed_metrics 의 대문자 유보 코드 → 소문자 reason 어휘 (SPEC §7)."""
    return _LEGACY_REASON.get(code, code.lower())


def _cohort_evidence(inp: FeedInput) -> dict[str, Any]:
    c = inp.cohort
    assert c is not None
    return {**_base_evidence(inp), "time_basis": "GROUP_LIFECYCLE", "cohort": {
        "groups": c.groups, "head_out": c.head_out, "gain_kg": str(c.gain_kg), "feed_kg": str(c.feed_kg),
        "costed_rows": c.costed_rows, "uncosted_rows": c.uncosted_rows, "currencies": sorted(c.currencies),
        "legacy_formula_version": legacy.FORMULA_VERSION}}


@_stamped
def fcr(inp: FeedInput) -> FeedMetricResult:
    """Σ귀속사료 / Σ((exit−entry)×head_out) — kpi_service:535 와 동일 조건. 보간·head_in 대체 없음."""
    cohort, bad = _cohort_or_reason(inp, FCR, "kg/kg")
    if bad:
        return bad
    r = legacy.compute(cohort)
    ev = _cohort_evidence(inp)
    if r.fcr is None:
        return insufficient(FCR, "kg/kg", withheld_to_reason(r.withheld.get("FCR", legacy.NO_GAIN)), **ev)
    return FeedMetricResult(FCR, r.fcr, "kg/kg", DERIVED, evidence=ev)


@_stamped
def feed_cost_per_pig(inp: FeedInput) -> FeedMetricResult:
    cohort, bad = _cohort_or_reason(inp, FEED_COST_PER_PIG, "currency/head")
    if bad:
        return bad
    r = legacy.compute(cohort)
    ev = _cohort_evidence(inp)
    if r.feed_cost_per_pig is None:
        return insufficient(FEED_COST_PER_PIG, "currency/head",
                            withheld_to_reason(r.withheld.get("FEED_COST_PER_PIG", legacy.NO_COST)), **ev)
    ev["currency"] = r.currency
    return FeedMetricResult(FEED_COST_PER_PIG, r.feed_cost_per_pig, "currency/head", DERIVED, evidence=ev)


@_stamped
def feed_cost_per_kg_gain(inp: FeedInput) -> FeedMetricResult:
    cohort, bad = _cohort_or_reason(inp, FEED_COST_PER_KG_GAIN, "currency/kg")
    if bad:
        return bad
    r = legacy.compute(cohort)
    ev = _cohort_evidence(inp)
    if r.feed_cost_per_kg_gain is None:
        return insufficient(FEED_COST_PER_KG_GAIN, "currency/kg",
                            withheld_to_reason(r.withheld.get("FEED_COST_PER_KG_GAIN", legacy.NO_COST)), **ev)
    ev["currency"] = r.currency
    return FeedMetricResult(FEED_COST_PER_KG_GAIN, r.feed_cost_per_kg_gain, "currency/kg", DERIVED, evidence=ev)


@_stamped
def feed_qty_per_head(inp: FeedInput) -> FeedMetricResult:
    """Σ귀속사료 / Σhead_out (kg/head). 분모는 **출하두수** 로 명시 — 평균재고·입식두수가 아니다."""
    cohort, bad = _cohort_or_reason(inp, FEED_QTY_PER_HEAD, "kg/head")
    if bad:
        return bad
    ev = _cohort_evidence(inp)
    if cohort.head_out <= 0:
        return insufficient(FEED_QTY_PER_HEAD, "kg/head", R_NO_HEAD_OUT, **ev)
    ev["denominator"] = "head_count_out"
    return FeedMetricResult(FEED_QTY_PER_HEAD, _r(cohort.feed_kg / Decimal(cohort.head_out), "kg/head"),
                            "kg/head", DERIVED, evidence=ev)


@_stamped
def adg(inp: FeedInput) -> FeedMetricResult:
    """일당증체 = Σgain / Σ((end−start)×head_out) × 1000 (g/day) — kpi_service:534 와 같은 적격 코호트."""
    ev = _base_evidence(inp)
    if inp.quantity_basis != QUANTITY_BASIS:
        # ADG 자체는 사료와 무관하지만 코호트 지표 묶음(§11)은 한 basis 규칙을 따른다 — 입고 소스에서 효율 묶음을 내지 않는다
        return insufficient(ADG, "g/day", R_BASIS_UNSUPPORTED, quantity_basis=inp.quantity_basis)
    if inp.cohort is None or inp.cohort.groups == 0:
        return insufficient(ADG, "g/day", R_NO_COHORT, **ev)
    c = inp.cohort
    ev = _cohort_evidence(inp)
    ev["cohort"]["pig_days"] = str(c.pig_days)
    if c.pig_days <= 0:
        return insufficient(ADG, "g/day", R_CONTEXT_MISSING, **ev)
    if c.gain_kg <= 0:
        return insufficient(ADG, "g/day", R_NO_GAIN, **ev)
    return FeedMetricResult(ADG, _r(c.gain_kg / c.pig_days * 1000, "g/day"), "g/day", DERIVED, evidence=ev)


def compute_all(inp: FeedInput, prev: FeedInput | None = None) -> dict[str, FeedMetricResult]:
    """한 번에 전부. 순서·키는 고정 — 결정론 테스트가 dict 동등성을 본다."""
    out = {FEED_QTY: feed_qty(inp), FEED_COST: feed_cost(inp),
           FEED_UNIT_PRICE: feed_unit_price(inp), FEED_MIX_SHARE: feed_mix_share(inp)}
    if prev is not None:
        out[FEED_QTY_CHANGE] = feed_qty_change(prev, inp)
        out[FEED_COST_CHANGE] = feed_cost_change(prev, inp)
    if inp.cohort is not None:
        out[FEED_QTY_PER_HEAD] = feed_qty_per_head(inp)
        out[FEED_COST_PER_PIG] = feed_cost_per_pig(inp)
        out[FCR] = fcr(inp)
        out[FEED_COST_PER_KG_GAIN] = feed_cost_per_kg_gain(inp)
        out[ADG] = adg(inp)
    return out


# ── helpers ────────────────────────────────────────────────────────────────
def _share(part: Decimal, whole: Decimal) -> Decimal:
    return part / whole if whole else Decimal(0)


def _qty_by_type(inp: FeedInput) -> dict[str, Decimal]:
    d: dict[str, Decimal] = defaultdict(Decimal)
    for r in inp.rows:
        d[r.feed_type_key] += r.quantity_kg
    return dict(d)


def _unit_price_by_type(inp: FeedInput) -> dict[str, Decimal]:
    cost: dict[str, Decimal] = defaultdict(Decimal)
    qty: dict[str, Decimal] = defaultdict(Decimal)
    for r in inp.rows:
        if r.costed:
            cost[r.feed_type_key] += r.quantity_kg * r.unit_cost
            qty[r.feed_type_key] += r.quantity_kg
    return {k: cost[k] / qty[k] for k in sorted(qty) if qty[k]}


def _cost_by_currency(inp: FeedInput) -> dict[str, float]:
    d: dict[str, Decimal] = defaultdict(Decimal)
    for r in inp.rows:
        if r.costed:
            d[r.currency] += r.quantity_kg * r.unit_cost
    return {k: _r(v, "currency") for k, v in sorted(d.items())}
