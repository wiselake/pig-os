"""트렌드 PSY 정정(#2) — 분자=이유 자돈수 합계, 분모=월별 활성 재고(스펙 §1).

기존 get_trend는 분자를 COUNT(*)(이유 건수)로, 분모를 전체 sows COUNT로 계산해
PSY가 ~복당두수배 과소이고 대시보드 PSY와도 불일치했음.
"""
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.events import Farrowing, Mating, Weaning
from app.db.models.platform import Farm
from app.db.models.sow import Sow
from app.services.kpi_service import get_trend

pytestmark = pytest.mark.anyio


async def test_trend_psy_uses_weaned_count_and_monthly_inventory(db: AsyncSession, test_farm: Farm):
    """활성 10두 · 당월 이유 자돈수 40(4건x10) -> PSY = (40/10)x12 = 48.0.

    * 2026-09-01 정정 - 이 테스트는 원래 `2026-06` 을 하드코딩했다.
      `get_trend(months=3)` 창이 날짜와 함께 움직이므로 8월까지는 우연히 통과하다가
      9월 1일에 6월이 창 밖으로 나가 깨졌다(`['2026-07','2026-08','2026-09']`).
      산식 회귀가 아니라 **테스트의 날짜 의존성**이었다.
      이제 기준월을 실행일에서 계산한다 - 언제 돌려도 같은 것을 검증한다.
    """
    today = date.today()
    this_month = today.replace(day=1)          # 당월 1일 - 월 경계에서도 안전
    period = this_month.strftime("%Y-%m")
    # 재고 계산은 월초 시점 entry_date 를 본다 -> 충분히 과거로 둔다.
    entry = datetime(this_month.year - 2, 1, 1, tzinfo=UTC)

    sows = [
        Sow(farm_id=test_farm.id, ear_tag=f"S-{uuid.uuid4().hex[:6].upper()}", parity=1,
            status="OPEN", entry_date=entry, entry_type="GILT")
        for _ in range(10)
    ]
    for s in sows:
        db.add(s)
    await db.flush()

    farrowed = this_month - timedelta(days=25)
    m = Mating(farm_id=test_farm.id, sow_id=sows[0].id,
               mating_date=farrowed - timedelta(days=115),
               mating_type="AI", mating_number=1)
    db.add(m)
    await db.flush()
    f = Farrowing(farm_id=test_farm.id, sow_id=sows[0].id, mating_id=m.id,
                  farrowing_date=farrowed, total_born=12, born_alive=12,
                  stillborn=0, mummified=0, nursing_head=12)
    db.add(f)
    await db.flush()
    # 당월 이유 4건 x 10두 = 40
    for _ in range(4):
        db.add(Weaning(farm_id=test_farm.id, sow_id=sows[0].id, farrowing_id=f.id,
                       weaning_date=this_month, weaned_count=10))
    await db.flush()

    trend = await get_trend(db, test_farm.id, months=3)
    cur = next((t for t in trend if t.period == period), None)
    assert cur is not None, (period, [t.period for t in trend])
    assert cur.psy == pytest.approx(48.0, abs=0.1), (
        f"당월 이유자돈 40/활성 10 x12 = 48.0 이어야 함(옛 건수기반이면 4.8), got {cur.psy}"
    )
    # HOTFIX(2026-08-27): 트렌드 npd는 WEI 오노출이라 응답에서 항상 null. 실호출로 억제 확인.
    assert all(t.npd is None for t in trend), \
        f"트렌드 npd는 전 기간 null이어야 함(WEI 오노출 억제), got {[(t.period, t.npd) for t in trend]}"


async def test_trend_psy_frozen_as_of_2026_06(db: AsyncSession, test_farm: Farm):
    """원래 회귀 fixture(2026-06 하드코딩) 를 **기준일 고정** 으로 복원한다.

    751aad5 는 기준월을 실행일에서 계산하도록 바꿔 날짜 의존을 없앴다 — 옳지만, 그 결과 처음 회귀를
    잡았던 고정 시나리오(2025-06 입식 · 2026-05-20 분만 · 2026-06-15 이유 x4) 자체는 스위트에서 사라졌다.
    `get_trend` 는 `as_of` 를 받고 계산 SQL 안에서 CURRENT_DATE 를 읽지 않는다(kpi_service:721-).
    그러므로 freezegun 없이 `as_of=2026-06-30` 으로 그 시나리오를 언제 돌려도 같은 결과로 검증한다.
    검증 대상(이유자돈 40 / 활성 10 x12 = 48.0, 건수기반이면 4.8)은 원본과 같다.
    """
    as_of = date(2026, 6, 30)
    sows = [
        Sow(farm_id=test_farm.id, ear_tag=f"S-{uuid.uuid4().hex[:6].upper()}", parity=1,
            status="OPEN", entry_date=datetime(2025, 6, 1, tzinfo=UTC), entry_type="GILT")
        for _ in range(10)
    ]
    for s in sows:
        db.add(s)
    await db.flush()
    m = Mating(farm_id=test_farm.id, sow_id=sows[0].id, mating_date=date(2026, 2, 1),
               mating_type="AI", mating_number=1)
    db.add(m)
    await db.flush()
    f = Farrowing(farm_id=test_farm.id, sow_id=sows[0].id, mating_id=m.id,
                  farrowing_date=date(2026, 5, 20), total_born=12, born_alive=12,
                  stillborn=0, mummified=0, nursing_head=12)
    db.add(f)
    await db.flush()
    for _ in range(4):
        db.add(Weaning(farm_id=test_farm.id, sow_id=sows[0].id, farrowing_id=f.id,
                       weaning_date=date(2026, 6, 15), weaned_count=10))
    await db.flush()

    trend = await get_trend(db, test_farm.id, months=3, as_of=as_of)
    assert [t.period for t in trend] == ["2026-04", "2026-05", "2026-06"], [t.period for t in trend]
    jun = next(t for t in trend if t.period == "2026-06")
    assert jun.psy == pytest.approx(48.0, abs=0.1), (
        f"2026-06: 이유자돈 40/활성 10 x12 = 48.0 이어야 함(옛 건수기반이면 4.8), got {jun.psy}"
    )
    # 이유가 없는 달은 0 — 창 안의 다른 달에 값이 새지 않는다
    assert all((t.psy or 0) == 0 for t in trend if t.period != "2026-06"), [(t.period, t.psy) for t in trend]
    assert all(t.npd is None for t in trend)
