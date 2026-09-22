"""약관 문서 렌더러 (TERMS_DISPLAY_SPEC §1, §2, §5, §7).

마스터 + 글로벌 방침 + (해당 국가) 부속조항 1개를 조합해 표시 세트를 만든다.
문구는 content/legal/*.md placeholder(변호사 확정 전) — 이 모듈은 조합·버전·언어우선만 담당.
notice_version = 표시된 문서 버전 묶음의 결정적 라벨 → consent_ledger 에 그대로 기록.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_CONTENT_DIR = Path(__file__).resolve().parents[2] / "content" / "legal"


@lru_cache(maxsize=1)
def _manifest() -> dict:
    return json.loads((_CONTENT_DIR / "manifest.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class RenderedDoc:
    doc_id: str
    kind: str               # master | privacy | addendum
    version: str
    status: str             # DRAFT_LAWYER_PENDING ...
    lang: str               # 실제 반환된 본문 언어
    is_legal_priority: bool  # 이 언어가 법적 우선본인지
    lang_pending: bool       # 법정 요구 현지어 미비 → 출시 게이트 신호
    body: str


@dataclass(frozen=True)
class DocumentSet:
    jurisdiction_code: str
    group: str
    lang: str
    docs: list[RenderedDoc]
    notice_version: str      # 예: 'MASTER_TERMS@0.1-draft+GLOBAL_PRIVACY_NOTICE@0.1-draft+ADDENDUM_US@0.1-draft'
    any_draft: bool          # 하나라도 DRAFT → 실서비스 게시 불가 신호
    lang_gate: bool          # 법정 현지어 미비 문서 존재 → 해당국 출시 게이트


def _pick_lang(doc_meta: dict, want: str) -> tuple[str, str]:
    """(file, lang) — 원하는 언어 없으면 en 폴백."""
    langs = doc_meta.get("langs", {})
    if want in langs:
        return langs[want], want
    if "en" in langs:
        return langs["en"], "en"
    # 아무거나
    k = next(iter(langs))
    return langs[k], k


def _render_one(doc_id: str, doc_meta: dict, want_lang: str) -> RenderedDoc:
    file, lang = _pick_lang(doc_meta, want_lang)
    body = (_CONTENT_DIR / file).read_text(encoding="utf-8")
    priority_lang = doc_meta.get("legal_priority_lang")
    pending = bool(doc_meta.get("pending_langs")) and priority_lang in (doc_meta.get("pending_langs") or [])
    is_priority = (priority_lang is None) or (lang == priority_lang)
    return RenderedDoc(
        doc_id=doc_id,
        kind=doc_meta.get("kind", "unknown"),
        version=doc_meta.get("version", "0"),
        status=doc_meta.get("status", "UNKNOWN"),
        lang=lang,
        is_legal_priority=is_priority,
        lang_pending=pending,
        body=body,
    )


# group -> addendum doc id (TERMS_DISPLAY §2)
#
# ★ D-16 (2026-09-10): KR·CN 은 부속조항을 두지 않는다 — 키를 빠뜨린 것이 아니라
#   None 으로 명시한다. jurisdiction._ADDENDUM 과 같은 의도를 두 곳이 같은 형태로
#   말하게 한다. 값 None 과 키 부재는 아래 build_document_set 에서 결과가 동일하다.
#     KR    PigOS 비대상(A-rule, signup_blocked). 한국법 적용은 마스터 준거법 조항과
#           목적② KR 분기가 흡수한다. ※ 법정 고지사항 충족 여부는 COUNSEL_PENDING
#     CN    진입 구조 미결(D-07)이라 부속조항이 성립하지 않는다. HOLD 는
#           docs/legal/internal/INTERNAL_LAUNCH_GATE_CN.md
#     OTHER 부속조항 없음 = 마스터+방침 두 건이 완전한 세트 (설계)
_GROUP_ADDENDUM: dict[str, str | None] = {
    "US": "ADDENDUM_US", "EU": "ADDENDUM_EU", "GB": "ADDENDUM_GB",
    "BR": "ADDENDUM_BR", "TH": "ADDENDUM_TH", "VN": "ADDENDUM_VN",
    "KR": None, "CN": None, "OTHER": None,
}


def language_for(group: str) -> str:
    return _manifest().get("language_priority", {}).get(group, "en")


def build_document_set(*, jurisdiction_code: str, group: str, lang: str | None = None) -> DocumentSet:
    """법역 그룹에 맞는 표시 문서 세트 조립."""
    m = _manifest()
    docs_meta = m["documents"]
    want = lang or language_for(group)

    order = ["MASTER_TERMS", "GLOBAL_PRIVACY_NOTICE"]
    addendum_id = _GROUP_ADDENDUM.get(group)
    if addendum_id and addendum_id in docs_meta:
        order.append(addendum_id)

    docs = [_render_one(did, docs_meta[did], want) for did in order]
    notice_version = "+".join(f"{d.doc_id}@{d.version}" for d in docs)
    any_draft = any(d.status.startswith("DRAFT") for d in docs)
    lang_gate = any(d.lang_pending for d in docs)

    return DocumentSet(
        jurisdiction_code=jurisdiction_code,
        group=group,
        lang=want,
        docs=docs,
        notice_version=notice_version,
        any_draft=any_draft,
        lang_gate=lang_gate,
    )
