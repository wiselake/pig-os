"""F4 — Feed Engine V1 을 실제(복원) 데이터에 돌려 결과를 독립 SQL 과 대조한다. READ-ONLY.

사용:  DATABASE_URL=postgresql+asyncpg://pigos:pigos@localhost:5499/pigos_f4 \
       uv run python scripts/feed_engine_real_data_audit.py --months 12 --out /path/report.json

프로덕션에 직접 붙이지 않는다 — 복원본/replica URL 만. 개인정보 컬럼을 읽지 않는다: farms 는 id·currency 만,
farm 식별은 sha256(id)[:8] 로 마스킹해 출력한다. 값·상태 분포만 집계한다.
독립 대조: 엔진(compute_all)이 낸 FEED_QTY/FEED_COST 를 엔진 코드가 아닌 SQL 로 다시 계산해 비교한다.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from collections import Counter
from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.engine.feed.status import deterministic_findings
from app.engine.feed.types import INSUFFICIENT
from app.services import feed_engine_service as svc

_PROD_MARKERS = ("52.78.65.6", "api.pigos.io", "rds.amazonaws.com", "pigos-prod")


class _Farm:
    def __init__(self, id, currency):
        self.id, self.currency = id, currency


def _month_windows(months: int, today: date) -> list[tuple[date, date]]:
    out = []
    y, mo = today.year, today.month
    for _ in range(months):
        start = date(y, mo, 1)
        nxt = date(y + (mo == 12), 1 if mo == 12 else mo + 1, 1)
        out.append((start, date.fromordinal(nxt.toordinal() - 1)))
        y, mo = (y - 1, 12) if mo == 1 else (y, mo - 1)
    return list(reversed(out))


async def _independent_sql(db: AsyncSession, farm_id, start: date, end: date) -> dict:
    r = (await db.execute(text(
        "SELECT count(*) rows, coalesce(sum(quantity_kg),0) qty, "
        "count(*) FILTER (WHERE unit_cost IS NULL) uncosted, "
        "sum(quantity_kg*unit_cost) FILTER (WHERE unit_cost IS NOT NULL) cost "
        "FROM feed_records WHERE farm_id=:f AND deleted_at IS NULL AND record_date BETWEEN :s AND :e"),
        {"f": farm_id, "s": start, "e": end})).one()
    return {"rows": int(r.rows), "qty": Decimal(str(r.qty)), "uncosted": int(r.uncosted),
            "cost": Decimal(str(r.cost)) if r.cost is not None else None}


async def main(months: int, out: str) -> None:
    url = os.environ["DATABASE_URL"]
    if any(x in url for x in _PROD_MARKERS):
        raise SystemExit("REFUSED: production URL — use a restored dump or replica")
    engine = create_async_engine(url, pool_pre_ping=True)
    today = date.today()
    windows = _month_windows(months, today)
    status_counter: Counter = Counter()
    mismatches: list[dict] = []
    per_farm: dict[str, dict] = {}
    findings_counter: Counter = Counter()
    async with AsyncSession(engine) as db:
        farms = (await db.execute(text("SELECT id, currency FROM farms WHERE active"))).all()
        for fid, ccy in farms:
            fh = hashlib.sha256(str(fid).encode()).hexdigest()[:8]
            per_farm[fh] = {"months_with_data": 0, "fcr_values": 0}
            for start, end in windows:
                farm = _Farm(fid, ccy)
                res = await svc.compute_feed_metrics(db, farm, start, end)
                ind = await _independent_sql(db, fid, start, end)
                for k, r in res.items():
                    status_counter[(k, r.provenance, r.reason)] += 1
                for f in deterministic_findings(res):
                    findings_counter[f.rule_id] += 1
                # 독립 대조: 엔진 FEED_QTY vs SQL
                q = res["FEED_QTY"]
                if ind["rows"] == 0:
                    if q.provenance != INSUFFICIENT or q.reason != "no_data":
                        mismatches.append({"farm": fh, "month": start.isoformat(), "metric": "FEED_QTY",
                                           "engine": (q.provenance, q.reason, q.value), "sql_rows": 0})
                else:
                    per_farm[fh]["months_with_data"] += 1
                    if q.value is None or abs(Decimal(str(q.value)) - ind["qty"].quantize(Decimal("0.1"))) > Decimal("0.05"):
                        mismatches.append({"farm": fh, "month": start.isoformat(), "metric": "FEED_QTY",
                                           "engine": q.value, "sql": str(ind["qty"])})
                    c = res["FEED_COST"]
                    if ind["uncosted"] == 0 and ind["cost"] is not None:
                        if c.value is None or abs(Decimal(str(c.value)) - ind["cost"].quantize(Decimal("0.01"))) > Decimal("0.005"):
                            mismatches.append({"farm": fh, "month": start.isoformat(), "metric": "FEED_COST",
                                               "engine": c.value, "sql": str(ind["cost"])})
                    elif c.provenance != INSUFFICIENT:
                        mismatches.append({"farm": fh, "month": start.isoformat(), "metric": "FEED_COST",
                                           "engine": ("value with uncosted rows", c.value), "sql_uncosted": ind["uncosted"]})
                if res.get("FCR") is not None and res["FCR"].provenance != INSUFFICIENT:
                    per_farm[fh]["fcr_values"] += 1
    await engine.dispose()
    report = {
        "months": months, "window": [windows[0][0].isoformat(), windows[-1][1].isoformat()],
        "farms_active": len(farms), "farm_months": len(farms) * months,
        "status_distribution": [{"metric": k[0], "provenance": k[1], "reason": k[2], "n": n}
                                for k, n in sorted(status_counter.items(), key=lambda kv: (kv[0][0], -kv[1]))],
        "findings": dict(findings_counter),
        "farms_with_any_feed_month": sum(1 for v in per_farm.values() if v["months_with_data"]),
        "farms_with_any_fcr_value": sum(1 for v in per_farm.values() if v["fcr_values"]),
        "independent_sql_mismatches": mismatches,
    }
    with open(out, "w", encoding="utf-8") as fh_:
        json.dump(report, fh_, ensure_ascii=False, indent=2, default=str)
    print(json.dumps({k: v for k, v in report.items() if k != "status_distribution"}, ensure_ascii=False, default=str))
    print("status_distribution:")
    for row in report["status_distribution"]:
        print(f"  {row['metric']:22s} {row['provenance']:12s} {str(row['reason']):22s} {row['n']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--out", default="feed_engine_real_data_audit.json")
    a = ap.parse_args()
    asyncio.run(main(a.months, a.out))
