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

from app.core.exceptions import ForbiddenError
from app.core.permissions import can_access_farm
from app.db.models.consent import ConsentRecord
from app.db.models.platform import User
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
from app.services import eligibility
from app.services import jurisdiction as jz
from app.services import terms_renderer as tr

_TOGGLE_KINDS = {"OPT_IN", "WRITTEN_OPT_IN", "TRANSFER_CONSENT"}
_WITHDRAW_ACTIONS = {"WITHDRAWN", "OBJECTED", "EXCLUSION_REQUESTED"}


async def _assert_farm_authority(
    db: AsyncSession, *, user_id: UUID, farm_id: UUID | None,
) -> None:
    """farm_id 가 주어졌으면 그 농장에 대한 접근 권한을 확인한다 (LEGAL-P0-CONSENT-FARM-AUTHORITY).

    ## 왜 필요한가

    이전에는 요청 본문의 `farm_id` 를 그대로 원장에 썼다. 인증만 하면 **남의 농장에
    귀속된 동의 행**을 만들 수 있었다. 읽기는 user_id 로 걸려 유출은 없었지만,
    원장은 "누가 · 어느 농장에 대해 · 무엇에 동의했는가" 의 법적 증거물이다.
    귀속이 틀린 행이 섞이면 그 원장으로는 아무것도 증명하지 못한다.

    ## 판정 기준 — 새 규칙을 만들지 않는다

    법무 전용 membership 규칙을 따로 만들면 기존 권한 모델과 갈라진다. farm-scoped
    API 가 이미 쓰는 canonical semantics(`can_access_farm`)를 그대로 재사용한다 —
    SUPER_ADMIN 전체, 조직레벨 롤은 org 서브트리, 농장레벨 롤은 user_farms 멤버십.
    `get_farm_context` 가 판정에 쓰는 것과 같은 함수다.

    실패도 같은 예외를 쓴다. `get_farm_context` 는 없는 농장·비활성 농장·접근 불가
    농장을 모두 ForbiddenError(403) 로 처리하며 404 로 존재를 숨기지 않는다.
    동의 엔드포인트만 새 status 를 발명하지 않는다.

    ★ farm_id 가 None 이면 검사하지 않는다. 계정 단위 목적(①⑥)은 농장 스코프가
      없는 것이 정상이다(`ConsentRecord.farm_id` 가 nullable 인 이유). 이 변경은
      모든 동의를 farm-scoped 로 강제하지 않는다.
    """
    if farm_id is None:
        return
    user = await db.get(User, user_id)
    if user is None or not await can_access_farm(user, farm_id, db):
        raise ForbiddenError("No access to this farm")


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
    # override 구성은 eligibility 파사드가 단일 출처다. 여기서 따로 만들면
    # "동의 화면은 막는데 가입은 뚫리는" 상태가 다시 생긴다(LEGAL-P0-CONSENT-AUTHORITY).
    j = eligibility.resolve_entry(
        selected_country=selected_country,
        farm_country=farm_country,
        farm_state=farm_state,
        extra_overrides=feature_overrides,
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
    # 인가 먼저 — 남의 농장인지 여부는 본문 유효성보다 앞선 질문이다.
    await _assert_farm_authority(db, user_id=user_id, farm_id=req.farm_id)

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
    # ★ commit 한다 (LEGAL-P0-CONSENT-LEDGER-PERSISTENCE).
    #
    #   flush 만 하면 요청 종료 시 `get_db` 가 세션을 닫으면서 전부 rollback 된다.
    #   200 을 받고도 원장이 비는 상태였다. 이 저장소는 **서비스가 트랜잭션을
    #   소유**하고 커밋한다 — event_service·auth_service·farm_service 전부 그렇다.
    #   consent_service 만 쓰기를 하면서 커밋하지 않는 유일한 서비스였다.
    #
    #   여기서 커밋해도 다른 업무의 atomicity 를 깨지 않는다: 이 함수의 호출자는
    #   consent 라우터 하나뿐이고, 다른 서비스 트랜잭션 안에서 불리지 않는다.
    await db.commit()
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
    # record 만 막으면 이 경로로 같은 일을 할 수 있다 — 두 경로 모두 검증한다.
    await _assert_farm_authority(db, user_id=user_id, farm_id=req.farm_id)

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

    # ★ farm_id 를 생략하면 아래에서 prev.farm_id 를 상속한다(`req.farm_id or prev.farm_id`).
    #   상속분을 검사하지 않으면 "farm_id 를 빼는 것"만으로 위 검증을 건너뛰고, 접근할 수
    #   없는 농장에 귀속된 행을 **새로** 하나 더 만들 수 있다. 결함기에 만들어진 행이나
    #   농장 비활성화(account_deletion_service 가 owner 삭제 시 farm.active=False)로
    #   접근을 잃은 경우가 실제 경로다. 상속할 값도 같은 기준으로 검증한다.
    if req.farm_id is None and prev.farm_id is not None:
        await _assert_farm_authority(db, user_id=user_id, farm_id=prev.farm_id)

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
    # 철회도 남아야 한다 — 저장되지 않는 철회는 기록하지 않은 것과 같다.
    await db.commit()
    return _to_status(rec)


def _to_status(r: ConsentRecord) -> ConsentStatusOut:
    return ConsentStatusOut(
        purpose_code=r.purpose_code, jurisdiction=r.jurisdiction,
        lawful_basis=r.lawful_basis, consent_status=r.consent_status,
        notice_version=r.notice_version, accepted_at=r.accepted_at,
        withdrawn_at=r.withdrawn_at, effective_from=r.effective_from,
        collection_context=r.collection_context,
    )
