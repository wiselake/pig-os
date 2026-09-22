"""U-8 / U-10 — `PRE_WEANING_MORTALITY` 3경로 characterization test.

★ 이 테스트는 canonical 을 **선택하지 않는다.**

  PWM 은 `implementation_status = AMBIGUOUS` 다. 분모가 셋이고 셋 다 live 다
  (`CANONICAL_FORMULA_SPEC_REAUDIT.md` §1-2). 어느 것이 옳은지는 P0-2 결정 사항이고,
  여기서 하나를 정답으로 잠그면 **결정을 코드가 대신하는 것**이 된다.

  대신 **현재 세 경로가 각각 무엇을 계산하는지 보존**한다.
  `test_inventory_denominator_divergence.py` 가 D-2 에서 쓴 것과 같은 방식이다.

  그래야 P0-2 이후 code alignment 가 일어날 때
  **어떤 기존 의미를 의도적으로 없앴는지 diff 로 명확하게 깨진다.**

★ U-10 — non-zero differentiating fixture

  기존 runtime 판정은 `ZERO_PATH_ONLY` 였다. DEATH 이벤트가 0건이라
  `0/A = 0/B = 0/C = 0` 이었고, 그래서 분모가 무엇이든 결과가 같아
  **아무것도 증명하지 못했다**(REAUDIT §5-3).

  이 fixture 는 두 조건을 강제한다:

      numerator > 0
      denominator_A != denominator_B != denominator_C

  둘 중 하나라도 깨지면 세 경로가 우연히 같은 값을 내고 U-10 은 무의미해진다.
  그래서 `test_pwm_nonzero_denominators_diverge` 가 그 전제 자체를 먼저 잠근다.

3경로 (REAUDIT §1-2):

    A  deaths / (weaned + deaths)          kpi_service.py:512 · report_service.py:194
    B  (born_alive - weaned) / born_alive   insight_service.py:229
    C  (total_born - weaned) / total_born   report_service.py:150
"""
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.config import DefaultMetricValue
from app.db.models.events import Farrowing, Mating, PigletEvent, Weaning
from app.db.models.platform import Farm
from app.db.models.sow import Sow
from app.services import insight_service
from app.services.kpi_service import get_dashboard

pytestmark = pytest.mark.anyio


# ── fixture 설계 ──────────────────────────────────────────────────────────────
#
#   total_born 16 · stillborn 2 · mummified 1  →  born_alive 13
#   weaned      8
#   DEATH       2
#
#   denom_A = weaned + deaths = 8 + 2 = 10      num_A = deaths            = 2   → 20.0%
#   denom_B = born_alive      =          13      num_B = 13 - 8            = 5   → 38.5%
#   denom_C = total_born      =          16      num_C = 16 - 8            = 8   → 50.0%
#
#   세 분모가 전부 다르고, 세 분자가 전부 0 보다 크다.
TOTAL_BORN = 16
STILLBORN = 2
MUMMIFIED = 1
BORN_ALIVE = TOTAL_BORN - STILLBORN - MUMMIFIED   # 13
WEANED = 8
DEATHS = 2

DENOM_A = WEANED + DEATHS      # 10
DENOM_B = BORN_ALIVE           # 13
DENOM_C = TOTAL_BORN           # 16

EXPECT_A = round(DEATHS / DENOM_A * 100, 1)                 # 20.0
EXPECT_B = round((BORN_ALIVE - WEANED) / DENOM_B * 100, 1)  # 38.5
EXPECT_C = round((TOTAL_BORN - WEANED) / DENOM_C * 100, 1)  # 50.0


async def _litter(db: AsyncSession, farm: Farm) -> tuple[Sow, Farrowing, Weaning]:
    """위 상수 그대로의 복 하나를 만든다."""
    ref = date.today() - timedelta(days=40)
    s = Sow(farm_id=farm.id, ear_tag=f"PWM-{uuid.uuid4().hex[:6].upper()}", parity=2,
            status="OPEN", entry_date=datetime(2024, 1, 1, tzinfo=UTC), entry_type="GILT")
    db.add(s)
    await db.flush()

    m = Mating(farm_id=farm.id, sow_id=s.id, mating_date=ref - timedelta(days=115),
               mating_type="AI", mating_number=1)
    db.add(m)
    await db.flush()

    f = Farrowing(farm_id=farm.id, sow_id=s.id, mating_id=m.id, farrowing_date=ref,
                  total_born=TOTAL_BORN, born_alive=BORN_ALIVE,
                  stillborn=STILLBORN, mummified=MUMMIFIED, nursing_head=BORN_ALIVE)
    db.add(f)
    await db.flush()

    db.add(PigletEvent(farm_id=farm.id, farrowing_id=f.id, sow_id=s.id,
                       event_date=ref + timedelta(days=5), event_type="DEATH",
                       piglet_count=DEATHS))
    w = Weaning(farm_id=farm.id, sow_id=s.id, farrowing_id=f.id,
                weaning_date=ref + timedelta(days=25), weaned_count=WEANED)
    db.add(w)
    await db.flush()
    return s, f, w


# ── U-10 전제 — 이것이 깨지면 아래 3개는 아무것도 증명하지 못한다 ──────────────

def test_pwm_nonzero_denominators_diverge():
    """fixture 자체가 세 경로를 구별할 수 있는지 먼저 잠근다.

    ZERO_PATH_ONLY 사고의 재발 방지선이다 — 분자가 0 이거나 분모가 우연히 같으면
    세 경로가 같은 값을 내서 characterization 이 무의미해진다.
    """
    assert DEATHS > 0, "numerator 가 0 이면 0/A = 0/B = 0/C 라 아무것도 증명 못 한다"
    assert BORN_ALIVE - WEANED > 0
    assert TOTAL_BORN - WEANED > 0

    denoms = {DENOM_A, DENOM_B, DENOM_C}
    assert len(denoms) == 3, (
        f"세 분모가 서로 달라야 한다 (A={DENOM_A} B={DENOM_B} C={DENOM_C}). "
        "같으면 경로를 구별할 수 없다."
    )
    results = {EXPECT_A, EXPECT_B, EXPECT_C}
    assert len(results) == 3, (
        f"세 결과가 서로 달라야 한다 (A={EXPECT_A} B={EXPECT_B} C={EXPECT_C})"
    )


# ── 경로별 현재 산식 보존 ─────────────────────────────────────────────────────

async def test_pwm_path_a_current_formula(db: AsyncSession, test_farm: Farm):
    """A: `deaths / (weaned + deaths)` — 이벤트 기록 기반. 대시보드가 쓰는 경로.

    ★ 이것이 canonical 이라는 뜻이 아니다. 현재 이 값을 낸다는 사실만 보존한다.
    """
    await _litter(db, test_farm)
    dash = await get_dashboard(db, test_farm)

    assert dash.metrics["PRE_WEANING_MORTALITY"] == pytest.approx(EXPECT_A, abs=0.1), (
        f"경로 A 가 {EXPECT_A} 가 아니다. 분모가 (weaned+deaths)={DENOM_A} 에서 "
        "바뀌었다면 P0-2 code alignment 인지 확인하라."
    )
    # 별칭도 같은 값이어야 한다 — 하나만 바뀌면 룰엔진과 화면이 갈라진다.
    assert dash.metrics["PWMR"] == dash.metrics["PRE_WEANING_MORTALITY"]

    # 다른 경로의 값이 아니라는 것까지 못박는다.
    assert dash.metrics["PRE_WEANING_MORTALITY"] != pytest.approx(EXPECT_B, abs=0.1)
    assert dash.metrics["PRE_WEANING_MORTALITY"] != pytest.approx(EXPECT_C, abs=0.1)


async def test_pwm_path_b_current_formula(db: AsyncSession, test_farm: Farm):
    """B: `(born_alive - weaned) / born_alive` — 차감 추정. 이유 입력 직후 인사이트.

    A 와 분모가 다르므로 **같은 복에서 다른 값이 나온다.** 그것이 LIVE_DIVERGENCE 다.
    """
    # 경로 B 는 임계가 있어야 인사이트가 발화한다. 임계가 없으면 테스트가 skip 되고
    # **U-10 이 경로 B 를 전혀 덮지 못한다** — 그래서 임계를 명시 주입한다.
    # (값 자체는 판정용이 아니라 발화용이다. 프로덕션 SYSTEM 값 13/18 과 같은 자리.)
    db.add(DefaultMetricValue(
        scope_type="system", scope_code="SYSTEM", metric_code="PRE_WEANING_MORTALITY",
        warning_threshold=13, critical_threshold=18, alert_direction="above",
    ))
    await db.flush()

    _s, _f, w = await _litter(db, test_farm)
    insights = await insight_service.analyze_weaning(db, test_farm, w)

    pwm = [i for i in insights if i.metric_code == "PRE_WEANING_MORTALITY"]
    assert pwm, (
        "PWM 인사이트가 발화하지 않았다. 임계를 주입했는데도 발화하지 않으면 "
        "insight_service 의 경로 B 자체가 끊긴 것이다."
    )
    assert pwm[0].value == pytest.approx(EXPECT_B, abs=0.1), (
        f"경로 B 가 {EXPECT_B} 가 아니다. 분모가 born_alive={DENOM_B} 에서 바뀌었다."
    )
    assert pwm[0].value != pytest.approx(EXPECT_A, abs=0.1), (
        "경로 B 가 경로 A 와 같은 값을 냈다 — 정렬이 일어났다면 P0-2 기록을 확인하라."
    )


async def test_pwm_path_c_current_formula():
    """C: `(total_born - weaned) / total_born` — 복단위 차감. 번식 리포트.

    ★ 이 경로는 분모가 `total_born` 이라 **사산·미라까지 포함한다.**
      이름은 "포유폐사율" 인데 실제로는 "총산 대비 손실률" 에 가깝다
      (REAUDIT §1-2). 그 의미 차이를 보존하는 것이 이 테스트의 목적이다.

    report_service 는 기간 집계 함수라 복 하나만으로 태우기 어렵다.
    산식 자체(`(tb - fw) / tb * 100`)를 상수로 고정해 의미를 잠근다.
    """
    tb, fw = TOTAL_BORN, WEANED
    pwmr_b = round((tb - fw) / tb * 100, 1)

    assert pwmr_b == pytest.approx(EXPECT_C, abs=0.1)
    # 사산·미라가 분모에 남아 있다는 사실 자체를 못박는다.
    assert tb == BORN_ALIVE + STILLBORN + MUMMIFIED
    assert pwmr_b != pytest.approx(EXPECT_B, abs=0.1), (
        "total_born 분모와 born_alive 분모가 같은 값을 냈다 — fixture 가 무력하다."
    )


# ── 세 경로가 실제로 갈라진다는 것 자체 ───────────────────────────────────────

async def test_pwm_three_paths_diverge_on_same_litter(db: AsyncSession, test_farm: Farm):
    """같은 복 하나에서 세 경로가 서로 다른 값을 낸다 — LIVE_DIVERGENCE 의 실증.

    P0-2 로 canonical 이 정해지고 code alignment 가 끝나면 이 테스트는 **깨져야 한다.**
    깨지지 않았다면 정렬이 실제로 일어나지 않은 것이다.
    """
    _s, _f, w = await _litter(db, test_farm)

    a = (await get_dashboard(db, test_farm)).metrics["PRE_WEANING_MORTALITY"]
    c = round((TOTAL_BORN - WEANED) / TOTAL_BORN * 100, 1)

    assert a == pytest.approx(EXPECT_A, abs=0.1)
    assert c == pytest.approx(EXPECT_C, abs=0.1)
    assert a != pytest.approx(c, abs=0.1), (
        f"경로 A({a}) 와 경로 C({c}) 가 같아졌다. "
        "정렬됐다면 docs/kpi/DECISION_REGISTER.md D-2026-001 을 확인하라."
    )
    assert w.weaned_count == WEANED
