"""Feed Engine 계약 타입 — 한 곳에만 둔다 (F0 SPEC §4 입력 · §7 provenance · §8 결측 의미).

raw ORM 은 여기 들어오지 않는다. 로더(services/feed_engine_service.py)가 행을 `FeedRow` 로,
코호트를 `Cohort` 로 바꿔 `FeedInput` 을 만든다. 엔진의 모든 함수는 `FeedInput` 만 받는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal

FORMULA_VERSION = "FEED_ENGINE.v1"
# quantity_kg 의 의미(급이/소진/입고)는 미확정 — 기록된 값 그대로라는 사실만 계약한다 (UNRESOLVED-1).
# 승격(CONSUMED 등)은 사람 결정 + FORMULA_VERSION bump 로만 한다.
QUANTITY_BASIS = "AS_RECORDED"

# ── provenance ──────────────────────────────────────────────────────────────
# ESTIMATED 는 계약상 존재하지만 V1 엔진은 절대 생성하지 않는다 (불변식 T-I3).
Provenance = Literal["ACTUAL", "DERIVED", "INSUFFICIENT"]
ACTUAL: Provenance = "ACTUAL"
DERIVED: Provenance = "DERIVED"
INSUFFICIENT: Provenance = "INSUFFICIENT"

# ── INSUFFICIENT reason 어휘 (기존 KpiStatus.reason + feed 추가, 전부 소문자) ──
R_NO_DATA = "no_data"                    # 기간 내 행 0 (0 이 아니다)
R_NO_COST = "no_cost"                    # unit_cost 있는 행 0
R_COST_INCOMPLETE = "cost_incomplete"    # unit_cost 없는 행이 있다 — 부분합은 원가가 아니다
R_CURRENCY_MIXED = "currency_mixed"      # 통화 ≥2 — 환산하지 않는다
R_NO_GAIN = "no_gain"                    # 코호트 증체 ≤ 0
R_NO_FEED = "no_feed"                    # 코호트 귀속 사료 0
R_NO_HEAD_OUT = "no_head_out"            # 출하두수 0
R_NO_COHORT = "no_cohort"                # CLOSED 그룹 0 (not applicable — no_data 와 다르다)
R_PRIOR_INSUFFICIENT = "prior_insufficient"   # 비교 기간이 INSUFFICIENT
R_ATTRIBUTION_MISSING = "attribution_missing"  # 그룹 귀속 사료 0 (사료는 있으나 group_id 없음)
R_CONTEXT_MISSING = "context_missing"    # 기간 길이 불일치 등 계산 전제 미충족

# ── 스코프 ──────────────────────────────────────────────────────────────────
Scope = Literal["SOW", "GROUP", "BUILDING", "FARM_UNATTRIBUTED"]
UNSPECIFIED_FEED_TYPE = "UNSPECIFIED"


@dataclass(frozen=True)
class Period:
    """닫힌 달력 구간 [start, end] (농장 현지 날짜)."""
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"period end {self.end} < start {self.start}")

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def contains(self, d: date) -> bool:
        return self.start <= d <= self.end


@dataclass(frozen=True)
class FeedRow:
    """정규화된 사료 행 하나. 값은 전부 Decimal(문자열 경유) — float 누적 오차를 들이지 않는다."""
    record_date: date
    quantity_kg: Decimal
    unit_cost: Decimal | None            # NULL = 미입력. 0 은 입력값 0 (무상)
    currency: str                        # NULL 은 로더가 farm.currency 로 귀속한 뒤 들어온다
    feed_type_raw: str | None
    feed_type_key: str                   # lower·trim·연속공백 1 — UNSPECIFIED 면 원문 없음
    scope: Scope
    group_id: str | None = None          # str 로 고정 — UUID 객체를 엔진에 들이지 않는다
    flags: frozenset[str] = frozenset()  # zero_qty · zero_cost · orphan_group

    @property
    def costed(self) -> bool:
        return self.unit_cost is not None


@dataclass(frozen=True)
class Cohort:
    """CLOSED finisher-group 코호트 집계 (kpi_service:428-449 와 같은 조건, GROUP_LIFECYCLE).

    `feed_kg` 는 코호트 그룹에 group_id 로 귀속된 사료의 **전생애** 합 — Period 와 무관하다.
    """
    groups: int
    head_out: int
    gain_kg: Decimal
    pig_days: Decimal
    feed_kg: Decimal
    feed_cost: Decimal | None
    costed_rows: int
    uncosted_rows: int
    currencies: frozenset[str] = frozenset()


@dataclass(frozen=True)
class FeedInput:
    """엔진의 유일한 입력. period 는 CALENDAR 지표의 창, cohort 는 GROUP_LIFECYCLE 지표의 입력."""
    period: Period
    farm_currency: str
    rows: tuple[FeedRow, ...]            # record_date ∈ period 인 행만 (로더가 자른다)
    cohort: Cohort | None = None         # None = 로더가 코호트를 싣지 않음(코호트 지표 계산 안 함)
    unattributed_rows: int = 0           # 참고용: 기간 내 sow/group/building 전부 NULL 인 행 수


@dataclass(frozen=True)
class FeedMetricResult:
    """metric 하나의 결과. 숫자 하나만 돌려주는 인터페이스를 만들지 않는다 (F0 §16)."""
    metric_id: str
    value: float | None
    unit: str
    provenance: Provenance
    reason: str | None = None            # provenance == INSUFFICIENT 일 때만
    evidence: dict[str, Any] = field(default_factory=dict)
    formula_version: str = FORMULA_VERSION

    def __post_init__(self) -> None:
        # 계약 자체가 위조를 막는다: 값이 없으면 INSUFFICIENT+reason, 있으면 reason 없음.
        if self.provenance == INSUFFICIENT:
            if self.value is not None or not self.reason:
                raise ValueError(f"{self.metric_id}: INSUFFICIENT must carry no value and a reason")
        else:
            if self.value is None or self.reason is not None:
                raise ValueError(f"{self.metric_id}: {self.provenance} must carry a value and no reason")


def insufficient(metric_id: str, unit: str, reason: str, **evidence: Any) -> FeedMetricResult:
    return FeedMetricResult(metric_id=metric_id, value=None, unit=unit,
                            provenance=INSUFFICIENT, reason=reason, evidence=dict(evidence))
