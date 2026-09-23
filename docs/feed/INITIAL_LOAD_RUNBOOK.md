# Feed Source Initial Load — Runbook (v1, 2026-09-23)

> 대상: PigPlan Oracle 사료 입고 원장(`TM_ETC_TRADE`) → PigOS `feed_source_rows`. 이 문서는 **절차**다.
> 프로덕션 실행은 별도 결재(INITIAL LOAD APPROVAL) 뒤. 여기 적힌 숫자는 로컬 일회용 DB 실측(`runs/OVERNIGHT_RESULTS_20260922.md`)이며 기대값이 아니라 참고값이다.
> 이 문서에 실제 농장 식별자는 없다. 실행 로그도 마스킹 id·집계만 남긴다.

## 0. 불변 원칙

```text
같은 원천은 중복되지 않는다        identity (FARM_NO, SEQ) + payload_hash → 재실행 = 새 revision 0
정정은 사라지지 않는다            값 변경 = 새 revision, 이전 revision superseded (UPDATE 없음)
원천 장애는 삭제로 해석되지 않는다  SOURCE_UNAVAILABLE / SYNC_FAILED · 빈 결과 · 농장 침묵 → 철회 0
DELIVERED 는 DELIVERED 로 남는다    quantity_basis 컬럼 · projection 필터 · 엔진 거부
KRW 는 KRW 로 남는다               행마다 명시 · farms.currency 미사용
모든 계산은 원천까지 역추적된다      FeedInput 행 → source_row_id → identity·revision·hash·contract
대사되지 않은 숫자는 승인하지 않는다  reconciliation mismatch 0 이 아니면 STOP
```

## 1. Preflight

| 항목 | 확인 |
|---|---|
| 브랜치/HEAD | `feat/feed-engine-v1-core` 최신 · CI green |
| alembic | `alembic heads` = 1 · 대상 DB `alembic current` = `a7c9e1f3b5d7` (프로덕션은 결재 뒤 적용) |
| 대상 DB | `DATABASE_URL` 호스트 확인. 스크립트는 localhost/127.0.0.1/pigos-postgres 외 호스트를 **거부**한다(프로덕션 실행 시 이 가드를 어떻게 풀지는 결재 패킷에 명시 — 현재 코드로는 프로덕션 적재가 불가능하다) |
| 원천 | 승인 read-only 계정 · `ORACLE_PW` **env 로만** · 파일/메모리에 두지 않음 · SELECT 만 |
| farm mapping | 대상 DB `farms.farm_code = 'PP-{FARM_NO}'` 존재 (하베스트 42) — 없는 농장은 자동 제외(fuzzy 0) |
| 창 | 완료월 12 + 부분월 (`--window-start` 는 1일, `--window-end` = today) |

## 2. Source scope (고정)

```text
SOURCE     pigplan · TM_ETC_TRADE · ACCOUNT_CD='410002' AND GAIN_YN='M'   (USE_YN 은 필터 아님 → ACTIVE/INACTIVE 상태)
FARMS      manifest 42 ∩ 창 안 사료행 보유 (실행 시 farms_with_rows 로 산출 — 숫자 hardcode 금지)
BASIS      DELIVERED   CURRENCY  KRW   CONTRACT  pigplan_feed_delivery.v1
scope_hash sha256(system·dataset·filter·contract·farm set·window) — 원장 feed_source_sync_runs.source_scope_hash 에 기록
```

## 3. Commands

```bash
cd api
# 1) snapshot (Oracle 1회 SELECT, repo 밖 경로)
ORACLE_PW=... python scripts/feed_source_snapshot_take.py --out /tmp/feed_snapshot/feed_snapshot.json \
   --meta-out ../docs/feed/runs/SNAPSHOT_META_<date>.json --window-start 2025-09-01 --window-end <today> --today <today>

# 2) dry-run — 대상 DB write 0 (변환·대사 미리보기)
DATABASE_URL=<local> python scripts/feed_source_initial_load.py --dry-run --snapshot /tmp/feed_snapshot/feed_snapshot.json \
   --window-start 2025-09-01 --window-end <today> --today <today> --out ../docs/feed/runs/L1_dry_run_<date>.json

# 3) target-local — 적재 + 자동 대사 (exit 0 = mismatch 0, exit 3 = mismatch 있음)
DATABASE_URL=<local> python scripts/feed_source_initial_load.py --target-local --snapshot ... --batch-size 1000 --out ../docs/feed/runs/L1_load_<date>.json

# 4) projection 검증 (persisted → FeedInput → 엔진 vs Oracle 독립 집계)
DATABASE_URL=<local> python scripts/feed_source_projection_validate.py --indep /tmp/feed_snapshot/feed_snapshot.indep.json \
   --shadow ../docs/feed/reports/SHADOW_ORACLE_FEED_20260922.json --today <today> --out ../docs/feed/runs/L4_<date>.json
```

## 4. Expected counts (참고 — 실행 시 재확인)

```text
로컬 실측 2026-09-22 (9농장 · 2025-09-01~2026-09-22): source 5,461 · gen-1 5,461 · ACTIVE 5,202 · INACTIVE 259
quantity ACCEPTED 5,198 · cost ACCEPTED 4,312 (정정: 이전 4,364 는 옮겨 적기 오류) · 재실행 unchanged 5,461 · 정정 시 새 revision = 정정 행 수 · 소실 = RETRACTED
```

## 5. Reconciliation (자동, 스크립트 내장)

grain: total · farm · month · farm×month · source_status · quantity_status · cost_status
invariants: payload_hash NULL 0 · currency NULL 0 · non-KRW 0 · non-DELIVERED 0 · current/identity ≤ 1 · scope_hash · watermark
projection: quantity/cost/unit_price/mix vs Oracle SQL · lineage 전량 역추적 · 결과 basis=DELIVERED

## 6. Failure handling

| 상황 | 원장 | 데이터 | 조치 |
|---|---|---|---|
| Oracle 연결/timeout/권한 | `SOURCE_UNAVAILABLE` + `notes.error_class` | 변경 0 · 철회 0 | 원인 해소 후 재실행 (멱등) |
| 저장 중 예외 | `SYNC_FAILED` + `error_class` (`TARGET_DB` 등) · `data_changed=false` | SAVEPOINT rollback — 부분 커밋 없음 | 재실행 = 처음부터 (`resumable: restart_from_scratch_idempotent`) |
| 빈 결과 | `SUCCEEDED` + `notes.empty_source=true` | 철회 0 | 소스 상태 확인 — 빈 결과는 삭제가 아니다 |
| 농장 침묵 | `notes.retraction_skipped_farms` | 그 농장 철회 0 | 다음 실행에서 다시 판단 |
| mismatch > 0 | exit 3 | 적재는 됐음 | **STOP** — 분류(SPEC/SOURCE/PERSISTENCE/PROJECTION/SYNC/ENGINE/TEST/EXPECTED/UNEXPLAINED) 전에 다음 단계 금지 |

## 7. Rollback

- 데이터: 물리 삭제 없음. 잘못된 적재는 "해당 sync_run_id 의 revision 을 superseded 처리" 로 되돌린다(스크립트 없음 — 결재 패킷에 포함 예정). 원천을 다시 넣으면 revive.
- 스키마: `alembic downgrade -1` 은 **두 테이블을 통째로 drop** 한다(L7 실측: 다른 테이블 무영향). 프로덕션에서는 백업 뒤에만.

## 8. Cleanup

- snapshot 파일(원자료 포함)은 repo 밖 임시 경로. 작업 종료 시 삭제하고 `OVERNIGHT_RESULTS` §END 에 삭제 여부 기록.
- 일회용 DB(`pigos_feedload*`) DROP.

### 8-1. 파일 권한 · 잔여 스윕 (2026-09-23 리뷰 ② 반영 — 필수)

```text
시작      원천 데이터를 만지는 모든 셸·스크립트 첫 줄 `umask 077`. 서버 작업 디렉터리는 `mktemp -d`(700) — 공용 경로(/var/tmp/feed 등) 금지.
          컨테이너가 써야 하면 uid 를 맞춘다(appuser 1000 = ubuntu 1000). chmod 777 디렉터리 금지(2026-09-23 에 한 번 썼다).
원천 행   가능하면 서버로 옮기지 않는다. 대사용 집계는 `feed_source_snapshot_take.py --indep-only`(행 0 · 마스킹 키 · 600).
종료 후   작업 디렉터리 삭제, 그리고 **이름 패턴이 아니라 시간으로** 스윕한다 — 패턴 스윕은 2026-09-23 에 두 건을 놓쳤다:
            sudo find /tmp /var/tmp /home/ubuntu /root -xdev -newermt "<작업 시작 시각>" -type f 2>/dev/null
          나온 파일을 하나씩 분류(우리 것 / 백업 cron / 타 프로젝트)해 우리 것은 repo 사본과 대조 후 삭제, 결과를 실행 기록에 남긴다.
          워크스테이션 scratchpad 도 같은 방식으로.
```

## 9. Estimated runtime (근거 있는 것만)

```text
관측(로컬 PG, batch 1000): 5,461행 → 5.6 s (≈1,000 rows/s, 대사 포함) · 재실행(변경 0) 1.8 s · Oracle fetch 0.78 s
승인 범위(9농장 · 13개월)  ≈ 5.5k 행 → 수 초. 67농장 전체(12m 21.6k 행)로 늘려도 ≈ 25 s ESTIMATED(선형 가정, 미실측)
projection 쿼리: partial index scan 0.27 ms / farm-month
```

## 10. STOP conditions

Oracle 쓰기 경로 발견 · 로컬 외 PG 접속 · scope hash 불일치 · mismatch 미분류 · currency ≠ KRW 행 · basis ≠ DELIVERED 행 · alembic heads > 1 · CI red(원인 미상) · 원자료가 repo/log 에 남음.

## 11. 기록 규칙 (2026-09-23 리뷰 반영)

```text
모든 검증 명령은 --out 으로 파일을 쓴다 — stdout 만 남기는 검증은 금지(TRANSCRIBED 등급이 생긴다)
실행 기록의 수치는 api/scripts/feed_load_report.py 로만 만든다 — 손으로 쓴 숫자는 CI(test_feed_load_report)가 막는다
실제로 돌린 스크립트는 run 폴더 ran/ 에 원본 그대로 · 승인본과 다르면 diff 를 함께 둔다
스냅샷 원자료: 권한 600 · 가능하면 호스트에서 직접 추출(전송 없음) · 폐기 후 검색으로 검증하고 결과를 기록한다
배포 전: ops/deploy.sh 0/5 드리프트 게이트(DB 리비전 == 코드 head)
```
