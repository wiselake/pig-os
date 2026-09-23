"""READ-ONLY production state for the feed initial load (aggregates only, no identifiers)."""
import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

Q = {
    "alembic_version": "SELECT version_num FROM alembic_version",
    "feed_source_tables": "SELECT count(*) FROM information_schema.tables WHERE table_name IN ('feed_source_rows','feed_source_sync_runs')",
    "feed_records": "SELECT count(*) FROM feed_records",
    "pp_farms_active": "SELECT count(*) FROM farms WHERE farm_code LIKE 'PP-%' AND active",
    "public_tables": "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'",
    "schema_fingerprint_non_feed": (
        "SELECT md5(string_agg(table_name||'.'||column_name||':'||data_type||':'||is_nullable, '|' ORDER BY table_name, column_name)) "
        "FROM information_schema.columns WHERE table_schema='public' AND table_name NOT IN ('feed_source_rows','feed_source_sync_runs')"),
}


async def main() -> None:
    eng = create_async_engine(os.environ["DATABASE_URL"])
    async with eng.connect() as c:
        await c.execute(text("SET TRANSACTION READ ONLY"))
        for k, sql in Q.items():
            print(k, (await c.execute(text(sql))).scalar())
    await eng.dispose()


asyncio.run(main())
