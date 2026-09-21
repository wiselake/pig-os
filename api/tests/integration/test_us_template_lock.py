"""US Template LOCK 수용 게이트 (L1~L6).

## 이 파일이 검증하는 명제

    "국가를 하나 추가하는 데 **로직 코드 변경이 0** 이어야 한다."

COUNTRY_PRODUCT_SPEC_INDEX.md §4: "US 는 Template LOCK 의 시험대이기도 하다 —
코드 변경 0으로 데이터만 넣어서 되는지가 이 구조 전체의 합격 기준이다."

★ 그래서 이 테스트는 **`us_pilot_seed.py` 같은 모듈을 만들지 않는다.** 만들면 증명이
  약해진다 — "새 시드 모듈을 작성했더니 됐다"는 코드를 쓴 것이고, LOCK 이 묻는 건
  "아무것도 안 써도 되느냐"다. 그래서 행(row)을 테스트 안에서 리터럴로 만들어
  DB 에 넣는다. 이게 통과하면 US 활성화에 필요한 것은 **INSERT 문 뿐**임이 증명된다.

  같은 이유로 여기 쓰인 US 값은 **제품 결정이 아니다.** 임의의 형상이며 seed 로
  승격하면 안 된다. 실제 US 지표·현지명은 Decision Register APPROVED 후 별도로 넣는다.

## 왜 P2/P3(threshold 44·신규 47)보다 먼저인가

대표 확정 순서: "US Template LOCK 이 실패하면 44/47 작업은 중단하는 게 맞습니다."
LOCK 이 깨져 있으면 국가마다 로직을 고쳐야 한다는 뜻이고, 그 상태에서 룰을 44개
얹으면 그 부채가 44배로 복제된다. 그래서 여기가 먼저다.

## 게이트

    L1  데이터만으로 US 표시 집합이 결정되는가
    L2  순서·현지 라벨이 데이터대로 나오는가
    L3  US 가 지정하지 않은 축은 GLOBAL 을 상속하는가
    L4  ★ 다른 국가(KR/BR) 행이 US 로 새지 않는가 — 폴백 금지
    L5  미승인 행이 무시되는가 (fail-closed)
    L6  발효기간 밖 행이 무시되는가
"""
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.global_policy_defaults import GLOBAL_HIDDEN, GLOBAL_VISIBLE
from app.db.global_presentation_seed import presentation_rows as global_presentation_rows
from app.db.models.kpi_policy import CountryKpiPolicy
from app.db.models.kpi_presentation import CountryKpiPresentation
from app.services.kpi_policy_resolver import (
    pick_headline,
    resolve_display_kpis,
)

pytestmark = pytest.mark.anyio

# ── 이 테스트가 쓰는 가상 US 형상 (제품 결정 아님 — 파일 헤더 참조) ──────────────
US = "US"
US_VISIBLE: tuple[tuple[str, int, str], ...] = (
    ("PSY", 10, "Pigs Weaned/Sow/Year"),
    ("FARROWING_RATE", 20, "Farrowing Rate"),
    ("PWMR", 30, "Pre-Wean Mortality Rate"),
)
US_HEADLINE = "PSY"
US_VISIBLE_CODES = frozenset(c for c, _, _ in US_VISIBLE)
# GLOBAL 에 있으나 US 가 명시적으로 숨기는 것. 암묵 상속으로 카드가 늘지 않게 한다.
# ★ 괄호 필수 — `-` 가 `|` 보다 먼저 묶여서 GLOBAL_VISIBLE 이 통째로 HIDDEN 이 된다.
US_HIDDEN = tuple(sorted((set(GLOBAL_VISIBLE) | set(GLOBAL_HIDDEN)) - US_VISIBLE_CODES))


def _policy(**kw) -> CountryKpiPolicy:
    """정책 행 하나. 축 기본값은 GLOBAL 이 채우므로 여기선 최소만 준다."""
    kw.setdefault("id", uuid.uuid4())
    kw.setdefault("decision_status", "APPROVED")
    kw.setdefault("decided_by", "US-TEMPLATE-LOCK-TEST")
    return CountryKpiPolicy(**kw)


def _pres(**kw) -> CountryKpiPresentation:
    kw.setdefault("id", uuid.uuid4())
    kw.setdefault("decision_status", "APPROVED")
    return CountryKpiPresentation(**kw)


async def _seed_global(db: AsyncSession) -> None:
    """GLOBAL 정책·표현. 어느 국가든 깔려 있는 바닥면."""
    for code in GLOBAL_VISIBLE:
        db.add(_policy(scope_level="GLOBAL", kpi_code=code, compute_enabled=True,
                       display_role="PRIMARY", rule_enabled=False,
                       benchmark_exposure="CONTEXT_ONLY", prediction_feature=False,
                       api_export_policy="TENANT_ONLY"))
    for code in GLOBAL_HIDDEN:
        db.add(_policy(scope_level="GLOBAL", kpi_code=code, compute_enabled=True,
                       display_role="HIDDEN", rule_enabled=False,
                       benchmark_exposure="CONTEXT_ONLY", prediction_feature=False,
                       api_export_policy="TENANT_ONLY"))
    for r in global_presentation_rows():
        db.add(_pres(**r))


async def _seed_us(db: AsyncSession) -> None:
    """★ US 를 켜는 데 필요한 전부 — INSERT 뿐이다. 코드 변경 0."""
    for code, order, label in US_VISIBLE:
        # ★ headline 은 priority_class='NORTH_STAR' 로 **명시**해야 정해진다.
        #   순서 1등이 자동으로 headline 이 되지 않는다 — 표시 순서(표현 축)와
        #   "무엇이 이 나라의 핵심 지표인가"(거버넌스 축)는 다른 결정이기 때문이다.
        db.add(_policy(scope_level="COUNTRY", country_code=US, kpi_code=code,
                       display_role="PRIMARY",
                       priority_class="NORTH_STAR" if code == US_HEADLINE else None))
        db.add(_pres(scope_level="COUNTRY", country_code=US, kpi_code=code,
                     display_order=order, display_order_override=True, local_label=label))
    for code in US_HIDDEN:
        db.add(_policy(scope_level="COUNTRY", country_code=US, kpi_code=code,
                       display_role="HIDDEN"))


async def _seed(db: AsyncSession) -> None:
    await _seed_global(db)
    await _seed_us(db)
    await db.flush()


# ── L1 ────────────────────────────────────────────────────────────────────────

async def test_l1_us_display_set_is_decided_by_data_alone(db: AsyncSession):
    """L1: US 표시 집합이 INSERT 한 행 그대로 결정된다.

    ★ 이 테스트가 통과했다는 것은 리졸버·서비스·라우터 중 **아무것도 US 를 알 필요가
      없다**는 뜻이다. 국가를 아는 코드가 하나라도 있으면 여기서 어긋난다."""
    await _seed(db)
    got = {r.kpi_code for r in await resolve_display_kpis(db, country=US)}
    assert got == US_VISIBLE_CODES, (
        f"데이터로 지정한 집합과 다르다 — 코드 어딘가가 국가를 알고 있다.\n"
        f"  기대 {sorted(US_VISIBLE_CODES)}\n  실제 {sorted(got)}")


async def test_l1_count_is_exact(db: AsyncSession):
    """부분집합 검사는 카드가 늘어난 경우를 못 잡는다 — 개수를 고정한다."""
    await _seed(db)
    assert len(await resolve_display_kpis(db, country=US)) == len(US_VISIBLE)


# ── L2 ────────────────────────────────────────────────────────────────────────

async def test_l2_order_and_local_labels_come_from_data(db: AsyncSession):
    """L2: 순서·현지 라벨이 presentation 행 그대로. headline 은 항상 첫 항목."""
    await _seed(db)
    rows = await resolve_display_kpis(db, country=US)
    assert [r.kpi_code for r in rows] == [c for c, _, _ in US_VISIBLE]
    assert [r.local_label for r in rows] == [lbl for _, _, lbl in US_VISIBLE]
    assert pick_headline(rows) == US_HEADLINE
    assert rows[0].kpi_code == US_HEADLINE


# ── L3 ────────────────────────────────────────────────────────────────────────

async def test_l3_unspecified_axes_inherit_global(db: AsyncSession):
    """L3: US 행은 display_role 만 줬다. 나머지 축은 GLOBAL 값이어야 한다.

    국가 행이 모든 축을 다 채워야 한다면 국가 추가 비용이 축 개수만큼 늘고,
    GLOBAL 축이 하나 늘 때마다 모든 국가 행을 고쳐야 한다 — LOCK 이 아니다."""
    await _seed(db)
    rows = {r.kpi_code: r for r in await resolve_display_kpis(db, country=US)}
    psy = rows["PSY"]
    assert psy.compute_enabled is True, "GLOBAL 의 compute_enabled 를 상속하지 못했다"
    assert psy.benchmark_exposure == "CONTEXT_ONLY"
    assert psy.api_export_policy == "TENANT_ONLY"


# ── L4 ★ 폴백 금지 ────────────────────────────────────────────────────────────

async def test_l4_no_fallback_from_other_countries(db: AsyncSession):
    """L4: KR·BR 행이 아무리 많아도 US 결과가 흔들리면 안 된다.

    ★ 이게 이 파일에서 가장 중요한 게이트다. 국가 행이 없을 때 다른 국가로
      떨어지는 구현이면 미국 농장에 한국 기준으로 경고가 뜬다 —
      COUNTRY_PRODUCT_SPEC_INDEX §5 가 격리한 사고가 정확히 이것이다."""
    await _seed(db)
    for other in ("KR", "BR"):
        for code in ("ADG", "FCR", "MSY"):        # US 가 숨긴 것들
            db.add(_policy(scope_level="COUNTRY", country_code=other, kpi_code=code,
                           display_role="PRIMARY"))
            db.add(_pres(scope_level="COUNTRY", country_code=other, kpi_code=code,
                         display_order=1, display_order_override=True,
                         local_label=f"{other}-라벨"))
    await db.flush()

    rows = await resolve_display_kpis(db, country=US)
    got = {r.kpi_code for r in rows}
    assert got == US_VISIBLE_CODES, f"타국 행이 US 로 샜다: {sorted(got - US_VISIBLE_CODES)}"
    leaked = [r.local_label for r in rows if r.local_label and "라벨" in r.local_label]
    assert not leaked, f"타국 현지명이 US 에 노출됐다: {leaked}"


async def test_l4_unknown_country_does_not_borrow(db: AsyncSession):
    """정책이 없는 국가는 GLOBAL 로 떨어져야 한다 — 임의의 국가를 빌리면 안 된다.

    US 는 3개 visible, GLOBAL 도 3개일 수 있다. 개수가 같아도 근거가 달라야 하므로
    **US 가 숨긴 것이 미지 국가에서는 보이는지**로 구분한다."""
    await _seed(db)
    zz = {r.kpi_code for r in await resolve_display_kpis(db, country="ZZ")}
    assert zz == set(GLOBAL_VISIBLE), f"미지 국가가 GLOBAL 이 아닌 값을 받았다: {sorted(zz)}"


# ── L5 fail-closed ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("status", ["PROPOSED", "REVIEWED", "REJECTED"])
async def test_l5_non_approved_rows_are_ignored(db: AsyncSession, status: str):
    """L5: 미승인 정책은 반영되지 않는다.

    위조 0 의 런타임 판본이다 — Decision Register 에서 APPROVED 아닌 정책이
    화면에 나타나면 결재 절차가 무의미해진다."""
    await _seed(db)
    db.add(_policy(scope_level="COUNTRY", country_code=US, kpi_code="ADG",
                   display_role="PRIMARY", decision_status=status))
    # ★ presentation 은 APPROVED 로 넣는다 — 표현이 승인돼도 **정책이 미승인이면
    #   안 보여야** 한다. 둘 다 미승인으로 두면 어느 쪽이 막았는지 구분되지 않는다.
    db.add(_pres(scope_level="COUNTRY", country_code=US, kpi_code="ADG",
                 display_order=5, display_order_override=True,
                 local_label="Average Daily Gain", decision_status="APPROVED"))
    await db.flush()
    got = {r.kpi_code for r in await resolve_display_kpis(db, country=US)}
    assert "ADG" not in got, f"{status} 행이 반영됐다 — fail-closed 위반"


# ── L6 발효기간 ───────────────────────────────────────────────────────────────

async def test_l6_future_and_expired_rows_are_ignored(db: AsyncSession):
    """L6: 아직 발효 전이거나 이미 만료된 행은 무시된다.

    국가 정책은 시행일을 갖는 결정이다. 넣자마자 켜지면 사전 고지가 불가능하다."""
    await _seed(db)
    # D9: 기준일은 테스트가 정한다. `date.today()`(호스트) 로 만들고 기준일 없이 부르면
    # 리졸버 기본값 governance_today()(Asia/Seoul) 와 호스트 날짜가 다른 시간대에서
    # `effective_to = 어제` 행이 아직 유효해져 깨진다 — test_kpi_presentation_resolver 와 같은 결함.
    ref = date(2026, 9, 21)
    db.add(_policy(scope_level="COUNTRY", country_code=US, kpi_code="ADG",
                   display_role="PRIMARY", effective_from=ref + timedelta(days=30)))
    db.add(_policy(scope_level="COUNTRY", country_code=US, kpi_code="FCR",
                   display_role="PRIMARY", effective_from=ref - timedelta(days=60),
                   effective_to=ref - timedelta(days=1)))
    await db.flush()
    got = {r.kpi_code for r in await resolve_display_kpis(db, country=US, ref=ref)}
    assert "ADG" not in got, "발효 전 행이 이미 반영됐다"
    assert "FCR" not in got, "만료된 행이 아직 반영된다"
