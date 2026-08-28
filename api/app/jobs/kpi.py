"""
KPI aggregation jobs — run by ARQ worker.

Scheduled (see WorkerSettings.cron_jobs):
  daily_kpi_aggregation   — 매일 00:05 UTC
  weekly_kpi_aggregation  — 매주 월요일 00:10 UTC
  monthly_kpi_aggregation — 매월 1일 00:15 UTC

On-demand (triggered after event write):
  recalculate_farm_kpi(farm_id, period_start, period_end)
"""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.farm_time import today_in_tz
from app.db.models.events import Farrowing, Mating, Weaning
from app.db.models.ops import KpiSnapshot
from app.db.models.platform import Farm
from app.db.models.sow import Sow
from app.db.session import AsyncSessionLocal
from app.jobs._result import job_result

log = logging.getLogger(__name__)


# -- Snapshot supported-field contract ----------------------------------------
# 2026-08-28 런타임 감사: 이 잡은 2026-05-29(26c2e68) 이래 한 번도 성공한 적이 없다.
#   _calculate_farm_kpi 가 "farrowing_rate" 를 반환하는데 KpiSnapshot 에 그 컬럼이 없어
#   TypeError 로 71농장 전건 실패했고, 잡은 성공으로 보고했다.
#   두 파일이 같은 커밋에서 태어나면서 어긋났다 - 표류가 아니라 처음부터 안 맞았다.
#   근거: docs/runs/RUNTIME_INTEGRITY_AUDIT_20260828.md A4
#
#   재발 방지: 모델 컬럼을 런타임에 읽어 그것만 저장한다. 페이로드에 새 키가 생겨도
#   전건 실패로 번지지 않고 그 필드만 빠진다(per-field fail-safe).

_SNAPSHOT_COLUMNS: frozenset[str] = frozenset(
    c.key for c in sa_inspect(KpiSnapshot).mapper.column_attrs
)

# 컬럼이 있더라도 아직 영속하면 안 되는 필드. 이유 없이 추가하지 말 것.
_WITHHELD_FIELDS: dict[str, str] = {
    "farrowing_rate": (
        "canonical formula AMBIGUOUS - 산식 4개가 live 다(D-13 재실사 1-3). "
        "P0-2/D-13 확정 전에는 어느 산식의 값인지 말할 수 없으므로 영속 금지."
    ),
    "psy": (
        "이 잡의 PSY 는 canonical(kpi_service.calculate_psy) 과 분모가 다르다"
        "(D-13 재실사 1-4: point-in-time 재고, parity 필터 없음). "
        "정렬 전에 저장하면 대시보드와 다른 PSY 가 영속된다."
    ),
}


def _snapshot_payload(kpi: dict) -> tuple[dict, dict[str, str]]:
    """KpiSnapshot 에 실제로 넣을 수 있고, 넣어도 되는 필드만 남긴다.

    반환 (persisted, dropped) - dropped 는 {필드: 사유}.
    """
    persisted: dict = {}
    dropped: dict[str, str] = {}
    for k, v in kpi.items():
        if k in _WITHHELD_FIELDS:
            dropped[k] = _WITHHELD_FIELDS[k]
        elif k not in _SNAPSHOT_COLUMNS:
            dropped[k] = "KpiSnapshot 에 해당 컬럼이 없다"
        else:
            persisted[k] = v
    return persisted, dropped


# ── Helpers ───────────────────────────────────────────────────────────────────

def _period_bounds(period_type: str, ref: date) -> tuple[date, date]:
    if period_type == "DAILY":
        return ref, ref
    if period_type == "WEEKLY":
        start = ref - timedelta(days=ref.weekday())
        return start, start + timedelta(days=6)
    if period_type == "MONTHLY":
        start = ref.replace(day=1)
        next_month = (start + timedelta(days=32)).replace(day=1)
        return start, next_month - timedelta(days=1)
    # ANNUAL
    return ref.replace(month=1, day=1), ref.replace(month=12, day=31)


def _last_completed_period(period_type: str, farm_today_value: date) -> tuple[date, date]:
    """농장 현지 오늘 기준으로 **이미 끝난** 직전 기간을 돌려준다.

    ★ 왜 이 함수가 필요한가 (독립검증 2026-08-25)
      예전에는 cron 이 도는 **시각**이 기간을 정했다. 월간 잡이 UTC 1일 00:15 에 돌면서
      농장 현지 날짜로 기간을 계산하니, America/Chicago 는 그 순간 **전월 마지막 날**이라
      한 달 전 기간을 계산했다 → 8월 스냅샷이 10월 1일까지 한 달 늦어진다.
      주간도 같은 방식으로 최신 주가 일주일 늦었다.

      그래서 "언제 도느냐"와 "무슨 기간을 계산하느냐"를 분리한다. 잡은 매일 돌고,
      각 농장의 현지 날짜 기준으로 **끝난 기간**을 집계한다. 이미 계산된 기간은
      같은 값으로 다시 upsert 되므로(멱등) 매일 돌아도 안전하다.
    """
    if period_type == "DAILY":
        d = farm_today_value - timedelta(days=1)          # 어제 = 마지막으로 끝난 하루
        return d, d
    if period_type == "WEEKLY":
        this_week_start = farm_today_value - timedelta(days=farm_today_value.weekday())
        last_week_start = this_week_start - timedelta(days=7)
        return last_week_start, last_week_start + timedelta(days=6)
    if period_type == "MONTHLY":
        this_month_start = farm_today_value.replace(day=1)
        last_month_end = this_month_start - timedelta(days=1)
        return last_month_end.replace(day=1), last_month_end
    raise ValueError(f"unsupported period_type: {period_type}")


async def _calculate_farm_kpi(
    db: AsyncSession,
    farm_id: UUID,
    period_type: str,
    period_start: date,
    period_end: date,
) -> dict:
    """Calculate KPI values for a farm/period. Returns dict ready for KpiSnapshot."""

    # Active sow counts
    active = await db.scalar(
        select(func.count()).select_from(Sow).where(
            Sow.farm_id == farm_id,
            Sow.deleted_at.is_(None),
            Sow.status.notin_(["CULLED", "DEAD"]),
        )
    ) or 0
    gestating = await db.scalar(
        select(func.count()).select_from(Sow).where(
            Sow.farm_id == farm_id, Sow.status == "PREGNANT", Sow.deleted_at.is_(None)
        )
    ) or 0
    lactating = await db.scalar(
        select(func.count()).select_from(Sow).where(
            Sow.farm_id == farm_id, Sow.status == "LACTATING", Sow.deleted_at.is_(None)
        )
    ) or 0

    # Farrowings in period
    farrowings = list(await db.scalars(
        select(Farrowing).where(
            Farrowing.farm_id == farm_id,
            Farrowing.farrowing_date >= period_start,
            Farrowing.farrowing_date <= period_end,
            Farrowing.deleted_at.is_(None),
        )
    ))

    # Matings in period
    matings_count = await db.scalar(
        select(func.count()).select_from(Mating).where(
            Mating.farm_id == farm_id,
            Mating.mating_date >= period_start,
            Mating.mating_date <= period_end,
            Mating.deleted_at.is_(None),
        )
    ) or 0

    # Weanings in period — for PSY calculation
    weanings = list(await db.scalars(
        select(Weaning).where(
            Weaning.farm_id == farm_id,
            Weaning.weaning_date >= period_start,
            Weaning.weaning_date <= period_end,
            Weaning.deleted_at.is_(None),
        )
    ))

    # PSY = (total_weaned / active_sows) * (365 / days_in_period)
    days = max((period_end - period_start).days + 1, 1)
    total_weaned = sum(w.weaned_count for w in weanings)
    psy = round((total_weaned / active * (365 / days)), 2) if active > 0 else None

    # Farrowing rate = farrowings / matings (same period)
    farrowing_rate = (
        round(len(farrowings) / matings_count * 100, 1) if matings_count > 0 else None
    )

    return {
        "psy": psy,
        "farrowing_rate": farrowing_rate,
        "active_sow_count": active,
        "gestating_count": gestating,
        "lactating_count": lactating,
    }


async def _upsert_snapshot(
    db: AsyncSession,
    farm_id: UUID,
    period_type: str,
    period_start: date,
    period_end: date,
    kpi: dict,
) -> None:
    existing = await db.scalar(
        select(KpiSnapshot).where(
            KpiSnapshot.farm_id == farm_id,
            KpiSnapshot.period_type == period_type,
            KpiSnapshot.period_start == period_start,
        )
    )
    persisted, dropped = _snapshot_payload(kpi)
    if dropped:
        # 조용히 버리지 않는다 - 무엇을 왜 안 넣었는지 보이게 한다.
        log.debug("snapshot fields withheld farm=%s: %s", farm_id, sorted(dropped))

    if existing:
        for k, v in persisted.items():
            setattr(existing, k, v)
        existing.is_stale = False
        existing.calculated_at = datetime.now(UTC)
    else:
        db.add(KpiSnapshot(
            farm_id=farm_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            is_stale=False,
            **persisted,
        ))
    await db.commit()


# ── ARQ job functions ─────────────────────────────────────────────────────────

async def _active_farms(db) -> list[tuple]:
    """활성 농장의 (id, timezone) — 기간 산출에 타임존이 필요하다."""
    return list((await db.execute(
        select(Farm.id, Farm.timezone).where(Farm.active.is_(True))
    )).all())


# ★ 스냅샷 기간은 **농장 현지 오늘** 기준으로 농장마다 따로 잡는다.
#   서버(컨테이너 UTC) 기준 하나로 잡으면, 잡이 도는 시각에 아직 하루가 끝나지 않은
#   농장의 스냅샷이 진행 중인 날짜로 찍힌다 — 예: 잡이 00:00 UTC 에 돌면 그 시각
#   America/Chicago 는 아직 전날 19:00 이라 "어제"가 실제로는 그 농장의 오늘이다.
#   상세: app/core/farm_time.py (2026-08-25 TZ 전수 점검)


async def daily_kpi_aggregation(ctx: dict) -> str:
    """Aggregate daily KPI snapshots for all active farms."""
    async with AsyncSessionLocal() as db:
        farms = await _active_farms(db)

    processed = errors = 0
    last_period = None
    for farm_id, tz in farms:
        try:
            period_start, period_end = _last_completed_period("DAILY", today_in_tz(tz))
            last_period = period_start
            async with AsyncSessionLocal() as db:
                kpi = await _calculate_farm_kpi(db, farm_id, "DAILY", period_start, period_end)
                await _upsert_snapshot(db, farm_id, "DAILY", period_start, period_end, kpi)
            processed += 1
        except Exception as e:
            log.error("daily_kpi farm=%s error=%s", farm_id, e)
            errors += 1

    return job_result(
        "daily_kpi_aggregation",
        expected=len(farms), success=processed, errors=errors,
        detail=f"period={last_period}",
    )


async def weekly_kpi_aggregation(ctx: dict) -> str:
    """Aggregate weekly KPI snapshots."""
    async with AsyncSessionLocal() as db:
        farms = await _active_farms(db)

    processed = errors = 0
    last_period = (None, None)
    for farm_id, tz in farms:
        try:
            period_start, period_end = _last_completed_period("WEEKLY", today_in_tz(tz))
            last_period = (period_start, period_end)
            async with AsyncSessionLocal() as db:
                kpi = await _calculate_farm_kpi(db, farm_id, "WEEKLY", period_start, period_end)
                await _upsert_snapshot(db, farm_id, "WEEKLY", period_start, period_end, kpi)
            processed += 1
        except Exception as e:
            log.error("weekly_kpi farm=%s error=%s", farm_id, e)
            errors += 1

    return job_result(
        "weekly_kpi_aggregation",
        expected=len(farms), success=processed, errors=errors,
        detail=f"period={last_period[0]}~{last_period[1]}",
    )


async def monthly_kpi_aggregation(ctx: dict) -> str:
    """Aggregate monthly KPI snapshots."""
    async with AsyncSessionLocal() as db:
        farms = await _active_farms(db)

    processed = errors = 0
    last_period = (None, None)
    for farm_id, tz in farms:
        try:
            period_start, period_end = _last_completed_period("MONTHLY", today_in_tz(tz))
            last_period = (period_start, period_end)
            async with AsyncSessionLocal() as db:
                kpi = await _calculate_farm_kpi(db, farm_id, "MONTHLY", period_start, period_end)
                await _upsert_snapshot(db, farm_id, "MONTHLY", period_start, period_end, kpi)
            processed += 1
        except Exception as e:
            log.error("monthly_kpi farm=%s error=%s", farm_id, e)
            errors += 1

    return job_result(
        "monthly_kpi_aggregation",
        expected=len(farms), success=processed, errors=errors,
        detail=f"period={last_period[0]}~{last_period[1]}",
    )


async def recalculate_farm_kpi(ctx: dict, farm_id: str, period_start: str, period_end: str) -> str:
    """
    On-demand recalculation triggered after event write (mating/farrowing/weaning).
    Marks matching snapshots as stale and recalculates.
    """
    fid = UUID(farm_id)
    ps = date.fromisoformat(period_start)
    pe = date.fromisoformat(period_end)

    periods = ("DAILY", "WEEKLY", "MONTHLY")
    processed = errors = 0
    for period_type in periods:
        try:
            async with AsyncSessionLocal() as db:
                kpi = await _calculate_farm_kpi(db, fid, period_type, ps, pe)
                await _upsert_snapshot(db, fid, period_type, ps, pe, kpi)
            processed += 1
        except Exception as e:
            log.error("recalc_kpi farm=%s period=%s error=%s", farm_id, period_type, e)
            errors += 1

    return job_result(
        "recalculate_farm_kpi",
        expected=len(periods), success=processed, errors=errors,
        detail=f"farm={farm_id} period={period_start}~{period_end}",
    )
