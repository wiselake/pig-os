# 프로덕션 롤백 런북

> 2026-08-24 장애 후 작성, 2026-08-25 DB 이전(Supabase → EC2 로컬 PG17) 반영.
> **당황하면 순서를 건너뛴다. 위에서부터 읽는다.**
>
> 현재 구성: DB = 같은 EC2 의 PostgreSQL 17, 포트 **5434**(5432 는 타 프로젝트의 PG16).
> 컨테이너는 `172.18.0.1:5434`, 호스트 도구는 `127.0.0.1:5434` 로 붙는다.

---

## 0. 먼저 판단 — 무엇이 깨졌나

| 증상 | 원인 계층 | 가야 할 절차 |
|---|---|---|
| 502 / 접속 불가 | 컨테이너·포트 매핑 | **A** |
| 응답은 오는데 매우 느림 | 느린 쿼리·인덱스 / DB 자원 | **B** |
| 기능이 잘못 동작 / 데이터가 이상 | 코드 | **C** |
| 스키마가 잘못 바뀜 | 마이그레이션 | **D** |
| 데이터가 손상·소실 | DB | **E** |

**A~C 는 되돌리기 쉽다. D·E 는 신중하게.**

---

## A. 502 · 접속 불가

거의 항상 **compose 파일 하나만 써서 포트 매핑이 빠진 것**이다.

```bash
sudo docker port pigos-api        # 8000/tcp -> 127.0.0.1:8010 이 나와야 정상
```

안 나오면:

```bash
cd ~/pigos
sudo docker compose -f docker-compose.prod.yml -f docker-compose.deploy.yml up -d api web
```

> `docker-compose.prod.yml` 단독으로 `up -d` 하면 `127.0.0.1:8010:8000` 매핑이 없어져
> 호스트 nginx 가 502 를 낸다. **항상 두 파일.**

---

## B. 매우 느림 (수십 초)

> ★ 2026-08-25 DB 이전으로 이 절의 전제가 완전히 바뀌었다. DB 는 이제 **같은 EC2 의
> 로컬 PostgreSQL 17(포트 5434)** 이고 Supavisor 풀러는 경로에 없다.
> 옛 절차는 §B-옛 에 접어 보존만 해 둔다 — 되돌아갈 때만 쓴다.

### B-1. 어느 계층인지 먼저 가른다

커넥션이 느린지, 쿼리가 느린지부터 나눈다. 이걸 안 하면 설정을 바꿔가며
재기동하는 함정에 빠진다(2026-08-25 에 그렇게 시간을 버렸다).

```bash
sudo docker exec -i pigos-api python - <<'PY'
import asyncio, time
from sqlalchemy import text
from app.db.session import engine
async def m():
    for _ in range(5):
        t = time.perf_counter()
        async with engine.connect() as c:
            await c.execute(text("select 1"))
        print("%.3fs" % (time.perf_counter() - t))
    await engine.dispose()
asyncio.run(m())
PY
```

**정상은 0.001~0.05s.** 여기가 느리면 → B-3(DB 자원).
여기가 빠른데 화면이 느리면 → **B-2(쿼리). 대부분 여기다.**

### B-2. 느린 쿼리 특정

엔드포인트 총 시간만 보면 범인을 못 찾는다. **하위 호출을 쪼개서** 찍는다.

```bash
sudo docker exec -i pigos-api python - <<'PY'
import asyncio, time
from datetime import date
from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.db.models.platform import Farm
from app.db.models.sow import Sow
from app.services import kpi_service as K
async def m():
    async with AsyncSessionLocal() as db:
        fid = (await db.execute(select(Sow.farm_id).group_by(Sow.farm_id)
               .order_by(func.count().desc()).limit(1))).scalar()   # 최대 농장 = 최악 케이스
        farm = (await db.execute(select(Farm).where(Farm.id == fid))).scalar_one()
        today = date.today()
        for name, fn in (("psy",  lambda: K.calculate_psy(db, fid, today)),
                         ("npd",  lambda: K.calculate_npd(db, fid, today)),
                         ("herd", lambda: K.build_herd_kpis(db, farm)),
                         ("dash", lambda: K.get_dashboard(db, farm))):
            t = time.perf_counter(); await fn()
            print("%-5s %.3fs" % (name, time.perf_counter() - t))
asyncio.run(m())
PY
```

범인을 찾았으면 **EXPLAIN (ANALYZE)** 로 어느 노드가 시간을 쓰는지 본다.
sow 단위 LATERAL 안에서 `farm_id` 선행 인덱스를 스캔하고 있으면 **by-sow 인덱스가
없는 것**이다 — 2026-08-25 에 `farrowings` 가 정확히 그랬다(단일 노드 3,691ms).

★ **인덱스 누락은 "느려짐"이 아니라 "장애"로 나타난다.** 대형 농장에서만 터지므로
평소엔 안 보이다가 특정 고객에게만 타임아웃이 난다. 반드시 **최대 농장**으로 잰다.

### B-3. DB 자원 확인

```bash
P="sudo -u postgres psql -p 5434 -d pigos"
$P -c "select state, count(*) from pg_stat_activity where datname='pigos' group by state"
$P -c "show max_connections"
$P -c "select query, now()-query_start as dur from pg_stat_activity
       where state='active' and datname='pigos' order by dur desc limit 5"
df -h /        # 디스크가 차면 PG 가 급격히 느려진다
uptime         # load average
```

★ **api 를 반복 재기동하지 말 것.** 원인을 고정하기 전에 설정을 바꿔가며 재기동하면
증상만 흔들리고 판단이 오염된다.

### B-옛. Supabase 풀러 시절 (되돌아갈 때만)

<details><summary>펼치기</summary>

같은 요청을 5번 보내 뒤로 갈수록 빨라지면 커넥션 수립 문제였다. Supavisor 세션
슬롯이 묵은 세션으로 막힌 것으로, 해결은 대시보드 → Settings → Infrastructure →
Restart project(약 1분 다운타임).

Nano 컴퓨트의 세션 모드 한도는 `pool_size: 15` 였고, 대시보드에서 30 으로 올려도
**반영되지 않았다**(프로젝트 재시작 후에도).

최후에는 `ConnectionDoesNotExistError: connection was closed in the middle of
operation` — 풀러가 **쿼리 실행 도중** 연결을 끊는 상태까지 갔다. 애플리케이션에서
고칠 수 없어 로컬 PG 로 이전했다. 같은 전체 덤프가 Supabase 67분 35초 / 로컬 29초.

</details>

---

## C. 코드 롤백 (가장 흔함)

```bash
sudo docker images | grep rollback          # 사용 가능한 시점 확인
```

`ops/deploy.sh` 로 배포했으면 `pigos-<svc>:rollback-<타임스탬프>` 가 최근 3개 남아 있다.

```bash
cd ~/pigos
TS=20260824-051600                          # 되돌릴 시점
sudo docker tag pigos-api:rollback-$TS pigos-api:latest
sudo docker tag pigos-web:rollback-$TS pigos-web:latest
sudo docker compose -f docker-compose.prod.yml -f docker-compose.deploy.yml up -d --no-build api web
curl -s -o /dev/null -w "%{http_code}\n" https://api.pigos.io/health
```

> `--no-build` 가 중요하다. 빼면 새 소스로 다시 빌드해서 롤백이 무효가 된다.

**롤백 태그가 없으면** 이 경로는 못 쓴다. 소스를 이전 커밋으로 되돌려 재빌드해야 한다(느리다).

### C-0. ★ a7c9e1f3b5d7 이전 코드로 되돌릴 때 (2026-09-23~)

프로덕션 DB 는 2026-09-23 feed initial load 로 `a7c9e1f3b5d7`(feed_source_rows · feed_source_sync_runs) 이다.
그 이전 코드(head `f3c6a8d0b2e4`, main `fc96efc` 이하)는 이 리비전을 모른다.

- **순서: D(DB downgrade → `f3c6a8d0b2e4`) 먼저, 그 다음 옛 코드 배포.** 일반 규칙(C 먼저, D 나중)과 **반대**다 —
  옛 코드는 새 테이블을 쓰지 않으므로 스키마를 먼저 내려도 현재 앱이 깨지지 않지만, 거꾸로 하면
  코드가 모르는 리비전 위에서 앱이 돈다.
- `ops/deploy.sh` 0/5 게이트가 거꾸로 된 순서를 **기계적으로 거부**한다(exit 3, "database is ahead of the code").
  우회 스위치 없음 — 게이트를 끄지 말고 순서를 지킨다. (§C 의 `docker tag … up -d --no-build` 롤백은 게이트를 거치지
  않으므로 이 순서를 사람이 지켜야 한다.)
- downgrade 는 `feed_source_rows`·`feed_source_sync_runs` 를 **drop 한다** — 적재된 5,461행이 사라진다.
  되살리려면 initial load 를 승인 경로로 다시 돌린다(런북 `docs/feed/INITIAL_LOAD_RUNBOOK.md`).
- 이 downgrade 의 실측 검증: `docs/feed/runs/restore_test_20260923/` (격리 컨테이너 복원 리허설). 검증 전까지는 미증명으로 본다.

---

## D. 마이그레이션 롤백

```bash
M="sudo docker run --rm --env-file ~/pigos/.env -v ~/mig-staging:/app -w /app pigos-api alembic"
$M current                    # 지금 어디인지
$M downgrade <되돌릴_리비전>
$M current                    # 확인
```

⚠️ **주의**

- `downgrade` 는 데이터를 지울 수 있다. 컬럼·테이블 drop 이 있으면 그 데이터는 사라진다.
- 코드가 새 스키마를 기대하는 상태에서 스키마만 되돌리면 앱이 깨진다. **C(코드 롤백)를 먼저 하고 D 를 한다.**
  - 예외: 되돌릴 대상이 `a7c9e1f3b5d7` 이전 코드면 **D 먼저** — §C-0.
- 로컬 PG 로 이전(2026-08-25)한 뒤로 `ECHECKOUTTIMEOUT`(풀러 고갈)은 나지 않는다.
  대신 실패하면 **진짜 실패다** — 재시도로 넘기지 말고 메시지를 읽는다.
- 실패는 트랜잭션째 롤백되니 중간 상태로 남지 않는다.

★ 실패 판정을 **풀러가 밀린 상태의 조회 결과로 내리지 말 것.** 2026-08-24 에 그 오판으로
이미 head 인 마커를 `stamp` 로 되돌려 `DuplicateTable` 사고를 만들었다.

---

## E. DB 복원 (최후 수단)

### E-1. ⚠️ 관리형 자동 백업은 **없다**

2026-08-25 이전 후 DB 는 같은 EC2 의 로컬 PostgreSQL 17 이다.
Supabase 시절의 `Database → Backups`(관리형 복원 지점)에 **해당하는 것이 없다.**
`~/pigos-backups/` 의 크론 덤프가 **유일한 방어선**이다. 바로 E-2 로 간다.

| 종류 | 크론 | 명령 | 크기·시간 |
|---|---|---|---|
| schema | 매일 03:15 | `backup_db.sh schema` | 37K |
| full | 매일 03:40 | `backup_db.sh full` | 143M · 약 30초 |
| 증분 | 매일 15:05 | `backup_incremental.sh 2` | 20K · 약 22초 |

**최악 손실 = 24시간**(전체 기준), 증분이 그 창을 절반으로 줄인다.
`-deploy` 태그가 붙은 덤프는 보존기간 정리에서 제외된다(되돌릴 지점).

### E-2. 덤프에서 복원

> **리허설 실측(2026-08-25)**: 143M 덤프 → 별도 DB 복원 **24.1초 · ERROR 0건**.
> 58테이블·sows 141,360·marker 일치, 덤프-복원본 테이블 차집합 0,
> 성능 인덱스(`idx_farrowings_sow_date`)도 복원본에 살아남았다.
> **운영 DB 를 건드리지 않고 리허설하는 법**은 아래 E-4.

```bash
ls -lh ~/pigos-backups/                     # deploy 태그 붙은 게 배포 직전 스냅샷
```

```bash
# ⚠️ 복원은 기존 데이터를 덮어쓴다. 반드시 현재 상태를 먼저 뜬다.
~/pigos/ops/backup_db.sh full before-restore

# ★ 호스트에서 실행하므로 루프백 주소를 쓴다. .env 의 DATABASE_URL 은 컨테이너
#   기준(도커 게이트웨이 172.18.0.1)이라 호스트에서 붙으면 pg_hba 에 걸린다.
URL=$(grep -E '^LOCAL_DATABASE_URL=' ~/pigos/.env | cut -d= -f2- | tr -d '"')
PGURL=$(printf '%s' "$URL" | sed -E 's#\+asyncpg##')
# ★ 이 EC2 는 PG16(타 프로젝트)과 PG17(PigOS)이 공존한다. PATH 기본 psql 은 16.x 다.
PSQL=/usr/lib/postgresql/17/bin/psql

gzip -dc ~/pigos-backups/pigos-full-<타임스탬프>.sql.gz | "$PSQL" "$PGURL" -q -v ON_ERROR_STOP=0
```

`ON_ERROR_STOP=0` 인 이유: Supabase 시절 덤프에는 `realtime`·`storage` 등 Supabase
전용 스키마와 롤 참조가 섞여 있어 로컬 PG 에서 일부 ERROR 가 난다. PigOS `public`
스키마와는 무관하므로 멈추지 않고 넘어간다. **대신 아래 검증을 반드시 한다.**

### E-3. 복원 후 검증 (건너뛰지 말 것)

```bash
P="sudo -u postgres psql -p 5434 -d pigos"
$P -c "select (select count(*) from information_schema.tables
                where table_schema='public' and table_type='BASE TABLE') tables,
              (select count(*) from sows) sows,
              (select count(*) from farms) farms,
              (select count(*) from users) users,
              (select version_num from alembic_version) marker"
```

덤프 쪽 기대값과 대조한다(테이블 목록 차집합이 비어야 한다):

```bash
gzip -dc <덤프> | grep '^CREATE TABLE public\.' | sed 's/CREATE TABLE public\.//; s/ .*//' \
  | tr -d '"' | sort > /tmp/dump_tables.txt
$P -tAc "select tablename from pg_tables where schemaname='public'" | sort > /tmp/db_tables.txt
comm -23 /tmp/dump_tables.txt /tmp/db_tables.txt     # 비어야 한다 = 복원 누락 없음
```

마지막으로 앱 경로까지:

```bash
$M current                                   # 마커가 덤프 시점과 맞는지
curl -s -o /dev/null -w "%{http_code}\n" https://api.pigos.io/health
```

★ **ANALYZE 는 자동으로 돌 때까지 기다리지 말고 직접 친다.** 복원 직후엔 통계가
없어 플랜이 틀어진다.

```bash
$P -c "ANALYZE;"
```


### E-4. 복원 리허설 (운영 DB 를 건드리지 않고)

**백업은 복원해 본 적 있을 때만 백업이다.** 분기 1회는 돌린다.

```bash
B=$(ls -t ~/pigos-backups/pigos-full-*.sql.gz | head -1)
P="sudo -u postgres psql -p 5434"

$P -c "DROP DATABASE IF EXISTS pigos_restore_test"
$P -c "CREATE DATABASE pigos_restore_test OWNER pigos"
time gzip -dc "$B" | sudo -u postgres /usr/lib/postgresql/17/bin/psql -p 5434      -d pigos_restore_test -q -v ON_ERROR_STOP=0 2>/tmp/restore_err.txt
grep -c '^ERROR' /tmp/restore_err.txt          # 로컬 PG 덤프면 0 이어야 한다

# 덤프 목록과 복원본을 대조 — 둘 다 비어야 누락 0
gzip -dc "$B" | grep '^CREATE TABLE public\.' | sed 's/CREATE TABLE public\.//; s/ .*//'   | tr -d '"' | sort > /tmp/dt.txt
$P -d pigos_restore_test -tAc   "select tablename from pg_tables where schemaname='public'" | sort > /tmp/rt.txt
comm -23 /tmp/dt.txt /tmp/rt.txt && comm -13 /tmp/dt.txt /tmp/rt.txt

$P -c "DROP DATABASE pigos_restore_test"       # ★ 반드시 정리 — 디스크를 두 배로 먹는다
```

★ 덤프에 `ERROR` 가 나오는 경우: **Supabase 시절 덤프**라면 `realtime`·`storage`
스키마 관련이라 정상이다(약 21건). **로컬 PG 덤프인데 ERROR 가 나오면 조사한다.**

---

## 사고 후 할 일

1. 무엇이 원인이었는지 **한 줄로** 적는다
2. 같은 일이 다시 나지 않게 하는 **테스트나 게이트**를 하나 추가한다
3. 이 문서에 증상 → 절차를 추가한다

> 2026-08-24 사례: 풀러 세션 포화로 커넥션 수립이 4~6초 → 대시보드 31초.
> 재기동을 반복해 악화. 교훈은 위 **B** 에 반영했다.
>
> 2026-08-25 사례: 같은 풀러가 결국 `ConnectionDoesNotExistError`(쿼리 도중 연결 절단)
> 까지 가서 로컬 PG 로 이전했다. **그런데 이전 후에도 대시보드는 5.67초였다** —
> 원인이 두 개였고 하나만 고친 상태였던 것이다(나머지는 `farrowings` by-sow 인덱스
> 누락, 3.7초). 교훈: **증상 하나에 원인 하나라고 가정하지 말 것.** 옮긴 뒤에도
> 반드시 다시 재고, 단계별로 쪼개서 잰다(B-2).
