"""
밤샘 QA 발견 정합성 버그 회귀방지 (2026-06-24).
INTEG-1(긴 ear_tag 이유 500) · C3(FOSTER_OUT 가드) · BUG-3(이유삭제→그룹 soft-delete) · TENANT#1.
(pigos_test, Docker)
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.db.models.platform import Farm
from app.db.models.sow import PigletGroup, Sow
from app.schemas.events import (
    FarrowingCreate,
    MatingCreate,
    PigletEventCreate,
    WeaningCreate,
)
from app.services import event_service


async def _new_sow(db, farm, ear_tag) -> Sow:
    sow = Sow(farm_id=farm.id, ear_tag=ear_tag, status="GILT", parity=0,
              entry_type="GILT", entry_date=date(2025, 12, 1))
    db.add(sow)
    await db.flush()
    return sow


class TestIntegrityFixes:
    async def test_integ1_long_ear_tag_weaning_ok(self, db: AsyncSession, test_farm: Farm, test_user):
        """INTEG-1: 21자 ear_tag로도 이유 성공(group_code VARCHAR(30) 미초과) + 모돈 OPEN."""
        sow = await _new_sow(db, test_farm, "KR-FARM-SOW-0001-2025")  # 21자
        m = await event_service.record_mating(
            db, test_farm.id, test_user.id,
            MatingCreate(sow_id=sow.id, mating_date=date(2026, 1, 1), mating_type="AI"))
        f = await event_service.record_farrowing(
            db, test_farm.id, test_user.id,
            FarrowingCreate(sow_id=sow.id, mating_id=m.id, farrowing_date=date(2026, 4, 25),
                            born_alive=11, stillborn=1, mummified=0))
        # 이유 — 예전엔 group_code 오버플로로 500. 이제 성공해야.
        await event_service.record_weaning(  # 성공 자체가 단언이다
            db, test_farm.id, test_user.id,
            WeaningCreate(sow_id=sow.id, farrowing_id=f.id, weaning_date=date(2026, 5, 16),
                          weaned_count=11))
        await db.refresh(sow)
        assert sow.status == "OPEN"
        grp = await db.scalar(select(PigletGroup).where(
            PigletGroup.farm_id == test_farm.id, PigletGroup.deleted_at.is_(None),
            PigletGroup.group_code.like("WG-%")))
        assert grp is not None and len(grp.group_code) <= 30

    async def test_c3_foster_out_exceeds_nursing_blocked(self, db: AsyncSession, test_farm: Farm, test_user):
        """C3: 포유두수 초과 FOSTER_OUT은 422 차단(음수 포유 방지)."""
        sow = await _new_sow(db, test_farm, "SOW-FO-1")
        tgt = await _new_sow(db, test_farm, "SOW-FO-2")
        for s, d in ((sow, date(2026, 1, 1)), (tgt, date(2026, 1, 2))):
            m = await event_service.record_mating(db, test_farm.id, test_user.id,
                MatingCreate(sow_id=s.id, mating_date=d, mating_type="AI"))
            await event_service.record_farrowing(db, test_farm.id, test_user.id,
                FarrowingCreate(sow_id=s.id, mating_id=m.id,
                                farrowing_date=d + timedelta(days=114), born_alive=10))
        with pytest.raises(ValidationError):  # 10마리 포유 중 12 전출 불가
            await event_service.record_piglet_event(
                db, test_farm.id, test_user.id,
                PigletEventCreate(sow_id=sow.id, event_date=date(2026, 4, 26),
                                  event_type="FOSTER_OUT", piglet_count=12, target_sow_id=tgt.id))

    async def test_bug3_delete_weaning_softdeletes_group(self, db: AsyncSession, test_farm: Farm, test_user):
        """BUG-3: 이유 삭제 시 자동생성 자돈그룹도 soft-delete(유령 재고 방지)."""
        sow = await _new_sow(db, test_farm, "SOW-WG-1")
        m = await event_service.record_mating(db, test_farm.id, test_user.id,
            MatingCreate(sow_id=sow.id, mating_date=date(2026, 1, 1), mating_type="AI"))
        f = await event_service.record_farrowing(db, test_farm.id, test_user.id,
            FarrowingCreate(sow_id=sow.id, mating_id=m.id, farrowing_date=date(2026, 4, 25), born_alive=10))
        w = await event_service.record_weaning(db, test_farm.id, test_user.id,
            WeaningCreate(sow_id=sow.id, farrowing_id=f.id, weaning_date=date(2026, 5, 16), weaned_count=10))
        active = await db.scalar(select(PigletGroup).where(
            PigletGroup.farm_id == test_farm.id, PigletGroup.deleted_at.is_(None),
            PigletGroup.group_code == f"WG-260516-{str(w.id)[:8]}"))
        assert active is not None  # 생성됨
        await event_service.delete_weaning(db, test_farm.id, test_user.id, w.id)
        gone = await db.scalar(select(PigletGroup).where(
            PigletGroup.group_code == f"WG-260516-{str(w.id)[:8]}",
            PigletGroup.deleted_at.is_(None)))
        assert gone is None  # soft-delete됨(유령 재고 0)
