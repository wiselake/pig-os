# B-10 오프사이트 백업 복구 — 개발 완료 · 운영 미적용 (2026-09-18)

> **승인 범위**: 개발·테스트·프로덕션 read-only 조사 = 승인. **프로덕션 스크립트 변경 = 미승인.
> S3 수명주기 변경 = 미승인.** 이 문서는 적용 여부를 Brian 이 한 번 보고 결정할 수 있게 만든 패킷이다.
> 브랜치 `fix/b10-offsite-backup-20260918` (origin/main 8a80ea4 기준, PR #2·#3 커밋 없음).

---

## 0. 한 화면

```
B-10 OFFSITE BACKUP — 2026-09-18

DEVELOPMENT
  PATCH_READY          YES   797394e · e708742 · 648a1dc
  TESTED               YES   ops/tests/test_backup.sh 25/25 (DB·클라우드 없이 대역으로)
  RESTORE_COMPATIBLE   YES   패치된 스크립트로 만든 덤프 → 격리 PG17 복원 → 59 tables · alembic head · FK

PRODUCTION
  CHANGED              NO
  OFFSITE_CURRENT      NO    최신 오프사이트 객체 2026-08-25 (24일째)

CURRENT RISK
  local backup and DB share the same EC2 / same /dev/root failure domain

PATCH
  local artifact verification      .part → gzip -t → sha256 → 최종 이름. 실패 시 오프사이트 안 감
  offsite copy                     기존 prefix pigos-db/ · 기존 파일명 · metadata sha256
  remote verification              head-object ContentLength == 로컬 bytes (ETag 미사용) · .sha256 sidecar
  failure exit semantics           ★ 로컬 OK + 오프사이트 실패 → exit 3/4/5, 로컬 보존. 더 이상 exit 0 아님
  freshness checker                ops/check_backup_freshness.sh — CURRENT/STALE/MISSING, 임계 36h 한 곳

TEST     25 passed · 0 failed  (아래 §5)

HUMAN DECISIONS
  S3 lifecycle          UNDECIDED (§7 저장량 표)
  freshness scheduling  UNDECIDED (크론에 넣지 않았다)
  production apply      UNDECIDED (§8 패킷 · §9 runbook)

RECOMMENDED NEXT ACTION
  §8 의 적용 패킷을 읽고 production apply 를 결정한다 — 승인되면 §9 순서 그대로
```

---

## 1. Phase A — 프로덕션 read-only 재확인 (2026-09-18)

기억이나 문서가 아니라 호스트에서 다시 봤다. 비밀값은 출력하지 않았다.

| # | 항목 | 실측 |
|---|---|---|
| 1 | `~/pigos/ops/backup_db.sh` | sha256 `0857e6f6…` · mtime **2026-08-25 14:43** · 오프사이트 단계 **0줄** (`grep -c BACKUP_S3_BUCKET\|aws` = 0) |
| 2 | `backup_incremental.sh` | 있음. §4 |
| 3 | git tracked | 저장소에 `ops/backup_db.sh` 있음 — sha `123e614d…` (8a80ea4). **호스트와 다르다** |
| 4 | 저장소 8/25 이력 | `b374e0d` 2026-08-25 "백업 오프사이트 사본(S3) 경로" — 저장소에는 그날 들어갔다 |
| 5 | cron | `15 3 schema` · `40 3 full` · `5 15 incremental 2` — 변경 없음 |
| 6 | 로컬 최신 | full `2026-09-18 03:40` 149,710,684 B · schema 03:15 36,887 B |
| 7 | 로컬 보관 | 30 파일 · 3.1 GB · KEEP_DAYS=7 (deploy 태그 제외) |
| 8 | 오프사이트 최신 | `pigos-db/pigos-full-20260825-144727-deploy.sql.gz` 2026-08-25 |
| 9 | 명명 | `pigos-db/pigos-{full,schema}-<ts>[-tag].sql.gz` — 패치는 이 규약을 그대로 쓴다 |
| 10 | IAM identity | `assumed-role/pigos-ec2-backup-role/i-03b1…` |
| 11 | 권한 | head-bucket OK · **GetBucketLifecycleConfiguration · GetBucketVersioning AccessDenied** → 버킷 수명주기·버전관리 상태를 이 역할로는 읽을 수 없다 |
| 12 | .env 키 | `BACKUP_S3_BUCKET` · `BACKUP_S3_PREFIX` **있음** (값 미출력) |

### 진단 — 설계 결함이 아니라 배포 결함이었다

```
저장소   ops/backup_db.sh 에 오프사이트 단계가 2026-08-25 부터 있다 (b374e0d)
호스트   같은 날 14:43 자 파일은 그 단계가 없는 판이다
.env     BACKUP_S3_BUCKET 은 설정돼 있다
버킷     8/25 13:45~14:47 객체 6개 — 설정하던 날 손으로 올린 것
→ 코드는 있었고 설정도 있었는데 호스트의 파일이 안 바뀌었다. 공개 방침(ec99391)과 같은 모양이다.
```

그렇다 해도 저장소 판을 그대로 배포하면 안 된다 — 그 판은 오프사이트 실패를 **경고 + exit 0** 으로
끝낸다. 크론이 매일 성공하면서 22일이 지나갔을 경로가 그것이다. §3 이 그것을 고친다.

---

## 2. Phase A-2 — 설계 질문: 무엇을 오프사이트에 올리나

```
full      단독 복원 가능 (B-8 검증). 올린다
schema    단독으로 구조 복원 가능. 올린다 (37KB)
incremental  ★ 올리지 않는다 — §4
```

---

## 3. 패치 내용 (`797394e`)

```
생성      pg_dump | gzip → $OUT.part
검증      빈 덤프 검사(기존) · gzip -t · bytes · sha256 → $OUT.sha256   ← 실패면 오프사이트로 안 간다
완료      mv .part → 최종 이름 (쓰다 만 파일이 최종 이름을 달지 않는다)
오프사이트  cp → head-object ContentLength 대조 → sidecar .sha256
종료코드   0 전부 성공 · 1 로컬 실패 · 2 사용법 · 3 미구성/CLI 없음 · 4 전송 실패 · 5 원격 검증 실패
          BACKUP_OFFSITE_REQUIRED=0 이면 3~5 → 경고 (개발 머신 전용, 운영 기본 1)
로그 토큰  BACKUP_LOCAL_OK · BACKUP_LOCAL_FAILED · BACKUP_VERIFY_FAILED · BACKUP_S3_OK · BACKUP_S3_FAILED · BACKUP_S3_SKIPPED
          각 줄에 type · file · bytes · sha256 · key. 비밀값 없음 (테스트 12)
보존      기존 find -mtime +7 유지 · .sha256 동반 삭제 · 하루 넘은 .part 정리
```

★ **실패 의미론이 핵심이다.** `LOCAL_OK` 와 `S3_FAILED` 가 같은 로그에 나란히 찍히고 종료코드는
실패다. 로컬 파일은 어떤 실패에서도 지우지 않는다(테스트 4·5·6).

## 4. 증분 백업 — 오프사이트 제외 근거

`backup_incremental.sh` 헤더가 스스로 적어둔 한계: created_at/updated_at 기준 CSV 라 **삭제된
행을 표현하지 못하고**, 복원은 수동 COPY 다. "유실 창을 좁히는 보조 수단이지 완전 복원 수단이
아니다". 2.7KB 짜리 tar 는 full 없이는 의미가 없다. 복구 의미가 검증된 것만 올린다는 원칙에
따라 이번에는 제외. 나중에 올리려면 "full + 증분 재생 절차" 를 먼저 리허설한다.

## 5. 테스트 (`648a1dc`) — 25/25

```
 1  로컬 OK + 오프사이트 OK            exit 0 · 두 토큰 · sidecar 양쪽 · .part 없음 · 로그 sha == 파일 sha
 2  덤프 실패                          exit 1 · 오프사이트 호출 0 · 로컬 파일 0 · LOCAL_FAILED
 3  빈 덤프                            exit 1 · 오프사이트 호출 0
 4  전송 실패                          exit 4 · ★ 로컬 보존 · S3_FAILED 와 LOCAL_OK 동시
 5  원격 크기 불일치                    exit 5 · 로컬 보존 · VERIFY_FAILED
 6  CLI 없음 / 6b 버킷 미구성           exit 3 · 로컬 보존 / S3_SKIPPED
 6c OFFSITE_REQUIRED=0                 exit 0 + 경고 (개발 머신)
 7  파일명·키 규약 · deploy 태그 유지
 8  freshness  최근+최근 → CURRENT/CURRENT exit 0
 9             최근+40h 전 → S3=STALE exit 1
10             객체 없음 → MISSING · 10b 임계 48h → CURRENT (한 곳에서 조정)
11             deploy 태그만 있음 → MISSING (정기 잡 기준)
12  로그에 자격증명·호스트 IP 없음
```

## 6. 복원 호환 (§11)

패치된 스크립트로 **로컬 개발 DB** 에서 덤프 1개 생성 → `sha256sum -c` OK → `gzip -t` OK →
격리 `postgres:17-alpine` 에 `gzip -dc | psql` (B-8 과 같은 명령) → 59 tables · `alembic_version
f3c6a8d0b2e4` · FK 93. 프로덕션 덤프를 새로 만들지 않았고 프로덕션에 쓰지 않았다.

## 7. S3 수명주기 — 결정 패킷 (임의 결정 안 함)

현 상태: 이 역할로는 lifecycle·versioning 을 **읽을 수 없다**(AccessDenied). 문서상 "미설정".

실측 크기로 계산한 저장량 (full 149.7MB + schema 0.04MB, 하루 1회):

| 보관 | 누적 |
|---|---|
| 7일 | 1.0 GB |
| 30일 | 4.5 GB |
| 90일 | 13.5 GB |
| 365일 | 54.7 GB |

비용은 결정 시점의 AWS 가격표(ap-northeast-2, 스토리지 클래스별)로 계산한다 — 여기 추정값을
쓰지 않는다. 결정할 것: 보관 일수 · 클래스 전환(예: 30일 후 IA) · 버전관리 · 만료.
**수명주기 결정을 기다리느라 업로드 재개를 미루지 않는다** — 업로드가 먼저다.

## 8. 프로덕션 적용 패킷

```
CURRENT PROD SCRIPT SHA     0857e6f67c477861…   (~/pigos/ops/backup_db.sh, 2026-08-25 14:43)
REPO @ main SHA             123e614d4a8fd313…   (8a80ea4 — 오프사이트 단계 있으나 exit 0)
PATCHED SCRIPT SHA          b2ef4c3638f8ff81…   (797394e)

현재 cron                   15 3 schema · 40 3 full · 5 15 incremental   — 변경 없음
변경 후 cron                변경 없음 (기본값). freshness 스케줄은 별도 결정

현재 로컬 백업              2026-09-18 03:40 full 149,710,684 B
현재 오프사이트 최신        2026-08-25 14:47 (deploy 태그) — 정기 잡 객체 0

적용 파일                   ~/pigos/ops/backup_db.sh 1개 (check_backup_freshness.sh 는 배치만, 스케줄 X)
변경 줄                     +78 / −20 (git diff 8a80ea4 797394e -- ops/backup_db.sh)
.env                        변경 없음 — BACKUP_S3_BUCKET·PREFIX 이미 있음

예상 동작                   다음 03:40 full 이 pigos-db/ 에 올라가고 크기 대조 후 BACKUP_S3_OK.
                            실패하면 크론 로그에 BACKUP_S3_FAILED + non-zero — 더 이상 조용하지 않다
롤백                        기존 파일을 backup_db.sh.pre-b10-<ts> 로 복사해 두고, 문제 시 되돌린다.
                            DB 에는 어떤 영향도 없다 (pg_dump 는 읽기 전용)

S3 lifecycle                UNDECIDED
freshness checker 스케줄    UNDECIDED
```

## 9. 적용 승인 후 검증 순서 (runbook — 아직 실행하지 않는다)

```
 0  pg_dump 가 DB 에 하는 일이 읽기 전용임을 확인한다 (스크립트 grep: pg_dump 외 psql 호출 없음)
 1  ssh 후  sha256sum ~/pigos/ops/backup_db.sh  == 0857e6f6…  아니면 STOP (사이에 누가 바꿨다)
 2  cp ~/pigos/ops/backup_db.sh ~/pigos/ops/backup_db.sh.pre-b10-$(date +%Y%m%d-%H%M%S)
 3  패치 파일 배치 → sha256 == b2ef4c36…
 4  bash -n ~/pigos/ops/backup_db.sh
 5  수동 1회: ~/pigos/ops/backup_db.sh schema     (37KB — 가장 싸고 빠르다)
 6  로컬에 pigos-schema-<ts>.sql.gz + .sha256 존재
 7  버킷에 pigos-db/pigos-schema-<ts>.sql.gz 존재 (aws s3 ls)
 8  로컬 bytes == 원격 ContentLength  (로그의 BACKUP_S3_OK 줄이 그것이다)
 9  로그의 sha256 == sha256sum 로컬 파일
10  ops/check_backup_freshness.sh  → schema 는 판정 대상이 아니므로 다음 03:40 full 이후 다시 본다
11  다음날 03:41 이후  check_backup_freshness.sh → BACKUP_FRESHNESS_OK
                      backup.log 에 BACKUP_S3_OK type=full
→ 여기까지 확인된 뒤에만  OFFSITE_CURRENT = YES  로 문서를 바꾼다
```

## 10. 상태 (섞지 않는다)

```
BACKUP_EXISTS        YES
RESTORE_VERIFIED     YES   (B-8, 2026-09-16)
OFFSITE_PATCH_READY  YES   (2026-09-18, 이 브랜치)
OFFSITE_CURRENT      NO    ← 코드가 준비됐다는 이유로 YES 라고 쓰지 않는다
PITR                 NO
```

## 11. CI 주의

이 브랜치는 origin/main(8a80ea4) 기준이라 main 의 ci.yml(트리거 없는 판)을 갖고 있다 — PR 을 열어도
CI 가 돌지 않고, 돈다 해도 main 의 ruff 47건에서 멈춘다. PR #3(ci.yml + lint) 가 먼저 merge 되면 이
브랜치를 그 위로 올려 CI 를 받는다. 그때까지의 증거는 §5 로컬 실행이다.

## 12. 관련

```
ops/backup_db.sh · ops/check_backup_freshness.sh · ops/tests/test_backup.sh
docs/runs/DR_RESTORE_REHEARSAL_20260916.md   B-8 · 최초 발견
docs/INFRA_DB_STRATEGY.md §3                   상태표
docs/legal/HUMAN_INPUT_QUEUE.md B-10
```
