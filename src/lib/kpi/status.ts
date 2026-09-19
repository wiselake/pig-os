// KPI 상태 4단계 판정 + 유효범위 검증. (severity enum 고정: normal|warning|critical|insufficient)
// normal=목표달성 / warning=주의 / critical=위험 / insufficient=데이터부족(null·NaN·범위밖)
// good/danger 금지 — normal/critical 사용.

export type KpiTier = "normal" | "warning" | "critical" | "insufficient";

function invalid(v: number | null | undefined, min: number, max: number): boolean {
  return v == null || !Number.isFinite(v) || v < min || v > max;
}

/** PSY 유효 0~45. ≥28 normal / ≥22 warning / 그외 critical. */
export function psyTier(v: number | null | undefined): KpiTier {
  if (invalid(v, 0, 45)) return "insufficient";
  const n = v as number;
  return n >= 28 ? "normal" : n >= 22 ? "warning" : "critical";
}

/** NPD 유효 0~365. ≤35 normal / ≤50 warning / 그외 critical. */
export function npdTier(v: number | null | undefined): KpiTier {
  if (invalid(v, 0, 365)) return "insufficient";
  const n = v as number;
  return n <= 35 ? "normal" : n <= 50 ? "warning" : "critical";
}

/** 분만율 — percent(0~100) 단일 SSOT(2026-06-25, 시드 benchmarks와 동일 스케일). ≥90 normal / ≥80 warning / 그외 critical. */
export function farrowingRateTier(v: number | null | undefined): KpiTier {
  if (invalid(v, 0, 100)) return "insufficient";
  const n = v as number;
  return n >= 90 ? "normal" : n >= 80 ? "warning" : "critical";
}

/** tier → 색상 토큰. 색의미: normal=outline(white카드 내), warning/critical=fill accent, insufficient=brown. */
export const TIER_STYLE: Record<KpiTier, { text: string; dot: string; chip: string }> = {
  normal:       { text: "text-success", dot: "bg-success", chip: "bg-transparent text-success border-success" },
  warning:      { text: "text-warning", dot: "bg-warning", chip: "bg-amber-soft text-warning border-warning/40" },
  critical:     { text: "text-danger",  dot: "bg-danger",  chip: "bg-red-soft text-danger border-danger/40" },
  insufficient: { text: "text-insufficient", dot: "bg-insufficient", chip: "bg-insufficient-soft text-insufficient border-insufficient-border" },
};

/** kpi_code → legacy 판정 함수.
 *
 *  ★ 2026-08-28 — **렌더 경로에서 분리됨.** 이 맵은 더 이상 화면 판정에 쓰이지 않는다.
 *    `statusObservation.resolveTier()` 가 백엔드 status 부재 시 `insufficient` 로
 *    fail-closed 하도록 바뀌었기 때문이다.
 *
 *    남겨 두는 이유는 하나뿐 — `findStatusMismatches()` 의 **관측용 비교 기준**이다.
 *    (백엔드 판정과 구 프론트 판정이 얼마나 다른지를 계측한다)
 *
 *  ★ 아래 임계는 **국가 구분이 없다.** KR 기준이며 서버 US 임계(PSY 26/23)와 다르다.
 *    렌더에 다시 연결하면 미국 농장에 한국 기준이 적용된다 — 절대 금지.
 *    새 임계값을 여기 추가하지 말 것. 판정은 백엔드 국가정책 소관이다. */
export const LEGACY_TIER_FN: Record<string, (v: number | null | undefined) => KpiTier> = {
  PSY: psyTier,
  NPD: npdTier,
  FARROWING_RATE: farrowingRateTier,
};

/** 레지스트리에 legacy 판정이 없는 KPI(SOW_TURNOVER 등)는 프론트가 판정하지 않는다. */
export function legacyTier(kpiCode: string, v: number | null | undefined): KpiTier {
  const fn = LEGACY_TIER_FN[kpiCode];
  return fn ? fn(v) : "normal";
}
