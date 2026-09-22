# Feed Initial Load — Approval Packet (2026-09-23)

> 승인 대상은 **하나**다: PigPlan 사료 입고 원장을 PigOS `feed_source_rows` 에 **한 번** 적재하기 위한
> migration 1건 + 수동 sync 1회. 고객 노출(API·UI)·스케줄러·FCR·과금은 이 승인에 포함되지 않는다.
> 이 문서는 실행 계약이다 — 값이 하나라도 다르면 실행은 거부되도록 코드가 강제한다(§5 가드).
> 이 세션은 프로덕션을 변경하지 않았다: migration 미적용 · 적재 0 · 배포 0 · Oracle 쓰기 0.

---

## 1. APPROVED CODE

```text
BRANCH        release/feed-initial-load        ← 적재 전용. API 라우터·웹이 **없는** 가지
CODE SHA      70e0dc2                          (= a4b4acd persistence + 70e0dc2 guard)
CODE FINGERPRINT (--expect-code-sha)
              b5d97396bad7e7b826f3e057422695b724d4354da67586350b9ac874e491c491
              app/harvest/{feed_load_guard,feed_source_snapshot,feed_source_sync,feed_source_reconcile,pigplan_feed_delivery}.py
              app/repositories/feed_source_repo.py · app/db/models/feed_source.py
              app/engine/feed/{types,normalize}.py · scripts/feed_source_initial_load.py
              (프로덕션 체크아웃에 .git 이 없어 커밋 SHA 를 신뢰할 수 없다 — 내용 지문으로 고정)
제외          4882427 read API · 89c1e70 web  → 이 가지에 **없다** (§9)
CI            Draft PR #8 (release/feed-initial-load → main) — 승인 SHA 가 자기 CI 근거를 갖게 하려고 연 것. merge 목적 아님
              ★ 알려진 시간경계: main 에서 분기한 모든 브랜치는 15:00~24:00 UTC 창에서
                test_kpi_presentation_resolver::test_future_presentation_row_ignored 하나로 빨갛다
                (원인·수정은 docs/runs/D9_TIME_BOUNDARY_20260921.md · 수정은 PR #2 에만 있고 main 에 없다).
                2026-09-23 23:52 UTC 실행이 그 이유로 빨강 → 00:03 UTC 이후 재실행으로 초록 확인.
                실행 직전 CI 는 반드시 창 밖(00:00~15:00 UTC)에서 다시 확인한다
```

## 2. APPROVED MIGRATION

```text
REVISION      a7c9e1f3b5d7   (revises f3c6a8d0b2e4)
대상 변경      CREATE TABLE feed_source_rows · feed_source_sync_runs + 인덱스·제약만
feed_records  변경 0 · 그 외 테이블 변경 0 · 파괴적 연산 0
프로덕션 현재  alembic_version = f3c6a8d0b2e4 (= 이 migration 의 부모, 2026-09-23 실측)
              → `alembic upgrade head` 는 **정확히 이 한 건만** 적용한다 (미승인 pending migration 0)
heads         1 (a7c9e1f3b5d7)
downgrade     이 두 테이블을 drop 한다(로컬 검증: 다른 테이블 무영향 61→59, farms 42 불변).
              데이터가 들어간 뒤의 downgrade 는 적재 데이터 삭제를 뜻한다 — §8 참조
```

## 3. SOURCE SCOPE

```text
SOURCE                 pigplan / TM_ETC_TRADE
FILTER                 ACCOUNT_CD='410002' AND GAIN_YN='M'     (USE_YN 은 필터가 아니라 상태: Y=ACTIVE · non-Y=INACTIVE)
QUANTITY BASIS         DELIVERED        CURRENCY  KRW (소스 계약, 행마다 명시 · farm currency fallback 금지)
AUTHORIZED_MAPPING_SCOPE  42            app.harvest.manifest.FARM_CODES ∩ PigOS farms.farm_code='PP-{no}' (프로덕션 42/42 실측)
OBSERVED_WITH_ROWS        실행 시 측정   (2026-09-23 스냅샷 기준 9 — 코드·명령 어디에도 9 를 박지 않는다)
UNMAPPED_INCLUDED         0             매핑 없는 소스 농장이 하나라도 섞이면 가드가 거부
SOURCE_SCOPE_HASH      승인 범위(42)+필터+계약+창 의 sha256. 창이 바뀌면 값이 바뀐다.
                       예) 창 2025-09-01..2026-09-23 → d2088df061abfce2a594d90d72e76b6b7661dbe94df3096f1d4690ca0207607b
```

## 4. DATE WINDOW · PARTIAL MONTH

```text
WINDOW      2025-09-01 ~ <적재일>      (완료 12개월 + 진행 중 부분월)
저장        부분월 행도 저장한다 — 소스의 사실이다. `event_date` 로 구분될 뿐 별도 플래그를 만들지 않는다
비교 제외   완료월 계산에 부분월을 끌어들이지 않는다:
            · 적재 후 검증(scripts/feed_source_projection_validate.py)은 완료월만 CHANGE/VARIANCE 대조 — 부분월은 대조에서 제외(L4 실측)
            · shadow 감사도 같은 규칙(부분월 별도 표기)
★ 미해결    읽기 API `/feed/summary` 는 부분월에도 전월 대비를 계산한다(`period.partial=true` 로 표시만).
            이 승인 범위 밖(API 미포함)이고, **API/UI 릴리스 게이트의 blocker** 로 넘긴다 — `FEED_API_UI_RELEASE_GATE.md`
```

## 5. EXPECTED PRECHECKS (P0)

| # | 확인 | 기대 |
|---|---|---|
| 1 | 배포될 코드가 승인 가지인가 | `--print-fingerprint` == §1 지문 |
| 2 | 대상 DB revision | `f3c6a8d0b2e4` (migration 적용 전) |
| 3 | alembic heads | 1 |
| 4 | PP- 농장 | 42 (active) |
| 5 | `feed_source_rows` / `feed_source_sync_runs` | 존재하지 않음 (첫 적재) |
| 6 | Oracle 계정 | 기존 승인 read-only · `ORACLE_PW` env 로만 · SELECT 만 |
| 7 | dry-run 결과 | `mismatch {}` · `source_scope_hash` · `source_rows` 를 기록 → 이 두 값이 그 실행의 기대값이 된다 |
| 8 | DB 백업 | `~/pigos-backups/pigos-full-*.sql.gz` 최신본 존재 확인(ops/deploy.sh 가 만드는 것과 같은 형식) |

## 6. EXECUTION COMMAND SHAPE

```bash
# P0 preflight — 쓰기 0. 여기서 나온 scope hash / source rows 를 그대로 아래에 넣는다.
ORACLE_PW=... python scripts/feed_source_snapshot_take.py --out /var/tmp/feed/s.json \
    --meta-out /var/tmp/feed/meta.json --window-start 2025-09-01 --window-end <load-date> --today <load-date>
python scripts/feed_source_initial_load.py --dry-run --snapshot /var/tmp/feed/s.json \
    --window-start 2025-09-01 --window-end <load-date> --today <load-date> --out /var/tmp/feed/preflight.json

# P3 migration (한 건)
alembic upgrade head

# P6 적재 — 다섯 기대값이 전부 맞아야 통과. 하나라도 다르면 거부(exit 4), 데이터 변경 0.
python scripts/feed_source_initial_load.py --apply \
    --expect-environment production \
    --expect-code-sha b5d97396bad7e7b826f3e057422695b724d4354da67586350b9ac874e491c491 \
    --expect-migration a7c9e1f3b5d7 \
    --expect-source-scope-hash <preflight 값> \
    --expect-source-rows <preflight 값> \
    --snapshot /var/tmp/feed/s.json --window-start 2025-09-01 --window-end <load-date> --today <load-date> \
    --out /var/tmp/feed/load.json
```

가드 동작(2026-09-23 일회용 DB 리허설 A~I 실측):

```text
--dry-run                     쓰기 0 (프로덕션 URL 이어도 읽기만)
--target-local + 프로덕션 환경  거부
--apply 기대값 누락            거부 (누락 항목을 전부 나열)
--apply 지문 불일치            거부
--apply scope hash 불일치      거부
--apply 행수 불일치            거부
--apply migration 불일치       거부
--apply 환경 불일치/미상       거부
위 거부 8종 후 적재된 행        0
다섯 값이 전부 일치할 때만      적재 (5,461행 · mismatch {} · 재실행 시 0건 추가)
```

## 7. RECONCILIATION (P7·P8)

```bash
# 적재 직후 — 읽기 전용, 프로덕션 허용
python scripts/feed_source_initial_load.py --verify-only --expect-environment production \
    --snapshot /var/tmp/feed/s.json --window-start 2025-09-01 --window-end <load-date> --today <load-date> \
    --out /var/tmp/feed/verify.json
```

통과 기준 (하나라도 어긋나면 성공 처리 금지):

```text
grain        total · farm · month · farm×month · ACTIVE/INACTIVE   전부 mismatch 0
invariants   duplicate identity 0 · payload_hash NULL 0 · basis≠DELIVERED 0 · currency≠KRW 0
             current/identity ≤ 1 · unmapped farms 0
ledger       feed_source_sync_runs 1행 · status SUCCEEDED · scope_hash·watermark 기록 · notes.empty_source=false
projection   (선택, 읽기 전용) scripts/feed_source_projection_validate.py — 수량/원가/단가/구성 mismatch 0 · lineage 실패 0
분류          partial cost · missing cost 는 mismatch 가 아니다 — evidence 계약대로 `cost_status` 에 남는다
```

## 8. STOP / RECOVERY

| 상황 | 처리 |
|---|---|
| 가드 거부(exit 4) | 데이터 변경 0. 원인 수정 후 preflight 부터 다시. 기대값을 억지로 맞추지 않는다 |
| 소스 장애 | 원장 `SOURCE_UNAVAILABLE` + `notes.error_class`. 데이터 변경 0 · 철회 0. 재실행(멱등) |
| 저장 실패 | SAVEPOINT rollback → `SYNC_FAILED` · `data_changed=false`. 재실행 = 처음부터(중복 0) |
| 대사 불일치 | **성공 처리 금지.** 분류(SOURCE/PERSISTENCE/PROJECTION/SYNC/ENGINE/TEST/EXPECTED/UNEXPLAINED) 전에 다음 단계 없음 |
| 잘못 적재됨 | ★ 임의 DELETE 금지. 해당 `sync_run_id` 의 revision 을 superseded 로 닫고 원천 재투입(revive) — 정본은 `FEED_PERSISTENCE_ARCHITECTURE.md` §6 |
| 스키마 되돌리기 | migration rollback ≠ data rollback. downgrade 는 두 테이블을 drop 한다 → 데이터 폐기를 뜻하므로 백업 확인 뒤에만 |

## 9. API/UI EXCLUDED · SCHEDULER OFF

```text
이 승인이 포함하지 않는 것
  /feed 신규 결과 UI 노출 · Oracle DELIVERED 데이터의 고객 노출 · 읽기 API 공개
  D-15(FCR·원가 노출 경계) · FCR 계산 · entitlement · billing · 스케줄러(ARQ) 등록
근거
  적재 코드는 라우터를 import 하지 않는다(단방향). 승인 가지에 라우터 파일 자체가 없고 main.py 등록도 없다 —
  이 코드로 api 를 배포해도 /feed/summary 경로가 존재하지 않는다.
  웹은 별도 배포 단위(ops/deploy.sh web)이며 이 승인에서 배포하지 않는다.
후속
  FEED_API_UI_RELEASE_GATE.md (별도 게이트 · blocker 2건 등재)
```

## 10. 최종 플래그

```text
FINAL_HEAD_CI_GREEN      YES (feed HEAD ecd1ae8 green · 승인 가지 a4b4acd green + 70e0dc2 push)
SOURCE_SCOPE_APPROVED    YES (42 권한 · 관측은 실행 시 측정 · unmapped 0 강제)
MIGRATION_APPROVED       YES (단일 head · 한 건만 적용 · feed_records 무변경)
PROD_GUARD_APPROVED      YES (다섯 기대 일치 시에만 · 리허설 8종 거부 실측)
RECONCILIATION_READY     YES (--verify-only + projection validate, 읽기 전용)
API_UI_SEPARATED         YES (승인 가지에 라우터·웹 없음)

INITIAL_LOAD_APPROVED    — 사람 결재 대기 (기술 조건 충족)
API_UI_RELEASE_APPROVED  NO
READY_FOR_PRODUCTION     NO
```
