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
#
# 종료코드: 0 전부 성공 · 1 로컬 실패 · 2 사용법 · 3 오프사이트 미구성 · 4 업로드 실패 · 5 원격 검증 실패
# 로그 토큰(grep 용): BACKUP_LOCAL_OK · BACKUP_LOCAL_FAILED · BACKUP_VERIFY_FAILED
#                     BACKUP_S3_OK · BACKUP_S3_FAILED · BACKUP_S3_SKIPPED
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
# DUMP_CMD: 테스트·비상용 명시 지정. 운영에서는 비워 둔다(아래 자동 탐색).
if [ -n "${DUMP_CMD:-}" ]; then
  read -r -a DUMP <<< "$DUMP_CMD"
  NATIVE="${DUMP_NATIVE:-1}"
elif [ -n "$PG17_BIN" ]; then
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
# ★ .part 로 쓰고 검증 후 이름을 바꾼다. 쓰는 도중의 파일이 최종 이름을 달고 있으면
#   "완료된 백업" 과 "쓰다 만 백업" 을 파일명으로 구분할 수 없다 — 복구 당일에 그 둘을
#   고르는 사람이 있다. 오래된 .part 는 아래 보존 정리에서 치운다.
PART="$OUT.part"
# --no-owner/--no-acl: Supabase 롤 구성이 복원 대상과 다를 수 있어 소유권을 빼둔다.
if ! "${DUMP[@]}" "$PGURL" --no-owner --no-acl "${ARGS[@]}" | gzip -9 > "$PART"; then
  echo "BACKUP_LOCAL_FAILED type=$MODE reason=pg_dump"; rm -f "$PART"; exit 1
fi

# 빈 덤프(연결은 됐는데 내용이 없는 경우)를 성공으로 넘기지 않는다.
LINES=$(gzip -dc "$PART" | head -50 | grep -c . || true)
if [ "$LINES" -lt 5 ]; then
  echo "BACKUP_LOCAL_FAILED type=$MODE reason=empty_dump"; rm -f "$PART"; exit 1
fi
# ── 산출물 검증 — 오프사이트로 보내기 전에, 그리고 최종 이름을 달기 전에 ───────────
# gzip 무결성이 깨진 파일을 올리면 오프사이트에도 쓰레기가 간다.
if ! gzip -t "$PART" 2>/dev/null; then
  echo "BACKUP_VERIFY_FAILED type=$MODE reason=gzip_integrity file=$PART"
  mv -f "$PART" "${OUT%.sql.gz}-CORRUPT.sql.gz" 2>/dev/null || true
  exit 1
fi
mv -f "$PART" "$OUT"
BYTES=$(stat -c %s "$OUT" 2>/dev/null || wc -c < "$OUT")
SHA256=$(sha256sum "$OUT" | cut -d' ' -f1)
printf '%s  %s\n' "$SHA256" "$(basename "$OUT")" > "$OUT.sha256"
SIZE=$(du -h "$OUT" | cut -f1)
echo "[$(date '+%F %T')] 완료 $SIZE"
echo "BACKUP_LOCAL_OK type=$MODE file=$(basename "$OUT") bytes=$BYTES sha256=$SHA256"

# ── 오프사이트 사본 (S3) ─────────────────────────────────────────────────────
# ★ 이게 없으면 백업이 원본과 같은 EBS 볼륨에만 있다. 인스턴스·볼륨 장애가 나면
#   DB 와 백업이 **같이** 사라진다. 2026-08-25 로컬 PG 이전 후 최대 위험 요소.
#
# ★ 2026-09-18 (B-10): 실패 의미론을 뒤집었다. 이전 판은 오프사이트 실패를 "⚠ 경고" 로
#   찍고 exit 0 으로 끝났다 — 그래서 2026-08-25 이후 22일간 업로드가 0건이어도 크론은
#   매일 성공이었다. 지금부터:
#     LOCAL 성공 + 오프사이트 실패  →  로컬 파일은 **보존**하되 종료코드는 실패
#   종료코드:  0 전부 성공 · 1 로컬 실패 · 2 사용법 · 3 오프사이트 미구성/CLI 없음
#              4 업로드 실패 · 5 원격 검증 실패
#   BACKUP_OFFSITE_REQUIRED=0 이면 3~5 를 경고로 낮춘다 — 개발 머신용. 운영 기본은 1.
#
# 활성화 조건: 버킷 + 이 EC2 의 PutObject/HeadObject 권한 + .env 의 BACKUP_S3_BUCKET.
S3_BUCKET=$(grep -E '^BACKUP_S3_BUCKET=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)
S3_PREFIX=$(grep -E '^BACKUP_S3_PREFIX=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)
S3_PREFIX="${S3_PREFIX:-pigos-db}"
OFFSITE_REQUIRED="${BACKUP_OFFSITE_REQUIRED:-1}"
# ★ 크론은 PATH 가 제한적이라(/usr/bin:/bin) CLI v2 의 /usr/local/bin 을 못 찾는다.
#   command -v 만 믿으면 손으로 돌릴 땐 되고 크론에서만 조용히 실패한다. 테스트는 AWS_BIN 으로 대역을 꽂는다.
AWS_BIN="${AWS_BIN:-$(command -v aws || echo /usr/local/bin/aws)}"
S3_KEY="$S3_PREFIX/$(basename "$OUT")"
OFFSITE_RC=0

offsite_fail() {  # <code> <token> <detail>
  OFFSITE_RC=$1
  echo "$2 type=$MODE file=$(basename "$OUT") key=$S3_KEY $3"
  echo "  로컬 백업은 보존됨: $OUT"
}

if [ -z "$S3_BUCKET" ]; then
  offsite_fail 3 BACKUP_S3_SKIPPED "reason=unconfigured (BACKUP_S3_BUCKET 미설정 — 백업이 이 EBS 볼륨에만 있음)"
elif [ ! -x "$AWS_BIN" ]; then
  offsite_fail 3 BACKUP_S3_FAILED "reason=aws_cli_missing bin=$AWS_BIN"
elif ! "$AWS_BIN" s3 cp "$OUT" "s3://$S3_BUCKET/$S3_KEY" --only-show-errors \
        --metadata "sha256=$SHA256,backup_type=$MODE"; then
  offsite_fail 4 BACKUP_S3_FAILED "reason=upload_error"
else
  # ★ 올렸다는 말을 믿지 않는다 — 원격 객체를 다시 읽어 크기를 대조한다.
  #   ETag 를 sha256 으로 쓰지 않는다: multipart 업로드에서는 같지 않다.
  REMOTE_BYTES=$("$AWS_BIN" s3api head-object --bucket "$S3_BUCKET" --key "$S3_KEY" \
                  --query ContentLength --output text 2>/dev/null || echo "")
  if [ "$REMOTE_BYTES" != "$BYTES" ]; then
    offsite_fail 5 BACKUP_VERIFY_FAILED "reason=remote_size_mismatch local=$BYTES remote=${REMOTE_BYTES:-none}"
  else
    # sidecar .sha256 — 복원 당일 로컬이 없을 때 오프사이트만으로 무결성을 확인할 수 있게
    "$AWS_BIN" s3 cp "$OUT.sha256" "s3://$S3_BUCKET/$S3_KEY.sha256" --only-show-errors 2>/dev/null \
      || echo "  주의: sha256 sidecar 업로드 실패 (본 파일은 검증됨)"
    echo "BACKUP_S3_OK type=$MODE file=$(basename "$OUT") bytes=$BYTES sha256=$SHA256 key=$S3_KEY"
  fi
fi

if [ "$OFFSITE_RC" -ne 0 ] && [ "$OFFSITE_REQUIRED" != "1" ]; then
  echo "  (BACKUP_OFFSITE_REQUIRED=0 — 오프사이트 실패를 경고로 낮춤)"
  OFFSITE_RC=0
fi

# 보존 정리 — deploy 태그가 붙은 것은 지우지 않는다(되돌릴 지점이라 오래 남긴다).
find "$BACKUP_DIR" -name 'pigos-*.sql.gz' ! -name '*-deploy.sql.gz' \
     -mtime +"$KEEP_DAYS" -print -delete 2>/dev/null || true
find "$BACKUP_DIR" -name 'pigos-*.sql.gz.sha256' -mtime +"$KEEP_DAYS" -delete 2>/dev/null || true
# 쓰다 만 .part 가 하루 넘게 남아 있으면 죽은 실행의 잔해다
find "$BACKUP_DIR" -name 'pigos-*.sql.gz.part' -mtime +1 -print -delete 2>/dev/null || true

echo "보관 현황:"; ls -lh "$BACKUP_DIR" | tail -8
# ★ 마지막 줄이 종료코드다. 로컬은 성공했어도 오프사이트가 실패면 크론에 실패로 보여야 한다.
exit "$OFFSITE_RC"
