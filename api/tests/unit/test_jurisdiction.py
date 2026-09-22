"""법역 판별기 (TERMS_DISPLAY §1.2·§3·§4) — 순수 리졸버, 기존 테스트 없음.

핵심: EU/GB 분리(v1.4 결정 — 부속조항 별도), US 주별 플래그, 게이트, 선택국≠농장국 보수적용.
"""
import pytest

from app.services.jurisdiction import resolve


@pytest.mark.xfail(strict=True, reason="H13 (4) 해석 A(전역 default-deny) 에서만 깨진다 — B(OTHER 한정) 로 코드를 좁히면 XPASS 로 빨개져 결정 기록을 강제한다 (APPROVAL_RECORD §5-1 [2])")
def test_eu_de_uses_eu_addendum_and_release_hold():
    j = resolve(selected_country="DE")
    assert j.group == "EU"
    assert j.code == "DE"
    assert j.doc_addendum == "ADDENDUM_EU"
    assert j.gate.release_hold is True
    assert j.gate.reason_code == "OPEN_EU_REP"


@pytest.mark.xfail(strict=True, reason="H13 (4) 해석 A(전역 default-deny) 에서만 깨진다 — B(OTHER 한정) 로 코드를 좁히면 XPASS 로 빨개져 결정 기록을 강제한다 (APPROVAL_RECORD §5-1 [2])")
def test_gb_is_split_from_eu():
    j = resolve(selected_country="GB")
    assert j.group == "GB"
    assert j.doc_addendum == "ADDENDUM_GB"       # EU와 별도 부속조항
    assert j.gate.reason_code == "OPEN_UK_REP"    # EU와 다른 대리인 게이트


def test_us_ne_written_opt_in_and_uoom():
    j = resolve(selected_country="US", farm_country="US", farm_state="NE")
    assert j.code == "US-NE"
    assert j.state_flags.written_opt_in_required is True   # LB525
    assert j.state_flags.honor_uoom is True                # NE ∈ UOOM


def test_us_ca_do_not_sell_and_uoom():
    j = resolve(selected_country="US", farm_country="US", farm_state="CA")
    assert j.code == "US-CA"
    assert j.state_flags.do_not_sell_link is True
    assert j.state_flags.honor_uoom is True
    assert j.state_flags.written_opt_in_required is False   # CA는 서면 옵트인 아님


def test_us_md_location_sale_ban():
    j = resolve(selected_country="US", farm_country="US", farm_state="MD")
    assert j.state_flags.exclude_location_from_sale is True  # MODPA


def test_cn_signup_blocked_and_override():
    blocked = resolve(selected_country="CN")
    assert blocked.gate.signup_blocked is True
    assert blocked.gate.reason_code == "HOLD_D07"
    unblocked = resolve(selected_country="CN", feature_overrides={"CN_signup": True})
    assert unblocked.gate.signup_blocked is False
    assert unblocked.gate.reason_code == "OVERRIDE_CN"


def test_country_mismatch_picks_stricter_and_flags_counsel():
    # 선택 US(느슨) vs 농장 DE(엄격) → DE 채택 + counsel
    j = resolve(selected_country="US", farm_country="DE")
    assert j.country == "DE" and j.group == "EU"
    assert j.counsel_review is True


def test_kr_reference_only_signup_blocked_by_default():
    # KR = 레퍼런스 전용 → 실고객 가입 기본 차단(부속조항은 없음)
    j = resolve(selected_country="KR")
    assert j.group == "KR"
    assert j.doc_addendum is None
    assert j.gate.signup_blocked is True
    assert j.gate.reason_code == "KR_REFERENCE_ONLY"


def test_kr_signup_override_unblocks():
    # 대표 확인용 override(allow_kr_signup env → KR_signup) 시 해제
    j = resolve(selected_country="KR", feature_overrides={"KR_signup": True})
    assert j.gate.signup_blocked is False
    assert j.gate.reason_code == "OVERRIDE_KR"


@pytest.mark.xfail(strict=True, reason="H13 (4) 해석 A(전역 default-deny) 에서만 깨진다 — B(OTHER 한정) 로 코드를 좁히면 XPASS 로 빨개져 결정 기록을 강제한다 (APPROVAL_RECORD §5-1 [2])")
def test_th_paid_gate_and_override():
    th = resolve(selected_country="TH")
    assert th.gate.paid_blocked is True and th.gate.reason_code == "GATE_D09"
    override = resolve(selected_country="TH", feature_overrides={"TH_paid": True})
    assert override.gate.paid_blocked is False and override.gate.reason_code == "OVERRIDE_TH"
