"""NPD 여집합(비생산일수) + 모돈회전율 — PigPlan 정합 (KPI 스펙 §3 재정의).

기존 대시보드 NPD는 v_sow_npd의 AVG(wei_days)=이유→교배 간격(≈수일)을 '비생산일수'로
잘못 표시했음. PigPlan 비생산일수는 여집합: NPD/모돈-년 = 365 × (사육일 − 임신일 − 포유일)/사육일.
모돈회전율 = 창내 분만복수 / 평균 상시모돈(경산). 둘 다 부재/오표시 → 정정.

결정론 공식이라 TDD 의무(verify 스킬 §2). 완결 사이클만 있는 통제 시나리오로 경계 고정.
"""
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.events import Farrowing, Mating, Weaning
from app.db.models.platform import Farm
from app.db.models.sow import Sow
from app.services.kpi_service import calculate_npd

pytestmark = pytest.mark.anyio


async def _cycle(db, farm, sow, *, mate: date, farrow: date, wean: date, tb=12, weaned=11):
    m = Mating(farm_id=farm.id, sow_id=sow.id, mating_date=mate, mating_type="AI", mating_number=1)
    db.add(m)
    await db.flush()
    f = Farrowing(farm_id=farm.id, sow_id=sow.id, mating_id=m.id, farrowing_date=farrow,
                  total_born=tb, born_alive=tb, stillborn=0, mummified=0, nursing_head=tb)
    db.add(f)
    await db.flush()
    db.add(Weaning(farm_id=farm.id, sow_id=sow.id, farrowing_id=f.id, weaning_date=wean,
                   weaned_count=weaned))
    await db.flush()


async def test_npd_complement_and_turnover(db: AsyncSession, test_farm: Farm):
    # 경산 모돈 1두, 창(2025-01-01~2026-01-01) 내내 사육(365일).
    sow = Sow(farm_id=test_farm.id, ear_tag="NPD-1", parity=2, status="OPEN",
              entry_date=datetime(2024, 6, 1, tzinfo=UTC), entry_type="PURCHASE")
    db.add(sow)
    await db.flush()
    # 완결 사이클 2건: 각 임신 114일 + 포유 24일 (생산일 276) → 비생산 89일
    await _cycle(db, test_farm, sow, mate=date(2025, 1, 11), farrow=date(2025, 5, 5), wean=date(2025, 5, 29))
    await _cycle(db, test_farm, sow, mate=date(2025, 6, 5), farrow=date(2025, 9, 27), wean=date(2025, 10, 21))

    npd = await calculate_npd(db, test_farm.id, date(2026, 1, 1))
    assert npd is not None
    # NPD/모돈-년 = 365 × (365 − 228 − 48)/365 = 89
    assert npd.avg_npd == pytest.approx(89.0, abs=1.0), f"여집합 NPD 89 기대, got {npd.avg_npd}"
    # 회전율 = 분만 2건 / 평균 재고 1두 = 2.0
    assert npd.sow_turnover == pytest.approx(2.0, abs=0.05), f"회전율 2.0 기대, got {npd.sow_turnover}"
    assert npd.avg_gestation_days == pytest.approx(114.0, abs=1.0)
    assert npd.avg_lactation_days == pytest.approx(24.0, abs=1.0)


async def test_npd_no_inventory_returns_none(db: AsyncSession, test_farm: Farm):
    npd = await calculate_npd(db, test_farm.id, date(2026, 1, 1))
    assert npd is None or npd.avg_npd is None


async def test_pregnant_gilts_do_not_deflate_npd(db: AsyncSession, test_farm: Farm):
    """리뷰 F1: 임신 후보돈(parity=0)은 재고(parity>=1) 밖 → 분자에만 새면 NPD가 0으로 오클램프.
    parity>=1 필터로 후보돈이 preg_open에 안 새는지 회귀 가드."""
    # 경산 1두(재고 모집단)
    old = Sow(farm_id=test_farm.id, ear_tag="OLD-1", parity=2, status="OPEN",
              entry_date=datetime(2024, 6, 1, tzinfo=UTC), entry_type="PURCHASE")
    db.add(old)
    await db.flush()
    await _cycle(db, test_farm, old, mate=date(2025, 1, 11), farrow=date(2025, 5, 5), wean=date(2025, 5, 29))
    # 임신 후보돈 20두(parity=0, 최근 교배·미분만) — 예전 버그면 preg_open이 이들을 더해 NPD=0
    for i in range(20):
        g = Sow(farm_id=test_farm.id, ear_tag=f"GILT-{i}", parity=0, status="PREGNANT",
                entry_date=datetime(2025, 10, 1, tzinfo=UTC), entry_type="GILT")
        db.add(g)
        await db.flush()
        db.add(Mating(farm_id=test_farm.id, sow_id=g.id, mating_date=date(2025, 11, 20),
                      mating_type="AI", mating_number=1))
    await db.flush()

    npd = await calculate_npd(db, test_farm.id, date(2026, 1, 1))
    assert npd is not None and npd.avg_npd is not None
    assert npd.avg_npd > 30, f"후보돈 임신일이 새서 NPD가 0으로 클램프되면 안 됨, got {npd.avg_npd}"


async def test_npd_not_wei_magnitude(db: AsyncSession, test_farm: Farm):
    """여집합 NPD는 WEI(수일)가 아니라 수십일 규모여야 함 (오표시 회귀 방지)."""
    sow = Sow(farm_id=test_farm.id, ear_tag="NPD-2", parity=3, status="OPEN",
              entry_date=datetime(2024, 6, 1, tzinfo=UTC), entry_type="PURCHASE")
    db.add(sow)
    await db.flush()
    await _cycle(db, test_farm, sow, mate=date(2025, 2, 1), farrow=date(2025, 5, 26), wean=date(2025, 6, 19))
    npd = await calculate_npd(db, test_farm.id, date(2026, 1, 1))
    assert npd is not None and npd.avg_npd is not None
    assert npd.avg_npd > 30, "1산 사육이면 비생산일수가 크게 나와야(WEI≈수일 아님)"
