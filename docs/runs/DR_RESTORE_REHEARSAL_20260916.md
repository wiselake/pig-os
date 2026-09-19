# 백업 복구 리허설 — 2026-09-16 (B-8)

> **왜**: `INFRA_DB_STRATEGY` §4 는 백업을 "유일한 방어선"이라 적었다. 그런데 **복원을
> 해본 기록이 0건**이었다. 복구해본 적 없는 백업은 백업이 아니라 파일이다.
>
> **결과**: 복원은 **성공**했다. 그리고 그 과정에서 백업 체계의 더 큰 문제가 나왔다.

---

## 0. 한 줄

```
BACKUP_EXISTS      YES   로컬 일간 full + schema, 7일 보관
RESTORE_VERIFIED   YES   2026-09-16 03:40 덤프 → 격리 PG17 복원 완주 · 행수·FK·alembic·ORM 조회 전부 통과
OFFSITE            ★ NO — S3 업로드가 2026-08-25 이후 22일간 0건이다 (아래 §3)
```

---

## 1. 절차 — 프로덕션에 쓰지 않았다

```
1  EC2 에서 sha256 계산          0ff1b111…5e3a7   149,703,432 bytes
2  로컬로 scp (15초)             sha256 동일 — 전송 중 손상 없음
3  격리 컨테이너 기동            docker run postgres:17-alpine (프로덕션과 같은 메이저)
                                 ★ 로컬 pigos-postgres(PG16)를 쓰지 않았다 — 17→16 복원은 검증이 아니다
4  gzip -dc | psql -v ON_ERROR_STOP=1
5  검증 쿼리 + ORM 조회
6  컨테이너 정리, 증거·해시 보존
```

프로덕션 DB 에는 `SELECT` 만 나갔고, 복원은 전부 로컬 격리 환경에서 했다.

---

## 2. 결과

### 2-1. 1차 시도 — 실패, 그리고 그 실패가 알려준 것

```
증상   ADD CONSTRAINT farrowings_breeding_cycle_id_fkey 실행 중
       server process (PID 87) was terminated by signal 9: Killed
원인   Docker VM 총 메모리 1GB (~/.wslconfig 의 memory=1GB — 호스트는 64GB)
       FK 검증이 대형 테이블을 훑을 때 OOM killer 가 백엔드를 죽였다
```

★ **백업 결함이 아니라 복원 환경의 한계다.** 다만 이것 자체가 DR 절차에 들어가야 할
사실이다 — **복원에는 1GB 로는 부족하다.** 프로덕션 EC2 는 15GiB 라 거기서는 문제가
아니지만, "어디서 복원할 것인가" 를 안 정해두면 사고 당일에 이걸 처음 알게 된다.

`.wslconfig` 는 사용자가 정한 값이라 임의로 바꾸지 않았다. 대신 PostgreSQL 쪽을
1GB 에 맞게 낮춰 재시도했다(`shared_buffers=96MB · maintenance_work_mem=48MB ·
work_mem=4MB · autovacuum=off`).

### 2-2. 2차 시도 — 성공

```
exit code       0
stderr          2줄 — 둘 다 wal_level 관련 WARNING(논리 복제 publication). 오류 아님
```

검증:

| 항목 | 값 | 판정 |
|---|---|---|
| public 테이블 | 59 | 스키마 완전 |
| `alembic_version` | `f3c6a8d0b2e4` | ★ 저장소 head 와 **일치** — 복원본에 마이그레이션을 더 돌릴 필요가 없다 |
| farms / users | 79 / 89 | |
| sows / farrowings | 141,408 / 531,841 | 대량 테이블 완주 |
| consent_ledger | **0** | 기존 실측과 일치 (동의 원장 0행 — 별건 H11) |
| FK 제약 | 116 | 1차에서 죽은 지점 통과 |
| 인덱스 | 162 | |
| 미검증 제약 | 1 | `realtime.messages` — Supabase 잔여 스키마. public 아님 (§4) |
| ORM 조회 | farms 79 · sows 141,408 | 애플리케이션 계층에서도 읽힌다 |

**즉 이 백업 하나로 새 환경을 세울 수 있다.**

---

## 3. ★ 이번 리허설의 진짜 발견 — 오프사이트 백업이 22일째 끊겨 있다

`INFRA_DB_STRATEGY.md` §3 은 이렇게 적어두었다:

> **오프사이트 백업은 해결됐다**(2026-08-25). S3 `pigos-db-backup` + EC2 인스턴스 역할

실측:

```
s3://pigos-db-backup/pigos-db/     객체 6개, 전부 2026-08-25 자
                                   최신: pigos-full-20260825-144727-deploy.sql.gz
cron                               15 3 * * *  backup_db.sh schema
                                   40 3 * * *  backup_db.sh full
                                    5 15 * * * backup_incremental.sh
grep -rn "s3\|aws" ~/pigos/ops/    0건
grep -rl "pigos-db-backup" ~/*.sh  0건
```

**어떤 스크립트도 S3 에 올리지 않는다.** 8/25 의 6개는 설정하던 날 손으로 올린 것이고,
그 뒤로 22일간 자동 업로드는 한 번도 없었다. 같은 버킷의 `wiselake-console/` 은 매일
올라오고 있어 **버킷·권한·네트워크는 정상**이다 — PigOS 쪽 업로드 단계가 없을 뿐이다.

★ 그래서 지금 상태는 문서가 "해결됐다"고 적은 것과 반대다:

```
문서    로컬 + S3 이중
실제    로컬 단독 — DB 와 같은 EC2, 같은 디스크(/dev/root 96G)
        EC2 가 사라지면 DB 와 백업이 함께 사라진다
```

`INFRA_DB_STRATEGY` §3 이 "이중화 부재"를 남은 최대 위험으로 꼽았는데, **백업의
오프사이트성까지 함께 사라져 있었다.**

### 왜 고치지 않았나

업로드 한 줄(`aws s3 cp`)을 `backup_db.sh` 에 넣는 것은 작은 변경이지만, 그 파일은
**프로덕션 운영 스크립트**다. 이 세션의 금지 목록에 프로덕션 변경이 있고, 백업 정책은
보관 기간·비용·수명주기가 붙는 결정이다. **패치는 준비하되 적용은 사람이 한다.**

권고 (검토 후 적용):

```
backup_db.sh 말미에   aws s3 cp "$OUT" "s3://pigos-db-backup/pigos-db/$(basename "$OUT")"
                      실패해도 로컬 백업은 남기고 종료코드만 남긴다
버킷 수명주기         미설정 상태 (INFRA §3 이 이미 지적). 업로드 재개 전에 같이 정한다
검증                  다음날 aws s3 ls 로 그날 파일 존재 확인 — 없으면 알림
```

---

## 4. 부수 관측

```
Supabase 잔여 스키마   덤프에 realtime.* 가 그대로 들어 있다 (미검증 제약 1건의 출처).
                       2026-08-25 Supabase → EC2 이전의 잔여물. 기능에는 무해하나
                       덤프 크기·복원 시간에 기여한다. 정리 여부는 별건
로컬 보관              KEEP_DAYS=7 · find -mtime +7 -delete. 32개 파일 3.1GB
                       ★ 7일 = 7일 이전 상태로는 못 돌아간다. PITR 없음(INFRA §3)과 합쳐
                         "7일 내 사고만 복구 가능" 이 실제 경계다
```

---

## 5. 상태 어휘

```
BACKUP_EXISTS        YES
RESTORE_VERIFIED     YES   (2026-09-16, 격리 PG17, 증거 위)
OFFSITE_CURRENT      NO    ★ 22일 끊김 — 사람 조치 필요
PITR                 NO    (기존 기록과 동일)
```

---

## 6. 관련

```
docs/INFRA_DB_STRATEGY.md §3·§4        "오프사이트 해결됨" 서술 — §3 에 의해 반증됨
docs/legal/HUMAN_INPUT_QUEUE.md B-8    이 리허설의 출처
~/pigos/ops/backup_db.sh (EC2)         KEEP_DAYS · S3 없음
```
