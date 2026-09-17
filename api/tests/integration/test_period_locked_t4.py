"""
TRACK4 게이트 C — PeriodLockedError 409→423 일관화.
잠긴 기간 이벤트 가드(_ensure_period_unlocked)가 PeriodLockedError(HTTP 423)를 던지는지.
죽은 409/ raw HTTPException 제거 확인.
"""
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PeriodLockedError
from app.db.models.ops import PeriodLock
from app.db.models.platform import Farm, User
from app.services.event_service import _ensure_period_unlocked

pytestmark = pytest.mark.anyio


def test_period_locked_error_is_423():
    """명명 예외 상태코드 = 423 (Locked), 409 아님."""
    assert PeriodLockedError.status_code == 423
    assert PeriodLockedError("x").status_code == 423
    assert PeriodLockedError.code == "PERIOD_LOCKED"


async def _lock(db, farm, user, *, y=2026, m=3, unlocked=False):
    db.add(PeriodLock(farm_id=farm.id, period_year=y, period_month=m, locked_by=user.id,
                      unlocked_at=datetime.now(UTC) if unlocked else None))
    await db.flush()


async def test_locked_month_raises_423(db: AsyncSession, test_farm: Farm, test_user: User):
    await _lock(db, test_farm, test_user, y=2026, m=3)
    with pytest.raises(PeriodLockedError) as ei:
        await _ensure_period_unlocked(db, test_farm.id, date(2026, 3, 15))
    assert ei.value.status_code == 423


async def test_unlocked_month_passes(db: AsyncSession, test_farm: Farm, test_user: User):
    await _lock(db, test_farm, test_user, y=2026, m=3)
    # 다른 달은 잠금 아님 → 통과
    await _ensure_period_unlocked(db, test_farm.id, date(2026, 4, 15))


async def test_explicitly_unlocked_passes(db: AsyncSession, test_farm: Farm, test_user: User):
    await _lock(db, test_farm, test_user, y=2026, m=5, unlocked=True)
    await _ensure_period_unlocked(db, test_farm.id, date(2026, 5, 10))
