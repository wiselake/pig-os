"""ADR-KPI-00 I-1 — 국가 정책을 바꿔도 계산값은 바뀌지 않는다.

## 왜 이 파일이 따로 필요한가

`test_us_template_lock.py` 의 L1~L6 은 ADR-KPI-00 의 불변식 중 **I-2~I-6 만**
덮는다.

    L1  데이터만으로 표시 집합이 결정된다        → I-2 (국가 추가 = INSERT 뿐)
    L2  순서·현지 라벨이 데이터대로 나온다        → I-2
    L3  미지정 축은 GLOBAL 을 상속한다            → I-3
    L4  다른 국가 행이 새지 않는다                → I-4
    L5  미승인 행은 무시된다                      → I-5
    L6  발효 전·만료 행은 무시된다                → I-6

정작 **I-1 — 표시 정책을 바꿔도 계산값은 그대로다 — 를 확인하는 테스트가 없었다.**

I-1 이 이 아키텍처의 하중을 지는 명제다. 이것이 깨지면 "엔진은 하나, 정책만
여럿" 이라는 말 자체가 성립하지 않는다. 국가마다 다른 숫자가 나오면 그건
정책 분리가 아니라 그냥 국가별 분기다.

가장 가까운 기존 테스트(`test_global_visible_minimum.py:70`)는
`compute_enabled` 가 True 로 유지되는지만 본다 — **시드의 형상**이지
계산 결과가 실제로 같은지가 아니다.

## 이 파일이 잠그는 것

    같은 농장 · 같은 이벤트 · 같은 as_of 에 대해
    국가를 바꾸거나 표시 정책(순서·현지 라벨·표시군)을 바꿔도
    KPI 의 **수치**는 비트 단위로 동일하다.

★ 검증 대상은 "값이 같다" 이지 "정책이 무시된다" 가 아니다. 정책은 표시·판정에
  분명히 영향을 준다(그게 CKP/CKPRES 의 존재 이유다). 영향을 주면 **안 되는**
  곳이 계산이다.
"""
from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.events import Farrowing, Mating, Weaning
from app.db.models.kpi_policy import CountryKpiPolicy
from app.db.models.kpi_presentation import CountryKpiPresentation
from app.db.models.platform import Farm
from app.db.models.sow import Sow
from app.services.kpi_policy_resolver import resolve_display_kpis
from app.services.kpi_service import calculate_npd, calculate_psy

pytestmark = pytest.mark.anyio

AS_OF = date(2026, 1, 1)


async def _stocked_farm(db: AsyncSession, farm: Farm) -> None:
    """완결 사이클 2건을 가진 경산 모돈 1두. 값 자체보다 '재현 가능한 값'이 목적이다."""
    sow = Sow(farm_id=farm.id, ear_tag="OEMP-1", parity=2, status="OPEN",
              entry_date=datetime(2024, 6, 1, tzinfo=UTC), entry_type="PURCHASE")
    db.add(sow)
    await db.flush()

    for mate, farrow, wean in (
        (date(2025, 1, 11), date(2025, 5, 5), date(2025, 5, 29)),
        (date(2025, 6, 5), date(2025, 9, 27), date(2025, 10, 21)),
    ):
        m = Mating(farm_id=farm.id, sow_id=sow.id, mating_date=mate,
                   mating_type="AI", mating_number=1)
        db.add(m)
        await db.flush()
        f = Farrowing(farm_id=farm.id, sow_id=sow.id, mating_id=m.id, farrowing_date=farrow,
                      total_born=12, born_alive=12, stillborn=0, mummified=0, nursing_head=12)
        db.add(f)
        await db.flush()
        db.add(Weaning(farm_id=farm.id, sow_id=sow.id, farrowing_id=f.id,
                       weaning_date=wean, weaned_count=11))
        await db.flush()


def _policy(kpi: str, *, country: str | None = None, role: str = "PRIMARY") -> CountryKpiPolicy:
    return CountryKpiPolicy(
        scope_level="COUNTRY" if country else "GLOBAL", country_code=country,
        kpi_code=kpi, compute_enabled=True, display_role=role,
        rule_enabled=True, benchmark_exposure="CONTEXT_ONLY", prediction_feature=False,
        api_export_policy="TENANT_ONLY", decision_status="APPROVED", decided_by="test",
    )


async def _measure(db: AsyncSession, farm: Farm) -> tuple:
    """계산 층만 호출한다 — 정책 층을 거치지 않는 순수 수치."""
    return (await calculate_psy(db, farm.id, AS_OF), await calculate_npd(db, farm.id, AS_OF))


# ── I-1 핵심 ────────────────────────────────────────────────────────────────

async def test_country_does_not_change_the_computed_value(db: AsyncSession, test_farm: Farm):
    """★ 하중을 지는 명제.

    같은 농장·같은 이벤트에서 농장 국가만 바꿔가며 계산한다. 값이 달라지면
    계산이 국가로 분기하고 있다는 뜻이고, ADR-KPI-00 은 무효가 된다."""
    await _stocked_farm(db, test_farm)
    baseline = await _measure(db, test_farm)

    for country in ("US", "BR", "VN", "MX", "CN", "ZZ"):
        test_farm.country = country
        await db.flush()
        assert await _measure(db, test_farm) == baseline, (
            f"국가를 {country} 로 바꾸자 계산값이 달라졌다 — 엔진이 국가로 분기한다"
        )


async def test_presentation_rows_do_not_change_the_computed_value(
    db: AsyncSession, test_farm: Farm,
):
    """표현 정책(순서·현지 라벨)은 계산에 닿지 않는다."""
    await _stocked_farm(db, test_farm)
    test_farm.country = "BR"
    await db.flush()
    baseline = await _measure(db, test_farm)

    db.add(_policy("PSY", country="BR"))
    db.add(CountryKpiPresentation(
        scope_level="COUNTRY", country_code="BR", kpi_code="PSY",
        display_order=1, display_order_override=True, local_label="Leitões Desmamados",
        decision_status="APPROVED",
    ))
    await db.flush()

    assert await _measure(db, test_farm) == baseline, (
        "현지 라벨·순서를 넣었더니 수치가 바뀌었다 — 표현이 계산에 새고 있다"
    )


async def test_hiding_a_kpi_does_not_change_what_it_computes(
    db: AsyncSession, test_farm: Farm,
):
    """★ 표시를 숨겨도 계산은 유지된다 — 그리고 **같은 값**이어야 한다.

    `compute_enabled` 가 True 로 남는지(기존 테스트)와 계산 결과가 같은지는
    다른 질문이다. 여기서는 후자를 본다."""
    await _stocked_farm(db, test_farm)
    test_farm.country = "US"
    await db.flush()
    baseline = await _measure(db, test_farm)

    db.add(_policy("PSY", country="US", role="HIDDEN"))
    await db.flush()

    assert await _measure(db, test_farm) == baseline, (
        "표시군을 HIDDEN 으로 바꿨더니 계산값이 달라졌다"
    )


# ── 대조군 — 정책이 아무 데도 영향을 못 준다면 그것도 결함이다 ──────────────

async def test_policy_does_change_what_is_displayed(db: AsyncSession):
    """★ 위 세 테스트가 '정책이 무시된다' 로 통과하면 안 된다.

    정책은 **표시에는 반드시** 영향을 준다. 그 영향이 계산에만 닿지 않는 것이
    ADR-KPI-00 이다. 대조군이 없으면 위 테스트들은 아무것도 증명하지 못한다."""
    db.add(_policy("PSY"))
    db.add(_policy("NPD"))
    await db.flush()
    before = {r.kpi_code for r in await resolve_display_kpis(db, country="US")}
    assert "NPD" in before, "GLOBAL PRIMARY 인데 표시 집합에 없다 — 전제가 깨졌다"

    db.add(_policy("NPD", country="US", role="HIDDEN"))
    await db.flush()
    after = {r.kpi_code for r in await resolve_display_kpis(db, country="US")}

    assert "NPD" not in after, "COUNTRY HIDDEN 을 넣었는데 표시 집합이 그대로다"
    assert "PSY" in after, "숨기지 않은 지표까지 사라졌다"
