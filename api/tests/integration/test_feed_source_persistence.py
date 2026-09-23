"""feed_source_rows persistence — P-2 identity/idempotency · P-3 basis/currency · P-4 projection · P-5 correction · §24 failure.

합성 소스 행만(농장 식별자 없음). Oracle 없음 — source 는 메모리 fake. feed_records 는 만지지 않는다.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.feed_source import FeedSourceRow, FeedSourceSyncRun
from app.db.models.health import FeedRecord
from app.db.models.platform import Farm
from app.engine.feed import metrics as m
from app.engine.feed.types import INSUFFICIENT, Period
from app.harvest import feed_source_sync as sync
from app.harvest import pigplan_feed_delivery as pf
from app.repositories import feed_source_repo as repo
from app.services.feed_engine_service import load_feed_input, load_feed_input_from_source

TODAY = date(2026, 9, 22)
OBS = datetime(2026, 9, 22, 9, 0, tzinfo=UTC)
AUG = Period(date(2026, 8, 1), date(2026, 8, 31))
JUL = Period(date(2026, 7, 1), date(2026, 7, 31))
SRC_FARM = 9001            # 합성 소스 농장번호 (매핑은 테스트 안에서만)


def srow(seq, d="2026-08-10", kg="4400", price="582", total=None, stage="비육돈", use="Y", ctry="KOR", upt=None, **kw):
    total = Decimal(price) * Decimal(kg) if total is None and price is not None else (Decimal(total) if total else None)
    base = dict(source_farm_no=SRC_FARM, seq=seq, wk_dt=date.fromisoformat(d), wk_dt_raw=d,
                total_kg=Decimal(kg) if kg is not None else None, fper_price=Decimal(price) if price is not None else None,
                total_price=total, feed_stage_cd="100005", feed_stage_name=stage, feed_cd=17, feed_name="제품A",
                use_yn=use, account_cd="410002", gain_yn="M", country_code=ctry, has_supplier=True,
                source_inserted_at=OBS, source_updated_at=upt or OBS)
    base.update(kw)
    return pf.PigPlanFeedDeliveryRow(**base)


class FakeSource:
    def __init__(self, rows=None, fail=False):
        self.rows, self.fail = list(rows or []), fail

    def fetch_rows(self, farm_nos, start, end):
        if self.fail:
            raise ConnectionError("ORA-12541 TNS no listener (simulated)")
        return [r for r in self.rows if r.source_farm_no in farm_nos]


async def _run(db, farm, rows, fail=False):
    return await sync.run_pigplan_feed_sync(db, FakeSource(rows, fail), {SRC_FARM: farm.id},
                                            today=TODAY, lookback_days=400, observed_at=OBS)


async def _count(db, **w):
    return await repo.count_rows(db, **w)


@pytest.mark.asyncio
async def test_source_row_to_persistence_to_canonical_to_feedinput(db: AsyncSession, test_farm: Farm):
    rows = [srow(1), srow(2, d="2026-08-20", kg="3000", price="600", stage="육성돈"),
            srow(3, d="2026-08-25", price=None, total=None),          # 원가 없음
            srow(4, use="N"),                                           # 소스 soft-delete
            srow(5, kg="0")]                                            # 수량 불가
    out = await _run(db, test_farm, rows)
    assert (out.status, out.inserted, out.unchanged, out.retracted) == ("SUCCEEDED", 5, 0, 0)
    assert await _count(db) == 5                                        # 관측은 전부 남는다 (제외도 사실이다)
    assert await _count(db, source_status="INACTIVE") == 1 and await _count(db, quantity_status="EXCLUDED") == 2   # INACTIVE 도 수량 제외
    inp, lineage = await load_feed_input_from_source(db, test_farm.id, AUG.start, AUG.end, quantity_basis="DELIVERED")
    assert inp.quantity_basis == "DELIVERED" and inp.farm_currency == "KRW" and len(inp.rows) == 3
    assert {r.currency for r in inp.rows} == {"KRW"}
    assert len(lineage["source_row_ids"]) == 3 and lineage["contract_versions"] == ["pigplan_feed_delivery.v1"]
    q, c = m.feed_qty(inp), m.feed_cost(inp)
    assert q.value == 4400 + 3000 + 4400 and q.quantity_basis == "DELIVERED"
    assert (c.provenance, c.reason, c.evidence["partial_cost"]) == (INSUFFICIENT, "cost_incomplete", 4400 * 582 + 3000 * 600)
    # lineage 역추적: metric → FeedInput 행 → source_row_id → 소스 identity
    first = await db.get(FeedSourceRow, __import__("uuid").UUID(lineage["source_row_ids"][0]))
    assert (first.source_system, first.source_dataset, first.source_row_key) == ("pigplan", "TM_ETC_TRADE", f"{SRC_FARM}:1")
    assert first.feed_product_raw == "제품A" and first.feed_stage_raw == "비육돈"   # 두 축 보존


@pytest.mark.asyncio
async def test_same_source_three_times_inserts_once(db: AsyncSession, test_farm: Farm):
    rows = [srow(1), srow(2, d="2026-08-20")]
    r1 = await _run(db, test_farm, rows)
    r2 = await _run(db, test_farm, rows)
    r3 = await _run(db, test_farm, rows)
    assert (r1.inserted, r2.inserted, r3.inserted) == (2, 0, 0)
    assert (r2.unchanged, r3.unchanged) == (2, 2)
    assert await _count(db) == 2 and await _count(db, is_current=True) == 2
    runs = (await db.execute(select(FeedSourceSyncRun).order_by(FeedSourceSyncRun.started_at))).scalars().all()
    assert [r.status for r in runs] == ["SUCCEEDED"] * 3 and runs[-1].watermark_to is not None


@pytest.mark.asyncio
async def test_source_correction_appends_revision_and_keeps_history(db: AsyncSession, test_farm: Farm):
    await _run(db, test_farm, [srow(1, kg="4400")])
    later = datetime(2026, 9, 23, 9, 0, tzinfo=UTC)
    out = await _run(db, test_farm, [srow(1, kg="4000", upt=later)])       # 소스가 수량을 고쳤다
    assert (out.inserted, out.superseded, out.unchanged) == (1, 1, 0)
    revs = (await db.execute(select(FeedSourceRow).where(FeedSourceRow.source_row_key == f"{SRC_FARM}:1")
                             .order_by(FeedSourceRow.revision))).scalars().all()
    assert [(r.revision, r.is_current, float(r.quantity_kg)) for r in revs] == [(1, False, 4400.0), (2, True, 4000.0)]
    assert revs[0].superseded_at is not None and revs[1].superseded_at is None
    inp, _ = await load_feed_input_from_source(db, test_farm.id, AUG.start, AUG.end, quantity_basis="DELIVERED")
    assert m.feed_qty(inp).value == 4000.0                                  # 현재 revision 만 계산에 들어간다


@pytest.mark.asyncio
async def test_source_inactive_and_missing_are_revisions_not_deletes(db: AsyncSession, test_farm: Farm):
    await _run(db, test_farm, [srow(1), srow(2, d="2026-08-20")])
    # 1 이 소스에서 USE_YN='N' 이 되고, 2 는 소스에서 아예 사라졌다
    out = await _run(db, test_farm, [srow(1, use="N", upt=datetime(2026, 9, 23, tzinfo=UTC))])
    assert (out.inserted, out.superseded, out.retracted) == (1, 1, 1)
    assert await _count(db) == 4                                             # 2 원본 + INACTIVE rev + RETRACTED rev
    cur = {r.source_row_key: r for r in (await db.execute(select(FeedSourceRow).where(FeedSourceRow.is_current.is_(True)))).scalars()}
    assert cur[f"{SRC_FARM}:1"].source_status == "INACTIVE" and cur[f"{SRC_FARM}:2"].source_status == "RETRACTED"
    assert "SOURCE_ROW_MISSING" in cur[f"{SRC_FARM}:2"].quality_reasons
    inp, _ = await load_feed_input_from_source(db, test_farm.id, AUG.start, AUG.end, quantity_basis="DELIVERED")
    assert inp.rows == () and m.feed_qty(inp).reason == "no_data"
    # 되살아나면(같은 payload 가 다시 옴) 새 행이 아니라 그 revision 이 다시 current 가 된다
    back = await _run(db, test_farm, [srow(1), srow(2, d="2026-08-20")])
    assert await _count(db) == 4 and back.inserted == 2
    assert await _count(db, is_current=True) == 2 and await _count(db, is_current=True, source_status="ACTIVE") == 2


@pytest.mark.asyncio
async def test_partial_and_missing_cost_and_identity_mismatch_keep_quantity(db: AsyncSession, test_farm: Farm):
    await _run(db, test_farm, [srow(1), srow(2, d="2026-08-12", total="1"),            # 항등 깨짐 → 원가만 유보
                               srow(3, d="2026-08-15", price=None, total=None)])       # 원가 없음
    assert await _count(db, cost_status="INSUFFICIENT") == 2 and await _count(db, quantity_status="ACCEPTED") == 3
    inp, _ = await load_feed_input_from_source(db, test_farm.id, AUG.start, AUG.end, quantity_basis="DELIVERED")
    assert m.feed_qty(inp).value == 4400 * 3 and m.feed_cost(inp).reason == "cost_incomplete"
    assert m.feed_unit_price(inp).value == 582.0                             # costed 행만


@pytest.mark.asyncio
async def test_krw_is_preserved_and_farm_currency_never_used(db: AsyncSession, test_farm: Farm):
    test_farm.currency = "USD"                                               # PigOS 농장은 합성 USD 라도
    await db.flush()
    await _run(db, test_farm, [srow(1), srow(2, d="2026-08-11", ctry="VNM")])          # 비KOR 행: 수량만
    assert await _count(db, currency="KRW") == 2 and await _count(db, cost_status="EXCLUDED") == 1
    inp, _ = await load_feed_input_from_source(db, test_farm.id, AUG.start, AUG.end, quantity_basis="DELIVERED")
    assert inp.farm_currency == "KRW" and {r.currency for r in inp.rows} == {"KRW"}
    assert m.feed_qty(inp).value == 8800.0 and m.feed_cost(inp).reason == "cost_incomplete"
    assert "USD" not in {r.currency for r in inp.rows}


@pytest.mark.asyncio
async def test_as_recorded_and_delivered_stay_separate_and_never_mix(db: AsyncSession, test_farm: Farm, test_user):
    # 같은 농장·같은 달에 수기 feed_records(AS_RECORDED) 와 Oracle 입고(DELIVERED) 가 둘 다 있다 — 중복이 아니라 다른 사실
    db.add(FeedRecord(farm_id=test_farm.id, record_date=date(2026, 8, 10), quantity_kg=100, feed_type="Grower",
                      unit_cost=1.0, currency="USD", created_by=test_user.id))
    await db.flush()
    await _run(db, test_farm, [srow(1)])
    manual = await load_feed_input(db, test_farm, AUG.start, AUG.end, with_cohort=False)
    delivered, _ = await load_feed_input_from_source(db, test_farm.id, AUG.start, AUG.end, quantity_basis="DELIVERED")
    assert (manual.quantity_basis, m.feed_qty(manual).value) == ("AS_RECORDED", 100.0)
    assert (delivered.quantity_basis, m.feed_qty(delivered).value) == ("DELIVERED", 4400.0)
    assert await _count(db) == 1 and await db.scalar(select(FeedRecord.id).where(FeedRecord.farm_id == test_farm.id)) is not None
    # 다른 basis 의 기간을 비교하면 엔진이 거부한다 (persistence 뒤에도)
    mixed = m.feed_qty_change(manual, delivered)
    assert (mixed.provenance, mixed.reason, mixed.evidence["basis_mismatch"]) == (INSUFFICIENT, "context_missing", ["AS_RECORDED", "DELIVERED"])
    # AS_RECORDED 요청에 소스 행은 절대 섞이지 않는다
    none, _ = await load_feed_input_from_source(db, test_farm.id, AUG.start, AUG.end, quantity_basis="AS_RECORDED")
    assert none.rows == ()


@pytest.mark.asyncio
async def test_oracle_unavailable_changes_nothing_and_is_not_empty_data(db: AsyncSession, test_farm: Farm):
    await _run(db, test_farm, [srow(1), srow(2, d="2026-08-20")])
    before = await _count(db)
    out = await _run(db, test_farm, [], fail=True)
    assert out.status == "SOURCE_UNAVAILABLE" and "ORA-12541" in out.error
    assert await _count(db) == before and await _count(db, is_current=True, source_status="ACTIVE") == 2   # 철회 0
    run = await db.get(FeedSourceSyncRun, out.run_id)          # started_at 이 같은 상수라 정렬로 고르면 TEST_BUG
    assert run.status == "SOURCE_UNAVAILABLE" and run.rows_fetched == 0 and run.error
    assert run.notes["error_class"] == "SOURCE_CONNECTION" and run.notes["data_changed"] is False


@pytest.mark.asyncio
async def test_calendar_month_change_from_persisted_source(db: AsyncSession, test_farm: Farm):
    # P-6: 7월(31일) ↔ 8월(31일) 도, 8월(31일) ↔ 9월(30일) 도 달력월이면 비교된다
    await _run(db, test_farm, [srow(1, d="2026-07-10", kg="4000"), srow(2, d="2026-08-10", kg="4400"),
                               srow(3, d="2026-09-05", kg="1000")])
    jul, _ = await load_feed_input_from_source(db, test_farm.id, JUL.start, JUL.end, quantity_basis="DELIVERED")
    aug, _ = await load_feed_input_from_source(db, test_farm.id, AUG.start, AUG.end, quantity_basis="DELIVERED")
    sep, _ = await load_feed_input_from_source(db, test_farm.id, date(2026, 9, 1), date(2026, 9, 30), quantity_basis="DELIVERED")
    c1, c2 = m.feed_qty_change(jul, aug), m.feed_qty_change(aug, sep)
    assert (c1.value, c1.evidence["comparison_grain"]) == (400.0, "calendar_month")
    assert (c2.value, c2.evidence["comparison_grain"]) == (-3400.0, "calendar_month")
    bad = m.feed_qty_change(aug, sep.__class__(period=Period(date(2026, 9, 1), date(2026, 9, 20)), farm_currency="KRW",
                                               rows=sep.rows, quantity_basis="DELIVERED"))
    assert bad.reason == "context_missing" and bad.evidence["period_days"] == [31, 20]


# ── L2 idempotency: 순서 무관 · 해시/uuid 결정론 · 중단 후 재시작 ──────────────────────────
@pytest.mark.asyncio
async def test_input_order_shuffle_gives_same_identities_hashes_and_ids(db: AsyncSession, test_farm: Farm):
    import random
    rows = [srow(i, d=f"2026-08-{(i % 28) + 1:02d}", kg=str(100 + i)) for i in range(1, 41)]
    shuffled = rows[:]
    random.Random(42).shuffle(shuffled)
    obs_a = [sync.to_observation(r, pf.classify(r, today=TODAY), test_farm.id) for r in rows]
    obs_b = [sync.to_observation(r, pf.classify(r, today=TODAY), test_farm.id) for r in shuffled]
    assert {o.source_row_key for o in obs_a} == {o.source_row_key for o in obs_b}
    assert {o.row_id() for o in obs_a} == {o.row_id() for o in obs_b}
    assert {(o.source_row_key, o.payload_hash()) for o in obs_a} == {(o.source_row_key, o.payload_hash()) for o in obs_b}
    r1 = await _run(db, test_farm, shuffled)
    r2 = await _run(db, test_farm, rows)
    assert (r1.inserted, r2.inserted, r2.unchanged) == (40, 0, 40)


@pytest.mark.asyncio
async def test_mid_batch_interruption_then_restart_has_no_duplicates_or_gaps(db: AsyncSession, test_farm: Farm, monkeypatch):
    rows = [srow(i, d=f"2026-08-{(i % 28) + 1:02d}") for i in range(1, 31)]
    real = repo.retract_missing

    async def boom(*a, **k):                       # 삽입 뒤·커밋 전 실패 = 한 트랜잭션이므로 전부 rollback
        raise RuntimeError("simulated crash after ingest, before commit")
    monkeypatch.setattr(repo, "retract_missing", boom)
    failed = await _run(db, test_farm, rows)
    assert failed.status == "SYNC_FAILED" and await _count(db) == 0          # 부분 커밋 없음
    run = await db.get(FeedSourceSyncRun, failed.run_id)
    assert run.status == "SYNC_FAILED" and run.notes["data_changed"] is False and run.notes["resumable"]
    monkeypatch.setattr(repo, "retract_missing", real)
    restarted = await _run(db, test_farm, rows)                                # 재시작 = 처음부터, 멱등
    assert (restarted.status, restarted.inserted) == ("SUCCEEDED", 30)
    assert await _count(db) == 30 and await _count(db, is_current=True) == 30
    again = await _run(db, test_farm, rows)
    assert (again.inserted, again.unchanged) == (0, 30)
    runs = {r.status for r in (await db.execute(select(FeedSourceSyncRun))).scalars()}
    assert {"SYNC_FAILED", "SUCCEEDED"} <= runs


@pytest.mark.asyncio
async def test_failure_after_ingest_never_leaves_data_behind(db: AsyncSession, test_farm: Farm, monkeypatch):
    """L3 드릴에서 잡힌 SYNC_BUG 회귀: 저장 뒤·원장 기록 중 예외 → SYNC_FAILED 이면서 데이터도 0 이어야 한다."""
    rows = [srow(i, d=f"2026-08-{(i % 28) + 1:02d}") for i in range(1, 11)]
    monkeypatch.setattr(sync, "_watermark", lambda rows: (_ for _ in ()).throw(TypeError("simulated bookkeeping failure")))
    out = await _run(db, test_farm, rows)
    assert out.status == "SYNC_FAILED" and await _count(db) == 0
    run = await db.get(FeedSourceSyncRun, out.run_id)
    assert run.status == "SYNC_FAILED" and run.notes["data_changed"] is False


# ── L5 failure injection ──────────────────────────────────────────────────────
class _Boom:
    def __init__(self, exc):
        self.exc = exc

    def fetch_rows(self, farm_nos, start, end):
        raise self.exc


@pytest.mark.asyncio
@pytest.mark.parametrize("exc,klass", [
    (ConnectionError("ORA-12541: TNS:no listener"), "SOURCE_CONNECTION"),
    (TimeoutError("socket timeout"), "TIMEOUT"),
    (PermissionError("ORA-01031: insufficient privileges"), "PERMISSION_DENIED"),
    (RuntimeError("DPY-4011: the database or network closed the connection"), "SOURCE_CONNECTION"),
])
async def test_source_failures_are_classified_and_never_empty(db: AsyncSession, test_farm: Farm, exc, klass):
    await _run(db, test_farm, [srow(1), srow(2, d="2026-08-20")])
    before_all, before_active = await _count(db), await _count(db, is_current=True, source_status="ACTIVE")
    out = await sync.run_pigplan_feed_sync(db, _Boom(exc), {SRC_FARM: test_farm.id}, today=TODAY, lookback_days=400, observed_at=OBS)
    run = await db.get(FeedSourceSyncRun, out.run_id)
    assert out.status == run.status == "SOURCE_UNAVAILABLE" and run.notes["error_class"] == klass
    assert run.notes.get("empty_source") is None                        # 장애 원장에는 '빈 결과' 표기가 없다
    assert await _count(db) == before_all and await _count(db, is_current=True, source_status="ACTIVE") == before_active   # 철회 0


@pytest.mark.asyncio
async def test_empty_successful_result_is_recorded_as_empty_and_retracts_nothing(db: AsyncSession, test_farm: Farm):
    await _run(db, test_farm, [srow(1), srow(2, d="2026-08-20")])
    out = await _run(db, test_farm, [])                                   # 성공했지만 0행
    run = await db.get(FeedSourceSyncRun, out.run_id)
    assert (out.status, out.retracted, run.notes["empty_source"], run.notes["retraction_skipped_farms"]) == ("SUCCEEDED", 0, True, 1)
    assert await _count(db, is_current=True, source_status="ACTIVE") == 2


@pytest.mark.asyncio
async def test_partial_batch_db_failure_has_no_partial_commit(db: AsyncSession, test_farm: Farm, monkeypatch):
    """두 번째 statement 배치에서 DB 예외 → 첫 배치도 남지 않는다 (SAVEPOINT 전체 rollback)."""
    from sqlalchemy.exc import OperationalError
    rows = [srow(i, d=f"2026-08-{(i % 28) + 1:02d}") for i in range(1, 41)]
    real_execute = db.execute
    calls = {"n": 0}

    async def flaky(stmt, *a, **k):
        if "INSERT INTO feed_source_rows" in str(stmt):
            calls["n"] += 1
            if calls["n"] == 2:
                raise OperationalError("INSERT", {}, Exception("simulated disk full on batch 2"))
        return await real_execute(stmt, *a, **k)
    monkeypatch.setattr(db, "execute", flaky)
    out = await sync.run_pigplan_feed_sync(db, sync_fake(rows), {SRC_FARM: test_farm.id}, today=TODAY, lookback_days=400,
                                           observed_at=OBS, batch_size=10)
    monkeypatch.setattr(db, "execute", real_execute)
    run = await db.get(FeedSourceSyncRun, out.run_id)
    assert out.status == "SYNC_FAILED" and run.notes["error_class"] == "TARGET_DB" and run.notes["data_changed"] is False
    assert await _count(db) == 0 and calls["n"] == 2
    ok = await _run(db, test_farm, rows)                                   # 재시작 → 전량, 중복 0
    assert (ok.status, ok.inserted) == ("SUCCEEDED", 40) and await _count(db) == 40


def sync_fake(rows):
    return FakeSource(rows)
