"""Render the numbers section of a feed-load execution record from the run folder — no hand-typed numbers.

    python scripts/feed_load_report.py ../docs/feed/runs/prod_20260923            # print the block
    python scripts/feed_load_report.py ../docs/feed/runs/prod_20260923 --write ../docs/feed/releases/FEED_INITIAL_LOAD_EXECUTION_20260923.md
    python scripts/feed_load_report.py ../docs/feed/runs/prod_20260923 --check ../docs/feed/releases/FEED_INITIAL_LOAD_EXECUTION_20260923.md

The block lives between `<!-- BEGIN GENERATED -->` and `<!-- END GENERATED -->`. --check exits 1 if the committed block differs
from what the files produce (tests/unit/test_feed_load_report.py runs it) — editing a number by hand breaks CI.

Every row carries its provenance:
  MACHINE      written by the load/verify scripts themselves (preflight/load/verify/load2.json)
  CAPTURED     command output tee'd to a file at run time (state_before.txt, schema_after.txt)
  TRANSCRIBED  copied from the terminal after the fact (projection.json, ops_evidence.txt) — lowest trust, labelled as such

If projection_rerun.json exists (the approved validator re-run with --production-read-only --out), the projection rows come
from it as MACHINE, the shadow cross-check rows are added, and one row states whether the old TRANSCRIBED values agree with it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BEGIN, END = "<!-- BEGIN GENERATED -->", "<!-- END GENERATED -->"


def _kv(path: Path, sep: str) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or sep not in line:
            continue
        k, v = line.split(sep, 1)
        out[k.strip()] = v.strip()
    return out


# (label, transcribed projection.json key, rerun projection_rerun.json path) — the items both runs measured
_AGREE = (("projected rows", "projected_rows", ("projected_rows",)), ("lineage checked", "lineage_checked", ("lineage", "checked")),
          ("lineage failures", "lineage_failures", ("lineage", "failures")), ("compared", "compared", ("recon_vs_oracle_sql", "compared")),
          ("quantity", "quantity", ("recon_vs_oracle_sql", "quantity")), ("cost", "cost", ("recon_vs_oracle_sql", "cost")),
          ("unit price", "unit_price", ("recon_vs_oracle_sql", "unit_price")), ("mix", "mix", ("recon_vs_oracle_sql", "mix")),
          ("change values", "change_values", ("change", "value")), ("variance eligible", "variance_eligible", ("variance", "eligible")),
          ("variance pass", "variance_identity_pass", ("variance", "identity_pass")))


def _get(d: dict, path: tuple[str, ...]):
    for k in path:
        d = d[k]
    return d


def _projection_rows(run: Path, proj: dict) -> list[tuple[str, str, str, str]]:
    rr = run / "projection_rerun.json"
    if not rr.exists():
        return [
            ("projection", "completed farm-months · compared", f'{proj["farm_months_completed"]} · {proj["compared"]}', "TRANSCRIBED projection.json"),
            ("projection", "quantity · cost · unit price · mix mismatch", f'{proj["quantity"]} · {proj["cost"]} · {proj["unit_price"]} · {proj["mix"]}', "TRANSCRIBED projection.json"),
            ("projection", "lineage checked · failures", f'{proj["lineage_checked"]} · {proj["lineage_failures"]}', "TRANSCRIBED projection.json"),
            ("projection", "change values · variance pass/eligible", f'{proj["change_values"]} · {proj["variance_identity_pass"]}/{proj["variance_eligible"]}', "TRANSCRIBED projection.json"),
        ]
    r = json.loads(rr.read_text(encoding="utf-8"))
    o, sh = r["recon_vs_oracle_sql"], r["recon_vs_shadow"]
    src = "MACHINE projection_rerun.json"
    diff = [label for label, old, new in _AGREE if proj[old] != _get(r, new)]
    return [
        ("projection", "mode · DB alembic", f'{r["mode"]} · {r.get("db_alembic")}', src),
        ("projection", "① vs Oracle SQL: compared · qty · cost · unit price · mix mismatch", f'{o["compared"]} · {o["quantity"]} · {o["cost"]} · {o["unit_price"]} · {o["mix"]}', src),
        ("projection", "② vs shadow: compared · qty · cost · unit price · change · variance mismatch",
         f'{sh["compared"]} · {sh["quantity"]} · {sh["cost"]} · {sh["unit_price"]} · {sh["change"]} · {sh["variance"]}', src),
        ("projection", "lineage checked · failures", f'{r["lineage"]["checked"]} · {r["lineage"]["failures"]}', src),
        ("projection", "change values · variance pass/eligible", f'{r["change"]["value"]} · {r["variance"]["identity_pass"]}/{r["variance"]["eligible"]}', src),
        ("projection", "basis·currency·provenance ok · UNEXPLAINED", f'{r["basis_currency_provenance_ok"]} · {r["classification"]["UNEXPLAINED"]}', src),
        ("projection", f"당시 ad-hoc 값 = 재실행 ({len(_AGREE)} 항목)", "SAME" if not diff else "DIFFERENT: " + ", ".join(diff),
         "MACHINE projection_rerun.json vs TRANSCRIBED projection.json"),
    ]


def render(run: Path) -> str:
    pre = json.loads((run / "preflight.json").read_text(encoding="utf-8"))
    load = json.loads((run / "load.json").read_text(encoding="utf-8"))
    ver = json.loads((run / "verify.json").read_text(encoding="utf-8"))
    load2 = json.loads((run / "load2.json").read_text(encoding="utf-8"))
    proj = json.loads((run / "projection.json").read_text(encoding="utf-8"))
    before = _kv(run / "state_before.txt", " ")
    after = _kv(run / "schema_after.txt", " ")
    ops = _kv(run / "ops_evidence.txt", ": ")
    e = pre["expected"]
    li, vi = load["invariants"], ver["invariants"]
    rows = [
        ("preflight", "gate", pre["gate"]["mode"] + " / writes " + pre["gate"]["writes"], "MACHINE preflight.json"),
        ("preflight", "scope hash", pre["source_scope_hash"], "MACHINE preflight.json"),
        ("preflight", "authorized / observed / unmapped", f'{pre["authorized_mapping_scope"]} / {pre["observed_farms_with_rows"]} / {pre["unmapped_included"]}', "MACHINE preflight.json"),
        ("preflight", "source rows · ACTIVE · INACTIVE", f'{e["total"]} · {e["source_status"].get("ACTIVE")} · {e["source_status"].get("INACTIVE")}', "MACHINE preflight.json"),
        ("preflight", "quantity ACCEPTED / EXCLUDED", f'{e["quantity_status"].get("ACCEPTED")} / {e["quantity_status"].get("EXCLUDED")}', "MACHINE preflight.json"),
        ("preflight", "cost ACCEPTED / INSUFFICIENT / EXCLUDED", f'{e["cost_status"].get("ACCEPTED")} / {e["cost_status"].get("INSUFFICIENT")} / {e["cost_status"].get("EXCLUDED")}', "MACHINE preflight.json"),
        ("preflight", "partial month rows (source)", str(e["by_month"].get(pre["window"][1][:7], 0)), "MACHINE preflight.json"),
        ("code", "fingerprint (load gate)", load["gate"]["code_fingerprint"], "MACHINE load.json"),
        ("code", "fingerprint (in container)", ops.get("fingerprint_in_container", "?"), "TRANSCRIBED ops_evidence.txt"),
        ("recovery", "backup", f'{ops.get("backup_file")} ({int(ops.get("backup_bytes", 0)):,} bytes)', "TRANSCRIBED ops_evidence.txt"),
        ("migration", "before → after", f'{before.get("alembic_version")} → {after.get("alembic_version")}', "CAPTURED state_before/schema_after"),
        ("schema", "public tables before → after", f'{before.get("public_tables")} → {after.get("public_tables")}', "CAPTURED"),
        ("schema", "indexes missing / checks missing", f'{after.get("indexes_missing")} / {after.get("checks_missing")}', "CAPTURED schema_after.txt"),
        ("schema", "non-feed fingerprint before = after", f'{before.get("schema_fingerprint_non_feed")} = {after.get("schema_fingerprint_non_feed")} '
         f'({"SAME" if before.get("schema_fingerprint_non_feed") == after.get("schema_fingerprint_non_feed") else "DIFFERENT"})', "CAPTURED"),
        ("load", "status · fetched · inserted", f'{load["sync"]["status"]} · {load["sync"]["fetched"]} · {load["sync"]["inserted"]}', "MACHINE load.json"),
        ("load", "elapsed s · DB delta bytes", f'{load["performance"]["elapsed_s"]} · {load["db_size_delta_bytes"]}', "MACHINE load.json"),
        ("load", "grain mismatch", json.dumps(load["mismatch"]), "MACHINE load.json"),
        ("verify", "current total · mismatch", f'{ver["observed_current_total"]} · {json.dumps(ver["mismatch"])}', "MACHINE verify.json"),
        ("verify", "hash NULL · non-KRW · non-DELIVERED · current/identity · identities · max rev",
         f'{vi["payload_hash_null"]} · {vi["currency_not_krw"]} · {vi["basis_not_delivered"]} · {vi["current_per_identity_max"]} · {vi["identities"]} · {vi["max_revision"]}', "MACHINE verify.json"),
        *_projection_rows(run, proj),
        ("projection", "partial-month rows (persisted, qty ACCEPTED)", str(proj["partial_month_rows"]), "TRANSCRIBED projection.json"),
        ("idempotency", "2nd apply inserted · unchanged · revisions", f'{load2["sync"]["inserted"]} · {load2["sync"]["unchanged"]} · {load2["invariants"]["rows_all_revisions"]}', "MACHINE load2.json"),
        ("idempotency", "sync_runs", " , ".join(f'{r["status"]}(+{r["inserted"]})' for r in load2["invariants"]["sync_runs"]), "MACHINE load2.json"),
        ("post", "feed_source_rows · feed_records", f'{li["rows_all_revisions"]} · {after.get("feed_records")}', "MACHINE load.json / CAPTURED"),
        ("post", "api /health · /feed/summary · worker feed jobs", f'{ops.get("api_health_http")} · {ops.get("feed_summary_http")} · {ops.get("worker_jobs_mentioning_feed_source")}', "TRANSCRIBED ops_evidence.txt"),
    ]
    lines = [BEGIN, "", "| 단계 | 항목 | 값 | 출처 |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | `{c}` | {d} |" for a, b, c, d in rows]
    grades = {}
    for *_, d in rows:
        g = d.split()[0]
        grades[g] = grades.get(g, 0) + 1
    lines += ["", "등급별 행 수: " + " · ".join(f"{k} {v}" for k, v in sorted(grades.items())), "", END]
    return "\n".join(lines)


def splice(doc: str, block: str) -> str:
    i, j = doc.index(BEGIN), doc.index(END) + len(END)
    return doc[:i] + block + doc[j:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", type=Path)
    g.add_argument("--check", type=Path)
    a = ap.parse_args()
    block = render(a.run)
    if a.write:
        a.write.write_text(splice(a.write.read_text(encoding="utf-8"), block), encoding="utf-8", newline="\n")
        return 0
    if a.check:
        doc = a.check.read_text(encoding="utf-8").replace("\r\n", "\n")
        cur = doc[doc.index(BEGIN):doc.index(END) + len(END)]
        if cur != block:
            print("GENERATED BLOCK OUT OF DATE (hand-edited or files changed) — rerun with --write")
            return 1
        print("OK")
        return 0
    print(block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
