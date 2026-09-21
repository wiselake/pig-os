"""F3 SAFE — 계산 결과 → 기존 KpiStatus 조립 + 임계값 없는 deterministic finding.

판정(좋다/나쁘다)은 여기 없다. 임계값이 필요한 finding(feed.cost_increased 등)은 정책 결재 전이라
등록하지 않는다(SPEC §13, rule_enabled=false 원칙). 여기 있는 것은 수학적으로 명확한 **상태** 뿐:
  feed.cost_incomplete   원가 미입력 행이 있어 사료비를 낼 수 없다        severity INFO (기존 enum)
  fcr.unavailable        그룹/사료는 있는데 FCR 을 낼 수 없다 + 이유         severity INFO
INFO 는 assemble_kpi_status 가 카드 상태로 매핑하지 않는다(evaluation_skipped) — 그래서 여기서는
INSUFFICIENT 결과를 **직접** insufficient+reason 으로 조립하고, 값이 있는 metric 은 정책(rule)이 없으므로
기존 규칙대로 `no_policy` 가 된다. 이것이 "정책 없이 normal 을 주장하지 않는다" 는 기존 불변식이다.
"""
from __future__ import annotations

from app.engine.feed.metrics import FCR, FEED_COST
from app.engine.feed.types import (
    INSUFFICIENT,
    R_ATTRIBUTION_MISSING,
    R_COST_INCOMPLETE,
    R_NO_GAIN,
    R_NO_HEAD_OUT,
    FeedMetricResult,
)
from app.engine.rule_engine import Finding, Severity
from app.schemas.kpi import KpiStatus
from app.services.kpi_status_assembler import assemble_kpi_status

FEED_COST_INCOMPLETE = "feed.cost_incomplete"
FCR_UNAVAILABLE = "fcr.unavailable"
FEED_FINDING_IDS = (FEED_COST_INCOMPLETE, FCR_UNAVAILABLE)


def deterministic_findings(results: dict[str, FeedMetricResult]) -> list[Finding]:
    """임계값 없이 결정되는 finding 만. 값의 좋고 나쁨은 말하지 않는다."""
    out: list[Finding] = []
    cost = results.get(FEED_COST)
    if cost is not None and cost.provenance == INSUFFICIENT and cost.reason == R_COST_INCOMPLETE:
        out.append(Finding(
            rule_id=FEED_COST_INCOMPLETE, kpi=FEED_COST, severity=Severity.INFO,
            current_value=None, target_value=None,
            causes=["feed_cost_missing_unit_cost"],
            recommended_actions=["enter_unit_cost_for_uncosted_rows"],
            detail={k: cost.evidence.get(k) for k in ("uncosted_rows", "costed_rows", "coverage_rows", "coverage_kg", "partial_cost", "currency")},
        ))
    f = results.get(FCR)
    if f is not None and f.provenance == INSUFFICIENT and f.reason in (R_NO_GAIN, R_NO_HEAD_OUT, R_ATTRIBUTION_MISSING):
        # no_cohort / no_data 는 "낼 것이 없다" 이지 "못 냈다" 가 아니다 — finding 이 아니다 (SPEC §13)
        out.append(Finding(
            rule_id=FCR_UNAVAILABLE, kpi=FCR, severity=Severity.INFO,
            current_value=None, target_value=None,
            causes=[f"fcr_{f.reason}"],
            recommended_actions={
                R_NO_GAIN: ["check_entry_exit_weights"],
                R_NO_HEAD_OUT: ["enter_head_count_out_for_closed_groups"],
                R_ATTRIBUTION_MISSING: ["tag_feed_records_with_group_id"],
            }[f.reason],
            detail={"reason": f.reason, "cohort": f.evidence.get("cohort"), "quality": f.evidence.get("quality")},
        ))
    return out


def to_kpi_status(results: dict[str, FeedMetricResult], findings: list[Finding] | None = None,
                  policy_kpis: set[str] | None = None) -> dict[str, KpiStatus]:
    """INSUFFICIENT 는 사유 그대로, 값 있는 metric 은 기존 assembler 로 (정책 없으면 no_policy).

    policy_kpis 는 호출자가 CountryKpiPolicy 에서 가져온 것만 넣는다 — 여기서 만들어내지 않는다.
    """
    pending = {k: r.reason for k, r in results.items() if r.provenance == INSUFFICIENT and r.reason}
    values = {k: (None if r.provenance == INSUFFICIENT else r.value) for k, r in results.items()}
    # INFO finding 은 assembler 에서 evaluation_skipped 로 정규화된다 — 상태 카드에 INFO 를 섞지 않기 위해 제외
    graded = [f for f in (findings or []) if f.severity in (Severity.WARNING, Severity.CRITICAL, Severity.OK)]
    return assemble_kpi_status(values=values, findings=graded, policy_kpis=policy_kpis or set(), pending=pending)

