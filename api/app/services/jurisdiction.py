"""법역 판별기 (TERMS_DISPLAY_SPEC §1.2, §3, §4).

원칙: IP는 참고값. 기준은 ① 가입 시 선택 국가 ② 농장 소재지. 불일치 시 더 엄격한
법역 적용 + counsel 플래그. 미국은 농장 주(state) 코드까지 판별하며, 주 규칙은
계정 단위가 아니라 해당 주 농장 데이터 단위로 적용된다.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

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


# --- 개시 허용 국가 (launch enablement) — H13 (4), 2026-09-10 ---------------
#
# ★ 세 상태를 분리한다. 하나로 합치지 않는다.
#
#     publication eligibility   문서 세트가 완성됐는가        (manifest status)
#     jurisdiction clearance    그 법역을 법무 검토했는가      (research/*_legal)
#     launch enablement         가입을 열기로 결정했는가       (← 이 목록)
#
# 이 목록에 없는 국가는 문서 세트가 완전해도 가입이 열리지 않는다.
# "부속조항이 없어 마스터+방침 두 건이 곧 완전한 세트가 된다"는 렌더러의 성질이
# 개시 결정을 대신하지 못하게 하는 것이 이 목록의 유일한 목적이다.
#
# 추가 절차: 해당 국가의 최소 법무 검토 완료 → 사업 승인 → 여기에 ISO-2 추가.
# 그룹(OTHER 등) 단위로 넣지 않는다 — 국가 단위여야 "고르는 행위"가 기록에 남는다.
_LAUNCH_ALLOWLIST: frozenset[str] = frozenset({"US"})

# 기존 그룹 단위 signup 해제 오버라이드는 그 그룹을 여는 사람의 명시적 판단이므로
# 개시 허용도 함께 의미한다(이중 플래그를 요구하지 않는다).
_SIGNUP_OVERRIDE_KEYS = {GROUP_CN: "CN_signup", GROUP_KR: "KR_signup"}


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

    # --- launch enablement 판정 (H13 (4)) --------------------------------
    # publication eligibility 와 독립. 두 축을 모두 통과해야 가입이 열린다.
    ov = feature_overrides or {}
    launch_ok = (
        country in _LAUNCH_ALLOWLIST
        or bool(ov.get(f"LAUNCH_{country}"))
        or bool(ov.get(_SIGNUP_OVERRIDE_KEYS.get(group, "")))
    )
    if not launch_ok and not gate.signup_blocked:
        gate = replace(gate, signup_blocked=True, reason_code="LAUNCH_NOT_ENABLED")
        notes.append(f"launch not enabled for {country} (H13 allowlist)")

    if gate.signup_blocked:
        notes.append(f"signup blocked: {gate.reason_code}")

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
