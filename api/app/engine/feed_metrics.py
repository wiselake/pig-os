"""Feed Basic 산식 — PIGOS-F-0011 (EPIC 4).

FCR · Feed Cost/pig · Feed Cost/kg gain 세 값의 canonical 산식. 순수 함수만 둔다 —
DB 를 모르고, 추정하지 않는다. 입력이 모자라면 값 대신 **이유**를 돌려준다
(jobs/kpi.py 의 _WITHHELD 와 같은 규율: 없는 값을 0 이나 평균으로 채우지 않는다).

★ 응답 노출 없음. FEED_COST_* 두 값은 EXPANSION_DECISION §5-2 · HANDOFF §6-5 가
  Paid hypothesis 로 적어 두었고 과금 경계(D-15)는 미결이다. 산식·테스트만 여기 두고
  KPI 응답에 싣는 것은 결재 뒤 한 줄이다 (FEATURE_REGISTRY F-0011 "범위 결정 (나)").

코호트 정의는 kpi_service 의 FCR 과 동일해야 한다 — CLOSED finisher_groups(end_date 가
기간 안) 에 group_id 로 귀속된 사료의 전생애 합. 분모 gain 도 같은 그룹이다. 그래서
FCR 을 여기서도 계산하되 kpi_service:535 와 같은 값이 나와야 하고, 그 동치가 테스트다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

FORMULA_VERSION = "FEED_BASIC.v1"

# 값을 유보하는 이유 — 문자열은 로그·테스트용 식별자다. 사용자 문구가 아니다.
NO_GAIN = "NO_GAIN"                        # CLOSED 그룹 없음 또는 gain <= 0
NO_FEED = "NO_FEED"                        # 그룹 귀속 사료 0 kg
NO_HEAD_OUT = "NO_HEAD_OUT"                # 출하두수 0
COST_INCOMPLETE = "COST_INCOMPLETE"        # unit_cost 없는 사료 행이 있다 — 부분합은 원가가 아니다
CURRENCY_MIXED = "CURRENCY_MIXED"          # 통화가 둘 이상 — 환산하지 않는다
NO_COST = "NO_COST"                        # unit_cost 있는 행이 하나도 없다


@dataclass(frozen=True)
class FeedCohort:
    """산식 입력. 전부 같은 CLOSED 그룹 집합에서 나온 값이어야 한다."""
    feed_kg: Decimal                       # SUM(quantity_kg), 그룹 귀속분
    gain_kg: Decimal                       # SUM((exit - entry) * head_out)
    head_out: int                          # SUM(head_count_out)
    feed_cost: Decimal | None              # SUM(quantity_kg * unit_cost), unit_cost 있는 행만
    costed_rows: int                       # unit_cost 있는 사료 행 수
    uncosted_rows: int                     # unit_cost 없는 사료 행 수
    currencies: frozenset[str] = frozenset()   # 사료 행의 currency 집합(None 제외)


@dataclass(frozen=True)
class FeedBasicResult:
    formula_version: str
    fcr: float | None
    feed_cost_per_pig: float | None
    feed_cost_per_kg_gain: float | None
    currency: str | None                   # 원가 두 값의 통화. 값이 None 이면 None
    withheld: dict[str, str] = field(default_factory=dict)   # 지표 → 이유


def fcr(feed_kg: Decimal, gain_kg: Decimal) -> float | None:
    """사료요구율 = 사료 kg / 증체 kg. kpi_service:535 와 동일 조건(gain>0, feed>0)."""
    if gain_kg <= 0 or feed_kg <= 0:
        return None
    return round(float(feed_kg) / float(gain_kg), 3)


def feed_cost_per_pig(feed_cost: Decimal, head_out: int) -> float | None:
    """두당 사료비 = 사료비 / 출하두수."""
    if head_out <= 0:
        return None
    return round(float(feed_cost) / head_out, 2)


def feed_cost_per_kg_gain(feed_cost: Decimal, gain_kg: Decimal) -> float | None:
    """증체 kg 당 사료비 = 사료비 / 증체 kg."""
    if gain_kg <= 0:
        return None
    return round(float(feed_cost) / float(gain_kg), 4)


def _cost_reason(c: FeedCohort) -> str | None:
    """원가 두 값을 계산해도 되는가. 안 되면 이유. 부분 원가는 원가가 아니다."""
    if c.costed_rows == 0:
        return NO_COST
    if c.uncosted_rows > 0:
        return COST_INCOMPLETE
    if len(c.currencies) > 1:
        return CURRENCY_MIXED
    return None


def compute(c: FeedCohort) -> FeedBasicResult:
    withheld: dict[str, str] = {}

    v_fcr = fcr(c.feed_kg, c.gain_kg)
    if v_fcr is None:
        withheld["FCR"] = NO_GAIN if c.gain_kg <= 0 else NO_FEED

    cost_reason = _cost_reason(c)
    per_pig: float | None = None
    per_kg: float | None = None
    currency: str | None = None
    if cost_reason is not None:
        withheld["FEED_COST_PER_PIG"] = cost_reason
        withheld["FEED_COST_PER_KG_GAIN"] = cost_reason
    else:
        assert c.feed_cost is not None
        currency = next(iter(c.currencies)) if c.currencies else None
        per_pig = feed_cost_per_pig(c.feed_cost, c.head_out)
        if per_pig is None:
            withheld["FEED_COST_PER_PIG"] = NO_HEAD_OUT
        per_kg = feed_cost_per_kg_gain(c.feed_cost, c.gain_kg)
        if per_kg is None:
            withheld["FEED_COST_PER_KG_GAIN"] = NO_GAIN
        if per_pig is None and per_kg is None:
            currency = None

    return FeedBasicResult(
        formula_version=FORMULA_VERSION,
        fcr=v_fcr,
        feed_cost_per_pig=per_pig,
        feed_cost_per_kg_gain=per_kg,
        currency=currency,
        withheld=withheld,
    )
