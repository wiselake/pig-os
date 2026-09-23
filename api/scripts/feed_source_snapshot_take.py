"""L0-B — Oracle 을 **한 번** 읽어 repo 밖 snapshot 으로 고정한다 (SELECT 만 · READ ONLY 세션).

    ORACLE_PW=... python scripts/feed_source_snapshot_take.py --out <repo 밖 경로>/feed_snapshot.json \
        --window-start 2025-09-01 --window-end 2026-09-22 --meta-out ../docs/feed/runs/snapshot_meta.json

--out 은 repo 밖이어야 한다(실제 원장 행). --meta-out 은 식별자 없는 메타만 담아 repo 에 둘 수 있다.
독립 대조용 Oracle 집계(farm×month)도 같은 세션에서 한 번에 가져와 snapshot 옆에 저장한다 (L4 용, 재조회 0).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.harvest import feed_source_snapshot as snap  # noqa: E402
from app.harvest import pigplan_feed_delivery as pf  # noqa: E402
from app.harvest.manifest import FARM_CODES  # noqa: E402

DSN_DEFAULT = "pigclouddb.c8ks4denaq5l.ap-northeast-2.rds.amazonaws.com:1521/PIGPLAN"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--meta-out", type=Path, required=True)
    ap.add_argument("--window-start", required=True)
    ap.add_argument("--window-end", required=True)
    ap.add_argument("--today", default=None)
    a = ap.parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    if repo_root in a.out.resolve().parents:
        raise SystemExit("REFUSED: snapshot must live outside the repository (contains raw source rows)")
    pw = os.environ.get("ORACLE_PW")
    if not pw:
        print("SKIP_SOURCE_UNAVAILABLE: ORACLE_PW env 없음")
        return 78
    start, end = date.fromisoformat(a.window_start), date.fromisoformat(a.window_end)
    today = date.fromisoformat(a.today) if a.today else date.today()
    src = pf.PigPlanFeedDeliverySource(os.environ.get("ORACLE_DSN", DSN_DEFAULT), os.environ.get("ORACLE_USER", "pksu"), pw)
    try:
        t0 = time.perf_counter()
        farms = src.farms_with_rows(FARM_CODES, start, end)
        rows = src.fetch_rows(farms, start, end)
        indep = src.independent_month_aggregates(farms, start, end, today=today)
        elapsed = time.perf_counter() - t0
    finally:
        src.close()
    meta = snap.summarize(rows, FARM_CODES, start, end, extracted_at=datetime.now(UTC), oracle_elapsed_s=round(elapsed, 2))
    meta["authorized_mapping_scope"] = len(FARM_CODES)
    meta["observed_farms_with_rows"] = len(farms)
    meta["independent_aggregates_farm_months"] = len(indep)
    snap.save(a.out, rows, meta)
    # 독립 집계는 마스킹 없이 snapshot 옆(repo 밖)에 — L4 가 읽는다
    side = a.out.with_suffix(".indep.json")
    side.write_text(json.dumps({f"{k[0]}|{k[1]}": {kk: (str(vv) if vv is not None and not isinstance(vv, (int, dict)) else vv)
                                                     for kk, vv in v.items()} for k, v in indep.items()},
                               ensure_ascii=False, default=str), encoding="utf-8")
    a.meta_out.parent.mkdir(parents=True, exist_ok=True)
    a.meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
