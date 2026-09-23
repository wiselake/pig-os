# Feed load 후속 — 결정 목록 (2026-09-23)

> 대표 리뷰(2026-09-23) 이후 상태. GO 받은 항목은 실행 결과를, 결정 항목은 선택지와 권고를 적는다.
> 결정이 나면 이 문서에 날짜와 선택을 적고, 구현은 별도 PR 로 한다.
> **2026-09-23 결정 전달(세션)** — 아래 여섯 건 확정. 실행 순서: D-C → D-A+D-B → B-1 → B-2 → D-15 → 화면/API 게이트 검증 → PR #9 → 배포 판단(별도).

## 상태 한눈에

| # | 항목 | 결정 (2026-09-23) | 상태 |
|---|---|---|---|
| D-C | 적재 전 recovery point 보존 | **GO** | **완료** — S3 `recovery-points/` 보존 · 왕복 sha256 일치 · ledger `ops/RECOVERY_POINTS.md` RP-1 |
| D-B | 서버 소스 SHA 고정 | **GO — tarball + SHA manifest 우선** (deploy key 는 나중) | 설계·구현 대기 |
| D-A | additive migration 허용 목록 | **GO — 앱 코드 밖, 서버 deploy gate 에 둔다** | 설계·구현 대기 (D-B 와 한 묶음) |
| B-1 | 부분월 | **완료월 비교에서 제외** — 당월 값은 "MTD/집계 중"으로 표시 가능, 전월 대비 없음, variance 는 완료월만 | 반영 대기 (API·웹) |
| B-2 | 문구·의미 | **DELIVERED 와 FCR 입력원을 분리** — "사료 입고" / "사료 급여·소비" 두 영역 | 반영 대기 (웹·8 로케일) |
| D-15 · Q-0 | 공개 범위 | **REFERENCE_VISIBLE 로 한정 — CUSTOMER_VISIBLE 아님.** KR PigPlan 레퍼런스·내부 계정 = REFERENCE_VISIBLE · 글로벌 상용 고객 = HIDDEN · D-15b(FCR) 보류 | 반영 대기 |
| — | backup 스크립트 동기화 · 적재 후 복원 테스트 · 화면 기획서 초안 | GO (이전) | 완료 |
| — | 오프사이트 백업 공백(2026-08-25 ~ 09-23) | 운영 결함으로 기록 | 기록 — `ops/ROLLBACK.md` 사고 사례 |
| — | Oracle 조회 로그 | 사람 작업 (Brian, DBA 계정) | 대기 — 아래 §Oracle |

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

**결정 (2026-09-23): GO — 목록은 앱 코드(릴리스 tarball) 밖, 서버 deploy gate 쪽에서 독립 관리.** 구조:

```text
release tarball + manifest(code SHA · expected migration head)
        ↓
server-side deploy gate + 독립 관리 additive allowlist  ← 옛 코드로 롤백해도 gate 는 현재 DB 의 additive 리비전을 안다
        ↓
deploy
```

구현 전까지 `ROLLBACK.md` §C-0 의 비용 기재가 유효하다.

## D-B. 서버 소스의 SHA

**문제.** `~/pigos` 는 git 체크아웃이 아니다. 이번 주 드리프트 3건(deploy.sh · backup 스크립트 · ROLLBACK.md)이 전부 같은 뿌리 —
서버에 어떤 코드가 있는지 SHA 로 말할 수 없다. backup 스크립트 동기화는 증상 처리다.

| 선택지 | 방식 | 장점 | 비용·위험 |
|---|---|---|---|
| B1 | `~/pigos` 를 git 체크아웃(detached, SHA 고정)으로 전환 · `.env` 등 비추적 파일은 그대로 | `git rev-parse HEAD` · `git status` 로 드리프트가 즉시 보인다 | 서버에 GitHub 읽기 자격(deploy key) 필요 · 전환 1회 작업(현재 파일과 diff 확인 후) |
| B2 | `git archive <sha>` tarball + `MANIFEST`(SHA + 파일별 sha256) 배포 | 서버에 GitHub 자격 불필요 | 서버에서 손으로 고친 파일은 manifest 대조로만 드러난다 |
| 공통 | `deploy.sh <svc> --expect-sha <sha>` — 0/5 앞에 "서버 소스 SHA == 배포 대상 SHA" 대조, 불일치면 거부 | 어느 쪽이든 필요 | — |

**결정 (2026-09-23): GO — B2(tarball + SHA manifest) 우선 + 공통 preflight.** B1(git 체크아웃)은 deploy key 가 정리되면 재검토. 어느 쪽이든 D-A 의
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

**결정 (2026-09-23): GO (C1).** 실행 2026-09-23 05:52 UTC:

```text
대상     s3://pigos-db-backup/pigos-db/recovery-points/pigos-full-20260923-091859-pre-feed-load.sql.gz
         (일반 백업 경로 pigos-db/ 와 분리된 recovery-points/ 접두사 + 파일명·메타데이터에 pre-feed-load 표식)
검증     크기 149,733,226 = 원본 · S3 에서 다시 내려받아 sha256 = 27b5fde1…b41297 = 원본 · SSE AES256
         (S3 ChecksumSHA256 은 멀티파트 18 조각 합성값이라 파일 sha256 과 형식이 다르다 — 판정은 왕복 sha256 으로)
DB       손대지 않음
남은 것  로컬 원본은 예정대로 2026-10-02 03:15 KST 에 지워진다(S3 사본이 복구점) · 버킷 수명주기는 이 역할로 조회 불가 — 사람 확인
ledger   ops/RECOVERY_POINTS.md RP-1
```

## Oracle 조회 로그 (사람 작업)

```text
1) SELECT value FROM v$option WHERE parameter = 'Unified Auditing';
2) TRUE 면  UNIFIED_AUDIT_TRAIL 에서 DBUSERNAME = <read-only 계정>, EVENT_TIMESTAMP 2026-09-22 ~ 2026-09-23 (UTC 기준 주의)
   FALSE 면 V$SQL / V$SQLAREA 에서 PARSING_SCHEMA_NAME = <계정>, SQL_TEXT LIKE '%TM_ETC_TRADE%' — shared pool 에서 밀려났으면 "확인 불가"
3) 결과(또는 "확인 불가")를 FEED_INITIAL_LOAD_EXECUTION_20260923.md §3-2 조회 행에 한 줄로
```

우리 쪽 조회 시각(UTC): 2026-09-22 shadow·preflight(여러 차례) · 2026-09-23 00:08(적재 스냅샷) · 01:46(집계만, `--indep-only`).
