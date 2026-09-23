"""Feed Cost Variance — 정확 분해 (SPEC §11). 잔차 버킷 없음.

  ΔC = PRICE + VOLUME + MIX
  PRICE  = Σ_i (p_i¹ − p_i⁰) · q_i⁰                 기준 수량 (Laspeyres)
  VOLUME = (Q¹ − Q⁰) · Σ_i p_i¹ s_i⁰                총량 변화, 기준 구성비
  MIX    = Q¹ · Σ_i p_i¹ (s_i¹ − s_i⁰)              구성비 변화, 현재 총량
  (i = feed_type key, p_i = 수량 가중 단가, s_i = q_i/Q). 신규/소멸 i 는 없는 쪽 q=0, p 는 있는 쪽 값.
전제: 두 기간 모두 FEED_COST 가 값(cost complete) · 같은 통화 · 비교 가능 grain(달력월↔달력월 또는 같은 길이, P-6). 아니면 전체 INSUFFICIENT.
POPULATION 효과: NOT_SUPPORTED (두당 분모 미확정 — SPEC §11).

★ 유리수(Fraction) 산술 — Decimal 나눗셈(s_i = q_i/Q)은 순환소수를 자르므로 항등식이 마지막 자리에서
  깨진다. Fraction 은 정확하다. 표시 값은 마지막에 한 번 Decimal 로 내린다.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
from fractions import Fraction
from typing import Any

from app.engine.feed.metrics import (
    FEED_COST_CHANGE,
    _qty_by_type,
    _r,
    _unit_price_by_type,
    feed_cost,
)
from app.engine.feed.types import (
    DERIVED,
    INSUFFICIENT,
    QUANTITY_BASIS,
    R_CONTEXT_MISSING,
    R_CURRENCY_MIXED,
    R_PRIOR_INSUFFICIENT,
    FeedInput,
    Provenance,
)

POPULATION_EFFECT = "NOT_SUPPORTED"


@dataclass(frozen=True)
class VarianceResult:
    provenance: Provenance
    reason: str | None = None
    currency: str | None = None
    total: float | None = None
    price: float | None = None
    volume: float | None = None
    mix: float | None = None
    population: str = POPULATION_EFFECT
    exact: dict[str, str] = field(default_factory=dict)     # 유리수 문자열 — 항등식 테스트용
    evidence: dict[str, Any] = field(default_factory=dict)
    quantity_basis: str = QUANTITY_BASIS                    # 입고 원가 분해는 "구매 변화" 다 — 소비가 아니다


def _ins(reason: str, **ev: Any) -> VarianceResult:
    return VarianceResult(provenance=INSUFFICIENT, reason=reason, evidence=ev)


def _dec(x: Fraction) -> Decimal:
    return Decimal(x.numerator) / Decimal(x.denominator)


def decompose_cost_change(prev: FeedInput, cur: FeedInput) -> VarianceResult:
    return replace(_decompose(prev, cur), quantity_basis=cur.quantity_basis)


def _decompose(prev: FeedInput, cur: FeedInput) -> VarianceResult:
    if prev.quantity_basis != cur.quantity_basis:
        return _ins(R_CONTEXT_MISSING, basis_mismatch=[prev.quantity_basis, cur.quantity_basis])
    grain = prev.period.comparison_grain(cur.period)
    if grain is None:
        return _ins(R_CONTEXT_MISSING, period_days=[prev.period.days, cur.period.days])
    pc, cc = feed_cost(prev), feed_cost(cur)
    if cc.provenance == INSUFFICIENT:
        return _ins(cc.reason or R_CONTEXT_MISSING, cur_reason=cc.reason)
    if pc.provenance == INSUFFICIENT:
        return _ins(R_PRIOR_INSUFFICIENT, prior_reason=pc.reason)
    if pc.evidence["currency"] != cc.evidence["currency"]:
        return _ins(R_CURRENCY_MIXED, currencies=[pc.evidence["currency"], cc.evidence["currency"]])

    f = Fraction
    q0 = {k: f(v) for k, v in _qty_by_type(prev).items()}
    q1 = {k: f(v) for k, v in _qty_by_type(cur).items()}
    p0 = {k: f(v) for k, v in _unit_price_by_type(prev).items()}   # cost complete → 전 type 에 단가 존재
    p1 = {k: f(v) for k, v in _unit_price_by_type(cur).items()}
    keys = sorted(set(q0) | set(q1))
    big_q0 = sum(q0.values(), f(0))
    big_q1 = sum(q1.values(), f(0))
    price = volume = mix = f(0)
    for k in keys:
        qk0, qk1 = q0.get(k, f(0)), q1.get(k, f(0))
        pk1 = p1.get(k, p0.get(k, f(0)))    # 소멸 type: 현재 단가 없음 → 기준 단가
        pk0 = p0.get(k, pk1)                 # 신규 type: 기준 단가 없음 → 현재 단가 (Δp = 0)
        s0 = qk0 / big_q0 if big_q0 else f(0)
        s1 = qk1 / big_q1 if big_q1 else f(0)
        price += (pk1 - pk0) * qk0
        volume += (big_q1 - big_q0) * pk1 * s0
        mix += big_q1 * pk1 * (s1 - s0)
    total = sum((q1[k] * p1[k] for k in q1), f(0)) - sum((q0[k] * p0[k] for k in q0), f(0))
    assert price + volume + mix == total, "variance identity broke — this is a bug, not a rounding issue"

    return VarianceResult(
        provenance=DERIVED, currency=cc.evidence["currency"],
        total=_r(_dec(total), "currency"), price=_r(_dec(price), "currency"),
        volume=_r(_dec(volume), "currency"), mix=_r(_dec(mix), "currency"),
        exact={"total": str(total), "price": str(price), "volume": str(volume), "mix": str(mix)},
        evidence={"metric": FEED_COST_CHANGE, "feed_types": keys,
                  "prev": {"kg": str(big_q0)}, "cur": {"kg": str(big_q1)}},
    )
