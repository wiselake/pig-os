# MOBILE_PARITY — 웹 → 모바일 반영 대장

> **이 문서는 살아 있는 백로그다.** 웹에 기능·약관·API 계약이 붙거나 바뀔 때마다
> 여기에 한 줄 추가한다. 추가를 빠뜨리면 모바일은 조용히 뒤처지고, 그 사실을
> 출시 직전에 발견하게 된다.
>
> 대상 저장소 (독립 저장소 2개 — PigOS 하위 디렉터리가 아니다)
> ```
> Android  C:\dev\pigos-android   (wiselake/pigos-android)
> iOS      C:\dev\pigos-ios       (wiselake/pigos-ios)
> ```

---

## 0. 기록 규칙

```
웹에 무언가 머지되면 → 이 문서에 항목 추가 → 상태를 셋 중 하나로 유지

  NEEDED     모바일에 반영 필요, 아직 안 됨
  N/A        모바일에는 해당 없음 (사유를 반드시 적는다)
  DONE       반영 완료 — **근거는 `파일:행` 또는 커밋 해시로 적는다. 서술 금지.**
             (CANONICAL_FORMULA_SPEC 의 CONFIRMED 기준과 형식을 맞춘다 —
              한 저장소에 기준이 두 개면 느슨한 쪽으로 수렴한다)
```

★ **`N/A` 를 사유 없이 쓰지 않는다.** "모바일엔 없어도 되겠지" 는 판단이지 사실이 아니다.
★ **API 계약 변경은 기능보다 위험하다** — 모바일이 배포 주기가 길어 구버전이 오래 남는다.
  nullable 여부·필드 추가/삭제는 항상 여기 적는다.

---

## 1. 지금 NEEDED — 우선순위 순

### 1-1. ★ 계정 삭제 화면 (iOS) — App Store 심사 요건

| | |
|---|---|
| 웹 | `src/app/(app)/settings/delete-account/page.tsx` — 구현·배포 완료 |
| API | `DELETE /api/v1/auth/me` (`32b032d`) — 배포 완료 |
| Android | 미확인 |
| **iOS** | **`AuthService.swift`·`AuthDTO.swift` 에 API 는 있는데 View 가 안 잡힌다** |
| 상태 | **NEEDED** |

App Store 가이드라인 5.1.1(v) 는 **앱 내에서** 계정 삭제가 가능할 것을 요구한다.
`pigos.io/support` 에는 "메뉴가 보이지 않으면 이메일로" 폴백을 안내해 뒀지만,
그건 보완이지 요건 충족이 아니다. **iOS 팀에 화면 존재 여부 확인 요청 중.**

### 1-2. ★ 양자(cross-foster) 입력 — 웹에 신규 추가(2026-08-27)

| | |
|---|---|
| 웹 | `record/page.tsx` `FosterPanel` — `FOSTER_IN` / `FOSTER_OUT` |
| API | `POST /piglet_events` — **이미 있었다.** 백엔드 검증도 완비 |
| 모바일 | **양쪽 다 없음** |
| 상태 | **NEEDED** |

★ 이 갭이 **KPI 정합성과 연결된다.** 포유폐사율 경로 ②는
`(born_alive − weaned) / born_alive` 라서 유모돈이 기록되지 않으면 **전출 자돈이 폐사로
계상**된다. 프로덕션 FOSTER 이벤트가 0건인 것은 "안 한다"가 아니라 **"기록할 방법이
없었다"** 였다 — 웹조차 패널이 없었다.

모바일이 구현할 때 지켜야 할 백엔드 제약 (`event_service.py:768~`):
```
target_sow_id 필수 · 자기 자신 금지 · 상대 모돈은 LACTATING 상태여야 함
FOSTER_IN  → 받는 모돈 포유두수 상한 초과 시 서버가 거부(과혼잡 방지)
FOSTER_OUT → 보내는 모돈 포유두수 음수 방지 가드
piglet_count 1~30
```
웹은 상대 모돈 선택지를 `status=LACTATING` 로 필터하고 자기 자신을 제외해
**서버 에러 전에 UI 에서 막는다.** 모바일도 같게 한다.

### 1-3. ★ KPI 표시 정책을 모바일이 무시한다 — 국가 확장의 구조적 갭

| | |
|---|---|
| 백엔드 | `/kpi/presentation` 이 국가별 KPI 집합·순서·현지명을 결정 |
| 웹 | registry-map 렌더링 — 데이터가 화면을 결정 |
| **Android** | **`DashboardScreen.kt:100-101` 이 `KpiCard("PSY")`, `KpiCard("NPD")` 하드코딩. `/kpi/presentation` 미소비** |
| **iOS** | **`DashboardScreen.swift:162-165` 하드코딩. `/kpi/presentation` 미소비** |
| 상태 | **NEEDED** |

★ **Template LOCK 결론의 한정 사유다.** `test_us_template_lock.py` L1~L6 은
백엔드 리졸버 축에서 "국가 추가 = 코드 변경 0" 을 증명했지만, **모바일에는 미치지
않는다.** 신규 국가의 KPI 집합을 데이터로 켜도 모바일 화면은
`PSY / NPD / FARROWING_RATE` 에 고정된 채 남는다.

→ 국가 확장(US 런치 등) **전에** 모바일이 `/kpi/presentation` 을 소비하도록 바꿔야 한다.
  D-17(G3 표시 안전 계약)의 입력이기도 하다.

### 1-4. `pigos.io/privacy` 구 방침 — 앱 내 링크 점검 필요

| | |
|---|---|
| 확정본 | `api.pigos.io/legal/privacy` (v1.0, 시행 2026-08-26) |
| `pigos.io/legal/privacy` | 302 → 확정본 (2026-08-27 배포) |
| `pigos.io/privacy` | **구 방침(공고 2026-04-30)이 아직 게시 중** — 대표 결재 대기 |
| 모바일 | **앱이 어느 URL 을 열고 있는지 미확인** |
| 상태 | **NEEDED (확인)** |

앱이 `pigos.io/privacy` 를 가리키면 **명함 수집용 구 방침**을 보여주게 된다.
`api.pigos.io/legal/privacy` 또는 `pigos.io/legal/privacy` 로 가리켜야 한다.

---


### 1-5. 사료 요약 읽기 API — 계약 확정, **미공개** (2026-09-23, 브랜치 `feat/feed-read-on-main-20260923` · draft PR #11)

| | |
|---|---|
| API | `GET /farms/{id}/feed/summary` · `/feed/months` — 공개 전(API/UI 게이트 `docs/feed/releases/FEED_API_UI_RELEASE_GATE.md`) |
| 계약 (B-1) | 진행 중인 달: `period.partial=true` · `FEED_QTY_CHANGE`·`FEED_COST_CHANGE` 는 `value=null` + `reason="partial_period"` · `period.as_of`·`period.timezone`·`period.comparison`(완료월이면 `"previous_calendar_month"`, 진행 중이면 `null`) · `months[].partial` (필드 추가) |
| 판정 | 서버가 **농장 현지 날짜**로 한다. 월말 당일도 진행 중. 클라이언트는 자기 날짜로 다시 판정하지 않는다 |
| 노출 (D-15a) | `GET /farms/{id}/feed/sources` → `delivered.visibility` = `HIDDEN`(기본) · `REFERENCE_VISIBLE` · `CUSTOMER_VISIBLE`. HIDDEN 이면 `rows`·`last_sync` 는 null, `basis=DELIVERED` 요약·월별은 **404**. 입고 영역은 visible + `rows>0` 일 때만. 클라이언트가 국가 등으로 다시 판정하지 않는다 |
| 데이터 기준일 | `delivered.last_sync.completed_at` (마지막 성공 동기화) — 입고 영역에 항상 표시 · `latest_run_status` ≠ SUCCEEDED 면 실패 표시(값은 유지) |
| 웹 | 기본 기간 = 직전 완료월 · 진행 중이면 MTD 배지 + 비교 UI 없음 |
| Android · iOS | 화면 없음 |
| 상태 | **NEEDED (API 공개 시)** — `null` 을 0 으로 그리지 말 것, `partial` 달은 비교하지 말 것, `reason` 은 키로 받아 현지화 |

## 2. 확인 완료 — 조치 불요

### 2-1. `/kpi/trend` 의 `npd` null 화 (2026-08-27 hotfix `5abb8a4`)

트렌드의 `npd` 는 실제로 WEI 였고 응답에서 null 로 억제했다. 모바일 영향 실측:

| | 결과 |
|---|---|
| 근거 | 위치 |
|---|---|
| Android nullable | `app/src/main/java/io/pigos/app/data/remote/dto/KpiDto.kt:8` `val npd: Double? = null` |
| iOS nullable | `PigOS/Domain/Model/KPI.swift:42` `let npd: Double?` |
| Android NPD 표시 | `ui/screens/dashboard/DashboardScreen.kt:101` — dashboard payload |
| iOS NPD 표시 | `UI/Screens/Dashboard/DashboardScreen.swift:82` — dashboard payload |
| iOS NPD 상세 | `UI/Screens/KPI/AnalyticsScreens.swift:26` — `repo.npd()` = `/kpi/npd` |
| 웹 hotfix | `5abb8a4` (`api/app/services/kpi_service.py` `get_trend` 반환부) |

→ **DONE — 크래시 없음.** 두 표시 경로 모두 dashboard·`/kpi/npd`(여집합 정상)라 값이
  틀리지도 않는다. 영향은 trend 차트의 npd 계열이 비는 것뿐이며, 그 계열을 그리는
  화면이 있는지는 **모바일 팀 확인 대상(미확인)**.

### 2-2. benchmark null 처리

| | 상태 |
|---|---|
| 근거 | 위치 |
|---|---|
| Android nullable | `data/remote/dto/KpiDto.kt:26,31-33,49,51` (`DashboardBenchmarks?`, `KpiBenchmark?`, `benchmarkAvg: Double?`) |
| Android null 가드 | `ui/screens/dashboard/DashboardScreen.kt:131` `data.benchmarks?.let { }` |
| iOS 모델 존재 | Codex 독립검증 `handoff/CODEX_RESULT_2026-08-27.md` C-4 (iOS HEAD `321d4e8`) |

→ **DONE.** D-13 §9 의 "iOS 에 benchmark 필드 자체가 없다" 는 **내 서술이 낡았던 것**이다
  — 당시 `DashboardScreen.swift` 만 grep 했고 모델 계층을 안 봤다. Codex C-4 가 정정.

---

## 3. 다음에 웹에 붙을 때 반드시 여기 적을 것

오늘 진행 중이거나 결재 대기인 것들 — 확정되면 모바일 항목이 생긴다.

| 웹/백엔드 변경 | 모바일 파급 |
|---|---|
| 사산율 산식 확정 (P0-2) | 값이 바뀐다. 모바일은 서버 값을 받으므로 **표시 자체는 무관**하나, 등급 변화를 사용자에게 어떻게 알릴지는 공통 결정 |
| threshold `origin` 승격 (D-19) | severity 발화 조건 변경. 모바일이 색을 자체 계산하면 어긋난다 — **iOS 는 알림 severity 를 다시 매칭한다고 확인됨.** 서버 판정을 그대로 쓰도록 바꿔야 함 |
| G3 표시 안전 계약 (D-17) | `benchmark_status` / `comparison_status` 필드 추가 예정 → **모바일 DTO 갱신 필요** |
| `_avg_active_inventory` 수정 | MSY 값이 바뀐다(표시 로직 무관) |
| 신규 국가 활성화 | §1-3 미해결이면 모바일에 반영 안 됨 |

---

## 4. 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-08-27 | 문서 신설. 오늘 확인분(계정삭제·양자·presentation 하드코딩·trend npd·benchmark) 기록 |
