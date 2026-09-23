"""L3 — revision/correction/inactive/retraction drill at real scale (LOCAL PG ONLY, snapshot copy mutated in memory).

Oracle 은 절대 건드리지 않는다. snapshot 을 읽어 **메모리에서** 시나리오별로 변형한 뒤 sync 를 돌리고,
기대값(변형 전에 독립 계산)과 원장/DB 를 대조한다.

  A  수량 정정        total_kg × 1.1              → 새 revision · 이전 superseded
  B  단가 정정        fper_price + 1 (total 재계산) → 새 revision
  C  USE_YN Y→N                                  → INACTIVE revision
  D  N→Y (되살림)     — C 로 만든 INACTIVE 를 원본으로 되돌림 → revive (새 행 없음, 원본 revision 이 다시 current)
  E  행 소실          snapshot 에서 제거          → RETRACTED revision (그 농장에 다른 행이 남아 있을 때만)
  F  같은 identity 다른 payload — A 와 같은 경로(정정 = payload 변경) 로 분류 · 별도 확인: 물리 삭제 0 · 이력 보존
  G  빈 소스 결과      fetch 가 0행               → 철회 0 (가드) · SUCCEEDED · empty_source=true
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from app.db.models.feed_source import FeedSourceRow  # noqa: E402
from app.engine.feed.types import Period  # noqa: E402
from app.harvest import feed_source_snapshot as snap  # noqa: E402
from app.harvest import feed_source_sync as sync  # noqa: E402
from scripts.feed_source_initial_load import assert_local_target, farm_map_from_db  # noqa: E402


async def counts(db: AsyncSession) -> dict:
    total = await db.scalar(select(func.count()).select_from(FeedSourceRow))
    cur = await db.scalar(select(func.count()).select_from(FeedSourceRow).where(FeedSourceRow.is_current.is_(True)))
    by_status = dict((await db.execute(select(FeedSourceRow.source_status, func.count()).where(FeedSourceRow.is_current.is_(True))
                                       .group_by(FeedSourceRow.source_status))).all())
    maxrev = await db.scalar(select(func.max(FeedSourceRow.revision)))
    ids = await db.scalar(select(func.count(func.distinct(FeedSourceRow.source_row_key))))
    return {"rows_all_revisions": int(total or 0), "current": int(cur or 0), "current_by_status": by_status,
            "max_revision": int(maxrev or 0), "identities": int(ids or 0)}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--window-start", required=True)
    ap.add_argument("--window-end", required=True)
    ap.add_argument("--today", required=True)
    ap.add_argument("--fraction", type=float, default=0.01)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    url = os.environ.get("DATABASE_URL", "")
    target = assert_local_target(url)
    if "pigos_feedload" not in target:
        raise SystemExit("REFUSED: drill only on an ephemeral pigos_feedload* DB")
    today = date.fromisoformat(a.today)
    window = Period(date.fromisoformat(a.window_start), date.fromisoformat(a.window_end))
    rows, meta = snap.load(a.snapshot)
    rng = random.Random(20260922)
    eng = create_async_engine(url)
    report = {"snapshot_content_hash": meta["content_hash"], "scenarios": {}}

    async with AsyncSession(eng, expire_on_commit=False) as db:
        farm_map = await farm_map_from_db(db)
        base = snap.SnapshotSource(rows, meta)
        scoped = base.farms_with_rows(sorted(farm_map), window.start, window.end)
        farm_map = {n: farm_map[n] for n in scoped}
        active = [r for r in rows if (r.use_yn or "") == "Y" and r.total_kg and r.total_kg > 0 and r.source_farm_no in farm_map]
        k = max(1, int(len(active) * a.fraction))
        pickA, pickB, pickC, pickE = (rng.sample(active, k) for _ in range(4))
        keyA, keyB, keyC, keyE = ({(r.source_farm_no, r.seq) for r in p} for p in (pickA, pickB, pickC, pickE))
        before = await counts(db)
        report["before"] = before
        later = datetime(2026, 9, 23)          # Oracle DATE 처럼 naive

        def mutate(r):
            key = (r.source_farm_no, r.seq)
            if key in keyE:
                return None
            if key in keyA:
                kg = (r.total_kg * Decimal("1.1")).quantize(Decimal("0.001"))
                return replace(r, total_kg=kg, total_price=(r.fper_price * kg).quantize(Decimal("1")) if r.fper_price else r.total_price, source_updated_at=later)
            if key in keyB:
                p = (r.fper_price or Decimal(0)) + 1
                return replace(r, fper_price=p, total_price=(p * r.total_kg).quantize(Decimal("1")), source_updated_at=later)
            if key in keyC:
                return replace(r, use_yn="N", source_updated_at=later)
            return r
        overlap = len(keyA & keyB) + len(keyA & keyC) + len(keyB & keyC) + len((keyA | keyB | keyC) & keyE)
        mutated = [m for m in (mutate(r) for r in rows) if m is not None]
        # 기대값(독립): 정정 A∪B∪C(겹침 제외) → superseded+inserted, E → retracted (E 가 농장 전체를 비우지 않는 한)
        changed = (keyA | keyB | keyC) - keyE
        expected = {"superseded": len(changed), "inserted": len(changed), "retracted": len(keyE), "overlap_keys": overlap}
        out = await sync.run_pigplan_feed_sync(db, snap.SnapshotSource(mutated, meta), farm_map, today=today, lookback_days=window.days,
                                               observed_at=later, window=window)
        after = await counts(db)
        report["scenarios"]["ABCE_correction_inactive_missing"] = {
            "expected": expected,
            "sync": {"status": out.status, "inserted": out.inserted, "unchanged": out.unchanged, "superseded": out.superseded, "retracted": out.retracted},
            "after": after,
            "checks": {
                # 원장 의미: rows_inserted = 소스 내용에서 온 새 revision · rows_retracted = tombstone revision(각각 이전 revision 을 supersede)
                "inserted_matches": out.inserted == expected["inserted"],
                "superseded_matches": out.superseded == expected["superseded"],
                "retracted_matches": out.retracted == expected["retracted"],
                "history_retained": after["rows_all_revisions"] == before["rows_all_revisions"] + out.inserted + out.retracted,
                "identities_unchanged": after["identities"] == before["identities"],
                "physical_deletes": before["rows_all_revisions"] - (after["rows_all_revisions"] - out.inserted - out.retracted),
                "current_inactive_delta": after["current_by_status"].get("INACTIVE", 0) - before["current_by_status"].get("INACTIVE", 0),
                "current_retracted": after["current_by_status"].get("RETRACTED", 0),
            },
        }
        # D — 되살림: 원본 snapshot 을 다시 넣는다 → C 의 INACTIVE 가 원본 revision 으로 revive · A/B 는 원본 payload 로 되돌아감(revive) · E 복귀(revive)
        out2 = await sync.run_pigplan_feed_sync(db, base, farm_map, today=today, lookback_days=window.days,
                                                observed_at=datetime(2026, 9, 24, tzinfo=UTC), window=window)
        after2 = await counts(db)
        report["scenarios"]["D_revive_original"] = {
            "sync": {"status": out2.status, "inserted": out2.inserted, "unchanged": out2.unchanged, "superseded": out2.superseded, "retracted": out2.retracted},
            "after": after2,
            "checks": {
                "no_new_rows_on_revive": after2["rows_all_revisions"] == after["rows_all_revisions"],   # 원본 revision 이 살아남 — 새 행 0
                "current_back_to_before": after2["current"] == before["current"] and after2["current_by_status"] == before["current_by_status"],
                "revived_count": out2.inserted, "expected_revived": expected["inserted"] + expected["retracted"],
            },
        }
        # G — 빈 소스 결과: 철회 0
        out3 = await sync.run_pigplan_feed_sync(db, snap.SnapshotSource([], meta), farm_map, today=today, lookback_days=window.days,
                                                observed_at=datetime(2026, 9, 25, tzinfo=UTC), window=window)
        after3 = await counts(db)
        report["scenarios"]["G_empty_source_result"] = {
            "sync": {"status": out3.status, "retracted": out3.retracted, "inserted": out3.inserted},
            "checks": {"nothing_retracted": out3.retracted == 0 and after3 == after2, "status_succeeded_not_unavailable": out3.status == "SUCCEEDED"},
        }
        # 정리: 원본 상태로 되돌린 상태(after2)가 최종 — 후속 L4 는 current 행이 원본과 같다는 전제
        report["final"] = after3
        report["final_equals_before_current"] = after3["current"] == before["current"]
    await eng.dispose()
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1, default=str))
    allchecks = [v for s_ in report["scenarios"].values() for kk, v in s_["checks"].items() if isinstance(v, bool)]
    return 0 if all(allchecks) and report["scenarios"]["ABCE_correction_inactive_missing"]["checks"]["physical_deletes"] == 0 else 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
