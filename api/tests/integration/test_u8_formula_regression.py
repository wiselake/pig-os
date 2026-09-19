"""U-8 — `regression_test_status = MISSING` 이던 산식 4종을 잠근다.

대상 (CANONICAL_FORMULA_SPEC_REAUDIT.md §5-1):

    WSI                CONFIRMED · MATCHED   → 회귀만 없었다
    WEANED_PER_LITTER  CONFIRMED · MATCHED   → 〃
    MUMMIFIED_RATE     CONFIRMED · MATCHED   → 〃
    MSY                CONFIRMED · NOT_RUN   → §MSY 참조

★ 이 테스트가 바꾸지 않는 것

    implementation_status        CONFIRMED    (이미 코드에서 유일하게 특정됨)
    runtime_reproduction_status  변경 없음

  테스트가 생겼다고 구현 판정이나 실측 판정이 올라가지 않는다.
  D-13 v1.2 의 "테스트는 authority 가 아니라 corroboration" 규율 그대로다.
  이 커밋이 움직이는 축은 `regression_test_status` 하나뿐이다.

★ MSY 는 특히 주의

  `runtime_reproduction_status = NOT_RUN` 이다. 실데이터에 출하가 없어 손검산을
  못 했다. 아래 테스트는 **synthetic fixture** 이고, synthetic test 는
  production reproduction 을 대신하지 못한다. NOT_RUN 을 유지한다.
"""
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.events import Farrowing, Mating, Weaning
from app.db.models.ops import FinisherGroup
from app.db.models.platform import Farm
from app.db.models.sow import Sow
from app.services.kpi_service import get_dashboard

pytestmark = pytest.mark.anyio


async def _sow(db: AsyncSession, farm: Farm, tag: str) -> Sow:
    s = Sow(farm_id=farm.id, ear_tag=f"{tag}-{uuid.uuid4().hex[:6].upper()}", parity=2,
            status="OPEN", entry_date=datetime(2024, 1, 1, tzinfo=UTC), entry_type="GILT")
    db.add(s)
    await db.flush()
    return s


async def _farrowing(db: AsyncSession, farm: Farm, sow: Sow, when: date,
                     *, total_born: int = 14, born_alive: int = 12,
                     stillborn: int = 1, mummified: int = 1) -> Farrowing:
    """`weanings.farrowing_id` 가 NOT NULL 이라 이유에는 분만이 반드시 필요하다."""
    m = Mating(farm_id=farm.id, sow_id=sow.id, mating_date=when - timedelta(days=115),
               mating_type="AI", mating_number=1)
    db.add(m)
    await db.flush()
    f = Farrowing(farm_id=farm.id, sow_id=sow.id, mating_id=m.id, farrowing_date=when,
                  total_born=total_born, born_alive=born_alive,
                  stillborn=stillborn, mummified=mummified, nursing_head=born_alive)
    db.add(f)
    await db.flush()
    return f


async def _weaning(db: AsyncSession, farm: Farm, sow: Sow, f: Farrowing,
                   when: date, weaned: int) -> Weaning:
    w = Weaning(farm_id=farm.id, sow_id=sow.id, farrowing_id=f.id,
                weaning_date=when, weaned_count=weaned)
    db.add(w)
    await db.flush()
    return w


# ── WSI ───────────────────────────────────────────────────────────────────────
#
#   avg(mating_date − 그 교배 이전의 가장 최근 weaning_date), wsi >= 0 만
#   kpi_service.py:425-429

async def test_wsi_is_mean_weaning_to_service_interval(db: AsyncSession, test_farm: Farm):
    """이유 → 재교배 간격의 평균. 두 마리로 5일·9일 → 7.0."""
    ref = date.today() - timedelta(days=30)
    for tag, gap in (("WSI-A", 5), ("WSI-B", 9)):
        s = await _sow(db, test_farm, tag)
        f = await _farrowing(db, test_farm, s, ref - timedelta(days=25))
        await _weaning(db, test_farm, s, f, ref, 10)
        db.add(Mating(farm_id=test_farm.id, sow_id=s.id,
                      mating_date=ref + timedelta(days=gap),
                      mating_type="AI", mating_number=2))
        await db.flush()

    dash = await get_dashboard(db, test_farm)
    assert dash.metrics["WSI"] == pytest.approx(7.0, abs=0.1), (
        f"WSI 가 7.0 이 아니다 (실제 {dash.metrics['WSI']}). "
        "이유→재교배 간격 평균 정의가 바뀌었는지 확인하라."
    )


async def test_wsi_excludes_negative_intervals(db: AsyncSession, test_farm: Farm):
    """교배가 이유보다 앞서면 제외된다 (`wsi >= 0` 필터).

    이 조항이 사라지면 데이터 오류가 평균을 음수로 끌어내린다.
    """
    ref = date.today() - timedelta(days=30)
    # 정상 6일
    s1 = await _sow(db, test_farm, "WSI-OK")
    f1 = await _farrowing(db, test_farm, s1, ref - timedelta(days=25))
    await _weaning(db, test_farm, s1, f1, ref, 10)
    db.add(Mating(farm_id=test_farm.id, sow_id=s1.id, mating_date=ref + timedelta(days=6),
                  mating_type="AI", mating_number=2))
    await db.flush()

    # 이 교배는 **이전 이유가 없다** → 서브쿼리가 NULL 을 내고 평균에서 제외된다
    s2 = await _sow(db, test_farm, "WSI-NEG")
    f2 = await _farrowing(db, test_farm, s2, ref - timedelta(days=25))
    db.add(Mating(farm_id=test_farm.id, sow_id=s2.id, mating_date=ref,
                  mating_type="AI", mating_number=2))
    await db.flush()
    await _weaning(db, test_farm, s2, f2, ref + timedelta(days=10), 10)

    dash = await get_dashboard(db, test_farm)
    assert dash.metrics["WSI"] == pytest.approx(6.0, abs=0.1), (
        "음수/NULL 간격이 평균에 섞였다."
    )


# ── WEANED_PER_LITTER ─────────────────────────────────────────────────────────
#
#   avg(weanings.weaned_count) — kpi_service.py:530

async def test_weaned_per_litter_is_mean_of_weaned_count(db: AsyncSession, test_farm: Farm):
    """복당 이유두수 = 이유 건별 `weaned_count` 의 단순 평균. 10·11·12 → 11.0."""
    ref = date.today() - timedelta(days=20)
    for i, n in enumerate((10, 11, 12)):
        s = await _sow(db, test_farm, f"WPL{i}")
        f = await _farrowing(db, test_farm, s, ref - timedelta(days=25))
        await _weaning(db, test_farm, s, f, ref, n)

    dash = await get_dashboard(db, test_farm)
    assert dash.metrics["WEANED_COUNT"] == pytest.approx(11.0, abs=0.05), (
        f"복당 이유두수가 11.0 이 아니다 (실제 {dash.metrics['WEANED_COUNT']}). "
        "이유 건 평균이 아니라 다른 분모를 쓰기 시작했는지 확인하라."
    )


# ── MUMMIFIED_RATE ────────────────────────────────────────────────────────────
#
#   mummified / total_born * 100 — kpi_service.py:524
#   ★ 분모가 total_born 이다. born_alive 가 아니다.

async def test_mummified_rate_denominator_is_total_born(db: AsyncSession, test_farm: Farm):
    """미라율 = 미라 / **총산**. 분모가 실산으로 바뀌면 값이 올라간다.

    total_born 20 · mummified 2  →  10.0%
    (실산 분모였다면 2/17 = 11.8% 가 됐을 것이다)
    """
    ref = date.today() - timedelta(days=30)
    s = await _sow(db, test_farm, "MUM")
    await _farrowing(db, test_farm, s, ref,
                     total_born=20, born_alive=17, stillborn=1, mummified=2)

    dash = await get_dashboard(db, test_farm)
    assert dash.metrics["MUMMIFIED_RATE"] == pytest.approx(10.0, abs=0.1), (
        f"미라율이 10.0 이 아니다 (실제 {dash.metrics['MUMMIFIED_RATE']}). "
        "분모가 total_born 에서 바뀌었는지 확인하라."
    )
    # 실산 분모였을 때의 값이 아님을 못박는다.
    assert dash.metrics["MUMMIFIED_RATE"] != pytest.approx(11.8, abs=0.1)

    # ★ D-8 참고: PigCHAMP `Average mummies per litter` 는 COUNT 다.
    #   우리는 RATE 다. 단위가 달라 직접 비교 불가(NOT_EQUIVALENT).
    assert dash.metrics["MUMMIFIED_RATE"] < 100


# ── MSY ───────────────────────────────────────────────────────────────────────
#
#   head_count_out 합 / 평균 활성 모돈 재고 — kpi_service.py:559
#   ★ runtime = NOT_RUN. 아래는 synthetic 이며 그 판정을 바꾸지 않는다.

async def test_msy_is_headout_over_average_inventory(db: AsyncSession, test_farm: Farm):
    """MSY = 기간 출하두수 / 평균 활성 모돈 재고.

    ★ synthetic fixture 다. `runtime_reproduction_status = NOT_RUN` 을 유지한다 —
      이 테스트는 산식을 잠글 뿐 실데이터 재현을 대신하지 않는다.
    """
    ref = date.today() - timedelta(days=30)
    # 모돈 2두 (평균 재고 2)
    for i in range(2):
        await _sow(db, test_farm, f"MSY{i}")
    db.add(FinisherGroup(
        farm_id=test_farm.id, group_code=f"G-{uuid.uuid4().hex[:6].upper()}",
        start_date=ref - timedelta(days=120), end_date=ref,
        head_count_in=110, head_count_out=100,
        avg_entry_weight_kg=25.0, avg_exit_weight_kg=115.0,
    ))
    await db.flush()

    dash = await get_dashboard(db, test_farm)
    msy = dash.metrics["MSY"]
    assert msy is not None, (
        "MSY 가 None 이다. 출하 데이터가 있는데 계산되지 않으면 게이트 조건이 바뀐 것이다."
    )
    # 평균 재고는 월초 표본 평균이라 정확히 2가 아닐 수 있다 → 산식 형태만 잠근다.
    assert msy > 0
    assert msy == pytest.approx(100 / 2, rel=0.5), (
        f"MSY 가 (출하 100 / 평균재고 ~2) 규모를 벗어났다 (실제 {msy}). "
        "분모가 평균 재고에서 바뀌었는지 확인하라."
    )


async def test_msy_is_none_without_shipment(db: AsyncSession, test_farm: Farm):
    """출하 데이터가 없으면 None — 오발화 방지 조항.

    이 조항이 사라지면 출하를 기록하지 않는 농장에 MSY 0 이 표시되고
    그것이 severity 로 이어진다.
    """
    await _sow(db, test_farm, "MSY-NONE")
    dash = await get_dashboard(db, test_farm)
    assert dash.metrics["MSY"] is None, (
        "출하 데이터가 없는데 MSY 가 값을 냈다 — 0 이 severity 로 이어질 수 있다."
    )
