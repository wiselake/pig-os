# Runtime Integrity Audit — 2026-08-28

```
mode              READ-ONLY  (production SELECT · 기존 로그 · git 이력)
target_commit     c949181
production        52.78.65.6 · pigos-api / pigos-worker · PostgreSQL 17 :5434 db=pigos
production writes 0 · deploys 0 · migrations 0 · flag changes 0 · job executions 0
scope             A1 ARQ false-success · A2 notification 71/10 ·
                  A3 historical authority · A4 farrowing_rate mismatch origin
```

---

## A1. ARQ job integrity — item-level vs job-level success

### A1-1. 전 job entrypoint 열거 (7건)

`app/jobs/worker.py::WorkerSettings.functions` 기준 **전수**.

| job | 스케줄 | 대상 |
|---|---|---|
| `daily_kpi_aggregation` | cron 00:05 UTC | 활성 농장 전체 |
| `weekly_kpi_aggregation` | cron 00:10 UTC | 〃 |
| `monthly_kpi_aggregation` | cron 00:15 UTC | 〃 |
| `recalculate_farm_kpi` | on-demand (이벤트 기록 후) | 1농장 × 3기간 |
| `generate_tasks_job` | cron 05:30 UTC | 활성 농장 전체 |
| `generate_notifications_job` | cron 06:00 UTC | 활성 농장 전체 |
| `db_keepalive` | cron 12:00 UTC | 없음(단일 쿼리) |

### A1-2. `ARQ_JOB_INTEGRITY`

| job | expected | success | errors 집계 | errors 보고 | raise | false_success | user_facing |
|---|---|---|---|---|---|---|---|
| `daily_kpi_aggregation` | 71 | **0** | YES | YES(문자열) | NO | **YES** | 간접 |
| `weekly_kpi_aggregation` | 71 | **0** | **NO** | **NO** | NO | **YES ★심각** | 간접 |
| `monthly_kpi_aggregation` | 71 | **0** | **NO** | **NO** | NO | **YES ★심각** | 간접 |
| `recalculate_farm_kpi` | 3 | 0 | **NO** | **NO** | NO | **YES ★심각** | 간접 |
| `generate_tasks_job` | 71 | 71 | YES | YES | NO | 구조상 YES | YES |
| `generate_notifications_job` | 71 | 71 | YES | YES | NO | 구조상 YES | **YES** |
| `db_keepalive` | 1 | 1 | n/a | n/a | 전파 | NO | NO |

### A1-3. ★ 등급이 셋으로 갈린다

```
등급 1  errors 를 세고 결과 문자열에 넣는다 — 그러나 성공/실패 semantics 는 없다
        daily_kpi_aggregation · generate_tasks_job · generate_notifications_job
        → "0 farms, 71 errors" 도 ARQ 에서는 ● (성공) 이다

등급 2  errors 를 아예 세지 않는다 ★
        weekly_kpi_aggregation · monthly_kpi_aggregation
        코드: except Exception as e: log.error(...)   ← errors 변수 자체가 없다
        결과: 'weekly KPI done: 0 farms, period=…'
        → 로그만 보면 "처리할 농장이 없었다" 와 구분되지 않는다

등급 3  errors 를 세지도, 보고하지도 않고, 항상 성공 문자열을 만든다 ★★
        recalculate_farm_kpi
        3개 기간 전부 실패해도 return f"recalculated KPI farm=… period=…"
        → 이벤트 기록 직후 재계산이 전건 실패해도 호출자는 성공으로 본다
```

### A1-4. ★★ 네 번째 삼킴 — 로그조차 없다

`notification_service.create_from_alerts:169-176`

```python
try:
    async with db.begin_nested():
        dash = await kpi_service.get_dashboard(db, farm)
        for a in dash.alerts: items.append(...)
except Exception:   # noqa: BLE001
    pass            # ← log 없음. 카운터 없음.
```

**KPI 알림 생성이 통째로 실패해도 흔적이 0이다.**
job 이 `0 errors` 를 보고해도 그것은 *과기한·도태 알림이 만들어졌다*는 뜻일 뿐,
**KPI 알림이 손실되지 않았다는 근거가 되지 못한다.**

> 이 경로는 등급 1~3과 성격이 다르다. 앞의 셋은 "실패를 성공으로 보고"이고,
> 이것은 **"실패를 기록조차 하지 않음"** 이다. 관측 가능성이 0이다.

### A1-5. `false_success_possible` 후보 목록

```
P0  weekly_kpi_aggregation      errors 미집계 + 미보고
P0  monthly_kpi_aggregation     〃
P0  recalculate_farm_kpi        항상 성공 문자열
P0  create_from_alerts KPI 블록  except: pass — 로그·카운터 0
P1  daily_kpi_aggregation       errors 는 보고하나 성공 semantics 없음
P1  generate_tasks_job          〃
P1  generate_notifications_job  〃 (user_facing)
```

---

## A2. `notification generation done: 71 farms, 10 created, 0 pushed, 0 errors`

### A2-1. 코드 경로 실측

```
활성 농장 조회            Farm.active is True                → 71
농장별 recipients          user_farms ⋈ users
                          coalesce(role_override, system_role)
                          IN ('FARM_OWNER','FARM_MANAGER')
  recipients 비면 return 0  ← 이 게이트에서 걸리는 농장 수 = 0 (아래 실측)
alert 수집                 ① 과기한 6유형 ② 도태 권고 ③ KPI(룰엔진)
  ③은 begin_nested + except: pass  ← A1-4
items 비면 return 0
멱등 필터                  미읽음 IN_APP 의 (user, alert_type, entity, severity) 키
승격 처리                  낮은 severity 미읽음은 read 처리
```

### A2-2. 프로덕션 실측

```
활성 농장                                   71
유효 역할 분포 (user_farms ⋈ users, active)
    FARM_OWNER    71 memberships / 70 farms
    FARM_MANAGER   1 membership  /  1 farm
    VIEWER 2 · FARM_WORKER 1 · VET 1        ← 수신 대상 아님
활성 농장 중 멤버가 아예 없는 농장           0
미읽음 IN_APP 알림                          555건 / 65농장
오늘(2026-08-28) 신규 생성                   10건
    OVERDUE_OPEN_OVERDUE_MATING WARNING  7
    KPI_PSY WARNING 1 · KPI_SUMMER_FARROW_DROP CRITICAL 1 · KPI_WSI CRITICAL 1
```

### A2-3. `NOTIFICATION_71_10`

```
eligible          71   (활성 농장 전건. recipient 게이트 통과 71 — 0건 탈락)
filtered_normal   미상  발화 alert 이 0인 농장 수. 룰엔진을 돌려야 알 수 있어
                       측정하지 않았다(§금지: get_dashboard 는 Redis 캐시를 쓴다)
deduped           지배적  미읽음 555건과 같은 (user, alert_type, entity, severity) 는 전부 억제
suppressed        0     별도 suppression 로직 없음(멱등 필터가 유일)
created           10
errors            0     ← job 레벨 카운터
unexplained       ★ 정량 불가 — A1-4 의 except: pass 때문에
                       "KPI 알림이 몇 건 유실됐는가" 를 사후에 셀 수단이 없다
```

### A2-4. 판정

> **`61개 실패 삼킴` 은 아니다.** 71은 *순회한 농장 수*이고 10은 *신규 생성 건수*다.
> 둘은 애초에 같은 단위가 아니며, 555건의 미읽음이 존재하는 상태에서 10건 신규는
> 멱등 설계의 정상 동작으로 설명된다.
>
> **그러나 `0 errors` 를 "손실 없음"으로 읽을 수는 없다.** KPI 알림 블록의
> `except: pass` 가 job 카운터 바깥에 있기 때문이다. 이 구간은
> **`user_facing severity 상승` 대상**으로 남긴다 — 실패가 발생했는지 자체를 모른다.

---

## A3. Historical authority 판별

### A3-1. 판별 원리

`use_governance_benchmarks` 가 갈라놓는 것은 **A-resolve 29룰뿐**이다.
`PSY`·`NPD`·`FARROWING_RATE` 는 A-bench 라 flag 와 무관하게 항상 DMV 를 읽는다
→ **NPD/PSY 알림은 판별에 쓸 수 없다.**

`notifications.body` 가 `f"{kpi}: {current_value:.1f}"` 형식이라
**발화 당시 KPI 값이 보존돼 있다.** 이것을 임계 후보와 대조한다.

| 지표 | flag OFF (DMV) | flag ON (operational_defaults) |
|---|---|---|
| `WSI` | US 7 / 9 · BR·KR·VN·SYSTEM 7 / 10 | **10 / 14** |
| `BORN_ALIVE` | US·BR 13 / 12 · SYSTEM 13 / 11.5 · CN·VN 11 / 10 · KR 10.5 / 9.5 | **11 / 10** |

### A3-2. ★ 결정적 사례 — code_default 로는 **발생 불가능**한 알림

| # | 국가 | 알림 | 값 | DMV 판정 | opdef 판정 | 결론 |
|---|---|---|---|---|---|---|
| 1 | US | `KPI_WSI` **CRITICAL** | 9.3 | >9 → CRITICAL ✓ | 9.3 < 10 → **무발화** | **DMV 확정** |
| 2 | US | `KPI_WSI` **CRITICAL** | 10.0 | >9 → CRITICAL ✓ | 10.0 ≯ 10 → **무발화** | **DMV 확정** |
| 3 | US | `KPI_WSI` WARNING | 7.6 · 7.4 | >7 → WARNING ✓ | **무발화** | **DMV 확정** |
| 4 | BR | `KPI_WSI` WARNING | 8.0 · 9.2 · 9.6 | >7 → WARNING ✓ | **무발화** | **DMV 확정** |
| 5 | CN | `KPI_WSI` **CRITICAL** | 10.5 · 11.1 · 12.4 | >10(SYSTEM) → CRITICAL ✓ | <14 → WARNING뿐 | **DMV 확정** |
| 6 | US | `KPI_BORN_ALIVE` **CRITICAL** | 11.8 | <12 → CRITICAL ✓ | 11.8 > 11 → **무발화** | **DMV 확정** |
| 7 | US·BR | `KPI_BORN_ALIVE` WARNING | 12.9 | <13 → WARNING ✓ | **무발화** | **DMV 확정** |
| 8 | DE·MX·TH·ES | `KPI_BORN_ALIVE` WARNING | 11.9~12.9 | SYSTEM <13 → WARNING ✓ | **무발화** | **DMV 확정** |

**통제 확인**: 위 사례는 전부 threshold-only 판정이다(해당 룰에 eligibility·
suppression·cadence 조건이 없다). 값은 알림 본문에 보존된 실제 발화값이며
추정이 아니다.

### A3-3. 시간 커버리지

```
결정적 사례 존재 구간   2026-07-20 ~ 2026-08-28
결정적 사례 없는 구간   2026-07-03 ~ 2026-07-19   (알림은 있으나 두 authority 가
                                                   같은 판정을 내는 값뿐)
```

### A3-4. 판정

```
HISTORICAL_AUTHORITY = CONFIRMED_DMV        (2026-07-20 ~ 2026-08-28)
                     = NO_DISCRIMINATING_CASE (2026-07-03 ~ 2026-07-19)

MIXED_AUTHORITY_STATE = NO   confidence = HIGH (상향. ABSOLUTE 아님)
```

★ 이전 판정은 "임계값이 불변이었다"는 **간접** 근거였다. 이제
**code_default 로는 물리적으로 발생할 수 없는 알림 8종**이 관측됐으므로
DMV authority 가 **양성 확인**됐다. 다만 첫 17일 구간에 판별 사례가 없어
`ABSOLUTE` 로 올리지 않는다.

---

## A4. `farrowing_rate` snapshot mismatch — 기원

### A4-1. 실측

```
git log -S "farrowing_rate" -- api/app/db/models/ops.py     → 0 commits
git log -S "farrowing_rate" -- api/app/jobs/kpi.py          → 1 commit: 26c2e68

26c2e68  2026-05-29 16:08  "feat(api): FastAPI 백엔드 전체 구현"
  ├ jobs/kpi.py       _calculate_farm_kpi 가 {"farrowing_rate": …} 를 반환   (L110,116)
  └ models/ops.py     KpiSnapshot 컬럼 13개 — farrowing_rate 없음
```

**두 파일이 같은 커밋에서 태어났고, 그때부터 어긋나 있었다.**
`ops.py` 를 건드린 이후 커밋 5건 중 `farrowing_rate` 를 추가·삭제한 것은 없다.
DB 마이그레이션에도 이 컬럼이 등장한 적이 없다.

### A4-2. 판정

```
FARROWING_RATE_MISMATCH_ORIGIN = IMPLEMENTATION_OMISSION
```

**`INTENTIONAL_BLOCK` 이 아니다.** 근거:

```
mismatch 발생   2026-05-29
FARROWING_RATE canonical AMBIGUOUS 판정   2026-08-28 (D-13 재실사)
                                          → 3개월 뒤. 인과 불가.
차단 의도를 기록한 ADR·주석·커밋 메시지   0건
```

`SCHEMA_DRIFT` 도 아니다 — **표류한 적이 없다. 처음부터 맞은 적이 없다.**

### A4-3. 귀결

```
SNAPSHOT_PIPELINE_STATUS = NEVER_OPERATIONAL
```

* `kpi_snapshots` 행 수 = **0** (2026-05-29 이래 단 한 건도 기록된 적 없음)
* daily/weekly/monthly 3개 cron 이 매일 71농장 전건 실패
* `recalculate_farm_kpi`(이벤트 기록 후 on-demand)도 같은 이유로 전건 실패
* ARQ 는 전부 성공(●)으로 보고

★ 이것이 D-19 `V-3 NOT_REPRODUCIBLE` 과 만나는 지점이다.
  과거 severity 를 재현할 수 없는 이유 중 하나가 **스냅샷이 애초에 없기 때문**이다.

---

## A5. 요약 — 무엇이 실제로 틀렸는가

| # | 사실 | 등급 |
|---|---|---|
| R-1 | KPI 스냅샷 파이프라인이 **한 번도 동작한 적 없다** (2026-05-29~) | P0 |
| R-2 | weekly/monthly 집계는 실패를 **세지도 보고하지도 않는다** | P0 |
| R-3 | `recalculate_farm_kpi` 는 전건 실패해도 성공 문자열을 돌려준다 | P0 |
| R-4 | KPI 알림 생성 실패가 **로그조차 남기지 않는다** (`except: pass`) | P0 |
| R-5 | 세 job 이 `errors>0`·`success==0` 에서도 ARQ 성공으로 끝난다 | P1 |
| R-6 | 고객 대면 알림 468건에 판정 provenance 가 없다 | P1 |

## A6. 반증된 가설 — 기록

| 가설 | 결과 |
|---|---|
| `71 farms, 10 created` = 61건 실패 삼킴 | **반증.** 단위가 다르고 멱등 억제로 설명된다 |
| `farrowing_rate` 누락 = FARROWING_RATE 모호성 때문 | **반증.** 3개월 앞선다 |
| 과거 알림이 code_default 로 만들어졌을 수 있다 | **반증.** DMV 로만 가능한 알림 8종 확인 |
