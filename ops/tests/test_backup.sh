#!/usr/bin/env bash
# ops/backup_db.sh · ops/check_backup_freshness.sh 결정론 테스트 — 진짜 DB·진짜 S3 없이.
#
# 실행:  bash ops/tests/test_backup.sh
#
# 어떻게: PATH 앞에 대역 디렉터리를 두어 `pg_dump` 와 `aws` 를 가짜로 바꾼다.
#   가짜 aws 는 파일시스템 디렉터리(FAKE_S3)를 버킷처럼 쓰고, 환경변수로 실패를 주입한다.
#   실제 AWS 는 어떤 시나리오에서도 호출되지 않는다.
#
# ★ 이 파일이 지키는 것: "오프사이트 실패가 조용히 성공으로 끝나는 경로가 없다".
set -uo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OPS=$(cd "$HERE/.." && pwd)
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n       %s\n' "$1" "${2:-}"; }
check(){ # <name> <cond-exit> <detail>
  if [ "$2" -eq 0 ]; then ok "$1"; else bad "$1" "$3"; fi; }

# ── 대역 ────────────────────────────────────────────────────────────────────────
WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT
STUB="$WORK/bin"; mkdir -p "$STUB"
FAKE_S3="$WORK/s3"; mkdir -p "$FAKE_S3"

cat > "$STUB/pg_dump" <<'EOF'
#!/usr/bin/env bash
# 가짜 pg_dump: FAKE_DUMP_MODE=ok|fail|empty
case "${FAKE_DUMP_MODE:-ok}" in
  fail)  echo "pg_dump: connection refused" >&2; exit 1 ;;
  empty) echo "--"; exit 0 ;;
  *)     for i in $(seq 1 40); do echo "CREATE TABLE t$i (id int);"; done; exit 0 ;;
esac
EOF
cat > "$STUB/aws" <<'EOF'
#!/usr/bin/env bash
# 가짜 aws: FAKE_S3 디렉터리를 버킷으로 쓴다. FAKE_AWS_MODE=ok|upload_fail|head_mismatch|list_empty
mode="${FAKE_AWS_MODE:-ok}"
case "$1 $2" in
  "s3 cp")
    [ "$mode" = upload_fail ] && { echo "upload failed (simulated)" >&2; exit 1; }
    src="$3"; dst="$4"; key="${dst#s3://*/}"
    mkdir -p "$FAKE_S3/$(dirname "$key")"; cp "$src" "$FAKE_S3/$key"; exit 0 ;;
  "s3api head-object")
    key=""; while [ $# -gt 0 ]; do [ "$1" = --key ] && key="$2"; shift; done
    [ -f "$FAKE_S3/$key" ] || exit 1
    if [ "$mode" = head_mismatch ]; then echo 1; else stat -c %s "$FAKE_S3/$key"; fi; exit 0 ;;
  "s3api list-objects-v2")
    [ "$mode" = list_empty ] && exit 0
    prefix=""; while [ $# -gt 0 ]; do [ "$1" = --prefix ] && prefix="$2"; shift; done
    for f in "$FAKE_S3/$prefix"*; do [ -f "$f" ] || continue
      k="${f#$FAKE_S3/}"; ts=$(date -u -d @"$(stat -c %Y "$f")" +%Y-%m-%dT%H:%M:%S.000Z)
      printf '%s\t%s\n' "$ts" "$k"; done; exit 0 ;;
  *) echo "fake aws: unsupported $*" >&2; exit 2 ;;
esac
EOF
chmod +x "$STUB/pg_dump" "$STUB/aws"

ENVF="$WORK/.env"
printf 'DATABASE_URL=postgresql+asyncpg://u:p@172.18.0.1:5434/pigos\nBACKUP_S3_BUCKET=fake-bucket\nBACKUP_S3_PREFIX=pigos-db\n' > "$ENVF"
ENVF_NOS3="$WORK/.env.nos3"
printf 'DATABASE_URL=postgresql+asyncpg://u:p@172.18.0.1:5434/pigos\n' > "$ENVF_NOS3"

run_backup() {  # <mode> [env=value ...] → sets RC, OUTLOG, BDIR.  두 번째 인자(tag)는 BACKUP_TAG 변수로 준다
  local mode="$1"; shift
  BDIR="$WORK/backups-$RANDOM"; mkdir -p "$BDIR"
  OUTLOG=$(env PATH="$STUB:$PATH" BACKUP_DIR="$BDIR" ENV_FILE="${ENV_FILE_OVERRIDE:-$ENVF}" \
             DUMP_CMD="$STUB/pg_dump" AWS_BIN="$STUB/aws" FAKE_S3="$FAKE_S3" "$@" \
             bash "$OPS/backup_db.sh" "$mode" ${BACKUP_TAG:-} 2>&1); RC=$?
}
count_local() { ls "$BDIR"/pigos-*.sql.gz 2>/dev/null | wc -l; }
count_s3()    { ls "$FAKE_S3"/pigos-db/pigos-*.sql.gz 2>/dev/null | wc -l; }
reset_s3()    { rm -rf "$FAKE_S3"; mkdir -p "$FAKE_S3"; }

echo "backup_db.sh"

# 1  로컬 성공 + 오프사이트 성공 → exit 0
reset_s3; run_backup full
check "1 local ok + s3 ok → exit 0" $([ "$RC" -eq 0 ] && echo 0 || echo 1) "rc=$RC $OUTLOG"
check "1 tokens LOCAL_OK + S3_OK" $(grep -q BACKUP_LOCAL_OK <<<"$OUTLOG" && grep -q BACKUP_S3_OK <<<"$OUTLOG" && echo 0 || echo 1) "$OUTLOG"
check "1 sidecar .sha256 local + remote" $([ -f "$BDIR"/pigos-full-*.sql.gz.sha256 ] && ls "$FAKE_S3"/pigos-db/*.sha256 >/dev/null 2>&1 && echo 0 || echo 1) "$(ls -R "$BDIR" "$FAKE_S3")"
check "1 no .part left behind" $([ -z "$(ls "$BDIR"/*.part 2>/dev/null)" ] && echo 0 || echo 1)
check "1 sha256 in log matches file" $(f=$(ls "$BDIR"/pigos-full-*.sql.gz); s=$(sha256sum "$f"|cut -d' ' -f1); grep -q "sha256=$s" <<<"$OUTLOG" && echo 0 || echo 1)

# 2  로컬 dump 실패 → S3 호출 없음 · exit 1
reset_s3; run_backup full FAKE_DUMP_MODE=fail
check "2 dump fail → exit 1" $([ "$RC" -eq 1 ] && echo 0 || echo 1) "rc=$RC"
check "2 dump fail → no S3 call, no local file" $([ "$(count_s3)" -eq 0 ] && [ "$(count_local)" -eq 0 ] && echo 0 || echo 1)
check "2 token LOCAL_FAILED" $(grep -q BACKUP_LOCAL_FAILED <<<"$OUTLOG" && echo 0 || echo 1) "$OUTLOG"

# 3  빈 덤프 → exit 1, S3 없음
reset_s3; run_backup full FAKE_DUMP_MODE=empty
check "3 empty dump → exit 1, no S3" $([ "$RC" -eq 1 ] && [ "$(count_s3)" -eq 0 ] && echo 0 || echo 1) "rc=$RC"

# 4  S3 업로드 실패 → 로컬 보존 · exit 4
reset_s3; run_backup full FAKE_AWS_MODE=upload_fail
check "4 upload fail → exit 4" $([ "$RC" -eq 4 ] && echo 0 || echo 1) "rc=$RC $OUTLOG"
check "4 upload fail → local artifact preserved" $([ "$(count_local)" -eq 1 ] && echo 0 || echo 1)
check "4 token S3_FAILED + LOCAL_OK both present" $(grep -q BACKUP_S3_FAILED <<<"$OUTLOG" && grep -q BACKUP_LOCAL_OK <<<"$OUTLOG" && echo 0 || echo 1)

# 5  원격 검증 실패(크기 불일치) → 로컬 보존 · exit 5
reset_s3; run_backup full FAKE_AWS_MODE=head_mismatch
check "5 remote size mismatch → exit 5" $([ "$RC" -eq 5 ] && echo 0 || echo 1) "rc=$RC"
check "5 local preserved · token VERIFY_FAILED" $([ "$(count_local)" -eq 1 ] && grep -q BACKUP_VERIFY_FAILED <<<"$OUTLOG" && echo 0 || echo 1)

# 6  aws CLI 없음 → 로컬 보존 · exit 3
reset_s3; run_backup full AWS_BIN="$WORK/no-such-aws"
check "6 aws missing → exit 3, local preserved" $([ "$RC" -eq 3 ] && [ "$(count_local)" -eq 1 ] && echo 0 || echo 1) "rc=$RC"

# 6b 버킷 미구성 → exit 3 (조용히 지나가지 않는다)
reset_s3; ENV_FILE_OVERRIDE="$ENVF_NOS3" run_backup full; unset ENV_FILE_OVERRIDE
check "6b bucket unconfigured → exit 3 + S3_SKIPPED" $([ "$RC" -eq 3 ] && grep -q BACKUP_S3_SKIPPED <<<"$OUTLOG" && echo 0 || echo 1) "rc=$RC"

# 6c BACKUP_OFFSITE_REQUIRED=0 → 개발 머신에서만 경고로 낮춤
reset_s3; run_backup full FAKE_AWS_MODE=upload_fail BACKUP_OFFSITE_REQUIRED=0
check "6c offsite not required → exit 0 with warning" $([ "$RC" -eq 0 ] && grep -q "경고로 낮춤" <<<"$OUTLOG" && echo 0 || echo 1) "rc=$RC"

# 7  파일명·키 규약 유지
reset_s3; run_backup schema
f=$(basename "$(ls "$BDIR"/pigos-schema-*.sql.gz)")
check "7 filename pigos-schema-<ts>.sql.gz · key pigos-db/<same>" $(grep -Eq '^pigos-schema-[0-9]{8}-[0-9]{6}\.sql\.gz$' <<<"$f" && [ -f "$FAKE_S3/pigos-db/$f" ] && echo 0 || echo 1) "$f"
reset_s3; BACKUP_TAG=deploy run_backup full; unset BACKUP_TAG
f=$(basename "$(ls "$BDIR"/pigos-full-*-deploy.sql.gz)")
check "7 deploy tag preserved in key" $([ -f "$FAKE_S3/pigos-db/$f" ] && echo 0 || echo 1) "$f"

# ── freshness ──────────────────────────────────────────────────────────────────
echo "check_backup_freshness.sh"
run_fresh() {  # [env...] → RC, OUTLOG
  OUTLOG=$(env PATH="$STUB:$PATH" BACKUP_DIR="$BDIR" ENV_FILE="$ENVF" AWS_BIN="$STUB/aws" FAKE_S3="$FAKE_S3" "$@" \
             bash "$OPS/check_backup_freshness.sh" 2>&1); RC=$?
}
NOW=$(date +%s)

# 8  최근 로컬 + 최근 S3 → CURRENT / exit 0
reset_s3; run_backup full
run_fresh FRESH_NOW_EPOCH="$NOW"
check "8 recent local + recent s3 → CURRENT/CURRENT exit 0" $([ "$RC" -eq 0 ] && grep -q 'LOCAL=CURRENT' <<<"$OUTLOG" && grep -q 'S3=CURRENT' <<<"$OUTLOG" && echo 0 || echo 1) "$OUTLOG"

# 9  최근 로컬 + 오래된 S3 → STALE / exit 1  (S3 객체 mtime 을 40시간 전으로)
touch -d "@$((NOW - 40*3600))" "$FAKE_S3"/pigos-db/pigos-full-*.sql.gz
run_fresh FRESH_NOW_EPOCH="$NOW"
check "9 recent local + stale s3 → S3=STALE exit 1" $([ "$RC" -eq 1 ] && grep -q 'S3=STALE' <<<"$OUTLOG" && grep -q 'LOCAL=CURRENT' <<<"$OUTLOG" && echo 0 || echo 1) "$OUTLOG"

# 10 S3 객체 없음 → MISSING
reset_s3; run_fresh FRESH_NOW_EPOCH="$NOW"
check "10 no s3 object → S3=MISSING exit 1" $([ "$RC" -eq 1 ] && grep -q 'S3=MISSING' <<<"$OUTLOG" && echo 0 || echo 1) "$OUTLOG"

# 10b 임계값 한 곳에서 조정 — 40시간 전 객체도 48시간 임계면 CURRENT
reset_s3; run_backup full; touch -d "@$((NOW - 40*3600))" "$FAKE_S3"/pigos-db/pigos-full-*.sql.gz "$BDIR"/pigos-full-*.sql.gz
run_fresh FRESH_NOW_EPOCH="$NOW" FRESH_FULL_MAX_AGE_HOURS=48
check "10b threshold configurable (48h → CURRENT)" $([ "$RC" -eq 0 ] && echo 0 || echo 1) "$OUTLOG"

# 11 deploy 태그 백업은 신선도 판정에서 제외 (정기 잡의 신선도를 보는 것)
reset_s3; BACKUP_TAG=deploy run_backup full; unset BACKUP_TAG; run_fresh FRESH_NOW_EPOCH="$NOW"
check "11 deploy-tagged only → MISSING (regular job freshness)" $(grep -q 'LOCAL=MISSING' <<<"$OUTLOG" && grep -q 'S3=MISSING' <<<"$OUTLOG" && echo 0 || echo 1) "$OUTLOG"

# ── 비밀 누출 없음 ──────────────────────────────────────────────────────────────
reset_s3; run_backup full
check "12 log carries no credential" $(grep -qE 'u:p@|password|172\.18\.0\.1' <<<"$OUTLOG" && echo 1 || echo 0) "$OUTLOG"

echo
echo "passed=$PASS failed=$FAIL"
[ "$FAIL" -eq 0 ]
