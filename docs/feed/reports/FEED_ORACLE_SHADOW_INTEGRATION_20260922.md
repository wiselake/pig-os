# Feed × PigPlan Oracle — Shadow Integration (F4-1 실데이터 검증, 2026-09-22)

> Oracle(READ ONLY) → `PigPlanFeedDeliverySource` → `PigPlanFeedDeliveryRow` → classify → `FeedInput(DELIVERED, KRW)` → Feed Engine → 감사 JSON.
> **PigOS DB write 0 · Oracle write 0 · feed_records INSERT 0 · 배포 0.** 이번 단계는 ETL 이 아니라 "기존 실데이터로 엔진이 맞는가" 다.
> 근거: `PIGPLAN_ORACLE_FEED_PREFLIGHT_20260922.md` · `../FEED_ENGINE_V1_CANONICAL_SPEC.md` · `F4_REAL_DATA_AUDIT_20260922.md`.
> 산출: `SHADOW_ORACLE_FEED_20260922.json`(집계·마스킹 id 만) · `api/app/harvest/pigplan_feed_delivery.py` · `api/scripts/feed_oracle_shadow_run.py`.

---

## 0. 한 화면

```text
SOURCE        TM_ETC_TRADE  ACCOUNT_CD='410002' AND GAIN_YN='M'   quantity_basis = DELIVERED   currency = KRW(소스 설정 근거)
EXTRACTION    9농장(직접 매핑) × 12 완료월(2025-09~2026-08) + 부분월 2026-09(별도)   5,339행 → 수량 ACCEPTED 5,077 · EXCLUDED 262
CORE          수량 가용 farm-month 89 / 108 · 원가 COMPLETE 62 · PARTIAL 14 · MISSING 13 · 행 없음 19
RECON         Oracle 독립 SQL 대조 89 farm-month: 수량 0 · 원가 0 · 단가 0 · 구성비 0 불일치
CHANGE        같은 길이 기간쌍 18 → 수량 13 값(13/13 손계산 일치) · 원가 9 값(9/9) · 나머지 no_data/partial 로 정직하게 유보
              ★ 달 길이가 다른 쌍 81 은 엔진이 context_missing 으로 거부 — F0 "같은 길이" 규칙. 버그 아님, 계약 결정 필요
VARIANCE      적격 9쌍 전부 PRICE+VOLUME+MIX = TOTAL (9/9)
GOLDEN        실데이터 8/8 PASS (complete·partial·missing·multi-type·consecutive·qty change·cost change·variance)
ENGINE        버그 0 · 의미 변경 1 (QuantityBasis 추가) · 기존 AS_RECORDED 경로 무변경 · 1437 passed
FINAL         ORACLE_FEED_SOURCE_VALID YES · DELIVERED_CORE_VALID YES · READY_FOR_PERSISTENCE_DESIGN YES
NEXT STEP     PERSISTENCE DESIGN
```

## 1. SOURCE — 세 결정의 근거

| 결정 | 값 | 근거 (이번 세션 실측) |
|---|---|---|
| D-FEED-01 quantity_basis | **DELIVERED** — 입고/구매/배송량. CONSUMED·FED·USED 라 부르지 않는다 | `GAIN_YN` 컬럼 코멘트 "입고기준(M:경영 입고기록)" · 거래처 80 % · 배송 단위 kg 분포. PigOS 수기 UI(AS_RECORDED "급여")와 **섞지 않는다** — 엔진이 basis 불일치 쌍을 거부한다(§6) |
| D-FEED-02 currency | **KRW** — `source_currency` 를 adapter 계약에 고정. `currency_evidence_status = CONFIRMED_BY_SOURCE_CONFIG` | 소스 설정: `TC_CODE_SYS` pcode 943 = {943001 **KRW** ↔ 942001 Korea(ko), 943002 USD ↔ English, 943003 VND ↔ Vietnam} · `TA_FARM.COUNTRY_CODE='KOR'` 3,224/3,224 (9농장 전부). 규칙: COUNTRY_CODE ≠ KOR 이면 그 농장 원가는 `BLOCKED_CURRENCY_EVIDENCE`(수량은 계속). **PigOS farm.currency fallback 금지** — 프로덕션 42 PP- 농장의 currency 는 합성값(KRW 0/42) 이라 쓰면 곧 오표기다 |
| D-FEED-03 ACCOUNT_CD 410002 | `source_filter_status = EVIDENCE_SUPPORTED_LABEL_UNVERIFIED` | 코드표(`TC_CODE_SYS`·`TC_CODE_JOHAP`) 어디에도 없음. **추가 증거**: 소스 스키마 트리거 `TRG_TM_FEED_01` 16행 `AND ACCOUNT_CD = '410002' -- 계정코드 : 사료비` (stored code, 사료 마스터 변경 시 이 계정의 거래행을 갱신). 로컬 저장소엔 PigPlan 앱 소스 없음. "공식 사료 계정" 이라고 쓰지 않는다 — 라벨 승격은 PigPlan 담당자 확인 뒤 |

## 2. EXTRACTION

```text
farms      manifest 42 (PP-{farm_no}, 프로덕션 read-only 확인 42/42 존재 · pigplan_migration 42/42)
           → 창 안 사료행 보유 9 (fuzzy 매칭 0)
period     완료월 2025-09-01 ~ 2026-08-31 (12) · 부분월 2026-09-01 ~ 09-22 (3농장 121행 — 계산·대조에서 분리)
rows       5,339  →  수량 ACCEPTED 5,077 · EXCLUDED 262
   EXCLUDED   INACTIVE_SOURCE_ROW 258 · NON_POSITIVE_QUANTITY 4 · INVALID_DATE 0 (창 안엔 불량 날짜 없음)
   원가       ACCEPTED 4,254 (직접 단가 3,188 + 총액/kg 파생 1,094) · INSUFFICIENT 823 (COST_INCOMPLETE 795 · COST_IDENTITY_MISMATCH 28) · EXCLUDED 0
```

원가 파생(`COST_DERIVED_FROM_TOTAL`)의 타당성: preflight 는 `FPER_PRICE IS NULL` 만 봤는데 실제로는 **`FPER_PRICE = 0` + `TOTAL_PRICE > 0`** 행이 1,094 있다. 파생 단가 분포 p05/p50/p95 = 535 / **579** / 679 vs 직접 단가 519 / **580** / 3,005 — 중앙값이 일치해 총액/kg 가 kg 당 단가와 같은 의미임을 실데이터가 뒷받침한다. 보정이 아니라 항등식(§preflight 96 %) 의 역산이다. 직접 단가 p95 3,005 는 378행·kg 0.73 %·소량(kg p50 300)·항등 372/378 성립 → 고가 소량 제품(자돈 사료 추정, 확정 안 함) = `VALID_OUTLIER` 후보, `UNKNOWN` 병기. 보정 없음.

## 3. MAPPING

```text
mapped   9/9   (farm_code 'PP-{FARM_NO}' — harvest_import.py:368 · 프로덕션 42/42 존재)
failed   0
group    0     GRP_NO → TJ_GAIN_GRP 조인 0.3 % (preflight) — 이 소스로 FCR 계열은 계산하지 않는다 (엔진이 basis_unsupported 로 거부, §6)
```

## 4. CORE (farm × 완료월 = 108)

| | farm-months |
|---|---|
| 수량 가용 (행 ≥1) | **89** |
| 원가 COMPLETE (전 행 단가) | **62** |
| 원가 PARTIAL (일부 단가 → `cost_incomplete`, partial_cost 는 evidence) | 14 |
| 원가 MISSING (`no_cost`) | 13 |
| 행 없음 (`no_data`) | 19 |

농장별 12개월 원가 상태(마스킹 id · C/P/M): 4농장 전월 C · 1농장 전월 M · 나머지 혼합. 수량 12/12 보유 6농장 · 8·5·4개월 각 1.
**preflight 재현**: 직접 단가 기준 농장 프로파일 fully 6 / partially 2 / unpriced 1 — preflight 6/2/1 과 **정확히 일치**. (엔진의 farm-month COMPLETE 판정은 파생 단가를 포함하고 월 단위라 4/4/1 로 다르게 보이는 것이 정상 — 정의가 다르다.)

## 5. RECONCILIATION — 엔진 vs Oracle 집계 SQL (엔진 미경유)

| 축 | 비교 | 불일치 | 허용오차 |
|---|---|---|---|
| FEED_QTY | 89 | **0** | 0.15 kg |
| FEED_COST (ACTUAL 값 또는 partial_cost evidence) | 89 | **0** | 1 KRW |
| FEED_UNIT_PRICE (수량 가중) | 89 | **0** | 0.0006 KRW/kg |
| FEED_MIX_SHARE (단계별 kg) | 89 | **0** | 0.15 kg / 단계 |

독립 SQL 은 분류 규칙(§7 어휘)을 SQL 로 다시 적은 것이라 두 구현이 서로를 검증한다. 단계 어휘 8종 전부 관측(갓돈·젖돈·젖뗀돈·육성돈·비육돈·임신돈·포유돈·기타). 제품명(625종)은 소스 행에 보존, `feed_type` 에 섞지 않았다.

## 6. CHANGE / VARIANCE

```text
연속 완료월 쌍            99 (9농장 × 11)
  달 길이 같은 쌍          18   (12→1월, 7→8월)  → FEED_QTY_CHANGE 13 값 + 5 no_data · FEED_COST_CHANGE 9 값 + 2 no_cost + 2 cost_incomplete + 5 no_data
                               13/13 · 9/9 손계산(cur − prev) 일치 · quantity_basis 전부 DELIVERED · cost_incomplete 가 성공으로 위장한 사례 0
  달 길이 다른 쌍          81   → 엔진 context_missing (F0 §5 "CALENDAR_PERIOD ×2 (같은 길이)")
VARIANCE                  적격 9쌍 (원가 COMPLETE·같은 길이·같은 통화·같은 basis) → PRICE+VOLUME+MIX = TOTAL 9/9 (허용 0.02)
                          비적격 사유: context_missing 81 · no_data 5 · no_cost 2 · cost_incomplete 2
basis 혼합 방어           AS_RECORDED × DELIVERED 쌍 → context_missing + evidence.basis_mismatch (단위테스트로 고정)
```

★ **EXPECTED_LIMITATION → 계약 결정 후보**: 월 단위 실데이터에서 "같은 길이" 규칙은 12쌍 중 2쌍만 통과시킨다. 선택지는 (a) 규칙 유지(월 비교는 30/31일 쌍만) (b) "같은 달력 grain(월↔월)" 허용 (c) 일당 환산 비교. 엔진 버그가 아니므로 여기서 바꾸지 않았다 — F0 개정 항목으로 넘긴다.

## 7. GOLDEN (실데이터 · 마스킹 · 독립 기대값 대조)

| 사례 | farm · month | 행 | 엔진 | 독립 SQL | 상태 |
|---|---|---|---|---|---|
| normal_complete_cost | 42b90a8d7e4c · 2025-09 | 77 | qty 691,900.0 · cost 415,210,100.00 KRW · 단가 600.1013 | 691,900 · 415,210,100 | PASS |
| partial_cost | 349fd35ef703 · 2025-10 | 12 | qty 585,490.0 · cost INSUFFICIENT(cost_incomplete), partial 264,917,590 | 585,490 · 264,917,590 | PASS |
| missing_cost | f3d1d3973c17 · 2025-09 | 68 | qty 875,270.0 · cost INSUFFICIENT(no_cost) | 875,270 · NULL | PASS |
| multiple_feed_types | f3d1d3973c17 · 2025-09 | 68 | 단계 ≥2 · shares Σ=1 | 단계별 kg 일치 | PASS |
| consecutive_months | f3d1d3973c17 · 2025-10 | 81 | 두 달 모두 값 | 일치 | PASS |
| quantity_change | f3d1d3973c17 · 2026-01 (vs 12월) | 71 | 값 = cur − prev | 손계산 일치 | PASS |
| cost_change | 42b90a8d7e4c · 2026-01 | 77 | 값 = cur − prev | 손계산 일치 | PASS |
| variance_eligible | 42b90a8d7e4c · 2026-01 | 77 | total −62,376,690 = price 2,061,353 + volume −62,121,380 + mix −2,316,663 | 항등 | PASS |

허용된 표현만 쓴다: "입고량 증가/감소 · 입고 원가 증가/감소 · 원가 미완". 사료효율·소비 해석은 하지 않는다(§16).

## 8. QUALITY

| reason | 행 | 처리 |
|---|---|---|
| INACTIVE_SOURCE_ROW (USE_YN≠Y) | 258 | EXCLUDED |
| NON_POSITIVE_QUANTITY | 4 | EXCLUDED |
| COST_INCOMPLETE (단가·총액 없음) | 795 | 수량 ACCEPTED · 원가 INSUFFICIENT |
| COST_IDENTITY_MISMATCH (총액 ≠ 단가×kg) | 28 | 수량 ACCEPTED · 원가 INSUFFICIENT — 어느 쪽이 맞는지 정하지 않음 |
| COST_DERIVED_FROM_TOTAL (단가 0, 총액 >0) | 1,094 | 원가 ACCEPTED(파생) — §2 타당성 |
| INVALID_DATE | 0 (창 안) | 전체 원장의 불량 날짜 51행은 창 밖 |
| 고가 소량 직접단가(>1,500/kg) | 378 · kg 0.73 % | 보정 없음 · VALID_OUTLIER 후보 / UNKNOWN |

## 9. ENGINE

```text
bugs                0
semantic changes    1  QuantityBasis = AS_RECORDED | DELIVERED (types.py) — FeedInput·FeedMetricResult·VarianceResult 에 실림
                       · 공개 지표 11개 결과에 basis 스탬프 (입고량을 급여량처럼 읽히지 않게)
                       · CHANGE/VARIANCE: basis 불일치 → INSUFFICIENT context_missing + basis_mismatch
                       · 코호트 효율 5식(FCR·cost/pig·cost/kg gain·qty/head·ADG): DELIVERED → basis_unsupported
                       · DELIVERED → CONSUMED 변환 규칙 없음 · 기본값 AS_RECORDED · 기존 수기 경로 무변경
tests               unit 46+2 기존 그대로(필드 집합 가드 1건만 새 필드 명시) · 신규 basis 5 · adapter 13 · backend full 1437 passed · 1 skipped · ruff clean
adapter             app/harvest/pigplan_feed_delivery.py — SOURCE_CONTRACT · Row · classify · to_raw_feed_row · ShadowBatch · Oracle READ ONLY 소스 + 독립 SQL
script              scripts/feed_oracle_shadow_run.py — credential 은 env 로만(ORACLE_PW 없으면 exit 78) · 출력은 집계·sha256 id 만
```

## 10. PERSISTENCE — 추천안(결정 아님)

이번 단계에서 적재하지 않았다. 결과가 맞다고 확인됐으므로 다음 결정의 근거만 적는다.

| 안 | 장점 | 단점 | 판정 |
|---|---|---|---|
| A. `feed_records` 확장(basis 컬럼 추가) | 테이블 1개 · 기존 리포트 즉시 | **의미 혼합 위험** — 이 테이블은 "급여" 의미로 만들어졌고 cost 리포트·FCR 이 `SUM(quantity_kg)` 을 소비량처럼 읽는다. basis 컬럼을 잊은 쿼리 하나가 입고를 소비로 만든다 | 비추천 |
| B. 별도 `feed_delivery` 테이블 | 의미 분리 명확 · FCR 이 실수로 못 읽음 | 엔진 로더 2개 · 향후 CONSUMED 소스가 오면 테이블 3개 | 차선 |
| **C. source/staging 테이블(`feed_source_rows`: source_system·source_row_id·basis·raw provenance) + canonical view** | 원자료 provenance 보존(§6) · basis 가 행의 속성 · IoT/CONSUMED 소스가 와도 같은 자리 · DELIVERED→CONSUMED→GROUP_ATTRIBUTED 품질 단계를 같은 모델로 올릴 수 있음 · `feed_records` 무변경 | 마이그레이션 1건 · 로더가 view 를 읽도록 F2.5 변경 | **추천** |
| D. 런타임 federation(Oracle 직접) | 적재 0 | Oracle 가용성·지연·법역(KR 소스 데이터 국외 노출 아님이나 운영 의존) · 스냅샷 불가 | 비추천 |

C 를 추천하는 이유는 하나다 — **basis 가 테이블 이름이 아니라 행의 속성이어야** 다음 소스(급이기 IoT = CONSUMED 후보)가 붙을 때 구조를 다시 바꾸지 않는다.

## 11. 판정

```text
ORACLE_SOURCE_SEMANTICS_VALID       YES   (입고 = DELIVERED · KRW 근거 · 필터 내용 근거 — 라벨만 미확인)
FARM_MAPPING_VALID                  YES   (9/9 직접 · 프로덕션 42/42)
DELIVERED_QUANTITY_VALID            YES   (89/89 대조)
CORE_QUANTITY_RECONCILED            YES
CORE_COST_RECONCILED                YES   (COMPLETE 62 · PARTIAL 14 는 evidence 로 일치 · MISSING 13)
CHANGE_METRICS_VALID                YES   (적격 쌍 22/22 — 단, 달 길이 규칙으로 81쌍 유보 → 계약 결정)
VARIANCE_VALID                      YES   (9/9)
PIGOS_DB_WRITES                     0
```

## 12. 하지 않은 것

feed_records INSERT · 마이그레이션 · 시드 · 배포 · API · UI · 모바일 · Oracle adapter 의 운영화(재시도·스케줄) · 매핑 테이블 · FCR/효율 해석 · F0 "같은 길이" 규칙 변경 · 라벨 승격 · 42 밖 58 사료 농장.
