#!/usr/bin/env bash
# 공개 방침 내부 마커 종결 검증 — KNOWN_PUBLICATION_EXPOSURE "종결 검증 절차" 다섯 항목.
#
# ★ 마커 수만 세지 않는다. 빈 문서·잘못된 fallback 도 0 이기 때문이다.
# 사용: scripts/verify_public_notice.sh [BASE_URL]
set -uo pipefail
BASE="${1:-https://api.pigos.io}"
FAIL=0
say() { printf '%-42s %s\n' "$1" "$2"; }
bad() { FAIL=1; }

for lang in ko en; do
  url="$BASE/legal/privacy?lang=$lang"
  body=$(curl -s -m 20 -w '\n%{http_code}' "$url") || { say "[$lang] fetch" "FAIL (curl)"; bad; continue; }
  code=$(printf '%s' "$body" | tail -1)
  html=$(printf '%s' "$body" | sed '$d')

  # 1  HTTP 200
  [ "$code" = "200" ] && say "[$lang] 1 http" "ok (200)" || { say "[$lang] 1 http" "FAIL ($code)"; bad; }

  # 2  본문이 비어 있지 않다 — 20KB 미만이면 다른 것을 받은 것이다
  size=$(printf '%s' "$html" | wc -c)
  [ "$size" -gt 20000 ] && say "[$lang] 2 non-empty" "ok (${size}B)" || { say "[$lang] 2 non-empty" "FAIL (${size}B < 20000)"; bad; }

  # 3  문서 정체성 — 방침이 맞는지. 마커가 0 인 빈 페이지와 구분한다
  if [ "$lang" = ko ]; then needle="제9조"; else needle="Article 9"; fi
  printf '%s' "$html" | grep -q "$needle" && say "[$lang] 3 identity" "ok ('$needle')" || { say "[$lang] 3 identity" "FAIL ('$needle' 없음)"; bad; }

  # 4  전체 detector — 한 종류만 세면 나머지가 남는다
  total=0
  for pat in '\[V —' '\[V -' '\[OPEN' '\[COUNSEL\]' '\[ \]'; do
    n=$(printf '%s' "$html" | grep -o "$pat" | wc -l)
    total=$((total + n))
    [ "$n" -gt 0 ] && say "[$lang] 4 marker $pat" "FAIL ($n)"
  done
  [ "$total" -eq 0 ] && say "[$lang] 4 markers total" "ok (0)" || bad
done

echo
if [ "$FAIL" -eq 0 ]; then
  echo "PASS — 1~4 충족. ★ 5(배포 SHA 일치)는 서버에서 따로 확인한다:"
  echo "  ssh … 'docker exec <api> sha256sum /app/content/legal/public_privacy.ko.md'"
  echo "  저장소 값: $(sha256sum api/content/legal/public_privacy.ko.md 2>/dev/null | cut -d' ' -f1)"
  echo "  다섯 항목이 모두 참일 때만 PUBLIC_INTERNAL_MARKER_EXPOSURE = CLOSED."
else
  echo "FAIL — 종결 조건 미충족. 격리를 닫지 않는다."
fi
exit "$FAIL"
