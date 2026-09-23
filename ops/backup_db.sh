#!/usr/bin/env bash
# PigOS 프로덕션 DB 백업.
#
# 왜 필요한가: 2026-08-24 배포 사고 때 롤백 이미지가 사라져 되돌릴 수단이 없었고,
# DB 백업 상태도 확인되지 않았다.
#
# ★ 2026-08-25 DB 이전: Supabase 풀러가 쿼리 도중 연결을 끊어(ConnectionDoesNotExist)
#   운영이 불가능해져 같은 EC2 의 로컬 PostgreSQL 17(포트 5434)로 옮겼다. 그러면서
#   백업 대상도 바뀐다 — Supabase 는 자체 백업이 1차 방어선이었지만 로컬 PG 는
#   **이 스크립트가 유일한 방어선**이다. 따라서 대상 선택 규칙을 뒤집었다:
#   "앱이 실제로 쓰는 DB(DATABASE_URL)를 백업한다"가 원칙이고, MIGRATION_DATABASE_URL
#   은 DATABASE_URL 이 덤프 불가능한 트랜잭션 모드일 때만 쓰는 대체 경로다.
#   (이전엔 MIGRATION 을 우선했는데, 이전 후 그 값이 죽은 Supabase 를 가리키는 바람에
#    라이브가 아닌 DB 를 백업할 뻔했다.)
#
# ★ 전송량: 로컬 PG 는 egress 가 없다. full 주기를 늘려도 비용이 들지 않는다.
#
# 사용:
#   ./backup_db.sh schema      스키마만 (수십 KB, 매일)
#   ./backup_db.sh full        전체 (약 100~150MB 압축, 주 1회/배포 직전)
#   ./backup_db.sh full deploy 배포 직전용 — 파일명에 표시하고 보존기간에서 제외
set -euo pipefail

MODE="${1:-full}"
TAG="${2:-}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/pigos-backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
ENV_FILE="${ENV_FILE:-$HOME/pigos/.env}"

mkdir -p "$BACKUP_DIR"

# DATABASE_URL 은 .env 에서만 읽는다 — 스크립트에 자격증명을 두지 않는다.
[ -f "$ENV_FILE" ] || { echo "ERROR: $ENV_FILE 없음"; exit 1; }
# ★ 대상 = 앱이 실제로 쓰는 DB. 백업이 라이브를 따라가지 못하면 백업이 아니다.
#   예외는 하나뿐이다: DATABASE_URL 이 트랜잭션 모드(6543)면 pg_dump 가 동작하지
#   않으므로 그때만 MIGRATION_DATABASE_URL(세션 모드)로 넘어간다.
#   (이전엔 MIGRATION 을 우선했는데, 2026-08-25 DB 이전 후 그 값이 죽은 Supabase 를
#    가리켜 라이브가 아닌 DB 를 백업할 뻔했다.)
# ★ `|| true` 필수: 키가 없으면 grep 이 1 을 반환하고, set -euo pipefail 아래에서
#   **아래 case 문(폴백·오류 안내)에 닿기도 전에 무출력으로 죽는다**
#   (독립검증 2026-08-25: stdout/stderr 0 byte, exit 1). 모니터링이 원인을 못 본다.
URL=$( { grep -E '^DATABASE_URL=' "$ENV_FILE" || true; } | head -1 | cut -d= -f2- | tr -d '"'"'"'')
case "$URL" in
  ''|*:6543/*)
    ALT=$( { grep -E '^MIGRATION_DATABASE_URL=' "$ENV_FILE" || true; } | head -1 | cut -d= -f2- | tr -d '"'"'"'')
    [ -n "$ALT" ] || { echo "ERROR: DATABASE_URL 이 덤프 불가(6543)인데 MIGRATION_DATABASE_URL 이 없습니다."; exit 1; }
    echo "  주의: DATABASE_URL 이 덤프 불가(6543) → MIGRATION_DATABASE_URL 로 대체"
    URL="$ALT" ;;
esac
[ -n "$URL" ] || { echo "ERROR: DATABASE_URL 미설정"; exit 1; }
case "$URL" in
  *:6543/*) echo "ERROR: 대체 URL 도 트랜잭션 모드(6543)입니다 — 세션 모드가 필요합니다."; exit 1 ;;
esac
# SQLAlchemy 드라이버 표기를 libpq 가 이해하는 형태로
PGURL=$(printf '%s' "$URL" | sed -E 's#\+asyncpg##; s#\?ssl=require#?sslmode=require#')

TS=$(date +%Y%m%d-%H%M%S)
SUFFIX="${TAG:+-$TAG}"
OUT="$BACKUP_DIR/pigos-$MODE-$TS$SUFFIX.sql.gz"

# 디스크 여유 확인 — full 은 넉넉히 1GB 는 있어야 안전하다.
AVAIL_MB=$(df -Pm "$BACKUP_DIR" | awk 'NR==2{print $4}')
NEED_MB=$([ "$MODE" = "full" ] && echo 1024 || echo 50)
if [ "$AVAIL_MB" -lt "$NEED_MB" ]; then
  echo "ERROR: 디스크 부족 (${AVAIL_MB}MB 남음, ${NEED_MB}MB 필요)"; exit 1
fi

case "$MODE" in
  schema) ARGS=(--schema-only) ;;
  full)   ARGS=() ;;
  *)      echo "usage: $0 {schema|full} [tag]"; exit 2 ;;
esac

# ★ pg_dump 는 서버보다 낮은 버전이면 거부한다(대상 = PG 17, 우분투 PATH 기본 = 16.x).
#   이 EC2 에는 PG16(다른 프로젝트)과 PG17(PigOS)이 함께 있어 PATH 의 pg_dump 가
#   16.13 이다. 버전별 바이너리를 직접 찾고, 없을 때만 컨테이너로 넘어간다.
PG_IMAGE="${PG_IMAGE:-postgres:17-alpine}"
# ★ `|| true` 필수: 두 glob 중 하나만 존재해도 ls 는 2 를 반환하고,
#   set -euo pipefail 아래에서 그대로 스크립트가 죽는다(실측 2026-08-25).
PG17_BIN=$( { ls -d /usr/lib/postgresql/1[7-9]/bin/pg_dump /usr/lib/postgresql/2*/bin/pg_dump 2>/dev/null || true; } | sort -V | tail -1)
if [ -n "$PG17_BIN" ]; then
  DUMP=("$PG17_BIN")
elif command -v pg_dump >/dev/null 2>&1 &&    [ "$(pg_dump --version | grep -oE '[0-9]+' | head -1)" -ge 17 ]; then
  DUMP=(pg_dump)
else
  sudo docker image inspect "$PG_IMAGE" >/dev/null 2>&1 || sudo docker pull -q "$PG_IMAGE"
  DUMP=(sudo docker run --rm -i "$PG_IMAGE" pg_dump)
  NATIVE=0
fi
: "${NATIVE:=1}"

# ★ .env 의 DATABASE_URL 은 **컨테이너 기준** 주소다(도커 브리지 게이트웨이 172.1x.0.1).
#   호스트에서 네이티브 pg_dump 로 붙으면 출발지가 EC2 사설 IP(172.31.x.x)라
#   pg_hba 에 안 걸린다. pg_hba 를 넓히는 대신 호스트에서는 루프백으로 붙는다
#   — 같은 서버의 같은 인스턴스이고, 접근 범위를 늘리지 않는다.
if [ "$NATIVE" = "1" ]; then
  PGURL=$(printf '%s' "$PGURL" | sed -E 's#@172\.1[6-9]\.0\.1:#@127.0.0.1:#; s#@172\.2[0-9]\.0\.1:#@127.0.0.1:#')
fi

echo "[$(date '+%F %T')] $MODE 백업 시작 → $OUT"
echo "  덤프 도구: ${DUMP[*]}"
# --no-owner/--no-acl: Supabase 롤 구성이 복원 대상과 다를 수 있어 소유권을 빼둔다.
if ! "${DUMP[@]}" "$PGURL" --no-owner --no-acl "${ARGS[@]}" | gzip -9 > "$OUT"; then
  echo "ERROR: pg_dump 실패"; rm -f "$OUT"; exit 1
fi

SIZE=$(du -h "$OUT" | cut -f1)
# 빈 덤프(연결은 됐는데 내용이 없는 경우)를 성공으로 넘기지 않는다.
LINES=$(gzip -dc "$OUT" | head -50 | grep -c . || true)
if [ "$LINES" -lt 5 ]; then
  echo "ERROR: 덤프 내용이 비정상적으로 적음 — 실패로 처리"; rm -f "$OUT"; exit 1
fi
echo "[$(date '+%F %T')] 완료 $SIZE"

# ── 오프사이트 사본 (S3) ─────────────────────────────────────────────────────
# ★ 이게 없으면 백업이 원본과 같은 EBS 볼륨에만 있다. 인스턴스·볼륨 장애가 나면
#   DB 와 백업이 **같이** 사라진다. 2026-08-25 로컬 PG 이전 후 최대 위험 요소.
#
# 활성화 조건(둘 다 대표 승인 필요 — AWS 리소스 생성):
#   1) S3 버킷 생성 (버전관리 + 수명주기 권장)
#   2) 이 EC2 가 s3:PutObject 할 수 있는 IAM 인스턴스 역할 또는 자격증명
#   3) .env 에 BACKUP_S3_BUCKET=<버킷명> (선택: BACKUP_S3_PREFIX)
#
# 셋 중 하나라도 없으면 **조용히 건너뛰지 않고 경고**한다 — 오프사이트 사본이
# 없다는 사실이 로그에서 보이지 않으면 있다고 착각하게 된다.
S3_BUCKET=$(grep -E '^BACKUP_S3_BUCKET=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)
S3_PREFIX=$(grep -E '^BACKUP_S3_PREFIX=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)
S3_PREFIX="${S3_PREFIX:-pigos-db}"
# ★ 크론은 PATH 가 제한적이라(/usr/bin:/bin) aws CLI v2 의 /usr/local/bin 을 못 찾는다.
#   command -v 만 믿으면 손으로 돌릴 땐 되고 크론에서만 조용히 실패한다.
AWS_BIN=$(command -v aws || echo /usr/local/bin/aws)
if [ -z "$S3_BUCKET" ]; then
  echo "  ⚠ 오프사이트 사본 없음 — BACKUP_S3_BUCKET 미설정 (백업이 이 EBS 볼륨에만 있음)"
elif [ ! -x "$AWS_BIN" ]; then
  echo "  ⚠ 오프사이트 사본 실패 — aws CLI 없음 ($AWS_BIN)"
elif ! "$AWS_BIN" s3 cp "$OUT" "s3://$S3_BUCKET/$S3_PREFIX/$(basename "$OUT")" --only-show-errors; then
  echo "  ⚠ 오프사이트 사본 실패 — S3 업로드 오류(자격증명·권한 확인)"
else
  echo "  오프사이트 사본 OK → s3://$S3_BUCKET/$S3_PREFIX/$(basename "$OUT")"
fi

# 보존 정리 — deploy 태그가 붙은 것은 지우지 않는다(되돌릴 지점이라 오래 남긴다).
find "$BACKUP_DIR" -name 'pigos-*.sql.gz' ! -name '*-deploy.sql.gz' \
     -mtime +"$KEEP_DAYS" -print -delete 2>/dev/null || true

echo "보관 현황:"; ls -lh "$BACKUP_DIR" | tail -8
