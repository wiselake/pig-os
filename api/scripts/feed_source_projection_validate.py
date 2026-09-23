"""L4 — persisted rows → canonical projection → FeedInput → Feed Engine, 전량 검증 (LOCAL PG ONLY).

대조 대상은 두 가지 **독립** 경로:
  ① Oracle 집계 SQL 결과(snapshot 옆 .indep.json — L0-B 에서 함께 가져옴, 엔진 미경유)
  ② 이전 shadow 실행(SHADOW_ORACLE_FEED_20260922.json, Oracle 직접 → 엔진) 의 farm×month 값
lineage: 모든 FeedInput 행 → source_row_id → DB 행 → (system, dataset, row_key, revision, hash, contract) 역추적 가능해야 한다.

--production-read-only (2026-09-23 리뷰 ①③): 일회용 DB 가드 대신 `SET TRANSACTION READ ONLY` 를 걸고 확인한 뒤
같은 비교를 프로덕션에서 돌린다. 끝에 rollback. 이 모드의 --indep 는 마스킹 키(snapshot_take --indep-only)만 받는다.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from app.db.models.feed_source import FeedSourceRow  # noqa: E402
from app.engine.feed import metrics as m  # noqa: E402
from app.engine.feed.normalize import feed_type_key  # noqa: E402
from app.engine.feed.types import INSUFFICIENT, Period  # noqa: E402
from app.engine.feed.variance import decompose_cost_change  # noqa: E402
from app.harvest.feed_source_reconcile import indep_get, mask  # noqa: E402
from app.services.feed_engine_service import load_feed_input_from_source  # noqa: E402
from scripts.feed_source_initial_load import assert_local_target, farm_map_from_db  # noqa: E402

MASKED_KEY = re.compile(r"[0-9a-f]{12}")   # mask() 형식 — 원천 농장번호(정수)는 여기에 맞지 않는다


def months(n: int, today: date) -> list[Period]:
    end = today.replace(day=1) - timedelta(days=1)
    out = []
    for _ in range(n):
        start = end.replace(day=1)
        out.append(Period(start, end))
        end = start - timedelta(days=1)
    return list(reversed(out))


def close(a, b, tol):
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= tol


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--indep", type=Path, required=True, help="snapshot 옆 .indep.json (Oracle 독립 집계)")
    ap.add_argument("--shadow", type=Path, required=True)
    ap.add_argument("--today", required=True)
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--production-read-only", action="store_true",
                    help="일회용 DB 가드 대신 READ ONLY 트랜잭션(확인 후 진행, 끝에 rollback). --indep 는 마스킹 키만")
    a = ap.parse_args()
    url = os.environ.get("DATABASE_URL", "")
    if not a.production_read_only:
        target = assert_local_target(url)
        if "pigos_feedload" not in target:
            raise SystemExit("REFUSED: validate only on an ephemeral pigos_feedload* DB")
    today = date.fromisoformat(a.today)
    indep = json.loads(a.indep.read_text(encoding="utf-8"))
    if a.production_read_only and any(not MASKED_KEY.fullmatch(k.split("|", 1)[0]) for k in indep):
        raise SystemExit("REFUSED: --production-read-only takes masked indep keys only (snapshot_take --indep-only)")
    shadow = json.loads(a.shadow.read_text(encoding="utf-8"))
    periods = months(a.months, today)
    partial = Period(today.replace(day=1), today)
    eng = create_async_engine(url)
    rep = {"mode": "production_read_only" if a.production_read_only else "ephemeral", "farm_months": 0, "projected_rows": 0, "lineage": {"checked": 0, "failures": 0},
           "recon_vs_oracle_sql": {"compared": 0, "quantity": 0, "cost": 0, "unit_price": 0, "mix": 0, "details": []},
           "recon_vs_shadow": {"compared": 0, "quantity": 0, "cost": 0, "unit_price": 0, "change": 0, "variance": 0, "details": []},
           "change": {"value": 0, "reasons": {}}, "variance": {"eligible": 0, "identity_pass": 0}, "basis_currency_provenance_ok": True,
           "classification": {"UNEXPLAINED": 0, "EXPECTED_DIFFERENCE": 0}}
    async with AsyncSession(eng, expire_on_commit=False) as db:
        if a.production_read_only:
            await db.execute(text("SET TRANSACTION READ ONLY"))
            if (await db.execute(text("SHOW transaction_read_only"))).scalar() != "on":
                raise SystemExit("REFUSED: transaction is not read-only")
            rep["db_alembic"] = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar()
        farm_map = await farm_map_from_db(db)
        for farm_no, fid in sorted(farm_map.items()):
            prev = None
            for p in periods + [partial]:
                inp, lineage = await load_feed_input_from_source(db, fid, p.start, p.end, quantity_basis="DELIVERED", source_system="pigplan")
                ym = f"{p.start:%Y-%m}"
                res = m.compute_all(inp, prev if p is not partial else None)
                if not inp.rows and p is partial:
                    continue
                rep["farm_months"] += 1
                rep["projected_rows"] += len(inp.rows)
                # ── 계약: basis · currency · provenance
                for r in res.values():
                    if r.quantity_basis != "DELIVERED" or r.provenance not in ("ACTUAL", "DERIVED", "INSUFFICIENT"):
                        rep["basis_currency_provenance_ok"] = False
                if inp.rows and (inp.farm_currency != "KRW" or {x.currency for x in inp.rows} != {"KRW"}):
                    rep["basis_currency_provenance_ok"] = False
                # ── lineage 역추적
                ids = [UUID(x) for x in lineage["source_row_ids"]]
                if len(ids) != len(inp.rows):
                    rep["lineage"]["failures"] += 1
                if ids:
                    rows = (await db.execute(select(FeedSourceRow).where(FeedSourceRow.id.in_(ids)))).scalars().all()
                    by_id = {r.id: r for r in rows}
                    for i, rid in enumerate(ids):
                        rep["lineage"]["checked"] += 1
                        r = by_id.get(rid)
                        if (r is None or not r.is_current or r.source_status != "ACTIVE" or r.source_system != "pigplan"
                                or not r.source_row_key or not r.payload_hash or r.source_contract_version != "pigplan_feed_delivery.v1"
                                or Decimal(str(r.quantity_kg)) != inp.rows[i].quantity_kg or r.event_date != inp.rows[i].record_date):
                            rep["lineage"]["failures"] += 1
                if p is partial:
                    continue
                q, c, up, mix = res[m.FEED_QTY], res[m.FEED_COST], res[m.FEED_UNIT_PRICE], res[m.FEED_MIX_SHARE]
                # ── ① Oracle 독립 SQL
                ind = indep_get(indep, farm_no, ym)
                if ind is not None or q.provenance != INSUFFICIENT:
                    rep["recon_vs_oracle_sql"]["compared"] += 1
                    d = {}
                    sql_kg = Decimal(ind["kg"]) if ind else None
                    if not close(q.value, sql_kg, 0.15):
                        d["quantity"] = [q.value, str(sql_kg)]
                    sql_cost = Decimal(ind["cost"]) if ind and ind.get("cost") not in (None, "None") else None
                    eng_cost = c.value if c.provenance != INSUFFICIENT else c.evidence.get("partial_cost")
                    if not (eng_cost is None and (sql_cost is None or sql_cost == 0)) and not close(eng_cost, sql_cost, 1.0):
                        d["cost"] = [eng_cost, str(sql_cost)]
                    sql_pk = Decimal(ind["priced_kg"]) if ind and ind.get("priced_kg") not in (None, "None") else None
                    sql_up = (sql_cost / sql_pk) if sql_cost is not None and sql_pk else None
                    if not close(up.value, sql_up, 0.0006):
                        d["unit_price"] = [up.value, str(sql_up)]
                    eng_mix = mix.evidence.get("kg_by_feed_type") if mix.provenance != INSUFFICIENT else None
                    sql_mix = {feed_type_key(k): Decimal(v) for k, v in ind["stages"].items()} if ind and ind.get("stages") else None
                    ok_mix = (eng_mix is None and not sql_mix) or (eng_mix is not None and sql_mix is not None and set(eng_mix) == set(sql_mix)
                                                                    and all(close(eng_mix[k], sql_mix[k], 0.15) for k in eng_mix))
                    if not ok_mix:
                        d["mix"] = True
                    for k in d:
                        rep["recon_vs_oracle_sql"][k] += 1
                    if d:
                        rep["recon_vs_oracle_sql"]["details"].append({"farm": mask(farm_no), "month": ym, "diff": d})
                # ── ② shadow(Oracle 직접 → 엔진)
                sh = shadow["per_farm"].get(mask(farm_no), {}).get("months", [])
                shm = next((x for x in sh if x["month"] == ym and not x["partial"]), None)
                if shm:
                    rep["recon_vs_shadow"]["compared"] += 1
                    e = shm["engine"]
                    d2 = {}
                    # 허용오차: 원가 계열은 통화 최소단위(1 KRW) — 저장 단가 NUMERIC(18,8) 의 파생 반올림 drift 가 그 아래에 있어야 한다
                    for key, r, tol in ((m.FEED_QTY, q, 0.01), (m.FEED_COST, c, 1.0), (m.FEED_UNIT_PRICE, up, 0.0006)):
                        if not (close(r.value, e[key]["value"], tol) and r.reason == e[key]["reason"]):
                            d2[key] = [r.value, r.reason, e[key]["value"], e[key]["reason"]]
                    if prev is not None:
                        qc, cc = res[m.FEED_QTY_CHANGE], res[m.FEED_COST_CHANGE]
                        ch = shm.get("change", {})
                        if not (close(qc.value, ch.get("qty_change"), 0.01) and qc.reason == ch.get("qty_change_reason")):
                            d2["qty_change"] = [qc.value, qc.reason, ch.get("qty_change"), ch.get("qty_change_reason")]
                        if not (close(cc.value, ch.get("cost_change"), 1.0) and cc.reason == ch.get("cost_change_reason")):
                            d2["cost_change"] = [cc.value, cc.reason, ch.get("cost_change"), ch.get("cost_change_reason")]
                        v = decompose_cost_change(prev, inp)
                        sv = ch.get("variance")
                        if (v.provenance != INSUFFICIENT) != (sv is not None) or (sv and not close(v.total, sv["total"], 1.0)):
                            d2["variance"] = [v.provenance, v.reason, sv]
                    for k in d2:
                        rep["recon_vs_shadow"]["quantity" if k == m.FEED_QTY else "cost" if k == m.FEED_COST else "unit_price" if k == m.FEED_UNIT_PRICE
                                               else "variance" if k == "variance" else "change"] += 1
                    if d2:
                        rep["recon_vs_shadow"]["details"].append({"farm": mask(farm_no), "month": ym, "diff": d2})
                if prev is not None:
                    qc = res[m.FEED_QTY_CHANGE]
                    rep["change"]["reasons"][qc.reason or "value"] = rep["change"]["reasons"].get(qc.reason or "value", 0) + 1
                    v = decompose_cost_change(prev, inp)
                    if v.provenance != INSUFFICIENT:
                        rep["variance"]["eligible"] += 1
                        if abs((v.price + v.volume + v.mix) - v.total) <= 0.02:
                            rep["variance"]["identity_pass"] += 1
                prev = inp
        await db.rollback()
    await eng.dispose()
    rep["change"]["value"] = rep["change"]["reasons"].get("value", 0)
    mism = sum(rep["recon_vs_oracle_sql"][k] for k in ("quantity", "cost", "unit_price", "mix")) + \
        sum(rep["recon_vs_shadow"][k] for k in ("quantity", "cost", "unit_price", "change", "variance"))
    rep["classification"]["UNEXPLAINED"] = mism + rep["lineage"]["failures"] + (0 if rep["basis_currency_provenance_ok"] else 1)
    a.out.write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items()}, ensure_ascii=False, indent=1, default=str)[:4000])
    return 0 if rep["classification"]["UNEXPLAINED"] == 0 else 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
