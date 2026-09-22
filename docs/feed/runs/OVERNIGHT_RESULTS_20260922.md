# Feed Persistence — Overnight Results (2026-09-22 → 23)

> 브리프: PERSISTENCE OVERNIGHT AUTONOMOUS DEVELOPMENT & VERIFICATION. 기준 `a65d464`. 대상 DB = 로컬 일회용 `pigos_feedload` 만.
> Oracle 은 L0-B 에서 **1회** SELECT(0.78 s). 이후 전 단계는 repo 밖 snapshot 사용. 원자료·식별자는 이 문서에 없다(마스킹 id·집계·해시만).

## L0-A SOURCE SCOPE FREEZE

```text
SOURCE_SYSTEM     PigPlan Oracle (pigplan)
SOURCE_TABLE      TM_ETC_TRADE
SOURCE_FILTER     ACCOUNT_CD='410002' AND GAIN_YN='M'   (USE_YN 은 필터가 아니라 상태: Y→ACTIVE · non-Y→INACTIVE)
FARM_SCOPE        app.harvest.manifest.FARM_CODES 42 (PigOS farm_code 'PP-{no}' 직접 매핑) ∩ 창 안 사료행 보유 → 9
DATE_WINDOW       2025-09-01 ~ 2026-09-22 (12 완료월 + 부분월, today=2026-09-22 고정)
USE_YN_SEMANTICS  소스 soft-delete(UPDATE). 추출 필터 없음 · 상태 보존 · projection 은 ACTIVE 만
QUANTITY_BASIS    DELIVERED
CURRENCY          KRW (source contract, TC_CODE_SYS 943001↔942001 + COUNTRY_CODE KOR)
SOURCE_IDENTITY   NATIVE_STABLE_KEY (FARM_NO, SEQ) → "{no}:{seq}"
P6_STATUS         ACCEPTED (P6-B, a65d464) — 재결정 없음
SOURCE_SCOPE_CONFLICT   없음 (fetch 는 USE_YN 무필터 · reconciliation 은 상태별 집계 · 독립 SQL 만 use_yn='Y' = ACTIVE projection 과 동일 의미)
SOURCE_SCOPE_FROZEN     YES   scope_hash 7eb1e1536ef1…
```

## L0 PRECHECK
```text
STATUS PASS · tree clean · branch feat/feed-engine-v1-core · HEAD a65d464(후손) · CI a65d464 green · alembic head a7c9e1f3b5d7 = 1
effective DATABASE_URL host = localhost (supabase 줄은 주석) · 원천 모드 ORACLE_READONLY → snapshot
```

## L0-B SOURCE SNAPSHOT
```text
STATUS PASS · extracted 2026-09-22T07:55Z · rows 5,461 · farms 9 · date 2025-09-01~2026-09-22 · dateless 0
USE_YN Y 5,202 / non-Y 259 · changed_after_insert 540 · Oracle elapsed 0.78 s (1 fetch + 1 독립집계, 재조회 0)
scope_hash 7eb1e153… · content_hash 705d8a06… · 저장: repo 밖 scratchpad/feed_snapshot/ (종료 시 삭제 여부 §END)
meta: docs/feed/runs/SNAPSHOT_META_20260922.json
```

## L1 INITIAL LOAD LOCAL
```text
STATUS PASS
FILES  app/db/models/feed_source.py(+source_scope_hash, notes) · alembic a7c9e1f3b5d7(같은 2 컬럼, 미적용 migration 편집 · 로컬 down/up 재검증)
       app/harvest/feed_source_snapshot.py · feed_source_reconcile.py · scripts/feed_source_snapshot_take.py · scripts/feed_source_initial_load.py
       app/harvest/feed_source_sync.py(scope_hash·error_class·철회 가드·batch) · app/repositories/feed_source_repo.py(batch·chunked lookups)
TESTS  unit test_feed_source_snapshot_reconcile 5 · integration persistence 9→12
EXECUTION  fail-closed: RDS 호스트 URL → REFUSED ✓ · --dry-run: DB write 0 ✓(count 0) · bootstrap 42 PP- 농장(합성, currency USD 로 일부러 다르게)
SOURCE ROWS 5,461 → TARGET gen-1 5,461 · ACTIVE 5,202 / INACTIVE 259 · quantity ACCEPTED 5,198 / EXCLUDED 263 · cost ACCEPTED 4,364 / INSUFFICIENT 834
MISMATCHES total 0 · farm 0 · month 0 · farm×month 0 · status 0 · invariants: hash NULL 0 · currency NULL 0 · non-KRW 0 · non-DELIVERED 0 · current/identity max 1 · sync_run scope_hash 있음 · watermark 있음
FIX ATTEMPTS 2  ① reconcile 중첩 집계 SQL(GroupingError) → 서브쿼리  ② PERSISTENCE_BUG: asyncpg 바인드 32,767 상한(2,000행×30열) → statement 당 행수 = min(batch, 32000//열수)
              (①② 모두 원장에 SYNC_FAILED · data_changed=false · 0행으로 남음 — 부분 커밋 없음 증명)
PERFORMANCE elapsed 19.0 s · 287 rows/s · peak py mem 47 MB · DB +5.4 MB (batch 2000 → 실제 statement 1,066행)  ← L6 에서 프로파일
```

## L2 IDEMPOTENCY / RESTART
```text
STATUS PASS
RUN1 insert 5,461 · RUN2 insert 0 / unchanged 5,461 · RUN3 insert 0 / unchanged 5,461 · RUN4(savepoint 리팩터 뒤) insert 0 · rows_all_revisions 5,461 · max_revision 1
shuffle → 같은 identity 집합·payload_hash·uuid5 (test_input_order_shuffle_…)
restart → 저장 뒤·커밋 전 예외 = SYNC_FAILED · 데이터 0 · 재시작 30/30 · 중복 0 (test_mid_batch_interruption_…)
원장: SYNC_FAILED(error_class·data_changed=false·resumable) · SUCCEEDED 기록 확인
FIX ATTEMPTS 1  sync 를 SAVEPOINT(begin_nested) 로 — 픽스처 트랜잭션과 운영 세션 양쪽에서 같은 의미
```

## L3 REVISION / CORRECTION / INACTIVE / RETRACTION
```text
STATUS PASS  (scripts/feed_source_revision_drill.py · snapshot 메모리 변형 · Oracle 무접촉 · 2 % 표본 = 각 109행)
A/B 정정 + C Y→N : 기대 298 (겹침 제외) → inserted 298 · superseded 298 ✓ · E 소실 103 → RETRACTED 103 ✓
history_retained ✓ (5,461 → 5,862 = +298 +103) · identities 5,461 불변 ✓ · physical_deletes 0 ✓ · current INACTIVE +96 · RETRACTED 103
D 되살림(원본 재투입): 새 행 0 ✓ · revive 401 = 298+103 ✓ · current 상태 원본과 동일 ✓
G 빈 소스 결과: SUCCEEDED · retracted 0 ✓ (철회 가드 · empty_source=true)
REFERENCE_CORRECTION_RATE  snapshot 실측 540/5,461 = 9.9 % changed_after_insert (Oracle LOG_UPT_DT 기준) — 목표값 아님, 참고만
FIX ATTEMPTS 2  ① SYNC_BUG(진짜): savepoint 밖 예외(watermark tz-mixed max) 가 SYNC_FAILED 를 적고도 outer commit 으로 데이터를 남김
                   → 원장 기록까지 savepoint 안으로 · watermark tz 정규화 · 회귀 테스트 test_failure_after_ingest_never_leaves_data_behind
                ② TEST_BUG(드릴 회계): rows_inserted 에 tombstone 미포함 — 원장 의미 명시 후 검사식 수정
MISMATCH CLASSIFICATION  SYNC_BUG 1(수정) · TEST_BUG 1(수정) · UNEXPLAINED 0
```

## L4 CANONICAL PROJECTION FULL VALIDATION
```text
STATUS PASS  (scripts/feed_source_projection_validate.py · 일회용 DB 의 persisted 행 → projection → FeedInput → 엔진, 전량)
projected rows 5,198 (= 수량 ACCEPTED·ACTIVE·current) · farm-months 계산 108(9×12) + 부분월 3
lineage  5,198 / 5,198 역추적 OK (FeedInput 행 → source_row_id → DB 행: current·ACTIVE·pigplan·row_key·hash·contract·수량·날짜 일치) · failures 0
계약     모든 결과 quantity_basis=DELIVERED · provenance ∈ {ACTUAL,DERIVED,INSUFFICIENT} · FeedInput 통화 KRW (농장은 USD 로 만들어 뒀는데도)
① vs Oracle 독립 SQL (엔진 미경유)  89 farm-month · quantity 0 · cost 0 · unit_price 0 · mix 0
② vs shadow (Oracle 직접→엔진)     108 farm-month · quantity 0 · cost 0 · unit_price 0 · change 0 · variance 0
CHANGE   값 80 · no_data 380(42 농장 중 33 은 행 없음) · prior_insufficient 2 · context_missing 0 (P6-B)
VARIANCE 적격 52 · PRICE+VOLUME+MIX=TOTAL 52/52
FIX ATTEMPTS 1  EXPECTED_DIFFERENCE→제거: 저장 unit_cost NUMERIC(14,4) 가 파생단가(total/kg)를 4자리로 잘라 월 원가 0.1 KRW 차이(1농장 2개월)
                → NUMERIC(18,8) (미적용 migration 편집, 두 로컬 DB down/up 재검증) + 원가 허용오차 = 통화 최소단위 1 KRW 명시. 재실행 0 불일치
MISMATCH CLASSIFICATION  EXPECTED_DIFFERENCE 1(해소) · UNEXPLAINED 0
```

## P6 PERIOD SEMANTICS
```text
P6_STATUS ACCEPTED (P6-B @ a65d464) — 재결정 없음. 실데이터: 달 길이 다른 81쌍 전부 계산(context_missing 0). same-length 18쌍 동일 결과.
unit: Jan31→Feb28 · Aug31→Sep30 · 임의 20d vs 30d(context_missing) · missing prior(prior_insufficient) · prior zero(rate None) — test_feed_engine.py / test_feed_engine_basis.py
```

## L5 FAILURE INJECTION
```text
STATUS PASS  (tests/integration/test_feed_source_persistence.py 18)
connection drop → SOURCE_UNAVAILABLE · error_class SOURCE_CONNECTION · 데이터 변경 0 · 철회 0
timeout        → SOURCE_UNAVAILABLE · TIMEOUT
permission     → SOURCE_UNAVAILABLE · PERMISSION_DENIED
empty success  → SUCCEEDED · notes.empty_source=true · retraction_skipped_farms · 철회 0   (SOURCE_UNAVAILABLE ≠ EMPTY_SOURCE: 장애 원장에는 empty_source 키 자체가 없다)
partial batch  → 2번째 statement 에서 DB 예외 → SYNC_FAILED · TARGET_DB · 첫 배치도 남지 않음(0행) · 재시작 40/40 중복 0   ← "partial commit 없음" 쪽 선택
DB txn failure → 위와 같은 경로(SAVEPOINT rollback) · 원장 행은 남는다
```
