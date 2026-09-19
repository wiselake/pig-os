// ADR-KPI-08 Phase 2 — dual observation.
// 백엔드 canonical status와 현행 프론트 tier 판정이 얼마나 다른지 "관측만" 한다.
// 사용자 화면 판정은 바꾸지 않는다(전환은 Phase 3).
//
// 왜 하는가: 백엔드가 warning인데 화면이 normal이던 케이스가 곧 놓친 경보이며,
// 이는 재고 분모 결함(D-2)의 간접 증거가 된다.
import { track } from "@/lib/analytics";
import type { KpiStatusDto } from "@/types/api.types";
import type { KpiTier } from "./status";

/** 백엔드 status ↔ 프론트 tier 비교용 정규화. 판정하지 않고 이름만 맞춘다. */
function normalize(v: string): string {
  return v.toLowerCase();
}

export interface StatusMismatch {
  metric: string;
  backend: string;
  backendReason: string | null;
  frontend: KpiTier;
}

/**
 * 불일치 목록을 계산한다(순수 함수 — 로깅은 report* 에서).
 * backend가 insufficient인 경우도 불일치로 본다(프론트가 임의 판정 중이라는 뜻).
 */
export function findStatusMismatches(
  backend: Record<string, KpiStatusDto> | undefined,
  frontend: Record<string, KpiTier>,
): StatusMismatch[] {
  if (!backend) return [];
  const out: StatusMismatch[] = [];
  for (const [metric, fe] of Object.entries(frontend)) {
    const be = backend[metric];
    if (!be) continue;                       // 백엔드가 안 준 지표는 비교 대상 아님
    if (normalize(be.status) !== normalize(fe)) {
      out.push({ metric, backend: be.status, backendReason: be.reason, frontend: fe });
    }
  }
  return out;
}

/**
 * ADR-KPI-08 Phase 4 — 렌더용 tier 결정. **판정은 전적으로 백엔드 소관이다.**
 *
 * ★ 2026-08-28 변경: 백엔드 status가 없을 때 legacy 임계로 폴백하던 것을 제거했다.
 *
 *   폴백 임계(`status.ts` psyTier>=28 / npdTier<=35 / farrowingRateTier>=90)는
 *   **국가 구분이 없다.** KR 기준값인데 서버 DMV는 US PSY 임계를 26/23으로 둔다.
 *   폴백이 발동하는 순간 미국 농장에 한국 기준이 적용된다
 *   (`CROSS_COUNTRY_DECISION_RISK`, D-19 v1.4 N-7 / PLATFORM_PARITY §3-3).
 *
 *   backend status 부재 = "판정을 받지 못했다"이지 "정상"도 "위험"도 아니다.
 *   canonical no-judgment 상태인 `insufficient`로 렌더한다.
 *   신규 enum(neutral/unknown/no_alert)을 만들지 않는다 — 서버 계약에 이미 있다.
 *
 * `legacy` 인자는 시그니처 호환을 위해 남아 있으나 **렌더 판정에 쓰이지 않는다.**
 * 관측(`findStatusMismatches`)에는 계속 쓰인다.
 */
const _CANONICAL: readonly KpiTier[] = ["normal", "warning", "critical", "insufficient"];

export function resolveTier(
  backend: Record<string, KpiStatusDto> | undefined,
  metric: string,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _legacy?: KpiTier,
): KpiTier {
  const be = backend?.[metric];
  if (!be) return "insufficient";                           // fail-closed. 자체 판정 금지
  const s = normalize(be.status) as KpiTier;
  return _CANONICAL.includes(s) ? s : "insufficient";       // unknown → 중립, 재판정 금지
}

/** 불일치를 텔레메트리로 보낸다(있을 때만). 화면 동작에는 영향 없음. */
export function reportStatusMismatches(
  backend: Record<string, KpiStatusDto> | undefined,
  frontend: Record<string, KpiTier>,
): StatusMismatch[] {
  const mismatches = findStatusMismatches(backend, frontend);
  for (const m of mismatches) {
    track("kpi_status_mismatch", {
      metric: m.metric,
      backend_status: m.backend,
      backend_reason: m.backendReason,
      frontend_tier: m.frontend,
    });
  }
  return mismatches;
}
