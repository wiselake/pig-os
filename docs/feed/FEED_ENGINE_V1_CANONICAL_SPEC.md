# Feed Engine V1 — Canonical Contract (F0 freeze, 2026-09-21)

> 성격: **구현 계약**. 이후 F1(입력 정규화)·F2(계산 엔진)는 이 문서 밖에서 해석하지 않는다.
> 근거 규율: 기존 조사·코드만 계약으로 변환했다. 새 외부 조사 0. 추정값 0.
> base `main fc96efc` · branch `feat/feed-engine-f0-canonical` · 코드 변경 0 (docs 만).
> 짝 문서: `FEED_ENGINE_IMPLEMENTATION_MAP.md` (파일 단위 F1/F2 경로 + 테스트 계약).

---

## 0. 한 화면

```
F0_CANONICAL_FREEZE       DONE  (사람 결정 필요 항목은 §12 에 명시 — F1/F2 착수를 막지 않는 것과 막는 것을 구분)

V1 metric                 CORE 6 · CONDITIONAL 5 · DEFERRED 6 · REJECTED 2 · UNRESOLVED 3
architecture              B — 별도 Feed domain engine + 기존 정책·상태·룰·프레젠테이션 재사용
canonical unit            kg · <currency>/kg (환산 없음) · head (스코프별 명시 분모)
canonical time            CALENDAR_PERIOD(record_date) · GROUP_LIFECYCLE(CLOSED 그룹, end_date∈period)
provenance                ACTUAL / DERIVED / INSUFFICIENT(+reason) — ESTIMATED 는 V1 에서 절대 생성하지 않음
FCR                       CONDITIONAL — CLOSED finisher group 코호트만, 정의는 kpi_service:428-449 == feed_metrics(PR #2)
cost variance             PARTIALLY_SUPPORTED — price+quantity(+mix) 정확 분해 지원, population 효과 미지원
findings                  6 (id 확정) — 임계값은 정책 결재 대상(fcr.high 만 기존 값 존재)
BLOCKER_FOUND             0 (P0 correctness). CONFLICT 1건 기록(FCR 두 정의) — 수정 안 함
```

---

## 1. 기존 조사 evidence 인벤토리 (새 조사 없음)

| # | 출처 | 위치 | 내용 | 판정 |
|---|---|---|---|---|
| E1 | KPI 산식 스펙 §5 FCR | `docs/specs/2026-03-19_kpi-calculation-specs.md:248-290` | `FCR = Σ사료 / ((exit−entry)×surviving_head)`, CLOSED 그룹만, 사료 누락→NULL, **체중 누락→추정 ADG 보간(옵션)** | `DOC_STALE` (SQL 은 `animal_groups`/`grow_records` — 현재 스키마엔 없음) · 보간 항목은 §5 REJECTED |
| E2 | 제품 확장 결정 §5 Feed | safety `docs/product/PIGOS_PRODUCT_EXPANSION_DECISION.md:306-380` | Feed-1 = FCR · Feed Cost/pig · Feed Cost/kg gain + What Changed + Action. 최소 입력 feed_quantity·feed_unit_cost·pig/group weight·period. WTP = HYPOTHESIS. Feed-2(IOFC·OMW·packer grid·multi-farm) P1.5 이후. Off-feed 보류 | `DOC_CURRENT` |
| E3 | 구현 핸드오프 §6 EPIC 4 | safety `docs/product/PIGOS_PRODUCT_IMPLEMENTATION_HANDOFF.md:561-620` | "데이터 없을 때 추정값으로 채우지 않는다" · canonical formula/version · What Changed 문장 · bounded action checklist · 자동 처방 금지 · Basic FCR Free 후보 / Cost Paid 가설 | `DOC_CURRENT` |
| E4 | FEATURE_REGISTRY F-0011 | safety `docs/FEATURE_REGISTRY.md:281-330` | 경로 목록 · 착수 실측(있는 것/없는 것) · **★ FCR 은 문서상 유료·런타임상 무료(D-15 비대칭)** | `DOC_CURRENT` |
| E5 | 결정 원장 D-15 / HIQ B-7 | safety `docs/legal/DECISION_REGISTER.md` · `HUMAN_INPUT_QUEUE.md` | FCR 과금 경계 미결 — 무료 추인(a) vs 유료 회수(b) | `UNRESOLVED` (사람) |
| E6 | 국가 KPI 룰 스펙 v0.3.1 | `docs/specs/COUNTRY_KPI_RULE_SPEC_v0.3.1.md:165,273` | FCR·ADG 계열 = "TBD · v0.4 실사 대상" · `code_mappings` 도메인에 `FEED_PRODUCT` 예정 | `DOC_CURRENT` (미정의가 사실) |
| E7 | T6 정의 충돌 등록부 | safety `docs/kpi/T6_DEFINITION_CONFLICT_REGISTER.md:163-198` | T6-18 FCR: 분자 사료급여량(=투입)·분모 증체량·`kg_per_kg`, "체중구간 정의필요, value_scale D-13" · T6-19 ADG/출하체중 lb vs kg 정의 없음 · 외부(AHDB·NPB·InterPIG)는 명칭만 일치, 산식 미기재 | `DOC_CURRENT` |
| E8 | 벤치마크 시드 | `api/app/db/benchmark_seed.py:10-12,62-64` | FCR 행 `value_scale='n/a'`(enum 에 ratio 없음) "사용자 확정 필요" | `CODE_CURRENT` + `UNRESOLVED`(D-13) |
| E9 | 운영 기본값 | `api/app/db/operational_defaults_seed.py:20` | `fcr.high` lower_better warning 3.0 critical 3.3 | `CODE_CURRENT` |
| E10 | 글로벌 표시 정책 | `api/app/db/global_policy_defaults.py:25-45` | FCR·ADG = `GLOBAL_HIDDEN`(계산·룰은 계속, 표시만 숨김) | `CODE_CURRENT` |
| E11 | Entitlement 매트릭스 | `docs/product/PIGOS_FEATURE_ENTITLEMENT_MATRIX.md:24,45` | `capture_feed` 기존·무료 · `insight_feed_intel`(사료효율·FCR 최적화) R2 유료 TBD — **결재 대기, 승인 전 paywall 구현 금지** | `DOC_CURRENT` |
| E12 | PHASE 0 coverage audit | safety `docs/feed/PHASE0_AUDIT_PLAN.md` · `scripts/feed_coverage_audit.sql` | GO/PARTIAL/NO-GO 임계 선정의 · STRUCTURAL 실측: quantity 의미 컬럼 0 · 재고 경계 0 · 폐사체중 0 · live/carcass 구분 0 · feed_type 자유입력 · 실데이터 미실행(결재 5) | `DOC_CURRENT` |
| E13 | 스펙 §5 "FCR 절감 금액" | `2026-03-19_kpi-calculation-specs.md:367-405` | `fcr_savings = ΔFCR × avg_daily_feed_intake × feed_price` — intake 는 추정 입력 | `DOC_STALE` → §5 DEFERRED (ESTIMATED 입력 필요) |

충돌 처리: E1 SQL 스키마 ≠ 현재 코드 → `CODE_CURRENT` 가 우선(§2). E1 "보간 옵션" ↔ E3 "추정 금지" → E3 채택(§5 REJECTED). E4 "FCR 유료" ↔ E10 "숨김·무료 계산" → 사실은 "계산되고 기본 응답 metrics 에 실리나 GLOBAL_HIDDEN" — 노출 경계는 E5 결재.

---

## 2. 현재 Feed 구현 인벤토리 (실측, 호출 경로 기준)

기준: `main fc96efc`(=프로덕션 api 6675b3f 와 feed 경로 동일) / 괄호 안 = PR #2 `safety e0286de` 추가분.

| 계층 | 판정 | 근거 (호출 경로) |
|---|---|---|
| DB/model | `EXISTS` | `feed_records` (`health.py:48-69`): farm_id·sow_id?·group_id?(FK 없음)·building_id?·record_date·feed_type(50, 자유)·quantity_kg·unit_cost?·currency?·notes·soft-delete. `finisher_groups`(entry/exit avg weight?·head_count_in/out?·start/end_date?) `ops.py:85-118`. `kpi_snapshots.fcr` 컬럼 `ops.py:73`. 재고·단가 마스터·사료 제품 테이블 **없음** |
| schema | `EXISTS` | `schemas/feed.py` FeedRecordCreate(quantity_kg 0<x≤100000 · unit_cost 0≤x≤999999 · 미래일 +1일 거부) / Response. (PR #2: `FeedBasicResult` 스키마 `withheld` 포함) |
| API | `EXISTS` (입력만) | `routers/base/feed.py` GET/POST/DELETE `/farms/{id}/feed-records` → `feed_service` CRUD. **계산 엔드포인트 없음** |
| service | `EXISTS` (CRUD) / (PR #2 `PARTIAL`) | `feed_service.create/list/delete` (농장 소속·월마감·미래일 검증). PR #2 `load_feed_cohort()` — **어느 라우터도 호출하지 않음**(docstring 명시) |
| calculation | `PARTIAL` ×2 + (PR #2 `EXISTS`, 미연결) | ① `kpi_service.build_herd_kpis:428-449,534-535` FCR·ADG — 대시보드 `metrics` 에 실림(GLOBAL_HIDDEN) · CLOSED 그룹(end_date∈기간)·head_out·양 체중 존재 필수·group_id 귀속 사료 전생애 합 ② `report_service.build_grow_finish_rows:355-390` 그룹별 fcr/adg — **open 그룹은 head_in 으로 gain 대체** ③ `report_service.get_cost_summary:916-1045` Σqty×unit_cost 통화별 + `feed_cost_coverage` (PR #2 ④ `engine/feed_metrics.py` FCR·cost/pig·cost/kg gain 순수 함수, `FORMULA_VERSION="FEED_BASIC.v1"`, withheld 사유 — 라우터 0) |
| worker/job | `PARTIAL` | `jobs/kpi.py` 가 `build_herd_kpis` 결과 중 snapshot 컬럼에 있는 `fcr` 를 영속(`_WITHHELD_FIELDS` 에 fcr 없음). 사료 전용 잡 없음 |
| frontend | `EXISTS` (입력·원가 리포트) | web `src/app/(app)/feed/page.tsx`(feed_type 자유 텍스트 입력) · `reports/cost/page.tsx`. Android/iOS: 사료 입력·표시 **없음** (grep: 알림 DTO 의 "feed" 문자열뿐) |
| tests | `PARTIAL` | main: `test_feed_records.py`(스키마·월마감), 리포트 테스트. PR #2: `unit/test_feed_metrics.py` · `integration/test_feed_cohort.py`(코호트 FCR == build_herd_kpis FCR 동치) |
| country policy | `PARTIAL` | `CountryKpiPolicy`(compute_enabled·display_role·rule_enabled·benchmark_exposure·effective_from/to) 에 FCR 행 GLOBAL_HIDDEN. 국가별 FCR 정책 행 0 (E6 TBD) |
| benchmark | `PLACEHOLDER` | `benchmark_seed.py` fcr 행 value_scale n/a · "체중구간 정의필요" (E8) |
| unit conversion | `NOT_FOUND` | 백엔드에 kg↔lb 변환 코드 0 (`countries.py` 는 `unit_system` 라벨만). 웹 표시 변환 0. 저장·계산·표시 전부 kg |
| currency | `PARTIAL` | 행 단위 currency(NULL→농장 기본통화로 귀속, cost-summary) · 환산 0 · 혼합 통화는 cost-summary 는 통화별 분리, feed_metrics 는 `CURRENCY_MIXED` 유보 |
| data quality | `PARTIAL` | cost-summary `feed_cost_coverage` · feed_metrics `withheld` · PHASE0 audit 하네스(실데이터 미실행) |
| AI/LLM | `NOT_FOUND` (feed) | `llm_renderer` 는 룰 결과 문장화 전용. feed finding 0 · `fcr.high` 룰 1건(`rules/grow_finish.py:16-36`) |

**CONFLICT-2 (2026-09-22 Codex 리뷰, 엔진 쪽만 수정)**: `kpi_service:443-449` 의 FCR 분자 조인은 `end_date` 만 보고 체중·head_out 조건이 없어, 체중 없는 CLOSED 그룹의 사료가 분자에만 들어가 FCR 을 부풀린다(분모 집합 ≠ 분자 집합). 엔진 로더(`feed_service.load_feed_cohort`)는 두 집합을 같게 고쳤다. kpi_service 는 **LEGACY BUG** 로 기록만(F4 보고), `test_cohort_feed_numerator_uses_the_same_eligible_groups_as_the_denominator` 가 차이를 고정.

**CONFLICT-1 (기록만, 수정 안 함)**: FCR 정의가 둘이다 — ① `kpi_service`/`feed_metrics`: CLOSED + head_out + 양 체중 필수, gain=(exit−entry)×head_out ② `report_service` 그룹행: end_date 없어도 계산, head_out 없으면 head_in 으로 대체. 같은 농장에서 대시보드 FCR 과 grow-finish 리포트 FCR 이 다를 수 있다. **canonical = ①** (§5). ②의 정렬은 F2 범위 밖 별도 항목(IMPLEMENTATION_MAP §4).

---

## 3. 계층 계약

```
RAW INPUT           feed_records 행 (+ finisher_groups, farms.currency/unit_system)          ACTUAL 만 존재
    ↓
NORMALIZATION (F1)  단위 kg 고정(변환 없음) · currency NULL→farm.currency(cost-summary 관례) ·
                    feed_type key = lower(trim, 연속공백 1) · 귀속 스코프 분류(SOW/GROUP/BUILDING/FARM_UNATTRIBUTED)
                    · 기간 절단(record_date∈period) · 코호트 선정(CLOSED 그룹 end_date∈period)
    ↓
DATA QUALITY /      coverage(costed_rows/rows, kg 가중) · currency 집합 · orphan group_id · zero qty ·
AVAILABILITY        분모 존재 여부 → 각 metric 의 INSUFFICIENT reason 결정 (§7)
    ↓
DETERMINISTIC       순수 함수 (feed_metrics 확장). Decimal 입력, 반올림은 마지막 한 곳.
CALCULATION (F2)    같은 입력 → 같은 출력. DB·시계·난수 접근 0
    ↓
BENCHMARK /         기존 CountryKpiPolicy + benchmark(effective_metric_values) 재사용. FCR 외 feed metric 은
COMPARISON          벤치마크 없음(V1) → 비교는 period-over-period 만
    ↓
FINDING             RuleRegistry 룰 (`feed.*`) → Finding(rule_id·kpi·severity·current/target·detail.evidence).
                    임계값은 operational_defaults(resolve) — APPROVED 전 룰 비활성(rule_enabled=false)
    ↓
AI EXPLANATION      llm_renderer 가 StructuredResult 를 문장화. 숫자 계산·finding 생성 금지 (기존 원칙 그대로)
```

---

## 4. 입력 계약 (F1 이 소비하는 것)

| 입력 | 출처 | 필수 | 정규화 규칙 | 결측/0 의미 (§8) |
|---|---|---|---|---|
| `quantity_kg` | feed_records | Y (NOT NULL, 스키마 >0) | 그대로 kg. **의미 = "기록된 급여량"(AS_RECORDED)** — 급이/소진/입고 구분 컬럼 없음(E12 A1). 0 은 스키마가 거부하므로 DB 의 0 은 데이터 오류 → `zero_qty` 품질 플래그, 합산 제외 안 함(값 그대로) | 행 없음 = **no_data**, 행 있음 = 활동 |
| `record_date` | feed_records | Y | 농장 현지 날짜(입력 시 farm_today 검증). 기간 절단 기준 | — |
| `unit_cost` | feed_records | N | currency/kg. NULL = **원가 미입력**(0 아님) | NULL 행은 `uncosted` 로 센다. 채우지 않는다 |
| `currency` | feed_records | N | NULL → `farm.currency` (cost-summary:929 관례 채택). 행 집합 통화 ≥2 → `currency_mixed` | — |
| `feed_type` | feed_records | N | key = lower·trim·연속공백→1. 원문 보존. NULL/blank → `UNSPECIFIED` | 어휘 없음(UNRESOLVED-2) |
| `sow_id / group_id / building_id` | feed_records | N (최대 1) | 스코프 분류. group_id 는 FK 없음 → 존재하지 않는/삭제된 그룹 = `orphan_group` 플래그, 코호트 제외 | 셋 다 NULL = `FARM_UNATTRIBUTED` |
| 코호트 | finisher_groups | 조건부 | CLOSED = `end_date IS NOT NULL AND end_date∈period AND head_count_out IS NOT NULL AND avg_entry/exit_weight IS NOT NULL` (kpi_service:428-436 문자 그대로) | 조건 미충족 그룹 = 코호트 밖(무시, 추정 안 함) |
| `farm.unit_system` | farms | Y | 표시 계층에만 전달. 계산 미사용 | — |

입력에서 **하지 않는 것**: lb→kg 변환(입력이 kg 로만 들어온다 — 웹 폼 라벨 kg, 변환 코드 0) · 통화 환산 · 재고 차감 · 두수 추정.

---

## 5. V1 Metric Inventory

공통: `scope` ∈ {FARM, GROUP_COHORT} · `time_basis` ∈ {CALENDAR_PERIOD, GROUP_LIFECYCLE} · `unit` canonical(§10) · `country_dependency`: 산식 **없음**(전부 global), 표시/벤치마크만 국가 · `estimated_policy`: **NEVER** (전 metric 공통) · `source_evidence`: E-번호.

| metric_id | display | scope | numerator / denominator | unit | time_basis | required_inputs | missing_policy | quality_req | benchmark_dep | impl_status | **v1_status** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `FEED_QTY` | 사료 급여량 | FARM (+scope 필터) | Σ quantity_kg / — | kg | CALENDAR_PERIOD | quantity_kg, record_date | 행 0 → INSUFFICIENT(no_data). 행 있으면 값(0 불가) | zero_qty·orphan 플래그 동반 | 없음 | cost-summary `feed_qty_kg` 로 존재(EXISTS) | **CORE** |
| `FEED_COST` | 사료비 | FARM | Σ(quantity_kg×unit_cost) / — | currency | CALENDAR_PERIOD | + unit_cost, currency(단일) | uncosted_rows>0 → INSUFFICIENT(cost_incomplete) — 부분합은 evidence 에만(`partial_cost`, `coverage`). costed 0 → no_cost. 통화≥2 → currency_mixed | coverage==100% | 없음 | cost-summary 는 부분합+coverage 노출 / feed_metrics 는 유보 → **canonical = 유보 + evidence** (E3 "채우지 않는다") | **CORE** |
| `FEED_UNIT_PRICE` | 평균 단가 | FARM (feed_type 별 가능) | Σ(qty×cost) / Σqty (costed 행만) | currency/kg | CALENDAR_PERIOD | unit_cost 행 ≥1 | costed 0 → no_cost · currency_mixed | — | 없음 | NOT_FOUND | **CORE** |
| `FEED_MIX_SHARE` | 사료 구성비 | FARM | Σqty(feed_type key) / Σqty — 결과 본체는 evidence.shares(항목별), **스칼라 value = 최대 구성비(dominant share)**, evidence.dominant_type | ratio_0_1 | CALENDAR_PERIOD | feed_type | UNSPECIFIED 도 한 항목으로 노출(숨기지 않음) | 어휘 흔들림 → normalized key 기준 | 없음 | NOT_FOUND | **CORE** (어휘는 UNRESOLVED-2, 산식은 확정) |
| `FEED_QTY_CHANGE` | 급여량 변화 | FARM | QTY(p1) − QTY(p0) (+ ratio) | kg, ratio | CALENDAR_PERIOD ×2 (**같은 grain** — 달력월↔달력월 또는 같은 길이, P-6 2026-09-22) | 두 기간 모두 FEED_QTY 값 | 어느 한 기간 INSUFFICIENT → INSUFFICIENT(prior_insufficient) | grain 비교 가능 (evidence.comparison_grain) | 없음 | NOT_FOUND | **CORE** |
| `FEED_COST_CHANGE` | 사료비 변화 | FARM | COST(p1) − COST(p0) | currency | CALENDAR_PERIOD ×2 | 두 기간 FEED_COST 값(둘 다 complete, 같은 통화) | 同上 + currency_mixed | — | 없음 | NOT_FOUND | **CORE** |
| `FEED_QTY_PER_HEAD` | 두당 급여량 | GROUP_COHORT | Σqty(그룹 귀속) / Σhead_count_out | kg/head | GROUP_LIFECYCLE | group_id 귀속 사료, CLOSED 코호트 | head_out 0 → no_head_out · 코호트 0 → no_cohort | 귀속률 | 없음 | NOT_FOUND | **CONDITIONAL** (귀속·코호트 존재) |
| `FEED_COST_PER_PIG` | 두당 사료비 | GROUP_COHORT | Σ(qty×cost) / Σhead_out | currency/head | GROUP_LIFECYCLE | + cost complete | cost_incomplete·currency_mixed·no_head_out | coverage 100% | 없음 | PR #2 feed_metrics EXISTS(미연결) | **CONDITIONAL** |
| `FCR` | 사료요구율 | GROUP_COHORT | Σqty(귀속) / Σ((exit−entry)×head_out) | kg/kg | GROUP_LIFECYCLE | 코호트(양 체중·head_out) + 귀속 사료 | gain≤0 → no_gain · feed≤0 → no_feed | 귀속률 · 체중 기준(live, 입력 라벨) | benchmark fcr(value_scale UNRESOLVED-3) · `fcr.high` 룰 | kpi_service EXISTS(대시보드 metrics, GLOBAL_HIDDEN) · feed_metrics EXISTS | **CONDITIONAL** |
| `FEED_COST_PER_KG_GAIN` | 증체 kg 당 사료비 | GROUP_COHORT | Σ(qty×cost) / Σgain | currency/kg | GROUP_LIFECYCLE | FCR 입력 + cost complete | no_gain·cost_incomplete·currency_mixed | 同 FCR | 없음 | feed_metrics EXISTS(미연결) | **CONDITIONAL** |
| `ADG` | 일당증체 | GROUP_COHORT | Σgain / Σ((end−start)×head_out) ×1000 | g/day | GROUP_LIFECYCLE | 코호트(pig_days) | pigdays 0 → context_missing · gain≤0 → no_gain · 코호트 0 → no_cohort | — | GLOBAL_HIDDEN | kpi_service:534 EXISTS | **CONDITIONAL** — 엔진이 같은 적격 코호트로 계산하고 kpi_service 값과 동치 테스트 (2026-09-22 정정: "참조만" → 계산) |
| `FEED_COST_PER_HEAD_FARM` | 농장 두당 사료비 | FARM | FEED_COST / 평균 상시모돈 등 | currency/head | CALENDAR_PERIOD | 분모 정의 | — | — | — | NOT_FOUND | **DEFERRED** — 사료가 모돈/비육 어느 쪽인지 귀속 없이 농장 두당은 의미 없음(UNRESOLVED-1) |
| `MARKET_WEIGHT_EFFICIENCY` | 출하체중 연동 효율 | GROUP_COHORT | — | — | — | 출하체중 live/carcass 기준 | — | — | — | NOT_FOUND(D1 구조적 0) | **DEFERRED** (E12 D1 · E2 Feed-2) |
| `IOFC` | 사료비 차감 수익 | FARM | 판매수익 − 사료비 | currency | CALENDAR_PERIOD | removals.sale_price(모돈만) · 비육 판매가 없음 | — | — | — | cost-summary 에 sale_revenue 부분 존재 | **DEFERRED** (E2 Feed-2: 판매가·판매두수 prerequisite) |
| `FCR_SAVINGS` | FCR 절감액 | — | ΔFCR×intake×price | currency | — | avg_daily_feed_intake(추정) | — | — | — | E13 | **DEFERRED** (ESTIMATED 입력 필요 → V1 금지) |
| `FEED_INVENTORY` | 사료 재고 | FARM | 입고−소진 | kg | — | 재고 경계 | — | — | — | E12 E1 STRUCTURAL 0 | **DEFERRED** |
| `OFF_FEED_ANOMALY` | 급이 이상 | — | — | — | daily | 고빈도 급이 데이터 | — | — | — | — | **DEFERRED** (E2 §5-4) |
| `SOW_FCR` | 모돈 FCR | SOW | — | — | — | 모돈 증체 개념 부재 | — | — | — | — | **REJECTED** (분모 정의 불가) |
| `FCR_INTERPOLATED` | 체중 누락 보간 FCR | — | 추정 ADG 보간 | — | — | — | — | — | — | E1 "옵션" | **REJECTED** (E3 추정 금지) |
| — | quantity_kg 의미(급이 vs 소진 vs 입고) | — | — | — | — | — | — | — | — | E12 A1 | **UNRESOLVED-1** (계약: AS_RECORDED 로 표기, 산식 버전에 명시) |
| — | feed_type canonical 어휘 | — | — | — | — | — | — | — | — | E6 FEED_PRODUCT 예정 | **UNRESOLVED-2** (V1 은 normalized key) |
| — | FCR benchmark value_scale | — | — | — | — | — | — | — | — | E8/D-13 | **UNRESOLVED-3** |

집계: CORE 6 · CONDITIONAL 5 · DEFERRED 6 · REJECTED 2 · UNRESOLVED 3.

`calculation` 정본은 IMPLEMENTATION_MAP §2 의 함수 서명 + 본 표의 numerator/denominator. 반올림: FCR 3 · cost 2 · unit price 4 · ratio 4 · kg 1 (feed_metrics 기존 값 유지).

---

## 6. CORE / CONDITIONAL 분리 근거

- CORE = `feed_records` 만으로 결정되는 것. 분모가 "기록 자체"(kg, 통화)라 돈군 경계·체중이 필요 없다.
- CONDITIONAL = `finisher_groups` 코호트(CLOSED + 양 체중 + head_out)와 **group_id 귀속**이 있어야 한다. PHASE0 실데이터 감사(결재 5 대기)에서 `B4 FCR-computable` 비율이 나오기 전까지 실제 가용성은 미확인 — 그래서 CONDITIONAL 이지 CORE 가 아니다.
- FCR 입력 가용성 실측(E12 STRUCTURAL): feed consumed = AS_RECORDED · entry/exit weight = 그룹 avg(NULL 허용) · mortality = head_in−head_out 로만(폐사 체중 없음 → gain 은 **출하두 기준**, 폐사 증체 미반영 — 산식 버전 문서에 한계로 기재) · 그룹 경계 = start/end_date · 측정 기간 = 전생애.
- 분모/경계가 추정이면 값 대신 INSUFFICIENT: open 그룹의 head_in 대체(CONFLICT-1 ②)는 canonical 에서 **불허**.

---

## 7. Provenance 계약 (기존 모델 재사용 판정)

| 기존 모델 | 위치 | 재사용 |
|---|---|---|
| `KpiStatus{status: normal/warning/critical/insufficient, reason}` | `schemas/kpi.py:25-35` · `kpi_status_assembler.py` | **재사용** — 판정 결과 표현. reason 어휘 확장(아래) |
| `assemble_kpi_status(values, findings, pending)` | 同 | **재사용** — feed metric 도 같은 assembler 로 status 산출 |
| `withheld: dict[metric, reason]` | PR #2 `feed_metrics.FeedBasicResult` · `jobs/kpi.py _WITHHELD_FIELDS` | **재사용** — INSUFFICIENT 의 구체 사유 전달 |
| `Finding.detail` / `evidence` | `rule_engine.py:51-61` | **재사용** — 근거 숫자(coverage·rows·currencies) 실림 |
| benchmark `KpiBenchmark{avg,top25,target}` | `schemas/kpi.py:15-22` | 재사용(FCR 만 해당) |

새 enum 은 **하나만** 추가한다 — 값의 출처:

```
provenance ∈ { ACTUAL, DERIVED, INSUFFICIENT }        # ESTIMATED 는 정의만 두고 V1 에서 생성 금지(불변식 T-I3)
  ACTUAL        기록값의 합/필터 (FEED_QTY, FEED_COST[complete])
  DERIVED       비율·차분 (UNIT_PRICE, MIX_SHARE, *_CHANGE, FCR, COST_PER_*, ADG)
  INSUFFICIENT  값 없음 + reason (아래 어휘)
quantity_basis = "AS_RECORDED"                         # UNRESOLVED-1 이 닫히면 CONSUMED|DELIVERED 로 승격 — 산식 버전 bump
```

reason 어휘 = 기존(`no_data · insufficient_sample · out_of_valid_range · no_policy · policy_pending · evaluation_skipped · rule_disabled · context_missing`) + feed 추가: `cost_incomplete · no_cost · currency_mixed · no_gain · no_feed · no_head_out · no_cohort · prior_insufficient · attribution_missing`. (feed_metrics 의 대문자 상수 `NO_GAIN` 등은 이 소문자 어휘로 통일 — F2 에서 매핑.)

---

## 8. Missing / Zero / Unknown 의미 고정

| 상태 | feed 데이터에서의 정의 | 결과 |
|---|---|---|
| 행 없음 (기간 내 feed_records 0) | **missing** = 입력 안 됨. "급여 0" 이 아니다 | FEED_QTY = INSUFFICIENT(no_data). 0 으로 표시 금지 |
| `quantity_kg = 0` 행 | 스키마가 거부(>0)하므로 정상 경로로 생길 수 없음. 존재하면 데이터 오류 | 값에 포함(0 이라 영향 없음) + quality flag `zero_qty` |
| `unit_cost NULL` | 원가 **미입력**. 0원 아님 | uncosted 로 계수 → cost 계열 INSUFFICIENT(cost_incomplete) |
| `unit_cost = 0` | 스키마 허용(ge=0). "무상"으로 해석 — 입력 그대로 | costed 로 계수. 값 0 기여. quality flag `zero_cost` |
| `currency NULL` | 농장 기본통화로 간주(cost-summary 관례) | 통화 집합에 farm.currency 로 편입 |
| `feed_type NULL/blank` | 미지정 | `UNSPECIFIED` 구성비 항목 |
| 코호트 0 (CLOSED 그룹 없음) | not applicable(이 기간에 출하 완료 없음) | 코호트 metric INSUFFICIENT(no_cohort) — no_data 와 구분 |
| 사료 있으나 group_id 미귀속 | attribution missing | 코호트 metric 의 분자에서 제외 + quality `unattributed_share` 노출. INSUFFICIENT(attribution_missing) 는 귀속 0 일 때 |
| 이전 기간 INSUFFICIENT | 비교 불가 | *_CHANGE = INSUFFICIENT(prior_insufficient) |

기존 원칙 재사용: `insufficient + reason` (ADR-KPI-08) 그대로. Feed 는 새 상태를 만들지 않고 reason 만 늘린다.

---

## 9. 시간 기준

| time_basis | 대상 | 정의 | V1 지원 |
|---|---|---|---|
| `CALENDAR_PERIOD` | CORE 전부 | `record_date ∈ [start, end]` (농장 현지 날짜, 입력 시 검증됨). 월·주·임의 구간 | **월·주·임의(start,end)**. 일별 집계는 F2 함수는 지원하되 표시 대상 아님 |
| `GROUP_LIFECYCLE` | CONDITIONAL 전부 | 코호트 = `end_date ∈ [start,end]` 인 CLOSED 그룹. 분자 사료 = 그 그룹에 귀속된 행 **전생애**(record_date 무관) | 지원 (kpi_service 와 동일) |
| period-over-period | *_CHANGE · VARIANCE | p0 = p1 과 **같은 grain** 의 직전 구간 — 월이면 전월(28~31일 길이 차이 허용) · 임의 구간이면 같은 길이. **P-6 (2026-09-22)**: §5 표의 "같은 길이" 는 이 줄의 "월이면 전월" 을 잘못 좁힌 표현이었고 실데이터(Oracle shadow)에서 월 쌍 99 중 81 을 막았다 — 정정. RATE 지표는 V1 에 없음(생기면 days 정규화) | 지원 |
| rolling | — | — | **미지원**(V1). rolling12M 등은 KPI 트렌드 계층 몫 |

혼동 금지: 코호트 metric 을 "이 달에 먹은 사료 / 이 달 증체" 로 계산하지 않는다(E4 실측 §5 사고 기록). 달력 metric 과 코호트 metric 은 같은 화면에 있어도 기간 의미가 다르다 — 표시 계층이 라벨로 구분한다.

---

## 10. 단위 계약

```
raw unit        kg (입력 폼·스키마·DB 전부 kg) · currency/kg · head
canonical unit  kg · <currency>/kg · head            ← 계산 엔진 내부. 변환 0
display unit    farm.unit_system == IMPERIAL → lb (×2.20462, 표시 계층) · tonne(×0.001, 표시 계층) · currency/tonne
```

- 변환 위치: **표시 계층(F3, 웹/모바일 프레젠테이션)** 만. F1/F2 는 kg 만 안다. 국가별 표시 단위가 계산에 들어오지 않는다(불변식 T-I4).
- 현재 lb 변환 코드는 어디에도 없다(§2). US 농장도 kg 로 입력·표시 중 — IMPERIAL 표시는 F3 항목.
- 통화: 행 통화 그대로. 환산 없음. 혼합이면 INSUFFICIENT(currency_mixed). 농장 기본통화 귀속만 허용.
- head: 분모 종류를 metric 이 명시(`head_count_out` = marketed head). average inventory·placed head 는 V1 분모 아님.

---

## 11. Feed Cost Variance decomposition — `PARTIALLY_SUPPORTED`

기호: 기간 0→1, feed_type key i, `q_i` kg, `p_i` 단가(currency/kg, costed 행 가중), `C = Σ_i p_i q_i`, `Q = Σ_i q_i`, `s_i = q_i/Q`.

**정확 항등식 (잔차 0)**
```
ΔC = Σ_i (p_i^1 − p_i^0)·q_i^0        ← PRICE effect      (Laspeyres, 기준 수량)
   + Σ_i p_i^1·(q_i^1 − q_i^0)        ← QUANTITY effect   (Paasche, 현재 단가)

QUANTITY effect 의 정확 분해:
   Σ_i p_i^1·(q_i^1 − q_i^0)
 = (Q^1 − Q^0)·Σ_i p_i^1 s_i^0        ← VOLUME effect  (총량 변화, 기준 구성비)
 + Q^1·Σ_i p_i^1 (s_i^1 − s_i^0)      ← MIX effect     (구성비 변화, 현재 총량)
```
증명: Δq_i = ΔQ·s_i^0 + Q^1·Δs_i (Σ_i Δs_i = 0 이므로 항등). 세 항 합 = ΔC, 근사 없음.

| 효과 | 필요 입력 | V1 |
|---|---|---|
| PRICE | 양 기간 feed_type 별 p_i, q_i (costed 100%, 단일 통화) | **SUPPORTED** |
| QUANTITY (VOLUME + MIX) | 同上 | **SUPPORTED** |
| POPULATION (두수 변화) | 기간별 두수 분모 — FARM 스코프 분모 UNRESOLVED-1, 코호트는 달력 기간과 불일치 | **NOT_SUPPORTED** (V1) |
| 신규/소멸 feed_type | i 가 한 기간에만 있으면 q_i^0 또는 q_i^1 = 0 으로 두고 p_i 는 존재하는 쪽 값 사용 — 항등식 유지 | SUPPORTED (edge 테스트 T-C7) |

조건: 두 기간 모두 `FEED_COST` 가 complete(cost_incomplete 아님)·같은 통화. 아니면 decomposition 전체 INSUFFICIENT — 부분 분해를 내지 않는다. 채택하지 않는 것: 평균가×평균량 근사(잔차 발생).

---

## 12. Country policy 경계

| 축 | 국가별? | 근거·V1 처리 |
|---|---|---|
| formula | **아니오** | 전 metric global canonical. 국가별 fork 0 (T6-18 "체중구간" 은 코호트 정의이지 국가 차이가 아님) |
| unit | 표시만 | `farm.unit_system` → F3. 계산 kg 고정 |
| display (노출·순서·라벨) | 예 | `CountryKpiPolicy.display_role` + `CountryKpiPresentation` 재사용. 현재 FCR·ADG GLOBAL_HIDDEN; 새 feed metric 은 정책 행 없음 → `resolve` 결과 None = 미거버넌스 → **표시 안 함**(fail-closed, 기존 규칙) |
| benchmark | 예 | `effective_metric_values`(FCR 만 시드, value_scale UNRESOLVED-3). CORE metric 벤치마크 없음 |
| threshold | 예 | `operational_defaults`/`rule_configs` 경유 `resolve(ctx, rule_id, kpi, w, c)`. 신규 룰 임계값 = **정책 결재 대상**(APPROVED 전 seed 금지) |
| recommended range | 예 | 同 threshold |
| terminology | 예 | `engine/i18n.py` 8언어 (fcr 항목 존재) |
| availability | 예 | `compute_enabled`/`rule_enabled` 행 |

기존 KPI 엔진과의 충돌: 없음 — 정책 축은 전부 재사용. 단 `DASHBOARD_POLICY_KPIS = {PSY, NPD, FARROWING_RATE}` 만 status 조립 대상이므로 feed metric status 는 별도 호출로 조립(IMPLEMENTATION_MAP §2).

---

## 13. Finding layer 계약

naming = 기존 `<domain>.<condition>` (`fcr.high`, `adg.low`, `inventory.zero`). `feed` 도메인 신설.

| finding_id | trigger (deterministic) | inputs | severity source | evidence(detail) | no-judgment 조건 |
|---|---|---|---|---|---|
| `feed.cost_increased` | FEED_COST_CHANGE ratio ≥ w/c | FEED_COST p0,p1 | `resolve(ctx,"feed.cost_increased","FEED_COST",w,c)` — 값 **미정(결재)** | ΔC, ratio, 분해(§11) | 어느 기간 INSUFFICIENT · currency_mixed |
| `feed.unit_price_increased` | UNIT_PRICE 변화율 ≥ w/c | UNIT_PRICE p0,p1 | 同(미정) | Δp, 상위 feed_type | costed 행 0 |
| `feed.consumption_increased` | FEED_QTY_CHANGE ratio ≥ w/c | FEED_QTY p0,p1 | 同(미정) | ΔQ, ratio | 어느 기간 no_data |
| `feed.mix_changed` | max_i |Δs_i| ≥ w/c | MIX_SHARE p0,p1 | 同(미정) | Δs_i 상위 3 | feed_type 전부 UNSPECIFIED |
| `feed.cost_incomplete` | coverage < 100% (data quality) | uncosted_rows, coverage | severity **INFO 고정**(정책 아님 — 품질 신호) | coverage, uncosted_rows | 행 0 |
| `fcr.unavailable` | FCR INSUFFICIENT 인데 그룹/사료는 존재 | withheld reason | INFO 고정 | reason(no_gain/no_head_out/attribution_missing) + 결측 그룹 수 | 코호트도 사료도 0 (no_data 는 finding 아님) |
| `fcr.high` (기존) | 기존 룰 그대로 | FCR | operational_defaults 3.0/3.3 (`CODE_CURRENT`) | 기존 | 기존 |

계약: finding 은 F2 결과(값+provenance)만 읽는다. AI 는 finding 을 만들지 않는다. 임계값 4건은 `rule_enabled=false` 로 등록 → APPROVED 결재 후 값 seed (§12).

---

## 14. 기존 KPI engine 재사용 경계 — 판정 **B**

| 기준 | A(포함) | B(별도 도메인 + 정책 재사용) | C(독립) | 코드 근거 |
|---|---|---|---|---|
| calculation semantics | 사료는 이벤트 KPI(교배·분만·이유)와 입력 모델·분모가 다름 | ✓ 순수 함수 모듈 이미 분리(PR #2 feed_metrics) | ✓ | `build_herd_kpis` 는 700줄 단일 함수 — 확장 시 회귀 면적 |
| input model | feed_records·finisher_groups vs sows/events | ✓ | ✓ | §4 |
| time semantics | CALENDAR + GROUP_LIFECYCLE 혼재 | ✓ | ✓ | §9 |
| country policy | 재사용 필수 | ✓ | ✗ | §12 — C 는 정책을 두 벌 만든다 |
| availability/status | KpiStatus·assembler 재사용 | ✓ | ✗ | §7 |
| benchmark | FCR 만 | ✓ | ✗ | E8 |
| worker scheduling | snapshot 컬럼 fcr 만 존재. feed 스냅샷은 V1 범위 밖(요청 시 계산 + 30s 캐시 관례) | ✓ | — | `jobs/kpi.py` |
| API serving | 별도 라우터(`/feed-records` 확장) | ✓ | ✓ | §2 |
| testability | 순수 함수 + 코호트 동치 테스트(PR #2) | ✓ | ✓ | `test_feed_cohort.py` |

→ **B**. FCR 은 두 엔진이 같은 값을 내야 하므로 동치 테스트(PR #2 존재)를 계약으로 유지하고, 장기적으로 kpi_service 의 FCR 계산을 feed 엔진 호출로 교체하는 것은 F2 이후 별도 항목.

---

## 15. 사람 결정 필요 (F1/F2 를 막는 것과 막지 않는 것)

| # | 결정 | F1/F2 착수 | 근거 |
|---|---|---|---|
| UNRESOLVED-1 | `quantity_kg` 의미(급이/소진/입고) — 입력 UX 라벨 확정 또는 PHASE0 실데이터(결재 5) | **막지 않음** — `quantity_basis=AS_RECORDED` 로 계약, 산식 버전에 명시 | E12 A1 |
| UNRESOLVED-2 | feed_type canonical 어휘(선택지화) | 막지 않음 — normalized key | E6 |
| UNRESOLVED-3 | FCR benchmark value_scale (D-13) | 막지 않음 — 벤치마크 비교는 F3 | E8 |
| D-15 / B-7 | FEED_COST_* 노출·과금 경계 | 막지 않음 — F2 는 계산만, 응답 노출은 F3+결재 | E4·E5·E11 |
| 임계값 4건 | `feed.*` 룰 w/c | 막지 않음 — F2 밖(F3 finding). rule_enabled=false 로 등록 | §13 |
| CONFLICT-1 | report_service 그룹행 FCR(head_in 대체) 정렬 | 막지 않음 — 별도 항목(수정 시 리포트 값 변동 → 릴리스 노트) | §2 |
| 결재 5 | 실데이터 PHASE0 감사 | 막지 않음 — F2 는 합성 fixture 로 검증 가능. **GO/NO-GO(기능 출시)** 는 막음 | E12 |

→ F1/F2(정규화·계산·테스트, 노출 0) 착수에 필요한 사람 결정: **없음**. F3(노출·finding 임계값·표시 단위·과금)은 위 결정 후.
