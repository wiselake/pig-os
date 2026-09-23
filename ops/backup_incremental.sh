#!/usr/bin/env bash
# PigOS 증분 백업 — 전체 덤프 사이의 시간 간격을 메운다.
#
# 왜 필요한가: 2026-08-25 DB 이전 후 DB 는 같은 EC2 의 로컬 PostgreSQL 이고,
# **자동 백업이 전혀 없다.** ops/backup_db.sh 가 유일한 방어선이다.
#
# ★ 전제 변경: 원래 이 스크립트는 Supabase Free egress 쿼터(5GB) 때문에 존재했다.
#   전체 덤프가 원본 825MB 를 전송해 매일 돌리면 쿼터를 5배 초과했으므로 매일은
#   변경분만 받았다. 로컬 PG 는 egress 가 없어 그 제약이 사라졌고, 전체 덤프를
#   매일 돌린다(ops/deploy.sh·crontab). 증분은 이제 "매일 사이"를 메우는 역할이다 —
#   전체가 하루 1회면 최악 24시간이 날아가는데, 증분이 그 창을 좁힌다.
#
# ★ created_at/updated_at 컬럼이 있는 테이블을 자동 탐색한다. 테이블 목록을 하드코딩하면
#   새 테이블이 생겼을 때 조용히 백업에서 빠진다.
# ★ 복원은 CSV → COPY 로 수동이다. 전체 덤프로 뼈대를 세우고 증분을 얹는 순서.
#   절차는 ops/ROLLBACK.md §E-3 참조.
# ★ 한계(반드시 인지): 증분 CSV 는 **삭제된 행을 표현하지 못한다.** 시점 컬럼 기준
#   SELECT 라 지워진 행은 애초에 안 잡힌다. 전체 덤프 이후 삭제된 데이터는 증분을
#   얹어도 되살아난다 — 증분은 "유실 창을 좁히는 보조 수단"이지 완전 복원 수단이 아니다.
#
# 사용:  ./backup_incremental.sh [일수]     기본 3일(겹치게 받아 누락 방지)
set -euo pipefail

DAYS="${1:-3}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/pigos-backups}"
INC_DIR="$BACKUP_DIR/incremental"
KEEP_DAYS="${KEEP_INC_DAYS:-14}"
ENV_FILE="${ENV_FILE:-$HOME/pigos/.env}"
PG_IMAGE="${PG_IMAGE:-postgres:17-alpine}"

mkdir -p "$INC_DIR"
[ -f "$ENV_FILE" ] || { echo "ERROR: $ENV_FILE 없음"; exit 1; }
# ★ 대상 = 앱이 실제로 쓰는 DB(DATABASE_URL). 백업이 라이브를 따라가지 못하면 백업이 아니다.
#   DATABASE_URL 이 덤프 불가능한 트랜잭션 모드(6543)일 때만 MIGRATION_DATABASE_URL 로 넘어간다.
# ★ `|| true` 필수: 키가 없으면 grep 이 1 을 반환하고, set -euo pipefail 아래에서
#   **아래 case 문(폴백·오류 안내)에 닿기도 전에 무출력으로 죽는다**
#   (독립검증 2026-08-25: stdout/stderr 0 byte, exit 1). 모니터링이 원인을 못 본다.
URL=$( { grep -E '^DATABASE_URL=' "$ENV_FILE" || true; } | head -1 | cut -d= -f2- | tr -d '"'"'"'')
case "$URL" in
  ''|*:6543/*)
    ALT=$( { grep -E '^MIGRATION_DATABASE_URL=' "$ENV_FILE" || true; } | head -1 | cut -d= -f2- | tr -d '"'"'"'')
    [ -n "$ALT" ] || { echo "ERROR: DATABASE_URL 이 덤프 불가(6543)인데 MIGRATION_DATABASE_URL 이 없습니다."; exit 1; }
    URL="$ALT" ;;
esac
[ -n "$URL" ] || { echo "ERROR: DATABASE_URL 미설정"; exit 1; }
# full 스크립트에만 있던 검사 — 대체 URL 도 트랜잭션 모드면 덤프가 안 된다.
case "$URL" in
  *:6543/*) echo "ERROR: 대체 URL 도 트랜잭션 모드(6543)입니다 — 세션 모드가 필요합니다."; exit 1 ;;
esac
PGURL=$(printf '%s' "$URL" | sed -E 's#\+asyncpg##; s#\?ssl=require#?sslmode=require#')

sudo docker image inspect "$PG_IMAGE" >/dev/null 2>&1 || sudo docker pull -q "$PG_IMAGE"
PSQL=(sudo docker run --rm -i "$PG_IMAGE" psql "$PGURL" -qtAX)

TS=$(date +%Y%m%d-%H%M%S)
OUT="$INC_DIR/inc-$TS.tar.gz"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

echo "[$(date '+%F %T')] 증분 백업 (최근 ${DAYS}일)"

# 시점 컬럼이 있는 테이블 자동 탐색 — updated_at 우선(수정도 잡아야 한다)
TABLES=$("${PSQL[@]}" -c "
  SELECT c.table_name || ':' ||
         CASE WHEN bool_or(c.column_name='updated_at') THEN 'updated_at' ELSE 'created_at' END
  FROM information_schema.columns c
  JOIN information_schema.tables t
    ON t.table_name = c.table_name AND t.table_schema = c.table_schema
  WHERE c.table_schema='public' AND t.table_type='BASE TABLE'
    AND c.column_name IN ('created_at','updated_at')
  GROUP BY c.table_name ORDER BY 1")

[ -n "$TABLES" ] || { echo "ERROR: 시점 컬럼 있는 테이블을 못 찾음"; exit 1; }

TOTAL=0
FAILED=""
for entry in $TABLES; do
  tbl="${entry%%:*}"; col="${entry##*:}"
  f="$WORK/$tbl.csv"
  if ! "${PSQL[@]}" -c "\\copy (SELECT * FROM public.$tbl WHERE $col >= now() - interval '$DAYS days') TO STDOUT WITH CSV HEADER" > "$f" 2>/dev/null; then
    # ★ 건너뛰고 계속하되 **실패를 기억한다.** 예전엔 그냥 continue 해서, 한 테이블이
    #   통째로 빠진 백업이 exit 0 으로 끝나 모니터링이 정상으로 봤다
    #   (독립검증 2026-08-25). 부분 백업을 정상으로 착각하는 게 백업 없는 것보다 위험하다.
    echo "  ⚠ $tbl 건너뜀(조회 실패)"; rm -f "$f"; FAILED="$FAILED $tbl"; continue
  fi
  rows=$(( $(wc -l < "$f") - 1 ))
  if [ "$rows" -le 0 ]; then rm -f "$f"; continue
  fi
  TOTAL=$((TOTAL + rows))
  printf "  %-28s %6d행 (%s)\n" "$tbl" "$rows" "$col"
done

if [ -n "$FAILED" ]; then
  echo "ERROR: 조회 실패 테이블이 있어 **불완전한 증분 백업**입니다:$FAILED"
  echo "       이 아카이브는 복원에 쓸 수 없습니다. 원인을 확인한 뒤 다시 실행하십시오."
fi

if [ "$TOTAL" -eq 0 ]; then
  echo "  변경분 없음 — 파일 생성 생략"
  [ -z "$FAILED" ] || exit 1
  exit 0
fi

tar -czf "$OUT" -C "$WORK" .
echo "[$(date '+%F %T')] 완료 $(du -h "$OUT" | cut -f1) / 총 ${TOTAL}행"

# ── 오프사이트 사본 (S3) — backup_db.sh 와 동일 규칙 ─────────────────────────
# 증분이야말로 오프사이트가 중요하다: 전체 덤프 사이의 하루치가 여기에만 있다.
S3_BUCKET=$(grep -E '^BACKUP_S3_BUCKET=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)
S3_PREFIX=$(grep -E '^BACKUP_S3_PREFIX=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)
S3_PREFIX="${S3_PREFIX:-pigos-db}"
AWS_BIN=$(command -v aws || echo /usr/local/bin/aws)
if [ -z "$S3_BUCKET" ]; then
  echo "  ⚠ 오프사이트 사본 없음 — BACKUP_S3_BUCKET 미설정"
elif [ ! -x "$AWS_BIN" ]; then
  echo "  ⚠ 오프사이트 사본 실패 — aws CLI 없음"
elif ! "$AWS_BIN" s3 cp "$OUT" "s3://$S3_BUCKET/$S3_PREFIX/incremental/$(basename "$OUT")" --only-show-errors; then
  echo "  ⚠ 오프사이트 사본 실패 — S3 업로드 오류(자격증명·권한 확인)"
else
  echo "  오프사이트 사본 OK → s3://$S3_BUCKET/$S3_PREFIX/incremental/$(basename "$OUT")"
fi

find "$INC_DIR" -name 'inc-*.tar.gz' -mtime +"$KEEP_DAYS" -print -delete 2>/dev/null || true

# ★ 불완전 백업은 파일을 남기되(부분이라도 있는 게 낫다) **exit 1** 로 끝낸다.
#   파일명에도 표시해 복원 때 실수로 쓰지 않게 한다.
if [ -n "$FAILED" ]; then
  mv "$OUT" "${OUT%.tar.gz}-INCOMPLETE.tar.gz" 2>/dev/null || true
  echo "  → ${OUT%.tar.gz}-INCOMPLETE.tar.gz 로 표시했습니다."
  exit 1
fi
