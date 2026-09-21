"""D9 — 실행 시각(wall clock)이 테스트 결과를 정하지 않는다.

배경 (2026-09-21, docs/runs/D9_TIME_BOUNDARY_20260921.md)
  PR #2 CI 가 하루 중 00:00–09:00 KST 에만 빨갔다. 원인은 정책 발효일 게이트 테스트가
  "어제/내일" 을 `date.today()`(러너 로컬 = UTC) 로 만들고, 리졸버는 기본 기준일로
  `governance_today()`(GOVERNANCE_TZ, 기본 Asia/Seoul) 를 쓴 것 — 세 개의 시계가 섞였다:
      호스트 로컬 날짜 · 회사 거버넌스 날짜 · (DB server_default CURRENT_DATE)
  같은 커밋·같은 입력인데 15:00–24:00 UTC 에만 "내일" 이 이미 오늘이 됐다.

이 파일이 고정하는 두 불변식
  ① 기준일(ref)을 명시하면 결과는 실행 시각과 무관하다 — UTC 자정·KST 자정·월말·연말을 넘겨도 같다.
  ② 기준일을 생략하면 기준은 **회사 거버넌스 날짜** 이고 호스트 날짜가 아니다 (kpi_policy_resolver 모듈 docstring).

시계를 바꾸는 방법: `governance_today` 를 모듈 경계에서 대체한다. `date.today()` 를 고치는
전역 몽키패치·OS TZ 변경·CI TZ 환경변수는 쓰지 않는다 — 그건 문제를 가리는 쪽이다.
"""
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.kpi_policy_resolver as resolver
from app.db.models.kpi_presentation import CountryKpiPresentation
from app.services.kpi_policy_resolver import resolve_kpi_presentation

pytestmark = pytest.mark.anyio

KST = ZoneInfo("Asia/Seoul")
REF = date(2026, 9, 21)                     # 테스트가 정한 기준일 — 실행 시각과 무관

# 논리 실행 시각 (UTC 인스턴트). 각각의 KST 날짜와 UTC 날짜가 다른 조합을 고른다.
#   KST 자정 경계: 2026-09-20 15:00Z 전후 · UTC 자정 경계: 2026-09-21 00:00Z 전후
#   월말/연말: KST 로는 다음 달/해인데 UTC 로는 아직 이전 달/해인 인스턴트
BOUNDARY_INSTANTS = [
    pytest.param(datetime(2026, 9, 20, 14, 59, 59, tzinfo=UTC), id="2026-09-20T23:59:59+09 KST-day-end"),
    pytest.param(datetime(2026, 9, 20, 15, 0, 0, tzinfo=UTC), id="2026-09-21T00:00:00+09 KST-midnight (UTC still 09-20)"),
    pytest.param(datetime(2026, 9, 20, 23, 59, 59, tzinfo=UTC), id="2026-09-21T08:59:59+09 UTC-day-end"),
    pytest.param(datetime(2026, 9, 21, 0, 0, 0, tzinfo=UTC), id="2026-09-21T09:00:00+09 UTC-midnight"),
    pytest.param(datetime(2026, 9, 21, 14, 59, 59, tzinfo=UTC), id="2026-09-21T23:59:59+09"),
    pytest.param(datetime(2026, 9, 21, 15, 0, 0, tzinfo=UTC), id="2026-09-22T00:00:00+09 next KST day"),
    pytest.param(datetime(2026, 9, 30, 15, 0, 0, tzinfo=UTC), id="2026-10-01T00:00:00+09 month-end (UTC 09-30)"),
    pytest.param(datetime(2026, 12, 31, 15, 0, 0, tzinfo=UTC), id="2027-01-01T00:00:00+09 year-end (UTC 12-31)"),
]


def _clock(monkeypatch, instant: datetime) -> tuple[date, date]:
    """리졸버가 보는 '회사 오늘' 을 주어진 인스턴트로 고정하고 (거버넌스 날짜, UTC 호스트 날짜) 를 돌려준다."""
    gov = instant.astimezone(KST).date()
    monkeypatch.setattr(resolver, "governance_today", lambda: gov)
    return gov, instant.astimezone(UTC).date()


def _pres(kpi, scope="GLOBAL", **kw):
    base = dict(scope_level=scope, kpi_code=kpi, decision_status="APPROVED")
    base.update(kw)
    return CountryKpiPresentation(**base)


async def _seed_window(db: AsyncSession, kpi: str) -> None:
    """GLOBAL=30 · BR 행=10 은 REF 당일 하루만 유효 (effective_from = effective_to = REF)."""
    db.add(_pres(kpi, display_order=30, display_order_override=True))
    db.add(_pres(kpi, scope="COUNTRY", country_code="BR", display_order=10,
                 display_order_override=True, effective_from=REF, effective_to=REF))
    await db.flush()


@pytest.mark.parametrize("instant", BOUNDARY_INSTANTS)
async def test_fixed_ref_result_is_independent_of_wall_clock(db: AsyncSession, monkeypatch, instant):
    """① 같은 입력 + 같은 ref + 다른 실행 시각 → 같은 결과.

    KST 자정·UTC 자정·월말·연말 어느 인스턴트에서 돌려도, ref 가 REF 이면 BR 행은 적용(10),
    ref 가 REF±1 이면 미적용(30) 이다. 거버넌스 날짜와 호스트 날짜가 서로 달라도 상관없다.
    """
    gov, host = _clock(monkeypatch, instant)
    await _seed_window(db, "WC")

    on = await resolve_kpi_presentation(db, kpi_code="WC", country="BR", ref=REF)
    before = await resolve_kpi_presentation(db, kpi_code="WC", country="BR", ref=REF - timedelta(days=1))
    after = await resolve_kpi_presentation(db, kpi_code="WC", country="BR", ref=REF + timedelta(days=1))

    assert (on.display_order, before.display_order, after.display_order) == (10, 30, 30), (
        f"clock gov={gov} host={host}: 명시 ref 결과가 실행 시각에 따라 달라졌다")


@pytest.mark.parametrize("instant", BOUNDARY_INSTANTS)
async def test_default_ref_follows_governance_date_not_host_date(db: AsyncSession, monkeypatch, instant):
    """② ref 생략 시 기준은 거버넌스 날짜다 — 호스트(UTC) 날짜가 아니다.

    같은 인스턴트에서 호스트 날짜와 거버넌스 날짜가 다르면, 결과는 거버넌스 쪽을 따라야 한다.
    기대값은 리졸버를 다시 돌려 만들지 않고 날짜 비교로 직접 정한다.
    """
    gov, host = _clock(monkeypatch, instant)
    await _seed_window(db, "GV")

    got = await resolve_kpi_presentation(db, kpi_code="GV", country="BR")
    expected = 10 if gov == REF else 30
    # 예: 2026-09-20T15:00Z 는 gov=09-21(적용, 10) 이지만 host=09-20 — 호스트 기준이면 30 이 나온다.
    #     그 인스턴트에서 이 assert 가 두 시계를 구분한다.
    assert got.display_order == expected, (
        f"gov={gov} host={host}: 기본 기준일이 거버넌스 날짜를 따르지 않는다 (got {got.display_order})")


async def test_effective_window_is_closed_on_both_ends(db: AsyncSession):
    """effective_from ≤ ref ≤ effective_to (닫힌 구간) — 경계 당일 포함. 실행 시각 무관."""
    await _seed_window(db, "CL")
    assert (await resolve_kpi_presentation(db, kpi_code="CL", country="BR", ref=REF)).display_order == 10
    assert (await resolve_kpi_presentation(db, kpi_code="CL", country="BR",
                                           ref=REF - timedelta(days=1))).display_order == 30
    assert (await resolve_kpi_presentation(db, kpi_code="CL", country="BR",
                                           ref=REF + timedelta(days=1))).display_order == 30
