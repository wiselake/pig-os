"""READ-ONLY production projection reconciliation (same logic as scripts/feed_source_projection_validate.py L4, minus its
ephemeral-DB guard). Persisted rows -> canonical projection -> FeedInput -> engine, compared with Oracle aggregate SQL
taken in the same snapshot session (/var/tmp/feed/s.indep.json). Prints aggregates and masked ids only."""
import asyncio
import hashlib
import json
import os
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.models.feed_source import FeedSourceRow
from app.db.models.platform import Farm
from app.engine.feed import metrics as m
from app.engine.feed.normalize import feed_type_key
from app.engine.feed.types import INSUFFICIENT, Period
from app.engine.feed.variance import decompose_cost_change
from app.harvest.manifest import FARM_CODES
from app.services.feed_engine_service import load_feed_input_from_source

TODAY = date(2026, 9, 23)


def mask(n):
    return hashlib.sha256(f"PP-{n}".encode()).hexdigest()[:12]


def months(n, today):
    end = today.replace(day=1) - timedelta(days=1)
    out = []
    for _ in range(n):
        s = end.replace(day=1)
        out.append(Period(s, end))
        end = s - timedelta(days=1)
    return list(reversed(out))


def close(a, b, tol):
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= tol


async def main():
    indep = json.load(open("/var/tmp/feed/s.indep.json", encoding="utf-8"))
    eng = create_async_engine(os.environ["DATABASE_URL"])
    rep = {"farm_months_completed": 0, "partial_month_rows": 0, "projected_rows": 0, "lineage_checked": 0, "lineage_failures": 0,
           "basis_currency_violations": 0, "compared": 0, "quantity": 0, "cost": 0, "unit_price": 0, "mix": 0,
           "change_values": 0, "change_reasons": {}, "variance_eligible": 0, "variance_identity_pass": 0,
           "partial_used_in_completed_comparison": 0, "details": []}
    async with AsyncSession(eng, expire_on_commit=False) as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        fm = {int(c.split("-", 1)[1]): fid for c, fid in (await db.execute(
            select(Farm.farm_code, Farm.id).where(Farm.farm_code.in_([f"PP-{n}" for n in FARM_CODES])))).all()}
        have = {fid for (fid,) in (await db.execute(select(FeedSourceRow.farm_id).distinct())).all()}
        fm = {n: fid for n, fid in fm.items() if fid in have}
        rep["farms_with_rows"] = len(fm)
        periods = months(12, TODAY)
        partial = Period(TODAY.replace(day=1), TODAY)
        for n, fid in sorted(fm.items()):
            prev = None
            for p in periods + [partial]:
                is_partial = p is partial
                inp, lin = await load_feed_input_from_source(db, fid, p.start, p.end, quantity_basis="DELIVERED", source_system="pigplan")
                res = m.compute_all(inp, None if is_partial else prev)   # 부분월은 비교 입력도, 비교 대상도 되지 않는다
                rep["projected_rows"] += len(inp.rows)
                for r in res.values():
                    if r.quantity_basis != "DELIVERED":
                        rep["basis_currency_violations"] += 1
                if inp.rows and {x.currency for x in inp.rows} != {"KRW"}:
                    rep["basis_currency_violations"] += 1
                ids = [UUID(x) for x in lin["source_row_ids"]]
                if len(ids) != len(inp.rows):
                    rep["lineage_failures"] += 1
                if ids:
                    got = {r.id: r for r in (await db.execute(select(FeedSourceRow).where(FeedSourceRow.id.in_(ids)))).scalars()}
                    for i, rid in enumerate(ids):
                        rep["lineage_checked"] += 1
                        r = got.get(rid)
                        if (r is None or not r.is_current or r.source_status != "ACTIVE" or r.source_system != "pigplan"
                                or not r.payload_hash or r.source_contract_version != "pigplan_feed_delivery.v1"
                                or Decimal(str(r.quantity_kg)) != inp.rows[i].quantity_kg or r.event_date != inp.rows[i].record_date):
                            rep["lineage_failures"] += 1
                if is_partial:
                    rep["partial_month_rows"] += len(inp.rows)
                    continue
                rep["farm_months_completed"] += 1
                ym = f"{p.start:%Y-%m}"
                q, c, up, mix = res[m.FEED_QTY], res[m.FEED_COST], res[m.FEED_UNIT_PRICE], res[m.FEED_MIX_SHARE]
                ind = indep.get(f"{n}|{ym}")
                if ind is not None or q.provenance != INSUFFICIENT:
                    rep["compared"] += 1
                    d = {}
                    if not close(q.value, Decimal(ind["kg"]) if ind else None, 0.15):
                        d["quantity"] = 1
                    sc = Decimal(ind["cost"]) if ind and ind.get("cost") not in (None, "None") else None
                    ec = c.value if c.provenance != INSUFFICIENT else c.evidence.get("partial_cost")
                    if not (ec is None and (sc is None or sc == 0)) and not close(ec, sc, 1.0):
                        d["cost"] = 1
                    sp = Decimal(ind["priced_kg"]) if ind and ind.get("priced_kg") not in (None, "None") else None
                    if not close(up.value, (sc / sp) if sc is not None and sp else None, 0.0006):
                        d["unit_price"] = 1
                    em = mix.evidence.get("kg_by_feed_type") if mix.provenance != INSUFFICIENT else None
                    sm = {feed_type_key(k): Decimal(v) for k, v in ind["stages"].items()} if ind and ind.get("stages") else None
                    if not ((em is None and not sm) or (em is not None and sm is not None and set(em) == set(sm)
                                                        and all(close(em[k], sm[k], 0.15) for k in em))):
                        d["mix"] = 1
                    for k in d:
                        rep[k] += 1
                    if d:
                        rep["details"].append({"farm": mask(n), "month": ym, "diff": sorted(d)})
                if prev is not None:
                    qc = res[m.FEED_QTY_CHANGE]
                    if qc.evidence.get("cur", {}).get("start", "").startswith(f"{partial.start:%Y-%m}"):
                        rep["partial_used_in_completed_comparison"] += 1
                    rep["change_reasons"][qc.reason or "value"] = rep["change_reasons"].get(qc.reason or "value", 0) + 1
                    v = decompose_cost_change(prev, inp)
                    if v.provenance != INSUFFICIENT:
                        rep["variance_eligible"] += 1
                        if abs((v.price + v.volume + v.mix) - v.total) <= 0.02:
                            rep["variance_identity_pass"] += 1
                prev = inp
        await db.rollback()
    await eng.dispose()
    rep["change_values"] = rep["change_reasons"].get("value", 0)
    print(json.dumps(rep, ensure_ascii=False))


asyncio.run(main())
