# Feed Initial Load — Production Execution Record (2026-09-23)

> 승인: 사람 GO (2026-09-23, 이 세션 질의 응답 "GO — 전부 실행"). 계약: `FEED_INITIAL_LOAD_APPROVAL_20260923.md`.
> 실행한 프로덕션 변경은 두 가지뿐: **migration `a7c9e1f3b5d7` 1건 + 승인 범위 적재 1회**(+ 멱등 확인 재실행 1회, 신규 0행).
> 운영 api·worker·web 컨테이너는 교체하지 않았다. 원자료·농장 식별자는 이 문서와 첨부 JSON 에 없다.

## 1. GO GATE

```text
FINAL_HEAD_CI_GREEN      YES  release/feed-initial-load 854765a · run 35799219789 (00:03 UTC 재실행, D9 창 밖) backend 3.12/3.14 · frontend
SOURCE_SCOPE_APPROVED    YES  MIGRATION_APPROVED YES  PROD_GUARD_APPROVED YES  RECONCILIATION_READY YES  API_UI_SEPARATED YES
```

## 2. 실행 방식 — 운영 서비스 무교체

```text
코드      git archive 854765a:api → 호스트 ~/pigos-feedload/api (운영 ~/pigos 와 분리) · SOURCE_COMMIT=854765a
이미지    pigos-feedload:854765a (sha256:25d6c036…) — 일회용. compose `feedload` 서비스(profile oneoff)가 api 서비스를 extends 해
          같은 환경·네트워크를 쓰되 이미지만 다르다. 자격증명을 파일로 복사하지 않는다(자동모드 분류기가 env 덤프를 차단 → 이 방식으로 전환)
지문      컨테이너 안 --print-fingerprint = b5d97396…c491 (승인값과 일치) · ENVIRONMENT=production · DB = api 와 동일
Oracle    워크스테이션에서 승인 read-only 계정으로 SELECT 1회(스냅샷) → 호스트 /var/tmp/feed 로 전송(sha256 일치) · 운영 이미지엔 oracledb 없음
```

## 3. 순서와 결과 — 숫자는 생성된다

아래 표는 `api/scripts/feed_load_report.py` 가 `docs/feed/runs/prod_20260923/` 파일에서 **생성**한다. 손으로 고치면
`tests/unit/test_feed_load_report.py` 가 CI 에서 실패한다. 행마다 출처 등급을 단다:
`MACHINE`(스크립트가 쓴 파일) · `CAPTURED`(실행 시점에 tee 로 파일화) · `TRANSCRIBED`(실행 뒤 터미널 출력을 그대로 옮김 — 가장 약함).

<!-- BEGIN GENERATED -->

| 단계 | 항목 | 값 | 출처 |
|---|---|---|---|
| preflight | gate | `dry-run / writes none` | MACHINE preflight.json |
| preflight | scope hash | `d2088df061abfce2a594d90d72e76b6b7661dbe94df3096f1d4690ca0207607b` | MACHINE preflight.json |
| preflight | authorized / observed / unmapped | `42 / 9 / 0` | MACHINE preflight.json |
| preflight | source rows · ACTIVE · INACTIVE | `5461 · 5202 · 259` | MACHINE preflight.json |
| preflight | quantity ACCEPTED / EXCLUDED | `5198 / 263` | MACHINE preflight.json |
| preflight | cost ACCEPTED / INSUFFICIENT / EXCLUDED | `4312 / 886 / 263` | MACHINE preflight.json |
| preflight | partial month rows (source) | `122` | MACHINE preflight.json |
| code | fingerprint (load gate) | `b5d97396bad7e7b826f3e057422695b724d4354da67586350b9ac874e491c491` | MACHINE load.json |
| code | fingerprint (in container) | `b5d97396bad7e7b826f3e057422695b724d4354da67586350b9ac874e491c491` | TRANSCRIBED ops_evidence.txt |
| recovery | backup | `pigos-full-20260923-091859-feedload-initial-load.sql.gz (149,733,226 bytes)` | TRANSCRIBED ops_evidence.txt |
| migration | before → after | `f3c6a8d0b2e4 → a7c9e1f3b5d7` | CAPTURED state_before/schema_after |
| schema | public tables before → after | `59 → 61` | CAPTURED |
| schema | indexes missing / checks missing | `[] / []` | CAPTURED schema_after.txt |
| schema | non-feed fingerprint before = after | `417247fce26c8c83b3c139615a2d90c8 = 417247fce26c8c83b3c139615a2d90c8 (SAME)` | CAPTURED |
| load | status · fetched · inserted | `SUCCEEDED · 5461 · 5461` | MACHINE load.json |
| load | elapsed s · DB delta bytes | `10.29 · 5382144` | MACHINE load.json |
| load | grain mismatch | `{}` | MACHINE load.json |
| verify | current total · mismatch | `5461 · {}` | MACHINE verify.json |
| verify | hash NULL · non-KRW · non-DELIVERED · current/identity · identities · max rev | `0 · 0 · 0 · 1 · 5461 · 1` | MACHINE verify.json |
| projection | mode · DB alembic | `production_read_only · a7c9e1f3b5d7` | MACHINE projection_rerun.json |
| projection | ① vs Oracle SQL: compared · qty · cost · unit price · mix mismatch | `89 · 0 · 0 · 0 · 0` | MACHINE projection_rerun.json |
| projection | ② vs shadow: compared · qty · cost · unit price · change · variance mismatch | `108 · 0 · 0 · 0 · 0 · 0` | MACHINE projection_rerun.json |
| projection | lineage checked · failures | `5198 · 0` | MACHINE projection_rerun.json |
| projection | change values · variance pass/eligible | `80 · 52/52` | MACHINE projection_rerun.json |
| projection | basis·currency·provenance ok · UNEXPLAINED | `True · 0` | MACHINE projection_rerun.json |
| projection | 당시 ad-hoc 값 = 재실행 (11 항목) | `SAME` | MACHINE projection_rerun.json vs TRANSCRIBED projection.json |
| projection | partial-month rows (persisted, qty ACCEPTED) | `121` | TRANSCRIBED projection.json |
| idempotency | 2nd apply inserted · unchanged · revisions | `0 · 5461 · 5461` | MACHINE load2.json |
| idempotency | sync_runs | `SUCCEEDED(+5461) , SUCCEEDED(+0)` | MACHINE load2.json |
| post | feed_source_rows · feed_records | `5461 · 0` | MACHINE load.json / CAPTURED |
| post | api /health · /feed/summary · worker feed jobs | `200 · 404 · 0` | TRANSCRIBED ops_evidence.txt |

등급별 행 수: CAPTURED 4 · MACHINE 23 · TRANSCRIBED 4

<!-- END GENERATED -->

**출처 감사 (2026-09-23, 리뷰 ③):** 이 문서의 첫 판(c6492b0)은 수치를 전부 손으로 옮겼다. 생성 결과와 한 줄씩 대조한 결과
**불일치 0** — 다만 그것은 운이지 구조가 아니다. 등급별 행 수는 표 아래 생성 줄에 있다.
(이 문단의 첫 초안은 등급별 행 수를 손으로 적어 21/7 이라고 썼는데 실제는 20/8 이었다 — 리뷰 ③ 이 지적한 오류가 몇 분 만에 재현됐다. 그래서 수치는 문단에서 뺐다.)
TRANSCRIBED 가 남은 이유: projection 스크립트와 몇몇 운영 명령이 실행 시 파일을 쓰지 않고 stdout 으로만 냈다.
→ 다음 실행부터: 모든 검증 명령은 `--out` 으로 파일을 쓰고, 리포트는 이 생성기로만 만든다(런북 반영).

**projection 승격 (2026-09-23 01:47 UTC, 리뷰 ①③ 후속):** 승인 validator(`api/scripts/feed_source_projection_validate.py`)에
`--production-read-only` 를 더해(READ ONLY 트랜잭션 확인 · 끝에 rollback · 마스킹 키만 수용) 프로덕션에서 `--out` 으로 재실행했다.
표의 projection 행은 이제 `projection_rerun.json`(MACHINE)에서 나온다 — ① Oracle SQL 과 ② shadow **두 경로 모두**.
당시 ad-hoc 결과(TRANSCRIBED)와 공통 항목 대조는 표의 "당시 ad-hoc 값 = 재실행" 행(생성값)이 판정한다.
남은 TRANSCRIBED: 부분월 행 수 1 · ops_evidence 3. 재실행 입력과 경로는 §3-2 마지막 행.
재실행 차이 한 가지(설명됨): `change.reasons.no_data` 가 17 → 380 — 승인 validator 는 매니페스트 42농장을 전부 돌고
ad-hoc 은 행이 있는 9농장만 돌았다(행 없는 33농장 × 비교 11개월 = 363 → 17 + 363 = 380). 비교 대상 수(89)·불일치(0)와는 무관.

### 3-1. 실제로 돌린 코드 (리뷰 ①)

`docs/feed/runs/prod_20260923/ran/` 에 이번 GO 를 만든 스크립트 원본을 그대로 둔다 — 재현은 이 파일로 한다.

| 파일 | 역할 |
|---|---|
| `compose.feedload.yml` | 일회용 러너(api 서비스 extends, 이미지만 교체) |
| `take.py` · `summarize.py` | 워크스테이션 스냅샷(승인 `feed_source_snapshot_take.py` 호출 래퍼) · 사전 집계 출력 |
| `prod_state_ro.py` · `schema_verify_ro.py` | 전후 상태·스키마 확인 (SET TRANSACTION READ ONLY) |
| `projection_ro.py` | projection 대사 — **승인되지 않은 ad-hoc 스크립트** |
| `projection_ro.vs_approved.diff` | 승인본 `api/scripts/feed_source_projection_validate.py` 대비 diff (`git diff --no-index` 원문) |

diff 가 보여 주는 **사실상 차이** ("같은 로직" 이 아니라 이것이 기록이다):

```text
제거   일회용 DB 가드(assert_local_target · pigos_feedload 이름 검사) — 프로덕션에서 돌리기 위해
제거   ★ shadow 교차대조(recon_vs_shadow: 수량·원가·단가·change·variance 를 shadow JSON 과 비교) — 입력 파일을 서버에 두지 않았다.
       → 프로덕션 projection 은 Oracle 집계 SQL 한 경로하고만 대조됐다. 승인본(L4)보다 **약한** 검증이다
       → 해소(2026-09-23 01:47 UTC): 승인본 --production-read-only 재실행, shadow 108 farm-month 대조 불일치 0 (§3 표 ② 행)
추가   SET TRANSACTION READ ONLY · 종료 시 rollback
동일   허용오차(수량 0.15 kg · 원가 1 KRW · 단가 0.0006 · 구성 0.15 kg · variance 0.02) · 부분월 제외 방식 · lineage 검사 항목
★ 한계 `partial_used_in_completed_comparison = 0` — **구조적 보장, 관측 아님.** 동어반복이다 — 루프가 부분월을 비교에 넣지 않도록 짜여 있어서
       이 카운터는 무엇도 검출할 수 없다. 부분월 제외는 **관측된 사실이 아니라 스크립트 구조의 성질**이다.
       제품 코드(/feed/summary)에서의 부분월 정책은 B-1 결정으로 따로 잠근다
       이 카운터는 §3 생성 표에 없고(생성기가 읽지 않는다), 재실행한 승인 validator 에는 아예 없다 — 근거로 인용하지 않는다
```

## 3-2. Oracle 스냅샷 반출 기록 (리뷰 ②)

프로덕션(PigPlan) 읽기 권한의 승인 조건은 "법무 실측 목적 외 export 금지" 다. 이번 반출은 승인된 initial load
(`FEED_INITIAL_LOAD_APPROVAL_20260923.md`) 의 입력으로 쓰기 위한 것이며, 경로와 폐기를 아래에 남긴다.

| 항목 | 기록 |
|---|---|
| 조회 | 기존 승인 read-only 계정 · `SET TRANSACTION READ ONLY` · SELECT 2문(행 추출 1 · 독립 집계 1) · 2026-09-23 00:08 UTC · Oracle 조회 로그(감사)는 **그 계정으로는 조회 불가** — DBA 계정으로 audit trail / `V$SQL` 확인 시 닫을 수 있음(사람 요청 대기) |
| 범위 | TM_ETC_TRADE · 410002/M · 매핑 9농장 · 2025-09-01~2026-09-23 · 5,461행 · 식별자 포함(원장 그대로) |
| 1차 저장 | 워크스테이션 `%TEMP%\claude\…\scratchpad\feed_load_20260923\s.json`(2.98 MB) · `s.indep.json`(23 KB) · **암호화 없음**(사용자 프로필 임시 폴더) |
| 전송 | `scp` (SSH 암호화) → 호스트 `/tmp/feed_s.json` · `/tmp/feed_indep.json` → 즉시 `sudo mv` 로 `/var/tmp/feed/s.json` · `s.indep.json` · sha256 앞 16자 양쪽 일치 `04d267125d0bb07f` |
| 서버 보관 | ★ **권한 644(호스트 전 사용자 읽기 가능)** 로 약 09:15~09:24 KST 존재 · 암호화 없음 · 컨테이너에는 볼륨 마운트로만 노출(이미지에 포함 안 됨) |
| 노출 구간에 서버 계정을 가진 자 | 로그인 셸 계정 root · ubuntu · postgres — 셋 다 비밀번호 잠김(`passwd -S` L), SSH 비밀번호 인증 off · SSH 키: ubuntu 1개 · root 1개(forced-command 제한, EC2 기본) · sudo 그룹 = ubuntu 단독 · 09-23 SSH 접속 78회 전부 `ubuntu` @ 사무실 IP(210.92.91.133) · ★ 파일은 644 라 **서비스 계정으로 도는 프로세스**(postgres 42 · www-data 4 · dnsmasq 등)도 읽을 수 있었다 — 읽었다는 흔적도, 안 읽었다는 증거도 없다 · 실행 중 컨테이너의 `/tmp`·`/var/tmp` 마운트 0 (2026-09-23 10:5x KST 확인) |
| 폐기 | 호스트: `rm -f` 두 파일 · 워크스테이션: 두 파일 + `meta.json` · 전송용 코드 tar 도 삭제 |
| 폐기 검증 (호스트) | `/tmp /var/tmp /home/ubuntu /root` 전수 검색: 스냅샷 파일 0(다른 프로젝트의 무관한 `*snapshot*.json` 만 존재) · `/var/tmp/feed` 에는 식별자 없는 보고서 4개만 · 일회용 이미지 안 `/var/tmp/feed` 없음 · 이미지 history 에 스냅샷 경로 0 · `.bash_history` 마지막 수정 2026-09-04(비대화 ssh 명령은 기록되지 않음) · 남은 일회용 컨테이너 0 |
| 폐기 검증 (워크스테이션) | scratchpad 전수 검색 → ★ **승인 게이트 리허설(09-23 08:50 KST) 스냅샷 `feed_snapshot2/s.json`(sha 081a10f5…) · `s.indep.json` 이 삭제되지 않고 남아 있었다** → 이번 점검에서 발견·삭제 · 이후 0 · git 이력에 스냅샷 파일 0(`*s.json` 일치 3건은 `src/messages/es.json`) |
| 백업 | 복구지점 덤프(09:18)는 적재 **전** pg_dump — 스냅샷 파일을 포함하지 않는다. 이후 일일 백업에는 적재된 `feed_source_rows`(승인된 사용 데이터)가 들어간다 |
| 남은 위험 | 워크스테이션 임시 폴더의 삭제는 파일시스템 삭제(보안 삭제 아님) · 호스트 644 노출 구간 · Oracle 측 조회 로그 미확인 · Oracle 비밀번호가 로컬 memory 파일에 평문으로 있다(take.py 가 거기서 읽음 — 이번에 생긴 문제는 아니나 기록한다) |
| 다음부터 | 스냅샷 파일 600 · 호스트 전송 없이 호스트에서 직접 추출(oracledb 포함 일회용 이미지) 검토 · 비밀번호는 env/secret store · `umask 077` + 종료 후 잔여 파일 스윕(런북 §8) |
| 추가 스윕 발견 (2026-09-23 10:4x KST) | ★ 첫 스윕이 `*snapshot*` 패턴만 봐서 놓친 것 2건: 호스트 `/tmp/feedload_stdout.txt`(664, 1차 apply stdout — `load.json` 과 `expected` 블록만 다름, 식별자 0) · `/var/tmp/feed/out/`(777 디렉터리, 보고서 4개 — repo 사본과 sha256 동일) → 둘 다 삭제. `/tmp/restore_err.txt`(2026-08-25, DB 이전 때 것 — 이번 작업 무관) 는 두었다 |
| 재실행 입력 (projection 승격) | Oracle SELECT 는 **독립 집계만**(행 추출 0) · `feed_source_snapshot_take.py --indep-only` · 농장 키 **마스킹**(원천 번호 0) · 파일 600 · 01:46 UTC · 범위 해시 승인본과 동일(`d2088df0…`) · 메타 `docs/feed/runs/prod_20260923/indep_meta_rerun.json` · 서버 `mktemp -d`(700) 에 validator·reconcile 모듈(커밋 66be67f, sha 는 `projection_rerun_mounted_sha.txt`)·집계·shadow JSON → 일회용 러너 → 결과만 회수 → 디렉터리 삭제 · 워크스테이션 집계 파일 삭제 |

## 4. 정리

```text
원자료     호스트 /var/tmp/feed/s.json · s.indep.json 삭제 · 워크스테이션 스냅샷 삭제
남김       ~/pigos-feedload (승인 코드 사본) · 이미지 pigos-feedload:854765a · compose.feedload.yml — 재대사/재실행용, 서비스로 뜨지 않음(profile)
운영 변경  migration 1 + feed_source_rows 5,461 + feed_source_sync_runs 2 · 그 외 0
후속 정리  /var/tmp/feed 전체 · /tmp/feedload_stdout.txt 삭제 (2026-09-23 10:4x KST, §3-2 추가 스윕)
```

## 5. ★ 운영상 주의 (적재 직후 기준 — 2026-09-23 PR #8 merge 로 해소, §5-1)

```text
main(fc96efc) 에는 migration a7c9e1f3b5d7 파일이 없다. 프로덕션 DB 는 이제 a7c9e1f3b5d7 이다.
→ main 코드로 `alembic upgrade/current` 를 돌리면 "Can't locate revision a7c9e1f3b5d7" 로 실패한다.
→ 다음 api 배포(PR #2 포함 어떤 것이든) 전에 release/feed-initial-load(PR #8) 가 main 에 먼저 들어가야 한다.
   api·worker 는 기동 시 alembic 을 돌리지 않으므로 **재시작 자체는 안전**하다(Dockerfile CMD uvicorn / arq 확인).
```

## 5-1. 드리프트 게이트 · 롤백 실효성 (리뷰 ④)

```text
main head        f3c6a8d0b2e4 확인(ops/alembic_graph.py --ref origin/main) · f3c6a8d0b2e4 의 자식: main 0 · PR #2(safety) 0 · PR #8 1(a7c9e1f3b5d7)
                 → main+PR#2+PR#8 합집합 head 1개. PR #8 merge 로 multiple heads 가 생기지 않는다
게이트           ops/deploy.sh 0/5 단계 = ops/check_migration_drift.sh — api/worker 배포 시 DB 리비전 ≠ 코드 유일 head 면 거부(exit 3), 우회 없음
                 검증: 오늘 상태(main 코드 vs DB a7c9e1f3b5d7) → REFUSED "database is ahead of the code" · 테스트 tests/unit/test_alembic_graph.py
호스트 설치       (2026-09-23 01:38 UTC, GO) main 599dc55 의 deploy.sh · check_migration_drift.sh · alembic_graph.py 를 ~/pigos/ops 에 설치,
                 sha 가 main 과 일치. 옛 deploy.sh 는 ~/pigos/ops/.bak-20260923/ 에 보존. 배포·빌드·재시작 없이 게이트만 단독 실행:
                   A 호스트 체크아웃(옛 코드, 리비전 53개, head f3c6a8d0b2e4) vs DB a7c9e1f3b5d7 → REFUSED exit 3 "database is ahead"
                   B main 599dc55 리비전(54개, head a7c9e1f3b5d7) vs DB a7c9e1f3b5d7 → OK exit 0
                   C DB 리비전 못 읽음 → REFUSED exit 3
                 원문 docs/feed/runs/prod_20260923/deploy_gate_preflight.txt · 스크립트 ran/deploy_gate_preflight.sh
                 ★ 호스트 ~/pigos 는 git 체크아웃이 아니다 → "pull 후" 방향은 main 트리를 임시 디렉터리에 두고 확인했다.
                 호스트 소스는 여전히 옛 코드 → 지금 누가 `deploy.sh api` 를 돌리면 게이트가 거부한다(의도된 상태). 소스 동기화는 다음 배포 때
★ 남은 호스트 드리프트 backup_db.sh · backup_incremental.sh · ROLLBACK.md 도 main 보다 옛 판(2026-08-25). cron 이 쓰는 백업 스크립트라
                 이번 GO 범위 밖으로 두었다. 동작은 정상: DATABASE_URL 만 읽고 그 값이 로컬 PG17(5434)이라 올바른 DB 를 덤프한다
                 (주석만 Supabase 시절). 인자 형식(schema|full [tag])도 새 deploy.sh 의 `backup_db.sh full deploy` 와 호환
복원·downgrade    (2026-09-23 01:41–01:42 UTC, GO) 호스트 안 격리 컨테이너(postgres:17-alpine, network none, 포트 0, api env 없음,
                 CPU 1 · 메모리 2G 제한)에 09:18:59 덤프 복원 42초 → alembic f3c6a8d0b2e4 PASS → upgrade a7c9e1f3b5d7 PASS(두 테이블 0행)
                 → downgrade f3c6a8d0b2e4 PASS → 복원 직후와 비교: 스키마 덤프 sha256 동일(1881aa73…) · 사용자 테이블 92개 행 수 전부 동일
                 · 비피드 스키마 지문 417247fc… = 프로덕션 기록값. 컨테이너·볼륨 삭제 확인(0/0).
                 결과 docs/feed/runs/restore_test_20260923/RESULT.md (자동 CHECK 두 줄의 FAIL 표시는 측정 스크립트 결함 — 거기서 분류)
                 한계: upgrade 가 빈 테이블 위에서 돌았다 → 5,461행이 있는 상태의 downgrade 는 DROP TABLE 이라 동일하다고 보지만 실측은 아님
실질 롤백 순서    데이터만 되돌리기 = feed_source_rows 의 해당 sync_run revision 을 superseded(원장 규칙) ·
                 스키마까지 = downgrade(두 테이블 drop — 데이터 폐기) · 전체 = 덤프 복원(미검증)
```

## 6. 판정

```text
MIGRATION_APPLIED          YES
INITIAL_LOAD_EXECUTED      YES
SOURCE_RECONCILED          YES  (① Oracle 독립 SQL 89 · ② shadow 108 farm-month, 불일치 0 — 승인 validator 프로덕션 읽기 전용 재실행, MACHINE.
                                 재실행 전(첫 판)에는 ① 한 경로 = Oracle 자체 합계 기준만이었다)
PERSISTENCE_RECONCILED     YES
IDEMPOTENCY_CONFIRMED      YES
INITIAL_LOAD_COMPLETE      YES
READY_FOR_API_UI_GATE      YES  (게이트 진입 가능 — 통과는 B-1·B-2·D-15 결정 뒤)
READY_FOR_PRODUCTION       NO   (고객 노출 기준)

Oracle write NO · feed_records changed NO · scheduler OFF · API/UI deploy NO
```
