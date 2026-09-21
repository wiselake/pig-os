# Feed Engine V1 — Implementation Map (F1 / F2)  · 2026-09-21

> 짝 문서 `FEED_ENGINE_V1_CANONICAL_SPEC.md` 의 계약을 파일 단위로 내린 것. 여기 없는 파일은 F1/F2 에서 만지지 않는다.
> 전제: base 는 **PR #2(safety) 반영 후 main** 이어야 한다 — `engine/feed_metrics.py`·`feed_service.load_feed_cohort`·`test_feed_cohort.py` 가 PR #2 에만 있다. main 단독 base 면 그 세 파일을 먼저 cherry-pick(테스트 포함, production 노출 0)한다.

## 1. 순서

```
F1  INPUT NORMALIZATION     feed_records → FeedInput(정규화·품질 플래그·스코프·코호트)      DB 읽기만 · 노출 0
F2  CALCULATION ENGINE      FeedInput → FeedMetricResult(값·provenance·reason·evidence)     순수 함수 · 노출 0
F3  (범위 밖)               API 노출 · finding 룰 활성 · 표시 단위 · 과금 경계 · 리포트 FCR 정렬   ← 사람 결정 후
```

## 2. 파일 단위 경로

### NEW

| 파일 | why | responsibility | dependency | risk |
|---|---|---|---|---|
| `api/app/engine/feed/__init__.py` | feed 도메인 패키지(B) | re-export | — | 낮음 |
| `api/app/engine/feed/normalize.py` (F1) | 스펙 §4·§8 정규화 | `normalize_rows(rows, farm_currency) -> FeedInput`: feed_type key(lower·trim·공백1) · currency NULL→farm · 스코프 분류(SOW/GROUP/BUILDING/FARM_UNATTRIBUTED) · 품질 플래그(zero_qty·zero_cost·orphan_group·currency_mixed) · Decimal 변환. **DB·시계 접근 0** | `dataclasses`, `decimal` | 낮음 — 순수 함수 |
| `api/app/engine/feed/types.py` (F1) | 계약 타입 한 곳 | `FeedRow`(정규화 행) · `FeedInput`(기간·행·코호트·farm_currency) · `Provenance = Literal["ACTUAL","DERIVED","INSUFFICIENT"]` · `FeedMetricResult{metric_id, value, unit, provenance, reason, evidence, formula_version}` · reason 상수(소문자 어휘, 스펙 §7) | — | enum 중복 금지 — `KpiStatus` 는 재사용, provenance 만 신설 |
| `api/app/engine/feed/metrics.py` (F2) | CORE 6 산식 | `feed_qty(inp)` · `feed_cost(inp)` · `feed_unit_price(inp, by_type=False)` · `feed_mix_share(inp)` · `feed_qty_change(p0,p1)` · `feed_cost_change(p0,p1)` — 각각 `FeedMetricResult`. 반올림 스펙 §5. `FORMULA_VERSION="FEED_ENGINE.v1"` + `quantity_basis="AS_RECORDED"` 를 evidence 에 실음 | `types.py`, 기존 `engine/feed_metrics.py`(코호트 3식 재사용·이동 금지) | 중간 — cost complete 규칙(부분합은 evidence 만) |
| `api/app/engine/feed/variance.py` (F2) | 스펙 §11 항등식 | `decompose_cost_change(p0: FeedInput, p1: FeedInput) -> VarianceResult{price, volume, mix, total, residual==0}` · 전제 미충족 시 INSUFFICIENT | `metrics.py` | 중간 — 신규/소멸 feed_type edge |
| `api/app/engine/feed/status.py` (F2) | 스펙 §7 상태 조립 | `to_kpi_status(results, findings) -> dict[str, KpiStatus]` — `assemble_kpi_status` 를 feed metric 집합에 대해 호출(DASHBOARD_POLICY_KPIS 밖) | `services/kpi_status_assembler.py` | 낮음 |
| `api/app/services/feed_engine_service.py` (F1) | DB → FeedInput 로더 | `load_feed_input(db, farm, start, end) -> FeedInput`: feed_records 기간 조회(soft-delete 제외) + `feed_service.load_feed_cohort` 재사용 + `normalize_rows`. **라우터 미연결(F3)** | `feed_service`, `normalize.py` | 낮음 — 읽기 전용 |
| `api/tests/unit/test_feed_normalize.py` (F1) | 정규화 계약 | 스펙 §4·§8 표 1행 = 테스트 1건 | — | — |
| `api/tests/unit/test_feed_engine_metrics.py` (F2) | CORE 산식 + 불변식 | §3 테스트 계약 T-N/T-Z/T-M/T-P/T-U/T-C/T-R/T-D/T-I | — | — |
| `api/tests/unit/test_feed_variance.py` (F2) | 항등식 | T-V | — | — |
| `api/tests/integration/test_feed_engine_service.py` (F1) | 로더 ↔ 코호트 동치 | `load_feed_input().cohort == load_feed_cohort()` · FCR == `build_herd_kpis["FCR"]` (PR #2 `test_feed_cohort` 확장) | db fixture | — |

### MODIFY (최소)

| 파일 | 변경 | why | risk |
|---|---|---|---|
| `api/app/engine/feed_metrics.py` (PR #2) | reason 상수를 소문자 어휘로 매핑하는 어댑터 1함수 추가(`withheld_to_reason`). 산식·상수 이름은 유지(테스트 호환) | 스펙 §7 어휘 통일 | 낮음 |
| `api/app/services/feed_service.py` (PR #2) | `load_feed_cohort` 는 그대로. `list_feed_records_in_period(db, farm_id, start, end)` 1함수 추가(정렬·soft-delete 동일) | F1 로더 입력 | 낮음 |
| `api/app/engine/rules/feed.py` (신규지만 F3) | `feed.*` 룰 4 + `fcr.unavailable` 등록, **`rule_enabled=false`** — F2 에서는 파일만 두고 등록하지 않는다 | 스펙 §13 | F3 |

### DO NOT TOUCH (F1/F2)

| 파일 | 이유 |
|---|---|
| `api/app/services/kpi_service.py` (FCR/ADG 428-449, 534-535) | canonical 코호트 정의 원본. 동치 테스트의 기준. 교체는 F2 이후 별도 |
| `api/app/services/report_service.py` (355-390, 916-1045) | CONFLICT-1 정렬은 별도 항목 — 리포트 값이 바뀌므로 릴리스 노트 필요 |
| `api/app/routers/**` · `api/app/schemas/feed.py` 응답 | 노출 0 (D-15/B-7·Entitlement 결재 전) |
| `api/app/jobs/**` | 사료 스냅샷은 V1 범위 밖. `_WITHHELD_FIELDS` 건드리지 않음 |
| `api/app/db/models/**` · `alembic/**` | 마이그레이션 0 (재고·단가 마스터·quantity 의미 컬럼은 UNRESOLVED 후) |
| `api/app/db/*_seed.py` · `operational_defaults_seed.py` | 임계값·벤치마크 seed = 정책 결재 대상 |
| `api/app/engine/rules/grow_finish.py` (`fcr.high`) | 기존 룰 유지 |
| `src/**` · 모바일 두 저장소 | F3 |

## 3. 테스트 계약 (F1/F2 완료 조건)

표기: 입력 → 기대. 전부 합성 fixture(`Decimal` 문자열), DB 없음(unit). 실데이터 0.

| ID | 케이스 | 입력 | 기대 |
|---|---|---|---|
| T-N1 normal | 3행 qty 100/200/300, cost 1.0/1.5/2.0 USD | FEED_QTY 600 kg ACTUAL · FEED_COST 1000.00 USD ACTUAL · UNIT_PRICE 1.6667 DERIVED |
| T-Z1 zero | 기간 내 행 0 | FEED_QTY INSUFFICIENT no_data (0 아님) |
| T-Z2 zero | qty 0 행 1 + 정상 행 | 값 포함 · flag zero_qty · FEED_QTY 는 정상 행 합 |
| T-Z3 zero | unit_cost 0 행 | costed 로 계수 · flag zero_cost · cost 기여 0 |
| T-M1 missing | unit_cost NULL 1행 + costed 2행 | FEED_COST INSUFFICIENT cost_incomplete · evidence.partial_cost=Σ(costed) · coverage=2/3(행)·kg 가중 |
| T-M2 missing | costed 0 | FEED_COST no_cost · UNIT_PRICE no_cost |
| T-P1 partial | 코호트 그룹 2 중 1 만 사료 귀속 | FCR 분자 = 귀속분만 · evidence.unattributed_share · flag |
| T-P2 partial | group_id 가 삭제/부재 그룹 | orphan_group flag · 코호트 제외 |
| T-E1 estimated | (구성 불가) | **어떤 입력에도 provenance ESTIMATED 가 나오지 않는다** — 전 metric 전수 (T-I3) |
| T-U1 unit | 같은 입력 farm.unit_system METRIC vs IMPERIAL | FeedMetricResult 동일(kg). 표시 변환은 여기 없음 |
| T-C1 currency | currency NULL 행 + farm.currency KRW | 통화 집합 {KRW} · 정상 |
| T-C2 currency | USD 행 + KRW 행 | FEED_COST INSUFFICIENT currency_mixed · FEED_QTY 는 정상(통화 무관) |
| T-C3 currency | 두 기간 통화 다름 | FEED_COST_CHANGE currency_mixed |
| T-B1 period | record_date = start / end 경계 | 포함(닫힌 구간) · end+1 제외 |
| T-B2 period | p0 길이 ≠ p1 길이 | *_CHANGE INSUFFICIENT (context_missing) |
| T-G1 group | 그룹 end_date = period.end | 코호트 포함 · start−1 제외 |
| T-G2 group | open 그룹(end_date NULL) 에 사료 귀속 | 코호트 제외 · **head_in 대체 금지** (CONFLICT-1 ② 불허) |
| T-G3 group | 그룹 전생애 사료 중 record_date 가 기간 밖 | FCR 분자에 포함(GROUP_LIFECYCLE) · FEED_QTY(CALENDAR) 엔 미포함 — 두 값 다름을 단언 |
| T-D1 denominator | gain ≤ 0 (exit ≤ entry) | FCR no_gain · COST_PER_KG_GAIN no_gain |
| T-D2 denominator | head_out 0 | COST_PER_PIG no_head_out · QTY_PER_HEAD no_head_out |
| T-F1 FCR unavailable | 그룹 있으나 체중 NULL | 코호트 0 → no_cohort (no_data 와 구분) |
| T-R1 rounding | 1/3 류 | FCR 3자리 · cost 2 · unit price 4 · share 4 — 반올림은 결과 생성 시 한 번 |
| T-K1 country isolation | 국가 KR/US/BR 동일 입력 | FeedMetricResult 바이트 동일(산식에 국가 없음) |
| T-I1 determinism | 같은 FeedInput 2회 · 행 순서 셔플 | 동일 결과 |
| T-I2 invariant | 분모 없음 | 비율 metric 값 None + reason — 0 이나 평균으로 채우지 않음 |
| T-I3 invariant | 전 metric | provenance ∈ {ACTUAL, DERIVED, INSUFFICIENT} — ESTIMATED 0건 |
| T-I4 invariant | display unit 변경 | canonical 결과 불변 |
| T-V1 variance | 2 feed_type, 두 기간 complete | price+volume+mix == ΔC (Decimal 정확 비교, 잔차 0) |
| T-V2 variance | feed_type 신규/소멸 | 항등식 유지 |
| T-V3 variance | 한 기간 cost_incomplete | decomposition 전체 INSUFFICIENT (부분 분해 없음) |
| T-S1 status | INSUFFICIENT 결과 | `KpiStatus(status="insufficient", reason=<사유>)` — 기존 assembler 경유 |
| T-EQ1 integration | 코호트 로더 | `load_feed_input().cohort` == `load_feed_cohort()` · FCR == `build_herd_kpis["FCR"]` (PR #2 동치 테스트 유지) |
| T-X1 scan | `engine/feed/**` | DB·datetime.now·random import 0 (순수성 소스 스캔) |

## 4. F2 이후 별도 항목 (F3 큐)

```
F3-1  API 노출     GET /farms/{id}/feed-metrics?start&end  — D-15/B-7·Entitlement 결재 후. GLOBAL_HIDDEN 정책 행 신설 필요
F3-2  finding 활성  feed.* 임계값 4건 APPROVED → operational_defaults seed → rule_enabled=true
F3-3  표시 단위     IMPERIAL lb/tonne 변환 (웹·모바일 프레젠테이션)
F3-4  CONFLICT-1   report_service 그룹행 FCR 을 canonical 코호트 정의로 정렬 (리포트 값 변동 고지)
F3-5  quantity 의미 UNRESOLVED-1 확정 → quantity_basis 승격 + FORMULA_VERSION bump
F3-6  feed_type 어휘 UNRESOLVED-2 → 입력 선택지 + code_mappings FEED_PRODUCT
F3-7  실데이터 GO/NO-GO  결재 5 → PHASE0 감사 → 출시 판정
```
