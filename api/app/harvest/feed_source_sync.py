"""PigPlan 사료 입고 원장 → feed_source_rows 동기화 (계약 + 구현, 스케줄러 없음).

계약 (docs/feed/FEED_PERSISTENCE_ARCHITECTURE.md §SYNC):
  window      [today − lookback_days, today] 의 event_date 를 **전량** 가져와 대조한다 — 늦게 들어오는 행(p95 88일, max 347일)과
              소스에서 사라진 행(RETRACTED) 을 잡으려면 증분(watermark)만으로는 부족하다
  watermark   관측 기록용: 이번 실행이 본 max(LOG_UPT_DT). 다음 실행의 증분 최적화 근거이지 정확성의 근거가 아니다
  idempotent  같은 소스 상태를 몇 번 돌려도 revision 이 늘지 않는다 (payload_hash)
  correction  값이 바뀐 identity → 새 revision (이전 superseded). 조용히 덮어쓰지 않는다
  inactive    USE_YN≠Y 는 소스의 soft-delete(UPDATE) 다 → source_status INACTIVE revision. 물리 삭제 아님
  missing     창 안에서 소스가 더 주지 않는 identity → RETRACTED revision (tombstone)
  failure     소스 예외 → 원장 SOURCE_UNAVAILABLE, 데이터 변경 0. 저장 예외 → SYNC_FAILED, rollback. 빈 결과로 해석하지 않는다
  ledger      feed_source_sync_runs 한 행 / 실행
금지: 스케줄러 등록 · 프로덕션 실행 · feed_records 접근
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.feed_source import FeedSourceSyncRun
from app.engine.feed.types import QUANTITY_BASIS_DELIVERED, Period
from app.harvest import pigplan_feed_delivery as pf
from app.repositories import feed_source_repo as repo


class FeedDeliverySourceLike(Protocol):
    def fetch_rows(self, farm_nos: list[int], start: date, end: date) -> list[pf.PigPlanFeedDeliveryRow]: ...


def to_observation(row: pf.PigPlanFeedDeliveryRow, cls: pf.RowClassification, farm_id: UUID) -> repo.Observation:
    """adapter 행 + 분류 → 저장 관측. basis/currency 는 소스 계약에서 온다. farm 은 내부 UUID 만."""
    return repo.Observation(
        source_system=pf.SOURCE_SYSTEM, source_dataset=pf.SOURCE_DATASET, source_row_key=pf.source_row_key(row),
        source_contract_version=pf.SOURCE_CONTRACT_VERSION, farm_id=farm_id,
        event_date=row.wk_dt, event_date_raw=row.wk_dt_raw,
        quantity_kg=row.total_kg, quantity_basis=QUANTITY_BASIS_DELIVERED,
        unit_cost=cls.unit_cost, total_cost=row.total_price, currency=pf.SOURCE_CURRENCY,
        feed_stage_raw=row.feed_stage_name, feed_product_raw=row.feed_name,
        source_status="ACTIVE" if (row.use_yn or "") == "Y" else "INACTIVE",
        quantity_status=cls.quantity, cost_status=cls.cost, quality_reasons=cls.reasons,
        source_inserted_at=row.source_inserted_at, source_updated_at=row.source_updated_at,
        payload={"fper_price": str(row.fper_price) if row.fper_price is not None else None,
                 "feed_stage_cd": row.feed_stage_cd, "feed_cd": row.feed_cd, "country_code": row.country_code,
                 "account_cd": row.account_cd, "gain_yn": row.gain_yn, "has_supplier": row.has_supplier},
    )


@dataclass
class SyncOutcome:
    run_id: UUID
    status: str
    fetched: int = 0
    inserted: int = 0
    unchanged: int = 0
    superseded: int = 0
    retracted: int = 0
    error: str | None = None


async def run_pigplan_feed_sync(db: AsyncSession, source: FeedDeliverySourceLike, farm_map: dict[int, UUID], *,
                                today: date, lookback_days: int, observed_at: datetime,
                                window: Period | None = None) -> SyncOutcome:
    """한 번의 동기화. 호출자가 세션/소스를 준비한다. 스케줄러가 부르지 않는다(이번 단계)."""
    window = window or Period(today - timedelta(days=lookback_days), today)
    run = FeedSourceSyncRun(source_system=pf.SOURCE_SYSTEM, source_dataset=pf.SOURCE_DATASET,
                            source_contract_version=pf.SOURCE_CONTRACT_VERSION, status="RUNNING",
                            started_at=observed_at, window_start=window.start, window_end=window.end,
                            lookback_days=lookback_days, farms=len(farm_map))
    db.add(run)
    await db.flush()
    run_id = run.id

    # 1) 소스 읽기 — 실패는 SOURCE_UNAVAILABLE, 데이터 변경 0
    try:
        rows = source.fetch_rows(sorted(farm_map), window.start, window.end)
    except Exception as e:  # noqa: BLE001 — 소스 장애는 종류를 가리지 않고 '빈 데이터'로 읽지 않는다
        run.status, run.error, run.completed_at = "SOURCE_UNAVAILABLE", f"{type(e).__name__}: {e}"[:2000], observed_at
        await db.commit()
        return SyncOutcome(run_id=run_id, status="SOURCE_UNAVAILABLE", error=run.error)

    # 2) 분류 → 관측 → 멱등 저장 → 철회 감지. 저장 실패는 SYNC_FAILED + rollback (원장 행은 남긴다)
    try:
        obs: list[repo.Observation] = []
        present: set[str] = set()
        for r in rows:
            fid = farm_map.get(r.source_farm_no)
            if fid is None or r.seq is None:
                continue                      # 매핑 없는 농장/키 없는 행은 저장하지 않는다 (fuzzy 매칭 없음)
            c = pf.classify(r, today=today)
            if c.reasons == ("OUT_OF_FILTER",):
                continue
            o = to_observation(r, c, fid)
            obs.append(o)
            present.add(o.source_row_key)
        res = await repo.ingest_observations(db, obs, observed_at=observed_at, sync_run_id=run_id)
        retracted = await repo.retract_missing(db, source_system=pf.SOURCE_SYSTEM, source_dataset=pf.SOURCE_DATASET,
                                              farm_ids=list(farm_map.values()), window=window, present_keys=present,
                                              observed_at=observed_at, sync_run_id=run_id)
        wm = [r.source_updated_at for r in rows if r.source_updated_at is not None]
        run.status, run.completed_at = "SUCCEEDED", observed_at
        run.rows_fetched, run.rows_inserted, run.rows_unchanged = len(rows), res.inserted, res.unchanged
        run.rows_superseded, run.rows_retracted = res.superseded, retracted
        run.watermark_to = max(wm) if wm else None
        await db.commit()
        return SyncOutcome(run_id=run_id, status="SUCCEEDED", fetched=len(rows), inserted=res.inserted,
                           unchanged=res.unchanged, superseded=res.superseded, retracted=retracted)
    except Exception as e:  # noqa: BLE001
        await db.rollback()
        failed = FeedSourceSyncRun(id=run_id, source_system=pf.SOURCE_SYSTEM, source_dataset=pf.SOURCE_DATASET,
                                   source_contract_version=pf.SOURCE_CONTRACT_VERSION, status="SYNC_FAILED",
                                   started_at=observed_at, completed_at=observed_at, window_start=window.start,
                                   window_end=window.end, lookback_days=lookback_days, farms=len(farm_map),
                                   rows_fetched=len(rows), error=f"{type(e).__name__}: {e}"[:2000])
        db.add(failed)
        await db.commit()
        return SyncOutcome(run_id=run_id, status="SYNC_FAILED", fetched=len(rows), error=failed.error)

