#!/usr/bin/env bash
# PigOS 백업 신선도 검사 — 읽기 전용.
#
# 왜 필요한가 (B-10, 2026-09-18): 오프사이트 업로드가 2026-08-25 이후 22일간 0건이었는데
# 아무도 몰랐다. 백업 잡 자체보다 "아무도 신선도를 확인하지 않았다" 가 사고의 본질이다.
# 이 스크립트는 로컬과 오프사이트의 **최신 full 백업 나이**를 재고 판정만 한다.
# 아무것도 만들거나 지우지 않는다.
#
# 사용:  ./check_backup_freshness.sh            (설정은 .env + 환경변수)
# 판정:  CURRENT   최신 full 이 임계 안
#        STALE     있으나 임계보다 오래됨
#        MISSING   없음
# 종료:  0 로컬·오프사이트 둘 다 CURRENT · 1 그 외
#
# ★ 임계값은 한 곳(FRESH_FULL_MAX_AGE_HOURS)에만 있다. 운영 주기가 하루 1회(03:40)라
#   기본 36시간 — 하루 놓치면 STALE. 여러 파일에 숫자를 흩뿌리지 않는다.
# ★ 이번 단계에서는 크론에 넣지 않는다. 스케줄링은 운영 적용 승인 때 정한다.
set -uo pipefail

BACKUP_DIR="${BACKUP_DIR:-$HOME/pigos-backups}"
ENV_FILE="${ENV_FILE:-$HOME/pigos/.env}"
MAX_AGE_H="${FRESH_FULL_MAX_AGE_HOURS:-36}"
NOW="${FRESH_NOW_EPOCH:-$(date +%s)}"          # 테스트가 "지금" 을 고정할 수 있게
AWS_BIN="${AWS_BIN:-$(command -v aws || echo /usr/local/bin/aws)}"

S3_BUCKET=$( { grep -E '^BACKUP_S3_BUCKET=' "$ENV_FILE" 2>/dev/null || true; } | head -1 | cut -d= -f2- | tr -d '"')
S3_PREFIX=$( { grep -E '^BACKUP_S3_PREFIX=' "$ENV_FILE" 2>/dev/null || true; } | head -1 | cut -d= -f2- | tr -d '"')
S3_PREFIX="${S3_PREFIX:-pigos-db}"
MAX_AGE_S=$((MAX_AGE_H * 3600))

judge() {  # <epoch or empty> → CURRENT|STALE|MISSING
  local ts="$1"
  [ -n "$ts" ] || { echo MISSING; return; }
  [ $((NOW - ts)) -le "$MAX_AGE_S" ] && echo CURRENT || echo STALE
}
age_h() { [ -n "$1" ] && echo $(( (NOW - $1) / 3600 )) || echo "-"; }

# ── 로컬 최신 full (deploy 태그 제외 — 정기 잡의 신선도를 보는 것이다) ─────────────
LOCAL_LATEST=$(ls -t "$BACKUP_DIR"/pigos-full-*.sql.gz 2>/dev/null | grep -v -- '-deploy.sql.gz' | head -1 || true)
LOCAL_TS=""; [ -n "$LOCAL_LATEST" ] && LOCAL_TS=$(stat -c %Y "$LOCAL_LATEST" 2>/dev/null || echo "")
LOCAL_STATE=$(judge "$LOCAL_TS")

# ── 오프사이트 최신 full ────────────────────────────────────────────────────────
S3_STATE="MISSING"; S3_TS=""; S3_KEY=""
if [ -z "$S3_BUCKET" ]; then
  S3_DETAIL="reason=unconfigured"
elif [ ! -x "$AWS_BIN" ]; then
  S3_DETAIL="reason=aws_cli_missing"
else
  # LastModified 가 가장 큰 pigos-full-* 객체 하나. deploy 태그는 제외.
  LINE=$("$AWS_BIN" s3api list-objects-v2 --bucket "$S3_BUCKET" --prefix "$S3_PREFIX/pigos-full-" \
          --query 'Contents[].[LastModified,Key]' --output text 2>/dev/null \
          | grep -v -- '-deploy.sql.gz' | grep -v '\.sha256$' | sort | tail -1 || true)
  if [ -n "$LINE" ]; then
    S3_KEY=$(printf '%s' "$LINE" | awk '{print $2}')
    S3_TS=$(date -d "$(printf '%s' "$LINE" | awk '{print $1}')" +%s 2>/dev/null || echo "")
  fi
  S3_STATE=$(judge "$S3_TS")
  S3_DETAIL="key=${S3_KEY:-none}"
fi

echo "BACKUP_FRESHNESS_LOCAL=$LOCAL_STATE age_h=$(age_h "$LOCAL_TS") file=$(basename "${LOCAL_LATEST:-none}") max_age_h=$MAX_AGE_H"
echo "BACKUP_FRESHNESS_S3=$S3_STATE age_h=$(age_h "$S3_TS") $S3_DETAIL max_age_h=$MAX_AGE_H"

if [ "$LOCAL_STATE" = CURRENT ] && [ "$S3_STATE" = CURRENT ]; then
  echo "BACKUP_FRESHNESS_OK"; exit 0
fi
echo "BACKUP_FRESHNESS_FAILED local=$LOCAL_STATE s3=$S3_STATE"
exit 1
