"""임신감정 /sync 프로세서 — 오프라인 큐 경로(REST record_pregnancy_check 미러).

검증: PREGNANT 모돈만 수락, 잘못된 result/부적격 상태 거부, NEGATIVE→ACCIDENT 전이.
"""
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.events import PregnancyCheck
from app.db.models.platform import Farm
from app.db.models.sow import Sow
from app.schemas.sync import SyncChanges, SyncPregnancyCheck, SyncRequest
from app.services import sync_service

NOW = datetime.now(UTC)


def _pc(sid, result):
    return SyncPregnancyCheck(id=uuid4(), sow_id=sid, check_date="2026-02-01",
                              result=result, days_after_mating=28, method="ULTRASOUND",
                              client_created_at=NOW)


async def _run(db, farm, *checks):
    req = SyncRequest(farm_id=farm.id, client_id=uuid4(), last_sync_at=None, dry_run=False,
                      changes=SyncChanges(pregnancy_checks=list(checks)))
    return await sync_service.process_sync(db, farm, req)


def _rej(resp):
    return [r for r in resp.rejected if r.entity == "pregnancy_check"]


async def test_pregnant_sow_positive_accepted(db: AsyncSession, test_farm: Farm, test_sow: Sow):
    test_sow.status = "PREGNANT"
    await db.flush()
    item = _pc(test_sow.id, "POSITIVE")
    resp = await _run(db, test_farm, item)
    assert _rej(resp) == [], f"unexpected reject: {resp.rejected}"
    saved = await db.get(PregnancyCheck, item.id)
    assert saved is not None and saved.result == "POSITIVE"


async def test_non_pregnant_sow_status_conflict(db: AsyncSession, test_farm: Farm, test_sow: Sow):
    test_sow.status = "OPEN"
    await db.flush()
    resp = await _run(db, test_farm, _pc(test_sow.id, "POSITIVE"))
    rej = _rej(resp)
    assert rej and rej[0].reason == "STATUS_CONFLICT"


async def test_invalid_result_validation_failed(db: AsyncSession, test_farm: Farm, test_sow: Sow):
    test_sow.status = "PREGNANT"
    await db.flush()
    resp = await _run(db, test_farm, _pc(test_sow.id, "MAYBE"))
    rej = _rej(resp)
    assert rej and rej[0].reason == "VALIDATION_FAILED"


async def test_negative_transitions_sow_to_accident(db: AsyncSession, test_farm: Farm, test_sow: Sow):
    test_sow.status = "PREGNANT"
    await db.flush()
    resp = await _run(db, test_farm, _pc(test_sow.id, "NEGATIVE"))
    assert _rej(resp) == []
    refreshed = await db.get(Sow, test_sow.id)
    assert refreshed.status == "ACCIDENT", f"NEGATIVE는 공태→ACCIDENT여야: {refreshed.status}"
