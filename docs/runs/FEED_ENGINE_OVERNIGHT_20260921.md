# Feed Engine V1 — Overnight build handover (2026-09-21)

> F0 정본(`docs/feed/FEED_ENGINE_V1_CANONICAL_SPEC.md` · `FEED_ENGINE_IMPLEMENTATION_MAP.md`) 을 코드로 옮긴 기록.
> 불변: PROD deploy 0 · migration 0 · DB write 0 · seed 0 · cron/worker 0 · frontend/mobile 0 · AI 0 · 법무/consent/G-3/rate limit/auth 0.

## 0. 한 화면

```
LEVEL                 3  (F1 + CORE 6 + service slice + full regression + CONDITIONAL 4 + variance + F3 safe)
branch                feat/feed-engine-v1-core   base main fc96efc   HEAD <see git>
commits               9  (F0 docs cherry-pick · PR #2 feed 3건 cherry-pick(api/ only) · F1 · F2 · F3-safe · tests · F2.5)
files                 17 (+2152 / −1)   — 전부 api/app/engine/feed/**, feed_metrics.py, feed_service.py, schemas/feed.py, feed_engine_service.py, tests, docs/feed
tests                 unit 45 + purity 2 · integration 4 + PR #2 코호트 6 · feed_metrics 10 → backend full 1414 passed · 1 skipped (baseline main 1349) · ruff clean · alembic 단일 head
PR #2 dependency      PATH B — 8c8519c · bb04b57 · 784fcd2 를 api/ 만 cherry-pick (docs/FEATURE_REGISTRY·HUMAN_INPUT_QUEUE hunk 제외, 트레일러에 출처 기록). PR #2 자체는 merge 안 함
production            changed NO
```

## 1. 구현 범위

| 계층 | 파일 | 상태 |
|---|---|---|
| F1 types | `api/app/engine/feed/types.py` | Period · FeedRow · Cohort · FeedInput · FeedMetricResult(계약 강제) · reason 어휘 · QUANTITY_BASIS=AS_RECORDED |
| F1 normalize | `api/app/engine/feed/normalize.py` | feed_type key/raw · 통화 폴백 · 스코프 · 품질 플래그 · 닫힌 기간 · Decimal via str |
| F2 CORE | `api/app/engine/feed/metrics.py` | FEED_QTY · FEED_COST · FEED_UNIT_PRICE · FEED_MIX_SHARE · FEED_QTY_CHANGE · FEED_COST_CHANGE |
| F2 CONDITIONAL | 同 (legacy `feed_metrics.py` REUSE) | FCR · FEED_COST_PER_PIG · FEED_COST_PER_KG_GAIN · FEED_QTY_PER_HEAD. ADG = 참조만(재계산 안 함, SPEC §5) |
| F2 variance | `api/app/engine/feed/variance.py` | PRICE+VOLUME+MIX = ΔC (Fraction 정확) · POPULATION NOT_SUPPORTED |
| F3 safe | `api/app/engine/feed/status.py` | `feed.cost_incomplete` · `fcr.unavailable` (INFO, 임계값 0) · `to_kpi_status` (assembler 재사용, 정책 없으면 no_policy) |
| F2.5 service | `api/app/services/feed_engine_service.py` | `load_feed_input` · `compute_feed_metrics` — 라우터 0 |

미구현(의도): API 노출 · 임계값 finding 4건(feed.cost_increased 등, 결재) · 표시 단위 변환 · ADG 재계산 · CONFLICT-1 정렬.

## 2. 불변식 (테스트로 고정)

| 불변식 | 테스트 |
|---|---|
| 같은 입력 → 같은 결과 · 행 순서 무관 | `TestInvariants.test_same_input_same_output_and_row_order_independent` |
| ESTIMATED 0건 · value 없음 ⇔ INSUFFICIENT+reason | `test_no_estimated_provenance_anywhere` · `TestResultContract` |
| missing ≠ 0 (행 0 = no_data · unit_cost NULL = 미입력 · 코호트 0 = no_cohort · 귀속 0 = attribution_missing) | `test_no_rows_is_no_data_not_zero` · `test_no_cohort_is_not_no_data` · `test_attribution_missing_vs_no_data` |
| 부분 원가 → evidence 만, 값 아님 | `test_partial_cost_is_evidence_not_a_cost` |
| 분모 0 → 비율 없음 (no_gain·no_head_out·no_cost, prev 0 → rate None) | `test_denominators` · `test_previous_zero_does_not_hide_division` |
| Σ exact share = 1 · Σ type kg = total · priced+unpriced = total | `test_mix_share_sums_to_one_exactly_before_rounding` · `test_type_quantities_sum_to_total_and_priced_plus_unpriced` |
| PRICE+VOLUME+MIX == ΔC (정확, 200 랜덤) | `TestVariance.*` |
| 국가·표시 단위가 계산에 들어오지 않음 | `test_country_and_display_unit_do_not_enter_calculation` |
| 달력 ≠ 그룹 전생애 | `test_calendar_and_lifecycle_are_different_quantities` · integration `test_vertical_slice_*` |
| 엔진 FCR == kpi_service FCR == legacy cohort | integration `test_vertical_slice_matches_legacy_cohort_and_kpi_fcr` |
| 엔진에 DB·시계·난수·env import 0 | `test_feed_engine_purity.py` |
| 임계값·등급 단어 0 | `test_no_threshold_or_grade_words_in_feed_engine` |

## 3. Legacy 차이 (수정 안 함)

| 항목 | 분류 | 고정 테스트 |
|---|---|---|
| `report_service.build_grow_finish_rows`: open 그룹(end_date NULL) 에 head_in 으로 gain 을 만들어 fcr 산출 / 엔진·kpi_service: no_cohort | **EXPECTED_SEMANTIC_DIFFERENCE** (F0 CONFLICT-1 → F3-4) | `test_characterization_legacy_report_uses_head_in_for_open_groups_engine_does_not` |
| `report_service.get_cost_summary`: 부분 원가 합 + coverage 를 값으로 노출 / 엔진: INSUFFICIENT(cost_incomplete) + evidence.partial_cost | EXPECTED_SEMANTIC_DIFFERENCE (F0 §5 결정) | unit `test_partial_cost_is_evidence_not_a_cost` |
| `feed_metrics` 유보 코드 대문자(NO_GAIN) / 엔진 소문자(no_gain) | 어댑터 `withheld_to_reason` | `test_withheld_code_mapping` |

BUG 분류 0 · UNRESOLVED 는 F0 §15 그대로.

## 4. SCHEMA_GAP (마이그레이션 만들지 않음)

```
quantity_kg 의미 컬럼 없음            → QUANTITY_BASIS = AS_RECORDED 로 계약 (UNRESOLVED-1)
재고 경계 없음                        → 기간 소진량 = 기록량. FEED_INVENTORY DEFERRED
폐사 체중 없음                        → gain 은 출하두 기준, 폐사 증체 미반영 (evidence 에 기재 안 함 — 산식 문서 §6)
출하 live/carcass 구분 없음           → exit weight 기준 = 입력 라벨
feed_records.group_id FK 없음         → 로더가 orphan 판정(orphan_group 플래그)
feed_type 자유 텍스트                 → normalized key + raw 보존
```

## 5. 다음 (F3, 사람 결정 뒤)

```
F3-1  API 노출 GET /farms/{id}/feed-metrics     D-15/B-7 + Entitlement 결재 · GLOBAL_HIDDEN 정책 행
F3-2  feed.* 임계값 4건 APPROVED → seed → rule_enabled
F3-3  IMPERIAL lb/tonne 표시 변환 (프레젠테이션)
F3-4  CONFLICT-1 리포트 정렬 (값 변동 고지)
F3-7  결재 5 → PHASE0 실데이터 감사 → 출시 GO/NO-GO
+     PR #2 는 main fc96efc 기준 재갱신 필요(behind 4) — 이 브랜치와 PR #2 는 feed 3커밋을 공유(cherry-pick, patch-id 동일)
```
