import { apiClient } from "@/lib/api/client";

export interface FeedRecord {
  id: string;
  farm_id: string;
  record_date: string;
  quantity_kg: number;
  feed_type: string | null;
  sow_id: string | null;
  group_id: string | null;
  building_id: string | null;
  unit_cost: number | null;
  currency: string | null;
  notes: string | null;
  created_at: string;
}

export interface CreateFeedRecordRequest {
  record_date: string;
  quantity_kg: number;
  feed_type?: string | null;
  group_id?: string | null;
  building_id?: string | null;
  notes?: string | null;
  // 원가 계열(FEED_COST · 단가 · 원가 변화)은 unit_cost 가 **전 행**에 있을 때만 값이 된다 — 일부만 있으면 서버가 partial 로 유보한다.
  unit_cost?: number | null;   // 통화/kg
  currency?: string | null;    // 생략 시 서버 엔진이 농장 통화로 귀속
}

// ── 읽기 계약 (docs/feed/FEED_READ_API_CONTRACT_DRAFT.md E1/E2) ──────────────
// value == null ⇔ provenance == "INSUFFICIENT" ⇔ reason 존재. null 을 0 으로 그리지 않는다.
export type FeedBasis = "AS_RECORDED" | "DELIVERED";

export interface FeedMetric {
  value: number | null;
  unit: string;
  provenance: "ACTUAL" | "DERIVED" | "INSUFFICIENT";
  reason: string | null;
  evidence: Record<string, unknown>;
  status: { status: string; reason: string | null } | null;
}

export interface FeedSummary {
  farm_id: string;
  // partial = 진행 중인 달(농장 현지 날짜 기준, B-1). partial 이면 CHANGE 계열은 null + reason partial_period — 화면은 비교하지 않는다.
  period: { start: string; end: string; grain: string; partial: boolean; as_of?: string; timezone?: string; comparison?: string | null };
  quantity_basis: FeedBasis;
  currency: string | null;
  formula_version: string;
  metrics: Record<string, FeedMetric>;
  findings: { rule_id: string; kpi: string; severity: string; detail: Record<string, unknown> }[];
  no_data: boolean;
  provenance: { source_systems: string[]; contract_versions: string[]; rows: number };
}

export interface FeedMonth {
  period: string;
  quantity_basis: FeedBasis;
  currency: string | null;
  rows: number;
  feed_qty_kg: number | null;
  feed_cost: number | null;
  feed_cost_reason: string | null;
  partial_cost: number | null;
  unit_price: number | null;
  dominant_type: string | null;
  partial: boolean;
}

const base = (farmId: string) => `/api/v1/farms/${farmId}/feed-records`;
const feedBase = (farmId: string) => `/api/v1/farms/${farmId}/feed`;

export const feedApi = {
  list: (farmId: string) =>
    apiClient.get<FeedRecord[]>(base(farmId)).then((r) => r.data),
  create: (farmId: string, body: CreateFeedRecordRequest) =>
    apiClient.post<FeedRecord>(base(farmId), body).then((r) => r.data),
  delete: (farmId: string, id: string) =>
    apiClient.delete(`${base(farmId)}/${id}`),
  summary: (farmId: string, period: string, basis: FeedBasis) =>
    apiClient.get<FeedSummary>(`${feedBase(farmId)}/summary`, { params: { period, basis } }).then((r) => r.data),
  months: (farmId: string, from: string, to: string, basis: FeedBasis) =>
    apiClient.get<FeedMonth[]>(`${feedBase(farmId)}/months`, { params: { from, to, basis } }).then((r) => r.data),
};
