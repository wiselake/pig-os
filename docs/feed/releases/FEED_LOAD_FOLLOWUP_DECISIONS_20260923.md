# Feed load 후속 — 결정 대기 목록 (2026-09-23)

> 대표 리뷰(2026-09-23) 이후 상태. GO 받은 항목은 실행 결과를, 결정 항목은 선택지와 권고를 적는다.
> 결정이 나면 이 문서에 날짜와 선택을 적고, 구현은 별도 PR 로 한다.

## 상태 한눈에

| # | 항목 | 상태 | 근거 |
|---|---|---|---|
| D-A | gate 에 additive 리비전 허용 목록 도입 | **결정 대기** | §D-A · 안 바꾸는 동안의 비용은 `ops/ROLLBACK.md` §C-0 에 적었다 |
| D-B | 서버 소스를 SHA 로 말할 수 있게(git 체크아웃 또는 manifest tarball) + preflight SHA 대조 | **결정 대기** | §D-B |
| D-C | 적재 전 recovery point 의 보존 (신규 발견) | **결정 대기 · 기한 2026-10-02 03:15 KST** | §D-C |
| — | backup 스크립트 동기화 | **완료** (GO, 수동 실행 확인) | `../runs/prod_20260923/backup_sync_manual_run.txt` |
| — | 적재 후 덤프 복원 테스트 | **완료** (GO) | `../runs/restore_test_postload_20260923/RESULT.md` |
| — | 사료 화면 기획서 초안 | **초안 작성** (GO) | `../FEED_SCREEN_SPEC_DRAFT.md` — B-1·B-2·D-15 를 선택지로 표시 |
| B-1 · B-2 · D-15a/b | 부분월 · FCR 제외 · 공개 범위 | **결정 대기** | 화면 기획서 §5 에서 한 장으로 비교 |
| — | Oracle 조회 로그 | **사람 작업** (Brian, DBA 계정) | 아래 §Oracle |

## D-A. gate 의 additive 허용 목록

**문제.** a7c9 는 테이블 두 개 추가뿐이라 옛 코드가 새 스키마 위에서 그대로 돈다(지금 서버가 실제로 그 상태다 — 옛 이미지 + a7c9 DB).
그런데 `check_migration_drift` 는 "DB 가 코드보다 앞섬"을 전부 거부하므로, 옛 코드로 롤백하려면 downgrade 가 먼저이고 그러면
5,461행이 사라진다. 재적재 = Oracle 재추출 + custody 재실행.

**안 (우회 스위치가 아니라 리뷰 가능한 규칙).**

```text
파일      ops/additive_revisions.txt — 한 줄에 "<revision> <parent> <근거 한 줄>" · PR 리뷰로만 추가
규칙      DB 리비전이 코드에 없으면: DB 리비전에서 parent 를 따라 내려가며, 지나는 리비전이 **전부** 목록에 있고
          코드 head 에 닿으면 PASS("DB 가 additive 리비전 N 개만큼 앞섬: …" 출력) · 하나라도 없으면 지금처럼 REFUSED
판정 보조  목록에 올릴 때 CI 테스트가 해당 migration 의 upgrade() 를 정적 검사: create_table / create_index / nullable add_column 만 허용,
          drop·alter·rename·NOT NULL 추가·데이터 UPDATE 가 있으면 실패 — 사람 판단을 대체하지 않고 실수를 막는다
```

★ **설계상 함정 — 목록의 위치.** 롤백할 때 배포되는 것은 **옛 코드**이고, 옛 코드의 `ops/` 에는 a7c9 가 목록에 없다
(목록은 a7c9 보다 나중에 생긴다). 그래서 목록은 "배포 대상 트리"가 아니라 **호스트에 설치된 게이트 쪽**(`~/pigos/ops`, 지금처럼
main 에서 따로 설치)에서 읽어야 한다. D-B 로 서버 소스를 git 체크아웃으로 바꾸면 `ops/` 도 롤백과 함께 옛것이 되므로,
게이트·목록은 앱 소스와 **분리된 경로**(예: `~/pigos-ops`, main 고정)에 두는 것이 전제다. D-A 와 D-B 는 같이 결정해야 한다.

**권고:** 도입. 비용(재적재·custody 재실행)이 크고, 규칙이 명시적이며, 정적 검사로 잘못 올리는 실수를 막을 수 있다.
안 바꾼다면 현재 `ROLLBACK.md` §C-0 의 비용 기재로 닫는다(적어 두었다).

## D-B. 서버 소스의 SHA

**문제.** `~/pigos` 는 git 체크아웃이 아니다. 이번 주 드리프트 3건(deploy.sh · backup 스크립트 · ROLLBACK.md)이 전부 같은 뿌리 —
서버에 어떤 코드가 있는지 SHA 로 말할 수 없다. backup 스크립트 동기화는 증상 처리다.

| 선택지 | 방식 | 장점 | 비용·위험 |
|---|---|---|---|
| B1 | `~/pigos` 를 git 체크아웃(detached, SHA 고정)으로 전환 · `.env` 등 비추적 파일은 그대로 | `git rev-parse HEAD` · `git status` 로 드리프트가 즉시 보인다 | 서버에 GitHub 읽기 자격(deploy key) 필요 · 전환 1회 작업(현재 파일과 diff 확인 후) |
| B2 | `git archive <sha>` tarball + `MANIFEST`(SHA + 파일별 sha256) 배포 | 서버에 GitHub 자격 불필요 | 서버에서 손으로 고친 파일은 manifest 대조로만 드러난다 |
| 공통 | `deploy.sh <svc> --expect-sha <sha>` — 0/5 앞에 "서버 소스 SHA == 배포 대상 SHA" 대조, 불일치면 거부 | 어느 쪽이든 필요 | — |

**권고:** B2 + 공통 preflight 를 먼저(자격 추가 없이 가능), B1 은 deploy key 발급이 정리되면 전환. 어느 쪽이든 D-A 의
"게이트는 앱 소스와 분리" 전제를 같이 넣는다. 전환 전 현재 서버 트리와 main 의 diff 를 뽑아 **손으로 고친 파일이 있는지** 먼저 본다
(있으면 그것도 이번 드리프트의 일부다).

## D-C. 적재 전 recovery point 보존 (신규 — 기한 있음)

```text
사실   backup_db.sh 보존 정리 = pigos-*.sql.gz 중 `-deploy.sql.gz` 가 아닌 것을 -mtime +7 로 삭제 (구·신 판 동일)
       적재 전 덤프 pigos-full-20260923-091859-feedload-initial-load.sql.gz → 2026-10-02 03:15 KST cron 에서 삭제된다
       S3 사본 없음(당시 호스트 스크립트는 S3 단계가 없는 옛 판). 적재 후 덤프(110831-postload)는 S3 사본 있음
의미   a7c9 적용 **전** 상태로 돌아갈 수 있는 증명된 유일한 지점이 8일 뒤 사라진다
```

| 선택지 | 내용 |
|---|---|
| C1 | S3 로 1회 복사(`aws s3 cp … s3://pigos-db-backup/pigos-db/`) — 기존 백업 경로와 동일 버킷·역할. 버킷 수명주기 규칙은 이 역할로 조회 불가 → 확인 필요 |
| C2 | 보존 규칙에 `-keep.sql.gz` 예외 추가 + 해당 파일 하드링크 `…-keep.sql.gz` (repo 변경 1줄 + 서버 1회) |
| C3 | 그대로 둔다 — 적재 후 덤프 + downgrade(실측 PASS)로 적재 전 **스키마**는 재현 가능. 단 적재 전 **데이터 시점**은 잃는다 |

**권고:** C1 (지금 백업이 이미 쓰는 경로, 추가 권한 없음). 프로덕션 데이터 사본을 하나 더 만드는 일이라 GO 후 실행.

## Oracle 조회 로그 (사람 작업)

```text
1) SELECT value FROM v$option WHERE parameter = 'Unified Auditing';
2) TRUE 면  UNIFIED_AUDIT_TRAIL 에서 DBUSERNAME = <read-only 계정>, EVENT_TIMESTAMP 2026-09-22 ~ 2026-09-23 (UTC 기준 주의)
   FALSE 면 V$SQL / V$SQLAREA 에서 PARSING_SCHEMA_NAME = <계정>, SQL_TEXT LIKE '%TM_ETC_TRADE%' — shared pool 에서 밀려났으면 "확인 불가"
3) 결과(또는 "확인 불가")를 FEED_INITIAL_LOAD_EXECUTION_20260923.md §3-2 조회 행에 한 줄로
```

우리 쪽 조회 시각(UTC): 2026-09-22 shadow·preflight(여러 차례) · 2026-09-23 00:08(적재 스냅샷) · 01:46(집계만, `--indep-only`).
