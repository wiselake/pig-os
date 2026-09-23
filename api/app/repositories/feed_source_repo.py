"""feed_source_rows 저장/조회 + canonical projection (P-2 identity · P-4 projection · P-5 correction).

쓰기 규칙 (불변 revision):
  ingest_observations()  같은 identity + 같은 payload_hash → 0건 (멱등)
                         같은 identity + 다른 payload_hash → 새 revision INSERT, 이전 current 는 superseded (정정 = append, P-5 B)
                         처음 보는 identity → revision 1
  retract_missing()      창 안에서 소스가 더 이상 주지 않는 identity → RETRACTED revision (tombstone). 물리 삭제 없음
읽기 규칙 (projection):
  load_raw_rows()        is_current AND source_status='ACTIVE' AND quantity_status='ACCEPTED' AND basis = 요청 basis
                         → RawFeedRow (엔진은 이 ORM 을 모른다). 통화는 행의 값 그대로 — farm.currency 를 보지 않는다
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.feed_source import FeedSourceRow
from app.engine.feed.normalize import RawFeedRow
from app.engine.feed.types import Period

NS = uuid.uuid5(uuid.NAMESPACE_DNS, "pigos.feed_source")
ASYNCPG_MAX_PARAMS = 32000          # asyncpg 상한 32,767 아래 여유


@dataclass(frozen=True)
class Observation:
    """소스 어댑터 → 저장 경계. 값만. 식별정보 없음(farm 은 내부 UUID)."""
    source_system: str
    source_dataset: str
    source_row_key: str
    source_contract_version: str
    farm_id: UUID
    event_date: date | None
    event_date_raw: str | None
    quantity_kg: Decimal | None
    quantity_basis: str
    unit_cost: Decimal | None
    total_cost: Decimal | None
    currency: str
    feed_stage_raw: str | None
    feed_product_raw: str | None
    source_status: str                      # ACTIVE | INACTIVE (RETRACTED 는 retract_missing 이 만든다)
    quantity_status: str
    cost_status: str
    quality_reasons: tuple[str, ...] = ()
    source_inserted_at: datetime | None = None
    source_updated_at: datetime | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def identity(self) -> tuple[str, str, str]:
        return (self.source_system, self.source_dataset, self.source_row_key)

    def payload_hash(self) -> str:
        """정규화 payload 의 sha256 — 의미 있는 필드만. observed_at·sync_run 은 넣지 않는다(재실행이 같은 해시)."""
        body = {
            "event_date": self.event_date.isoformat() if self.event_date else self.event_date_raw,
            "quantity_kg": str(self.quantity_kg) if self.quantity_kg is not None else None,
            "quantity_basis": self.quantity_basis,
            "unit_cost": str(self.unit_cost) if self.unit_cost is not None else None,
            "total_cost": str(self.total_cost) if self.total_cost is not None else None,
            "currency": self.currency,
            "feed_stage_raw": self.feed_stage_raw,
            "feed_product_raw": self.feed_product_raw,
            "source_status": self.source_status,
            "quantity_status": self.quantity_status,
            "cost_status": self.cost_status,
            "quality_reasons": list(self.quality_reasons),
            "source_updated_at": self.source_updated_at.isoformat() if self.source_updated_at else None,
            "contract": self.source_contract_version,
        }
        return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def row_id(self) -> UUID:
        return uuid.uuid5(NS, ":".join([*self.identity, self.payload_hash()]))


@dataclass
class IngestResult:
    inserted: int = 0
    unchanged: int = 0
    superseded: int = 0
    retracted: int = 0


async def ingest_observations(db: AsyncSession, obs: list[Observation], *, observed_at: datetime,
                              sync_run_id: UUID | None = None, batch_size: int = 2000) -> IngestResult:
    """멱등 append. 한 배치 안에서 같은 identity 가 두 번 오면 마지막 것만 (소스 PK 라 실제로는 오지 않는다)."""
    res = IngestResult()
    if not obs:
        return res
    by_identity = {o.identity: o for o in obs}
    keys = list(by_identity)
    # 현재 revision 조회 (identity → (id, revision, payload_hash))
    current: dict[tuple[str, str, str], tuple[UUID, int, str]] = {}
    row_keys = [k[2] for k in keys]
    for i in range(0, len(row_keys), 5000):
        cur_rows = (await db.execute(
            select(FeedSourceRow.source_system, FeedSourceRow.source_dataset, FeedSourceRow.source_row_key,
                   FeedSourceRow.id, FeedSourceRow.revision, FeedSourceRow.payload_hash)
            .where(FeedSourceRow.is_current.is_(True),
                   FeedSourceRow.source_system == keys[0][0],
                   FeedSourceRow.source_dataset == keys[0][1],
                   FeedSourceRow.source_row_key.in_(row_keys[i:i + 5000]))
        )).all()
        current.update({(r[0], r[1], r[2]): (r[3], r[4], r[5]) for r in cur_rows})

    to_supersede: list[UUID] = []
    values: list[dict[str, Any]] = []
    for ident, o in by_identity.items():
        h = o.payload_hash()
        cur = current.get(ident)
        if cur is not None and cur[2] == h:
            res.unchanged += 1
            continue
        revision = 1 if cur is None else cur[1] + 1
        if cur is not None:
            to_supersede.append(cur[0])
            res.superseded += 1
        values.append({
            "id": o.row_id(), "source_system": o.source_system, "source_dataset": o.source_dataset,
            "source_row_key": o.source_row_key, "source_contract_version": o.source_contract_version,
            "revision": revision, "is_current": True, "sync_run_id": sync_run_id, "farm_id": o.farm_id,
            "event_date": o.event_date, "event_date_raw": o.event_date_raw,
            "quantity_kg": o.quantity_kg, "quantity_unit": "kg", "quantity_basis": o.quantity_basis,
            "unit_cost": o.unit_cost, "total_cost": o.total_cost, "currency": o.currency,
            "feed_stage_raw": o.feed_stage_raw, "feed_product_raw": o.feed_product_raw,
            "source_status": o.source_status, "quantity_status": o.quantity_status, "cost_status": o.cost_status,
            "quality_reasons": list(o.quality_reasons), "observed_at": observed_at,
            "source_inserted_at": o.source_inserted_at, "source_updated_at": o.source_updated_at,
            "payload_hash": h, "payload": o.payload,
        })
        res.inserted += 1
    for i in range(0, len(to_supersede), 5000):
        await db.execute(update(FeedSourceRow).where(FeedSourceRow.id.in_(to_supersede[i:i + 5000]))
                         .values(is_current=False, superseded_at=observed_at))
    if values:
        # 같은 id(= identity+payload) 가 이미 있으면(과거 revision 으로 되돌아온 정정) 새 행을 만들지 않는다 —
        # 그 경우는 이력상 존재하는 revision 이므로 current 로 되살린다.
        # 배치는 같은 트랜잭션 안의 statement 분할일 뿐이다 — 부분 커밋 없음.
        # asyncpg 는 statement 당 바인드 32,767 개 상한 (L1 실측: 2,000행×30열 = 60k → InterfaceError) → 열 수로 상한을 다시 계산.
        # ★ statement 는 한 번만 컴파일하고 파라미터 리스트를 넘긴다(insertmanyvalues) — L6 프로파일: 다중 VALUES 리터럴 컴파일이 3.6 s/5.5k행
        per_stmt = max(1, min(batch_size, ASYNCPG_MAX_PARAMS // len(values[0])))
        stmt = pg_insert(FeedSourceRow).on_conflict_do_update(
            constraint="uq_fsr_identity_payload",
            set_={"is_current": True, "superseded_at": None, "sync_run_id": sync_run_id, "observed_at": observed_at})
        for i in range(0, len(values), per_stmt):
            await db.execute(stmt, values[i:i + per_stmt])
    await db.flush()
    return res


async def retract_missing(db: AsyncSession, *, source_system: str, source_dataset: str, farm_ids: list[UUID],
                          window: Period, present_keys: set[str], observed_at: datetime,
                          sync_run_id: UUID | None = None) -> int:
    """창 안 current·비RETRACTED 행 중 소스가 이번에 주지 않은 identity → RETRACTED revision. 값은 이전 revision 복사."""
    base = [FeedSourceRow.source_system == source_system, FeedSourceRow.source_dataset == source_dataset,
            FeedSourceRow.farm_id.in_(farm_ids), FeedSourceRow.is_current.is_(True),
            FeedSourceRow.source_status != "RETRACTED",
            FeedSourceRow.event_date >= window.start, FeedSourceRow.event_date <= window.end]
    # 키만 먼저 (ORM 객체 5k 개를 비교 때문에 만들지 않는다 — L6) → 사라진 키의 행만 로드
    keys = [k for (k,) in (await db.execute(select(FeedSourceRow.source_row_key).where(*base))).all()]
    gone_keys = [k for k in keys if k not in present_keys]
    if not gone_keys:
        return 0
    gone = (await db.execute(select(FeedSourceRow).where(*base, FeedSourceRow.source_row_key.in_(gone_keys)))).scalars().all()
    obs = [Observation(
        source_system=r.source_system, source_dataset=r.source_dataset, source_row_key=r.source_row_key,
        source_contract_version=r.source_contract_version, farm_id=r.farm_id, event_date=r.event_date,
        event_date_raw=r.event_date_raw, quantity_kg=Decimal(str(r.quantity_kg)) if r.quantity_kg is not None else None,
        quantity_basis=r.quantity_basis, unit_cost=Decimal(str(r.unit_cost)) if r.unit_cost is not None else None,
        total_cost=Decimal(str(r.total_cost)) if r.total_cost is not None else None, currency=r.currency,
        feed_stage_raw=r.feed_stage_raw, feed_product_raw=r.feed_product_raw,
        source_status="RETRACTED", quantity_status=r.quantity_status, cost_status=r.cost_status,
        quality_reasons=tuple(r.quality_reasons or ()) + ("SOURCE_ROW_MISSING",),
        source_inserted_at=r.source_inserted_at, source_updated_at=r.source_updated_at, payload=r.payload or {},
    ) for r in gone]
    res = await ingest_observations(db, obs, observed_at=observed_at, sync_run_id=sync_run_id)
    return res.inserted


# ── projection (P-4) ────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Projection:
    raw_rows: list[RawFeedRow]
    source_row_ids: list[UUID]          # lineage: FeedInput 행 순서와 같다
    currencies: frozenset[str]
    contract_versions: frozenset[str]


async def load_raw_rows(db: AsyncSession, farm_id: UUID, period: Period, *, quantity_basis: str,
                        source_system: str | None = None) -> Projection:
    """현재·ACTIVE·수량 ACCEPTED 행만 → RawFeedRow. 원가 INSUFFICIENT/EXCLUDED 행은 unit_cost=None 으로 들어간다(partial 은 엔진 몫)."""
    conds = [FeedSourceRow.farm_id == farm_id, FeedSourceRow.is_current.is_(True),
             FeedSourceRow.source_status == "ACTIVE", FeedSourceRow.quantity_status == "ACCEPTED",
             FeedSourceRow.quantity_basis == quantity_basis,
             FeedSourceRow.event_date >= period.start, FeedSourceRow.event_date <= period.end]
    if source_system:
        conds.append(FeedSourceRow.source_system == source_system)
    rows = (await db.execute(select(FeedSourceRow).where(and_(*conds))
                             .order_by(FeedSourceRow.event_date, FeedSourceRow.source_row_key))).scalars().all()
    raws = [RawFeedRow(
        record_date=r.event_date, quantity_kg=Decimal(str(r.quantity_kg)),
        unit_cost=Decimal(str(r.unit_cost)) if (r.cost_status == "ACCEPTED" and r.unit_cost is not None) else None,
        currency=r.currency, feed_type=r.feed_stage_raw, sow_id=None, group_id=None, building_id=None,
    ) for r in rows]
    return Projection(raw_rows=raws, source_row_ids=[r.id for r in rows],
                      currencies=frozenset(r.currency for r in rows),
                      contract_versions=frozenset(r.source_contract_version for r in rows))


async def count_rows(db: AsyncSession, **where: Any) -> int:
    conds = [getattr(FeedSourceRow, k) == v for k, v in where.items()]
    return int(await db.scalar(select(func.count()).select_from(FeedSourceRow).where(and_(*conds))) or 0) if conds \
        else int(await db.scalar(select(func.count()).select_from(FeedSourceRow)) or 0)
