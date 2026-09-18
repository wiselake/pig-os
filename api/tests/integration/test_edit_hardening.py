"""
수정/삭제 경로 견고화 회귀 테스트 (코어 단단하게).
생성(record_*)이 막는 제약을 수정(update_*)에서도 동일하게 강제하는지.
"""
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.db.models.sow import Boar, Sow
from app.schemas.events import (
    FarrowingCreate,
    FarrowingUpdate,
    MatingCreate,
    MatingUpdate,
    PigletEventCreate,
    WeaningCreate,
    WeaningUpdate,
)
from app.services import event_service


async def _new_sow(db, farm, tag, status="GILT"):
    s = Sow(farm_id=farm.id, ear_tag=tag, parity=0, status=status,
            entry_date=datetime(2024, 1, 1, tzinfo=UTC), entry_type="GILT")
    db.add(s)
    await db.flush()
    return s


async def test_delete_only_mating_rolls_back_to_open(db: AsyncSession, test_farm, test_sow, test_user):
    """단일 교배 삭제 → 모돈 OPEN 복귀 (재교배 잔존 카운트가 삭제건을 제외해야 함)."""
    m = await event_service.record_mating(
        db, test_farm.id, test_user.id,
        MatingCreate(sow_id=test_sow.id, mating_date=date(2026, 1, 1), mating_type="AI"))
    await db.refresh(test_sow)
    assert test_sow.status == "PREGNANT"
    await event_service.delete_mating(db, test_farm.id, test_user.id, m.id)
    await db.refresh(test_sow)
    assert test_sow.status == "OPEN"


async def _farrow(db, farm, sow, user, ba=12):
    m = await event_service.record_mating(
        db, farm.id, user.id, MatingCreate(sow_id=sow.id, mating_date=date(2026, 1, 1), mating_type="AI"))
    f = await event_service.record_farrowing(
        db, farm.id, user.id,
        FarrowingCreate(sow_id=sow.id, mating_id=m.id, farrowing_date=date(2026, 4, 25),
                        born_alive=ba, stillborn=0, mummified=0))
    return m, f


# ── 양자 self-target ──────────────────────────────────────────────────────────
async def test_foster_to_self_blocked(db: AsyncSession, test_farm, test_sow, test_user):
    _, f = await _farrow(db, test_farm, test_sow, test_user, ba=12)
    with pytest.raises(ValidationError, match="cannot foster to self"):
        await event_service.record_piglet_event(
            db, test_farm.id, test_user.id,
            PigletEventCreate(sow_id=test_sow.id, farrowing_id=f.id, event_date=date(2026, 5, 1),
                              event_type="FOSTER_OUT", piglet_count=2, target_sow_id=test_sow.id))


# ── update_mating: 도태 웅돈으로 수정 차단 ────────────────────────────────────
async def test_update_mating_to_inactive_boar_blocked(db: AsyncSession, test_farm, test_sow, test_user):
    active = Boar(farm_id=test_farm.id, ear_tag="B-OK", status="ACTIVE",
                  entry_date=datetime(2024, 1, 1, tzinfo=UTC))
    culled = Boar(farm_id=test_farm.id, ear_tag="B-CULL", status="CULLED",
                  entry_date=datetime(2024, 1, 1, tzinfo=UTC))
    db.add_all([active, culled]); await db.flush()
    m = await event_service.record_mating(
        db, test_farm.id, test_user.id,
        MatingCreate(sow_id=test_sow.id, mating_date=date(2026, 1, 1), mating_type="NATURAL", boar_id=active.id))
    with pytest.raises(ValidationError, match="cannot be used for mating"):
        await event_service.update_mating(
            db, test_farm.id, test_user.id, m.id, MatingUpdate(boar_id=culled.id))


# ── update_mating: 같은 모돈 같은 날짜 중복으로 수정 차단 ──────────────────────
async def test_update_mating_to_duplicate_date_blocked(db: AsyncSession, test_farm, test_user):
    sow = await _new_sow(db, test_farm, "DUP2")
    m1 = await event_service.record_mating(
        db, test_farm.id, test_user.id,
        MatingCreate(sow_id=sow.id, mating_date=date(2026, 1, 1), mating_type="AI"))
    # 사고로 사이클 종료시켜 재교배 허용
    await event_service.record_reproductive_event(
        db, test_farm.id, test_user.id,
        __import__("app.schemas.events", fromlist=["ReproductiveEventCreate"]).ReproductiveEventCreate(
            sow_id=sow.id, event_date=date(2026, 1, 10), event_type="RETURN_TO_ESTRUS", mating_id=m1.id))
    m2 = await event_service.record_mating(
        db, test_farm.id, test_user.id,
        MatingCreate(sow_id=sow.id, mating_date=date(2026, 1, 20), mating_type="AI"))
    # m2 날짜를 m1과 같은 날로 수정 → 중복 차단
    with pytest.raises(Exception):
        await event_service.update_mating(
            db, test_farm.id, test_user.id, m2.id, MatingUpdate(mating_date=date(2026, 1, 1)))


# ── update_farrowing: 기존 이유두수 밑으로 실산 축소 차단 ─────────────────────
async def test_update_farrowing_below_weaned_blocked(db: AsyncSession, test_farm, test_sow, test_user):
    _, f = await _farrow(db, test_farm, test_sow, test_user, ba=12)
    await event_service.record_weaning(
        db, test_farm.id, test_user.id,
        WeaningCreate(sow_id=test_sow.id, farrowing_id=f.id, weaning_date=date(2026, 5, 16),
                      weaned_count=12))
    # 실산을 8로 축소 → 이미 12두 이유했으므로 정합성 깨짐 차단
    with pytest.raises(ValidationError):
        await event_service.update_farrowing(
            db, test_farm.id, test_user.id, f.id, FarrowingUpdate(born_alive=8))


# ── update_weaning: 부분이유 형제 합계 초과 차단 ──────────────────────────────
async def test_update_weaning_sibling_aware(db: AsyncSession, test_farm, test_sow, test_user):
    _, f = await _farrow(db, test_farm, test_sow, test_user, ba=12)
    await event_service.record_weaning(  # 첫 부분이유 — 이후 w2 갱신의 형제 맥락만 만든다
        db, test_farm.id, test_user.id,
        WeaningCreate(sow_id=test_sow.id, farrowing_id=f.id, weaning_date=date(2026, 5, 10),
                      weaned_count=5, is_partial=True))
    w2 = await event_service.record_weaning(
        db, test_farm.id, test_user.id,
        WeaningCreate(sow_id=test_sow.id, farrowing_id=f.id, weaning_date=date(2026, 5, 16),
                      weaned_count=7))
    # w2를 9로 수정하면 합계 5+9=14 > 유효복당 12 → 차단
    with pytest.raises(ValidationError):
        await event_service.update_weaning(
            db, test_farm.id, test_user.id, w2.id, WeaningUpdate(weaned_count=9))
