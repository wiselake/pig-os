"""Feed source initial load — snapshot/Oracle → feed_source_rows.

모드 (기본 dry-run · 쓰기는 언제나 명시해야 한다):
  --dry-run        원천 읽기 · 변환 · 대사 미리보기. 대상 DB write 0 (연결은 farms 읽기만)
  --target-local   로컬/일회용 PG 에만 적재. 환경이 local 이 아니면 즉시 거부
  --apply          승인된 일회성 프로덕션 적재. 아래 기대를 **전부** 명시해야 하고 하나라도 실제와 다르면 거부
                     --expect-environment production
                     --expect-code-sha <적재 코드 지문>      (app/harvest/feed_load_guard.code_fingerprint)
                     --expect-migration <alembic revision>   (코드 head == 대상 DB revision)
                     --expect-source-scope-hash <scope hash>
                     --expect-source-rows <preflight 실측 N>
  --verify-only    읽기 전용 대사(프로덕션 허용). 적재 후 검증용 — SELECT 만

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
from app.harvest import feed_load_guard as guard  # noqa: E402
from app.harvest import feed_source_reconcile as rc  # noqa: E402
from app.harvest import feed_source_snapshot as snap  # noqa: E402
from app.harvest import feed_source_sync as sync  # noqa: E402
from app.harvest import pigplan_feed_delivery as pf  # noqa: E402
from app.harvest.manifest import FARM_CODES  # noqa: E402

LOCAL_HOSTS = guard.LOCAL_HOSTS
PROD_MARKERS = guard.PROD_URL_MARKERS


def target_label(url: str) -> str:
    u = urlparse(url.replace("+asyncpg", ""))
    return f"{(u.hostname or '?').lower()}/{(u.path or '').lstrip('/')}"


def assert_local_target(url: str) -> str:
    """로컬 전용 도구(드릴·projection 검증)가 쓰는 가드. 적재 스크립트 본체는 guard.check_write_allowed 를 쓴다."""
    if guard.detect_environment(url) != "local" or (urlparse(url.replace("+asyncpg", "")).hostname or "").lower() not in LOCAL_HOSTS:
        raise SystemExit(f"REFUSED: target is not a local/ephemeral PG (host={(urlparse(url.replace('+asyncpg', '')).hostname or '?')}) — production/shared write is forbidden")
    return target_label(url)


def alembic_heads() -> list[str]:
    """코드 트리의 alembic head 목록 — 프로덕션 체크아웃에 .git 이 없어도 동작한다."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    return list(ScriptDirectory.from_config(cfg).get_heads())


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
    g.add_argument("--apply", action="store_true", help="승인된 일회성 프로덕션 적재 (기대값 전부 필수)")
    g.add_argument("--verify-only", action="store_true", help="읽기 전용 대사 (프로덕션 허용)")
    ap.add_argument("--expect-environment")
    ap.add_argument("--expect-code-sha")
    ap.add_argument("--expect-migration")
    ap.add_argument("--expect-source-scope-hash")
    ap.add_argument("--expect-source-rows", type=int)
    ap.add_argument("--print-fingerprint", action="store_true", help="적재 코드 지문만 출력하고 종료")
    ap.add_argument("--snapshot", type=Path)
    ap.add_argument("--oracle", action="store_true")
    ap.add_argument("--window-start", required=True)
    ap.add_argument("--window-end", required=True)
    ap.add_argument("--today", default=None)
    ap.add_argument("--batch-size", type=int, default=2000)
    ap.add_argument("--out", type=Path, required=True, help="집계 JSON (식별자 없음)")
    ap.add_argument("--bootstrap-farms", action="store_true", help="일회용 DB 에 PP- 농장 합성 생성 (target-local 전용)")
    a = ap.parse_args()
    if a.print_fingerprint:
        print(guard.code_fingerprint())
        return 0
    mode = ("apply" if a.apply else "verify-only" if a.verify_only else "target-local" if a.target_local else "dry-run")
    today = date.fromisoformat(a.today) if a.today else date.today()
    window = Period(date.fromisoformat(a.window_start), date.fromisoformat(a.window_end))
    url = os.environ.get("DATABASE_URL", "")
    target = target_label(url)
    exp = guard.Expectations(environment=a.expect_environment, code_sha=a.expect_code_sha, migration=a.expect_migration,
                             source_scope_hash=a.expect_source_scope_hash, source_rows=a.expect_source_rows)
    try:
        gate = guard.check_write_allowed("dry-run" if mode == "verify-only" else mode, url, exp)
    except guard.RefusedError as e:
        print(f"REFUSED: {e}")
        return 4

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
        # 매핑 범위 = manifest 42 ∩ 대상 DB 의 PP- 농장. 관측된 농장 수를 코드에 박지 않는다.
        farm_map = await farm_map_from_db(db)
        authorized = len(farm_map)
        all_source_farms = set(source.farms_with_rows(FARM_CODES, window.start, window.end))
        scoped = sorted(all_source_farms & set(farm_map))
        unmapped = len(all_source_farms - set(farm_map))
        farm_map = {n: farm_map[n] for n in scoped}
        rows = source.fetch_rows(sorted(farm_map), window.start, window.end)
        if mode == "apply":
            db_rev = await db.scalar(text("SELECT version_num FROM alembic_version"))
            try:
                guard.check_migration(a.expect_migration, db_rev, alembic_heads())
                guard.check_scope(a.expect_source_scope_hash, snap.scope_hash(FARM_CODES, window.start, window.end),
                                  a.expect_source_rows, len(rows), unmapped_farms=unmapped)
            except guard.RefusedError as e:
                print(f"REFUSED: {e}")
                await eng.dispose()
                return 4
        expected = rc.expected_from_rows(rows, set(farm_map), window.start, window.end, today=today)
        report = {"mode": mode, "gate": gate, "source_mode": source_mode, "target": target,
                  "authorized_mapping_scope": authorized, "observed_farms_with_rows": len(farm_map), "unmapped_included": unmapped,
                  "window": [window.start.isoformat(), window.end.isoformat()],
                  "source_scope_hash": snap.scope_hash(FARM_CODES, window.start, window.end),
                  "farms_in_scope": len(farm_map), "source_rows_fetched": len(rows),
                  "expected": {"total": expected.total, "by_month": dict(sorted(expected.by_month.items())),
                               "source_status": dict(expected.source_status), "quantity_status": dict(expected.quantity_status),
                               "cost_status": dict(expected.cost_status), "farms": len(expected.by_farm)}}
        if mode == "verify-only":
            obs = await rc.observed_from_db(db, farm_map, revision=None)
            report["observed_current_total"] = obs["expected_shape"].total
            report["invariants"] = obs["invariants"]
            report["mismatch"] = rc.diff(expected, obs["expected_shape"])
        elif mode == "dry-run":
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
