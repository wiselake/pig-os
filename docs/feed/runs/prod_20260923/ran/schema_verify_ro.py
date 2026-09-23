"""READ-ONLY schema verification after migration a7c9e1f3b5d7."""
import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

EXPECTED_INDEXES = {"uq_fsr_identity_current", "idx_fsr_farm_basis_date", "idx_fssr_source_started",
                    "uq_fsr_identity_payload", "uq_fsr_identity_revision"}
EXPECTED_CHECKS = {"ck_fsr_basis", "ck_fsr_source_status", "ck_fsr_quantity_status", "ck_fsr_cost_status",
                   "ck_fsr_revision", "ck_fssr_status"}


async def main() -> None:
    eng = create_async_engine(os.environ["DATABASE_URL"])
    async with eng.connect() as c:
        await c.execute(text("SET TRANSACTION READ ONLY"))
        q = lambda s: c.execute(text(s))  # noqa: E731
        print("alembic_version", (await q("SELECT version_num FROM alembic_version")).scalar())
        print("feed_source_tables", (await q("SELECT count(*) FROM information_schema.tables WHERE table_name IN ('feed_source_rows','feed_source_sync_runs')")).scalar())
        print("public_tables", (await q("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")).scalar())
        idx = {r[0] for r in (await q("SELECT indexname FROM pg_indexes WHERE tablename IN ('feed_source_rows','feed_source_sync_runs')")).all()}
        con = {r[0] for r in (await q("SELECT conname FROM pg_constraint WHERE conrelid IN ('feed_source_rows'::regclass,'feed_source_sync_runs'::regclass)")).all()}
        print("indexes_missing", sorted(EXPECTED_INDEXES - idx))
        print("checks_missing", sorted(EXPECTED_CHECKS - con))
        print("unit_cost_precision", (await q("SELECT numeric_precision||','||numeric_scale FROM information_schema.columns WHERE table_name='feed_source_rows' AND column_name='unit_cost'")).scalar())
        print("currency_nullable", (await q("SELECT is_nullable FROM information_schema.columns WHERE table_name='feed_source_rows' AND column_name='currency'")).scalar())
        print("feed_source_rows", (await q("SELECT count(*) FROM feed_source_rows")).scalar())
        print("feed_records", (await q("SELECT count(*) FROM feed_records")).scalar())
        print("schema_fingerprint_non_feed", (await q(
            "SELECT md5(string_agg(table_name||'.'||column_name||':'||data_type||':'||is_nullable, '|' ORDER BY table_name, column_name)) "
            "FROM information_schema.columns WHERE table_schema='public' AND table_name NOT IN ('feed_source_rows','feed_source_sync_runs')")).scalar())
    await eng.dispose()


asyncio.run(main())
