"""Initial-load reconciliation — snapshot(원천) 과 feed_source_rows(대상) 를 **독립 경로**로 집계해 대조한다 (L1/L4).

원천 쪽 집계는 adapter 의 classify() 만 재사용하고 저장 코드는 부르지 않는다. 대상 쪽은 SQL 집계.
grain: total · farm · month · farm×month · status. 차이는 분류(§4)해서 돌려준다 — 숫자를 맞추지 않는다.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.feed_source import FeedSourceRow, FeedSourceSyncRun
from app.harvest import pigplan_feed_delivery as pf


def mask(farm_no: int) -> str:
    return hashlib.sha256(f"PP-{farm_no}".encode()).hexdigest()[:12]


def serialize_indep(indep: dict[tuple[int, str], dict[str, Any]], *, masked: bool) -> dict[str, dict[str, Any]]:
    """Oracle 독립 집계(farm×month) → JSON. masked=True 면 키에 원천 농장번호 대신 mask() — 서버로 옮길 때는 이것만 쓴다."""
    return {f"{mask(k[0]) if masked else k[0]}|{k[1]}": {kk: (str(vv) if vv is not None and not isinstance(vv, (int, dict)) else vv)
                                                          for kk, vv in v.items()} for k, v in indep.items()}


def indep_get(indep: dict[str, Any], farm_no: int, ym: str) -> dict[str, Any] | None:
    """원시 키(repo 밖 로컬 스냅샷)와 마스킹 키(프로덕션 읽기 전용 검증) 둘 다 받는다."""
    return indep.get(f"{farm_no}|{ym}") or indep.get(f"{mask(farm_no)}|{ym}")


@dataclass
class Expected:
    total: int = 0
    by_farm: Counter = field(default_factory=Counter)          # masked farm → rows
    by_month: Counter = field(default_factory=Counter)         # 'YYYY-MM' | 'dateless' → rows
    by_farm_month: Counter = field(default_factory=Counter)
    source_status: Counter = field(default_factory=Counter)    # ACTIVE/INACTIVE
    quantity_status: Counter = field(default_factory=Counter)
    cost_status: Counter = field(default_factory=Counter)
    identities: set[str] = field(default_factory=set)


def expected_from_rows(rows: list[pf.PigPlanFeedDeliveryRow], farm_nos: set[int], start: date, end: date, *, today: date) -> Expected:
    """저장 코드와 무관하게 '무엇이 저장돼야 하는가' 를 원천 행에서 직접 계산."""
    e = Expected()
    for r in rows:
        if r.source_farm_no not in farm_nos or r.seq is None:
            continue
        if r.wk_dt is not None and not (start <= r.wk_dt <= end):
            continue
        c = pf.classify(r, today=today)
        if c.reasons == ("OUT_OF_FILTER",):
            continue
        key = f"{r.source_farm_no}:{r.seq}"
        if key in e.identities:
            raise ValueError("source identity duplicated in snapshot — SOURCE_ANOMALY")
        e.identities.add(key)
        fm, ym = mask(r.source_farm_no), (r.wk_dt.strftime("%Y-%m") if r.wk_dt else "dateless")
        e.total += 1
        e.by_farm[fm] += 1
        e.by_month[ym] += 1
        e.by_farm_month[f"{fm}|{ym}"] += 1
        e.source_status["ACTIVE" if (r.use_yn or "") == "Y" else "INACTIVE"] += 1
        e.quantity_status[c.quantity] += 1
        e.cost_status[c.cost] += 1
    return e


async def observed_from_db(db: AsyncSession, farm_map: dict[int, UUID], *, revision: int | None = 1) -> dict[str, Any]:
    """대상 DB 집계 (SQL). revision=1 → generation-1 만, None → current 만."""
    inv = {fid: no for no, fid in farm_map.items()}
    conds = [FeedSourceRow.source_system == pf.SOURCE_SYSTEM, FeedSourceRow.source_dataset == pf.SOURCE_DATASET,
             FeedSourceRow.farm_id.in_(list(farm_map.values()))]
    conds.append(FeedSourceRow.revision == revision if revision is not None else FeedSourceRow.is_current.is_(True))
    ym = func.coalesce(func.to_char(FeedSourceRow.event_date, "YYYY-MM"), "dateless")
    q = (select(FeedSourceRow.farm_id, ym, FeedSourceRow.source_status, FeedSourceRow.quantity_status,
                FeedSourceRow.cost_status, func.count())
         .where(*conds).group_by(FeedSourceRow.farm_id, ym, FeedSourceRow.source_status,
                                 FeedSourceRow.quantity_status, FeedSourceRow.cost_status))
    o = Expected()
    for farm_id, month, ss, qs, cs, n in (await db.execute(q)).all():
        fm = mask(inv[farm_id])
        o.total += n
        o.by_farm[fm] += n
        o.by_month[month] += n
        o.by_farm_month[f"{fm}|{month}"] += n
        o.source_status[ss] += n
        o.quantity_status[qs] += n
        o.cost_status[cs] += n
    invariants = {}
    base = select(func.count()).select_from(FeedSourceRow).where(*conds[:3])
    invariants["payload_hash_null"] = int(await db.scalar(base.where(FeedSourceRow.payload_hash.is_(None))) or 0)
    invariants["currency_null"] = int(await db.scalar(base.where(FeedSourceRow.currency.is_(None))) or 0)
    invariants["currency_not_krw"] = int(await db.scalar(base.where(FeedSourceRow.currency != pf.SOURCE_CURRENCY)) or 0)
    invariants["basis_not_delivered"] = int(await db.scalar(base.where(FeedSourceRow.quantity_basis != "DELIVERED")) or 0)
    per_identity = (select(func.count().label("n")).select_from(FeedSourceRow)
                    .where(*conds[:3], FeedSourceRow.is_current.is_(True)).group_by(FeedSourceRow.source_row_key)).subquery()
    invariants["current_per_identity_max"] = int(await db.scalar(select(func.max(per_identity.c.n))) or 0)
    invariants["rows_all_revisions"] = int(await db.scalar(base) or 0)
    invariants["identities"] = int(await db.scalar(select(func.count(func.distinct(FeedSourceRow.source_row_key))).where(*conds[:3])) or 0)
    invariants["max_revision"] = int(await db.scalar(select(func.max(FeedSourceRow.revision)).where(*conds[:3])) or 0)
    runs = (await db.execute(select(FeedSourceSyncRun).where(FeedSourceSyncRun.source_system == pf.SOURCE_SYSTEM)
                             .order_by(FeedSourceSyncRun.started_at))).scalars().all()
    invariants["sync_runs"] = [{"status": r.status, "fetched": r.rows_fetched, "inserted": r.rows_inserted,
                                "unchanged": r.rows_unchanged, "superseded": r.rows_superseded, "retracted": r.rows_retracted,
                                "watermark_to": r.watermark_to.isoformat() if r.watermark_to else None,
                                "scope_hash": r.source_scope_hash, "notes": r.notes} for r in runs]
    return {"expected_shape": o, "invariants": invariants}


def diff(expected: Expected, observed: Expected) -> dict[str, Any]:
    """grain 별 차이. 0 이면 빈 dict."""
    out: dict[str, Any] = {}
    if expected.total != observed.total:
        out["total"] = {"expected": expected.total, "observed": observed.total}
    for name in ("by_farm", "by_month", "by_farm_month", "source_status", "quantity_status", "cost_status"):
        e, o = getattr(expected, name), getattr(observed, name)
        d = {k: (e.get(k, 0), o.get(k, 0)) for k in set(e) | set(o) if e.get(k, 0) != o.get(k, 0)}
        if d:
            out[name] = d
    return out
