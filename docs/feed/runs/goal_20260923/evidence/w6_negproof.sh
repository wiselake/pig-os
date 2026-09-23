#!/usr/bin/env bash
# W6 (visibility) negative proofs on the feed branch.
set -u
cd /c/dev/PigOS-wt-feed
export PATH=/c/Users/bjh/AppData/Roaming/nvm/v22.23.2:$PATH
echo "# W6 negative proofs · generated $(date -u +%FT%TZ) · feed branch at $(git rev-parse --short HEAD)"
apply() {
  python - "$1" <<PY
import sys
from pathlib import Path
p = Path(sys.argv[1]); s = p.read_text(encoding="utf-8"); before = s
$2
assert s != before, "mutation did not apply"
p.write_text(s, encoding="utf-8", newline="\n")
PY
}
js() { (cd src && npx vitest run $1 2>&1 | grep -E "×|Tests " | head -6); }
py() { (cd api && uv run pytest -q -p no:cacheprovider "$@" 2>&1 | grep -E "^FAILED|passed|failed" | sed -E 's/ - .{0,60}.*$//' | tail -6); }
restore() { git checkout -- "$1"; echo "restored $1: [$(git diff --stat -- "$1")]"; }
T="tests/unit/test_feed_visibility_guard.py tests/integration/test_feed_visibility_api.py"

echo; echo "=== M25 default flipped: no flag -> REFERENCE_VISIBLE"
apply api/app/services/feed_visibility.py 's = s.replace("    return v if v in (REFERENCE_VISIBLE, CUSTOMER_VISIBLE) else HIDDEN", "    return v if v in (REFERENCE_VISIBLE, CUSTOMER_VISIBLE) else REFERENCE_VISIBLE")'
py $T
restore api/app/services/feed_visibility.py

echo; echo "=== M26 DELIVERED summary no longer gated"
apply api/app/routers/base/feed_summary.py 's = s.replace("    if not is_visible(await delivered_visibility(db, farm.id)):\n        raise HTTPException(404", "    if False:\n        raise HTTPException(404")'
py $T
restore api/app/routers/base/feed_summary.py

echo; echo "=== M27 country inference added to the decision"
apply api/app/services/feed_visibility.py 's = s.replace("async def delivered_visibility(db: AsyncSession, farm_id: UUID) -> str:\n", "async def delivered_visibility(db: AsyncSession, farm_id: UUID, country: str | None = None) -> str:\n    if country == \"KR\":\n        return REFERENCE_VISIBLE\n")'
py $T
restore api/app/services/feed_visibility.py

echo; echo "=== M28 a seed-like writer of CUSTOMER_VISIBLE appears in app/"
mkdir -p api/app/seeds_tmp_proof && printf 'ROW = {"config_key": "FEED_DELIVERY_VISIBILITY", "config_value": "CUSTOMER_VISIBLE"}\n' > api/app/seeds_tmp_proof/x.py
py tests/unit/test_feed_visibility_guard.py
rm -rf api/app/seeds_tmp_proof; echo "removed api/app/seeds_tmp_proof: [$(ls api/app/seeds_tmp_proof 2>&1 | head -1)]"

echo; echo "=== M29 /sources leaks row counts while HIDDEN"
apply api/app/routers/base/feed_summary.py 's = s.replace("    delivered = DeliveredSourceOut(visibility=vis)\n    if is_visible(vis):", "    delivered = DeliveredSourceOut(visibility=vis)\n    if True:")'
py tests/integration/test_feed_visibility_api.py
restore api/app/routers/base/feed_summary.py

echo; echo "=== M30 web renders the deliveries area without the server's visibility"
apply src/components/feed/DeliveredArea.tsx 's = s.replace("  const shown = !!sources && VISIBLE.has(sources.delivered.visibility) && (sources.delivered.rows ?? 0) > 0;", "  const shown = !!sources;")'
js tests/components/DeliveredArea.test.tsx
restore src/components/feed/DeliveredArea.tsx

echo; echo "=== M31 web shows the partial sum as the cost"
apply src/components/feed/DeliveredArea.tsx 's = s.replace("      ? t(\"delivered.costPartial\", { pct: Math.round(coverage * 100) })", "      ? fmt(cost?.evidence?.[\"partial_cost\"] as number, 0)")'
js tests/components/DeliveredArea.test.tsx
restore src/components/feed/DeliveredArea.tsx

echo; echo "=== M32 web decides visibility from the farm country"
apply src/components/feed/DeliveredArea.tsx 's = s.replace("const VISIBLE = new Set([\"REFERENCE_VISIBLE\", \"CUSTOMER_VISIBLE\"]);", "const VISIBLE = new Set([\"REFERENCE_VISIBLE\", \"CUSTOMER_VISIBLE\"]);\nexport const isKr = (country: string) => country === \"KR\";")'
js tests/components/DeliveredArea.test.tsx
restore src/components/feed/DeliveredArea.tsx

echo; echo "=== restored — all green"
py $T tests/integration/test_feed_summary_api.py
js tests/components/DeliveredArea.test.tsx
echo "tracked changes: [$(git status --short)]"
