"""Feed source initial load — snapshot/Oracle → feed_source_rows (LOCAL / EPHEMERAL PG ONLY).

모드 (둘 중 하나, 기본 dry-run):
  --dry-run        원천 읽기 · 변환 · 대사 미리보기. 대상 DB write 0 (연결은 farms 읽기만)
  --target-local   로컬/일회용 PG 에 실제 적재. DATABASE_URL 호스트가 localhost/127.0.0.1/pigos-postgres 가 아니거나
                   프로덕션 표식(rds.amazonaws.com · 52.78.65.6 · api.pigos.io · supabase)이 보이면 즉시 거부 (fail-closed)

원천 (둘 중 하나):
  --snapshot PATH  L0-B 로 고정한 repo 밖 snapshot 파일
  --oracle         ORACLE_PW env 로 직접 (SELECT 만). 기본은 snapshot — Oracle 을 반복 조회하지 않는다

범위: app.harvest.manifest.FARM_CODES(직접 매핑 42) ∩ 대상 DB 의 farms.farm_code='PP-{no}'  ×  --window-start/--window-end
"전량" = 승인 농장 × 승인 필터 × 승인 창. 675k 전체가 아니다.

출력: 집계·마스킹 id·해시만. 원자료·식별자 없음.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import tracemalloc
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from app.db.models.platform import Farm  # noqa: E402
from app.engine.feed.types import Period  # noqa: E402
from app.harvest import feed_source_reconcile as rc  # noqa: E402
from app.harvest import feed_source_snapshot as snap  # noqa: E402
from app.harvest import feed_source_sync as sync  # noqa: E402
from app.harvest import pigplan_feed_delivery as pf  # noqa: E402
from app.harvest.manifest import FARM_CODES  # noqa: E402

LOCAL_HOSTS = {"localhost", "127.0.0.1", "pigos-postgres", "::1"}
PROD_MARKERS = ("rds.amazonaws.com", "52.78.65.6", "api.pigos.io", "supabase", "pigos-prod")


def assert_local_target(url: str) -> str:
    u = urlparse(url.replace("+asyncpg", ""))
    host = (u.hostname or "").lower()
    if host not in LOCAL_HOSTS or any(m in url for m in PROD_MARKERS):
        raise SystemExit(f"REFUSED: target is not a local/ephemeral PG (host={host or '?'}) — production/shared write is forbidden")
    return f"{host}/{(u.path or '').lstrip('/')}"


async def bootstrap_farms(db: AsyncSession) -> int:
    """일회용 DB 전용: 직접 매핑 42 농장을 합성 신원(PP-{no}, 이름 없음)으로 만든다. 프로덕션 farms 는 하베스트가 만든다."""
    from app.db.models.platform import Organization
    have = {c for (c,) in (await db.execute(select(Farm.farm_code).where(Farm.farm_code.like("PP-%")))).all()}
    missing = [n for n in FARM_CODES if f"PP-{n}" not in have]
    if not missing:
        return 0
    org = Organization(name="ephemeral-harvest-org", country="KR", timezone="Asia/Seoul")
    db.add(org)
    await db.flush()
    for n in missing:
        db.add(Farm(org_id=org.id, farm_code=f"PP-{n}", name=f"PP-{n}", country="KR", timezone="Asia/Seoul",
                    currency="USD",                      # 일부러 소스 통화와 다르게 — farm fallback 이 새면 대사에서 잡힌다
                    data_origin="pigplan_migration", data_classification="internal_reference"))
    await db.commit()
    return len(missing)


async def farm_map_from_db(db: AsyncSession) -> dict[int, object]:
    rows = (await db.execute(select(Farm.farm_code, Farm.id).where(Farm.farm_code.in_([f"PP-{n}" for n in FARM_CODES])))).all()
    return {int(code.split("-", 1)[1]): fid for code, fid in rows}


async def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--target-local", action="store_true")
    ap.add_argument("--snapshot", type=Path)
    ap.add_argument("--oracle", action="store_true")
    ap.add_argument("--window-start", required=True)
    ap.add_argument("--window-end", required=True)
    ap.add_argument("--today", default=None)
    ap.add_argument("--batch-size", type=int, default=2000)
    ap.add_argument("--out", type=Path, required=True, help="집계 JSON (식별자 없음)")
    ap.add_argument("--bootstrap-farms", action="store_true", help="일회용 DB 에 PP- 농장 합성 생성 (target-local 전용)")
    a = ap.parse_args()
    mode = "target-local" if a.target_local else "dry-run"
    today = date.fromisoformat(a.today) if a.today else date.today()
    window = Period(date.fromisoformat(a.window_start), date.fromisoformat(a.window_end))
    url = os.environ.get("DATABASE_URL", "")
    target = assert_local_target(url)                      # dry-run 도 로컬 외 DB 에는 연결하지 않는다

    if a.oracle:
        pw = os.environ.get("ORACLE_PW")
        if not pw:
            print("SKIP_SOURCE_UNAVAILABLE: ORACLE_PW env 없음")
            return 78
        source = pf.PigPlanFeedDeliverySource(os.environ.get("ORACLE_DSN", "pigclouddb.c8ks4denaq5l.ap-northeast-2.rds.amazonaws.com:1521/PIGPLAN"),
                                              os.environ.get("ORACLE_USER", "pksu"), pw)
        source_mode = "ORACLE_READONLY"
    elif a.snapshot:
        source = snap.SnapshotSource.from_file(a.snapshot)
        source_mode = "SNAPSHOT"
    else:
        raise SystemExit("--snapshot PATH 또는 --oracle 중 하나")

    eng = create_async_engine(url)
    tracemalloc.start()
    t0 = time.perf_counter()
    async with AsyncSession(eng, expire_on_commit=False) as db:
        if a.bootstrap_farms:
            if mode != "target-local" or not target.endswith(("pigos_feedload", "pigos_feedload_rt")):
                raise SystemExit("REFUSED: --bootstrap-farms only on an ephemeral pigos_feedload* target")
            print("bootstrapped farms:", await bootstrap_farms(db))
        farm_map = await farm_map_from_db(db)
        scoped = source.farms_with_rows(sorted(farm_map), window.start, window.end)
        farm_map = {n: farm_map[n] for n in scoped}
        rows = source.fetch_rows(sorted(farm_map), window.start, window.end)
        expected = rc.expected_from_rows(rows, set(farm_map), window.start, window.end, today=today)
        report = {"mode": mode, "source_mode": source_mode, "target": target,
                  "window": [window.start.isoformat(), window.end.isoformat()],
                  "source_scope_hash": snap.scope_hash(sorted(farm_map), window.start, window.end),
                  "farms_in_scope": len(farm_map), "source_rows_fetched": len(rows),
                  "expected": {"total": expected.total, "by_month": dict(sorted(expected.by_month.items())),
                               "source_status": dict(expected.source_status), "quantity_status": dict(expected.quantity_status),
                               "cost_status": dict(expected.cost_status), "farms": len(expected.by_farm)}}
        if mode == "dry-run":
            size_before = None
        else:
            size_before = int(await db.scalar(text("SELECT pg_database_size(current_database())")))
            outcome = await sync.run_pigplan_feed_sync(db, source, farm_map, today=today, lookback_days=window.days,
                                                        observed_at=datetime.now(UTC), window=window, batch_size=a.batch_size)
            report["sync"] = {"status": outcome.status, "fetched": outcome.fetched, "inserted": outcome.inserted,
                              "unchanged": outcome.unchanged, "superseded": outcome.superseded, "retracted": outcome.retracted,
                              "error": outcome.error}
            obs = await rc.observed_from_db(db, farm_map, revision=1)
            report["observed_generation1_total"] = obs["expected_shape"].total
            report["invariants"] = obs["invariants"]
            report["mismatch"] = rc.diff(expected, obs["expected_shape"])
            size_after = int(await db.scalar(text("SELECT pg_database_size(current_database())")))
            report["db_size_delta_bytes"] = size_after - size_before
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    report["performance"] = {"elapsed_s": round(elapsed, 2), "rows_per_s": round(len(rows) / elapsed, 1) if elapsed else None,
                             "peak_py_mem_mb": round(peak / 1e6, 1), "batch_size": a.batch_size}
    await eng.dispose()
    if hasattr(source, "close"):
        source.close()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "expected"}, ensure_ascii=False, indent=1, default=str))
    return 0 if not report.get("mismatch") else 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
