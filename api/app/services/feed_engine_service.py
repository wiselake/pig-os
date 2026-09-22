"""Feed Engine 로더 — DB 행 → RawFeedRow → normalize → FeedInput → compute (F2.5 vertical slice).

★ 어느 라우터에도 연결돼 있지 않다 (SPEC §15: 노출은 F3 + D-15/B-7 결재 뒤).
읽기 전용. 코호트는 PR #2 의 `feed_service.load_feed_cohort` 를 그대로 재사용한다 —
kpi_service:428-449 와 같은 CLOSED 그룹 정의가 세 곳이 되지 않게.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.health import FeedRecord
from app.db.models.ops import FinisherGroup
from app.engine.feed.metrics import compute_all
from app.engine.feed.normalize import RawFeedRow, normalize
from app.engine.feed.types import Cohort, FeedInput, FeedMetricResult, Period
from app.services import feed_service


async def _raw_rows(db: AsyncSession, farm_id: UUID, period: Period) -> list[RawFeedRow]:
    rows = list(await db.scalars(
        select(FeedRecord)
        .where(FeedRecord.farm_id == farm_id, FeedRecord.deleted_at.is_(None),
               FeedRecord.record_date >= period.start, FeedRecord.record_date <= period.end)
        .order_by(FeedRecord.record_date, FeedRecord.created_at, FeedRecord.id)
    ))
    # group_id 는 FK 가 없다 — 살아 있는 finisher_group 인지 여기서 확인해 orphan 표지를 만든다
    gids = {r.group_id for r in rows if r.group_id is not None}
    live: set[UUID] = set()
    if gids:
        live = set(await db.scalars(
            select(FinisherGroup.id).where(FinisherGroup.id.in_(gids), FinisherGroup.farm_id == farm_id,
                                           FinisherGroup.deleted_at.is_(None))))
    return [
        RawFeedRow(
            record_date=r.record_date,
            quantity_kg=Decimal(str(r.quantity_kg)),
            unit_cost=Decimal(str(r.unit_cost)) if r.unit_cost is not None else None,
            currency=r.currency,
            feed_type=r.feed_type,
            sow_id=str(r.sow_id) if r.sow_id else None,
            group_id=str(r.group_id) if r.group_id else None,
            building_id=str(r.building_id) if r.building_id else None,
            group_exists=(r.group_id in live) if r.group_id is not None else None,
        )
        for r in rows
    ]


async def _cohort(db: AsyncSession, farm_id: UUID, period: Period, farm_currency: str) -> Cohort:
    c = await feed_service.load_feed_cohort(db, farm_id, period.start, period.end, farm_currency=farm_currency)
    g = (await db.execute(text(
        "SELECT count(*) n, coalesce(sum((end_date - start_date) * head_count_out),0) pigdays "
        "FROM finisher_groups WHERE farm_id=:fid AND deleted_at IS NULL "
        "AND end_date IS NOT NULL AND head_count_out IS NOT NULL "
        "AND avg_exit_weight_kg IS NOT NULL AND avg_entry_weight_kg IS NOT NULL "
        "AND end_date BETWEEN :s AND :e"), {"fid": farm_id, "s": period.start, "e": period.end})).one()
    return Cohort(groups=int(g.n), head_out=c.head_out, gain_kg=c.gain_kg, pig_days=Decimal(str(g.pigdays)),
                  feed_kg=c.feed_kg, feed_cost=c.feed_cost, costed_rows=c.costed_rows,
                  uncosted_rows=c.uncosted_rows, currencies=c.currencies)


async def load_feed_input(db: AsyncSession, farm, start: date, end: date, *, with_cohort: bool = True) -> FeedInput:
    """farm 은 `farms` 행(currency 필요). period 는 농장 현지 날짜."""
    period = Period(start, end)
    ccy = (farm.currency or "USD").upper()
    raw = await _raw_rows(db, farm.id, period)
    cohort = await _cohort(db, farm.id, period, ccy) if with_cohort else None
    return normalize(raw, period=period, farm_currency=ccy, cohort=cohort)


async def compute_feed_metrics(
    db: AsyncSession, farm, start: date, end: date, *, with_previous: bool = True,
) -> dict[str, FeedMetricResult]:
    """세로 슬라이스: 로더 → 정규화 → 계산. 이전 기간 = 같은 길이의 직전 구간."""
    cur = await load_feed_input(db, farm, start, end)
    prev = None
    if with_previous:
        span = cur.period.days
        prev_end = date.fromordinal(start.toordinal() - 1)
        prev_start = date.fromordinal(prev_end.toordinal() - span + 1)
        prev = await load_feed_input(db, farm, prev_start, prev_end, with_cohort=False)
    return compute_all(cur, prev)


# ── 외부 소스 projection (P-4) — feed_source_rows → FeedInput. feed_records(AS_RECORDED) 와 절대 합치지 않는다 ──
async def load_feed_input_from_source(
    db: AsyncSession, farm_id: UUID, start: date, end: date, *, quantity_basis: str, source_system: str | None = None,
) -> tuple[FeedInput, dict]:
    """현재·ACTIVE·수량 ACCEPTED 관측만 → FeedInput(basis 명시). 코호트 없음(외부 입고 소스는 그룹 귀속이 없다).

    farm_currency 는 **행의 통화**에서 온다 — farms.currency 를 읽지 않는다 (D-FEED-02). 행이 없으면 통화 미상("XXX"):
    FeedInput.farm_currency 는 NULL 통화 fallback 용인데 이 경로의 행은 전부 통화가 있으므로 실제로 쓰이지 않는다.
    반환 lineage: metric → FeedInput 행 순서 → source_row_ids → (source_system, source_row_key, contract) 역추적용 (§26).
    """
    from app.repositories import feed_source_repo as repo  # 지연 import — 엔진 순수성 검사와 무관한 서비스 계층

    period = Period(start, end)
    proj = await repo.load_raw_rows(db, farm_id, period, quantity_basis=quantity_basis, source_system=source_system)
    if len(proj.currencies) > 1:
        ccy = "XXX"          # 통화 혼합은 엔진이 currency_mixed 로 유보한다 — 여기서 하나를 고르지 않는다
    else:
        ccy = next(iter(proj.currencies), "XXX")
    inp = normalize(proj.raw_rows, period=period, farm_currency=ccy, cohort=None, quantity_basis=quantity_basis)
    lineage = {"source_row_ids": [str(x) for x in proj.source_row_ids],
               "source_system": source_system, "quantity_basis": quantity_basis,
               "contract_versions": sorted(proj.contract_versions)}
    return inp, lineage
