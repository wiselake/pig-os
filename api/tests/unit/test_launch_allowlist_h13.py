"""H13 (4) — launch enablement 를 publication eligibility 와 분리한다.

세 상태는 별개다.

    publication eligibility   문서 세트가 완성됐는가
    jurisdiction clearance    그 법역을 법무 검토했는가
    launch enablement         가입을 열기로 결정했는가   ← _LAUNCH_ALLOWLIST

렌더러는 부속조항이 없는 그룹에 대해 "마스터+방침 두 건이 곧 완전한 세트"로
동작한다. 그 성질이 개시 결정을 대신하지 못하게 하는 것이 이 테스트의 목적이다.

실행 결정: Brian, 2026-09-10 (대표 구두 포괄 승인 하의 위임 범위).
"""
from __future__ import annotations

import pytest

from app.services.jurisdiction import _LAUNCH_ALLOWLIST, resolve


def _blocked(country: str, **kw) -> tuple[bool, str | None]:
    j = resolve(selected_country=country, **kw)
    return j.gate.signup_blocked, j.gate.reason_code


def test_allowlist_is_country_level_and_starts_with_us_only():
    """그룹이 아니라 국가 단위여야 '고르는 행위'가 기록에 남는다."""
    assert _LAUNCH_ALLOWLIST == frozenset({"US"})


def test_us_is_launch_enabled():
    blocked, _ = _blocked("US")
    assert blocked is False


@pytest.mark.parametrize("country", ["MX", "PH", "JP", "CL", "CO"])
def test_other_group_countries_are_blocked_even_though_document_set_is_complete(country):
    """★ 이 그룹은 부속조항이 없어 문서 세트가 '완전'하다. 그래도 열리지 않는다."""
    blocked, reason = _blocked(country)
    assert blocked is True
    assert reason == "LAUNCH_NOT_ENABLED"


@pytest.mark.parametrize("country", ["BR", "DE", "GB"])
def test_draft_addendum_jurisdictions_stay_blocked(country):
    blocked, _ = _blocked(country)
    assert blocked is True


@pytest.mark.parametrize("country", ["TH", "VN"])
def test_hold_jurisdictions_no_longer_allow_free_signup(country):
    """R-10 회귀 방지.

    이전에는 paid_blocked 만 있어 **무료 가입은 열려 있었다**. 내부 출시 게이트가
    HOLD 인데 가입이 열려 있던 상태를 launch allowlist 가 닫는다.
    """
    blocked, reason = _blocked(country)
    assert blocked is True
    assert reason == "LAUNCH_NOT_ENABLED"


@pytest.mark.parametrize(
    "country,expected_reason",
    [("KR", "KR_REFERENCE_ONLY"), ("CN", "HOLD_D07")],
)
def test_existing_signup_gates_keep_their_own_reason(country, expected_reason):
    """기존 차단 사유를 LAUNCH_NOT_ENABLED 가 덮어쓰지 않는다 — 원인 추적이 끊긴다."""
    blocked, reason = _blocked(country)
    assert blocked is True
    assert reason == expected_reason


@pytest.mark.parametrize(
    "country,override",
    [("KR", {"KR_signup": True}), ("CN", {"CN_signup": True})],
)
def test_existing_group_overrides_still_open_signup(country, override):
    """그룹 단위 해제는 그 그룹을 여는 명시적 판단이므로 개시 허용도 함께 의미한다."""
    blocked, _ = _blocked(country, feature_overrides=override)
    assert blocked is False


def test_per_country_launch_override():
    """allowlist 추가 전 임시 확인용 탈출구. 국가 단위로만 동작한다."""
    assert _blocked("MX", feature_overrides={"LAUNCH_MX": True})[0] is False
    # 다른 국가에는 새지 않는다
    assert _blocked("PH", feature_overrides={"LAUNCH_MX": True})[0] is True
