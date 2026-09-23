"""Print identifier-free pre-count from the snapshot file."""
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
m = d["meta"]
rows = d["rows"]
print("extracted_at", m["extracted_at"])
print("scope_hash", m["source_scope_hash"])
print("content_hash", m["content_hash"])
print("rows", m["row_count"], "| ACTIVE", m["use_yn_distribution"].get("Y"), "| INACTIVE", m["use_yn_distribution"].get("non-Y"))
print("farms_with_rows", m["observed_farms_with_rows"], "| authorized", m["authorized_mapping_scope"],
      "| date", m["date_min"], "~", m["date_max"], "| dateless", m["dateless_rows"])
pm = [r for r in rows if r["wk_dt"] and r["wk_dt"].get("__d__", "").startswith("2026-09")]
print("partial month 2026-09 rows", len(pm))
