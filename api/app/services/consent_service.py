"""동의 인프라 서비스 (CONSENT_SPEC §3~§5, TERMS_DISPLAY §4·§7).

- build_signup_plan: 법역 판별 + 문서 세트 + 목적별 UI 계획 → 가입 화면 스펙
- record_consents: 가입/설정 선택을 consent_ledger 에 append
- current_consents: (user, farm)별 목적 최신 상태
- withdraw: 철회/이의/제외요청 append (append-only, 원장 이력 보존)

문구·미결값은 다루지 않는다(콘텐츠·설정 파일 소관). 여기선 상태·근거·버전만.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.consent import ConsentRecord
from app.policy import consent_matrix as cm
from app.schemas.consent import (
    ConsentChoice,
    ConsentStatusOut,
    DocMeta,
    GateOut,
    JurisdictionOut,
    PurposePlan,
    RecordConsentRequest,
    SignupPlan,
    StateFlagsOut,
    WithdrawRequest,
)
from app.services import jurisdiction as jz
from app.services import terms_renderer as tr

_TOGGLE_KINDS = {"OPT_IN", "WRITTEN_OPT_IN", "TRANSFER_CONSENT"}
_WITHDRAW_ACTIONS = {"WITHDRAWN", "OBJECTED", "EXCLUSION_REQUESTED"}


def _effective_ui_kind(base_kind: str, purpose: str, sf: jz.StateFlags) -> str:
    """주별 분기 반영(§3): NE 서면 옵트인 등."""
    if sf.written_opt_in_required and purpose in ("ANON_AGG_STATS", "NAMED_RESEARCH"):
        # LB525: 농업데이터 판매(②)·기명 제공(④)은 서면 옵트인
        return "WRITTEN_OPT_IN"
    return base_kind


def build_signup_plan(
    *,
    selected_country: str,
    farm_country: str | None,
    farm_state: str | None,
    lang: str | None,
    include_body: bool = True,
    feature_overrides: dict[str, bool] | None = None,
) -> SignupPlan:
    # 게이트 판정은 jurisdiction.resolve_for_signup 이 SSOT — 가입 경로 전부가 같은 판정을 쓴다.
    # (KR 은 운영 기본 차단=레퍼런스 전용, allow_kr_signup env 로만 해제. 서버 값이라 우회 불가.)
    j = jz.resolve_for_signup(
        selected_country=selected_country,
        farm_country=farm_country,
        farm_state=farm_state,
        feature_overrides=feature_overrides,
    )
    use_lang = lang or tr.language_for(j.group)
    doc_set = tr.build_document_set(jurisdiction_code=j.code, group=j.group, lang=use_lang)

    purposes: list[PurposePlan] = []
    for order, code in enumerate(cm.SIGNUP_PURPOSE_ORDER):
        pol = cm.policy_for(code, j.group)
        eff_kind = _effective_ui_kind(pol.ui_kind, code, j.state_flags)
        visible = eff_kind not in ("HIDDEN", "BLOCKED")
        is_toggle = eff_kind in _TOGGLE_KINDS
        requires_ev = pol.requires_evidence or eff_kind == "WRITTEN_OPT_IN"
        purposes.append(PurposePlan(
            purpose_code=code,
            order=order,
            ui_kind=eff_kind,
            lawful_basis=pol.lawful_basis,
            visible=visible,
            is_toggle=is_toggle,
            default_on=False,
            requires_evidence=requires_ev,
            status_tag=pol.status_tag,
            auto_off_if_uoom=(code == "TRANSACTION_MATCHING" and j.state_flags.honor_uoom),
        ))

    documents = [
        DocMeta(
            doc_id=d.doc_id, kind=d.kind, version=d.version, status=d.status,
            lang=d.lang, is_legal_priority=d.is_legal_priority, lang_pending=d.lang_pending,
            body=d.body if include_body else None,
        )
        for d in doc_set.docs
    ]

    return SignupPlan(
        jurisdiction=JurisdictionOut(
            code=j.code, country=j.country, group=j.group,
            counsel_review=j.counsel_review, notes=j.notes,
        ),
        gate=GateOut(
            signup_blocked=j.gate.signup_blocked, paid_blocked=j.gate.paid_blocked,
            release_hold=j.gate.release_hold, reason_code=j.gate.reason_code,
        ),
        state_flags=StateFlagsOut(
            state=j.state_flags.state,
            written_opt_in_required=j.state_flags.written_opt_in_required,
            do_not_sell_link=j.state_flags.do_not_sell_link,
            honor_uoom=j.state_flags.honor_uoom,
            exclude_location_from_sale=j.state_flags.exclude_location_from_sale,
        ),
        documents=documents,
        notice_version=doc_set.notice_version,
        any_draft=doc_set.any_draft,
        lang_gate=doc_set.lang_gate,
        required_acks=["TERMS", "PRIVACY"],
        purposes=purposes,
        lang=use_lang,
    )


def _synth_evidence(context: str, notice_version: str, choice: ConsentChoice) -> str:
    if choice.evidence_ref:
        return choice.evidence_ref
    ts = datetime.now(UTC).isoformat()
    return f"{context}|{notice_version}|checkbox|{ts}"


async def record_consents(
    db: AsyncSession, *, user_id: UUID, req: RecordConsentRequest,
) -> list[ConsentStatusOut]:
    """가입/설정 동의 선택을 원장에 기록. 필수 동의 미체크면 422."""
    if req.collection_context == "UI_SIGNUP" and not (req.terms_ack and req.privacy_ack):
        raise HTTPException(422, "TERMS_AND_PRIVACY_ACK_REQUIRED")

    plan = build_signup_plan(
        selected_country=req.selected_country,
        farm_country=req.farm_country,
        farm_state=req.farm_state,
        lang=req.lang,
        include_body=False,
    )
    if plan.gate.signup_blocked:
        raise HTTPException(451, f"SIGNUP_BLOCKED:{plan.gate.reason_code}")

    now = datetime.now(UTC)
    by_code = {c.purpose_code: c for c in req.choices}
    plan_by_code = {p.purpose_code: p for p in plan.purposes}
    written: list[ConsentRecord] = []

    for code, p in plan_by_code.items():
        if not p.visible:
            continue  # HIDDEN(VN⑤)/BLOCKED 는 기록 안 함
        choice = by_code.get(code)

        if not p.is_toggle:
            # 고지형(①②⑥ notice/LI/익명) — 가입 시 NOTICE_GIVEN 기록
            status = "NOTICE_GIVEN"
            rec = ConsentRecord(
                user_id=user_id, farm_id=req.farm_id, purpose_code=code,
                jurisdiction=plan.jurisdiction.code, lawful_basis=p.lawful_basis,
                consent_status=status, notice_version=plan.notice_version,
                accepted_at=now, effective_from=now.date(),
                collection_context=req.collection_context,
                evidence_ref=None,
            )
            written.append(rec)
            continue

        # 옵트인/서면/이전동의 — granted 일 때만 GRANTED 기록(기본 OFF 는 미기록)
        if choice and choice.granted:
            evidence = _synth_evidence(req.collection_context, plan.notice_version, choice)
            if p.requires_evidence and not evidence:
                raise HTTPException(422, f"EVIDENCE_REQUIRED:{code}")
            written.append(ConsentRecord(
                user_id=user_id, farm_id=req.farm_id, purpose_code=code,
                jurisdiction=plan.jurisdiction.code, lawful_basis="CONSENT",
                consent_status="GRANTED", notice_version=plan.notice_version,
                accepted_at=now, effective_from=now.date(),
                collection_context=req.collection_context, evidence_ref=evidence,
            ))

    for rec in written:
        db.add(rec)
    await db.flush()
    return [_to_status(r) for r in written]


async def current_consents(
    db: AsyncSession, *, user_id: UUID, farm_id: UUID | None,
) -> list[ConsentStatusOut]:
    """(user, farm)별 목적 최신 상태 = 현재 유효(§5.2)."""
    stmt = (
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user_id)
        .order_by(ConsentRecord.created_at.desc())
    )
    if farm_id is not None:
        stmt = stmt.where(ConsentRecord.farm_id == farm_id)
    rows = (await db.execute(stmt)).scalars().all()

    latest: dict[str, ConsentRecord] = {}
    for r in rows:
        if r.purpose_code not in latest:
            latest[r.purpose_code] = r
    return [_to_status(r) for r in latest.values()]


async def withdraw(
    db: AsyncSession, *, user_id: UUID, req: WithdrawRequest,
) -> ConsentStatusOut:
    """철회/이의/제외요청 append. 이전 근거·법역 승계."""
    if req.action not in _WITHDRAW_ACTIONS:
        raise HTTPException(422, f"INVALID_ACTION:{req.action}")

    stmt = (
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user_id, ConsentRecord.purpose_code == req.purpose_code)
        .order_by(ConsentRecord.created_at.desc())
        .limit(1)
    )
    if req.farm_id is not None:
        stmt = stmt.where(ConsentRecord.farm_id == req.farm_id)
    prev = (await db.execute(stmt)).scalars().first()
    if prev is None:
        raise HTTPException(404, f"NO_CONSENT_RECORD:{req.purpose_code}")

    now = datetime.now(UTC)
    rec = ConsentRecord(
        user_id=user_id, farm_id=req.farm_id or prev.farm_id, purpose_code=req.purpose_code,
        jurisdiction=prev.jurisdiction, lawful_basis=prev.lawful_basis,
        consent_status=req.action, notice_version=prev.notice_version,
        accepted_at=prev.accepted_at, withdrawn_at=now, effective_from=now.date(),
        collection_context="UI_SETTINGS",
        evidence_ref=(req.reason or prev.evidence_ref),
    )
    db.add(rec)
    await db.flush()
    return _to_status(rec)


def _to_status(r: ConsentRecord) -> ConsentStatusOut:
    return ConsentStatusOut(
        purpose_code=r.purpose_code, jurisdiction=r.jurisdiction,
        lawful_basis=r.lawful_basis, consent_status=r.consent_status,
        notice_version=r.notice_version, accepted_at=r.accepted_at,
        withdrawn_at=r.withdrawn_at, effective_from=r.effective_from,
        collection_context=r.collection_context,
    )
