"""사료 급여(Feed) 서비스 — 수기 급이량 CRUD.

FCR(kpi_service)·grow-finish 리포트가 SUM(feed_records.quantity_kg)을 읽으므로, 본 입력이 그 입력원.
검증: quantity_kg>0(스키마) + 월마감 잠금(period_locks) 시 423. soft-delete.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.farm_time import farm_today_by_id
from app.db.models.health import FeedRecord
from app.db.models.ops import FinisherGroup
from app.db.models.sow import Building, Sow
from app.engine.feed_metrics import FeedCohort
from app.schemas.feed import FeedRecordCreate
from app.services.event_service import _ensure_period_unlocked


async def _ensure_target_in_farm(db: AsyncSession, farm_id: UUID, body: FeedRecordCreate) -> None:
    """사료 대상(sow/group/building)이 해당 농장 소속인지 검증 — 크로스테넌트 오염 차단."""
    if body.sow_id is not None:
        ok = await db.scalar(
            select(Sow.id).where(Sow.id == body.sow_id, Sow.farm_id == farm_id)
        )
        if not ok:
            raise NotFoundError(f"Sow {body.sow_id} not found in this farm")
    if body.group_id is not None:
        ok = await db.scalar(
            select(FinisherGroup.id).where(
                FinisherGroup.id == body.group_id, FinisherGroup.farm_id == farm_id
            )
        )
        if not ok:
            raise NotFoundError(f"Finisher group {body.group_id} not found in this farm")
    if body.building_id is not None:
        ok = await db.scalar(
            select(Building.id).where(
                Building.id == body.building_id, Building.farm_id == farm_id
            )
        )
        if not ok:
            raise NotFoundError(f"Building {body.building_id} not found in this farm")


async def create_feed_record(
    db: AsyncSession, farm_id: UUID, user_id: UUID, body: FeedRecordCreate
) -> FeedRecord:
    # 대상 중복 지정 방지(있으면 1종만)
    targets = [t for t in (body.sow_id, body.group_id, body.building_id) if t is not None]
    if len(targets) > 1:
        raise ValidationError("Specify at most one target among sow_id / group_id / building_id")
    # ★ 미래 급여일 거부 — **농장 현지 오늘** 기준. 스키마는 농장을 몰라 +1일까지만
    #   거르므로 정확한 판정은 여기서 한다(app/core/farm_time.py).
    if body.record_date > await farm_today_by_id(db, farm_id):
        raise ValidationError(
            f"record_date {body.record_date} cannot be in the future")
    # 대상이 해당 농장 소속인지 검증 (크로스테넌트 차단)
    await _ensure_target_in_farm(db, farm_id, body)
    # 월마감 잠금 검사 (잠긴 기간이면 PeriodLockedError → 423)
    await _ensure_period_unlocked(db, farm_id, body.record_date)

    rec = FeedRecord(
        farm_id=farm_id, record_date=body.record_date, quantity_kg=body.quantity_kg,
        feed_type=body.feed_type, sow_id=body.sow_id, group_id=body.group_id,
        building_id=body.building_id, unit_cost=body.unit_cost, currency=body.currency,
        notes=body.notes, created_by=user_id,
    )
    db.add(rec)
    await db.flush()
    await db.commit()
    await db.refresh(rec)
    return rec


async def load_feed_cohort(
    db: AsyncSession, farm_id: UUID, start: date, end: date
) -> FeedCohort:
    """Feed Basic 코호트 — kpi_service 의 FCR 과 같은 CLOSED 그룹 집합 (F-0011).

    gain·head_out 은 end_date 가 [start, end] 인 CLOSED finisher_groups 에서, 사료는 그 그룹에
    group_id 로 귀속된 행의 전생애 합에서 온다. 두 SQL 의 그룹 조건은 kpi_service:428-449 와
    문자 그대로 같아야 한다 — 어긋나면 FCR 이 두 값이 된다.

    원가는 unit_cost 있는 행만 합산하고 없는 행은 **센다**. 채우지 않는다.
    ★ 어느 라우터에도 연결돼 있지 않다 (F-0011 범위 결정 (나)).
    """
    p = {"fid": farm_id, "s": start, "e": end}
    gf = (await db.execute(text(
        "SELECT coalesce(sum(head_count_out),0) hout, "
        "coalesce(sum((avg_exit_weight_kg - avg_entry_weight_kg) * head_count_out),0) gain "
        "FROM finisher_groups WHERE farm_id=:fid AND deleted_at IS NULL "
        "AND end_date IS NOT NULL AND head_count_out IS NOT NULL "
        "AND avg_exit_weight_kg IS NOT NULL AND avg_entry_weight_kg IS NOT NULL "
        "AND end_date BETWEEN :s AND :e"), p)).one()
    fr = (await db.execute(text(
        "SELECT coalesce(sum(fr.quantity_kg),0) feed_kg, "
        "sum(fr.quantity_kg * fr.unit_cost) FILTER (WHERE fr.unit_cost IS NOT NULL) feed_cost, "
        "count(*) FILTER (WHERE fr.unit_cost IS NOT NULL) costed, "
        "count(*) FILTER (WHERE fr.unit_cost IS NULL) uncosted, "
        "array_remove(array_agg(DISTINCT fr.currency), NULL) currencies "
        "FROM feed_records fr JOIN finisher_groups g ON g.id = fr.group_id "
        "WHERE fr.farm_id=:fid AND fr.deleted_at IS NULL AND g.deleted_at IS NULL "
        "AND g.end_date IS NOT NULL AND g.end_date BETWEEN :s AND :e"), p)).one()
    return FeedCohort(
        feed_kg=Decimal(str(fr.feed_kg)),
        gain_kg=Decimal(str(gf.gain)),
        head_out=int(gf.hout),
        feed_cost=Decimal(str(fr.feed_cost)) if fr.feed_cost is not None else None,
        costed_rows=int(fr.costed),
        uncosted_rows=int(fr.uncosted),
        currencies=frozenset(fr.currencies or ()),
    )


async def list_feed_records(
    db: AsyncSession, farm_id: UUID, *, limit: int = 50, offset: int = 0
) -> list[FeedRecord]:
    rows = await db.scalars(
        select(FeedRecord)
        .where(FeedRecord.farm_id == farm_id, FeedRecord.deleted_at.is_(None))
        .order_by(FeedRecord.record_date.desc(), FeedRecord.created_at.desc())
        .limit(limit).offset(offset)
    )
    return list(rows)


async def delete_feed_record(db: AsyncSession, farm_id: UUID, record_id: UUID) -> None:
    rec = await db.scalar(
        select(FeedRecord).where(
            FeedRecord.id == record_id, FeedRecord.farm_id == farm_id,
            FeedRecord.deleted_at.is_(None),
        )
    )
    if not rec:
        raise NotFoundError("Feed record not found")
    await _ensure_period_unlocked(db, farm_id, rec.record_date)
    from datetime import UTC, datetime
    rec.deleted_at = datetime.now(UTC)
    await db.commit()
