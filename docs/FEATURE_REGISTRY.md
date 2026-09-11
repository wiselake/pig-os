# FEATURE_REGISTRY

```
목적       기능 하나가 어느 코드에 사는지 — Web / Android / iOS / Core 를 한 줄로 잇는다
관계       상태(PLANNED/DONE 등)는 여기에 쓰지 않는다.  ← docs/PLATFORM_PARITY.md 소관
           여기는 identity 와 **실측 경로** 만 담는다
측정일     2026-08-28
측정 방식  파일 존재 확인 + grep. **추정 경로를 쓰지 않는다.**
           아직 없는 것은 경로를 지어내지 않고 `NOT_PRESENT` 로 둔다
```

## 0. ID 규율

```
형식        PIGOS-F-0001 …
재사용      금지 — 폐기된 ID 를 다른 기능에 다시 쓰지 않는다
의도적 결번  금지
rename      ID 유지. 이름만 바꾼다
split       기존 ID = SUPERSEDED, 신규 ID 를 발급하고 supersedes 를 남긴다
merge       살아남는 ID 하나를 정하고 나머지는 SUPERSEDED
```

`required_platforms` — 그 기능이 성립하려면 반드시 있어야 하는 surface.
`core` 는 백엔드다. 국가별로 required 가 달라지면 그 사실을 비고에 적는다.

---

## PIGOS-F-0001 — COUNTRY_KPI_PRESENTATION

```yaml
feature_id: PIGOS-F-0001
name: 국가별 KPI 표시 정책 소비 (/kpi/presentation)
required_platforms: [core, web, android, ios]
paths:
  core:
    - api/app/routers/base/kpi.py                     # 엔드포인트
    - api/app/services/kpi_policy_resolver.py         # GLOBAL→COUNTRY→FARM_TYPE→TENANT
    - api/app/db/models/kpi_presentation.py
  web:
    - src/lib/kpi/presentation.ts                     # resolveKpiCards
    - src/lib/kpi/cardRegistry.ts                     # 렌더 메타(임계·판정 금지)
  android:                                            # UNMERGED — wiselake/pigos-android#2 (5640711)
    - app/src/main/java/io/pigos/app/ui/screens/dashboard/KpiPresentationResolver.kt
    - app/src/main/java/io/pigos/app/data/remote/dto/KpiDto.kt
  ios:                                                # UNMERGED — wiselake/pigos-ios#2 (0628de1)
    - PigOS/Domain/Model/KpiPresentation.swift
    - PigOS/Data/Repository/KpiRepository.swift
offline_mode: READ_CACHE                              # 정책은 서버 확정. 클라 재정렬 금지
analytics_events: []                                  # 미정의
```

★ **android·ios 경로는 아직 main 에 없다.** 각 저장소 `fix/kpi-status-consumption`
위에 쌓인 stacked branch 이며 merge 0건이다. 경로를 미리 등재한 이유는 다음 세션이
"소비 0건" 이라는 낡은 실측을 다시 믿지 않게 하려는 것이고, 상태는 `NOT_PRESENT` 가
아니라 **`UNMERGED`** 다 — main 기준으로는 여전히 없다.
판정 근거는 `docs/PLATFORM_PARITY.md` §9-3-3.

---

## PIGOS-F-0002 — KPI_STATUS_CONSUMPTION

```yaml
feature_id: PIGOS-F-0002
name: 서버 canonical 판정(kpi_status) 소비
required_platforms: [core, web, android, ios]
paths:
  core:
    - api/app/schemas/kpi.py                          # KpiStatus (normal|warning|critical|insufficient)
    - api/app/services/kpi_status_assembler.py        # Severity → canonical status 변환만
    - api/app/services/kpi_service.py                 # assemble_kpi_status 호출부
  web:
    - src/lib/kpi/statusObservation.ts                # resolveTier — 부재 시 insufficient
  android:
    - app/src/main/java/io/pigos/app/data/remote/dto/KpiDto.kt          # KpiStatusDto · KpiDecision
    - app/src/main/java/io/pigos/app/ui/screens/dashboard/DashboardScreen.kt
  ios:
    - PigOS/Domain/Model/KPI.swift                    # KpiStatusDto · KpiDecision
    - PigOS/UI/Screens/Dashboard/DashboardScreen.swift
offline_mode: READ_CACHE
analytics_events: [kpi_status_mismatch]               # web statusObservation 에서만 발생
notes: >
  status enum 은 서버 계약이다. 클라이언트에서 neutral/unknown/no_alert 를 만들지 않는다.
  insufficient 가 canonical no-judgment 상태다.
```

---

## PIGOS-F-0003 — LOCAL_SEVERITY_REMOVAL

```yaml
feature_id: PIGOS-F-0003
name: 클라이언트 자체 판정 제거 (fail-closed)
required_platforms: [web, android, ios]
paths:
  core: NOT_APPLICABLE                                # 서버는 판정 주체다
  web:
    - src/lib/kpi/status.ts                           # 임계 함수 — 관측용으로만 잔존
    - src/lib/kpi/statusObservation.ts                # 렌더 경로에서 분리
    - src/tests/lib/statusObservation.test.ts
  android:
    - app/src/main/java/io/pigos/app/ui/screens/dashboard/DashboardScreen.kt   # BenchmarkRow
    - app/src/test/java/io/pigos/app/data/remote/dto/KpiDecisionTest.kt
  ios:
    - PigOS/UI/Screens/Dashboard/DashboardScreen.swift                          # dotColor
    - PigOS/UI/Theme/AppColor.swift                                             # SeverityColor default
    - PigOSTests/KpiDecisionTests.swift
offline_mode: NOT_APPLICABLE
analytics_events: []
notes: >
  제거 대상 3종 — Web: 국가 구분 없는 psyTier/npdTier/farrowingRateTier 폴백 ·
  Android: meetsAvg = myValue >= benchmark.avg · iOS: alert 없음 → success.
  benchmark 는 비교 맥락이지 판정 권한이 아니다.
```

---

## PIGOS-F-0004 — APP_VERSION_CONTRACT

```yaml
feature_id: PIGOS-F-0004
name: 클라이언트 platform/app version 송출 · 서버 관측
required_platforms: [core, web, android, ios]
paths:
  core:    NOT_PRESENT                                # 수신·파싱·관측 미구현
  web:     NOT_PRESENT
  android:
    - app/src/main/java/io/pigos/app/di/NetworkModule.kt    # 인터셉터 추가 지점 (현재 auth·logging 둘뿐)
    - app/src/main/java/io/pigos/app/data/repository/DeviceRepository.kt  # 기기등록 시 1회만
  ios:
    - PigOS/Core/Network/APIClient.swift               # 헤더 추가 지점
    - PigOS/Core/Network/Endpoint.swift
offline_mode: NOT_APPLICABLE
analytics_events: []
notes: >
  활성화 순서 고정 — Web → Android → iOS 송출 → 서버 관측 확인 → 그 다음에야
  missing-version fail-closed. 역순 활성화는 정상 클라이언트를 전부 차단한다.
  (PRODUCT_IMPLEMENTATION_HANDOFF §12-1)
```

---

## PIGOS-F-0005 — PRODUCT_INSTRUMENTATION

```yaml
feature_id: PIGOS-F-0005
name: 제품 계측 (이벤트 송출)
required_platforms: [web, android, ios]
paths:
  core: NOT_PRESENT
  web:
    - src/lib/analytics.ts                            # 모듈 존재. key 미설정 → 전면 no-op
  android: NOT_PRESENT                                # 제품 계측 0건
  ios:     NOT_PRESENT                                # 제품 계측 0건
offline_mode: WRITE_QUEUE                             # 설계 시. 현재 transport 없음
analytics_events: PLANNED_14                          # HANDOFF §11 — baseline 아님
notes: >
  ★ AnalyticsApi.kt(Android) / AnalyticsRepository.swift(iOS) 는 계측이 아니라
    prrs-by-genetics 조회 API 다. 이름만 보고 계측으로 분류하지 말 것.
  ★ PostHog secret/key 를 생성하지 않는다.
```

---

## PIGOS-F-0006 — KPI_SNAPSHOT_PIPELINE

```yaml
feature_id: PIGOS-F-0006
name: KPI 스냅샷 집계·영속
required_platforms: [core]
paths:
  core:
    - api/app/jobs/kpi.py                             # 집계 + supported-field contract
    - api/app/jobs/_result.py                         # job 성공 semantics
    - api/app/jobs/worker.py                          # cron 등록
    - api/app/db/models/ops.py                        # KpiSnapshot
    - api/tests/unit/test_snapshot_supported_fields.py
    - api/tests/unit/test_job_result_semantics.py
  web:     NOT_APPLICABLE
  android: NOT_APPLICABLE
  ios:     NOT_APPLICABLE
offline_mode: NOT_APPLICABLE
analytics_events: []
notes: >
  2026-05-29 이래 71농장 전건 실패 상태였다(farrowing_rate 컬럼 부재).
  2026-08-28 supported-field contract 로 per-field fail-safe 적용.
  farrowing_rate · psy 는 산식 미확정으로 여전히 보류(_WITHHELD_FIELDS).
  이 기능에 의존하는 것: WHAT_CHANGED · snapshot-first Home · 과거 비교.
```

---

## PIGOS-F-0007 — NOTIFICATION_DECISION_PROVENANCE

```yaml
feature_id: PIGOS-F-0007
name: 알림 판정 근거 영속 (threshold · authority · formula version)
required_platforms: [core]
paths:
  core:
    - api/app/db/models/ops.py                        # Notification — decision_provenance 미존재
    - api/app/services/notification_service.py        # create_from_alerts
    - api/app/jobs/notifications.py
  web:     NOT_APPLICABLE
  android: NOT_APPLICABLE
  ios:     NOT_APPLICABLE
offline_mode: NOT_APPLICABLE
analytics_events: []
notes: >
  현재 고객 대면 알림 468건에 판정 근거가 없다 → historical_reproducibility = NO.
  설계는 D21_THRESHOLD_GOVERNANCE_DESIGN §11 (JSONB 한 덩어리).
  ★ 과거 468건 backfill 금지 — 오늘의 추정이지 그때의 근거가 아니다.
```

---

## PIGOS-F-0008 — ROLE_AWARE_HOME

```yaml
feature_id: PIGOS-F-0008
name: 역할별 홈 화면
required_platforms: [core, web, android, ios]
paths:
  core:    NOT_PRESENT
  web:     NOT_PRESENT
  android: NOT_PRESENT
  ios:     NOT_PRESENT
offline_mode: READ_CACHE
analytics_events: [home_open]                         # PLANNED
notes: >
  미착수. grep 실측으로 어느 repo 에도 구현이 없음을 확인했다.
  선행: PIGOS-F-0006 (snapshot-first 를 쓸 경우)
```

---

## PIGOS-F-0009 — WHAT_CHANGED

```yaml
feature_id: PIGOS-F-0009
name: 무엇이 바뀌었는가 (기간 대비 변화)
required_platforms: [core, web, android, ios]
paths:
  core:    NOT_PRESENT
  web:     NOT_PRESENT
  android: NOT_PRESENT
  ios:     NOT_PRESENT
offline_mode: READ_CACHE                              # SERVER_ONLY 계산. 오프라인 재계산 금지
analytics_events: [change_card_view, change_card_expand]   # PLANNED
notes: >
  ★ 선행조건 둘 — PIGOS-F-0006 snapshot pipeline correctness · as_of 재현성(G0-D).
    D-19 V-6 = TIMESTAMPED_ONLY 라 as_of 가 선행이다(병렬 불가).
```

---

## PIGOS-F-0010 — ACTION_CENTER

```yaml
feature_id: PIGOS-F-0010
name: 할 일 / 조치 센터
required_platforms: [core, web, android, ios]
paths:
  core:
    - api/app/jobs/tasks.py                           # 기존 task 자동생성 (부분 선행 자산)
    - api/app/services/sync_service.py                # WRITE_QUEUE 재사용 대상
  web:     NOT_PRESENT
  android:
    - app/src/main/java/io/pigos/app/data/local/entity/SyncQueueEntity.kt   # 기존 큐
    - app/src/main/java/io/pigos/app/data/repository/SyncRepository.kt
  ios:
    - PigOS/Core/Sync/SyncScheduler.swift
    - PigOS/Core/Sync/NetworkMonitor.swift
offline_mode: WRITE_QUEUE                             # SERVER_WINS · CLIENT_UUID 멱등 · conflict observable
analytics_events: [action_open, action_start, action_done]  # PLANNED
notes: >
  기존 sync queue 를 재사용한다. 새 큐를 만들지 않는다.
```

---

## PIGOS-F-0011 — FEED_BASIC

```yaml
feature_id: PIGOS-F-0011
name: Feed Basic — FCR · Feed Cost/pig · Feed Cost/kg gain (EPIC 4)
issued: 2026-09-11                                    # 착수 시점 발급 (§0 규율)
required_platforms: [core, web]                       # 모바일은 READ_CACHE 소비만 — 산식 하드코딩 금지 (HANDOFF §0-6)
paths:
  core:
    - api/app/engine/feed_metrics.py                  # ★ 신규 — canonical 산식 FEED_BASIC.v1 · 유보 이유 · 응답 미연결
    - api/app/services/feed_service.py:load_feed_cohort  # ★ 신규 — kpi_service 와 같은 CLOSED 그룹 코호트 (라우터 0)
    - api/tests/unit/test_feed_metrics.py
    - api/tests/integration/test_feed_cohort.py       # 코호트 FCR == build_herd_kpis FCR 동치
    - api/app/db/models/health.py                     # FeedRecord (quantity_kg · unit_cost · currency · group_id)
    - api/app/services/feed_service.py                # 입력 CRUD (기존)
    - api/app/services/kpi_service.py:438-535         # FCR = SUM(feed_records.quantity_kg) / gain, CLOSED 그룹 (기존)
    - api/app/engine/rules/grow_finish.py:17          # fcr.high (기존)
    - api/app/services/report_service.py              # cost-summary: feed_cost = unit_cost×qty (기존)
  web:
    - src/app/(app)/feed/page.tsx                     # 입력 (기존)
    - src/app/(app)/reports/cost/page.tsx             # 원가 리포트 (기존)
  android: NOT_APPLICABLE                             # v1 은 웹만. 산식은 서버에만 둔다
  ios:     NOT_APPLICABLE
offline_mode: READ_CACHE                              # 값은 서버 계산. 오프라인 재계산 금지
analytics_events: []                                  # 미정의
```

### 착수 실측 (2026-09-11 · step 0)

```
있는 것
  FCR                kpi_service:535 — 기본 KPI 응답에 실려 전 사용자에게 나간다
  kpi_definitions    FCR 행 있음 (c5e7a9b1 KR_MAP · c7d9e1f3 country policy: SECONDARY · CONTEXT_ONLY)
  snapshot           KpiSnapshot.fcr 컬럼 있음 (ops.py:73) · _WITHHELD 아님 → 잡 성공 시 영속
  cost-summary       feed_cost(unit_cost×qty) · feed_cost_coverage 로 미입력분 표시

없는 것
  FEED_COST_PER_PIG · FEED_COST_PER_KG_GAIN   산식·정의행·테스트 전부 없음
  canonical formula 버전 표기                  FCR 도 산식 문서(specs/2026-03-19)와 코드 대조 미실시
  bounded action checklist                     없음

★ ①≠② 발견
  routers/base/kpi.py:6  "FCR → Addon #1 (ADDON_FCR) — handled in addons/fcr router"
  addons/               __init__.py 뿐. fcr 라우터 없음. require_addon("ADDON_FCR") 호출 0건
  ops.py:72             "only populated when ADDON_FCR subscribed" — 실제로는 구독과 무관
  → FCR 은 문서상 유료, 런타임상 무료. COUNTRY_PRODUCT_SPEC_BR:58 도 유료라 적음
  → 주석은 26c2e68(2026-05-29) 최초 구현부터, 기본 응답 노출은 63acdff(2026-06-23)부터
  ★ 즉 FCR 은 이미 (가)로 출시돼 있다. D-15 는 FCR 에 대해 대칭이 아니다 —
    (a) 무료 추인 = 비용 0 / (b) 유료 확정 = 회수. 기울기 측정 = HUMAN_INPUT_QUEUE B-7
  → 이 기능이 고치지 않는다. DECISION_REGISTER D-15 에 사실로 적었다
```

### 범위 결정 — (나) 계산만, 응답 미노출 (두 세션 권고 · 대표 미확인)

```
(가) 새 두 값을 KPI 응답에 실어 무료로 노출   → 나중에 유료로 옮기면 "있던 것을 뺏는" 변경
(나) 산식·정의·테스트만 만들고 응답에 안 실음  → D-15 결재 후 한 줄로 노출. 되돌리기 싼 쪽
```

step 1 (2026-09-11): `engine/feed_metrics.py` + `load_feed_cohort` + 테스트 12건. 산식 규율:
unit_cost 없는 행이 하나라도 있으면 부분합을 원가로 내지 않는다(COST_INCOMPLETE) ·
통화가 섞이면 환산하지 않는다(CURRENCY_MIXED) · 코호트 FCR 은 kpi_service FCR 과 동치(테스트).
어느 라우터에도 연결 안 됨. 백엔드 1468 passed · 1 skipped · 12 xfailed.

Feed Cost 두 값은 EXPANSION_DECISION §5-2 와 HANDOFF §6-5 둘 다 **Paid hypothesis** 로
적고 있다. 승인 전 paywall 금지 규칙 때문에 게이트를 달 수 없고, 게이트 없이 노출하면
사실상 무료 확정이 된다. 그래서 (나).

★ 근거의 정확한 위치: "사실을 만들지 않기"가 아니다 — 부모 지표 FCR 에서 그 사실은 이미
만들어져 있다. **이미 있는 사실 위에 두 번째를 얹지 않기**다. 나중에 "왜 FCR 은 열고
이 둘은 닫았나"의 답이 이 문장이다.

step 1c: 응답 계약 `schemas/feed.py:FeedBasicOut` 을 지금 둔다 — `withheld` 칸 포함. 라우터 0.
노출 전이라 비용 0. 노출 뒤에 유보 이유를 넣으면 게시된 계약 변경(세 클라이언트).
원가 칸이 비었을 때 "0" 인지 "못 냈다" 인지를 응답이 말한다 — M-3 fail-OPEN 과 같은 모양을 막는다.

★ B-7 이 0 이면 이 기능의 성격이 바뀐다 — 분석이 아니라 입력 경로 프로젝트. PHASE 1 계약
설계 전에 B-7 을 본다 (HUMAN_INPUT_QUEUE B-7).

step 1b: 제외 집합 동치 테스트 3건 추가 — feed_metrics 가 FCR 을 유보(NO_GAIN·NO_FEED)하면
kpi_service 도 None 이어야 하고, 원가만 유보(COST_INCOMPLETE)하면 양쪽 다 FCR 을 보고한다.
그 상태("FCR 은 뜨고 Feed Cost 만 빔")의 이유는 feed_metrics.withheld 에만 있고 KPI
응답에는 아직 없다 — 노출 시점에 같이 실어야 할 것. 대표가 한 단어로 (가)를 고르면 그때 노출한다.

---

## 부록 — 다음에 등록할 후보 (아직 ID 미발급)

```
Weekly Brief · Health Watch · Root Cause Candidate ·
Benchmark Depth · Multi-farm · Contextual AI Copilot
```

ID 는 **실제 착수 시점에** 발급한다. 미리 예약해 두면 결번이 생긴다.
