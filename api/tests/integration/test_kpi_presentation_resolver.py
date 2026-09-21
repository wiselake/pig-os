"""Presentation Policy 리졸버 — country_kpi_presentation (STEP B 보완).

경계: CKP = 그 KPI 를 써도 되는가 / CKPRES = 뭐라 부르고 몇 번째인가.
"""
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.kpi_policy import CountryKpiPolicy
from app.db.models.kpi_presentation import CountryKpiPresentation
from app.services.kpi_policy_resolver import (
    pick_headline,
    resolve_display_kpis,
    resolve_kpi_presentation,
)

pytestmark = pytest.mark.anyio


def _global(kpi, **kw):
    base = dict(scope_level="GLOBAL", kpi_code=kpi, compute_enabled=True, display_role="PRIMARY",
                rule_enabled=True, benchmark_exposure="CONTEXT_ONLY", prediction_feature=False,
                api_export_policy="TENANT_ONLY", decision_status="APPROVED", decided_by="test")
    base.update(kw)
    return CountryKpiPolicy(**base)


def _pres(kpi, scope="GLOBAL", **kw):
    base = dict(scope_level=scope, kpi_code=kpi, decision_status="APPROVED")
    base.update(kw)
    return CountryKpiPresentation(**base)


# ── ★ display_order_override 4상태 회귀 (P0-1) ────────────────────────────────
# 이 4개가 "NULL 이면 상속" 으로 되돌리는 회귀를 막는다. 4번이 핵심:
# override=true + NULL 은 상속이 아니라 "명시적으로 맨 뒤" 다.

async def test_override_state1_no_country_row_inherits_global(db: AsyncSession):
    """① GLOBAL=30 / COUNTRY 행 없음 → 30"""
    db.add(_pres("O1", display_order=30, display_order_override=True))
    await db.flush()
    r = await resolve_kpi_presentation(db, kpi_code="O1", country="BR")
    assert r.display_order == 30
    assert r.resolved_from == ["GLOBAL"]


async def test_override_state2_false_does_not_touch_order(db: AsyncSession):
    """② GLOBAL=30 / COUNTRY override=false → 30 (그 스코프는 순서에 관여하지 않음)"""
    db.add(_pres("O2", display_order=30, display_order_override=True))
    db.add(_pres("O2", scope="COUNTRY", country_code="BR",
                 display_order=10, display_order_override=False))
    await db.flush()
    r = await resolve_kpi_presentation(db, kpi_code="O2", country="BR")
    assert r.display_order == 30, "override=false 행의 값은 채택되지 않는다"


async def test_override_state3_true_with_value_wins(db: AsyncSession):
    """③ GLOBAL=30 / COUNTRY override=true, 10 → 10"""
    db.add(_pres("O3", display_order=30, display_order_override=True))
    db.add(_pres("O3", scope="COUNTRY", country_code="BR",
                 display_order=10, display_order_override=True))
    await db.flush()
    br = await resolve_kpi_presentation(db, kpi_code="O3", country="BR")
    kr = await resolve_kpi_presentation(db, kpi_code="O3", country="KR")
    assert br.display_order == 10
    assert kr.display_order == 30, "다른 국가는 GLOBAL 유지"


async def test_override_state4_true_with_null_means_last_not_inherit(db: AsyncSession):
    """④ GLOBAL=30 / COUNTRY override=true, NULL → NULL(맨 뒤)

    ★ 이번에 발견한 모순의 회귀 테스트. NULL 을 상속으로 처리하면
      "이 국가에서는 이 KPI 를 맨 뒤로" 를 표현할 방법이 사라진다."""
    db.add(_pres("O4", display_order=30, display_order_override=True))
    db.add(_pres("O4", scope="COUNTRY", country_code="BR",
                 display_order=None, display_order_override=True))
    await db.flush()
    r = await resolve_kpi_presentation(db, kpi_code="O4", country="BR")
    assert r.display_order is None, "override=true + NULL 은 상속이 아니라 명시적 마지막"


# ── 합성(resolve_display_kpis) ────────────────────────────────────────────────

async def test_visible_kpi_included_even_without_presentation_row(db: AsyncSession):
    """§4-1: Presentation row 가 없어도 CKP 가 visible 이면 목록에 포함(표현값만 null)."""
    db.add(_global("NOPRES", display_role="PRIMARY"))
    await db.flush()
    rows = {r.kpi_code: r for r in await resolve_display_kpis(db, country="BR")}
    assert "NOPRES" in rows
    assert rows["NOPRES"].display_order is None and rows["NOPRES"].local_label is None


async def test_hidden_kpi_excluded_even_with_presentation_row(db: AsyncSession):
    """표현 행이 있어도 거버넌스가 HIDDEN 이면 제외 — 포함 기준은 CKP 소관."""
    db.add(_global("HID", display_role="HIDDEN"))
    db.add(_pres("HID", display_order=1, display_order_override=True))
    await db.flush()
    codes = [r.kpi_code for r in await resolve_display_kpis(db, country="BR")]
    assert "HID" not in codes


async def test_display_list_sorted_north_star_then_order(db: AsyncSession):
    """정렬: NORTH_STAR 최상단 → display_order ASC → NULL 마지막 → kpi_code."""
    for code in ("SA", "SB", "SNULL", "SHEAD"):
        db.add(_global(code, display_role="PRIMARY"))
    db.add(_global("SHEAD", display_role="PRIMARY", priority_class="NORTH_STAR",
                   scope_level="COUNTRY", country_code="BR", decided_by="test"))
    db.add(_pres("SB", display_order=20, display_order_override=True))
    db.add(_pres("SA", display_order=10, display_order_override=True))
    db.add(_pres("SHEAD", display_order=99, display_order_override=True))
    await db.flush()
    rows = await resolve_display_kpis(db, country="BR")
    codes = [r.kpi_code for r in rows if r.kpi_code in ("SHEAD", "SA", "SB", "SNULL")]
    assert codes == ["SHEAD", "SA", "SB", "SNULL"], codes
    assert pick_headline(rows) == "SHEAD"


async def test_local_label_resolves_by_country(db: AsyncSession):
    """local_label 은 i18n 이 아니라 국가 용어 — UI 언어와 무관하게 국가로 결정."""
    db.add(_global("LBL", display_role="PRIMARY"))
    db.add(_pres("LBL", scope="COUNTRY", country_code="BR", local_label="Leitões desmamados/porca/ano"))
    await db.flush()
    br = await resolve_kpi_presentation(db, kpi_code="LBL", country="BR")
    us = await resolve_kpi_presentation(db, kpi_code="LBL", country="US")
    assert br.local_label == "Leitões desmamados/porca/ano"
    assert us.local_label is None, "다른 국가는 공용 라벨 사용"


# ── 유효기간·승인 게이트 (P0-2) ───────────────────────────────────────────────
#
# ★ D9 (2026-09-21): 이 두 테스트는 원래 `date.today()`(실행 호스트 로컬 날짜)로 "어제/내일" 을
#   만들고, 기준일 없이 리졸버를 불렀다. 리졸버 기본 기준일은 `governance_today()`(GOVERNANCE_TZ,
#   기본 Asia/Seoul) 이므로 **호스트 날짜 ≠ 거버넌스 날짜** 인 시간대(UTC 러너의 15:00–24:00 UTC =
#   00:00–09:00 KST)에는 "내일" 이 이미 오늘이 돼 `assert 10 == 30` 으로 깨졌다
#   (PR #2 run 35371186151 · 35394188042 · 35541576981, 같은 코드가 00:55 UTC 엔 초록).
#   기준일은 실행 시각이 아니라 테스트가 정한다 — 모든 호출에 `ref` 를 명시한다.

_REF = date(2026, 9, 21)   # 임의 고정 기준일. 실행 시각과 무관.


async def test_expired_presentation_row_ignored(db: AsyncSession):
    """effective_to 가 기준일보다 앞이면 무시된다(두 리졸버 모두 동일 게이트)."""
    y = _REF - timedelta(days=1)
    db.add(_pres("EXP", display_order=30, display_order_override=True))
    db.add(_pres("EXP", scope="COUNTRY", country_code="BR", display_order=10,
                 display_order_override=True, effective_to=y))
    await db.flush()
    r = await resolve_kpi_presentation(db, kpi_code="EXP", country="BR", ref=_REF)
    assert r.display_order == 30, "만료 행 무시 → 상위 유지"
    # 경계: effective_to == 기준일 은 아직 유효(닫힌 구간)
    on_last_day = await resolve_kpi_presentation(db, kpi_code="EXP", country="BR", ref=y)
    assert on_last_day.display_order == 10, "effective_to 당일까지는 적용"


async def test_future_presentation_row_ignored(db: AsyncSession):
    """effective_from 이 기준일보다 뒤면 아직 적용되지 않는다."""
    tomorrow = _REF + timedelta(days=1)
    db.add(_pres("FUT", display_order=30, display_order_override=True))
    db.add(_pres("FUT", scope="COUNTRY", country_code="BR", display_order=10,
                 display_order_override=True, effective_from=tomorrow))
    await db.flush()
    r = await resolve_kpi_presentation(db, kpi_code="FUT", country="BR", ref=_REF)
    assert r.display_order == 30
    future = await resolve_kpi_presentation(db, kpi_code="FUT", country="BR",
                                           ref=tomorrow)
    assert future.display_order == 10, "기준일이 발효일에 닿으면 적용(닫힌 구간)"


async def test_proposed_presentation_row_ignored(db: AsyncSession):
    """미승인(PROPOSED) 표현 행은 반영되지 않는다 — fail-closed."""
    db.add(_pres("PRP", display_order=30, display_order_override=True))
    db.add(_pres("PRP", scope="COUNTRY", country_code="BR", display_order=10,
                 display_order_override=True, decision_status="PROPOSED"))
    await db.flush()
    r = await resolve_kpi_presentation(db, kpi_code="PRP", country="BR")
    assert r.display_order == 30


async def test_tenant_scope_overrides_country(db: AsyncSession):
    """상속 체인 끝단(TENANT)이 COUNTRY 를 덮는다."""
    import uuid
    tid = uuid.uuid4()
    db.add(_pres("TEN", display_order=30, display_order_override=True))
    db.add(_pres("TEN", scope="COUNTRY", country_code="BR", display_order=20,
                 display_order_override=True))
    db.add(_pres("TEN", scope="TENANT", tenant_id=tid, display_order=1,
                 display_order_override=True))
    await db.flush()
    r = await resolve_kpi_presentation(db, kpi_code="TEN", country="BR", tenant_id=tid)
    assert r.display_order == 1
    assert r.resolved_from == ["GLOBAL", "COUNTRY", "TENANT"]
