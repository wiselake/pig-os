"""법역 판별기 (TERMS_DISPLAY_SPEC §1.2, §3, §4).

원칙: IP는 참고값. 기준은 ① 가입 시 선택 국가 ② 농장 소재지. 불일치 시 더 엄격한
법역 적용 + counsel 플래그. 미국은 농장 주(state) 코드까지 판별하며, 주 규칙은
계정 단위가 아니라 해당 주 농장 데이터 단위로 적용된다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.policy.consent_matrix import (
    GROUP_CN,
    GROUP_KR,
    GROUP_US,
    group_for_country,
)

# --- US 주별 분기 (§3) ------------------------------------------------------

# UOOM(Universal Opt-Out Mechanism, GPC 등) 신호 존중 주 — 목적⑤·타겟광고 자동 OFF
UOOM_STATES = frozenset({"CO", "CT", "CA", "TX", "MT", "OR", "DE", "NE", "NJ", "MN"})
# Do-Not-Sell 링크 상시 노출 + GPC 존중
DNS_LINK_STATES = frozenset({"CA"})
# 농업데이터 판매 서면(전자) 옵트인 — LB525
WRITTEN_OPT_IN_STATES = frozenset({"NE"})
# 정밀 위치(농장 GPS) 민감정보 판매 금지 — MODPA
LOCATION_SALE_BAN_STATES = frozenset({"MD"})


@dataclass(frozen=True)
class StateFlags:
    state: str | None = None
    written_opt_in_required: bool = False   # NE: ②④ 서면 옵트인
    do_not_sell_link: bool = False          # CA: DNS 링크 + GPC
    honor_uoom: bool = False                # UOOM: ⑤·타겟광고 자동 OFF
    exclude_location_from_sale: bool = False  # MD: ⑤ 위치 필드 제외


def _state_flags(state: str | None) -> StateFlags:
    s = (state or "").upper() or None
    if s is None:
        return StateFlags()
    return StateFlags(
        state=s,
        written_opt_in_required=s in WRITTEN_OPT_IN_STATES,
        do_not_sell_link=s in DNS_LINK_STATES,
        honor_uoom=s in UOOM_STATES,
        exclude_location_from_sale=s in LOCATION_SALE_BAN_STATES,
    )


# --- 게이트 (§2 차단·게이트 열, D-07/08/09) ---------------------------------

@dataclass(frozen=True)
class Gate:
    signup_blocked: bool = False   # CN (D-07)
    paid_blocked: bool = False     # TH(D-09)/VN(D-08): 유료·본격 마케팅 차단
    release_hold: bool = False     # EU/GB/BR: 대리인·SCC 등 출시 보류 [OPEN]
    reason_code: str | None = None


# 기능 플래그로 해제 가능(§7). 기본은 스펙대로 잠금.
_GATES: dict[str, Gate] = {
    "CN": Gate(signup_blocked=True, reason_code="HOLD_D07"),
    # KR: 레퍼런스 전용(공개 마케팅 타겟 아님) → 실고객 가입 차단. 대표 확인용은 allow_kr_signup(env)로 해제.
    "KR": Gate(signup_blocked=True, reason_code="KR_REFERENCE_ONLY"),
    "TH": Gate(paid_blocked=True, reason_code="GATE_D09"),
    "VN": Gate(paid_blocked=True, reason_code="GATE_D08"),
    "EU": Gate(release_hold=True, reason_code="OPEN_EU_REP"),
    "GB": Gate(release_hold=True, reason_code="OPEN_UK_REP"),
    "BR": Gate(release_hold=True, reason_code="OPEN_BR_SCC"),
}


@dataclass(frozen=True)
class Jurisdiction:
    """판별 결과. consent_ledger.jurisdiction 에는 `code`(ISO-2 또는 US-NE)를 기록."""
    code: str                       # 'KR', 'US-NE', 'DE' ...
    country: str                    # ISO alpha-2
    group: str                      # 정책 그룹(consent_matrix)
    state_flags: StateFlags
    gate: Gate
    counsel_review: bool = False    # 선택국≠농장국 등 보수 적용 케이스
    doc_addendum: str | None = None  # 표시할 부속조항 id (렌더러용)
    notes: list[str] = field(default_factory=list)


# 그룹 → 부속조항 문서 id (TERMS_DISPLAY §2). None = 부속 없음(마스터+방침만)
_ADDENDUM = {
    "US": "ADDENDUM_US", "EU": "ADDENDUM_EU", "GB": "ADDENDUM_GB",
    "BR": "ADDENDUM_BR", "TH": "ADDENDUM_TH", "VN": "ADDENDUM_VN",
    "KR": None, "CN": None, "OTHER": None,
}

# 엄격도 순위(불일치 시 더 엄격한 쪽 채택 — 대략적 보수 순위)
_STRICTNESS = {"CN": 9, "VN": 8, "TH": 7, "EU": 6, "GB": 6, "BR": 5, "KR": 4, "US": 3, "OTHER": 2}


def resolve(
    *,
    selected_country: str,
    farm_country: str | None = None,
    farm_state: str | None = None,
    feature_overrides: dict[str, bool] | None = None,
) -> Jurisdiction:
    """법역 판별. feature_overrides 로 게이트 해제 가능(예: {'TH_paid': True})."""
    sel = (selected_country or "").upper()
    farm = (farm_country or sel).upper()
    notes: list[str] = []
    counsel = False

    # 선택국 vs 농장국 불일치 → 더 엄격한 쪽 + counsel
    country = sel
    if farm and farm != sel:
        counsel = True
        notes.append(f"country_mismatch: selected={sel} farm={farm} → conservative")
        if _STRICTNESS.get(group_for_country(farm), 0) >= _STRICTNESS.get(group_for_country(sel), 0):
            country = farm

    group = group_for_country(country)
    state_flags = _state_flags(farm_state) if group == GROUP_US else StateFlags()

    code = country
    if group == GROUP_US and state_flags.state:
        code = f"US-{state_flags.state}"

    gate = _GATES.get(group, Gate())
    if feature_overrides:
        # 예: feature_overrides={'CN_signup': True} 로 특정 게이트 해제
        if group == GROUP_CN and feature_overrides.get("CN_signup"):
            gate = Gate(reason_code="OVERRIDE_CN")
        if group == GROUP_KR and feature_overrides.get("KR_signup"):
            gate = Gate(reason_code="OVERRIDE_KR")  # 대표 확인용(allow_kr_signup env)
        if group in ("TH", "VN") and feature_overrides.get(f"{group}_paid"):
            gate = Gate(release_hold=gate.release_hold, reason_code=f"OVERRIDE_{group}")
        if group in ("EU", "GB", "BR") and feature_overrides.get(f"{group}_release"):
            gate = Gate(reason_code=f"OVERRIDE_{group}")

    if gate.signup_blocked:
        # 사유는 게이트가 들고 있다. 예전엔 CN 문구를 그대로 붙여 KR 에도 "CN, D-07 HOLD" 가 찍혔다.
        notes.append(f"signup blocked ({country}, {gate.reason_code})")

    return Jurisdiction(
        code=code,
        country=country,
        group=group,
        state_flags=state_flags,
        gate=gate,
        counsel_review=counsel,
        doc_addendum=_ADDENDUM.get(group),
        notes=notes,
    )


# --- 가입 게이트 공용 진입점 -------------------------------------------------
# 계정을 만드는 경로는 **전부** 여기를 통과해야 한다. 예전엔 게이트가 /consent/record
# 한 곳에만 걸려 있어서, 차단 법역에서도 계정은 생성되고 동의만 451 로 실패했다
# (= 동의 없는 계정이 남는다). 클라이언트 UI 를 유일한 방어선으로 두면 안 된다.

def signup_overrides(extra: dict[str, bool] | None = None) -> dict[str, bool]:
    """운영 기본 해제 스위치(env). 서버 값이라 클라이언트가 우회할 수 없다."""
    from app.core.config import settings  # 지연 import — 설정 로딩 순서 의존 회피
    return {"KR_signup": settings.allow_kr_signup, **(extra or {})}


def resolve_for_signup(
    *,
    selected_country: str,
    farm_country: str | None = None,
    farm_state: str | None = None,
    feature_overrides: dict[str, bool] | None = None,
) -> Jurisdiction:
    """가입 맥락의 법역 판별 — env 해제 스위치를 적용한 뒤 resolve 한다."""
    return resolve(
        selected_country=selected_country,
        farm_country=farm_country,
        farm_state=farm_state,
        feature_overrides=signup_overrides(feature_overrides),
    )


def assert_signup_allowed(
    *,
    selected_country: str,
    farm_country: str | None = None,
    farm_state: str | None = None,
) -> None:
    """차단 법역이면 451(Unavailable For Legal Reasons). 사유코드를 그대로 실어 보낸다."""
    from fastapi import HTTPException  # 지연 import — 이 모듈은 순수 정책 계층

    j = resolve_for_signup(
        selected_country=selected_country,
        farm_country=farm_country,
        farm_state=farm_state,
    )
    if j.gate.signup_blocked:
        raise HTTPException(451, f"SIGNUP_BLOCKED:{j.gate.reason_code}")
