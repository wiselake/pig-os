"""가입 게이트가 **계정 생성 경로**에도 걸리는지 검증.

회귀 대상: 게이트가 `/consent/record` 한 곳에만 있어서 차단 법역(CN·KR)에서도
계정은 생성되고 동의만 451 로 실패했다 → '동의 없는 계정'이 남는다.
클라이언트 UI 가 유일한 방어선이면 구버전 앱·직접 API 호출로 그대로 통과한다.
"""
import pytest
from fastapi import HTTPException

from app.services import jurisdiction as jz


@pytest.fixture(autouse=True)
def _lock_kr(monkeypatch):
    """운영 기본값(allow_kr_signup=False)으로 고정. conftest 의 autouse override 를 끈다."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "allow_kr_signup", False)


class TestAssertSignupAllowed:
    @pytest.mark.parametrize("country,reason", [
        ("CN", "HOLD_D07"),
        ("KR", "KR_REFERENCE_ONLY"),
    ])
    def test_blocked_jurisdictions_raise_451(self, country, reason):
        with pytest.raises(HTTPException) as ei:
            jz.assert_signup_allowed(selected_country=country)
        assert ei.value.status_code == 451
        assert reason in str(ei.value.detail)

    @pytest.mark.parametrize("country", ["US", "BR", "DE", "GB", "TH", "VN", "AU"])
    def test_open_jurisdictions_pass(self, country):
        jz.assert_signup_allowed(selected_country=country)   # 예외 없음

    def test_paid_and_release_gates_do_not_block_signup(self):
        """TH/VN 은 유료차단, EU/GB/BR 은 릴리스보류 — 가입 자체를 막지는 않는다."""
        for c in ("TH", "VN", "DE", "GB", "BR"):
            jz.assert_signup_allowed(selected_country=c)

    def test_env_override_unlocks_kr(self, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "allow_kr_signup", True)
        jz.assert_signup_allowed(selected_country="KR")      # 대표 확인용 해제

    def test_farm_country_stricter_than_selected_is_applied(self):
        """선택국은 열려 있어도 농장 소재지가 차단 법역이면 막는다(보수 적용)."""
        with pytest.raises(HTTPException) as ei:
            jz.assert_signup_allowed(selected_country="US", farm_country="CN")
        assert ei.value.status_code == 451

    def test_lowercase_country_is_normalized(self):
        with pytest.raises(HTTPException):
            jz.assert_signup_allowed(selected_country="kr")


class TestGateNotes:
    """예전엔 차단 사유 note 에 CN 문구가 하드코딩돼 KR 에도 'CN, D-07 HOLD' 가 찍혔다."""

    def test_kr_note_names_kr_not_cn(self):
        j = jz.resolve_for_signup(selected_country="KR")
        note = " ".join(j.notes)
        assert "KR" in note
        assert "KR_REFERENCE_ONLY" in note
        assert "CN" not in note

    def test_cn_note_names_cn(self):
        j = jz.resolve_for_signup(selected_country="CN")
        note = " ".join(j.notes)
        assert "CN" in note
        assert "HOLD_D07" in note


class TestSharedResolution:
    """가입 플랜과 게이트가 같은 판정을 써야 한다(두 곳이 갈라지면 UI 와 서버가 어긋난다)."""

    def test_plan_gate_matches_assert(self):
        from app.services import consent_service as cs

        for country in ("KR", "CN", "US", "BR"):
            plan = cs.build_signup_plan(
                selected_country=country, farm_country=country,
                farm_state=None, lang="en", include_body=False,
            )
            blocked_by_assert = False
            try:
                jz.assert_signup_allowed(selected_country=country)
            except HTTPException:
                blocked_by_assert = True
            assert plan.gate.signup_blocked is blocked_by_assert, country
