# Feed Persistence Architecture — FROZEN (2026-09-22)

> 대상: Oracle shadow 로 검증된 사료 **입고(DELIVERED)** 관측을 PigOS 에 지속 저장하는 정본 구조. 이 문서가 P-1~P-6 의 결정 기록이다.
> 이번 단계의 산출: 설계 + 로컬 migration + repository/sync 계약 + 테스트. **프로덕션 migration/write/deploy/scheduler/historical load 0.**
> 선행: `reports/PIGPLAN_ORACLE_FEED_PREFLIGHT_20260922.md` · `reports/FEED_ORACLE_SHADOW_INTEGRATION_20260922.md` · `FEED_ENGINE_V1_CANONICAL_SPEC.md`.

---

## 0. 한 화면

```text
P-1 TOPOLOGY      C  immutable source revision (feed_source_rows) + Python projection (repositories/feed_source_repo.py) → FeedInput
P-2 IDENTITY      NATIVE_STABLE_KEY  (FARM_NO, SEQ) = 소스 PK · payload_hash 로 멱등 · 결정론 uuid5 id
P-3 SEMANTICS     quantity_basis 는 행의 컬럼(AS_RECORDED|DELIVERED|CONSUMED, CHECK) · currency NOT NULL(소스 계약 KRW) · 변환 규칙 없음
P-4 PROJECTION    엔진은 ORM 을 모른다 — load_raw_rows() 가 현재·ACTIVE·수량ACCEPTED·basis 일치 행만 RawFeedRow 로 · lineage = source_row_ids
P-5 CORRECTION    B append revision (이전 superseded) · USE_YN≠Y = INACTIVE revision · 소스에서 사라짐 = RETRACTED revision · 물리 삭제 0
P-6 PERIOD        P6-B  달력월↔달력월은 길이 무관 비교(TOTAL 지표) · 임의 구간은 같은 길이 · RATE 지표 없음(생기면 days 정규화)
SCHEMA            feed_source_rows · feed_source_sync_runs  (alembic a7c9e1f3b5d7, 로컬 upgrade/downgrade/upgrade 검증, head 단일)
SYNC              lookback 전량 대조 + watermark(LOG_UPT_DT) 기록 · SOURCE_UNAVAILABLE ≠ 빈 데이터 · 원장 1행/실행 · 스케줄러 없음
TESTS             persistence integration 9 · basis/P-6 unit · backend full 1447 passed · ruff clean
```

## 1. 기존 패턴 조사 (§2) — 새 테이블부터 만들지 않았다

| 패턴 | 저장소 실측 | 판정 |
|---|---|---|
| 소스키 기반 결정론 uuid5 + ON CONFLICT | `scripts/harvest_import.py:52-56` NS `pigos.harvest.pigplan`, `ON CONFLICT (id) DO NOTHING/UPDATE` | **REUSE** — id = uuid5(identity+payload_hash) |
| 외부 원문 불변 관측 테이블 | `db/models/benchmark.py:71 SourceObservation` "외부 원문(변환 전, 가공 금지)", `raw_fields_json` JSONB | **REUSE(형태)** — 원문 보존·JSONB payload 규율을 그대로 따른다 |
| 데이터 출처 표기 | `farms.data_origin / data_classification` | REUSE(개념) — 행 단위 `source_system/dataset/contract_version` |
| 동기화 원장 | `ops.py SyncLog` (모바일 sync: started/completed/records/conflicts) | **EXTEND(형태)** — 외부 소스용 별도 원장 `feed_source_sync_runs` (모바일 원장에 섞지 않음) |
| revision / tombstone / watermark / content hash | 없음 (harvest 는 `DO UPDATE` = 덮어쓰기, 이력 소실) | **NEW_REQUIRED** — 본 설계의 핵심 |
| QBridge 외부 티켓 연동 | `qbridge_service.py` `external_id` | 참고만 (단방향 이벤트, 관측 저장 아님) |

## 2. 후보 비교 (§3) — 코드 기준

| 기준 | A. feed_records 확장 | B. feed_delivery 별도 | **C. source revision + projection** | D. federation |
|---|---|---|---|---|
| source semantics 보존 | ✗ 컬럼 몇 개로는 provenance·revision 못 담음 | △ | **✓** payload·hash·revision·contract | ✓(소스에 있음) |
| basis 분리 | ✗ `SUM(quantity_kg)` 를 소비량처럼 읽는 쿼리 3곳(kpi_service·report_service·cost-summary)이 basis 컬럼을 잊으면 입고=소비 | ✓ 테이블로 분리 | **✓** 행 속성 + CHECK + 인덱스 | ✓ |
| idempotent sync | △ (id 결정론 필요) | △ | **✓** identity+hash | 해당 없음 |
| source correction | ✗ UPDATE = 근거 소실 | △ | **✓** append revision | 소스 이력 의존 |
| auditability | ✗ | △ | **✓** 원장 + revision | ✗ (스냅샷 불가) |
| future IoT(CONSUMED) | ✗ 또 확장 | ✗ 테이블 3개 | **✓** 같은 테이블, basis 값만 | △ |
| manual feed 호환 | 위험(의미 혼합) | ✓ | **✓** feed_records 무변경 | ✓ |
| Feed Engine 호환 | ✓ | ✓ | **✓** 이미 RawFeedRow 경계 | ✓ |
| query complexity | 낮음 | 낮음 | 중간(current·ACTIVE 필터, 인덱스로 해결) | 높음(원격) |
| operational | 낮음 | 낮음 | 중간(sync 원장) | 높음(Oracle 가용성·지연) |
| migration risk | 기존 테이블 변경 | 신규 1 | **신규 2, 기존 0** | 0 |

**결정 P-1 = C.** 결정적 근거는 하나: basis 가 테이블 이름이 아니라 행의 속성이어야 다음 소스(급이기 IoT = CONSUMED 후보)가 붙을 때 구조를 다시 바꾸지 않는다. A 는 `feed_records` 가 "급여" 의미로 태어난 흔적(라우터 docstring "수기 급이량", UI "급여량")이 있어 DELIVERED 를 넣는 순간 의미가 섞인다.

## 3. P-2 Source identity (§7-8) — 실측

```text
TM_ETC_TRADE  PK SYS_C007942 (FARM_NO, SEQ) · UNIQUE IDX_TM_ETC_TRADE (FARM_NO, SEQ)
              2,300,227 행: 중복 키 0 · NULL 키 0 (사료 행 675,631 도 0/0)
              SEQ = 농장별 일련번호 (rows/max(seq) 0.993 — 거의 빈틈 없음). row number 아님
→ NATIVE_STABLE_KEY   source_row_key = "{FARM_NO}:{SEQ}"
id            uuid5(NS "pigos.feed_source", source_system:dataset:row_key:payload_hash) — 재실행이 같은 id
멱등          UNIQUE (source_system, source_dataset, source_row_key, payload_hash)  → 같은 payload 는 두 번 INSERT 되지 않는다
현재 1개      partial UNIQUE (source_system, source_dataset, source_row_key) WHERE is_current
테스트        test_same_source_three_times_inserts_once: RUN1 inserts 2 · RUN2 0 · RUN3 0 · unchanged 2·2
```

payload_hash 에 들어가는 것: event_date·quantity·basis·unit_cost·total_cost·currency·stage·product·source_status·quantity/cost_status·reasons·source_updated_at·contract. 들어가지 않는 것: observed_at·sync_run_id (재실행이 해시를 바꾸면 안 된다).

## 4. P-3 Semantics (§5-6·§14-16)

```text
quantity_basis   컬럼 · CHECK IN ('AS_RECORDED','DELIVERED','CONSUMED') · projection 은 요청 basis 와 같은 행만
                 금지 변환: DELIVERED→AS_RECORDED · DELIVERED→CONSUMED (엔진에도 어댑터에도 없다 — 테스트로 고정)
currency         NOT NULL · 소스 계약이 행마다 명시 (pigplan: KRW, 근거 TC_CODE_SYS 943001↔942001 + TA_FARM.COUNTRY_CODE='KOR')
                 projection 의 FeedInput.farm_currency = 행의 통화(단일) — farms.currency 를 읽지 않는다 (test_krw_is_preserved_and_farm_currency_never_used: 농장 USD 여도 KRW)
                 비KOR 농장 행: 수량 ACCEPTED · 원가 EXCLUDED(BLOCKED_CURRENCY_EVIDENCE) · currency 는 계약값 유지
세 소스의 관계    manual feed_records → feed_engine_service.load_feed_input (AS_RECORDED, 기존 그대로)
                 Oracle → feed_source_rows(DELIVERED) → load_feed_input_from_source(basis="DELIVERED")
                 future IoT → feed_source_rows(CONSUMED) → 같은 함수 basis="CONSUMED"  (어댑터만 추가)
                 같은 농장·같은 날의 세 관측은 중복이 아니다. 호출자가 basis 를 명시한다. 엔진은 basis 혼합 쌍을 거부한다 (test_as_recorded_and_delivered_stay_separate_and_never_mix)
```

## 5. P-4 Canonical projection (§12-13·§26)

"view" = **Python projection** (`repositories/feed_source_repo.load_raw_rows`) — 저장소에 SQL VIEW 관례가 없고(KPI 뷰 1개는 마이그레이션 전용), materialization 은 불필요(농장×월 행 수십 개).

```text
feed_source_rows ──(is_current ∧ source_status=ACTIVE ∧ quantity_status=ACCEPTED ∧ basis=요청)──▶ RawFeedRow ──normalize──▶ FeedInput(basis)
                                                                                                    unit_cost = cost_status=ACCEPTED 일 때만 (INSUFFICIENT/EXCLUDED 는 None → 엔진 partial_cost)
lineage  Projection.source_row_ids (FeedInput 행 순서와 동일) + contract_versions
         FeedMetricResult → FeedInput 행 → source_row_id → (source_system, source_dataset, source_row_key, revision, payload_hash, contract)
         원문 payload 를 metric 에 복제하지 않는다 — id 로 역추적만 (test_source_row_to_persistence_to_canonical_to_feedinput)
```

## 6. P-5 Correction / inactive / deletion (§9-11) — 실측 근거

```text
정정 빈도     12개월 사료행 21,618 중 LOG_UPT_DT > LOG_INS_DT 1,534 (7.1 %) · 월 18~543건
비활성       USE_YN≠Y 917 중 663 은 UPDATE 로 전환됨 → soft-delete 다. HIS_TM_ETC_TRADE 에 UD_MODE='U' 8,718 (BE_USE_YN Y→N 8,058)
물리 삭제     HIS UD_MODE='D' 16건(전기간) · 12개월 0 · HIS 에 있고 TM 에 없는 키 0 → 드물지만 존재
지연 도착     LOG_INS_DT − WK_DT: p50 6.1일 · p95 88일 · max 347일 · 30일 초과 4,206 (19 %)

정책  correction   B append — 새 revision INSERT, 이전 is_current=false·superseded_at. 값 UPDATE 절대 없음
      inactive     소스 사실 그대로 revision (source_status=INACTIVE). projection 제외. 되살아나면 그 revision 이 다시 current (revive, 새 행 없음)
      missing      lookback 창 안에서 소스가 주지 않는 identity → RETRACTED revision(값 복사 + SOURCE_ROW_MISSING). 물리 삭제 0
      quality      source_status(소스 사실) ≠ quantity_status ≠ cost_status ≠ metric eligibility — 네 층. is_valid 하나 없음
```

## 7. P-6 Period comparison (§17-20) — evidence 와 결정

```text
evidence   F0 §5 표: "CALENDAR_PERIOD ×2 (같은 길이)"   ←  F0 §9: "p0 = p1 과 같은 길이의 직전 구간(월이면 전월)"
           엔진 metrics.py:176 `prev.period.days != cur.period.days` + 테스트 T-B2 는 2026-09-21 d16c8ce 에서 §5 문구로 작성됨(이 프로젝트)
           제품 문서(E2 확장결정 · E3 핸드오프 What Changed)에 기간 길이 규칙 없음 — 사람의 제품 결정이 아니었다
impact     Oracle shadow 최초 실행: 연속 월쌍 99 중 81 이 context_missing (2 쌍/농장만 통과: 12→1월, 7→8월)
decision   P6-B  TOTAL 지표(FEED_QTY_CHANGE · FEED_COST_CHANGE · VARIANCE)는 달력월↔달력월이면 28~31일 차이와 무관하게 비교
                 (§9 "월이면 전월" 의 원래 의도). 임의 구간은 같은 길이만(7일 vs 30일 차단 유지). evidence.comparison_grain 에 근거 표기
                 RATE 지표(kg/day)는 V1 에 없음 — 생기면 days 로 정규화하므로 이 규칙과 무관
함께 변경   spec §5·§9 · types.Period.is_calendar_month/comparison_grain · metrics/variance · T-B2 재작성 + 달력월 테스트 · shadow 재실행(80/80·52/52·52/52)
```

## 8. Schema (§21-22)

```text
feed_source_sync_runs   id · source_system · source_dataset · source_contract_version · status(RUNNING|SUCCEEDED|SOURCE_UNAVAILABLE|SYNC_FAILED)
                        started_at · completed_at · window_start/end · watermark_from/to · lookback_days · farms
                        rows_fetched/inserted/unchanged/superseded/retracted · error
feed_source_rows        id(uuid5) · source_system · source_dataset · source_row_key · source_contract_version · revision · is_current · superseded_at · sync_run_id
                        farm_id(FK farms, 내부 키) · event_date · event_date_raw · quantity_kg · quantity_unit · quantity_basis · unit_cost · total_cost · currency
                        feed_stage_raw · feed_product_raw · source_status · quantity_status · cost_status · quality_reasons(JSONB)
                        observed_at · source_inserted_at · source_updated_at · payload_hash · payload(JSONB, 식별정보 없음) · created_at
constraints             UNIQUE(identity, payload_hash) · UNIQUE(identity, revision) · partial UNIQUE(identity) WHERE is_current
                        CHECK basis/status 4종 · revision ≥ 1
indexes                 (farm_id, quantity_basis, event_date) WHERE is_current AND source_status='ACTIVE'   ← projection 경로
                        (source_system, source_dataset, started_at) on runs
migration               alembic a7c9e1f3b5d7 (revises f3c6a8d0b2e4) — autogenerate 산출에 신규 2 테이블 외 drift 0 · 로컬 upgrade→downgrade→upgrade OK · heads 1
```

## 9. Sync contract (§23-24)

| 항목 | 계약 |
|---|---|
| 대상 | 직접 매핑 농장만 (`farm_map: {FARM_NO → farms.id}` — `PP-{FARM_NO}` 로 만든다, fuzzy 0) |
| window | `[today − lookback_days, today]` 의 event_date **전량** 조회·대조. 지연 도착(p95 88일·max 347일)과 RETRACTED 감지 때문에 증분만으로는 부족 → lookback 기본 **400일** 제안(초기 적재는 완료월 12 + 부분월) |
| watermark | 실행이 본 max(LOG_UPT_DT) 를 원장에 기록(관측·최적화용). 정확성은 창 전량 대조가 보장 |
| idempotency | identity+payload_hash → 같은 소스 상태 N회 = revision 증가 0 |
| correction | 새 revision + supersede (원장 `rows_superseded`) |
| inactive | INACTIVE revision |
| missing | RETRACTED revision (원장 `rows_retracted`) |
| failure | 소스 예외 → `SOURCE_UNAVAILABLE`, 데이터 변경 0 (test_oracle_unavailable_changes_nothing_and_is_not_empty_data). 저장 예외 → rollback + `SYNC_FAILED` 원장. 기존 행 삭제 0 |
| ledger | `feed_source_sync_runs` 1행/실행 |
| scheduler | **없음** (이번 단계). ARQ 등록 금지 |
| credential | env 만 (ORACLE_PW). 파일·메모리 참조 없음. 로그에 출력 없음 |

## 10. Initial historical load — 설계만 (§25, 실행 안 함)

```text
scope      직접 매핑 9농장 (실행 시 farms_with_rows() 로 다시 구한다 — 9 를 hardcode 하지 않는다)
period     최근 12 완료월 + 진행 부분월 (lookback 400일 창으로 자연 포함)
expected   수량 ACCEPTED ≈ shadow 5,077 (완료월) — 실행 시 원장 rows_inserted 로 재확인. preflight 숫자를 기대값으로 박지 않는다
dry-run    같은 코드로 **로컬 PG** 에 먼저 적재 → feed_source_repo.load_raw_rows 로 projection → shadow JSON 과 farm-month 대조 (0 불일치여야)
prod       별도 결재: migration a7c9e1f3b5d7 적용 → 1회 sync 실행(수동) → 원장 확인. scheduler 는 그 뒤 또 별도
```

## 11. STOP 조건 점검 (§30)

| 조건 | 상태 |
|---|---|
| stable source identity 없음 | 해당 없음 — PK 실측 |
| correction semantics 불명 | 해당 없음 — HIS·LOG_UPT_DT 실측, 정책 B |
| currency evidence 충돌 | 해당 없음 — 소스 설정 단일(KOR→KRW) |
| farm mapping 불안정 | 해당 없음 — PP-{FARM_NO} 42/42 |
| QuantityBasis 유실 | 해당 없음 — 컬럼+CHECK+projection 필터+엔진 거부 |
| migration chain conflict | 해당 없음 — head 1 |
| P-6 unresolved | 해결 — P6-B, evidence §7 |

## 12. 하지 않은 것

프로덕션 migration · 프로덕션 write · 배포 · 스케줄러 · historical load(로컬 dry-run 포함) · API/UI · feed_records 변경 · CONSUMED 어댑터 · 42 밖 농장 매핑.
