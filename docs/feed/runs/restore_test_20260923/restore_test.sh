#!/usr/bin/env bash
# Restore rehearsal — isolated container, no ports, no api env, no network (network none).
# pre-load dump -> expect f3c6a8d0b2e4 -> upgrade a7c9e1f3b5d7 -> downgrade f3c6a8d0b2e4 -> compare with the restored original.
# Writes results to $OUT only. Always removes the container and volume at exit.
set -uo pipefail
umask 077
DUMP="$HOME/pigos-backups/pigos-full-20260923-091859-feedload-initial-load.sql.gz"
OUT="$HOME/restore_test_20260923"
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
  FOR r IN SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') LOOP
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
[ "$(cat "$OUT/alembic_s0_restored.txt")" = "$BASE" ] && echo "CHECK alembic_after_restore == $BASE : PASS" || { echo "CHECK alembic_after_restore == $BASE : FAIL"; exit 12; }

echo "== upgrade $(date -u +%FT%TZ)"
ALEMBIC upgrade "$HEAD" > "$OUT/alembic_upgrade.txt" 2>&1; echo "upgrade_rc=$?"
snap s1_upgraded
[ "$(cat "$OUT/alembic_s1_upgraded.txt")" = "$HEAD" ] && echo "CHECK alembic_after_upgrade == $HEAD : PASS" || echo "CHECK alembic_after_upgrade == $HEAD : FAIL"
grep -E '^public\.feed_source_(rows|sync_runs)\s' "$OUT/rowcounts_s1_upgraded.tsv" | sed 's/^/  /'

echo "== downgrade $(date -u +%FT%TZ)"
ALEMBIC downgrade "$BASE" > "$OUT/alembic_downgrade.txt" 2>&1; echo "downgrade_rc=$?"
snap s2_downgraded
[ "$(cat "$OUT/alembic_s2_downgraded.txt")" = "$BASE" ] && echo "CHECK alembic_after_downgrade == $BASE : PASS" || echo "CHECK alembic_after_downgrade == $BASE : FAIL"

echo "== compare s0_restored vs s2_downgraded"
if diff -u "$OUT/schema_s0_restored.sql" "$OUT/schema_s2_downgraded.sql" > "$OUT/diff_schema_s0_s2.txt"; then echo "CHECK schema identical : PASS"; else echo "CHECK schema identical : FAIL ($(grep -c '^[-+][^-+]' "$OUT/diff_schema_s0_s2.txt") changed lines)"; fi
if diff -u "$OUT/rowcounts_s0_restored.tsv" "$OUT/rowcounts_s2_downgraded.tsv" > "$OUT/diff_rowcounts_s0_s2.txt"; then echo "CHECK rowcounts identical : PASS"; else echo "CHECK rowcounts identical : FAIL"; fi
echo "== compare s0_restored vs s1_upgraded (expected: only the two feed tables + alembic)"
diff -u "$OUT/schema_s0_restored.sql" "$OUT/schema_s1_upgraded.sql" > "$OUT/diff_schema_s0_s1.txt"
echo "s0_s1 schema changed lines=$(grep -c '^[-+][^-+]' "$OUT/diff_schema_s0_s1.txt") non_feed_changed=$(grep '^[-+][^-+]' "$OUT/diff_schema_s0_s1.txt" | grep -vc 'feed_source\|fsr_\|fssr_')"
diff "$OUT/rowcounts_s0_restored.tsv" "$OUT/rowcounts_s1_upgraded.tsv" > "$OUT/diff_rowcounts_s0_s1.txt"; echo "s0_s1 rowcount diff:"; sed 's/^/  /' "$OUT/diff_rowcounts_s0_s1.txt"
[ "$(cat "$OUT/fp_nonfeed_s0_restored.txt")" = "$(cat "$OUT/fp_nonfeed_s1_upgraded.txt")" ] && echo "CHECK non-feed fingerprint unchanged by upgrade : PASS" || echo "CHECK non-feed fingerprint unchanged by upgrade : FAIL"
echo "== end $(date -u +%FT%TZ)"
