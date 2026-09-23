"""Feed Engine × PigPlan Oracle — shadow integration run (READ ONLY · PigOS DB write 0).

    Oracle(READ ONLY) → PigPlanFeedDeliverySource → classify → FeedInput(DELIVERED, KRW) → Feed Engine → audit JSON

용법:
    ORACLE_PW=... uv run --with oracledb python scripts/feed_oracle_shadow_run.py --months 12 --out ../docs/feed/reports/x.json
    (ORACLE_DSN / ORACLE_USER 는 harvest_import.py 와 같은 env. 비밀은 env 로만 — 이 스크립트는 파일에서 비밀을 읽지 않는다)

대상  하베스트 매핑 42농장(app.harvest.manifest.FARM_CODES) 중 창 안에 사료 입고 행이 있는 농장만 (fuzzy 매칭 없음)
기간  최근 12 **완료월** + 진행 중 부분월(별도 표시, 완료월 계산과 섞지 않음)
대조  Oracle 집계 SQL(엔진 미경유)과 farm×month 비교 — 엔진 결과를 엔진으로 검증하지 않는다
출력  집계·마스킹 id(sha256 앞 12자)만. 원시 행·농장 식별자·credential 은 쓰지 않는다
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine.feed import metrics as m  # noqa: E402
from app.engine.feed.normalize import feed_type_key  # noqa: E402
from app.engine.feed.types import INSUFFICIENT, Period  # noqa: E402
from app.engine.feed.variance import decompose_cost_change  # noqa: E402
from app.harvest import pigplan_feed_delivery as pf  # noqa: E402
from app.harvest.manifest import FARM_CODES  # noqa: E402

DSN_DEFAULT = "pigclouddb.c8ks4denaq5l.ap-northeast-2.rds.amazonaws.com:1521/PIGPLAN"


def mask(farm_no: int) -> str:
    return hashlib.sha256(f"PP-{farm_no}".encode()).hexdigest()[:12]


def completed_months(n: int, today: date) -> list[Period]:
    first_of_this = today.replace(day=1)
    out: list[Period] = []
    end = first_of_this - timedelta(days=1)
    for _ in range(n):
        start = end.replace(day=1)
        out.append(Period(start, end))
        end = start - timedelta(days=1)
    return list(reversed(out))


def f(v: Decimal | None, places: int = 1) -> float | None:
    return None if v is None else round(float(v), places)


def close(a: float | None, b: float | None, tol: float) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--out", required=True)
    ap.add_argument("--today", default=None, help="YYYY-MM-DD (기본: 오늘) — 결정론 재실행용")
    args = ap.parse_args()
    today = date.fromisoformat(args.today) if args.today else date.today()

    pw = os.environ.get("ORACLE_PW")
    if not pw:
        print("ORACLE_PREFLIGHT = BLOCKED_NO_CREDENTIAL (ORACLE_PW env 없음)")
        return 78
    src = pf.PigPlanFeedDeliverySource(os.environ.get("ORACLE_DSN", DSN_DEFAULT), os.environ.get("ORACLE_USER", "pksu"), pw)
    try:
        return _run(src, args.months, today, Path(args.out))
    finally:
        src.close()


def _run(src: pf.PigPlanFeedDeliverySource, months: int, today: date, out: Path) -> int:
    periods = completed_months(months, today)
    partial = Period(today.replace(day=1), today)
    win_start, win_end = periods[0].start, periods[-1].end
    farms = src.farms_with_rows(FARM_CODES, win_start, win_end)
    print(f"window {win_start}..{win_end} (+partial {partial.start}..{partial.end}) · mapped farms with rows: {len(farms)}")

    rows = src.fetch_rows(farms, win_start, partial.end)
    indep = src.independent_month_aggregates(farms, win_start, partial.end, today=today)

    per_farm: dict[str, dict] = {}
    totals = {"source_rows": 0, "quantity_accepted": 0, "excluded": 0, "cost_accepted": 0, "cost_insufficient": 0, "cost_excluded": 0}
    reasons: dict[str, int] = {}
    fm = {"quantity_usable": 0, "cost_complete": 0, "cost_partial": 0, "cost_missing": 0, "no_rows": 0}
    recon = {"quantity_mismatch": 0, "cost_mismatch": 0, "unit_price_mismatch": 0, "mix_mismatch": 0, "compared": 0, "details": []}
    change = {"qty_eligible": 0, "qty_pass": 0, "cost_eligible": 0, "cost_pass": 0, "cost_prior_insufficient": 0, "cost_incomplete_masked_as_success": 0,
              "qty_engine_reasons": {}, "cost_engine_reasons": {}, "pairs_equal_days": 0, "pairs_unequal_days": 0}
    var = {"eligible": 0, "identity_pass": 0, "identity_fail": 0, "ineligible_reasons": {}}
    golden: dict[str, dict] = {}
    engine_errors: list[str] = []
    farm_cost_profile = {"complete": 0, "partial": 0, "missing": 0}
    consecutive_2plus = 0

    for farm_no in farms:
        fid = mask(farm_no)
        frows = [r for r in rows if r.source_farm_no == farm_no]
        months_out: list[dict] = []
        prev_inp = None
        prev_month_res = None
        month_cost_states: list[str] = []
        for p in periods + [partial]:
            is_partial = p is partial
            b = pf.build_batch(farm_no, p, [r for r in frows if r.wk_dt is None or p.contains(r.wk_dt)] if not is_partial
                               else [r for r in frows if r.wk_dt is not None and p.contains(r.wk_dt)], today=today)
            # 날짜 없는 행은 첫 완료월 배치에서 한 번만 센다
            if p is not periods[0]:
                b.rows = [r for r in b.rows if r.wk_dt is not None]
                b.classes = [pf.classify(r, today=today) for r in b.rows]
            c = b.counts()
            if not is_partial:
                for k in totals:
                    totals[k] += c[k]
                for k, v in c["reasons"].items():
                    reasons[k] = reasons.get(k, 0) + v
            inp = b.feed_input()
            try:
                res = m.compute_all(inp, None if (prev_inp is None or is_partial) else prev_inp)
            except Exception as e:  # noqa: BLE001
                engine_errors.append(f"{fid} {p.start:%Y-%m}: {type(e).__name__}: {e}")
                continue
            ym = f"{p.start:%Y-%m}"
            q, cost, up, mix = res[m.FEED_QTY], res[m.FEED_COST], res[m.FEED_UNIT_PRICE], res[m.FEED_MIX_SHARE]
            cost_state = ("MISSING" if cost.reason in ("no_data", "no_cost") else "PARTIAL" if cost.reason else "COMPLETE") if not is_partial else None

            # ── 독립 대조 (완료월만) ──
            rc: dict = {}
            if not is_partial:
                key = (farm_no, ym)
                ind = indep.get(key)
                if ind is None:
                    if q.provenance != INSUFFICIENT:
                        recon["quantity_mismatch"] += 1
                        rc["quantity"] = "ENGINE_HAS_ROWS_SQL_NONE"
                    fm["no_rows"] += 1
                else:
                    recon["compared"] += 1
                    fm["quantity_usable"] += 1
                    fm[{"COMPLETE": "cost_complete", "PARTIAL": "cost_partial", "MISSING": "cost_missing"}[cost_state]] += 1
                    ok_q = close(q.value, f(ind["kg"]), 0.15)
                    sql_cost = f(ind["cost"], 2)
                    eng_cost = cost.value if cost.provenance != INSUFFICIENT else cost.evidence.get("partial_cost")
                    ok_c = close(eng_cost, sql_cost, 1.0) if not (eng_cost is None and (sql_cost in (None, 0.0))) else True
                    sql_up = f(ind["cost"] / ind["priced_kg"], 4) if ind["cost"] is not None and ind["priced_kg"] else None
                    ok_u = close(up.value, sql_up, 0.0006)
                    eng_mix = mix.evidence.get("kg_by_feed_type") if mix.provenance != INSUFFICIENT else None
                    sql_mix = {feed_type_key(k): f(v) for k, v in ind["stages"].items()} if ind["stages"] else None
                    ok_m = (eng_mix is None and sql_mix is None) or (eng_mix is not None and sql_mix is not None
                            and set(eng_mix) == set(sql_mix) and all(close(eng_mix[k], sql_mix[k], 0.15) for k in eng_mix))
                    if not ok_q:
                        recon["quantity_mismatch"] += 1
                    if not ok_c:
                        recon["cost_mismatch"] += 1
                    if not ok_u:
                        recon["unit_price_mismatch"] += 1
                    if not ok_m:
                        recon["mix_mismatch"] += 1
                    rc = {"quantity": ok_q, "cost": ok_c, "unit_price": ok_u, "mix": ok_m}
                    if not all(rc.values()):
                        recon["details"].append({"farm": fid, "month": ym, "engine": {"qty": q.value, "cost": eng_cost, "unit_price": up.value, "mix": eng_mix},
                                                 "sql": {"qty": f(ind["kg"]), "cost": sql_cost, "unit_price": sql_up, "mix": sql_mix}})
                month_cost_states.append(cost_state)

            # ── CHANGE / VARIANCE (완료월, 이전 완료월 존재) ──
            ch: dict = {}
            if not is_partial and prev_inp is not None:
                qc, cc = res[m.FEED_QTY_CHANGE], res[m.FEED_COST_CHANGE]
                change["pairs_equal_days" if prev_inp.period.days == inp.period.days else "pairs_unequal_days"] += 1
                for key, r_ in (("qty_engine_reasons", qc), ("cost_engine_reasons", cc)):
                    lab = r_.reason or "value"
                    change[key][lab] = change[key].get(lab, 0) + 1
                if q.provenance != INSUFFICIENT and prev_month_res[m.FEED_QTY].provenance != INSUFFICIENT:
                    change["qty_eligible"] += 1
                    expect = round(q.value - prev_month_res[m.FEED_QTY].value, 1)
                    if qc.provenance != INSUFFICIENT and close(qc.value, expect, 0.15) and qc.quantity_basis == "DELIVERED":
                        change["qty_pass"] += 1
                if cost.provenance != INSUFFICIENT and prev_month_res[m.FEED_COST].provenance != INSUFFICIENT:
                    change["cost_eligible"] += 1
                    expect = round(cost.value - prev_month_res[m.FEED_COST].value, 2)
                    if cc.provenance != INSUFFICIENT and close(cc.value, expect, 1.0):
                        change["cost_pass"] += 1
                elif cost.provenance != INSUFFICIENT and prev_month_res[m.FEED_COST].provenance == INSUFFICIENT:
                    change["cost_prior_insufficient"] += 1
                    if cc.provenance != INSUFFICIENT:
                        change["cost_incomplete_masked_as_success"] += 1
                elif cost.provenance == INSUFFICIENT and cc.provenance != INSUFFICIENT:
                    change["cost_incomplete_masked_as_success"] += 1
                v = decompose_cost_change(prev_inp, inp)
                if v.provenance != INSUFFICIENT:
                    var["eligible"] += 1
                    if abs((v.price + v.volume + v.mix) - v.total) <= 0.02 and v.quantity_basis == "DELIVERED":
                        var["identity_pass"] += 1
                    else:
                        var["identity_fail"] += 1
                    ch["variance"] = {"total": v.total, "price": v.price, "volume": v.volume, "mix": v.mix}
                else:
                    var["ineligible_reasons"][v.reason] = var["ineligible_reasons"].get(v.reason, 0) + 1
                ch.update({"qty_change": qc.value, "qty_change_reason": qc.reason, "cost_change": cc.value, "cost_change_reason": cc.reason})

            month_rec = {"month": ym, "partial": is_partial, "counts": c, "cost_state": cost_state,
                         "engine": {k: {"value": r.value, "provenance": r.provenance, "reason": r.reason, "basis": r.quantity_basis}
                                    for k, r in res.items()},
                         "unit_price_by_stage": up.evidence.get("by_feed_type"), "mix_shares": mix.evidence.get("shares"),
                         "recon": rc, "change": ch}
            months_out.append(month_rec)

            # ── golden cases (실데이터, 마스킹) ──
            def _g(name: str, expected: dict) -> None:
                if name not in golden:
                    golden[name] = {"farm": fid, "month": ym, "raw_summary": c,
                                    "canonical": {"rows": len(inp.rows), "basis": inp.quantity_basis, "currency": inp.farm_currency},
                                    "engine": month_rec["engine"], "independent_expected": expected, "status": "PASS" if all(rc.values() or [True]) else "FAIL"}
            if not is_partial and ind is not None:
                exp = {"qty": f(ind["kg"]), "cost": f(ind["cost"], 2), "priced_kg": f(ind["priced_kg"])}
                if cost_state == "COMPLETE":
                    _g("normal_complete_cost", exp)
                if cost_state == "PARTIAL":
                    _g("partial_cost", exp)
                if cost_state == "MISSING" and q.provenance != INSUFFICIENT:
                    _g("missing_cost", exp)
                if c["feed_stages"] >= 2:
                    _g("multiple_feed_types", exp)
                if ch.get("qty_change") is not None:
                    _g("quantity_change", {**exp, "prev_qty": prev_month_res[m.FEED_QTY].value})
                if ch.get("cost_change") is not None:
                    _g("cost_change", {**exp, "prev_cost": prev_month_res[m.FEED_COST].value})
                if "variance" in ch:
                    _g("variance_eligible", {**exp, "identity": "PRICE+VOLUME+MIX=TOTAL"})
                if prev_inp is not None and q.provenance != INSUFFICIENT and prev_month_res[m.FEED_QTY].provenance != INSUFFICIENT:
                    _g("consecutive_months", exp)
            if not is_partial:
                prev_inp, prev_month_res = inp, res

        # farm-level cost profile (12 완료월 기준)
        states = [s for s in month_cost_states if s]
        if states and all(s == "COMPLETE" for s in states if s != "MISSING") and any(s == "COMPLETE" for s in states) and "PARTIAL" not in states:
            farm_cost_profile["complete"] += 1
        elif any(s in ("COMPLETE", "PARTIAL") for s in states):
            farm_cost_profile["partial"] += 1
        else:
            farm_cost_profile["missing"] += 1
        with_rows = [mo for mo in months_out if not mo["partial"] and mo["engine"][m.FEED_QTY]["provenance"] != "INSUFFICIENT"]
        if any(mo2["month"] == _next_month(mo1["month"]) for mo1 in with_rows for mo2 in with_rows):
            consecutive_2plus += 1
        per_farm[fid] = {"months": months_out, "cost_profile_states": states}

    # ── 원가 파생 타당성: 직접 단가 vs 총액/kg 파생 단가 분포 (완료월·수량 ACCEPTED 행) ──
    def _p(vals: list[float], q: float) -> float | None:
        if not vals:
            return None
        v = sorted(vals)
        return round(v[min(len(v) - 1, int(q * (len(v) - 1)))], 1)
    direct, derived = [], []
    farm_direct_ratio: dict[int, list[int]] = {}
    for r in rows:
        if r.wk_dt is None or not (win_start <= r.wk_dt <= win_end):
            continue
        c_ = pf.classify(r, today=today)
        if c_.quantity != "ACCEPTED":
            continue
        fr = farm_direct_ratio.setdefault(r.source_farm_no, [0, 0])
        fr[1] += 1
        if r.fper_price is not None and r.fper_price > 0:
            fr[0] += 1
            direct.append(float(r.fper_price))
        elif pf.COST_DERIVED_FROM_TOTAL in c_.reasons and c_.unit_cost is not None:
            derived.append(float(c_.unit_cost))
    preflight_profile = {"fully_priced": 0, "partially_priced": 0, "unpriced": 0}
    for a, n in farm_direct_ratio.values():
        ratio = a / n if n else 0
        preflight_profile["fully_priced" if ratio >= 0.999 else "partially_priced" if ratio > 0 else "unpriced"] += 1
    cost_derivation = {"direct_unit_price_rows": len(direct), "derived_from_total_rows": len(derived),
                       "direct_p05_p50_p95": [_p(direct, .05), _p(direct, .5), _p(direct, .95)],
                       "derived_p05_p50_p95": [_p(derived, .05), _p(derived, .5), _p(derived, .95)],
                       "preflight_equivalent_farm_profile(direct unit price only)": preflight_profile}

    report = {
        "generated": today.isoformat(), "engine_formula_version": m.FeedMetricResult.__dataclass_fields__["formula_version"].default,
        "source_contract": pf.SOURCE_CONTRACT,
        "extraction": {"window": {"start": win_start.isoformat(), "end": win_end.isoformat(), "completed_months": months},
                       "partial_month": {"start": partial.start.isoformat(), "end": partial.end.isoformat()},
                       "mapped_farms_in_manifest": len(FARM_CODES), "farms_with_rows": len(farms), "farms_masked": [mask(x) for x in farms],
                       **totals, "reasons": reasons},
        "farm_months": fm, "farm_cost_profile": farm_cost_profile, "farms_2plus_consecutive": consecutive_2plus,
        "reconciliation": recon, "change": change, "variance": var, "cost_derivation": cost_derivation,
        "golden_cases": golden, "engine_errors": engine_errors,
        "per_farm": per_farm,
        "production": {"oracle_write": "NO", "pigos_write": "NO", "deploy": "NO"},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("farm_months", "farm_cost_profile", "farms_2plus_consecutive", "reconciliation", "change", "variance", "cost_derivation")},
                     ensure_ascii=False, indent=1, default=str)[:6000])
    print("golden:", {k: v["status"] for k, v in golden.items()})
    print("engine_errors:", len(engine_errors))
    print("report:", out)
    return 0


def _next_month(ym: str) -> str:
    y, mth = int(ym[:4]), int(ym[5:7])
    return f"{y + (mth == 12):04d}-{(mth % 12) + 1:02d}"


if __name__ == "__main__":
    raise SystemExit(main())
