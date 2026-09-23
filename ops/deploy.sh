#!/usr/bin/env bash
# PigOS 프로덕션 배포 — 되돌릴 수 있는 상태를 만들고 배포한다.
#
# 2026-08-24 사고에서 배운 것:
#   1) 롤백 이미지를 손으로 태깅했더니 사라져 있었다 → 자동화하고 prune 에서 보호
#   2) 배포 직전 DB 스냅샷이 없었다 → 배포 전에 뜬다
#   3) compose 파일 하나만 쓰면 포트 매핑이 빠져 502 → 두 파일 강제
#   4) api 재기동마다 커넥션을 새로 맺어 수십 초 느려진다 → 불필요한 재기동 금지
#
# 서버에서 실행 (게이트 설치 위치에서 — 앱 트리 안의 사본이 아니다):
#   ~/pigos-gate/deploy.sh <api|web|worker|all> --expect-sha <40자리 커밋 sha> [--preflight-only]
#   --preflight-only  게이트(G·A·0)만 돌리고 끝낸다 — 백업·빌드·재기동 없음
#
# 2026-09-23 결정 D-A·D-B:
#   G) 게이트 자신이 GATE_SOURCE.json 과 같은가 (게이트 파일 변조 거부)
#   A) 서버 앱 트리(~/pigos)가 배포 대상 커밋과 파일 단위로 같은가 (RELEASE_MANIFEST.json, ops/ 포함)
#   0) DB 리비전 ↔ 코드 alembic head — DB 가 앞서면 additive 허용 목록(게이트 쪽 파일)으로만 통과
#   게이트는 앱 트리 밖에 둔다: 롤백 때 앱 트리는 DB 보다 옛것이라 새 리비전을 모른다.
set -euo pipefail

usage() { echo "usage: $0 <api|web|worker|all> --expect-sha <40-hex> [--preflight-only]"; exit 2; }
SVC="${1:-}"; shift || true
EXPECT_SHA=""; PREFLIGHT_ONLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --expect-sha) EXPECT_SHA="${2:-}"; shift 2 || usage ;;
    --preflight-only) PREFLIGHT_ONLY=1; shift ;;
    *) usage ;;
  esac
done
[ -n "$EXPECT_SHA" ] || usage
ROOT="${PIGOS_ROOT:-$HOME/pigos}"
GATE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE="-f $ROOT/docker-compose.prod.yml -f $ROOT/docker-compose.deploy.yml"
TS=$(date +%Y%m%d-%H%M%S)
KEEP_ROLLBACKS="${KEEP_ROLLBACKS:-3}"

case "$SVC" in
  all) SERVICES="api worker web" ;;
  api|web|worker) SERVICES="$SVC" ;;
  *) usage ;;
esac

if [ "$(cd "$ROOT" && pwd)/ops" = "$GATE" ]; then
  echo "❌ 거부 (APP_TREE) — 앱 트리 안의 deploy.sh($GATE)로 실행했다. 게이트 설치 위치(~/pigos-gate)에서 실행하라"; exit 3
fi

echo "════ G/5 게이트 무결성 ════"
python3 "$GATE/release_manifest.py" verify-gate --dir "$GATE" || { echo "❌ 배포 거부 — 게이트 파일이 기록과 다르다"; exit 3; }

echo "════ A/5 서버 소스 == 배포 대상 커밋 ════"
python3 "$GATE/release_manifest.py" verify --root "$ROOT" --expect-sha "$EXPECT_SHA" \
  || { echo "❌ 배포 거부 — 서버 앱 트리가 배포 대상 커밋 $EXPECT_SHA 와 다르다"; exit 3; }

cd "$ROOT"
echo "════ 0/5 DB 리비전 ↔ 코드 alembic head ════"
# ★ 2026-09-23: 프로덕션 DB(a7c9e1f3b5d7)가 main 코드보다 앞선 상태가 생겼다. api/worker 를 배포할 때
#   DB 리비전이 배포될 코드의 유일한 head 와 같지 않으면 거부한다 — 단 앞선 리비전이 전부 additive 허용 목록에 있으면 통과(D-A).
case " $SERVICES " in
  *" api "*|*" worker "*)
    DBREV=$(sudo docker exec -i pigos-api python - <<'PY' 2>/dev/null | tail -1
import asyncio, os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
async def m():
    e = create_async_engine(os.environ["DATABASE_URL"])
    async with e.connect() as c:
        print((await c.execute(text("SELECT version_num FROM alembic_version"))).scalar())
    await e.dispose()
asyncio.run(m())
PY
) || DBREV=""
    echo "  DB revision: ${DBREV:-<unknown>}"
    "$GATE/check_migration_drift.sh" "${DBREV}" "$ROOT/api/alembic/versions" \
      || { echo "❌ 배포 거부 — DB 리비전과 코드 alembic head 불일치"; exit 3; }
    ;;
  *) echo "  web 만 배포 — 생략" ;;
esac

if [ "$PREFLIGHT_ONLY" = "1" ]; then
  echo "✅ preflight 통과 (--preflight-only: 백업·빌드·재기동 없이 종료)"; exit 0
fi

echo "════ 1/5 배포 전 DB 스냅샷 ════"
if [ -x "$ROOT/ops/backup_db.sh" ]; then
  "$ROOT/ops/backup_db.sh" full deploy
else
  echo "⚠ ops/backup_db.sh 없음 — 스냅샷 없이 진행합니다"
  read -r -p "계속? (yes/no) " a; [ "$a" = "yes" ] || exit 1
fi

echo "════ 2/5 롤백 이미지 태깅 ════"
# ★ :rollback-<ts> 로 남긴다. 태그가 붙어 있으면 dangling 이 아니라 prune 대상이 아니다.
for s in $SERVICES; do
  cname="pigos-$s"
  if img=$(sudo docker inspect "$cname" --format '{{.Image}}' 2>/dev/null); then
    sudo docker tag "$img" "pigos-$s:rollback-$TS"
    echo "  pigos-$s:rollback-$TS"
  else
    echo "  $cname 미실행 — 태깅 생략"
  fi
done

echo "════ 2.5/5 빌드 컨텍스트 검증 ════"
# ★ 소스를 부분 동기화하다 디렉토리가 통째로 빠지는 사고가 있었다(2026-08-24).
#   api/content 가 서버에 없어서 가입 API 가 500 을 내고 있었는데 아무도 몰랐다.
#   빌드 전에 필수 경로가 컨텍스트에 있는지 확인한다.
REQUIRED_API=(app alembic content pyproject.toml Dockerfile)
REQUIRED_WEB=(app components lib messages package.json)
miss=0
for s_ in $SERVICES; do
  case "$s_" in
    api|worker) for r in "${REQUIRED_API[@]}"; do
        [ -e "$ROOT/api/$r" ] || { echo "  ❌ api/$r 없음"; miss=1; }; done ;;
    web) for r in "${REQUIRED_WEB[@]}"; do
        [ -e "$ROOT/src/$r" ] || { echo "  ❌ src/$r 없음"; miss=1; }; done ;;
  esac
done
[ "$miss" -eq 0 ] || { echo "빌드 컨텍스트가 불완전합니다 — 소스 동기화를 다시 하십시오"; exit 1; }
echo "  필수 경로 확인 완료"

echo "════ 3/5 빌드 ════"
# shellcheck disable=SC2086
sudo docker compose $COMPOSE build $SERVICES

echo "════ 4/5 기동 ════"
# ★ compose 두 파일 모두 필요. deploy.yml 이 빠지면 127.0.0.1:8010/3010 매핑이 없어져
#   호스트 nginx 가 502 를 낸다(2026-08-11 실제 사고).
# shellcheck disable=SC2086
sudo docker compose $COMPOSE up -d $SERVICES

echo "════ 5/5 검증 ════"
sleep 12
for s in $SERVICES; do sudo docker ps --format '  {{.Names}} {{.Status}}' | grep "pigos-$s" || true; done
echo "  포트 매핑:"; sudo docker port pigos-api 2>/dev/null | sed 's/^/    /' || true
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 https://api.pigos.io/health || echo 000)
echo "  api.pigos.io/health = $code"
[ "$code" = "200" ] || { echo "❌ 헬스체크 실패 — 롤백을 검토하십시오(ops/ROLLBACK.md)"; exit 1; }

# 오래된 롤백 태그 정리 — 최근 N개만 남긴다.
for s in $SERVICES; do
  sudo docker images --format '{{.Repository}}:{{.Tag}}' \
    | grep "^pigos-$s:rollback-" | sort -r | tail -n +$((KEEP_ROLLBACKS+1)) \
    | xargs -r -n1 sudo docker rmi 2>/dev/null || true
done

echo "✅ 배포 완료. 롤백 태그: rollback-$TS"
echo "   되돌리려면: ops/ROLLBACK.md 참조"
