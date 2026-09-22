"""RUN 1 — 미지원국(부속조항 없음) 목적② 기본 OFF.

배경: 마스터 약관 제10조③(고객 노출 문서)은 미지원국 ②③④⑤ 기본 OFF ·
     옵트아웃 자동적용 금지를 정한다. 코드는 TERMS_DISPLAY_SPEC §2 "기타 국가:
     ② 고지+제외요청"을 따르고 있었다 → 마스터가 우선한다.

★ 이 변경은 어떤 국가도 legal-ready 로 만들지 않는다. 게이트(signup_blocked /
  paid_blocked / release_hold)는 건드리지 않으며, 미지원국은 여전히 미지원이다.

DB 불필요(순수 정책).
"""
import json
from pathlib import Path

import pytest

from app.services.consent_service import build_signup_plan

_SNAPSHOT = Path(__file__).resolve().parents[1] / "fixtures" / "consent_plan_snapshot_pre_run1.json"

# AC-6 대조 대상 — 미지원국(MX)은 의도적으로 제외한다. 그건 바뀌어야 하는 케이스다.
_UNCHANGED_CASES = ("US", "US-NE", "BR", "TH", "VN", "DE", "GB")


def _plan(sel, st=None):
    return build_signup_plan(selected_country=sel, farm_country=sel, farm_state=st,
                             lang=None, include_body=False)


def _purpose(plan, code):
    return next(p for p in plan.purposes if p.purpose_code == code)


def _project(plan):
    """스냅샷과 같은 모양으로 투영 — 비교 대상을 명시적으로 고정한다."""
    return {
        "group": plan.jurisdiction.group,
        "gate": {"signup_blocked": plan.gate.signup_blocked,
                 "paid_blocked": plan.gate.paid_blocked,
                 "release_hold": plan.gate.release_hold,
                 "reason_code": plan.gate.reason_code},
        "purposes": {x.purpose_code: {"ui_kind": x.ui_kind, "visible": x.visible,
                                      "is_toggle": x.is_toggle, "default_on": x.default_on,
                                      "lawful_basis": x.lawful_basis} for x in plan.purposes},
        "docs": [f"{d.doc_id}@{d.version}" for d in plan.documents],
    }


# ── AC-1  미지원국 ② 비활성 ──────────────────────────────────────────────

def test_ac1_unsupported_country_anon_agg_is_inactive():
    """MX(부속조항 없음) → ② 는 화면에 없고 제외요청 채널도 없다."""
    p2 = _purpose(_plan("MX"), "ANON_AGG_STATS")
    # CN 이 각 목적에 쓰는 것과 같은 목적 수준 비활성 값.
    # (게이트 signup_blocked 에서 파생되는 값이 아니라 MATRIX 의 ui_kind 다)
    assert p2.ui_kind == "BLOCKED"
    assert p2.visible is False
    assert p2.is_toggle is False
    # 제외요청 UI 는 NOTICE_EXCLUSION 일 때만 존재한다 — 그 모드가 아니게 됐다.
    assert p2.ui_kind != "NOTICE_EXCLUSION"


def test_ac1_unsupported_country_purpose2_is_not_recorded():
    """visible=False 인 목적은 원장에 기록되지 않는다(consent_service 기록 루프 규칙)."""
    plan = _plan("MX")
    invisible = {x.purpose_code for x in plan.purposes if not x.visible}
    assert "ANON_AGG_STATS" in invisible


def test_ac1_applies_to_every_unsupported_country_not_just_mx():
    """지원국 목록이 아니라 '부속조항 없음' 판정을 따르는지 — PH 등도 동일해야 한다."""
    for country in ("MX", "PH", "AR", "ZZ"):
        assert _purpose(_plan(country), "ANON_AGG_STATS").ui_kind == "BLOCKED", country


# ── AC-2 · AC-3 · AC-4  기존 법역 불변 ──────────────────────────────────

def test_ac2_us_keeps_notice_exclusion():
    p2 = _purpose(_plan("US"), "ANON_AGG_STATS")
    assert p2.ui_kind == "NOTICE_EXCLUSION"
    assert p2.visible is True


def test_ac3_us_ne_keeps_written_opt_in():
    plan = _plan("US", st="NE")
    assert _purpose(plan, "ANON_AGG_STATS").ui_kind == "WRITTEN_OPT_IN"
    assert _purpose(plan, "NAMED_RESEARCH").ui_kind == "WRITTEN_OPT_IN"


def test_ac4_vn_keeps_hidden_and_transfer_consent():
    plan = _plan("VN")
    assert _purpose(plan, "TRANSACTION_MATCHING").ui_kind == "HIDDEN"
    assert _purpose(plan, "EXTERNAL_AI_PROCESSING").ui_kind == "TRANSFER_CONSENT"


def test_ac4b_li_object_countries_unchanged():
    """EU·GB·BR 의 ② 는 정당한이익 + 이의권 — 미지원국 변경에 휩쓸리면 안 된다."""
    for country in ("DE", "GB", "BR"):
        assert _purpose(_plan(country), "ANON_AGG_STATS").ui_kind == "LI_OBJECT", country


# ── AC-5  게이트 불변 ───────────────────────────────────────────────────

def test_ac5_blocked_jurisdictions_gate_unchanged():
    """AC-5 는 '유지'다 — 절대값을 단정하지 않는다.

    KR 의 signup_blocked 는 환경 의존값이다(conftest 가 allow_kr_signup=True 로
    monkeypatch → reason_code=OVERRIDE_KR). 여기서 True 를 하드코딩하면 테스트가
    운영 설정이 아니라 테스트 설정을 검증하게 된다. 스냅샷 대비 불변만 본다."""
    pre = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    for country in ("KR", "CN"):
        assert _project(_plan(country))["gate"] == pre[country]["gate"], country


def test_ac5_cn_signup_blocked_is_hardcoded():
    """CN 은 환경 플래그로 열리지 않는다 — D-07 HOLD 는 하드코딩이다."""
    gate = _plan("CN").gate
    assert gate.signup_blocked is True
    assert gate.reason_code == "HOLD_D07"


@pytest.mark.xfail(strict=True, reason="H13 (4) 가 purpose2 AC5b 를 뒤집는다 — 해석 A/B 무관하게 깨진다. 결재문 (4) 행 재작성 후 supersede 기록 + 테스트 갱신 (APPROVAL_RECORD §5-1 [1])")
def test_ac5b_unsupported_country_is_not_signup_blocked():
    """★ 이 RUN 은 게이트를 건드리지 않는다.
    ② 비활성은 목적 수준이고, 미지원국 가입 차단은 별개 결정이다(레지스트리 스펙 R-3).
    같은 enum 값을 쓴다고 게이트까지 따라가면 안 된다."""
    gate = _plan("MX").gate
    assert gate.signup_blocked is False
    assert gate.paid_blocked is False
    assert gate.release_hold is False


# ── AC-6  6개국 스냅샷 diff 0 ───────────────────────────────────────────

@pytest.mark.xfail(strict=True, reason="H13 (4) 가 purpose2 AC5b 를 뒤집는다 — 해석 A/B 무관하게 깨진다. 결재문 (4) 행 재작성 후 supersede 기록 + 테스트 갱신 (APPROVAL_RECORD §5-1 [1])")
def test_ac6_supported_countries_snapshot_unchanged():
    """변경 전 캡처와 값 단위 비교. 미지원국(MX)은 대상이 아니다."""
    pre = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    for key in _UNCHANGED_CASES:
        country, _, state = key.partition("-")
        got = _project(_plan(country, st=state or None))
        assert got == pre[key], f"{key} plan 이 바뀌었다 — 이 RUN 의 변경 범위 밖이다"


@pytest.mark.xfail(strict=True, reason="선존 실패(2026-09-10 baseline 8fc382b 에서 이미 red) + H13 (4) 로 7개국이 바뀌어 'MX 하나만' 단언은 어느 해석에서도 거짓. 결재문 재작성 후 스냅샷 재생성 (APPROVAL_RECORD §5-1 [4])")
def test_ac6b_only_other_group_changed_in_snapshot():
    """스냅샷 대비 실제로 달라진 케이스가 MX 하나뿐인지 확인."""
    pre = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    changed = []
    for key, expected in pre.items():
        country, _, state = key.partition("-")
        if _project(_plan(country, st=state or None)) != expected:
            changed.append(key)
    assert changed == ["MX"], f"의도한 것보다 많이 바뀌었다: {changed}"


# ── 실측 기록 (변경 아님) ────────────────────────────────────────────────

def test_measured_opt_in_purposes_are_off_by_default_everywhere():
    """③④⑤ 는 이미 기본 OFF 다 — 이 RUN 에서 바꾸지 않았고 그 사실을 고정한다."""
    for country in ("US", "BR", "MX", "TH"):
        for code in ("AI_MODEL_TRAINING", "NAMED_RESEARCH", "TRANSACTION_MATCHING"):
            p = _purpose(_plan(country), code)
            if p.visible:
                assert p.default_on is False, f"{country}/{code}"


def test_measured_purpose6_unsupported_country_remains_notice():
    """⑥ 는 미지원국에서 'NOTICE' 그대로다.
    기존 enum 에 '제한/차단' 모드가 없어 변경하지 않았다(FOUND_OUT_OF_SCOPE).
    TRANSFER_CONSENT 는 '별도 동의'이지 제한이 아니고, BLOCKED 는 CN 진입차단 의미다."""
    assert _purpose(_plan("MX"), "EXTERNAL_AI_PROCESSING").ui_kind == "NOTICE"
