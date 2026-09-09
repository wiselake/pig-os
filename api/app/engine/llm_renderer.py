"""
LLM Renderer — Addon #1 (AI Insight).

Same interface as the Template Renderer, but turns a StructuredResult into a
natural-language explanation via an LLM. The LLM is told to **explain only, never
judge** — all decisions already come from the verified Rule Engine.

Safety / cost controls:
  * Falls back to the Template Renderer when no API key is configured, when
    ``use_llm`` is False, or when the farm's monthly quota is exhausted.
  * Vendor-agnostic: swap the call in ``_call_llm`` without touching chat_service.

This module never imports the vendor SDK at module load (lazy import inside the
call) so the Base tier has zero extra dependencies.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from app.engine.renderer import render_text
from app.engine.rule_engine import StructuredResult

logger = logging.getLogger(__name__)

MONTHLY_LIMIT = 100
LLM_MODEL = "claude-haiku-4-5-20251001"


def has_api_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"))


def within_quota(used: int, limit: int = MONTHLY_LIMIT) -> bool:
    return used < limit


# detail 중 LLM이 설명에 쓸 수 있는 안전 키만 통과(룰엔진 계산값, raw DB 아님).
_DETAIL_WHITELIST = ("loss", "grade", "ear_tag", "weakest_kpi", "weakest_rule",
                     "method", "benchmark_avg", "accidents", "per_litter", "head", "matings")


def _safe_detail(detail: dict) -> dict:
    return {k: detail[k] for k in _DETAIL_WHITELIST if k in detail}


def _result_to_payload(result: StructuredResult) -> dict:
    """Compact, vendor-neutral JSON the LLM is allowed to see (no raw DB rows)."""
    return {
        "intent": result.intent,
        "severity": result.severity.value,
        "as_of": str(result.as_of),
        "findings": [
            {
                "rule_id": f.rule_id,
                "kpi": f.kpi,
                "severity": f.severity.value,
                "current_value": f.current_value,
                "target_value": f.target_value,
                "grade": getattr(f, "grade", None),
                "causes": f.causes,
                "recommended_actions": f.recommended_actions,
                "detail": _safe_detail(f.detail) if getattr(f, "detail", None) else {},
            }
            for f in result.findings
        ],
    }


# 7개 로케일(공개 6 + ko 관리자). 미지정은 English 폴백.
_LANG_NAME = {
    "ko": "Korean", "en": "English", "zh": "Chinese", "es": "Spanish",
    "vi": "Vietnamese", "th": "Thai", "pt": "Brazilian Portuguese",
}


def build_system_prompt(locale: str) -> str:
    lang = _LANG_NAME.get(locale, "English")
    # PigPlan RENDERER 가이드 증류(출력규칙·금지·데이터신뢰) — 판단 금지 원칙은 유지.
    return (
        "You are a swine-farm analytics explainer. You receive a JSON object produced "
        "by a verified rule engine (the 'findings'). Your ONLY job is to explain that "
        f"result in fluent {lang}, in 2-4 short sentences.\n"
        "Rules:\n"
        "- Explain only. Do NOT add new judgments, numbers, diagnoses, or recommendations "
        "beyond what the JSON contains. Do not contradict or re-rank the findings.\n"
        "- Lead with the most severe finding (CRITICAL > WARNING > INFO).\n"
        "- For actions, use ONLY the items in recommended_actions; never invent specifics, "
        "and never name a drug, vaccine, or commercial product.\n"
        "- State a monetary amount ONLY if a finding's detail.loss.amount is present; if "
        "detail.loss.demo is true, present it as an approximate estimate.\n"
        "- If a value is 0 or 0%, treat it as possibly missing input rather than asserting "
        "perfect or zero performance.\n"
        "- Be concrete and practical; do not pad with generalities."
    )


# ── 출력 가드 — 프롬프트가 아니라 코드로 강제한다 ──────────────────────────
#
# CLAUDE.md: "LLM은 판단 금지 — 검증된 Rule Engine 결과를 자연어로 변환만".
# 그동안 그 원칙은 build_system_prompt() 의 문장으로만 존재했고, 모델 응답은
# 검증 없이 그대로 사용자에게 나갔다. 프롬프트는 요청이지 강제가 아니다.
#
# 유료 티어(AI Insight)에서만 LLM 경로를 타므로, 지어낸 숫자는 **돈을 낸
# 고객에게만** 도달했다. 그래서 표시 전에 막는다.

# 통화 기호 또는 통화 코드를 동반한 금액.
_MONEY = re.compile(
    r"(?:R\$|US\$|[$€£¥₩])\s*\d[\d.,]*"
    r"|\d[\d.,]*\s*(?:USD|BRL|VND|KRW|CNY|THB|MXN|EUR|GBP)\b",
    re.IGNORECASE,
)

# 소수 또는 퍼센트 — "데이터로 읽히는" 숫자만 본다.
# 맨 정수(예: "3가지 원인")는 산문 표현과 구분할 수 없어 검사 대상이 아니다.
_DATA_NUMBER = re.compile(r"\d+(?:[.,]\d+)+%?|\d+%")


def _collect_numbers(node: Any, out: set[float]) -> None:
    """룰엔진 결과에 실제로 등장하는 수치를 모두 모은다."""
    if isinstance(node, bool) or node is None:
        return
    if isinstance(node, (int, float)):
        out.add(float(node))
    elif isinstance(node, dict):
        for v in node.values():
            _collect_numbers(v, out)
    elif isinstance(node, (list, tuple)):
        for v in node:
            _collect_numbers(v, out)


def _allowed_numbers(result: StructuredResult) -> set[float]:
    nums: set[float] = set()
    _collect_numbers(_result_to_payload(result), nums)
    # 기준일은 문장에 그대로 쓰이는 것이 정상이다(2026-09-07).
    nums.update({float(result.as_of.year), float(result.as_of.month), float(result.as_of.day)})
    return nums


def _as_float(token: str) -> float | None:
    """'1,200' · '5.000' · '42.5%' 같은 표기를 수치로 읽는다.

    ★ 자릿수 구분자와 소수점은 로케일마다 반대다(pt-BR 은 5.000 = 오천).
      그래서 두 해석을 모두 시도하고, 하나라도 허용값과 맞으면 통과시킨다.
      가드가 로케일 표기 때문에 정상 응답을 죽이지 않게 하려는 것이다."""
    t = token.strip().rstrip("%").strip()
    for cleaned in (t.replace(",", ""), t.replace(".", "").replace(",", ".")):
        try:
            return float(cleaned)
        except ValueError:
            continue
    return None


def _matches_allowed(value: float, allowed: set[float]) -> bool:
    """반올림 재표기는 왜곡이 아니다 — 42.5 를 43 이나 42.50 으로 쓸 수 있다."""
    for a in allowed:
        for digits in (0, 1, 2, 3):
            if round(a, digits) == round(value, digits):
                return True
    return False


def _loss_amounts(result: StructuredResult) -> set[float]:
    out: set[float] = set()
    for f in result.findings:
        loss = (getattr(f, "detail", None) or {}).get("loss")
        if isinstance(loss, dict) and isinstance(loss.get("amount"), (int, float)):
            out.add(float(loss["amount"]))
    return out


def verify_rendering(text: str, result: StructuredResult) -> str | None:
    """설명이 룰엔진 결과를 벗어나지 않는지 확인한다.

    Returns:
        None 이면 통과. 문자열이면 거부 사유(로그용).

    ★ 범위를 좁게 잡았다. 개체 이표번호(ear_tag)는 검사하지 않는다 — 농장마다
      형식이 달라 텍스트에서 안전하게 식별할 규칙이 없고, 느슨하게 잡으면
      날짜·제품명까지 걸려 유료 응답이 상시 템플릿으로 떨어진다. 가드가
      오작동해 기능을 죽이는 쪽이 지어낸 숫자보다 나쁘다. 별도 과제로 둔다.
    """
    allowed = _allowed_numbers(result)

    # 1) 금액 — 가장 위험하다. 고객은 이 숫자를 실제 손실로 읽는다.
    money = _MONEY.findall(text)
    if money:
        losses = _loss_amounts(result)
        if not losses:
            return f"money mentioned but no finding carries detail.loss.amount: {money[0]!r}"
        for m in money:
            digits = re.search(r"\d[\d.,]*", m)
            value = _as_float(digits.group()) if digits else None
            if value is None or not _matches_allowed(value, losses):
                return f"money amount not in findings: {m!r}"

    # 2) 소수·퍼센트 — 룰엔진이 내지 않은 수치인지
    for token in _DATA_NUMBER.findall(text):
        value = _as_float(token)
        if value is None:
            continue
        if not _matches_allowed(value, allowed):
            return f"number not produced by the rule engine: {token!r}"

    return None


async def _call_llm(result: StructuredResult, locale: str) -> str:
    """Vendor call. Lazy-imports the SDK; raises on any failure (caller falls back)."""
    import anthropic  # lazy

    client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = await client.messages.create(
        model=LLM_MODEL,
        max_tokens=400,
        system=build_system_prompt(locale),
        messages=[{"role": "user", "content": json.dumps(_result_to_payload(result), ensure_ascii=False)}],
    )
    return msg.content[0].text.strip()


async def render(
    result: StructuredResult,
    locale: str = "en",
    *,
    use_llm: bool = False,
    usage_count: int = 0,
) -> tuple[str, str]:
    """Return ``(text, rendered_by)`` where rendered_by is "llm" or "template".

    Falls back to the template renderer whenever the LLM path is unavailable or
    disallowed, so callers always get a valid answer.
    """
    if not use_llm or not has_api_key() or not within_quota(usage_count):
        return render_text(result, locale), "template"
    try:
        text = await _call_llm(result, locale)
    except Exception:
        return render_text(result, locale), "template"

    # 표시 전 검증. 실패하면 같은 결과의 템플릿으로 대체한다 —
    # 사용자는 항상 유효한 답을 받고 API 계약(renderer)도 그대로다.
    reason = verify_rendering(text, result)
    if reason:
        # ★ 조용히 떨어뜨리지 않는다. 이 프로젝트는 이미 침묵 실패로 데였다
        #   (ARQ 잡이 실패를 성공으로 보고하던 건). 발동 빈도를 알아야
        #   프롬프트를 고칠지 모델을 바꿀지 판단할 수 있다.
        logger.warning(
            "LLM rendering rejected (intent=%s, locale=%s): %s", result.intent, locale, reason
        )
        return render_text(result, locale), "template"
    return text, "llm"
