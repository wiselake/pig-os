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
| projection | completed farm-months · compared | `108 · 89` | TRANSCRIBED projection.json |
| projection | quantity · cost · unit price · mix mismatch | `0 · 0 · 0 · 0` | TRANSCRIBED projection.json |
| projection | lineage checked · failures | `5198 · 0` | TRANSCRIBED projection.json |
| projection | change values · variance pass/eligible | `80 · 52/52` | TRANSCRIBED projection.json |
| projection | partial-month rows (persisted, qty ACCEPTED) | `121` | TRANSCRIBED projection.json |
| idempotency | 2nd apply inserted · unchanged · revisions | `0 · 5461 · 5461` | MACHINE load2.json |
| idempotency | sync_runs | `SUCCEEDED(+5461) , SUCCEEDED(+0)` | MACHINE load2.json |
| post | feed_source_rows · feed_records | `5461 · 0` | MACHINE load.json / CAPTURED |
| post | api /health · /feed/summary · worker feed jobs | `200 · 404 · 0` | TRANSCRIBED ops_evidence.txt |

등급별 행 수: CAPTURED 4 · MACHINE 16 · TRANSCRIBED 8

<!-- END GENERATED -->

**출처 감사 (2026-09-23, 리뷰 ③):** 이 문서의 첫 판(c6492b0)은 수치를 전부 손으로 옮겼다. 생성 결과와 한 줄씩 대조한 결과
**불일치 0** — 다만 그것은 운이지 구조가 아니다. 등급별 행 수는 표 아래 생성 줄에 있다.
(이 문단의 첫 초안은 등급별 행 수를 손으로 적어 21/7 이라고 썼는데 실제는 20/8 이었다 — 리뷰 ③ 이 지적한 오류가 몇 분 만에 재현됐다. 그래서 수치는 문단에서 뺐다.)
TRANSCRIBED 가 남은 이유: projection 스크립트와 몇몇 운영 명령이 실행 시 파일을 쓰지 않고 stdout 으로만 냈다.
→ 다음 실행부터: 모든 검증 명령은 `--out` 으로 파일을 쓰고, 리포트는 이 생성기로만 만든다(런북 반영).

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
추가   SET TRANSACTION READ ONLY · 종료 시 rollback
동일   허용오차(수량 0.15 kg · 원가 1 KRW · 단가 0.0006 · 구성 0.15 kg · variance 0.02) · 부분월 제외 방식 · lineage 검사 항목
★ 한계 `partial_used_in_completed_comparison = 0` 은 동어반복이다 — 루프가 부분월을 비교에 넣지 않도록 짜여 있어서
       이 카운터는 무엇도 검출할 수 없다. 부분월 제외는 **관측된 사실이 아니라 스크립트 구조의 성질**이다.
       제품 코드(/feed/summary)에서의 부분월 정책은 B-1 결정으로 따로 잠근다
```

## 3-2. Oracle 스냅샷 반출 기록 (리뷰 ②)

프로덕션(PigPlan) 읽기 권한의 승인 조건은 "법무 실측 목적 외 export 금지" 다. 이번 반출은 승인된 initial load
(`FEED_INITIAL_LOAD_APPROVAL_20260923.md`) 의 입력으로 쓰기 위한 것이며, 경로와 폐기를 아래에 남긴다.

| 항목 | 기록 |
|---|---|
| 조회 | 기존 승인 read-only 계정 · `SET TRANSACTION READ ONLY` · SELECT 2문(행 추출 1 · 독립 집계 1) · 2026-09-23 00:08 UTC · Oracle 조회 로그(감사)는 **우리 계정으로 확인 불가** — 존재 여부 미확인 |
| 범위 | TM_ETC_TRADE · 410002/M · 매핑 9농장 · 2025-09-01~2026-09-23 · 5,461행 · 식별자 포함(원장 그대로) |
| 1차 저장 | 워크스테이션 `%TEMP%\claude\…\scratchpad\feed_load_20260923\s.json`(2.98 MB) · `s.indep.json`(23 KB) · **암호화 없음**(사용자 프로필 임시 폴더) |
| 전송 | `scp` (SSH 암호화) → 호스트 `/tmp/feed_s.json` · `/tmp/feed_indep.json` → 즉시 `sudo mv` 로 `/var/tmp/feed/s.json` · `s.indep.json` · sha256 앞 16자 양쪽 일치 `04d267125d0bb07f` |
| 서버 보관 | ★ **권한 644(호스트 전 사용자 읽기 가능)** 로 약 09:15~09:24 KST 존재 · 암호화 없음 · 컨테이너에는 볼륨 마운트로만 노출(이미지에 포함 안 됨) |
| 폐기 | 호스트: `rm -f` 두 파일 · 워크스테이션: 두 파일 + `meta.json` · 전송용 코드 tar 도 삭제 |
| 폐기 검증 (호스트) | `/tmp /var/tmp /home/ubuntu /root` 전수 검색: 스냅샷 파일 0(다른 프로젝트의 무관한 `*snapshot*.json` 만 존재) · `/var/tmp/feed` 에는 식별자 없는 보고서 4개만 · 일회용 이미지 안 `/var/tmp/feed` 없음 · 이미지 history 에 스냅샷 경로 0 · `.bash_history` 마지막 수정 2026-09-04(비대화 ssh 명령은 기록되지 않음) · 남은 일회용 컨테이너 0 |
| 폐기 검증 (워크스테이션) | scratchpad 전수 검색 → ★ **승인 게이트 리허설(09-23 08:50 KST) 스냅샷 `feed_snapshot2/s.json`(sha 081a10f5…) · `s.indep.json` 이 삭제되지 않고 남아 있었다** → 이번 점검에서 발견·삭제 · 이후 0 · git 이력에 스냅샷 파일 0(`*s.json` 일치 3건은 `src/messages/es.json`) |
| 백업 | 복구지점 덤프(09:18)는 적재 **전** pg_dump — 스냅샷 파일을 포함하지 않는다. 이후 일일 백업에는 적재된 `feed_source_rows`(승인된 사용 데이터)가 들어간다 |
| 남은 위험 | 워크스테이션 임시 폴더의 삭제는 파일시스템 삭제(보안 삭제 아님) · 호스트 644 노출 구간 · Oracle 측 조회 로그 미확인 · Oracle 비밀번호가 로컬 memory 파일에 평문으로 있다(take.py 가 거기서 읽음 — 이번에 생긴 문제는 아니나 기록한다) |
| 다음부터 | 스냅샷 파일 600 · 호스트 전송 없이 호스트에서 직접 추출(oracledb 포함 일회용 이미지) 검토 · 비밀번호는 env/secret store |

## 4. 정리

```text
원자료     호스트 /var/tmp/feed/s.json · s.indep.json 삭제 · 워크스테이션 스냅샷 삭제
남김       /var/tmp/feed/out/*.json (식별자 없는 보고서 — 같은 내용을 docs/feed/runs/prod_20260923/ 에 보관)
           ~/pigos-feedload (승인 코드 사본) · 이미지 pigos-feedload:854765a · compose.feedload.yml — 재대사/재실행용, 서비스로 뜨지 않음(profile)
운영 변경  migration 1 + feed_source_rows 5,461 + feed_source_sync_runs 2 · 그 외 0
```

## 5. ★ 운영상 주의 (지금부터 참)

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
★ 호스트 미설치   호스트의 deploy.sh 는 repo 보다 **오래된 판**이다(2026-08 빌드컨텍스트 검사가 없음 — 별도 드리프트).
                 게이트는 repo 에만 있고, 호스트 설치는 프로덕션 변경이라 별도 GO 대기
downgrade        a7c9e1f3b5d7 downgrade 는 **로컬 일회용 DB 에서만** 검증됐다(L7: 적재 후 downgrade → 두 테이블만 drop,
                 무관 테이블 무손실, upgrade 후 스키마·인덱스·제약 해시 동일). 스테이징 환경은 없다 → 프로덕션 등가 환경 검증은 **미실시**
복원              pigos-full-20260923-091859-feedload-initial-load.sql.gz 는 **복원 테스트를 하지 않았다** → 롤백 수단으로는 아직 가설
                 제안: 호스트 안의 일회용 postgres 컨테이너에 복원(데이터가 서버 밖으로 나가지 않게) → 테이블 수·행 수·alembic_version 대조 → 컨테이너 삭제.
                 프로덕션 호스트 작업이라 별도 GO
실질 롤백 순서    데이터만 되돌리기 = feed_source_rows 의 해당 sync_run revision 을 superseded(원장 규칙) ·
                 스키마까지 = downgrade(두 테이블 drop — 데이터 폐기) · 전체 = 덤프 복원(미검증)
```

## 6. 판정

```text
MIGRATION_APPLIED          YES
INITIAL_LOAD_EXECUTED      YES
SOURCE_RECONCILED          YES
PERSISTENCE_RECONCILED     YES
IDEMPOTENCY_CONFIRMED      YES
INITIAL_LOAD_COMPLETE      YES
READY_FOR_API_UI_GATE      YES  (게이트 진입 가능 — 통과는 B-1·B-2·D-15 결정 뒤)
READY_FOR_PRODUCTION       NO   (고객 노출 기준)

Oracle write NO · feed_records changed NO · scheduler OFF · API/UI deploy NO
```
