"""동의 인프라 스키마 (CONSENT_SPEC §3~§5, TERMS_DISPLAY §4·§7)."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocMeta(BaseModel):
    doc_id: str
    kind: str
    version: str
    status: str
    lang: str
    is_legal_priority: bool
    lang_pending: bool
    body: str | None = None


class PurposePlan(BaseModel):
    purpose_code: str
    order: int
    ui_kind: str            # NOTICE | NOTICE_EXCLUSION | LI_OBJECT | OPT_IN | WRITTEN_OPT_IN | HIDDEN | TRANSFER_CONSENT | BLOCKED
    lawful_basis: str
    visible: bool           # 화면 노출 여부(HIDDEN/BLOCKED=false)
    is_toggle: bool         # 사용자 개별 토글(옵트인) 여부
    default_on: bool = False
    requires_evidence: bool = False
    status_tag: str
    auto_off_if_uoom: bool = False   # ⑤: UOOM 신호 시 강제 OFF


class GateOut(BaseModel):
    signup_blocked: bool = False
    paid_blocked: bool = False
    release_hold: bool = False
    reason_code: str | None = None


class StateFlagsOut(BaseModel):
    state: str | None = None
    written_opt_in_required: bool = False
    do_not_sell_link: bool = False
    honor_uoom: bool = False
    exclude_location_from_sale: bool = False


class JurisdictionOut(BaseModel):
    code: str
    country: str
    group: str
    counsel_review: bool = False
    notes: list[str] = Field(default_factory=list)


class SignupPlan(BaseModel):
    """가입 동의 화면을 그리는 데 필요한 전부. 프론트는 이걸로 UI 구성."""
    jurisdiction: JurisdictionOut
    gate: GateOut
    state_flags: StateFlagsOut
    documents: list[DocMeta]
    notice_version: str
    any_draft: bool
    lang_gate: bool
    required_acks: list[str]          # ['TERMS', 'PRIVACY'] — 필수 2체크
    purposes: list[PurposePlan]
    lang: str


class ConsentChoice(BaseModel):
    purpose_code: str
    granted: bool = False
    evidence_ref: str | None = None   # 서면·전자서명 증적(NE 등)


class RecordConsentRequest(BaseModel):
    farm_id: UUID | None = None
    selected_country: str
    farm_country: str | None = None
    farm_state: str | None = None
    lang: str | None = None
    terms_ack: bool = False
    privacy_ack: bool = False
    choices: list[ConsentChoice] = Field(default_factory=list)
    collection_context: str = "UI_SIGNUP"


class ConsentStatusOut(BaseModel):
    purpose_code: str
    jurisdiction: str
    lawful_basis: str
    consent_status: str
    notice_version: str
    accepted_at: datetime | None = None
    withdrawn_at: datetime | None = None
    effective_from: date | None = None
    collection_context: str


class ConsentDiffItem(BaseModel):
    """목적 하나에 대한 두 사실 — 지금 필요한 버전과 원장에 적힌 버전. 판정 없음.

    LEGAL-P0-MANDATORY-CONSENT-LOGIN-GATE 구현 메모: 계정 단위 불리언은 만들지 않는다.
    어느 전이가 재동의인가(H16)·어느 모드로 막는가(H11)는 이 위에 한 겹 얹는다.
    """
    purpose_code: str
    lawful_basis: str
    ui_kind: str                          # 지금 계획의 UI 종류 (NOTICE/OPT_IN/…)
    required_version: str                 # 서버가 도출한 법역의 현재 notice_version
    recorded_version: str | None          # 원장 최신 행의 notice_version. 행이 없으면 None
    recorded_status: str | None           # GRANTED · NOTICE_GIVEN · WITHDRAWN … 행이 없으면 None
    recorded_at: datetime | None          # 그 행의 accepted_at


class ConsentDiffOut(BaseModel):
    """★ 국가는 서버가 정한다. 클라이언트 입력을 받지 않는다.

    가입 전 signup-plan 은 selected_country 를 쿼리로 받는다 — 계정이 없으니 그게 맞다.
    로그인 사용자의 diff 에서 같은 일을 하면, 문서가 적은 법역(KR·CN 은 부속조항이 없다)을
    지정해 "동의 완료"로 보이게 만들 수 있다. 법역은 farm.country(농장 스코프) 또는
    organization.country(계정 스코프)에서 도출하고, 그 출처를 응답에 적는다.
    """
    jurisdiction: str                     # 도출된 법역 코드
    group: str
    country: str                          # 도출에 쓴 ISO2
    country_source: str                   # FARM | ORG
    farm_id: UUID | None
    required_version: str                 # 문서 세트 전체의 notice_version (items 의 공통값)
    any_draft: bool                       # 필요 버전 자체가 초안인가 — 초안이면 재동의를 요구할 수 없다
    items: list[ConsentDiffItem]


class WithdrawRequest(BaseModel):
    purpose_code: str
    farm_id: UUID | None = None
    # WITHDRAWN(옵트인 철회) | OBJECTED(LI 이의) | EXCLUSION_REQUESTED(익명 편입 제외)
    action: str = "WITHDRAWN"
    reason: str | None = None
