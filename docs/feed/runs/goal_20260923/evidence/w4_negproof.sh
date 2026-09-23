#!/usr/bin/env bash
# W4 (B-1) negative proofs on the feed branch. Each guard broken on purpose → its test FAILs → git checkout restores.
set -u
cd /c/dev/PigOS-wt-feed
export PATH=/c/Users/bjh/AppData/Roaming/nvm/v22.23.2:$PATH
echo "# W4 negative proofs · generated $(date -u +%FT%TZ) · feed branch at $(git rev-parse --short HEAD)"

apply() {  # file python-snippet
  python - "$1" <<PY
import sys
from pathlib import Path
p = Path(sys.argv[1]); s = p.read_text(encoding="utf-8"); before = s
$2
assert s != before, "mutation did not apply"
p.write_text(s, encoding="utf-8", newline="\n")
PY
}
py() { (cd api && uv run pytest -q -p no:cacheprovider "$@" 2>&1 | grep -E "^FAILED|passed|failed" | sed -E 's/ - .{0,80}.*$//' | tail -6); }
js() { (cd src && npx vitest run tests/pages/feed.test.tsx 2>&1 | grep -E "✗|×|FAIL|Tests " | head -6); }
restore() { git checkout -- "$1"; echo "restored $1: [$(git diff --stat -- "$1")]"; }

echo; echo "=== M12 API: partial check off (period_is_partial always False)"
apply api/app/routers/base/feed_summary.py 's = s.replace("    return today <= end", "    return False")'
py tests/unit/test_feed_partial_period.py tests/integration/test_feed_summary_api.py
restore api/app/routers/base/feed_summary.py

echo; echo "=== M13 API: last day counted as complete again (today < end)"
apply api/app/routers/base/feed_summary.py 's = s.replace("    return today <= end", "    return today < end")'
py tests/unit/test_feed_partial_period.py tests/integration/test_feed_summary_api.py
restore api/app/routers/base/feed_summary.py

echo; echo "=== M14 API: farm timezone ignored (always UTC)"
apply api/app/routers/base/feed_summary.py 's = s.replace("        tz = ZoneInfo(tz_name or \"\")", "        tz = ZoneInfo(\"UTC\") if tz_name else ZoneInfo(\"\")")'
py tests/unit/test_feed_partial_period.py tests/integration/test_feed_summary_api.py
restore api/app/routers/base/feed_summary.py

echo; echo "=== M15 API: partial month still computes the comparison (override removed)"
apply api/app/routers/base/feed_summary.py 's = s.replace("    if partial:   # B-1", "    if False:   # B-1").replace("with_prev=not partial", "with_prev=True")'
py tests/integration/test_feed_summary_api.py
restore api/app/routers/base/feed_summary.py

echo; echo "=== M16 web: comparison card drawn even when partial"
apply "src/app/(app)/feed/page.tsx" 's = s.replace("            {!partial && (   /* B-1", "            {true && (   /* B-1")'
js
restore "src/app/(app)/feed/page.tsx"

echo; echo "=== M17 web: default period back to the current month"
apply "src/app/(app)/feed/page.tsx" 's = s.replace("useState(prevMonth(ym(localToday())))", "useState(ym(localToday()))")'
js
restore "src/app/(app)/feed/page.tsx"

echo; echo "=== restored — all green"
py tests/unit/test_feed_partial_period.py tests/integration/test_feed_summary_api.py
js
echo "tracked changes: [$(git status --short --untracked-files=no)]"
