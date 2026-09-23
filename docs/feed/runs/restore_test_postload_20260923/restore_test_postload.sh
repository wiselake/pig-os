#!/usr/bin/env bash
# Restore rehearsal #2 — POST-load dump (feed rows present). Isolated container, no ports, no api env, network none.
# post-load dump -> expect a7c9e1f3b5d7 + 5461 feed rows -> downgrade f3c6a8d0b2e4 -> upgrade a7c9e1f3b5d7 -> compare.
# Harness fixes from run #1: pg_temp schemas excluded from row counts; non-feed equality judged on fingerprint + non-feed rowcounts.
# Writes results to $OUT only. Always removes the container and volume at exit.
set -uo pipefail
umask 077
DUMP="$HOME/pigos-backups/pigos-full-20260923-110831-postload.sql.gz"
OUT="$HOME/restore_test_postload_20260923"
N=pigos-restoretest
V=pigos-restoretest-vol
IMG_PG=postgres:17-alpine
IMG_APP=pigos-feedload:854765a
BASE=f3c6a8d0b2e4
HEAD=a7c9e1f3b5d7
mkdir -p "$OUT"; chmod 700 "$OUT"
LOG="$OUT/run.log"
exec > >(tee -a "$LOG") 2>&1

cleanup() {
  echo "== cleanup $(date -u +%FT%TZ)"
  sudo docker rm -f "$N" >/dev/null 2>&1
  sudo docker volume rm "$V" >/dev/null 2>&1
  echo "container_left=$(sudo docker ps -a --format '{{.Names}}' | grep -c "^$N$")"
  echo "volume_left=$(sudo docker volume ls --format '{{.Name}}' | grep -c "^$V$")"
}
trap cleanup EXIT

echo "== start $(date -u +%FT%TZ)"
echo "dump $(basename "$DUMP") bytes=$(stat -c %s "$DUMP") sha256_16=$(sha256sum "$DUMP" | cut -c1-16)"
echo "disk_before $(df -Pm / | awk 'NR==2{print $4" MB free"}')"
echo "images pg=$IMG_PG app=$IMG_APP"

PW=$(openssl rand -hex 16)   # throwaway, never printed, dies with the container
sudo docker volume create "$V" >/dev/null
sudo docker run -d --name "$N" --network none --cpus 1 --memory 2g \
  -e POSTGRES_PASSWORD="$PW" -e POSTGRES_DB=pigos -v "$V":/var/lib/postgresql/data "$IMG_PG" >/dev/null || exit 10
for i in $(seq 1 60); do sudo docker exec "$N" pg_isready -U postgres -d pigos -q && break; sleep 1; done
echo "isolation network=$(sudo docker inspect -f '{{.HostConfig.NetworkMode}}' "$N") ports=$(sudo docker port "$N" | wc -l) env_keys=$(sudo docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$N" | cut -d= -f1 | sort | tr '\n' ' ')"

PSQL=(sudo docker exec -i "$N" psql -U postgres -d pigos -X -q -v ON_ERROR_STOP=1)
ALEMBIC() { sudo docker run --rm --network "container:$N" --cpus 1 --memory 1g \
  -e DATABASE_URL="postgresql+asyncpg://postgres:$PW@127.0.0.1:5432/pigos" "$IMG_APP" alembic "$@"; }

snap() {  # $1 = label. schema dump (hash + file) and exact row counts for every user table
  local L="$1"
  sudo docker exec "$N" pg_dump -U postgres -d pigos --schema-only --no-owner --no-acl \
    | grep -v '^\\restrict\|^\\unrestrict' > "$OUT/schema_$L.sql"
  "${PSQL[@]}" -At -c "SELECT version_num FROM alembic_version" > "$OUT/alembic_$L.txt"
  "${PSQL[@]}" -At > "$OUT/rowcounts_$L.tsv" <<'SQL'
DO $$ DECLARE r record; c bigint; BEGIN
  CREATE TEMP TABLE _rc(t text, n bigint);
  FOR r IN SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') AND schemaname NOT LIKE 'pg_temp%' LOOP
    EXECUTE format('SELECT count(*) FROM %I.%I', r.schemaname, r.tablename) INTO c;
    INSERT INTO _rc VALUES (r.schemaname||'.'||r.tablename, c);
  END LOOP; END $$;
SELECT t||E'\t'||n FROM _rc ORDER BY t;
SQL
  "${PSQL[@]}" -At -c "SELECT md5(string_agg(table_name||'.'||column_name||':'||data_type||':'||is_nullable, '|' ORDER BY table_name, column_name)) FROM information_schema.columns WHERE table_schema='public' AND table_name NOT IN ('feed_source_rows','feed_source_sync_runs')" > "$OUT/fp_nonfeed_$L.txt"
  echo "snap $L alembic=$(cat "$OUT/alembic_$L.txt") tables=$(wc -l < "$OUT/rowcounts_$L.tsv") rows_total=$(awk -F'\t' '{s+=$2} END{print s}' "$OUT/rowcounts_$L.tsv") schema_sha256_16=$(sha256sum "$OUT/schema_$L.sql" | cut -c1-16) fp_nonfeed=$(cat "$OUT/fp_nonfeed_$L.txt")"
}

echo "== restore $(date -u +%FT%TZ)"
T0=$(date +%s)
zcat "$DUMP" | "${PSQL[@]}" > "$OUT/restore_psql.txt" 2>&1; RC=$?
echo "restore_rc=$RC seconds=$(( $(date +%s) - T0 )) psql_output_lines=$(wc -l < "$OUT/restore_psql.txt")"
[ "$RC" -eq 0 ] || { echo "RESTORE FAILED — stop"; exit 11; }

snap s0_restored
[ "$(cat "$OUT/alembic_s0_restored.txt")" = "$HEAD" ] && echo "CHECK alembic_after_restore == $HEAD : PASS" || { echo "CHECK alembic_after_restore == $HEAD : FAIL"; exit 12; }
FR=$(awk -F'	' '$1=="public.feed_source_rows"{print $2}' "$OUT/rowcounts_s0_restored.tsv")
[ "$FR" = "5461" ] && echo "CHECK feed_source_rows after restore == 5461 : PASS" || echo "CHECK feed_source_rows after restore == 5461 : FAIL ($FR)"
echo "  sync_runs: $("${PSQL[@]}" -At -c "SELECT status||':'||rows_inserted FROM feed_source_sync_runs ORDER BY started_at" | paste -sd' ' -)"
echo "== downgrade (with data) $(date -u +%FT%TZ)"
ALEMBIC downgrade "$BASE" > "$OUT/alembic_downgrade.txt" 2>&1; echo "downgrade_rc=$?"
snap s1_downgraded
[ "$(cat "$OUT/alembic_s1_downgraded.txt")" = "$BASE" ] && echo "CHECK alembic_after_downgrade == $BASE : PASS" || echo "CHECK alembic_after_downgrade == $BASE : FAIL"
grep -c '^public\.feed_source' "$OUT/rowcounts_s1_downgraded.tsv" | sed 's/^/  feed tables present after downgrade: /'

echo "== upgrade $(date -u +%FT%TZ)"
ALEMBIC upgrade "$HEAD" > "$OUT/alembic_upgrade.txt" 2>&1; echo "upgrade_rc=$?"
snap s2_upgraded
[ "$(cat "$OUT/alembic_s2_upgraded.txt")" = "$HEAD" ] && echo "CHECK alembic_after_upgrade == $HEAD : PASS" || echo "CHECK alembic_after_upgrade == $HEAD : FAIL"

echo "== compare"
nf() { grep -v '^public\.feed_source_' "$1"; }
[ "$(nf "$OUT/rowcounts_s0_restored.tsv")" = "$(nf "$OUT/rowcounts_s1_downgraded.tsv")" ] && echo "CHECK non-feed rowcounts restored == downgraded : PASS ($(nf "$OUT/rowcounts_s0_restored.tsv" | wc -l) tables)" || echo "CHECK non-feed rowcounts restored == downgraded : FAIL"
[ "$(nf "$OUT/rowcounts_s0_restored.tsv")" = "$(nf "$OUT/rowcounts_s2_upgraded.tsv")" ] && echo "CHECK non-feed rowcounts restored == re-upgraded : PASS" || echo "CHECK non-feed rowcounts restored == re-upgraded : FAIL"
F0=$(cat "$OUT/fp_nonfeed_s0_restored.txt"); F1=$(cat "$OUT/fp_nonfeed_s1_downgraded.txt"); F2=$(cat "$OUT/fp_nonfeed_s2_upgraded.txt")
[ "$F0" = "$F1" ] && [ "$F1" = "$F2" ] && echo "CHECK non-feed fingerprint stable across down/up : PASS ($F0)" || echo "CHECK non-feed fingerprint stable : FAIL ($F0 $F1 $F2)"
if diff -u "$OUT/schema_s0_restored.sql" "$OUT/schema_s2_upgraded.sql" > "$OUT/diff_schema_s0_s2.txt"; then echo "CHECK schema restored == re-upgraded : PASS"; else echo "CHECK schema restored == re-upgraded : FAIL ($(grep -c '^[-+][^-+]' "$OUT/diff_schema_s0_s2.txt") lines)"; fi
echo "schema_sha256_16 s0=$(sha256sum "$OUT/schema_s0_restored.sql" | cut -c1-16) s1=$(sha256sum "$OUT/schema_s1_downgraded.sql" | cut -c1-16) s2=$(sha256sum "$OUT/schema_s2_upgraded.sql" | cut -c1-16)  (run #1: pre-migration 1881aa73d2200f66 · upgraded e09d6d821e3dee07)"
grep -E '^public\.feed_source_' "$OUT/rowcounts_s2_upgraded.tsv" | sed 's/^/  after re-upgrade (data is gone — the rollback cost): /'
echo "== end $(date -u +%FT%TZ)"
