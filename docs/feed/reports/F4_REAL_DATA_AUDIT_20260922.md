# F4 — Feed Engine V1 실데이터 감사 (2026-09-22)

> READ-ONLY. 프로덕션 DB 세션 0. 대상 = 프로덕션 일일 전체 백업 `pigos-full-20260922-034001.sql.gz`
> (서버 sha256 `bfd6cd41c7d77564…` == 로컬 사본, gzip -t ok) 를 격리 로컬 PG17 컨테이너(`pigos-f4audit`, 포트 5499)에
> 복원해 집계 쿼리만 실행. 개인정보 컬럼 SELECT 0 · 농장 식별은 sha256 마스킹 · 감사 후 사본·컨테이너 삭제.
> 엔진 = branch `feat/feed-engine-v1-core` @ `89530ea` (Codex 리뷰 반영판, backend 1418/0).

## 0. 한 화면

```
DATASET      farms 82 (active 80 · live_customer 40 · internal_reference 42) · sows 141,408 · matings 659,719 · alembic f3c6a8d0b2e4
             ★ feed_records = 0  (soft-delete 포함 0 · audit_log feed 액션 0)  — 프로덕션에 사료 입력이 한 번도 없었다
             finisher_groups = 1 (CLOSED · 체중 없음 · head 50→22 · 사료 0)   piglet_groups = 80 (closed 1 · 양 체중 0)
             kpi_snapshots.fcr non-null 0 / 1,976

ENGINE RUN   80 farms × 12 months = 960 farm-months (2025-10 ~ 2026-09)  실행 오류 0 · 위조 0
             CORE 6 × 960 = INSUFFICIENT no_data 5,760/5,760 · 코호트 5 × 960 = INSUFFICIENT no_cohort 4,800/4,800
             독립 SQL 대조 불일치 0 / 960 · findings 0 (임계값 없는 2종 모두 발화 조건 미충족)

CORE_CALCULATION_VALID   YES   (960 farm-months 에서 엔진 == 독립 SQL, 결측을 0 으로 만들지 않음; 값 케이스는 합성 golden 10/10)
COST_DATA_USABLE         NO    (원가 행 0)
FCR_DATA_USABLE          NO    (적격 코호트 0 / CLOSED 1)
VARIANCE_DATA_USABLE     NO    (적격 기간쌍 0)
```

## 1. 데이터 모집단 (§3)

| 항목 | 값 |
|---|---|
| feed_records total (incl. soft-deleted) | **0** |
| farms / active | 82 / 80 |
| record_date min/max | — (행 없음) |
| quantity NULL/zero/positive/negative | 0 / 0 / 0 / 0 |
| unit_cost NULL/zero/positive | 0 / 0 / 0 |
| feed_type distinct / NULL / blank | 0 / 0 / 0 |
| currency distinct / NULL | 0 / 0 |
| group_id present / missing / unmatched | 0 / 0 / 0 |
| farm_id coverage (farms with ≥1 feed row) | 0 / 80 (0.0 %) — 12개월 창에서도 0 |

대조 규모(사료 외 데이터는 있다): sows 141,408 (internal_reference 141,317 · live_customer 91), matings 659,719 (1995-11 ~ 2026-09-06), farrowings 531,841, weanings 527,094. live_customer 농장 중 최근 12개월 교배 기록 있는 곳 10.
웹 사료 입력 화면(`src/app/(app)/feed/page.tsx`, 2026-06-26 추가)과 API(`/farms/{id}/feed-records`)는 프로덕션 web 이미지(2026-08-26)에 포함돼 있다 — **기능은 있었고 입력이 0** 이다.

## 2. quantity 의미 · feed_type · 통화 · 원가 완전성 (§4–§7)

전부 **표본 0**. 분포·충돌·coverage 표는 만들 수 없다(0 행을 100% 로 적지 않는다). `QUANTITY_BASIS = AS_RECORDED` 는 실측으로 확정도 반증도 되지 않았다 — UNRESOLVED-1 유지.

| 구분 | 실측 |
|---|---|
| quantity 분포 (farm/월/type/group) | 표본 0 → 분류(DATA_ANOMALY 등) 해당 없음 |
| feed_type raw ↔ normalized key 충돌 | 0 (표본 0) |
| 월×농장 coverage 분포 100 / 90–<100 / 50–<90 / >0–<50 / 0% | 0 / 0 / 0 / 0 / **960** (행 없음 = coverage 정의 불가, 엔진은 `no_data`) |
| 통화 single / multiple / missing | 0 / 0 / 0 |

## 3. 코호트 / FCR eligibility (§8–§9)

| | 값 |
|---|---|
| CLOSED finisher groups | 1 |
| FCR_ELIGIBLE | 0 (0.0 %) |
| MISSING_WEIGHT | 1 (primary) |
| MISSING_FEED | 1 (동일 그룹, secondary) |
| MISSING_HEAD | 0 |
| ATTRIBUTION_MISSING | — (사료 0) |
| piglet_groups | 80, closed 1, 양 체중 0 → 코호트 후보 아님(V1 은 finisher 만) |

보간 없음. 이 비율(0 %)이 제품 판단 자료다.

## 4. Legacy comparison (§10)

실데이터에서 계산 가능한 그룹 0 → EXACT_MATCH/ROUNDING_ONLY 0/0. 구조적 차이는 테스트로 고정:

| 항목 | 분류 | 근거 |
|---|---|---|
| kpi_service:443-449 FCR 분자 조인이 체중·head_out 조건 없이 CLOSED 전체를 합산 → 부적격 그룹 사료가 분자에만 들어가 FCR 상승 | **BUG (legacy)** — 엔진은 정정, kpi_service 미수정 | `test_cohort_feed_numerator_uses_the_same_eligible_groups_as_the_denominator` (엔진 1.0 vs legacy 12.69 고정) |
| report grow-finish: open 그룹 head_in 대체 | EXPECTED_SEMANTIC_DIFFERENCE (CONFLICT-1) | `test_characterization_legacy_report_uses_head_in_for_open_groups_engine_does_not` |
| cost-summary: 부분원가를 값으로 노출 | EXPECTED_SEMANTIC_DIFFERENCE | unit `test_partial_cost_is_evidence_not_a_cost` |
| UNEXPECTED_DIFFERENCE | 0 | — |

## 5. CORE 6 실데이터 실행 + 독립 대조 (§11)

`api/scripts/feed_engine_real_data_audit.py` (복원본 URL 만 허용, 프로덕션 호스트 패턴 거부). 엔진 `compute_feed_metrics` ↔ 독립 SQL(`count/sum/filter` 직접 계산) 대조:

```
farm_months 960 · engine errors 0 · mismatches 0
FEED_QTY / FEED_COST / FEED_UNIT_PRICE / FEED_MIX_SHARE / *_CHANGE   → INSUFFICIENT no_data  (SQL rows=0 과 일치, 0 값 생성 없음)
FCR / FEED_COST_PER_PIG / FEED_COST_PER_KG_GAIN / FEED_QTY_PER_HEAD / ADG → INSUFFICIENT no_cohort (적격 그룹 0 과 일치)
findings 0
```

값 경로(ACTUAL/DERIVED)는 실데이터로 검증할 수 없었다 → 합성 golden(§6)이 대신한다. 이 한계를 숨기지 않는다.

## 6. Golden cases (§12) — 실데이터 0, 합성 fixture 로 대체

| 사례 | 실데이터 | 합성 테스트 (독립 손계산 기대값) | 결과 |
|---|---|---|---|
| complete normal | 없음 | `TestCore.test_normal_case` (600 kg · 1000.00 · 1.6667) | PASS |
| zero quantity | 없음 | `test_zero_quantity_row_no_divide_by_zero` | PASS |
| missing cost | 없음 | `test_no_costed_rows` | PASS |
| partial cost | 없음 | `test_partial_cost_is_evidence_not_a_cost` (partial 400, coverage 2/3·0.5) | PASS |
| multiple feed types | 없음 | `test_mix_share_*` · `test_unknown_feed_type_*` | PASS |
| previous period missing | 없음 | `test_previous_missing_is_insufficient_not_zero_percent` | PASS |
| previous quantity zero | 없음 | `test_previous_zero_does_not_hide_division` | PASS |
| attribution missing | 없음 | `test_attribution_missing_vs_no_data` | PASS |
| FCR eligible | 없음 | integration `test_vertical_slice_matches_legacy_cohort_and_kpi_fcr` (2.7) | PASS |
| FCR unavailable | **실데이터 1건**(CLOSED·체중 없음 → no_cohort) + `test_denominators` | PASS |

## 7. Variance (§13)

적격 기간쌍 0 / 부적격 960 (사유 전부 `no_data`). 항등식 검증은 합성 200 랜덤 + 손계산으로만.

## 8. Findings 분류 (§14)

| 분류 | 내용 |
|---|---|
| **PRODUCT_DECISION** | 사료 입력 기능이 3개월 프로덕션에 있었고 입력 0. Feed Intelligence 의 병목은 산식이 아니라 **입력 채택**이다. GO/NO-GO 는 PHASE0 임계(`docs/feed/PHASE0_AUDIT_PLAN.md` G-A ≥30 %)에 대입하면 **NO-GO(0 %)** — 산식 착수 금지가 아니라 "입력 경로 먼저" 판정 |
| **DATA_QUALITY** | 유일한 finisher_group 이 체중·사료 없이 당일 CLOSED(head 50→22) — 테스트성 입력으로 보임(추정, UNKNOWN 병기) |
| **SCHEMA_GAP** | 변화 없음(F0 §4 그대로): quantity 의미·재고·폐사체중·live/carcass·group_id FK·feed_type 어휘 |
| **EXPECTED_LIMITATION** | CLOSED 이나 부적격(체중 없음)인 그룹은 코호트 집계에서 빠져 `no_cohort` 로만 보이고 `fcr.unavailable` finding 이 뜨지 않는다 — "못 냈다" 를 구분하려면 Cohort 에 `closed_total` 카운트가 필요(F4-1 후보, 엔진 버그 아님) |
| **ENGINE_BUG** | 이번 감사 중 신규 0. Codex 리뷰 4건은 감사 전 수정 완료(`89530ea`) |
| **LEGACY_DIFFERENCE** | kpi_service 분자 집합 BUG · report head_in · cost-summary 부분원가 (§4) |
| **UNKNOWN** | quantity_kg 의미(표본 0) |

## 9. 코드 변경 · 테스트

```
코드   api/scripts/feed_engine_real_data_audit.py (감사 하네스, 읽기 전용, 프로덕션 URL 거부) — 신규
       엔진 변경: 감사 중 0 (Codex 반영은 89530ea, 감사 전)
테스트 변경 0 (하네스는 스크립트) · 재실행: unit 46 · feed integration 13 · backend full 1418 passed (89530ea)
```

## 10. 정리

사본 `C:\tmp\f4\pigos-full-20260922-034001.sql.gz` 및 컨테이너 `pigos-f4audit` 은 감사 종료 후 삭제(개인정보 포함 덤프를 로컬에 남기지 않는다).
