#!/usr/bin/env bash
# =====================================================================================
# Feed PHASE 0 — coverage audit runner (staging / local ONLY)
# =====================================================================================
# 사용:
#   scripts/run_feed_audit.sh                       # $DATABASE_URL (또는 PSQL_CMD) 대상, READ-ONLY 감사
#   scripts/run_feed_audit.sh --synthetic           # 로컬 docker 에 scratch DB 를 복제해 합성 fixture 로 하네스 검증
#   scripts/run_feed_audit.sh --out path/report.txt
#
# 대상 결정:
#   PSQL_CMD      psql 을 부르는 명령 (기본: 로컬 docker → "docker exec -i pigos-postgres psql -U pigos")
#   DATABASE_URL  postgresql://user:pass@host:port/db  — PSQL_CMD 미설정 시 psql 이 PATH 에 있어야 한다
#
# ★ 프로덕션 금지 (결재 5 미승인). 아래 호스트 패턴이면 실행하지 않고 종료한다. 우회 플래그 없음.
#   - 52.78.65.6 · api.pigos.io · *.rds.amazonaws.com · pigos-prod
# ★ 쓰기 없음: 감사 SQL 은 BEGIN READ ONLY 안에서 돈다. --synthetic 만 scratch DB(별도 이름) 를 만들고 끝에 지운다.
# =====================================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUDIT_SQL="$HERE/feed_coverage_audit.sql"
FIXTURE_SQL="$HERE/feed_audit_fixture_synthetic.sql"

MODE="target"
OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --synthetic) MODE="synthetic"; shift ;;
    --out) OUT="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

PROD_PATTERN='52\.78\.65\.6|api\.pigos\.io|rds\.amazonaws\.com|pigos-prod'
if [[ "${DATABASE_URL:-}${PSQL_CMD:-}" =~ $PROD_PATTERN ]]; then
  echo "REFUSED: target looks like production (결재 5 미승인 — 프로덕션 읽기 금지)" >&2
  exit 3
fi

# psql 호출 방법
if [[ -n "${PSQL_CMD:-}" ]]; then
  PSQL=( $PSQL_CMD )
elif [[ -n "${DATABASE_URL:-}" ]]; then
  command -v psql >/dev/null || { echo "psql not in PATH; set PSQL_CMD" >&2; exit 2; }
  # asyncpg URL 을 libpq 형식으로
  PSQL=( psql "${DATABASE_URL/postgresql+asyncpg:/postgresql:}" )
else
  PSQL=( docker exec -i pigos-postgres psql -U pigos )
fi

DB="pigos"
if [[ -n "${DATABASE_URL:-}" && -z "${PSQL_CMD:-}" ]]; then
  DB="${DATABASE_URL##*/}"; DB="${DB%%\?*}"
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ -z "$OUT" ]]; then
  mkdir -p "$HERE/../docs/feed/reports"
  OUT="$HERE/../docs/feed/reports/feed_audit_${MODE}_${STAMP}.txt"
fi

cleanup() { :; }
SCRATCH=""
if [[ "$MODE" == "synthetic" ]]; then
  SCRATCH="pigos_feedaudit_$(date +%s)"
  # TEMPLATE 복제는 원본에 접속이 없어야 한다 → 실패하면 alembic 으로 빈 스키마를 만든다
  if ! "${PSQL[@]}" -d postgres -v ON_ERROR_STOP=1 -qc "CREATE DATABASE $SCRATCH TEMPLATE $DB" 2>/dev/null; then
    "${PSQL[@]}" -d postgres -v ON_ERROR_STOP=1 -qc "CREATE DATABASE $SCRATCH"
    echo "NOTE: TEMPLATE copy refused (active connections?) — scratch DB is empty; apply schema first" >&2
  fi
  cleanup() { "${PSQL[@]}" -d postgres -qc "DROP DATABASE IF EXISTS $SCRATCH" >/dev/null 2>&1 || true; }
  trap cleanup EXIT
  DB="$SCRATCH"
  "${PSQL[@]}" -d "$DB" -v ON_ERROR_STOP=1 -q -f - < "$FIXTURE_SQL"
fi

# 헤더 — 대상 식별 (비밀번호는 절대 출력하지 않는다)
TARGET_DESC="${DATABASE_URL:-}"
TARGET_DESC="${TARGET_DESC//:\/\/*@/://***@}"   # user:pass@ → ***@
[[ -z "$TARGET_DESC" ]] && TARGET_DESC="${PSQL_CMD:-docker exec pigos-postgres (local)}"
ALEMBIC="$("${PSQL[@]}" -d "$DB" -tAc "SELECT version_num FROM alembic_version" 2>/dev/null | tr -d '[:space:]' || echo "n/a")"

{
  echo "# Feed PHASE 0 coverage audit"
  echo "generated_utc: $STAMP"
  echo "mode:          $MODE   $( [[ $MODE == synthetic ]] && echo '(★ SYNTHETIC fixture — no real-farm conclusion may be drawn)' )"
  echo "target:        $TARGET_DESC  db=$DB"
  echo "alembic:       $ALEMBIC"
  echo "audit_sql:     $(git -C "$HERE/.." rev-parse --short HEAD 2>/dev/null || echo n/a)  scripts/feed_coverage_audit.sql"
  echo "thresholds:    docs/feed/PHASE0_AUDIT_PLAN.md (judgement is made there, not here)"
  echo
  "${PSQL[@]}" -d "$DB" -v ON_ERROR_STOP=1 -f - < "$AUDIT_SQL"
} | tee "$OUT"

echo
echo "report: $OUT"
