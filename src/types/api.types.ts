// Auto-generated from PigOS OpenAPI v1 spec
// Reflects: docs/api/openapi-v1.yaml

// ─── Common ──────────────────────────────────────────────────────────────────

export interface ApiError {
  code: string;
  message: string;
  detail?: Record<string, unknown>;
}

export interface PageMeta {
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface PagedResult<T> {
  items: T[];
  meta: PageMeta;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface LoginRequest {
  username: string;
  password: string;
}

export type FarmRole = "FARM_OWNER" | "FARM_MANAGER" | "FARM_WORKER" | "VET" | "VIEWER";
export type OrgRole = "SUPER_ADMIN" | "VENDOR_ADMIN" | "DISTRIBUTOR_ADMIN" | "DEALER_ADMIN";
export type LegacyFarmRole = "OWNER" | "MANAGER" | "WORKER";
export type UserRole = FarmRole | OrgRole | LegacyFarmRole | "API_CLIENT";

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  name: string;
  username: string;
  email: string;
  role: UserRole;
  system_role?: UserRole;  // 플랫폼 권한 기준(백엔드 effective_system_role) — 관리자 UI 게이팅
  farm_ids: string[];
  farm_roles?: Record<string, UserRole>;  // farm_id → 농장별 role (멀티팜 게이팅)
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  phone?: string | null;
  name: string;
  role: UserRole;
  system_role?: UserRole;  // 플랫폼 권한 기준 — 관리자 UI 게이팅
  farm_ids: string[];
  farm_roles?: Record<string, UserRole>;  // farm_id → 농장별 role (멀티팜 게이팅)
}

export interface MeResponse {
  id: string;
  name: string;
  username: string;
  email: string | null;
  phone?: string | null;
  role: UserRole;
  system_role?: UserRole;  // 플랫폼 권한 기준 — 관리자 UI 게이팅
  org_id: string | null;
  language: string;
  farm_ids: string[];
  farm_roles?: Record<string, UserRole>;
}

// ─── Onboarding ───────────────────────────────────────────────────────────────

export interface OnboardingRequest {
  org_name: string;
  country: string;
  name: string;
  username: string;
  email: string;
  password: string;
  farm_name: string;
  farm_type?: "SOW_FARM" | "FARROW_TO_FINISH" | "NURSERY" | "FINISHER" | "BOAR_STUD";
  sow_count?: number;
  timezone?: string;
  language?: string;  // 온보딩 로케일 보존(M3)
  currency?: string;      // 국가서 프리필(서버가 미전송 시 파생)
  unit_system?: "METRIC" | "IMPERIAL";
}

// 공개 국가 설정 (GET /api/v1/config/countries) — 단일 소스 백엔드 country_config.
export interface CountryConfig {
  code: string;
  name: string;
  timezone: string;
  currency: string;
  unit_system: "METRIC" | "IMPERIAL";
  dial: string;
  language: string;
}

export interface OnboardingResponse {
  org_id: string;
  farm_id: string;
  user_id: string;
  access_token: string;
  refresh_token: string;
}

// ─── Farms ────────────────────────────────────────────────────────────────────

export interface FarmLocalConfig {
  weight_unit: "kg" | "lb";
  currency_code: string;
  currency_symbol: string;
  min_wean_period: number | null;
  requires_traceability: boolean;
  requires_antibiotic_tracking: boolean;
  slaughter_weight_target_kg: number | null;
  market_code: string | null;
}

export interface EventDefinition {
  event_code: string;
  category: string;
  label_en: string;
  label_ko: string | null;
  label_vi: string | null;
  required_fields: Record<string, string> | null;
  regional_applicability: string;
}

export interface Farm {
  id: string;
  name: string;
  country: string;
  farm_type: string;
  sow_count: number;
  timezone: string;
  currency: string;
  created_at: string;
}

// ─── Sows ─────────────────────────────────────────────────────────────────────

// docs/SCREEN_MENU_SPEC.md "Sow Status Definitions" 기준
export type SowStatus =
  | "GILT"      // 후보돈 — 입식, 미교배
  | "OPEN"      // 공태 — 이유 후 교배 대기
  | "PREGNANT"  // 임신
  | "LACTATING" // 포유
  | "ACCIDENT"  // 번식사고 — 재발/공태판정/유산, 재교배 대기
  | "CULLED"
  | "DEAD"
  | "SOLD"
  | "TRANSFER";

export interface Sow {
  id: string;
  farm_id: string;
  ear_tag: string;
  rfid_tag: string | null;
  status: SowStatus;
  parity: number;
  breed: string | null;
  breed_company: string | null;
  genetics_id: string | null;
  entry_date: string;
  entry_type: SowEntryType;
  building_id: string | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export type SowEntryType = "GILT" | "PURCHASE" | "TRANSFER" | "BORN";

export interface CreateSowRequest {
  ear_tag: string;
  entry_date: string;
  entry_type: SowEntryType;
  parity?: number;
  breed?: string;
  rfid_tag?: string;
  notes?: string;
}

export interface UpdateSowRequest {
  ear_tag?: string;
  breed?: string;
  breed_company?: string;
  genetics_id?: string;
  rfid_tag?: string;
  building_id?: string;
  parity?: number;
  entry_date?: string;   // YYYY-MM-DD
  entry_type?: "GILT" | "PURCHASE" | "TRANSFER" | "BORN";
  // 활성 상태만 (종료는 cull 모달). SowStatus 중 활성 부분집합
  status?: "GILT" | "OPEN" | "PREGNANT" | "LACTATING" | "ACCIDENT";
}

// ─── Events ───────────────────────────────────────────────────────────────────

// ── Threshold 관리 (#4) ──────────────────────────────────────────────────────
export interface ThresholdRow {
  metric_code: string;
  warning: number | null;
  critical: number | null;
  avg: number | null;
  top25: number | null;
  target: number | null;
  direction: "above" | "below";
  unit: string;
  confidence: "high" | "medium" | "low" | null;
  is_proxy: boolean;
  source: string | null;
  scope: "farm" | "country" | "global";
  is_override: boolean;
}

export interface ThresholdOverrideRequest {
  warning?: number | null;
  critical?: number | null;
}

// ── Event Insight (입력 즉시 분석 — 백엔드 판정, 프론트는 렌더만) ────────────
export interface EventInsight {
  metric_code: string;
  severity: "INFO" | "WARNING" | "CRITICAL";
  judgment_type: "absolute" | "relative";
  normalized_gap: number | null;
  priority: number;
  value: number | null;
  threshold: number | null;
  unit: string;
  direction: "above" | "below";
  confidence: "high" | "medium" | "low" | null;
  is_proxy: boolean;
  source: string | null;
  is_global_fallback: boolean;
  loss: Record<string, unknown> | null;      // 슬롯: 경제손실 (있을 때만)
  relative: Record<string, unknown> | null;   // 슬롯: 상대판정 (있을 때만)
}

export interface Mating {
  id: string;
  sow_id: string;
  mating_date: string;
  mating_type: "AI" | "NATURAL";
  mating_number: number;
  boar_id?: string;
  semen_batch?: string;
  notes?: string;
  farm_id: string;
  created_at: string;
  insights?: EventInsight[];
}

export interface CreateMatingRequest {
  sow_id: string;
  mating_date: string;
  mating_type: "AI" | "NATURAL";
  mating_number?: number;
  boar_id?: string;
  semen_batch?: string;
  notes?: string;
}

export interface Farrowing {
  id: string;
  farm_id: string;
  sow_id: string;
  mating_id: string | null;
  farrowing_date: string;
  total_born: number;
  born_alive: number;
  stillborn: number;
  mummified: number;
  farrowing_ease: "EASY" | "ASSISTED" | "DIFFICULT" | null;
  breeding_cycle_id: string | null;
  created_at: string;
  insights?: EventInsight[];
}

export interface CreateFarrowingRequest {
  sow_id: string;
  mating_id?: string;
  farrowing_date: string;
  born_alive: number;
  stillborn?: number;
  mummified?: number;
  avg_birth_weight_kg?: number;
  farrowing_ease?: "EASY" | "ASSISTED" | "DIFFICULT";
  notes?: string;
}

export interface Weaning {
  id: string;
  farm_id: string;
  sow_id: string;
  farrowing_id: string | null;
  weaning_date: string;
  weaned_count: number;
  weaning_age_days: number | null;
  avg_weaning_weight_kg: number | null;
  created_at: string;
  insights?: EventInsight[];
}

export interface CreateWeaningRequest {
  sow_id: string;
  farrowing_id?: string;
  weaning_date: string;
  weaned_count: number;
  avg_weaning_weight_kg?: number;
  is_partial?: boolean;
  notes?: string;
}

export interface ReproductiveEvent {
  id: string;
  sow_id: string;
  event_type: "RETURN_TO_ESTRUS" | "ABORTION" | "EMPTY" | "INFERTILE" | "CULLED" | "DEAD" | "TRANSFER_OUT" | "SOLD" | "HEAT_DETECTED";
  event_date: string;
  mating_id?: string;
  detected_method?: "ULTRASOUND" | "VISUAL" | "BEHAVIOR" | "BLOOD_TEST";
  notes?: string;
  farm_id: string;
  created_at: string;
}

export interface CreateReproductiveEventRequest {
  sow_id: string;
  event_type: "RETURN_TO_ESTRUS" | "ABORTION" | "EMPTY" | "INFERTILE" | "CULLED" | "DEAD" | "TRANSFER_OUT" | "SOLD" | "HEAT_DETECTED";
  event_date: string;
  mating_id?: string;
  detected_method?: "ULTRASOUND" | "VISUAL" | "BEHAVIOR" | "BLOOD_TEST";
  notes?: string;
}

export interface CreatePregnancyCheckRequest {
  sow_id: string;
  check_date: string;
  result: "POSITIVE" | "NEGATIVE" | "UNCERTAIN";
  mating_id?: string;
  days_after_mating?: number;
  method?: "ULTRASOUND" | "DOPPLER" | "VISUAL" | "BLOOD" | "OTHER";
  notes?: string;
}

export interface PregnancyCheck {
  id: string;
  farm_id: string;
  sow_id: string;
  mating_id?: string | null;
  check_date: string;
  days_after_mating?: number | null;
  result: string;
  method?: string | null;
  created_at: string;
  insights?: EventInsight[];
}

export interface SowCullRequest {
  removal_type: "CULLED" | "DEAD" | "SOLD" | "TRANSFER";
  removal_date: string;
  reason_category?: "REPRODUCTIVE" | "LAMENESS" | "DISEASE" | "AGE" | "PERFORMANCE" | "INJURY" | "BEHAVIOR" | "UNKNOWN" | "OTHER";
  reason_detail?: string;
  body_weight_kg?: number;
  sale_price?: number;
  sale_currency?: string;
  notes?: string;
}

export interface RemovalRecord {
  id: string;
  farm_id: string;
  sow_id: string;
  removal_date: string;
  removal_type: string;
  reason_category?: string;
  reason_detail?: string;
  body_weight_kg?: number;
  sale_price?: number;
  sale_currency?: string;
  created_at: string;
}

export interface CreatePigletEventRequest {
  sow_id: string;
  farrowing_id?: string;
  event_date: string;
  event_type: "STILLBORN_REMOVAL" | "DEATH" | "FOSTER_IN" | "FOSTER_OUT";
  piglet_count: number;
  reason?: "CRUSHING" | "SCOURS" | "STARVATION" | "CONGENITAL" | "HYPOTHERMIA" | "OTHER";
  target_sow_id?: string;
  notes?: string;
}

export interface PigletEventRecord {
  id: string;
  farm_id: string;
  farrowing_id: string;
  sow_id: string;
  event_date: string;
  event_type: string;
  piglet_count: number;
  reason?: string;
  created_at: string;
}

// ── Piglet Groups (자돈) ──────────────────────────────────────────────────────

export interface PigletGroup {
  id: string;
  farm_id: string;
  group_code: string;
  batch_name?: string;
  weaning_date: string;
  transfer_date?: string;
  transfer_type?: "FINISHER_TRANSFER" | "SOLD" | "CULLED";
  head_count_in: number;
  head_count_dead: number;
  head_count_out?: number;
  avg_entry_weight_kg?: number;
  avg_exit_weight_kg?: number;
  building_id?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface CreatePigletGroupRequest {
  group_code: string;
  batch_name?: string;
  weaning_date: string;
  head_count_in: number;
  avg_entry_weight_kg?: number;
  building_id?: string;
  notes?: string;
}

export interface PigletGroupTransferOutRequest {
  transfer_date: string;
  transfer_type: "FINISHER_TRANSFER" | "SOLD" | "CULLED";
  head_count_out: number;
  avg_exit_weight_kg?: number;
  notes?: string;
}

export interface PigletTransfer {
  id: string;
  farm_id: string;
  source_sow_id: string;
  dest_sow_id: string;
  transfer_date: string;
  piglet_count: number;
  source_farrowing_id?: string;
  dest_farrowing_id?: string;
  reason?: string;
  created_at: string;
}

export interface CreatePigletTransferRequest {
  source_sow_id: string;
  dest_sow_id: string;
  transfer_date: string;
  piglet_count: number;
  source_farrowing_id?: string;
  dest_farrowing_id?: string;
  reason?: string;
  notes?: string;
}

// ── Finisher Groups (비육돈) ──────────────────────────────────────────────────

export interface FinisherGroup {
  id: string;
  farm_id: string;
  group_code: string;
  batch_name?: string;
  start_date: string;
  end_date?: string;
  head_count_in: number;
  head_count_out?: number;
  avg_entry_weight_kg?: number;
  avg_exit_weight_kg?: number;
  building_id?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateFinisherGroupRequest {
  group_code: string;
  batch_name?: string;
  start_date: string;
  head_count_in: number;
  avg_entry_weight_kg?: number;
  building_id?: string;
  notes?: string;
}

export interface FinisherGroupShipRequest {
  end_date: string;
  head_count_out: number;
  avg_exit_weight_kg?: number;
  notes?: string;
}

export interface HealthEvent {
  id: string;
  sow_id?: string;
  event_date: string;
  disease_code?: string;
  vaccine_code?: string;
  active_substance?: string;
  dose_mg?: number;
  severity?: "MILD" | "MODERATE" | "SEVERE" | "CRITICAL";
  notes?: string;
  farm_id: string;
  created_at: string;
}

// ─── KPI ──────────────────────────────────────────────────────────────────────

export interface Alert {
  rule_id: string;
  kpi: string;
  severity: "OK" | "INFO" | "WARNING" | "CRITICAL";
  message: string;
  current_value?: number;
  target_value?: number;
}

export interface KpiDashboard {
  farm_id: string;
  as_of: string;
  psy: number | null;
  npd: number | null;                 // 비생산일수(여집합, 모돈-년) — PigPlan 정합
  sow_turnover?: number | null;       // 모돈회전율 = 분만복수 / 평균 상시모돈(경산)
  farrowing_rate: number | null;  // percent(0~100) 단일 SSOT — 시드 benchmarks·trend와 동일 스케일. ×100 금지.
  active_sows: number;
  gestating: number;
  lactating: number;
  weaned: number;
  week_matings: number;
  week_farrowings: number;
  week_weanings: number;
  country: string | null;
  benchmarks: Record<string, KpiBenchmark>;  // "PSY" | "NPD" | "FARROWING_RATE"
  /** ADR-KPI-08 — 백엔드(국가별 Rule Engine)가 판정한 KPI 상태. 키=metric_code.
   *  프론트는 렌더만 하고 자체 판정 금지. Phase 2에서는 관측만, Phase 3에서 렌더 전환. */
  kpi_status?: Record<string, KpiStatusDto>;
  alerts: Alert[];
  estimated_loss?: {
    amount: number; currency: string; lost_pigs: number; basis: string; demo: boolean;
  } | null;
}

/** GET /kpi/presentation — 국가별 표현 정책(country_kpi_presentation).
 *  ★ items 는 서버가 정렬을 끝낸 상태로 내려온다. HIDDEN 도 서버가 이미 제외했다.
 *  프론트는 재정렬·재필터·headline 탐색을 하지 않는다. */
export interface KpiPresentationItem {
  kpi_code: string;
  display_order: number | null;
  /** 현지 용어(i18n 번역 아님). null이면 공용 라벨 사용 */
  local_label: string | null;
  priority_class: string | null;
  display_role: string | null;
}

export interface KpiPresentation {
  country: string | null;
  /** priority_class='NORTH_STAR' — 프론트가 찾지 않고 이 필드를 그대로 쓴다 */
  headline_kpi: string | null;
  items: KpiPresentationItem[];
}

export interface KpiBenchmark {
  avg: number | null;
  top25: number | null;
  target: number | null;
}

/** ADR-KPI-08 canonical status. reason은 항상 존재(없으면 null) — 유무로 분기 금지. */
export interface KpiStatusDto {
  status: "normal" | "warning" | "critical" | "insufficient" | (string & {});
  reason: string | null;
}

export interface KpiTrend {
  period: string;
  psy: number | null;
  npd: number | null;
  farrowing_rate: number | null;  // percent(0~100) — KpiDashboard와 동일 스케일.
}

// ─── Q&A / Chat ───────────────────────────────────────────────────────────────

export interface ChatQuery {
  question: string;
  locale?: "en" | "ko" | "zh" | "es" | "vi" | "th" | "pt" | "ru";
}

export interface FindingOut {
  rule_id: string;
  kpi: string;
  severity: "OK" | "INFO" | "WARNING" | "CRITICAL";
  current_value: number | null;
  target_value: number | null;
  causes: string[];
  recommended_actions: string[];
}

export interface ChatResponse {
  intent: string;
  severity: "OK" | "INFO" | "WARNING" | "CRITICAL";
  answer: string;
  findings: FindingOut[];
  farm_id: string;
  as_of: string;
  renderer: "template" | "llm";
}

// ─── Offline Sync ─────────────────────────────────────────────────────────────

export interface SyncMating {
  id: string;
  sow_id: string;
  mating_date: string;
  mating_type: "AI" | "NATURAL";
  boar_id?: string;
  semen_batch?: string;
  mating_number?: number;
  notes?: string;
  client_created_at: string;
}

export interface SyncFarrowing {
  id: string;
  sow_id: string;
  farrowing_date: string;
  total_born: number;
  born_alive: number;
  born_dead?: number;
  mummies?: number;
  farrowing_type?: string;
  notes?: string;
  client_created_at: string;
}

export interface SyncWeaning {
  id: string;
  sow_id: string;
  weaning_date: string;
  weaned_count: number;
  avg_weight_kg?: number;
  notes?: string;
  client_created_at: string;
}

export interface SyncReproductiveEvent {
  id: string;
  sow_id: string;
  event_type: string;
  event_date: string;
  notes?: string;
  client_created_at: string;
}

export interface SyncHealthEvent {
  id: string;
  sow_id?: string;
  event_date: string;
  disease_code?: string;
  vaccine_code?: string;
  active_substance?: string;
  dose_mg?: number;
  severity?: string;
  notes?: string;
  client_created_at: string;
}

export interface SyncPigletEvent {
  id: string;
  sow_id: string;
  farrowing_id?: string;
  event_date: string;
  event_type: "STILLBORN_REMOVAL" | "DEATH" | "FOSTER_IN" | "FOSTER_OUT";
  piglet_count: number;
  reason?: "CRUSHING" | "SCOURS" | "STARVATION" | "CONGENITAL" | "HYPOTHERMIA" | "OTHER";
  target_sow_id?: string;
  notes?: string;
  client_created_at: string;
}

export interface SyncChanges {
  matings?: SyncMating[];
  farrowings?: SyncFarrowing[];
  weanings?: SyncWeaning[];
  reproductive_events?: SyncReproductiveEvent[];
  health_events?: SyncHealthEvent[];
  piglet_events?: SyncPigletEvent[];
}

export interface SyncRequest {
  farm_id: string;
  client_id: string;
  last_sync_at: string | null;
  changes: SyncChanges;
  dry_run?: boolean;
}

export interface SyncAccepted {
  id: string;
  entity: string;
  action: "created" | "merged";
}

export interface SyncRejected {
  id: string;
  entity: string;
  reason: string;
  detail: Record<string, unknown>;
}

export interface SyncConflict {
  id: string;
  entity: string;
  conflict_type: string;
  client_record: Record<string, unknown>;
  server_record: Record<string, unknown>;
}

export interface ServerChanges {
  sows: Record<string, unknown>[];
  matings: Record<string, unknown>[];
  farrowings: Record<string, unknown>[];
  weanings: Record<string, unknown>[];
  reproductive_events: Record<string, unknown>[];
  health_events: Record<string, unknown>[];
  piglet_events: Record<string, unknown>[];
  removals: Record<string, unknown>[];
  period_locks: Record<string, unknown>[];
  deleted_ids: string[];
}

export interface SyncResponse {
  sync_token: string;
  dry_run: boolean;
  accepted: SyncAccepted[];
  rejected: SyncRejected[];
  conflicts: SyncConflict[];
  server_changes: ServerChanges;
  require_full_sync: boolean;
  stats: Record<string, number>;
}

// ── Alerts / Tasks (Phase 2 backend) ──────────────────────────────────────────

export type OverdueType =
  | "gilt_no_estrus"
  | "gilt_overdue_mating"
  | "pregnant_overdue_farrowing"
  | "lactating_overdue_weaning"
  | "open_overdue_mating"
  | "accident_overdue_mating";

export interface OverdueSow {
  type: OverdueType;
  sow_id: string;
  ear_tag: string;
  status: SowStatus;
  parity: number;
  overdue_days: number;
}

export interface OverdueSummary {
  total: number;
  counts: Record<string, number>;
  items: OverdueSow[];
}

export interface CullCandidate {
  sow_id: string;
  ear_tag: string;
  status: SowStatus;
  parity: number;
  reasons: string[];
  last_weaned: number | null;
}

// ── Tasks (자동배정 작업 / 오늘 할 일) ─────────────────────────────────────
export type TaskType = OverdueType | "cull_candidate";
export type TaskStatus = "OPEN" | "DONE" | "DISMISSED";

export interface Task {
  id: string;
  farm_id: string;
  sow_id: string | null;
  ear_tag: string | null;
  task_type: TaskType;
  title: string;
  action: string | null;
  status: TaskStatus;
  priority: number;        // 1=high, 2=normal, 3=low
  overdue_days: number | null;
  due_date: string | null;
  assigned_to: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface TaskGenerateResult {
  created: number;
  closed: number;
  open_total: number;
}

export interface TaskUpdateRequest {
  status?: TaskStatus;
  assigned_to?: string | null;
}

export interface FarmReproConfig {
  gestation_days: number;
  lactation_days: number;
  wei_target_days: number;
  gilt_first_mating_age: number;
  slaughter_age: number;
}

// ── Event / group update bodies (Phase 12 CRUD) ───────────────────────────────

export interface UpdateMatingRequest {
  mating_date?: string;
  boar_id?: string | null;
  notes?: string | null;
}

export interface UpdateFarrowingRequest {
  farrowing_date?: string;
  born_alive?: number;
  stillborn?: number;
  mummified?: number;
  notes?: string | null;
}

export interface UpdateWeaningRequest {
  weaning_date?: string;
  weaned_count?: number;
  avg_weaning_weight_kg?: number | null;
  notes?: string | null;
}

export interface UpdateFinisherGroupRequest {
  batch_name?: string | null;
  head_count_in?: number;
  avg_entry_weight_kg?: number | null;
  notes?: string | null;
}

// ── Reports (Phase 7 backend) ─────────────────────────────────────────────────

export interface ReproductionRow {
  period: string;
  total_matings: number;
  total_farrowings: number;
  total_weanings: number;
  fr: number | null;
  avg_tb: number | null;
  avg_ba: number | null;
  avg_weaned: number | null;
  avg_lactation_days: number | null;
  pwmr_a: number | null;
  pwmr_b: number | null;
  rts_rate: number | null;
  // R3 확장 지표 (미집계 시 0/null)
  total_born_sum?: number | null;
  born_alive_sum?: number | null;
  total_stillborn?: number | null;
  total_mummified?: number | null;
  stillborn_rate?: number | null;
  mummified_rate?: number | null;
  birth_loss_rate?: number | null;
  mating_1_count?: number | null;
  mating_2_count?: number | null;
  mating_3plus_count?: number | null;
  ai_count?: number | null;
  natural_count?: number | null;
}

export interface BenchmarkValue {
  metric_code: string;
  target: number | null;
  benchmark_avg: number | null;
  benchmark_top25: number | null;
  warning: number | null;
  critical: number | null;
  alert_direction: string | null;
  unit: string | null;
  source_ref: string | null;
  confidence: string | null;
}

export interface ProductionSummary {
  group_by: string;
  period: string;
  country_scope: string | null;
  benchmarks: BenchmarkValue[];
  rows: ReproductionRow[];
}

export interface GrowFinishRow {
  group_code: string;
  start_date: string;
  end_date: string | null;
  head_in: number;
  head_out: number | null;
  avg_entry_weight_kg: number | null;
  avg_exit_weight_kg: number | null;
  adg_g: number | null;
  fcr: number | null;
  mortality_rate: number | null;
}

// #4 원가/수익 리포트
export interface CostByCurrency {
  currency: string;
  feed_cost: number | null;
  feed_qty_kg: number;
  sale_revenue: number | null;
  sale_head: number;
  sale_weight_kg: number | null;
  net: number | null;
}

export interface CostPeriodRow {
  period: string;
  currency: string;
  feed_cost: number | null;
  feed_qty_kg: number;
  sale_revenue: number | null;
  sale_head: number;
  net: number | null;
}

export interface CostSummary {
  start_date: string;
  end_date: string;
  period: string;
  by_currency: CostByCurrency[];
  rows: CostPeriodRow[];
  feed_cost_coverage: number | null;
  feed_records_total: number;
  feed_records_with_cost: number;
}

// PSY/NPD 연도별 추세 + 국가 벤치마크 병기
export interface AnnualKpiRow {
  year: number;
  psy: number | null;
  npd: number | null;
  avg_sows: number | null;
  total_weaned: number;
  total_farrowings: number;
  total_matings: number;
  farrowing_rate: number | null;
}

export interface CountryBenchmark {
  country: string;
  psy: number | null;
  npd: number | null;
  farrowing_rate: number | null;
}

export interface AnnualKpiTrend {
  country_scope: string | null;
  rows: AnnualKpiRow[];
  country_benchmarks: CountryBenchmark[];
}

// 무가입 농장 건강 스코어카드 (공개 퍼널)
export interface ScorecardRequest {
  country: string;
  psy?: number;
  npd?: number;
  farrowing_rate?: number;
  born_alive?: number;
  weaned?: number;
}
export type ScorecardBand = "TOP" | "GOOD" | "FAIR" | "LOW" | "NA";
export interface ScorecardMetric {
  code: string;
  value: number;
  avg: number | null;
  top25: number | null;
  target: number | null;
  direction: string;
  band: ScorecardBand;
  score: number;
  gap_to_avg: number | null;
}
export interface ScorecardOpportunity {
  code: string;
  band: ScorecardBand;
  gap_to_avg: number | null;
}
export interface ScorecardResponse {
  country: string;
  overall_score: number;
  overall_band: ScorecardBand;
  metrics: ScorecardMetric[];
  opportunities: ScorecardOpportunity[];
}

export interface DailyCount {
  count: number;
  total_born: number;
  born_alive: number;
  weaned: number;
  piglets: number;
}

export interface DailyReport {
  date: string;
  herd: { active_sows: number; gilts: number; open: number; pregnant: number; lactating: number; accident: number };
  matings: number;
  farrowings: DailyCount;
  weanings: DailyCount;
  accidents: number;
  piglet_deaths: DailyCount;
  removals: number;
}

export interface ComprehensiveDailyReport {
  date: string;
  herd: {
    gilt: number; open: number; pregnant: number; lactating: number; accident: number;
    sows_total: number; boars: number; nursing_piglets: number; finishers: number;
  };
  mating: { day: CdMating; month: CdMating };
  accidents: { day: CdAccident; month: CdAccident };
  production: { day: CdProduction; month: CdProduction };
  inout: { day: CdInout; month: CdInout };
}
export interface CdMating { total: number; gilt: number; sow: number; rebreed: number }
export interface CdAccident { total: number; rts: number; abortion: number; empty: number; infertile: number }
export interface CdProduction {
  farrowings: number; total_born: number; born_alive: number; stillborn: number; mummified: number;
  avg_birth_weight: number | null; weanings: number; weaned: number;
  avg_weaning_weight: number | null; avg_weaning_age: number | null; piglet_deaths: number;
}
export interface CdInout {
  gilt_in: number; sow_in: number; dead: number; culled: number; sold: number; transfer: number; boar_in: number;
}

export interface SowStatusRow {
  sow_id: string;
  ear_tag: string;
  status: SowStatus;
  parity: number;
  entry_date: string | null;
}

export interface SowStatusReport {
  total: number;
  by_status: Record<string, number>;
  sows: SowStatusRow[];
}

export interface FarrowingPerfRow {
  parity: number;
  farrowings: number;
  avg_total_born: number | null;
  avg_born_alive: number | null;
  avg_stillborn: number | null;
  avg_mummified: number | null;
  avg_weaned: number | null;
  avg_lactation_days: number | null;
  litters_weaned: number;
}

export interface MortalityCount {
  key: string;
  count: number;
  piglets: number | null;
}

export interface MortalityReport {
  removals_by_type: MortalityCount[];
  removals_by_reason: MortalityCount[];
  piglet_deaths_by_reason: MortalityCount[];
  piglet_deaths_by_age?: MortalityCount[];
  total_removals: number;
  total_piglet_deaths: number;
  born_alive_in_period: number;
  preweaning_mortality_rate: number | null;
}

export type DataQualityIssueType =
  | "LITTER_MISMATCH" | "WEANED_MISMATCH" | "DATE_REVERSAL"
  | "STATUS_ORPHAN" | "MISSING_FARROWING" | "MISSING_WEANING";

export interface DataQualityIssue {
  issue_type: DataQualityIssueType;
  severity: "CRITICAL" | "WARNING";
  sow_id: string | null;
  ear_tag: string | null;
  detail: string;
  event_date: string | null;
}

export type LedgerKind = "mating" | "farrowing" | "weaning" | "reproductive" | "piglet" | "removal";

export interface LedgerEntry {
  id: string;
  kind: LedgerKind;
  event_date: string;
  sow_id: string | null;
  ear_tag: string | null;
  summary: string;
}

export interface SowHistoryCycle {
  parity: number;
  mating_date: string | null;
  boar_ids: string[];
  farrowing_date: string | null;
  tb: number | null;
  ba: number | null;
  sb: number | null;
  mum: number | null;
  weaned: number | null;
  weaning_date: string | null;
  lactation_days: number | null;
  status: string;
}

// ── Notifications (P12-6 영구 인앱 알림) ──────────────────────────────────────
export interface NotificationItem {
  id: string;
  farm_id: string | null;
  title: string;
  body: string;
  alert_type: string | null;
  severity: "INFO" | "WARNING" | "CRITICAL" | null;
  related_entity_type: string | null;
  related_entity_id: string | null;
  read_at: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  unread_count: number;
  total: number;
}

export interface MarkReadResult {
  updated: number;
  unread_count: number;
}

export interface GenerateNotificationsResult {
  created: number;
}

// ── Analytics: PRRS 유전자 성과 추적 (Phase 2) ────────────────────────────────
export interface PrrsGeneticsRow {
  breed: string | null;
  breed_company: string | null;
  genetics_id: string | null;
  total_sows: number;
  affected_sows: number;
  prrs_events: number;
  incidence_rate: number;
}

export interface PrrsByGeneticsResponse {
  farm_id: string;
  rows: PrrsGeneticsRow[];
  total_sows: number;
  total_affected: number;
  total_events: number;
}

// ─── Admin Console (운영자 어드민, SUPER_ADMIN 전용) ───────────────────────────
export interface AdminOverview {
  organizations: number;
  farms: number;
  users: number;
  sows: number;
  signups_7d: number;
  activated_farms: number;
  stale_farms: number;
}

export interface DataMonitorRow {
  farm_id: string;
  farm_name: string;
  country: string;
  sows: number;
  last_event_at: string | null;
  events_7d: number;
  events_30d: number;
  events_total: number;
  issues: number;
  status: "onboarding" | "active" | "idle" | "stale";
  category: "real" | "test" | "pigplan";  // 실사용자 / 테스트 / 피그플랜이관
}

// 농장 데이터 심층 드릴다운 (GET /admin/data-monitor/{farm_id})
export interface SowStatusCount { status: string; count: number; }
export interface EventTypeBreakdown { type: string; total: number; count_30d: number; last_at: string | null; }
export interface RecentEvent { type: string; date: string | null; }
export interface FarmIntegrity { litter_mismatch: number; date_reversal: number; status_orphan: number; total: number; }
export interface FarmDataDetail {
  farm_id: string;
  farm_name: string;
  country: string;
  org_name: string | null;
  timezone: string | null;
  currency: string | null;
  created_at: string | null;
  total_sows: number;
  sows_by_status: SowStatusCount[];
  event_breakdown: EventTypeBreakdown[];
  recent_events: RecentEvent[];
  integrity: FarmIntegrity;
  psy: number | null;
  total_weaned_ytd: number;
  avg_sows_ytd: number | null;
}

export interface AdminMemberRow {
  id: string;
  email: string | null;
  name: string;
  role: string;
  system_role: string;
  approval_status: "PENDING" | "APPROVED" | "REJECTED";
  active: boolean;
  org_id: string | null;
  org_name: string | null;
  farm_count: number;
  created_at: string | null;
  last_login_at: string | null;
}
export interface AdminMemberFarm { farm_id: string; role: string; }
export interface AdminMemberDetail extends AdminMemberRow { farms: AdminMemberFarm[]; }
export interface PilotSignupRow {
  id: string; name: string; email: string; farm_size: string; country: string;
  role: string; lang: string; status: string; notes: string | null; created_at: string | null;
}
export interface AdminPaged<T> { items: T[]; meta: { total: number; page: number; per_page: number; pages: number }; }

export interface AnnouncementOut {
  id: string; title: string; body: string;
  category: "GENERAL" | "UPDATE" | "MAINTENANCE";
  pinned: boolean; published: boolean;
  publish_from: string | null; publish_until: string | null;
  lang: string | null; created_at: string | null;
}
export interface SupportReplyOut { id: string; author_id: string | null; is_staff: boolean; body: string; created_at: string | null; }
export interface SupportTicketOut {
  id: string; user_id: string; farm_id: string | null;
  subject: string; body: string; status: "OPEN" | "ANSWERED" | "CLOSED"; created_at: string | null;
}
export interface SupportTicketDetail extends SupportTicketOut { replies: SupportReplyOut[]; }

export interface AdminRuleRow {
  rule_id: string; domain: string; description: string; tier: string;
  enabled: boolean; warning: number | null; critical: number | null;
}

export interface AuditRow {
  id: string; actor_id: string | null; actor_name: string | null;
  action: string; entity_type: string; entity_id: string | null;
  old_value: Record<string, unknown> | null; new_value: Record<string, unknown> | null;
  created_at: string | null;
}

export interface AdminOrgRow {
  id: string; name: string; org_type: string; org_level: number;
  parent_org_id: string | null; country: string; farm_count: number; user_count: number;
}
export interface AdminOrgFarm { id: string; name: string; farm_code: string; country: string; active: boolean; }

// --- 동의 인프라 (CONSENT_SPEC / TERMS_DISPLAY §4·§7) ---
export interface ConsentDocMeta {
  doc_id: string; kind: string; version: string; status: string;
  lang: string; is_legal_priority: boolean; lang_pending: boolean; body?: string | null;
}
export type ConsentUiKind =
  | "NOTICE" | "NOTICE_EXCLUSION" | "LI_OBJECT" | "OPT_IN"
  | "WRITTEN_OPT_IN" | "HIDDEN" | "TRANSFER_CONSENT" | "BLOCKED";
export interface ConsentPurposePlan {
  purpose_code: string; order: number; ui_kind: ConsentUiKind; lawful_basis: string;
  visible: boolean; is_toggle: boolean; default_on: boolean;
  requires_evidence: boolean; status_tag: string; auto_off_if_uoom: boolean;
}
export interface ConsentGate {
  signup_blocked: boolean; paid_blocked: boolean; release_hold: boolean; reason_code: string | null;
}
export interface ConsentStateFlags {
  state: string | null; written_opt_in_required: boolean; do_not_sell_link: boolean;
  honor_uoom: boolean; exclude_location_from_sale: boolean;
}
export interface ConsentJurisdiction {
  code: string; country: string; group: string; counsel_review: boolean; notes: string[];
}
export interface SignupPlan {
  jurisdiction: ConsentJurisdiction; gate: ConsentGate; state_flags: ConsentStateFlags;
  documents: ConsentDocMeta[]; notice_version: string; any_draft: boolean; lang_gate: boolean;
  required_acks: string[]; purposes: ConsentPurposePlan[]; lang: string;
}
export interface ConsentChoice { purpose_code: string; granted: boolean; evidence_ref?: string | null; }
export interface RecordConsentRequest {
  farm_id?: string | null; selected_country: string; farm_country?: string | null;
  farm_state?: string | null; lang?: string | null; terms_ack: boolean; privacy_ack: boolean;
  choices: ConsentChoice[]; collection_context?: string;
}
export interface ConsentStatus {
  purpose_code: string; jurisdiction: string; lawful_basis: string; consent_status: string;
  notice_version: string; accepted_at: string | null; withdrawn_at: string | null;
  effective_from: string | null; collection_context: string;
}
// GET /consent/diff — 목적별 (필요 버전, 기록 버전). 판정 필드 없음 (PLATFORM_PARITY §9-8).
// ★ 국가 파라미터 없음 — 서버가 farm/org 에서 도출한다. 버전 동일성만 답하고 충분성은 답하지 않는다.
export interface ConsentDiffItem {
  purpose_code: string; lawful_basis: string; ui_kind: string;
  required_version: string; recorded_version: string | null;
  recorded_status: string | null; recorded_at: string | null;
}
export interface ConsentDiff {
  jurisdiction: string; group: string;
  selected_country: string; farm_country: string | null; counsel_review: boolean;
  farm_id: string | null; required_version: string; any_draft: boolean;
  items: ConsentDiffItem[];
}
export interface WithdrawRequest {
  purpose_code: string; farm_id?: string | null; action: string; reason?: string | null;
}

// v0.4 KPI 정책 벡터 (resolved) — GET /kpi/policy
export interface KpiPolicy {
  kpi_code: string;
  compute_enabled: boolean | null;
  display_role: "PRIMARY" | "SECONDARY" | "HIDDEN" | null;
  priority_class: "NORTH_STAR" | "DRIVER" | "GUARDRAIL" | "FINANCIAL" | "QUALITY" | "CONTEXT" | null;
  rule_enabled: boolean | null;
  benchmark_exposure: "FULL" | "CONTEXT_ONLY" | "NONE" | null;
  evidence_status: string | null;
}
