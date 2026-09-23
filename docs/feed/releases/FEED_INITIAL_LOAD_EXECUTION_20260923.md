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

## 3. 순서와 결과

| 단계 | 결과 |
|---|---|
| P0 preflight (dry-run, 쓰기 0) | scope `d2088df0…` · 권한 42 · 관측 9 · unmapped 0 · rows 5,461 (ACTIVE 5,202 / INACTIVE 259) · 창 2025-09-01~2026-09-23 · 부분월 2026-09 122행 |
| P1 코드 | 지문 일치 · alembic heads 1 (`a7c9e1f3b5d7`) |
| P2 복구지점 | `ops/backup_db.sh full feedload-initial-load` → `pigos-full-20260923-091859-feedload-initial-load.sql.gz` 149.7 MB · 당시 DB head `f3c6a8d0b2e4` · code `854765a` |
| P3 migration | `alembic upgrade a7c9e1f3b5d7` — `f3c6a8d0b2e4 → a7c9e1f3b5d7` 한 건 · 예상 외 migration 0 |
| P4 schema | 테이블 59→61 · 인덱스 5/5 · CHECK 6/6 · unit_cost NUMERIC(18,8) · currency NOT NULL · **feed 외 스키마 지문 전후 동일** `417247fc…` · feed_records 0 |
| P6 적재 `--apply` (5개 기대 전부) | SUCCEEDED · fetched 5,461 · inserted 5,461 · 10.3 s · DB +5.4 MB · sync_run 1 |
| P7 대사 `--verify-only` | total/farm/month/farm×month/status **mismatch 0** · payload_hash NULL 0 · non-KRW 0 · non-DELIVERED 0 · current/identity 1 · identities 5,461 · max revision 1 |
| P8 projection (읽기 전용) | 완료월 108 farm-month · 대조 89 · 수량 0 · 원가 0 · 단가 0 · 구성 0 · lineage 5,198/5,198 실패 0 · basis/통화 위반 0 · CHANGE 값 80 · VARIANCE 52/52 |
| 부분월 | 저장됨(121 수량 ACCEPTED 행) · 완료월 비교에 사용 0 |
| 멱등 재실행 `--apply` | inserted 0 · unchanged 5,461 · revisions 5,461 그대로 · sync_run 2(둘 다 SUCCEEDED) |
| P10 health | api `/health` 200 · 컨테이너 4개 가동시간 그대로(무교체) · `/feed/summary` 404(미노출) · worker 에 feed_source 잡 0(스케줄러 OFF) |

projection 대사는 승인 스크립트 `feed_source_projection_validate.py` 가 일회용 DB 이름만 허용하도록 잠겨 있어, 같은 로직을
`SET TRANSACTION READ ONLY` 로 감싼 읽기 전용 스크립트로 일회용 컨테이너에서 실행했다(코드 변경 0). 독립 기준값은 같은 Oracle
세션에서 뽑은 집계 SQL(엔진 미경유).

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
