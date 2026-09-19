"""LLM 출력이 룰엔진 결과를 벗어나지 않는지 — 표시 전 검증.

## 왜 필요한가

CLAUDE.md 는 "LLM은 판단 금지 — 검증된 Rule Engine 결과를 자연어로 변환하는
역할만" 이라고 못박고 있다. 그런데 그것이 **프롬프트에만** 있었다.

    llm_renderer.build_system_prompt()
        "Do NOT add new judgments, numbers, diagnoses ..."
        "State a monetary amount ONLY if a finding's detail.loss.amount is present"

프롬프트는 요청이지 강제가 아니다. `render()` 는 모델 응답을 그대로 돌려줬고,
없는 숫자나 금액이 섞여도 사용자에게 그대로 나갔다. 유료 티어(AI Insight)에서만
발생하므로 **돈을 낸 고객이 더 위험한** 구조였다.

## 이 가드가 보는 것 / 보지 않는 것

    본다      소수·퍼센트 숫자가 룰엔진 결과에 있는 값인가
              금액이 detail.loss.amount 없이 등장하는가
              금액 숫자가 실제 loss 금액과 다른가

    안 본다   맨 정수(산문의 "3가지 원인" 같은 것과 구분이 안 된다)
              개체 이표번호(ear_tag)  ← ★ 미구현. 아래 참조
              문장의 사실 왜곡 자체(숫자가 맞아도 서술은 틀릴 수 있다)

★ ear_tag 검증은 **의도적으로 v1 범위 밖**이다. 이표번호는 농장마다 형식이
  달라(숫자만·문자+숫자·하이픈) 텍스트에서 안전하게 식별할 규칙이 없다.
  느슨하게 잡으면 날짜·모델명까지 걸려 유료 응답이 상시 템플릿으로 떨어진다.
  가드가 오작동해 기능을 죽이는 쪽이 더 나쁘다 — 별도 과제로 남긴다.

## 실패 시 동작

차단하면 **같은 StructuredResult 의 템플릿 응답**으로 대체한다. 사용자는 항상
유효한 답을 받고, API 계약(`renderer` = "template" | "llm")도 그대로다.
"""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from app.engine import llm_renderer as lr
from app.engine.rule_engine import Finding, Severity, StructuredResult


def _result(**over) -> StructuredResult:
    f = Finding(
        rule_id="npd_high", kpi="NPD", severity=Severity.WARNING,
        current_value=42.5, target_value=35.0,
        causes=["weaning_to_service_long"],
        recommended_actions=["review_heat_detection"],
        detail=over.pop("detail", {}),
    )
    return StructuredResult(
        farm_id=uuid4(), intent="explain_npd", severity=Severity.WARNING,
        findings=[f], as_of=date(2026, 9, 7), **over,
    )


def _with_loss(amount: int = 1200, currency: str = "USD") -> StructuredResult:
    return _result(detail={"loss": {"amount": amount, "currency": currency, "demo": False}})


# ── 통과해야 하는 것 ────────────────────────────────────────────────────────

def test_explanation_using_only_engine_values_passes():
    r = _result()
    text = "NPD is 42.5 days against a target of 35.0. Review heat detection."
    assert lr.verify_rendering(text, r) is None


def test_rounded_restatement_passes():
    """모델이 42.5 를 43 이나 42.50 으로 다시 쓰는 것은 왜곡이 아니다."""
    r = _result()
    for text in ("NPD is about 43 days.", "NPD sits at 42.50 days.", "NPD 42.5%"):
        assert lr.verify_rendering(text, r) is None, text


def test_as_of_date_numbers_pass():
    r = _result()
    assert lr.verify_rendering("As of 2026-09-07, NPD is 42.5 days.", r) is None


def test_bare_integers_in_prose_pass():
    """맨 정수는 보지 않는다 — 산문의 개수 표현과 구분할 수 없다."""
    r = _result()
    assert lr.verify_rendering("There are 3 causes to check first.", r) is None


def test_money_matching_the_finding_passes():
    r = _with_loss(1200, "USD")
    assert lr.verify_rendering("Estimated impact is $1,200 this period.", r) is None


def test_text_without_numbers_passes():
    r = _result()
    assert lr.verify_rendering("Non-productive days are running long. Review heat detection.", r) is None


# ── 차단해야 하는 것 ────────────────────────────────────────────────────────

def test_invented_decimal_is_blocked():
    """룰엔진에 없는 소수를 만들어내면 차단한다."""
    r = _result()
    reason = lr.verify_rendering("NPD is 42.5 days, and PSY dropped to 21.7.", r)
    assert reason is not None
    assert "21.7" in reason


def test_invented_percentage_is_blocked():
    r = _result()
    reason = lr.verify_rendering("Farrowing rate fell 12.3% versus last month.", r)
    assert reason is not None
    assert "12.3" in reason


def test_money_without_any_loss_is_blocked():
    """★ 가장 위험한 경우. loss 가 없는데 금액을 말하면 고객은 그것을 실제 손실로 읽는다."""
    r = _result()
    reason = lr.verify_rendering("This is costing you about $3,400 per month.", r)
    assert reason is not None
    assert "money" in reason.lower() or "금액" in reason


def test_money_amount_that_disagrees_with_the_finding_is_blocked():
    r = _with_loss(1200, "USD")
    reason = lr.verify_rendering("Estimated impact is $9,900.", r)
    assert reason is not None


def test_multiple_currency_notations_are_caught():
    r = _result()
    for text in ("cerca de R$ 5.000 por mês", "khoảng 3.500.000 VND", "약 120,000 KRW"):
        assert lr.verify_rendering(text, r) is not None, text


# ── render() 통합 — 차단되면 템플릿으로 떨어진다 ────────────────────────────

@pytest.mark.anyio
async def test_render_falls_back_to_template_when_output_is_rejected(monkeypatch):
    r = _result()
    monkeypatch.setattr(lr, "has_api_key", lambda: True)

    async def _bad(result, locale):
        return "NPD is 42.5 days and PSY collapsed to 9.9, costing you $7,700."

    monkeypatch.setattr(lr, "_call_llm", _bad)
    text, rendered_by = await lr.render(r, "en", use_llm=True, usage_count=0)

    assert rendered_by == "template", "지어낸 숫자가 그대로 사용자에게 나갔다"
    assert "9.9" not in text and "7,700" not in text
    assert text == lr.render_text(r, "en")


@pytest.mark.anyio
async def test_render_keeps_llm_output_when_it_stays_within_the_result(monkeypatch):
    """★ 가드가 과하면 유료 기능이 상시 템플릿으로 죽는다. 정상 응답은 반드시 통과해야 한다."""
    r = _result()
    monkeypatch.setattr(lr, "has_api_key", lambda: True)

    async def _good(result, locale):
        return "Non-productive days reached 42.5 against a 35.0 target. Review heat detection."

    monkeypatch.setattr(lr, "_call_llm", _good)
    text, rendered_by = await lr.render(r, "en", use_llm=True, usage_count=0)

    assert rendered_by == "llm"
    assert "42.5" in text


@pytest.mark.anyio
async def test_rejection_is_logged_not_silent(monkeypatch, caplog):
    """조용한 폴백은 이 프로젝트가 이미 데인 실패 유형이다(ARQ false success).

    가드가 발동했다는 사실이 로그에 남아야 얼마나 자주 발동하는지 알 수 있다."""
    import logging

    r = _result()
    monkeypatch.setattr(lr, "has_api_key", lambda: True)

    async def _bad(result, locale):
        return "PSY is 88.8."

    monkeypatch.setattr(lr, "_call_llm", _bad)
    with caplog.at_level(logging.WARNING):
        await lr.render(r, "en", use_llm=True, usage_count=0)

    assert any("88.8" in rec.getMessage() for rec in caplog.records), (
        "가드가 발동했는데 로그가 없다 — 발동 빈도를 알 수 없다"
    )
