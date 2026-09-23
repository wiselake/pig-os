# 복원 리허설 + a7c9e1f3b5d7 upgrade/downgrade — 2026-09-23

> GO: 대표 2026-09-23 ("복원 테스트 — GO, 저트래픽 시간 · 디스크 먼저 · 격리 컨테이너 · 파일로 남기고 삭제").
> 원문 로그 `run.log`, 스크립트 `restore_test.sh`(실행한 그대로). 이 문서는 해석만 한다 — 수치는 옆 파일에 있다.

## 조건 확인

| 조건 | 결과 | 근거 |
|---|---|---|
| 저트래픽 | 10:39 KST load 0.08 · nginx 그 시간대 요청 54건(대부분 이번 작업 자신) | 실행 직전 `uptime` · access.log 시간별 집계 |
| 디스크 먼저 | 50,795 MB 여유 / 96 GB | `run.log` disk_before |
| 격리 | `--network none` · 포트 0 · api env 없음(컨테이너 env 는 postgres 이미지 기본 + 일회용 비밀번호) · CPU 1 · 메모리 2G | `run.log` isolation 줄 |
| 비밀번호 | `openssl rand` 일회용, 출력·저장 없음, 컨테이너와 함께 소멸 | `restore_test.sh` |
| 삭제 | container_left=0 · volume_left=0 | `run.log` 마지막 줄 |

덤프: `pigos-full-20260923-091859-feedload-initial-load.sql.gz` 149,733,226 bytes · sha256 앞 16자 `27b5fde1a1c763d0` · PG 17.11 ↔ 복원 이미지 psql 17.11.

## 결과

| 단계 | 판정 | 근거 파일 |
|---|---|---|
| 복원 | rc 0 · 42초 · psql 출력 47줄(setval 결과 + `wal_level` 경고 1 — 덤프의 `CREATE PUBLICATION` 1건, 복원엔 무해) | `restore_psql.txt` |
| 복원 직후 alembic = f3c6a8d0b2e4 | PASS | `alembic_s0_restored.txt` |
| 복원본 비피드 스키마 지문 = 프로덕션 기록값 417247fc… | 일치 | `fp_nonfeed_s0_restored.txt` · 실행 기록 §3 |
| upgrade → a7c9e1f3b5d7 | PASS · feed_source_rows 0 · feed_source_sync_runs 0 · 비피드 지문 불변 | `alembic_upgrade.txt` · `rowcounts_s1_upgraded.tsv` |
| downgrade → f3c6a8d0b2e4 | PASS | `alembic_downgrade.txt` |
| 복원 직후 vs downgrade 후 — 스키마 | 동일 (schema-only 덤프 sha256 `1881aa73…` 양쪽 같음, diff 0바이트) | `schema_sha256.txt` · `diff_schema_s0_s2.txt` |
| 복원 직후 vs downgrade 후 — 행 수 | 사용자 테이블 92개 전부 동일(합계 2,495,564 — 측정용 임시표 제외) | `rowcounts_s0_restored.tsv` · `rowcounts_s2_downgraded.tsv` |

## ★ 자동 CHECK 가 FAIL 로 찍은 두 줄 — 측정 스크립트 결함, 데이터 차이 아님

`run.log` 는 고치지 않았다. 대신 여기서 분류한다.

1. `CHECK rowcounts identical : FAIL` — 행 수를 세는 스크립트가 만든 **자기 임시 테이블** `pg_temp_N._rc` 가 목록에 들어갔고,
   세션마다 스키마 이름(`pg_temp_4` ↔ `pg_temp_14`)이 달라 diff 가 났다. 값은 양쪽 92 로 같다. `diff_rowcounts_s0_s2.txt` 의 유일한 차이가 이 줄이다.
   임시 스키마를 빼고 비교하면 92개 테이블 IDENTICAL(실행 후 호스트에서 `cmp` 로 확인).
2. `s0_s1 … non_feed_changed=53` — 필터가 줄에 `feed_source`/`fsr_`/`fssr_` 가 있는지만 봐서, 새 테이블 두 개의 `CREATE TABLE` 안
   **컬럼 정의 줄**(테이블 이름이 없는 줄)을 비피드로 셌다. `diff_schema_s0_s1.txt` 의 해당 53줄은 전부 두 피드 테이블의 컬럼이다.
   비피드 스키마 불변은 별도 지문(`fp_nonfeed_*` 세 개 동일)이 보여 준다.

→ 다음 실행 전 수정: 행 수 집계에서 `pg_temp%` 제외 · 비피드 판정은 지문으로만.

## 한계

- upgrade 가 **빈** 피드 테이블 위에서 돌았다(덤프가 적재 전). 프로덕션의 downgrade 는 5,461행이 든 두 테이블을 DROP 한다 —
  같은 DDL 이라 결과는 같다고 보지만 데이터가 있는 상태는 실측하지 않았다.
- 복원 대상은 같은 호스트의 격리 컨테이너다. 다른 호스트(재해 복구)로의 복원은 검증 범위 밖.
- 덤프 안 Supabase 시절 스키마(auth·storage·realtime 등)도 그대로 복원됐다 — 복원 절차 자체는 문제 없었다.

## 이것으로 바뀐 것

- 실행 기록 §5-1 "복원 — 가설" → 검증됨. "downgrade — 로컬만" → 프로덕션 덤프 등가 환경에서 검증됨(빈 테이블 한계 위).
- `ops/ROLLBACK.md` §C-0: a7c9 이전 코드로의 롤백 = DB downgrade 먼저.
