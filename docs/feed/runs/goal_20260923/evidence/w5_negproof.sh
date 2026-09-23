#!/usr/bin/env bash
# W5 (B-2) negative proofs on the feed branch.
set -u
cd /c/dev/PigOS-wt-feed
export PATH=/c/Users/bjh/AppData/Roaming/nvm/v22.23.2:$PATH
echo "# W5 negative proofs · generated $(date -u +%FT%TZ) · feed branch at $(git rev-parse --short HEAD)"
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
js() { (cd src && npx vitest run $1 2>&1 | grep -E "×|Tests " | head -5); }
py() { (cd api && uv run pytest -q -p no:cacheprovider "$@" 2>&1 | grep -E "^FAILED|passed|failed" | sed -E 's/ - .{0,60}.*$//' | tail -4); }
restore() { git checkout -- "$1"; echo "restored $1: [$(git diff --stat -- "$1")]"; }

echo; echo "=== M18 ko delivered string says FCR"
apply src/messages/ko.json 's = s.replace("\"basis\": \"배송(입고) 기준 — 돼지가 먹은 양이 아닙니다\"", "\"basis\": \"배송(입고) 기준 — FCR 입력원\"")'
js tests/feedDeliveredGuard.test.ts
restore src/messages/ko.json

echo; echo "=== M19 en delivered string says consumption"
apply src/messages/en.json 's = s.replace("\"qty\": \"Delivered\"", "\"qty\": \"Feed consumption\"")'
js tests/feedDeliveredGuard.test.ts
restore src/messages/en.json

echo; echo "=== M20 zh delivered key removed (8-locale parity)"
apply src/messages/zh.json 's = s.replace("      \"syncFailed\": \"上次同步失败\"\n", "").replace("\"asOf\": \"数据截至 {date}\",", "\"asOf\": \"数据截至 {date}\"")'
js tests/i18n.test.ts
restore src/messages/zh.json

echo; echo "=== M21 page references the FCR metric key"
apply "src/app/(app)/feed/page.tsx" 's = s.replace("  const qtyChange = m[\"FEED_QTY_CHANGE\"];", "  const qtyChange = m[\"FEED_QTY_CHANGE\"];\n  const fcrMetric = m[\"FCR\"];")'
js tests/feedDeliveredGuard.test.ts
restore "src/app/(app)/feed/page.tsx"

echo; echo "=== M22 router loads a cohort (with_cohort=True)"
apply api/app/routers/base/feed_summary.py 's = s.replace("cur = await load_feed_input(db, farm, start, end, with_cohort=False)", "cur = await load_feed_input(db, farm, start, end, with_cohort=True)")'
py tests/unit/test_feed_no_fcr_path.py
restore api/app/routers/base/feed_summary.py

echo; echo "=== M23 router returns an FCR metric"
apply api/app/routers/base/feed_summary.py 's = s.replace("    res = m.compute_all(cur, prev)\n", "    res = m.compute_all(cur, prev)\n    res.pop(m.FCR, None)\n")'
py tests/unit/test_feed_no_fcr_path.py
restore api/app/routers/base/feed_summary.py

echo; echo "=== M24 FCR subtitle leaks outside the fed area"
apply "src/app/(app)/feed/page.tsx" 's = s.replace("      <h1 className=\"text-2xl font-extrabold text-text\">{t(\"title\")}</h1>\n", "      <h1 className=\"text-2xl font-extrabold text-text\">{t(\"title\")}</h1>\n      <p>{t(\"subtitle\")}</p>\n")'
js tests/pages/feed.test.tsx
restore "src/app/(app)/feed/page.tsx"

echo; echo "=== restored — all green"
js "tests/feedDeliveredGuard.test.ts tests/i18n.test.ts tests/pages/feed.test.tsx"
py tests/unit/test_feed_no_fcr_path.py
echo "tracked changes: [$(git status --short --untracked-files=no)]"
