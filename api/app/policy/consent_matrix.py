"""목적×법역 lawful-basis 매트릭스 (CONSENT_AND_DATA_USE_SPEC §2 + TERMS_DISPLAY_SPEC §2·§3).

이 모듈은 정책의 코드화이며 변호사 확정 전 초안(D-01~D-04 DECIDED 조건부)을 반영한다.
문구는 콘텐츠 파일(content/legal/**), 미결 수치(코호트 k 등)는 설정에서 온다 — 여기엔 없음.

UI_KIND 의미:
  NOTICE            방침 고지만 (동의·토글 아님)
  NOTICE_EXCLUSION  고지 + 제외요청 채널 (② 익명, 토글 아님 — D-01)
  LI_OBJECT         정당한이익 고지 + 이의권(object) 채널 (② EU/GB/BR — D-01)
  OPT_IN            기본 OFF 개별 토글 (③④⑤ — D-02)
  WRITTEN_OPT_IN    서면(전자서명 수준) 옵트인 (US-NE 농업데이터 판매 — LB525)
  HIDDEN            해당 법역 미노출 (VN ⑤ — 매매 규제)
  TRANSFER_CONSENT  국외이전 별도 동의 (⑥ VN/CN)
  BLOCKED           진입 차단 (CN — D-07 HOLD)
"""
from __future__ import annotations

from dataclasses import dataclass

# --- 법역 그룹 ------------------------------------------------------------

EU_MEMBER_STATES = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE",
})

# 정책 그룹 키
GROUP_KR, GROUP_US, GROUP_EU, GROUP_GB = "KR", "US", "EU", "GB"
GROUP_BR, GROUP_TH, GROUP_VN, GROUP_CN = "BR", "TH", "VN", "CN"
GROUP_OTHER = "OTHER"


def group_for_country(country: str) -> str:
    """ISO alpha-2 국가코드 → 정책 그룹."""
    c = (country or "").upper()
    if c == "KR":
        return GROUP_KR
    if c == "US":
        return GROUP_US
    if c in EU_MEMBER_STATES:
        return GROUP_EU
    if c == "GB":
        return GROUP_GB
    if c == "BR":
        return GROUP_BR
    if c == "TH":
        return GROUP_TH
    if c == "VN":
        return GROUP_VN
    if c == "CN":
        return GROUP_CN
    return GROUP_OTHER


# --- 목적 정책 -------------------------------------------------------------

@dataclass(frozen=True)
class PurposePolicy:
    purpose_code: str
    lawful_basis: str
    ui_kind: str
    # 가입 완료 시 사용자가 토글을 건드리지 않아도 기록할 상태(고지형). None = 옵트인 전엔 미기록.
    signup_status: str | None
    # CONSENT/WRITTEN_OPT_IN 은 증적 필수(§5.2). True 면 evidence_ref 없이 GRANTED 불가.
    requires_evidence: bool = False
    # 근거 신뢰도·출처 태그(§2 태그열) — UNVERIFIED 격리·법무 확인 트래킹용
    status_tag: str = "LEGAL_REQUIREMENT"
    # 국외이전(⑥) 별도 동의 필요 여부
    transfer_consent: bool = False


def _opt_in(purpose: str, basis: str = "CONSENT", tag: str = "LEGAL_REQUIREMENT") -> PurposePolicy:
    return PurposePolicy(purpose, basis, "OPT_IN", signup_status=None,
                         requires_evidence=True, status_tag=tag)


# purpose_code -> group -> PurposePolicy
MATRIX: dict[str, dict[str, PurposePolicy]] = {
    # ① SERVICE_OPERATION — 계약 이행, 고지로 충분(EU는 동의 구성 금지)
    "SERVICE_OPERATION": {
        GROUP_KR: PurposePolicy("SERVICE_OPERATION", "CONTRACT", "NOTICE", "NOTICE_GIVEN"),
        GROUP_US: PurposePolicy("SERVICE_OPERATION", "CONTRACT", "NOTICE", "NOTICE_GIVEN"),
        GROUP_EU: PurposePolicy("SERVICE_OPERATION", "CONTRACT", "NOTICE", "NOTICE_GIVEN"),
        GROUP_GB: PurposePolicy("SERVICE_OPERATION", "CONTRACT", "NOTICE", "NOTICE_GIVEN"),
        GROUP_BR: PurposePolicy("SERVICE_OPERATION", "CONTRACT", "NOTICE", "NOTICE_GIVEN"),
        GROUP_TH: PurposePolicy("SERVICE_OPERATION", "CONTRACT", "NOTICE", "NOTICE_GIVEN"),
        GROUP_VN: PurposePolicy("SERVICE_OPERATION", "CONTRACT", "NOTICE", "NOTICE_GIVEN",
                                status_tag="COUNSEL_CONFIRMATION_REQUIRED"),
        GROUP_CN: PurposePolicy("SERVICE_OPERATION", "CONTRACT", "BLOCKED", None,
                                status_tag="HOLD_D07"),
        GROUP_OTHER: PurposePolicy("SERVICE_OPERATION", "CONTRACT", "NOTICE", "NOTICE_GIVEN"),
    },
    # ② ANON_AGG_STATS — D-01 국가별 분기(핵심). 토글 아님.
    "ANON_AGG_STATS": {
        GROUP_KR: PurposePolicy("ANON_AGG_STATS", "ANONYMIZED_EXEMPT", "NOTICE_EXCLUSION",
                                "NOTICE_GIVEN", status_tag="COUNSEL_CONFIRMATION_REQUIRED"),
        GROUP_US: PurposePolicy("ANON_AGG_STATS", "DEIDENTIFIED_EXEMPT", "NOTICE_EXCLUSION",
                                "NOTICE_GIVEN", status_tag="CASE_OR_ENFORCEMENT"),
        GROUP_EU: PurposePolicy("ANON_AGG_STATS", "LEGITIMATE_INTEREST", "LI_OBJECT",
                                "NOTICE_GIVEN", status_tag="DRAFT_GUIDANCE"),
        GROUP_GB: PurposePolicy("ANON_AGG_STATS", "LEGITIMATE_INTEREST", "LI_OBJECT",
                                "NOTICE_GIVEN", status_tag="OFFICIAL_GUIDANCE"),
        GROUP_BR: PurposePolicy("ANON_AGG_STATS", "LEGITIMATE_INTEREST", "LI_OBJECT",
                                "NOTICE_GIVEN", status_tag="OFFICIAL_GUIDANCE"),
        # TH: LI 선례 미확립 → 고지+옵트아웃 병행(보수). 옵트아웃 채널 = NOTICE_EXCLUSION 로 취급.
        GROUP_TH: PurposePolicy("ANON_AGG_STATS", "LEGITIMATE_INTEREST", "NOTICE_EXCLUSION",
                                "NOTICE_GIVEN", status_tag="COUNSEL_CONFIRMATION_REQUIRED"),
        # VN: 상업적 재판매는 동의 항목 포함(보수 기준선) → 옵트인.
        GROUP_VN: _opt_in("ANON_AGG_STATS", tag="COUNSEL_CONFIRMATION_REQUIRED"),
        GROUP_CN: PurposePolicy("ANON_AGG_STATS", "ANONYMIZED_EXEMPT", "BLOCKED", None,
                                status_tag="HOLD_D07"),
        # ★ 미지원국(부속조항 없음) — 마스터 약관 제10조③: ②③④⑤ 기본 OFF,
        #   옵트아웃 자동적용 금지. 이전에는 "NOTICE_EXCLUSION"(고지+제외요청)이었는데
        #   그건 TERMS_DISPLAY_SPEC §2 "기타 국가" 행을 따른 것이고, 마스터가 우선한다.
        #   법역 검토를 마치지 않은 국가에서 익명·집계 처리를 고지만으로 시작하지 않는다.
        #   ※ 이 값은 어떤 국가도 legal-ready 로 만들지 않는다 — 비활성화일 뿐이다.
        GROUP_OTHER: PurposePolicy("ANON_AGG_STATS", "ANONYMIZED_EXEMPT", "BLOCKED",
                                   "NOTICE_GIVEN", status_tag="COUNSEL_CONFIRMATION_REQUIRED"),
    },
    # ③ AI_MODEL_TRAINING — 옵트인 공통(D-02)
    "AI_MODEL_TRAINING": {
        g: _opt_in("AI_MODEL_TRAINING", tag=("OFFICIAL_GUIDANCE" if g in (GROUP_KR, GROUP_EU) else "LEGAL_REQUIREMENT"))
        for g in (GROUP_KR, GROUP_US, GROUP_EU, GROUP_GB, GROUP_BR, GROUP_TH, GROUP_VN, GROUP_OTHER)
    } | {
        GROUP_CN: PurposePolicy("AI_MODEL_TRAINING", "CONSENT", "BLOCKED", None, status_tag="HOLD_D07"),
    },
    # ④ NAMED_RESEARCH — 옵트인 공통(D-02)
    "NAMED_RESEARCH": {
        g: _opt_in("NAMED_RESEARCH", tag=("COUNSEL_CONFIRMATION_REQUIRED" if g == GROUP_KR else "LEGAL_REQUIREMENT"))
        for g in (GROUP_KR, GROUP_US, GROUP_EU, GROUP_GB, GROUP_BR, GROUP_TH, GROUP_VN, GROUP_OTHER)
    } | {
        GROUP_CN: PurposePolicy("NAMED_RESEARCH", "CONSENT", "BLOCKED", None, status_tag="HOLD_D07"),
    },
    # ⑤ TRANSACTION_MATCHING — 옵트인 공통(D-02). VN 미노출, CN HOLD.
    "TRANSACTION_MATCHING": {
        GROUP_KR: _opt_in("TRANSACTION_MATCHING"),
        GROUP_US: _opt_in("TRANSACTION_MATCHING"),
        GROUP_EU: _opt_in("TRANSACTION_MATCHING"),
        GROUP_GB: _opt_in("TRANSACTION_MATCHING"),
        GROUP_BR: _opt_in("TRANSACTION_MATCHING"),
        GROUP_TH: _opt_in("TRANSACTION_MATCHING"),
        GROUP_VN: PurposePolicy("TRANSACTION_MATCHING", "CONSENT", "HIDDEN", None,
                                requires_evidence=True, status_tag="COUNSEL_CONFIRMATION_REQUIRED"),
        GROUP_CN: PurposePolicy("TRANSACTION_MATCHING", "CONSENT", "BLOCKED", None, status_tag="HOLD_D07"),
        GROUP_OTHER: _opt_in("TRANSACTION_MATCHING"),
    },
    # ⑥ EXTERNAL_AI_PROCESSING — 위탁+국외이전. VN/CN 만 별도 동의.
    "EXTERNAL_AI_PROCESSING": {
        GROUP_KR: PurposePolicy("EXTERNAL_AI_PROCESSING", "PROCESSOR_TRANSFER", "NOTICE", "NOTICE_GIVEN"),
        GROUP_US: PurposePolicy("EXTERNAL_AI_PROCESSING", "PROCESSOR_TRANSFER", "NOTICE", "NOTICE_GIVEN"),
        GROUP_EU: PurposePolicy("EXTERNAL_AI_PROCESSING", "PROCESSOR_TRANSFER", "NOTICE", "NOTICE_GIVEN"),
        GROUP_GB: PurposePolicy("EXTERNAL_AI_PROCESSING", "PROCESSOR_TRANSFER", "NOTICE", "NOTICE_GIVEN"),
        GROUP_BR: PurposePolicy("EXTERNAL_AI_PROCESSING", "PROCESSOR_TRANSFER", "NOTICE", "NOTICE_GIVEN"),
        GROUP_TH: PurposePolicy("EXTERNAL_AI_PROCESSING", "PROCESSOR_TRANSFER", "NOTICE", "NOTICE_GIVEN",
                                status_tag="HOLD_D09"),
        GROUP_VN: PurposePolicy("EXTERNAL_AI_PROCESSING", "CONSENT", "TRANSFER_CONSENT", None,
                                requires_evidence=True, status_tag="HOLD_D08", transfer_consent=True),
        GROUP_CN: PurposePolicy("EXTERNAL_AI_PROCESSING", "CONSENT", "BLOCKED", None,
                                status_tag="HOLD_D07", transfer_consent=True),
        GROUP_OTHER: PurposePolicy("EXTERNAL_AI_PROCESSING", "PROCESSOR_TRANSFER", "NOTICE", "NOTICE_GIVEN"),
    },
}

# 가입 화면 노출 순서(TERMS_DISPLAY §4)
SIGNUP_PURPOSE_ORDER = (
    "SERVICE_OPERATION",       # [3] 필수(약관·방침)
    "ANON_AGG_STATS",          # [4] 고지 블록
    "AI_MODEL_TRAINING",       # [5] 옵트인 토글
    "NAMED_RESEARCH",
    "TRANSACTION_MATCHING",
    "EXTERNAL_AI_PROCESSING",  # [6] (해당 시) 국외이전 동의
)

OPT_IN_PURPOSES = ("AI_MODEL_TRAINING", "NAMED_RESEARCH", "TRANSACTION_MATCHING")


def policy_for(purpose_code: str, group: str) -> PurposePolicy:
    per_group = MATRIX[purpose_code]
    return per_group.get(group, per_group[GROUP_OTHER])
