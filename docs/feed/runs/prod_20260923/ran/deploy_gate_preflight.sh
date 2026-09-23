#!/usr/bin/env bash
# deploy.sh 0/5 게이트만 단독 실행 — 빌드·재시작·백업 없음. 양방향 확인.
set -u
umask 077
ROOT="$HOME/pigos"
echo "date_utc $(date -u +%FT%TZ)"
echo "installed_sha deploy.sh=$(sha256sum $ROOT/ops/deploy.sh|cut -c1-12) check_migration_drift.sh=$(sha256sum $ROOT/ops/check_migration_drift.sh|cut -c1-12) alembic_graph.py=$(sha256sum $ROOT/ops/alembic_graph.py|cut -c1-12)"
# deploy.sh 0/5 와 같은 방식으로 DB 리비전을 읽는다(읽기 전용 SELECT)
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
echo "db_revision ${DBREV:-<unknown>}"
echo "--- A: host checkout (old, $(ls $ROOT/api/alembic/versions/*.py | wc -l) revision files) — expect REFUSED"
"$ROOT/ops/check_migration_drift.sh" "$DBREV"; echo "exit_A $?"
echo "--- B: main 599dc55 versions ($(ls $1/*.py | wc -l) revision files) — expect PASS"
"$ROOT/ops/check_migration_drift.sh" "$DBREV" "$1"; echo "exit_B $?"
echo "--- C: empty DB revision — expect REFUSED"
"$ROOT/ops/check_migration_drift.sh" "None" "$1"; echo "exit_C $?"
