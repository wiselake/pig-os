"""F1 — 입력 정규화 (SPEC §4 · §8). 순수 함수. DB·시계·ORM 을 모른다.

로더가 넘기는 것은 이미 dict/원시값으로 풀린 행이다 (`RawFeedRow`). 여기서:
  단위      kg 그대로 (변환 0)                     통화   NULL → farm_currency
  feed_type key = lower · trim · 연속공백 1개        스코프 sow/group/building/FARM_UNATTRIBUTED
  품질 플래그  zero_qty · zero_cost · orphan_group   기간   record_date ∉ period 인 행은 버린다(보고용 카운트)
정규화는 값을 바꾸지 않는다 — 분류하고 표시할 뿐이다. missing 을 0 으로 만들지 않는다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.engine.feed.types import UNSPECIFIED_FEED_TYPE, Cohort, FeedInput, FeedRow, Period, Scope

_WS = re.compile(r"\s+")


@dataclass(frozen=True)
class RawFeedRow:
    """로더 ↔ 정규화 경계. ORM 객체가 아니라 값만."""
    record_date: date
    quantity_kg: Decimal | float | int | str
    unit_cost: Decimal | float | int | str | None
    currency: str | None
    feed_type: str | None
    sow_id: str | None
    group_id: str | None
    building_id: str | None
    group_exists: bool | None = None     # group_id 가 있을 때 로더가 채운다. None = 확인 안 함


def feed_type_key(raw: str | None) -> str:
    """표기 흔들림 흡수: 'Grower ' / 'grower' / 'GROWER' → 'grower'. 원문은 FeedRow.feed_type_raw 에 남긴다."""
    if raw is None:
        return UNSPECIFIED_FEED_TYPE
    k = _WS.sub(" ", raw.strip()).lower()
    return k or UNSPECIFIED_FEED_TYPE


def _dec(v: Decimal | float | int | str) -> Decimal:
    # float 를 곧장 Decimal 로 만들면 이진 오차가 그대로 들어온다 — 문자열 경유가 규칙.
    return v if isinstance(v, Decimal) else Decimal(str(v))


def _scope(r: RawFeedRow) -> Scope:
    if r.group_id is not None:
        return "GROUP"
    if r.sow_id is not None:
        return "SOW"
    if r.building_id is not None:
        return "BUILDING"
    return "FARM_UNATTRIBUTED"


def normalize_row(r: RawFeedRow, farm_currency: str) -> FeedRow:
    qty = _dec(r.quantity_kg)
    cost = _dec(r.unit_cost) if r.unit_cost is not None else None
    flags: set[str] = set()
    if qty == 0:
        flags.add("zero_qty")          # 스키마(>0)가 거부하므로 정상 경로로는 생기지 않는다 — 데이터 오류 표지
    if cost is not None and cost == 0:
        flags.add("zero_cost")         # 입력값 0 = 무상. 미입력(NULL)과 다르다
    if r.group_id is not None and r.group_exists is False:
        flags.add("orphan_group")      # FK 가 없어 생길 수 있다 — 코호트에서 제외된다
    return FeedRow(
        record_date=r.record_date,
        quantity_kg=qty,
        unit_cost=cost,
        currency=(r.currency or farm_currency).upper(),
        feed_type_raw=r.feed_type,
        feed_type_key=feed_type_key(r.feed_type),
        scope=_scope(r),
        group_id=r.group_id,
        flags=frozenset(flags),
    )


def normalize(
    raw_rows: list[RawFeedRow] | tuple[RawFeedRow, ...],
    *,
    period: Period,
    farm_currency: str,
    cohort: Cohort | None = None,
) -> FeedInput:
    """기간 밖 행은 버린다(로더가 이미 잘랐어도 여기서 한 번 더 — 엔진 입력은 스스로 완결돼야 한다)."""
    rows = tuple(
        normalize_row(r, farm_currency)
        for r in raw_rows
        if period.contains(r.record_date)
    )
    return FeedInput(
        period=period,
        farm_currency=farm_currency.upper(),
        rows=rows,
        cohort=cohort,
        unattributed_rows=sum(1 for x in rows if x.scope == "FARM_UNATTRIBUTED"),
    )


def quality_summary(inp: FeedInput) -> dict[str, Any]:
    """evidence 에 싣는 품질 요약. 값이 아니라 표지다."""
    rows = inp.rows
    return {
        "rows": len(rows),
        "zero_qty_rows": sum(1 for r in rows if "zero_qty" in r.flags),
        "zero_cost_rows": sum(1 for r in rows if "zero_cost" in r.flags),
        "orphan_group_rows": sum(1 for r in rows if "orphan_group" in r.flags),
        "unattributed_rows": inp.unattributed_rows,
        "unspecified_feed_type_rows": sum(1 for r in rows if r.feed_type_key == UNSPECIFIED_FEED_TYPE),
        "currencies": sorted({r.currency for r in rows}),
    }
