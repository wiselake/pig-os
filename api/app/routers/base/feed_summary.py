"""Feed summary — 읽기 전용, 엔진 호출만 (docs/feed/FEED_READ_API_CONTRACT_DRAFT.md E1/E2).

GET /farms/{farm_id}/feed/summary?period=YYYY-MM&basis=AS_RECORDED|DELIVERED
GET /farms/{farm_id}/feed/months?from=YYYY-MM&to=YYYY-MM&basis=

규칙: basis 필수(기본값 없음) · 값 없음 = null + reason (0 아님) · 두 basis 합산 없음 · FCR/효율 없음(코호트 미적재)
      · 원천 raw row/식별자 미노출 · 판정(좋고 나쁨) 없음 — KpiStatus 는 no_policy/insufficient 만
AS_RECORDED = 이 농장의 수기 feed_records. DELIVERED = feed_source_rows(프로덕션 적재 전엔 no_data 가 정상).

부분월(B-1, 2026-09-23 결정): 진행 중인 달은 값(MTD)은 주되 **비교하지 않는다** — FEED_QTY_CHANGE·FEED_COST_CHANGE 는
null + reason partial_period. 판정은 농장 현지 날짜: 월말이 **지나야** 완료월(월말 당일도 진행 중 — 그날 입력이 아직 들어온다).
농장 timezone 이 잘못돼 있으면 지구상 가장 이른 날짜(UTC-12)로 본다 — 완료를 일찍 선언하지 않는다.
"""
from __future__ import annotations

import re
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.dependencies import DbDep, FarmDep
from app.engine.feed import metrics as m
from app.engine.feed.status import deterministic_findings, to_kpi_status
from app.engine.feed.types import R_PARTIAL_PERIOD, FeedInput, FeedMetricResult, insufficient
from app.services.feed_engine_service import load_feed_input, load_feed_input_from_source

router = APIRouter(prefix="/farms/{farm_id}/feed", tags=["Feed"])

Basis = Literal["AS_RECORDED", "DELIVERED"]


class MetricOut(BaseModel):
    value: float | None
    unit: str
    provenance: str
    reason: str | None = None
    evidence: dict = {}
    status: dict | None = None


class FeedSummaryOut(BaseModel):
    farm_id: str
    period: dict
    quantity_basis: str
    currency: str | None
    formula_version: str
    metrics: dict[str, MetricOut]
    findings: list[dict]
    no_data: bool
    provenance: dict


class FeedMonthOut(BaseModel):
    period: str
    quantity_basis: str
    currency: str | None
    rows: int
    feed_qty_kg: float | None
    feed_cost: float | None
    feed_cost_reason: str | None
    partial_cost: float | None
    unit_price: float | None
    dominant_type: str | None
    partial: bool                      # 진행 중인 달(MTD) — 화면은 비교하지 않는다


_YM = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_EARLIEST = timezone(timedelta(hours=-12))     # 지구상 가장 이른 현재 날짜


def _now() -> datetime:
    """테스트가 바꿔 끼운다."""
    return datetime.now(UTC)


def farm_today(tz_name: str | None) -> tuple[date, str]:
    """농장 현지 날짜와 실제로 쓴 timezone 이름. 알 수 없는 timezone → UTC-12 (완료를 늦게 선언하는 쪽)."""
    try:
        tz = ZoneInfo(tz_name or "")
        return _now().astimezone(tz).date(), str(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return _now().astimezone(_EARLIEST).date(), "UTC-12(fallback)"


def period_is_partial(end: date, today: date) -> bool:
    """완료월 = 농장 현지 날짜로 월말이 지났다. 월말 당일·미래 달은 진행 중."""
    return today <= end


def _month(p: str) -> tuple[date, date]:
    if not _YM.match(p or ""):
        raise HTTPException(422, "period must be YYYY-MM")
    start = date(int(p[:4]), int(p[5:7]), 1)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return start, end


async def _inputs(db, farm, start: date, end: date, basis: Basis, *, with_prev: bool) -> tuple[FeedInput, FeedInput | None, dict]:
    if basis == "AS_RECORDED":
        cur = await load_feed_input(db, farm, start, end, with_cohort=False)
        prov = {"source_systems": ["pigos_manual"], "contract_versions": [], "rows": len(cur.rows)}
        prev = None
        if with_prev:
            ps, pe = _month(f"{(start - timedelta(days=1)):%Y-%m}")
            prev = await load_feed_input(db, farm, ps, pe, with_cohort=False)
    else:
        cur, lineage = await load_feed_input_from_source(db, farm.id, start, end, quantity_basis="DELIVERED")
        prov = {"source_systems": [s for s in [lineage.get("source_system")] if s] or ["feed_source_rows"],
                "contract_versions": lineage["contract_versions"], "rows": len(cur.rows)}
        prev = None
        if with_prev:
            ps, pe = _month(f"{(start - timedelta(days=1)):%Y-%m}")
            prev, _ = await load_feed_input_from_source(db, farm.id, ps, pe, quantity_basis="DELIVERED")
    return cur, prev, prov


def _metric_out(r: FeedMetricResult, status: dict | None) -> MetricOut:
    ev = {k: v for k, v in r.evidence.items() if k not in ("exact_shares",)}
    return MetricOut(value=r.value, unit=r.unit, provenance=r.provenance, reason=r.reason, evidence=ev, status=status)


@router.get("/summary", response_model=FeedSummaryOut)
async def feed_summary(
    farm: FarmDep, db: DbDep,
    period: str = Query(..., description="YYYY-MM (달력월)"),
    basis: Basis = Query(..., description="AS_RECORDED (수기) | DELIVERED (입고 원장)"),
):
    start, end = _month(period)
    today, tz_used = farm_today(getattr(farm, "timezone", None))
    partial = period_is_partial(end, today)
    cur, prev, prov = await _inputs(db, farm, start, end, basis, with_prev=not partial)
    res = m.compute_all(cur, prev)
    if partial:   # B-1: 진행 중인 달은 비교하지 않는다 — 키는 남기고 값은 null + 사유
        ev = {"period_end": end.isoformat(), "farm_today": today.isoformat(), "timezone": tz_used}
        res[m.FEED_QTY_CHANGE] = replace(insufficient(m.FEED_QTY_CHANGE, "kg", R_PARTIAL_PERIOD, **ev), quantity_basis=cur.quantity_basis)
        res[m.FEED_COST_CHANGE] = replace(insufficient(m.FEED_COST_CHANGE, "currency", R_PARTIAL_PERIOD, **ev), quantity_basis=cur.quantity_basis)
    findings = deterministic_findings(res)
    statuses = to_kpi_status(res, findings, policy_kpis=None)
    currency = None
    if cur.rows:
        ccy = {r.currency for r in cur.rows if r.costed}
        currency = next(iter(ccy)) if len(ccy) == 1 else None
    return FeedSummaryOut(
        farm_id=str(farm.id),
        period={"start": start.isoformat(), "end": end.isoformat(), "grain": "calendar_month",
                "partial": partial, "as_of": today.isoformat(), "timezone": tz_used,
                "comparison": None if partial else "previous_calendar_month"},
        quantity_basis=cur.quantity_basis, currency=currency, formula_version=next(iter(res.values())).formula_version,
        metrics={k: _metric_out(r, statuses.get(k).model_dump() if statuses.get(k) else None) for k, r in res.items()},
        findings=[{"rule_id": f.rule_id, "kpi": f.kpi, "severity": str(f.severity.value if hasattr(f.severity, "value") else f.severity),
                   "detail": f.detail} for f in findings],
        no_data=not cur.rows,
        provenance=prov,
    )


@router.get("/months", response_model=list[FeedMonthOut])
async def feed_months(
    farm: FarmDep, db: DbDep,
    basis: Basis = Query(...),
    from_: str = Query(..., alias="from"), to: str = Query(...),
):
    s0, _ = _month(from_)
    _, e1 = _month(to)
    today, _tz = farm_today(getattr(farm, "timezone", None))
    if s0 > e1:
        raise HTTPException(422, "from must be <= to")
    out: list[FeedMonthOut] = []
    cursor = s0
    for _ in range(36):                       # 최대 36개월 — 페이지네이션 대신 상한
        if cursor > e1:
            break
        ms, me = _month(f"{cursor:%Y-%m}")
        cur, _, _ = await _inputs(db, farm, ms, me, basis, with_prev=False)
        res = m.compute_all(cur)
        q, c, up, mix = res[m.FEED_QTY], res[m.FEED_COST], res[m.FEED_UNIT_PRICE], res[m.FEED_MIX_SHARE]
        ccy = {r.currency for r in cur.rows if r.costed}
        out.append(FeedMonthOut(
            period=f"{cursor:%Y-%m}", quantity_basis=cur.quantity_basis, currency=next(iter(ccy)) if len(ccy) == 1 else None,
            rows=len(cur.rows), feed_qty_kg=q.value, feed_cost=c.value, feed_cost_reason=c.reason,
            partial_cost=c.evidence.get("partial_cost"), unit_price=up.value, dominant_type=mix.evidence.get("dominant_type"),
            partial=period_is_partial(me, today),
        ))
        cursor = me + timedelta(days=1)
    return out
