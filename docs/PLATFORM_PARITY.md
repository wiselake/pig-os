# PLATFORM_PARITY — Web · Android · iOS 구현 상태 SSOT

> **이 문서가 플랫폼 구현 상태의 유일한 SSOT다.**
> `pigos-android/docs/*` · `pigos-ios/docs/*` 에 이 상태값을 복제하지 않는다.
> 모바일 저장소 문서는 build·signing·store release·platform-specific architecture ·
> offline 구현 세부 · native dependency · push 설정 등 **플랫폼 고유사항만** 다룬다.
>
> **Renamed from `docs/MOBILE_PARITY.md` at `4ff8a30`.**
> Pre-rename history: `git log docs/MOBILE_PARITY.md`
>
> `git log --follow docs/PLATFORM_PARITY.md` 는 이 연결을 자동으로 잇지 못한다.
> rename 과 대규모 내용 수정이 **같은 commit** 에 들어가 Git rename heuristic 의
> 유사도 임계 아래로 떨어졌기 때문이다. **pre-rename commit 은 전부 보존돼 있고**
> 위 명령으로 조회된다. history rewrite 는 하지 않는다.

### 규율 — 문서 rename 은 commit 을 분리한다

```
1. rename-only commit      (git mv 만. 내용 변경 0)
2. content-change commit   (내용 수정)
```

한 commit 에 섞으면 `--follow` 가 끊긴다. 이 문서가 그 사례다.

```
STEP 0 완료   2026-08-28
범위          문서 이관 + 기존 evidence 재판정 + Track B 사실 고정 + blocker 확인
미포함        D-19 실행 · Product v1.1 patch · FEATURE_REGISTRY · 코드 수정 ·
              CI/Release Gate 구현 (전부 후속 STEP)
```

---

## 0. 규율

### 0-1. Parity 기준은 화면 동일성이 아니다

```
same farm · same as_of · same country · same permission · same entitlement
   →  same KPI value
   →  same severity
   →  same benchmark availability
   →  same rule meaning
   →  same action semantics
```

Web/Android/iOS 화면은 달라도 된다. **공통 business logic 을 모바일에 다시
하드코딩하지 않는다.**

### 0-2. 상태 필드 이름 — `status` 단독 사용 금지

상태 축마다 의미가 드러나는 이름을 쓴다. 한 저장소에 `status` 가 여럿이면
어느 축의 상태인지 추적이 끊긴다.

```
formula_status · audit_status · migration_status · gate_status ·
platform_implementation_status · parity_result · runtime_verification_status
```

**이 문서의 셀 상태 이름은 `platform_implementation_status` 다.**

### 0-3. 셀 enum

```
PLANNED · IN_PROGRESS · DONE · PENDING_RECHECK · BLOCKED · NOT_APPLICABLE
```

`NOT_APPLICABLE` 은 반드시 `not_applicable_reason` 을 가진다. **사유 없는 N/A 금지.**

### 0-4. `DONE` 은 evidence commit 필수

```
implementation_commit   immutable SHA
evidence_paths          영향 코드 경로
verified_at             확인 일자
```

자기 커밋 안에 자기 SHA 를 못 쓰므로 **2-phase** 다:

```
① implementation commit  (모바일 저장소)
② central parity evidence commit  (이 문서에 그 SHA 등록)
```

**SHA 없으면 `DONE` 금지.** 기존 문서였다는 이유의 grandfathering 도 금지.

### 0-5. `parity_result` 는 사람이 쓰지 않는다

셀에서 계산한다(스크립트는 후속 STEP).

```
required 플랫폼 셀이 전부 DONE | NOT_APPLICABLE  →  PARITY_VERIFIED candidate
그 외                                            →  PARTIAL
```

### 0-6. Evidence staleness

`implementation_commit` 이후 `evidence_paths` 중 하나라도 바뀌면
`DONE → PENDING_RECHECK` 후보다.

```
git diff <implementation_commit>..HEAD -- <evidence_paths>   → non-empty 면 stale
```

`CANONICAL_FORMULA_SPEC` 에서 겪은 *"예전에 CONFIRMED → 코드 변경 → 문서는 계속
CONFIRMED"* 를 여기서 반복하지 않는다. 검출 스크립트는 후속 STEP.

---

## 1. ★ 이번 실사의 핵심 사실 — 위험의 종류를 나눈다

```
VALUE_INTEGRITY_RISK       NO    양 플랫폼에 KPI 산식 하드코딩이 없다
DECISION_INTEGRITY_RISK    YES   판정을 플랫폼이 자체 생성한다
PRESENTATION_PARITY_RISK   YES   같은 응답에 두 플랫폼이 다른 의미를 표시한다
```

**같은 `benchmark = null` 에 대해:**

```
Android  →  TextMuted / 회색   (fail-closed)
iOS      →  success / 초록      (fail-OPEN)
```

같은 farm · 같은 `as_of` · 같은 country · 같은 backend response 인데
**두 앱이 사용자에게 서로 다른 의미를 말한다.** 이것이 현존하는 parity violation 이다.

★ `meetsAvg` 는 **값을 바꾸지 않는다.** 그러나 **사용자 판정을 생성**하므로
위험을 낮게 평가하지 않는다. 계산엔진을 모바일마다 재구축할 필요는 없다 —
고칠 것은 **판정의 출처**다.

---

## 2. 기존 6행 재판정 — grandfathering 없음

`MOBILE_PARITY.md` 시절 `DONE` 이던 2건을 evidence 규칙으로 다시 봤다.

```
모바일 저장소 implementation commit 조회 결과
  pigos-android  최근 = 7545841 (FCM google-services.json)   ← parity 구현 커밋 없음
  pigos-ios      최근 = 6f5dad7 (SUBMISSION 문서 갱신)        ← parity 구현 커밋 없음
```

| 기존 행 | 기존 | 재판정 | 사유 |
|---|---|---|---|
| `/kpi/trend` npd null 화 | DONE | **IN_PROGRESS** | 모바일 implementation SHA **없음**. DTO 가 이미 nullable 이라 크래시는 없으나 그것은 **audit finding** 이지 구현 DONE 이 아니다. trend npd 계열을 그리는 화면이 있는지 **미확인** |
| benchmark null 처리 | DONE | **IN_PROGRESS** | 모바일 implementation SHA **없음**. Android `data.benchmarks?.let{}` 는 기존 코드이지 parity 작업 산출물이 아니다 |
| iOS 계정 삭제 화면 | NEEDED | **BLOCKED** | App Store 5.1.1(v). `AuthService`/`DTO` 는 있으나 View 미발견 |
| 양자(cross-foster) 입력 | NEEDED | **PLANNED** | 웹 `2fedb9c` 로 신규. 모바일 양쪽 없음 |
| `/kpi/presentation` 미소비 | NEEDED | **BLOCKED** | §3 참조 |
| `pigos.io/privacy` 구 방침 링크 | NEEDED (확인) | **NOT_APPLICABLE** (앱) · **★ 웹 노출 OPEN** | 2026-09-11 실측: Android·iOS 소스에 pigos.io/privacy·/terms 링크 0건 — 앱은 열지 않는다. 그러나 공개 사이트 자체가 5/30 자 한국어 구본 방침과 피그플랜 문안 약관을 서빙 중 — `KNOWN_PUBLICATION_EXPOSURE` "격리 밖 노출" · H17 |

```
LEGACY_ROWS
  total                        6
  previous_done                2
  done_with_sha                0
  downgraded_due_missing_sha   2
```

★ **`done_with_sha = 0` 이다.** 첫날부터 예외를 두지 않았다.

---

## 3. Track B 실측 — 2026-08-28 (read-only)

> Android: 코드 정적분석. iOS: `STATIC_CONFIRMED` / `NOT_RUNTIME_VERIFIED` (빌드 환경 없음).

### 3-1. `COUNTRY_KPI_PRESENTATION`

| | `platform_implementation_status` | 근거 |
|---|---|---|
| Core/Web | DONE | `/kpi/presentation` 제공 · 웹은 registry-map 렌더 |
| **Android** | **BLOCKED** | `/kpi/presentation` 미소비. `DashboardScreen.kt:100-101` `KpiCard("PSY")`/`("NPD")` · `KpiDto.kt:31-33` `@SerializedName` 고정 |
| **iOS** | **BLOCKED** | 미소비. `DashboardScreen.swift:162-165` 하드코딩. `runtime_verification_status = NOT_RUNTIME_VERIFIED` |

`hardcode_classification = LABEL_ONLY + PRESENTATION_POLICY`

### 3-2. `KPI_STATUS_CONSUMPTION`

| | 상태 | 근거 |
|---|---|---|
| Core/Web | DONE | `(app)/page.tsx:120,158-160` `resolveTier(kpi_status,…)` + `reportStatusMismatches` |
| **Android** | **BLOCKED** | `kpi_status` 소비 **0건** (전 소스 grep) |
| **iOS** | **BLOCKED** | `kpi_status` 소비 **0건** |

### 3-3. `MOBILE_LOCAL_SEVERITY` — DECISION_INTEGRITY_RISK

> ### ★ 정정 (2026-08-28) — Web 행은 틀렸다
>
> 이전 판정 `Core/Web = NOT_APPLICABLE · 자체 판정 경로 없음` 은 **사실이 아니다.**
> D-19 v1.4 감사(N-7)에서 웹 프론트 자체 임계가 발견됐다.
> **"Web 은 판정 reference implementation 이다" 라는 전제를 폐기한다.**

| | 상태 | 근거 |
|---|---|---|
| **Core/Web** | **BLOCKED** — `WEB_LOCAL_STATUS_FALLBACK` | `src/lib/kpi/status.ts` — `psyTier >=28/>=22` · `npdTier <=35/<=50` · `farrowingRateTier >=90/>=80`. `statusObservation.ts:53 resolveTier()` 가 backend `kpi_status` 부재 시 이 값으로 폴백 |
| **Android** | **BLOCKED** | `DashboardScreen.kt:238-243` `meetsAvg = myValue >= b.avg` → Success/Warning. **벤치마크를 판정으로 변환** |
| **iOS** | **BLOCKED** | `DashboardScreen.swift:241-246` alert 없음 → `AppColor.success`. **판정 없음이 초록(FAIL-OPEN)** |

### 3-3-1. ACTIVE vs DORMANT — 같은 BLOCKED 가 아니다

```
Android · iOS   ACTIVE   매 렌더마다 자체 판정이 실행된다
Web             DORMANT  backend kpi_status 가 있는 동안은 발동하지 않는다
```

```
WEB_LOCAL_STATUS_FALLBACK
platform_implementation_status = BLOCKED
risk                = CROSS_COUNTRY_DECISION_RISK
current_user_impact = NOT_OBSERVED
trigger             = backend kpi_status 부재 / 배포 스큐 / contract mismatch
```

★ `CROSS_COUNTRY_DECISION_RISK` 인 이유: 이 임계는 **국가 구분이 없다.**
`psyTier >= 28` 은 KR 기준이고, 서버 DMV 는 US PSY 임계를 26/23 으로 둔다.
폴백이 발동하는 순간 **미국 농장에 한국 기준이 적용된다.**

현재 미발동 근거(도달성 확인함):

```
backend kpi_status 키   PSY · NPD · FARROWING_RATE · SOW_TURNOVER
KPI_CARD_REGISTRY      동일 4종
presentation 미지 코드  unknownCodes 로 분리되어 렌더되지 않음
→ 오늘은 발동하지 않는다. 그러나 응답에서 kpi_status 가 빠지는 순간 발동한다.

### 3-4. `KPI_FORMULA_LOCAL_CALCULATION`

> 사실 확인과 구현 DONE 을 혼동하지 않는다.

```
audit_finding = NO_LOCAL_FORMULA_FOUND     (양 플랫폼)
```

| | 상태 | 근거 |
|---|---|---|
| **Android** | **IN_PROGRESS** | `ui/` 전수에서 KPI 산식 계산 **0건**. DTO 계산 프로퍼티 0건. 그러나 이를 잠그는 회귀 수단이 없어 `DONE` 아님 |
| **iOS** | **IN_PROGRESS** | `Domain/`·`Data/` 계산 프로퍼티 **0건**. `STATIC_CONFIRMED` only |

★ `VALUE_INTEGRITY_RISK = NO`. **모바일 수정 범위가 값이 아니라 판정·표시로 좁혀진다.**

### 3-5. `BENCHMARK_NULL_BEHAVIOR`

| | 상태 | 근거 |
|---|---|---|
| **Android** | IN_PROGRESS | `DashboardScreen.kt:131` `data.benchmarks?.let{}` · `:241` `null → TextMuted`. 로컬 상수 fallback 미발견. implementation SHA 없어 DONE 아님 |

```
Android safety_behavior   = FAIL_CLOSED_BY_COINCIDENCE
Android contract_compliance = NO
```

★ Android 가 무채색을 내는 것은 결과적으로 fail-closed 이지만, 서버 `kpi_status=insufficient` 를
  **소비한 결과가 아니다.** benchmark 가 null 이라서 그런 것이다. benchmark 가 채워지면
  서버가 `insufficient` 를 내더라도 `meetsAvg` 가 다시 판정을 만든다(§3-3). **contract 준수 아니다.**
| **iOS** | **BLOCKED** | `benchmarks` 모델은 존재하나 alert 부재를 초록으로 표현 = **fail-OPEN** |

★ **두 플랫폼이 같은 입력에 다른 의미를 낸다** — §1 의 `PRESENTATION_PARITY_RISK` 실체.

### 3-6. `APP_VERSION_REQUEST_REPORTING`

| | 상태 | 근거 |
|---|---|---|
| **Core/Web** | **BLOCKED** | 요청 헤더에 앱/클라이언트 버전 없음 |
| **Android** | **BLOCKED** | `DeviceRepository.kt:26` **기기등록 시 1회만**. `NetworkModule` 인터셉터는 `auth`·`logging` 둘뿐 → **per-request 헤더 없음** |
| **iOS** | **BLOCKED** | `PushNotificationService.swift:47` **기기등록 시 1회만**. `APIClient`/`Endpoint` 헤더는 `Authorization`·`Content-Type`·`Accept` 뿐 |

### 3-7. `FORCE_UPDATE / LEGACY_CONTROL`

| | 상태 | 근거 |
|---|---|---|
| **Android** | **BLOCKED** | `forceUpdate`/`minVersion`/`426` 등 **0건** (`Color.kt` 매치는 hex `0xFF0E1426` 오탐) |
| **iOS** | **BLOCKED** | **0건** |

★ **새 앱에 force-update 를 넣어도 이미 설치된 구버전에는 그 코드가 없다.** §5 참조.

### 3-8. `PRODUCT_INSTRUMENTATION`

| | 상태 | 근거 |
|---|---|---|
| **Core/Web** | **BLOCKED** | `lib/analytics.ts` 는 존재하나 `NEXT_PUBLIC_POSTHQ_KEY` 미설정 → `enabled()` false → **전면 no-op**. 배포 번들 전량(12청크) 검사에서 `phc_` 키 0건, 모듈은 번들됨 |
| **Android** | **BLOCKED** | 제품 계측 **0건** |
| **iOS** | **BLOCKED** | 제품 계측 **0건** |

> ★ **정정 기록**: `AnalyticsApi.kt`(Android) · `AnalyticsRepository.swift`(iOS) 를
> 계측으로 보고했던 것은 **틀렸다.** 둘 다 `prrs-by-genetics` **조회 API** 다.
> **이름만 보고 판단하지 않는다.**

### 3-9. `OFFLINE_CONTRACT` (발견 기록만 — 설계는 후속 STEP)

| | 발견 |
|---|---|
| **Android** | `Room` · `SyncQueueEntity` · `PigOsDatabase` — **기존 offline write queue 존재**. 로컬 엔티티는 `Event`·`Sow`·`SyncQueue` 뿐 → **KPI/presentation 캐시 없음** → `stale KPI local cache risk = not observed`, KPI 는 사실상 **online-only** |
| **iOS** | `NetworkMonitor` · `Core/Sync` 존재. KPI 캐시 여부 **미확인** |

★ 후속 설계 시 **Android 는 기존 `SyncQueueEntity` 를 재사용**한다. 별도 큐 생성 금지.

---

## 4. `BACKEND_NO_JUDGMENT_STATE` — ★ PRESENT

> 모바일 SAFETY FIX 의 선행조건 확인 (read-only)

```
result   : PRESENT
evidence : api/app/schemas/kpi.py  class KpiStatus
           status: normal | warning | critical | insufficient
           reason 어휘 8종: no_data · insufficient_sample · out_of_valid_range ·
                            no_policy · policy_pending · evaluation_skipped ·
                            rule_disabled · context_missing
```

★ 그리고 docstring 이 결정적이다:

> *"reason: 항상 존재(없으면 None). optional 로 두면 프론트가 유무로 분기 →
> **판단 로직의 입구가 됨**."*

**프론트 판단 금지를 스키마 설계 단계에서 이미 의도했다.**

```
SAFETY_FIX_PREREQUISITE : 불필요
```

→ 모바일은 **새 상태를 설계할 필요가 없다.** 이미 있는 `insufficient` 를 소비하면 된다.
   `alert 없음 → NEUTRAL` 을 모바일이 **새로 판단하게 하지 않는다.**

> 참고: 룰엔진 내부 `Severity` enum 은 `OK/INFO/WARNING/CRITICAL` 로 "판정 없음" 이
> 없으나, 룰이 발화하지 않으면 `Finding` 자체가 없으므로 다른 축이다.
> 사용자에게 나가는 계약은 `KpiStatus` 다.

---

## 5. `LEGACY_CLIENT_GATE` — 구현 순서 강제 (메모)

**잘못된 순서** — 이대로 켜면 Web 자신이 차단된다:

```
server: missing app-version header → LEGACY_CLIENT → deny     ✗
```

Web 도 현재 버전 헤더를 보내지 않는다(§3-6).

**정확한 순서:**

```
1. Web    version/platform header 송출
2. Android version/platform header 송출
3. iOS    version/platform header 송출
4. 서버에서 세 표면 header 수신 검증 (observability)
5. 이후에만  missing version = LEGACY_CLIENT  fail-closed 활성화

HEADER_TRANSMISSION → SERVER_OBSERVABILITY → LEGACY_FAIL_CLOSED
```

---

## 6. `LEGACY_CLIENT_TEST_CAPABILITY`

| | 결과 | 근거 |
|---|---|---|
| **Android** | **PARTIAL** | 저장소·빌드산출물에 APK/AAB **0건**, `app/build/outputs` 없음. CI(`android.yml`)가 `assembleDebug` 로 debug APK 를 만들지만 **artifact 업로드는 test report 뿐**. **과거 버전 APK 를 구할 수단이 없다** |
| **iOS** | **PARTIAL** | IPA/`xcarchive` **0건**. CI(`ci.yml`, `macos-15`)가 XcodeGen→`xcodebuild test` 로 **시뮬레이터 빌드·테스트는 가능**. **실기기 설치 가능한 과거 build 는 없음** |

★ 이번 STEP 0 에서 테스트를 억지로 실행하지 않았다. **수단 존재 여부만 확인했다.**

### 6-1. `ANDROID_RELEASE_ARTIFACT_RETENTION` — OPEN ISSUE

```
platform_implementation_status = NOT_IMPLEMENTED
current_build_capability       = AVAILABLE      (assembleDebug 가능)
artifact_retention             = NONE           (APK/AAB 업로드 없음. test report 만)
```

**권고**: 향후 버전별 APK/AAB artifact 를 저장하여 legacy-client regression test
자산을 축적한다. 지금 저장을 시작하지 않으면 **다음 버전부터도 과거 build 가 없다.**

★ 이번 STEP 에서 **CI 수정 금지.** 기록만 한다.

→ 구버전이 새 국가 API 거부에 어떻게 반응하는지 **검증할 수단이 현재 없다.**
   `COUNTRY_ROLLOUT_BLOCKER` 후보로 등록한다.

---

## 7. `IOS_RELEASE_CAPABILITY`

```
IOS_RELEASE_CAPABILITY = CI_EXTENSION_REQUIRED
```

| 항목 | 상태 | 근거 |
|---|---|---|
| CI macOS runner | **AVAILABLE** | `.github/workflows/ci.yml` — `runs-on: macos-15` |
| XcodeGen | **AVAILABLE** | 커밋된 `.xcodeproj` 없음. CI 가 생성 |
| `xcodebuild test` | **AVAILABLE** | 시뮬레이터 빌드·테스트 통과 경로 존재 |
| `xcodebuild archive` | **NOT_IMPLEMENTED** | ci.yml 에 단계 없음 |
| code signing | **NOT_IMPLEMENTED** | 〃 |
| TestFlight / distribute | **NOT_IMPLEMENTED** | fastlane·App Store Connect 단계 없음 |
| 로컬 빌드 | UNAVAILABLE | 현재 머신이 Windows(MINGW64). macOS/Xcode 없음 |

★ **`iOS build infrastructure unavailable` 이라고 일반화하지 않는다.**
  빌드·테스트 인프라는 **있다.** 없는 것은 **배포 파이프라인** 이고, 이는 기존 CI 를
  확장하면 되는 문제다 — 새 인프라 조달이 아니다.

**향후 확인 대상** (이번 STEP 구현 금지):

```
xcodebuild archive
code signing
provisioning profile
App Store Connect credentials / API key
export (ExportOptions.plist)
TestFlight / App Store distribution
```

`country_rollout_impact`:

> **iOS 가 required platform 인 국가에 한해**, 수정 버전을 build·sign·distribute 할 수
> 있는 capability 가 rollout prerequisite 다. **현재 build·test 는 CI 로 가능하나
> distribute 경로가 없다.**
>
> ★ iOS 를 지원하지 않는 국가까지 막지 않는다. *"iOS 빌드 인프라가 모든 국가 rollout 의
> 무조건 blocker"* 로 일반화하지 않는다.

---

## 8. `INSTRUMENTATION_REALITY` — Handoff 14개 이벤트의 실제 지위

```
Web        PostHog key 미설정 → no-op          BLOCKED
Android    제품 계측 0건                        BLOCKED
iOS        제품 계측 0건                        BLOCKED
```

→ `PIGOS_PRODUCT_IMPLEMENTATION_HANDOFF v1.0 §11` 의 14개 이벤트는
**`EXISTING_BASELINE` 이 아니라 `PLANNED_INSTRUMENTATION` 이다.**

`OPEN ISSUE` 로 등록 — Product v1.1 patch 대상(후속 STEP). **이번 STEP 0 에서 계측 구현 금지.**

---

## 9. `P0_CORRECTNESS_BLOCKERS` — parity 미구현이 아니라 **현재 결함**

> ★ 아래는 "아직 안 만든 것" 이 아니라 **지금 사용자에게 잘못된 판단을 표시하는 것** 이다.
> `OPEN_BLOCKERS`(§9-1) 와 분리한다. 우선순위가 다르기 때문이다.

### P0-1. iOS `insufficient` / no-judgment → `success`(초록)

```
Backend
  KpiStatus.status = insufficient        데이터 불충분 / 판정 불가

iOS
  DashboardScreen.swift:241-246
  alert 없음 → AppColor.success          정상 / 초록
```

**서버의 "판정 불가" 를 클라이언트가 "정상" 으로 뒤집는다.**

```
platform_implementation_status = BLOCKED
risk                           = SERVER_DECISION_OVERRIDE
class                          = CORRECTNESS_DEFECT   (parity gap 아님)
```

이는 제품 선택이 아니라 결함이므로 **결재 대상이 아니다.** 서버는 이미
`insufficient` 를 갖고 있으므로(§4) 신규 상태 설계 없이 소비하면 된다.

---

### P0-ANDROID-DETAIL-SEVERITY. Android `KpiDetailScreen` benchmark 유래 판정

> ★ **P0-1 과 합치지 않는다.** 뿌리는 같지만(판정 권한 누수) 결함 위치·수정 SHA·
> 회귀 테스트·runtime 검증·종료 시점이 모두 다르다. 한 항목으로 묶으면 한쪽만
> merge·검증됐는데 전체 P0 가 닫힌 것처럼 보인다.
>
> ★ **번호를 `P0-2` 로 쓰지 않는다.** 그 번호는 KPI 트랙에서 이미 다른 의미로 쓰이고 있다
> (`docs/kpi/CANONICAL_FORMULA_SPEC.md` §10 "AMBIGUOUS Items → P0-2 Decision",
> `D19_THRESHOLD_SOURCE_AUDIT.md` §6 "사산 P0-2"). 번호 재사용은 금지한다.

```
root_cause    client-side decision authority leakage
class         CORRECTNESS_DEFECT   (parity gap 아님)
risk          SERVER_DECISION_OVERRIDE
```

**finding**

`KpiDetailScreen.BenchmarkGauge` 가 농장값과 벤치마크 평균을 비교해 색을 직접 만들었다.

```kotlin
// KpiDetailScreen.kt:123  (수정 전)
val meetsAvg = if (higherIsBetter) myValue >= avg else myValue <= avg
val dotColor = when (meetsAvg) { true -> Success; false -> Warning; null -> TextMuted }
```

PR #1 이 대시보드에서 걷어낸 패턴이 상세 화면에 남아 있었다. 이 `dotColor` 는 게이지 점과
값 텍스트를 함께 칠하므로, 같은 KPI 가 두 화면에서 다른 판정으로 보일 수 있었다.

```
대시보드   서버 kpi_status = critical   →  빨강
상세       myValue >= avg               →  초록
```

**왜 단순 제거로 끝나지 않았는가**

`/kpi/psy` · `/kpi/npd` 응답에는 `kpi_status` 가 없다(benchmark 값만 있다). 상세 화면은
판정 재료 없이 화면을 그려야 했고 손에 있던 benchmark 로 자체 판정했다. 코드를 지우는 것이
아니라 **판정 소스를 연결**해야 했다 — 값은 상세 엔드포인트, 판정은 대시보드와 같은
`kpi_status` 맵(`KpiDetail.decisions`). 조회 실패 시 빈 맵 → `INSUFFICIENT`(무채색)이며
초록으로 승격하지 않는다.

**invariant**

```
server kpi_status  =  sole severity authority
benchmark          =  comparison context only
Dashboard severity == Detail severity          같은 소스 + 같은 decisionColor 함수
NO_VERDICT         →  INSUFFICIENT (초록 승격 금지)
```

`decisionColor` 를 `private` → `internal` 로 바꿔 두 화면이 같은 함수를 쓰게 했다.
매핑을 복제하면 한쪽만 고쳐져 다시 갈라진다.

**remediation**

```
PR                wiselake/pigos-android#4  fix/kpi-detail-server-severity
base              fix/kpi-status-consumption (#1)   — PR #2(presentation)와 무의존
diff              3 files · +49 −23
```

**상태 — 축을 분리한다**

```
implementation_status           DONE
implementation_sha              183aaa8
delivery_status                 NOT_MERGED
platform_implementation_status  IN_PROGRESS
    ★ CLAUDE.md §5 열거형은 DONE 에 implementation commit SHA 를 요구하고,
      그 SHA 는 main 에 있어야 한다. 183aaa8 은 아직 branch 위에 있다.
      "DONE_ON_BRANCH" 는 열거형에 없으므로 축을 나눠 표기한다.
regression_test_status          PASS
runtime_reproduction_status     NOT_RUNTIME_VERIFIED
```

**regression_evidence**

```
① behavioral conflict fixture   server=CRITICAL · myValue=29.0 · benchmark avg=28.0
                                (PSY 는 높을수록 좋음 → 로컬 계산은 초록을 냈다)
                                역방향(server=normal, 벤치마크 미달)과 NPD 방향도 함께 잠금
② structural guard              주석 제거 후 banned 패턴 검사
                                banned: meetsAvg · higherIsBetter · ">= avg" · "<= avg"
                                현재 브랜치 0건 · base 브랜치 5건 검출 확인
③ shared-function guard         decisionColor 정의가 DashboardScreen 에 1개,
                                상세 화면에 0개 — 매핑 복제 금지
파일                            KpiDetailSeverityTest.kt (8건)
로컬                            441 tests · 0 failures
CI                              run 33588525343 · build-and-test pass 4m44s
```

★ **①과 ②를 함께 유지한다.** 처음 작성한 계약 테스트(①만)는 **구 코드에서도 통과했다** —
구 코드는 `KpiDecision` 을 거치지 않고 `dotColor` 를 직접 만들었기 때문에 제거된 경로를
지나지 않는다. 그것을 확인한 뒤 ②를 추가했다. 반대로 ②만 남기면 소스 패턴은 피하면서
동작이 어긋나는 변형을 놓친다. 둘은 서로를 대체하지 않는다.

**closure_condition**

```
PR merge
+ target build / runtime verification
+ 대시보드와 상세가 같은 server decision 을 표시하는 것을 실기기에서 확인
```

세 조건이 모두 충족되기 전에는 `platform_implementation_status` 를 올리지 않는다.

---

## 9-1. `OPEN_BLOCKERS`

| # | blocker | 영향 |
|---|---|---|
| B-1 | 양 플랫폼 `/kpi/presentation` 미소비 | 국가를 데이터로 켜도 모바일 미반영 |
| B-2 | 양 플랫폼 `kpi_status` 미소비 + 자체 판정 | 서버 G3 강제가 모바일에서 무력화 |
| B-3 | **→ P0-1 로 승격.** iOS FAIL-OPEN | (§9 참조) |
| B-4 | ~~Android `benchmark → severity` 변환~~ → **해소** `5ed3dd7` (§9-2) | — |
| B-5 | 3표면 모두 per-request 앱버전 헤더 없음 | `min_supported_version` 게이트 불가 |
| B-6 | 양 플랫폼 force-update 없음 | 구버전 차단 불가 (§5 순서 필요) |
| B-7 | 구버전 테스트 수단 없음 | rollout 안전성 검증 불가. `ANDROID_RELEASE_ARTIFACT_RETENTION`(§6-1) 이 선행 |
| B-8 | iOS distribute 경로 없음 → **`CI_EXTENSION_REQUIRED`**(§7) | iOS required 국가의 rollout prerequisite. 인프라 부재가 아니라 CI 확장 |
| B-9 | 3표면 모두 제품 계측 없음 | baseline 수집 불가 |
| **B-10** | `WEB_LOCAL_STATUS_FALLBACK` (§3-3) | DORMANT. 발동 시 한국 임계가 타국에 적용 |
| **B-11** | `SNAPSHOT_PIPELINE_CORRECTNESS` — **부분 해소 · 배포됨** `2e372b1` | 크래시는 고쳤으나 `psy`·`farrowing_rate` 는 산식 미확정으로 보류. `WRITER_OPERATIONAL` 까지만 인정 — §9-4 |
| **B-12** | ~~`ARQ_FALSE_SUCCESS_OBSERVABILITY`~~ → **해소 · 프로덕션 배포됨** `2e372b1` (2026-08-31) | §9-4 |
| **B-13** | `ALERT_DECISION_REPRODUCIBILITY` | 고객 대면 알림 468건에 threshold · authority · formula version 미저장 |
| **B-14** | `UNAUDITED_AUTHORITY_CONFIG_CHANGE` | `use_governance_benchmarks` 는 GLOBAL scope 인데 변경 기록이 남는 곳이 없다 |
| **B-15** | `CONSENT_FARM_AUTHORITY_403` — **API 계약 변경** | `POST /consent/record`·`/consent/withdraw` 가 접근 불가 `farm_id` 에 **403** 을 반환하기 시작했다(LEGAL-P0-CONSENT-FARM-AUTHORITY). 기존에는 무조건 성공. 웹은 `PROD_NOT_DEPLOYED` 상태로 대응 완료, **모바일 2개 저장소는 미대응** — 403 을 처리하지 않으면 동의 화면이 원인 불명으로 실패한다. 계약 변경이라 기능보다 위험(§CLAUDE.md 5) |
| **B-16** | `CONSENT_PERSISTENCE_5XX` | consent write 가 커밋되도록 고쳐지면서 (LEGAL-P0-CONSENT-LEDGER-PERSISTENCE), **커밋 실패 시 5xx** 가 나올 수 있다. 이전에는 실패해도 200 이었다. 성공 응답 스키마는 변화 없음. 모바일이 record 를 무조건 성공으로 가정하고 있다면 그 가정이 이제 틀리다 |

---

## 9-2. ★ 구현 evidence 등록 (2026-08-28 야간)

> `DONE` 은 implementation commit SHA 필수(§0-4). 2-phase 규율대로
> **구현 commit 이 먼저 만들어진 뒤 이 evidence 를 별도 commit 으로 기록**한다.
> 자기 commit SHA 를 같은 commit 에 기록하지 않는다.

### 9-2-1. 구현 commit

| 대상 | repo | commit | 내용 |
|---|---|---|---|
| Core | PigOS | `2e372b1` | ARQ false-success 제거 · snapshot supported-field contract |
| Core | PigOS | `c3a46cc` | client version 수신·관측 미들웨어 |
| CI | PigOS | `9da765c` | frontend unit test 스텝 신설 (그전엔 실행 0) |
| Web | PigOS | `fdd9ca5` | local threshold fallback → `insufficient` fail-closed |
| Web | PigOS | `c3a46cc` | platform/app version 헤더 송출 |
| Android | pigos-android | `5ed3dd7` | `kpi_status` 소비 · benchmark→severity 제거 · version 헤더 · APK 보관 |
| iOS | pigos-ios | `c516e2d` | `kpi_status` 소비 · `insufficient` FAIL-OPEN 제거 |
| iOS | pigos-ios | `8ecfdfe` | platform/app version 헤더 송출 |
| iOS | pigos-ios | `1d303bc` | unsigned archive validation job |
| iOS | pigos-ios | `4b07d3c` | severity default 기대값을 fail-closed 로 갱신 (CI 가 잡음) |

브랜치: 모바일 두 repo 는 `fix/kpi-status-consumption` (main 병합 안 함).

### 9-2-2. 셀 재판정

| 항목 | Core/Web | Android | iOS |
|---|---|---|---|
| `KPI_STATUS_CONSUMPTION` | **DONE** `fdd9ca5` | **DONE** `5ed3dd7` | **IN_PROGRESS** `c516e2d` — §9-2-3 |
| `LOCAL_SEVERITY_REMOVAL` | **DONE** `fdd9ca5` | **DONE** `5ed3dd7` | **IN_PROGRESS** `c516e2d` |
| `APP_VERSION_REQUEST_REPORTING` | **IN_PROGRESS** `c3a46cc` | **IN_PROGRESS** `5ed3dd7` | **IN_PROGRESS** `8ecfdfe` |
| `COUNTRY_KPI_PRESENTATION` | DONE(기존) | **BLOCKED** 변화 없음 | **BLOCKED** 변화 없음 |
| `FORCE_UPDATE / LEGACY_CONTROL` | BLOCKED | BLOCKED | BLOCKED |
| `PRODUCT_INSTRUMENTATION` | BLOCKED | BLOCKED | BLOCKED |

`APP_VERSION_REQUEST_REPORTING` 이 `DONE` 이 아닌 이유: 송출·관측까지만 했고
`min_supported_version` 게이트는 의도적으로 켜지 않았다(§12-1 순서). 계약 미완성이다.

### 9-2-3. ★ verification 상태 — 거짓 DONE 을 만들지 않는다

| 대상 | 검증 수단 | 결과 |
|---|---|---|
| Core | `pytest tests/unit` 721 passed · `ruff` clean | **VERIFIED** |
| Web | `tsc --noEmit` clean. vitest 실행 불가 → **CI 에 테스트 스텝 신설**(`9da765c`) | **PARTIAL** — 아래 |
| Android | `:app:compileDebugKotlin` + `:app:testDebugUnitTest` BUILD SUCCESSFUL (로컬 실행) | **VERIFIED** |
| iOS | 로컬 빌드 불가(Windows). CI `workflow_dispatch` macos-15 — run `33156495747` **success** (`build-test-lint` + `archive-validation` 둘 다) | **COMPILED_AND_UNIT_TESTED** / `runtime_verification_status = NOT_RUNTIME_VERIFIED` |

★ **Web 이 PARTIAL 인 이유 — 환경 blocker**

```
vitest 실행 불가
원인  Node v20.11.1 < 20.12.
      vitest → rolldown 이 node:util 의 styleText 를 import 하는데
      20.11 에는 없다 → SyntaxError: does not provide an export named 'styleText'
```

★ **ROOT_CAUSE_CORRECTED** (2026-08-31 최종)

```
최초 기록   "vitest 가 워커를 못 띄운다"                         ← 오진
1차 정정    "Node 20.11 < 20.12 라 node:util.styleText 가 없다"   ← 증상은 맞음
최종        unsupported local Node version was not enforced       ← 진짜 원인
```

  버전 pin 은 **이미 있었다** — `.nvmrc 22.11.0` · `engines >=22.11` · CI node 22.
  셋 다 **선언일 뿐 강제가 아니었다.** 그래서 Node 20.11 환경에서 npm 이 조용히 통과했고
  오진이 가능했다. `src/.npmrc` 에 `engine-strict=true` 를 넣어 `npm ci` 가 즉시
  실패하도록 고쳤다(`aeca20d`).

  → 같은 오진을 반복하지 않으려면 **"버전이 낮다" 가 아니라 "강제가 없다" 로 기억해야 한다.**

  ★ 더 큰 문제를 같이 찾았다 — **PigOS CI 의 frontend job 에 테스트 스텝이 아예 없었다.**
    `tsc --noEmit` + `npm run build` 뿐이었다. 즉 프론트 테스트는 로컬에서도
    CI 에서도 **어디서도 실행된 적이 없다.** CI 는 이미 Node 22 를 쓰므로
    스텝 한 줄을 추가했다(`9da765c`).

  → 이 머신 기준: `regression_test_status = PRESENT_BUT_NOT_EXECUTED`
    다음 CI run 부터는 실행된다.

★ iOS 는 CI 에서 컴파일·SwiftLint·단위테스트·unsigned archive 가 전부 통과했다.
  그래도 `NOT_RUNTIME_VERIFIED` 를 유지한다 — **시뮬레이터에서 실제 카드가
  무채색으로 그려지는지 눈으로 확인하지 않았다.** 거짓 DONE 을 만들지 않는다.

★ CI 가 잡아낸 것 하나 (가치 있는 실패):
  `APIErrorTests.testSeverityColorMapping` 이 `SeverityColor(severity: nil) == .ok`
  를 기대하고 있었다. **그 기대값 자체가 FAIL-OPEN 을 잠그고 있었다.**
  1차 run(`33155980980`)에서 이 테스트 하나만 실패했고, 그것이 정확히
  `c516e2d` 가 의도적으로 바꾼 동작이다 → `4b07d3c` 로 계약 갱신.

### 9-2-4. stale evidence 규율

evidence path 가 위 SHA 이후 변경되면 `DONE → PENDING_RECHECK` 후보다.
특히 `src/lib/kpi/statusObservation.ts` · `DashboardScreen.kt` ·
`DashboardScreen.swift` 세 파일은 판정 경로의 중심이라 변경 시 재확인이 필요하다.

---

## 9-3. ★ G4 완료 정의 — `COUNTRY_KPI_PRESENTATION` (2026-08-31 확정)

> G4 는 더 이상 "presentation endpoint 를 소비한다" 로 끝나는 작업이 아니다.
> **구버전 앱이 서버 정책을 다시 뚫지 못하게 하는 것**까지가 완료다.

```
G4 PASS 조건

Android
  [ ] /kpi/presentation 소비
  [ ] 서버 visible/hidden 준수          (프론트 필터 금지 — 서버가 이미 제외했다)
  [ ] order 준수                        (프론트 재정렬 금지)
  [ ] local card list 를 business logic source 로 사용 금지
       ※ 렌더 메타(단위·소수자리·라벨키)는 로컬 유지 가능
  [ ] benchmark null 정상처리           (비교만 사라지고 값은 남는다)

iOS
  [ ] 위와 동일 5항목

Old clients
  [ ] min_supported_version 미만에서 **신규 country presentation 비활성**
```

### 9-3-1. 왜 old-client 조항이 G4 안에 있는가

새 앱만 고쳐도 **이미 설치된 구버전은 계속 로컬 카드 목록으로 그린다.**
국가를 데이터로 켜는 순간 구버전은 서버가 숨기라고 한 KPI 를 그대로 보여준다.
즉 **presentation 정책이 구버전에서 무력화**되고, 이는 G4 를 안 한 것과 같다.

선행: `APP_VERSION_REQUEST_REPORTING` 이 세 surface 에서 송출·관측 확인까지 끝나야
`min_supported_version` 을 판단할 수 있다(§12-1 순서). **역순 활성화 금지.**

### 9-3-2. 현재 상태

```
Core/Web   DONE (기존)
Android    BLOCKED  — 소비 0건
iOS        BLOCKED  — 소비 0건
Old client BLOCKED  — version gate 미활성 (송출·관측 단계)
```

`docs/FEATURE_REGISTRY.md` `PIGOS-F-0001` 과 같은 대상이다.

### 9-3-3. ★ G4 구현 결과 — 2026-09-01 (append-only)

> 위 9-3-2 의 판정은 **당시 상태 그대로 둔다.** 아래는 그 뒤에 일어난 일이다.

```
Android   feat/kpi-presentation-consumption   wiselake/pigos-android#2
iOS       feat/kpi-presentation-consumption   wiselake/pigos-ios#2
base      각 저장소 fix/kpi-status-consumption (#1)  — stacked, main 아님
merge     0건   ·  main push 0건  ·  force-push 0건
```

**5항목 판정 (양 플랫폼 동일)**

| 항목 | 판정 | 근거 |
|---|---|---|
| `/kpi/presentation` 소비 | DONE | `KpiRepository.presentation()` |
| 서버 visible/hidden 준수 | DONE | visibility = `items` 멤버십. 로컬 목록이 카드를 만들지 않음 |
| order 준수 | DONE | `items` 배열 순서 그대로. `display_order` 재정렬 금지 테스트 |
| local list 를 business logic 로 미사용 | DONE | `RENDERABLE_KPI_ORDER`/`renderableKpiOrder` = 폴백 순서 + 렌더 가능 여부 |
| benchmark null 정상처리 | DONE(기존) | PR #1 에서 benchmark→severity 변환 제거. `benchmark alone yields no decision` |

```
implementation_status        DONE      Android 5640711 · iOS 0628de1
regression_test_status       PASS      Android 10건 · iOS 9건 (동일 케이스)
runtime_reproduction_status  NOT_RUNTIME_VERIFIED
                                       CI 빌드·테스트만. 실서버 응답으로 화면을 본 적 없음
```

★ **`DONE` 은 아직 이 표에 못 쓴다.** 세션 프로토콜 §5 상 `DONE` 은 implementation
commit SHA 를 요구하고 SHA 는 있으나, **두 SHA 모두 merge 되지 않은 stacked branch 위**에 있다.
main 에 없는 SHA 를 `DONE` 근거로 쓰면 그것이 곧 거짓 DONE 이다 →
셀 상태는 `IN_PROGRESS` 를 유지하고, merge 시점에 승격한다.

#### 9-3-4. ★ G4 로 닫지 못한 것 — `BLOCKED_BY_PRODUCT_DECISION`

**(1) `ACTIVE_SOWS` — "server hidden" 이 아니라 "server 무관"**

```
country_kpi_policy 에 ACTIVE_SOWS 코드 자체가 없다
  → 서버가 표시 여부에 의견을 낸 적이 없다
  → 엄격히 G4 를 적용하면 화면에서 사라진다 = 눈에 보이는 제품 변경
```

제거할지 사육두수 컨텍스트로 유지할지는 제품 결정이다. **현재 동작을 보존**하고
Android·iOS 코드에 주석으로 표시했다. 정책 KPI 로 편입할지도 함께 결정해야 한다.

**(2) 폴백 3종의 표시 정책 — 관측 granularity 가 플랫폼마다 다르다**

```
                       unavailable(요청 실패)   empty(200 + items=[])   no_renderable
Android · iOS          구분함                   구분함                  구분함
Web                    ─────── 합쳐짐 ───────                          구분함
```

Web `resolveKpiCards` 는 `!presentation || items.length === 0` 을 한 분기로 처리하고
telemetry 도 `absent_or_empty` 하나로 낸다 (`src/lib/kpi/presentation.ts`).
현행 web 테스트 `"404/timeout(null) · items 빈 배열 → 동일 폴백"` 이 이 합침을 이미 고정하고 있다.

**렌더 결과는 세 플랫폼 모두 같다** — 발산이 아니라 관측 해상도 차이다.
"서버가 의도적으로 비운 것"과 "서버 정책을 모르는 것"에 다른 화면을 줄지가
제품 결정이고, 그 전까지 모바일은 구분을 **데이터 모델에만** 남긴다
(결정 후 재작업 0). 현재 동작은 양 플랫폼 characterization test 로 고정했다.

**(3) old-client gate — 여전히 BLOCKED, 이번에 건드리지 않았다**

```
헤더 송출     Android ClientVersionInterceptor · iOS APIClient · Web client.ts   3/3 송출
서버          api/app/core/client_version.py                        observe-only (raise 없음)
min_supported_version                                                미정
gate 활성                                                            0건
```

메커니즘은 갖춰졌고 **막힌 것은 제품 결정 하나**다 — 어느 버전 미만을 끊을지,
끊었을 때 무엇을 보여줄지. 임계값을 코드가 정하면 그 순간 정책을 발명하는 것이므로
threshold 를 넣지 않았다. §9-3-1 의 역순 활성화 금지 규율 그대로다.

---

## 9-4. ★ 프로덕션 배포 기록 — `2e372b1` (2026-08-31)

```
배포 대상    api · worker 만          (web 제외 — 이 커밋에 frontend 변경 없음)
배포 SHA     2e372b1                  hotfix/arq-observability-20260831
직전 SHA     7c6dda7                  (서버 api/app 173파일 해시 대조로 실측)
migration    없음   ·  .env 변경 없음  ·  use_governance_benchmarks 변경 없음
롤백 자산    ~/pigos/api.bak-predeploy-20260831-095111
```

### 9-4-1. 배포 검증 — 비파괴만

> ★ 의도적으로 production failure 를 발생시키지 않았다.
>   순수함수 호출과 상태 조회로만 확인했다.

```
트리 일치       server api/app 174 파일 == 2e372b1   (diff 0 · git-only 0 · prod-only 0)
health          200 {"status":"ok","version":"0.1.0"}
web             미변경 (created 2026-08-26, 재빌드 대상 아님)
flag            use_governance_benchmarks = False    (불변)
worker          functions 7 · cron 6 등록됨
```

**ARQ 실패 semantics** (순수함수 · 프로덕션 데이터 무접촉)

```
전건 실패  expected=71 success=0  →  JobTotalFailure raise      ✓ 성공 문자열 반환 안 함
부분 실패  expected=10 success=7  →  "PARTIAL — 7/10, 3 errors" ✓
정상       expected=5  success=5  →  "OK — 5/5"                  ✓
except:pass 잔존                   →  0 (log.exception 로 대체)  ✓
```

**Snapshot supported-field contract**

```
persisted  active_sow_count · gestating_count · lactating_count
withheld   psy · farrowing_rate          ← 산식 미확정이라 영속 금지
```

### 9-4-2. ★ 배포 후에도 유지하는 관계

```
snapshot writer 작동   ≠   snapshot authority 승인   ≠   snapshot feature ready
```

```
kpi_snapshots 배포 직후   0행
reader                   0건 (KpiSnapshot 참조는 writer 와 model 뿐)  ✓ 전환 없음
인정 범위                 WRITER_OPERATIONAL 까지.
                         행이 생겨도 "스냅샷 기능 검증됨" 이 아니다.
```

### 9-4-3. 자연 발생 확인 일정 (강제 실행 안 함)

```
배포 시각                    2026-08-31 00:53 UTC
generate_tasks_job           05:30 UTC 당일 — 신규 코드 첫 자연 실행
generate_notifications_job   06:00 UTC 당일
daily/weekly/monthly KPI     2026-09-01 00:05~00:15 UTC = 09:05~09:15 KST
                             ← WRITER_OPERATIONAL 판정 시점
baseline                     kpi_snapshots=0 · notifications=577
```

### 9-4-4. ★ ARQ_HOTFIX_ACCEPTANCE

```
1. daily_kpi_aggregation 실제 실행 시작
2. farm-level success/error 집계
3. 최종 결과가
     전건 성공 → OK
     일부 실패 → PARTIAL + 실제 errors
     전건 실패 → exception
4. ★ ARQ queue/job 자체 상태도 위 결과와 일치
     전건 실패인데 j_failed=0 이 다시 나오면 FAIL
5. traceback / error log 가 실제 실패 원인을 보존
```

#### ★ 4번은 자연 실행으로 관측되지 않는다 — 별도로 닫았다

```
수정 후 daily_kpi_aggregation 은 성공한다 (크래시 원인이 제거됐으므로).
→ 자연 실행은 OK 만 내고 실패 경로를 밟지 않는다.
→ 확인하려고 프로덕션에 의도적 실패를 만드는 것은 금지.
```

그래서 **로컬 burst worker + 로컬 redis** 로 닫았다. 프로덕션 무접촉.

```
api/tests/integration/test_arq_failure_propagation.py   (60fc542)

전건 실패   jobs_failed=1 · jobs_complete=0 · arq 가 traceback 전문 기록
정상        jobs_complete=1 · jobs_failed=0
부분 실패   jobs_complete=1 (잡 자체는 실패 아님) + 결과에 PARTIAL/errors
```

```
ACCEPTANCE_4 = CLOSED_BY_LOCAL_VERIFICATION   (프로덕션 자연 실행 대상 아님)
```

★ **정정** — 앞서 "전건 실패 시 `max_tries=5` 로 5회 재시도" 라고 기술했으나 **틀렸다.**
`arq/worker.py:612-634` 실측: `Retry` / `CancelledError` / `RetryJob` 만 재시도이고
일반 예외는 `logger.exception` + `finish=True` + `jobs_failed` 로 **즉시 종료**한다.
`max_tries` 는 `Retry` 유발 재시도만 제한한다.
→ 결과적으로 더 낫다. 매일 실패하는 cron 이 재시도 폭주를 일으키지 않는다.

### 9-4-5. ★ SNAPSHOT_WRITER_ACCEPTANCE

> 행 수가 아니라 **내용의 shape** 를 본다. `kpi_snapshots > 0` 만 보고 PASS 를 주지 않는다.

```
[ ] job crash 없음
[ ] 예상 farm scope 에 대해서만 row 생성        (활성 농장 71 기준)
[ ] persisted 대상 = 지원되는 counts 3종만
      active_sow_count · gestating_count · lactating_count
[ ] psy / farrowing_rate emitted 0
[ ] reader 0 유지
[ ] use_governance_benchmarks = False 유지
```

### 9-4-6. ★ 4축 판정 — 하나의 PASS 로 합치지 않는다

```
ARQ_HOTFIX          PASS | FAIL
SNAPSHOT_WRITER     OPERATIONAL | NOT_OPERATIONAL
SNAPSHOT_AUTHORITY  NOT_ENABLED        ← 고정. 이번 배포로 바뀌지 않는다
SNAPSHOT_FEATURE    NOT_READY          ← 고정. 이번 배포로 바뀌지 않는다
```

현재값 (2026-08-31 배포 직후):

```
ARQ_HOTFIX          코드 검증 PASS / 자연 실행 검증 대기
                    → 상태: DEPLOYED / AWAITING_NATURAL_RUN_ACCEPTANCE
SNAPSHOT_WRITER     NOT_OPERATIONAL    (kpi_snapshots 0행. 첫 실행 전)
SNAPSHOT_AUTHORITY  NOT_ENABLED
SNAPSHOT_FEATURE    NOT_READY
```

★ 9/1 자연 실행이 통과하면 그때 처음으로
`ARQ observability incident = CLOSED` 라고 닫을 수 있다. 지금은 아니다.

---

### 9-4-7. ★ Natural Run Acceptance Result — 2026-09-01

> §9-4-4/9-4-5 는 **기준**이고 이 절은 **결과**다. 기준은 수정하지 않고 결과만 append 한다.
> §9-4-6 의 "현재값" 은 2026-08-31 배포 직후 시점 기록이며, 이 절이 그 이후 상태다.

```
실행 구분    production natural schedule / 비강제 실행
대상 배포    2e372b1  (api + worker)
검증 시각    2026-09-01 00:05~00:52 UTC  =  09:05~09:52 KST
```

#### ARQ

자연 스케줄 실행 결과:

```
daily_kpi_aggregation     OK — 73/73 processed  period=2026-08-30
weekly_kpi_aggregation    OK — 73/73 processed  period=2026-08-24~2026-08-30
monthly_kpi_aggregation   OK — 73/73 processed  period=2026-07-01~2026-07-31
generate_tasks_job        OK — 73/73 processed, 1 created
generate_notifications    OK — 73/73 processed, 2 created, 0 pushed

ARQ success marker ●      5
ARQ failure marker !      0
traceback                 0
```

★ `expected` 는 **73** 이다. 기준 작성 시점의 71 에서 활성 농장이 2 증가했다.
  73/73 이므로 전건 처리다.

ARQ health refresh (`arq:queue:health-check`):

```
Aug-31 23:52:29   j_complete=3  j_failed=0  j_retried=0  j_ongoing=0  queued=0   ← 실행 이전
Sep-01 00:52:29   j_complete=6  j_failed=0  j_retried=0  j_ongoing=0  queued=0   ← 실행 이후
```

`j_complete` 3 → 6 (+3 = daily·weekly·monthly). **로그의 성공 결과와 queue/job-level
상태가 일치했다.** 원래 사고였던 "전건 실패인데 `j_failed=0`" 의 반대 상황이며 정합이다.

> health key 는 arq 가 **1시간 주기로만** 갱신한다. 실행 직후 조회하면 이전 값이 보인다.
> 이번에도 00:39 UTC 조회 시 `Aug-31 23:52` 가 나와 00:52 갱신을 기다려 확인했다.

#### 판정 — ARQ

```
ARQ_HOTFIX = PASS_ON_SUCCESS_PATH / FAILURE_PATH_LOCALLY_VERIFIED
```

이번 자연 실행에서는 **실패가 발생하지 않았으므로 production 에서 failure propagation
자체를 관측하지 않았다.** 전건 실패의 ARQ failure propagation 은 로컬 검증
`60fc542`(`test_arq_failure_propagation.py`)에서 확인됐다.

**따라서 아직 `CLOSED` 로 승격하지 않는다.**

향후 자연 실패 발생 시 아래를 **모두** 만족하면 `CLOSED` 후보로 전환한다.

```
[ ] 실제 task exception 발생
[ ] ARQ job status = FAILED
[ ] j_failed 증가
[ ] traceback 보존
[ ] false-success 없음
```

#### Snapshot Writer

자연 실행 후:

```
total rows   219
farms         73
DAILY         73
WEEKLY        73
MONTHLY       73
calculated_at 2026-09-01 09:05:00 ~ 09:15:01 KST
```

농장 timezone 에 따라 completed period 가 정상적으로 분리됐다:

```
DAILY     2026-08-30  12농장   ·  2026-08-31  61농장
MONTHLY   2026-07-01  12농장   ·  2026-08-01  61농장
WEEKLY    2026-08-24~08-30     73농장
```

Shape 검증:

```
psy_written        0            ← 산식 미확정. _WITHHELD_FIELDS 작동
farrowing_rate     column not present

active_sow_count   219
gestating_count    219
lactating_count    219

msy / npd / mortality_rate / fcr / avg_daily_gain   0
```

**산식 미확정 필드인 `psy` · `farrowing_rate` 가 snapshot 에 유입되지 않았다.**
특히 `psy` 는 컬럼이 존재하는데도 0건이므로, 컬럼 부재가 아니라 **보류 규칙이 실제로
동작한 결과**다.

#### 판정 — Snapshot

```
SNAPSHOT_WRITER     = OPERATIONAL
SNAPSHOT_AUTHORITY  = NOT_ENABLED
SNAPSHOT_FEATURE    = NOT_READY
```

`WRITER_OPERATIONAL` 은 authority 승인 또는 snapshot feature readiness 를 의미하지 않는다.

#### Authority invariants

배포 후 불변조건 유지 확인:

```
use_governance_benchmarks   False
KpiSnapshot readers         0            (writer·model 제외 시 참조 0)
Alembic head                f3c6a8d0b2e4
authority switch            not enabled  (컨테이너 env 에 키 없음)

DMV                         87
operational_defaults        29
rule_configs                0
DMV last update             2026-07-08
```

#### Final Acceptance

```
ARQ_HOTFIX          PASS_ON_SUCCESS_PATH / FAILURE_PATH_LOCALLY_VERIFIED
SNAPSHOT_WRITER     OPERATIONAL
SNAPSHOT_AUTHORITY  NOT_ENABLED
SNAPSHOT_FEATURE    NOT_READY
```

Snapshot-dependent features — **What Changed · snapshot-first Home ·
historical comparison — remain `NOT_READY`.**

#### 부수 관측

`generate_notifications_job` 이 `73/73, 2 created` 로 정상 동작했고 `notifications`
577 → 579. **`create_from_alerts` 의 KPI 블록에서 `log.exception` 이 찍히지 않았다** —
즉 KPI 알림 유실이 실제로 없었다. 배포 전에는 이 사실을 알 방법 자체가 없었다(§A1-4).

★ **writer 가 실제로 정상 작동하기 시작한 날 = 2026-09-01.**
  그 전 2026-05-29~2026-08-31 구간의 `kpi_snapshots` 는 0행이며 그 사실은 바뀌지 않는다.

---

### 9-4-8. ★ Snapshot 안전규칙 — forward-only

```
snapshot_epoch        = 2026-09-01
historical_backfill   = BLOCKED_BY_DEFAULT
```

**2026-05-29 ~ 2026-08-31 구간의 `kpi_snapshots` 공백을 현재 코드로 재계산해 메우지 않는다.**

그 구간을 지금 산식으로 채우면 당시의 `formula` · `as_of` · `authority` 를 재현하지 못한
**가짜 과거 snapshot** 이 된다. D-19 `V-3 = NOT_REPRODUCIBLE` 이 그 재현 불가를 이미 실측했고,
notification 468건 backfill 을 금지한 것과 같은 이유다.

해제 조건: **별도의 재현성 증명이 생긴 뒤**에만. 그 전까지 forward-only 가 안전하다.

---

## 9-6. `ARQ_OBSERVABILITY` — 인시던트 상태

```
remediation          DEPLOYED                      2e372b1 (2026-08-31)
success_path         PROD_VERIFIED                 §9-4-7
failure_path         LOCAL_VERIFIED                60fc542
prod_failure_path    AWAITING_NATURAL_OBSERVATION
incident_status      MONITORING
```

`CLOSED` 는 §9-4-7 의 5개 조건이 **자연 실패에서** 충족될 때만 올린다.
**일부러 실패를 만들지 않는다.**

---

## 9-5. P1 — `DEPLOY_PROVENANCE` (신규 등록)

### 문제

`2e372b1` 배포 시 프로덕션 SHA 를 알아내려고 **서버 api/app 173개 파일 전수 해시 대조**를
해야 했다. scp 배포라 서버에 git 이 없고, 이미지 라벨에도 revision 이 없다.

이번엔 정확히 특정했지만 **반복할 방식이 아니다.**

### 개선 방향 (이번 hotfix 에 섞지 않는다)

```
image label
  org.opencontainers.image.revision=<sha>

또는 health 응답
  {"status":"ok","version":"0.1.0","revision":"<sha>"}
```

그러면 앞으로:

```
"What is production?"  →  health / image inspect  →  SHA 즉시 확정
```

```
platform_implementation_status = PLANNED
priority = P1
★ 이번 hotfix 에 다시 섞어 넣지 않는다. 별도 deploy-provenance 개선으로 둔다.
```

---

## 9-7. ★ `PUBLICATION_GATE_451` — API 계약 변경 (2026-09-10 등재)

`G-3`(`320baea`)가 **가입 진입점 두 곳의 응답 계약을 바꾼다.** 아직 배포 전이다.

```
POST /api/v1/auth/register          미승인 문서 상태 → 451 "PUBLICATION_NOT_APPROVED"
POST /api/v1/onboarding/complete    〃
POST /api/v1/consent/record         〃 (심층 방어)
```

★ **기능 추가가 아니라 계약 변경이다.** `CLAUDE.md` §5 — 모바일은 독립 저장소
2개이고 배포 주기가 길어 구버전이 오래 남으므로, 계약 변경이 기능보다 위험하다.

| | `platform_implementation_status` | 근거 |
|---|---|---|
| Core/Web | `DONE` | `320baea` 게이트 · `f0934c0` 8 로케일 안내 문구 + 테스트 2건 |
| **Android** | **`DONE`** | pigos-android `b88c571` — 451 → `consent_blocked_title`(8 로케일 기존 문구) · 미지 사유코드 회귀 테스트 4건 · 이 머신에서 재실행 4/4 + OnboardingConsentTest 9/9 — §9-7-2 |
| **iOS** | **`PENDING_RECHECK`** | pigos-ios `608b418` — 사유코드 뱃지 `#if DEBUG` 뒤로 · 미지 코드 테스트. ★ **컴파일 미검증** — 이 PC 에 Xcode 없음. Mac 또는 CI(macos-15) 빌드 후 `DONE` — §9-7-2 |

### 9-7-1. 실측 (2026-09-10 · 두 저장소 read-only)

**가입 경로가 플랫폼마다 다르다.** 둘 다 게이트에 걸린다.

```
Android   POST /onboarding/complete          OnboardingApi.kt:15
          ★ 주석: "POST /auth/register 는 서버 500 이라 미사용"
iOS       POST /auth/register → /onboarding/farm   AuthService.swift:50
          ★ /onboarding/farm 은 게이트 대상이 아니므로 register 에서 막힌다
```

#### iOS — 사유는 보이나 번역은 없다

```
APIClient.swift:126        errorBody 의 detail 을 디코드한다
APIError.swift:18-29       451 은 case 없음 → default: .http(status:detail:)
APIError.swift:42-44       "Error occurred (451: PUBLICATION_NOT_APPROVED)."
```

★ **크래시하지 않고 묵살하지도 않는다.** 웹이 어제까지 하던 것과 같은 수준 —
사용자에게 영문 코드가 보인다. `f0934c0` 로 웹은 8 로케일 안내를 붙였으나
iOS 는 그 문구를 모른다.

#### Android — ★ 사유가 사라진다

```
OnboardingRepository.kt:32   runCatching { onboardingApi.complete(...) }
                             Response<T> 가 아니라 DTO 를 직접 받는다
                             → Retrofit 이 비 2xx 에 HttpException 을 던진다
errorBody 를 읽는 코드        저장소 전체 0건
```

**서버가 보낸 `PUBLICATION_NOT_APPROVED` 가 어디에도 도달하지 않는다.**
사용자는 "HTTP 451" 수준의 일반 오류만 본다 — 왜 막혔는지, 언제 열리는지,
자기 잘못인지 알 방법이 없다.

★ 기존 `SIGNUP_BLOCKED:{reason}` 451 도 **같은 이유로 이미 사유가 사라지고
있었다.** 이 게이트가 만든 문제가 아니라, 이 게이트가 **드러낸** 문제다.

#### 부수 관측 — Android 기본 국가가 KR 이다

```
OnboardingRepository.kt:26   country: String = "KR"
```

KR 은 `signup_blocked`(KR_REFERENCE_ONLY) 다. 호출부가 국가를 넘기지 않으면
게시 게이트 이전에 국가 게이트에 걸린다. **이 배포와 무관한 선존 항목**이나,
451 을 만나는 경로가 하나 더 있다는 뜻이므로 함께 기록한다.

#### ★ 2026-09-11 추가 실측 — 서버는 완비, 막힌 건 클라이언트 둘 다

```
서버      consent_service.py:186,194 · eligibility.py:109,143  사유코드 전부 내려보냄
Android   errorBody() 프로덕션 경로 0건 (test/BackendIntegrationTest.kt:99 에만)
iOS       OnboardingViewModel.swift:60  reasonCode ?? "SIGNUP_BLOCKED" 원시 노출
          ★ 451 본문이 아니라 GET signup-plan 의 gate.reasonCode 경로
양쪽      LAUNCH_NOT_ENABLED 문자열 0건 — H13 (4) 가 만든 새 사유코드를 모른다
```

iOS 상태를 `IN_PROGRESS` 에서 **`BLOCKED`** 로 내린다. "사유가 보인다"는 판정은
451 본문 기준이었고, 실제 표시 경로는 plan 의 reasonCode 를 원시 상수로 내는
것이라 사용자에게 보이는 것은 `LAUNCH_NOT_ENABLED` 라는 영문 상수다.

#### 배포 전 판단 (2026-09-10 시점 — §9-7-2 로 대체됨)

```
iOS       배포 가능. 영문 코드 노출은 기존 451 과 동일 수준
          → 후속으로 안내 문구 (별건)
Android   ★ errorBody 를 읽어 detail 을 표면화하는 수정이 선행되어야 한다
          없으면 미국 외 가입 시도가 전부 원인 불명 오류가 된다
          ★ 서버 로그는 451 정상 응답으로 보이므로 장애로 인지되지 않는다
```

### 9-7-2. ★ 2026-09-11 T3 완료 — 그리고 §9-7-1 의 전제 세 개가 틀렸다

다른 세션이 두 저장소를 고쳤고, 이 세션이 machine `bjh` 에서 디스크로 재검증했다.

```
pigos-android  b88c571  fix(onboarding): show a 451 as a regional block
               OnboardingViewModel.kt fail():  HttpException && code()==451
                 → errorRes = R.string.consent_blocked_title (else vm_process_failed)
               OnboardingBlockedReasonTest.kt  4건 신규
               ★ 재실행(이 머신, JDK openjdk-21.0.1, --offline):
                 OnboardingBlockedReasonTest 4/0/0 · OnboardingConsentTest 9/0/0
                 (다른 세션 보고: 전체 112 suites · 427 tests · 0 fail — 미재확인)

pigos-ios      608b418  fix(onboarding): keep the block reason code out of the production screen
               OnboardingScreen.swift:142-  조건을 `!= nil` 로, 코드 뱃지는 #if DEBUG 안으로
               OnboardingViewModel.swift:57  docstring "그대로 노출한다" → "제품 화면에 쓰지 않는다"
               ConsentTests.swift  testUnknownReasonCodeStillBlocks (LAUNCH_NOT_ENABLED · 미지 코드 · 코드 없음)
               ★ 컴파일 0회 — 이 PC 에 Xcode 없음
```

**§9-7-1 이 틀린 곳 세 군데** (다른 세션 지적 → 이 세션 디스크 확인):

```
① "Android 사용자는 HTTP 451 만 본다"
   틀림. 정상 경로는 plan 단계다 — GET signup-plan 의 signup_blocked 가 true 면
   ConsentSection.kt:104 BlockedCard 가 뜨고 canSubmitStep(VM:74) 이 false 라
   /onboarding/complete 는 호출조차 안 된다.
   consent_blocked_title/desc 는 이미 values + 7 로케일 = 8 개에 있다
     ko "해당 지역은 서비스 준비 중입니다" / en "Service not available in your region"
   451 에러 경로에 닿는 것은 plan 을 받은 뒤 서버 게이트가 바뀐 레이스뿐이다.
   → 심각도 낮음. 그래도 b88c571 이 그 경로를 같은 문구로 닫았다

② "클라이언트 게이트를 우회할 수 있다"
   틀림. canSubmitStep = consentPlan != null && consentCanSubmit — plan 조회
   실패도 통과시키지 않는다. OnboardingConsentTest:133
   `plan load failure blocks signup entirely` 가 이미 그것을 고정한다

③ "iOS 가 원시 상수를 화면에 띄운다"
   절반. OnboardingScreen.swift:150 "Sign-up isn't available in the country you
   selected." 문장이 먼저 나오고, 그 아래 mono 뱃지로 코드가 하나 더 붙었다.
   `?? "SIGNUP_BLOCKED"` 폴백도 뱃지에만 들어간다. 608b418 이 뱃지를 DEBUG 로 옮겼다
```

**이 세션이 §9-7-1 을 쓸 때 놓친 이유**: 에러 경로(451 본문·errorBody)만 읽고
정상 경로(plan 단계의 `signup_blocked`)를 안 읽었다. "찾지 못한 것과 없는 것은
다르다" — errorBody 0건은 맞았으나, 그것이 "사용자가 아무것도 못 본다"를 뜻하지
않았다.

**사유코드 → 문구 테이블은 만들지 않았다 — 의도적**:

```
KR_REFERENCE_ONLY  → "한국은 참조용 지역"
HOLD_D07           → "중국은 진입 보류"
LAUNCH_NOT_ENABLED → "아직 개시하지 않은 국가"
```

이 세 문장은 D-13 · Q-B 로 변호사에게 묻고 있는 성격 규정 그 자체다. 답이 오기
전에 8 개 언어 제품 문구로 박는 것은 승인 전 정책을 코드에 반영하는 것이다.
그리고 문구가 두 벌(plan 단계 + 451 경로)이면 한쪽만 갱신된다 — 이번 주 디스크
불일치 4건과 같은 구조다. **중립 문구 한 벌**(`consent_blocked_*`)을 양쪽 경로가
공유한다. MOBILE_BACKLOG M-1 의 "4항목 테이블"은 철회.

**다른 세션 보고에서 이 세션이 정정하는 것 한 가지**:

```
보고   ".xcodeproj/.pbxproj 가 없다 → 이 저장소는 현재 상태로 빌드가 안 된다"
디스크 README.md:36  ".xcodeproj 는 커밋하지 않고 XcodeGen 으로 project.yml 에서 생성"
       CI ci.yml(macos-15)  xcodegen generate → xcodebuild test   (§? XcodeGen AVAILABLE)
→ 빌드 안 되는 게 아니라 이 PC 에서 안 되는 것이다. Mac 이나 CI 면 된다
```

`#if DEBUG` 가 정의돼 있는지는 project.yml · xcconfig 에 명시가 없어 디스크로
확정 못 한다. 다만 `AppConfig.swift:19,50` 이 이미 같은 `#if DEBUG` 로 Base URL 을
가르고 있으므로, 정의가 안 돼 있었다면 Release 의 API 주소부터 틀렸을 것이다
(XcodeGen 은 Debug 구성에 `DEBUG` 를 기본 주입). 선례 근거이지 측정은 아니다.

**iOS 는 1.0 영어 단독**(project.yml:50-53, `CFBundleLocalizations: [en]`).
"8 로케일 안내"는 웹·Android 얘기이고 iOS 는 영문 한 문장이다 — T3 와 무관한
선존 상태(RELEASE_APPSTORE §4-1).

#### 배포 전 판단 (2026-09-11 갱신)

```
Android   b88c571 로 451 경로도 닫힘. 배포 선행조건 해소
iOS       608b418 은 Mac/CI 빌드 1회가 남는다. 다만 배포를 막지는 않는다 —
          변경 전에도 문장은 나왔고, 남은 것은 뱃지 하나였다
          ★ push 금지 중이라 CI 로 검증할 수 없다. 해제 후 첫 push 에서 확인
```

### 9-7-3. ★ iOS Debug 빌드가 프로덕션을 가리킨다 (2026-09-11 · 다른 세션 발견 · 이 세션 디스크 확인)

T3 의 남은 검증이 "Mac 에서 빌드해 온보딩 화면 확인"인데, 그 빌드가 `api.pigos.io`
를 친다. 서 있는 규칙(프로덕션 쓰기 금지 · 신규 가입 실제 enable 금지)과 정면 충돌.

```
Config/Debug.xcconfig:3-4     PIGOS_API_SCHEME = https / PIGOS_API_HOST = api.pigos.io
Config/Release.xcconfig:2-3   동일
git log --follow             6a725c2  http / localhost:8000 으로 신설 (컴파일 미검증)
                             34130df  "Android parity + QA fixes — production-ready"
                                      → https / api.pigos.io  ("Connect to production API")
                                      2026-08-25, author wiselake
```

**주석·문서 7곳은 하나도 안 따라갔다** — 전부 "Debug=localhost(http)" 라고 적혀 있다:

```
Config/Debug.xcconfig:1,5      "시뮬레이터/로컬 백엔드" · "로컬 평문(HTTP) 허용 — Debug 전용"
project.yml:31                 "Debug=localhost(http), Release=api.pigos.io(https)"
AppConfig.swift:14,25          같은 내용 2곳
docs/MAC_VERIFY_CHECKLIST.md:36  체크박스 "Debug baseURL = http://localhost:8000" — 지금 돌리면 실패
docs/PROGRESS.md:21            "§1 Base URL 환경분리 ✅"
CLAUDE.md:30                   "Debug=localhost:8000"
```

`PIGOS_ALLOWS_LOCAL_NETWORKING = YES` 는 https 프로덕션 호스트와 같이 남아 의미가
없고, 게다가 **어디에도 배선돼 있지 않다** (project.yml·swift·plist 0건 — project.yml:73
"ATS 예외 없음"). 값만 있고 읽는 곳이 없다.

**CI 는 안전하다** — 확인함:

```
ci.yml:61   xcodebuild test  -configuration 없음 → Debug
PigOSTests  APIClientTests:59 · SyncServiceTests:63  baseURL http://localhost + StubURLProtocol
            LivePayloadDecodingTests:124  https://example.invalid (저장 픽스처)
→ 단위 테스트는 AppConfig.baseURL 을 쓰지 않는다. CI 가 api.pigos.io 를 치지 않는다
```

**수동 확인의 안전한 경로는 이미 코드에 있다**: `AppConfig.swift:19` — Debug 빌드는
launch env `PIGOS_API_BASE_URL` 로 호스트를 덮어쓴다. Mac 에서 온보딩 화면을
확인할 때 이 env 를 로컬(또는 스테이징)로 주면 34130df 를 되돌리지 않고도
프로덕션 가입 시도 없이 검증된다. **MAC_VERIFY_CHECKLIST 에 그 env 를 필수로
적어야 한다** — 지금은 안 적혀 있어 정직하게 따르면 프로덕션을 친다.

**`#if DEBUG` 는 확정** — 선례가 아니라 이미 의존 중인 동작이다:

```
AppConfig.swift:18-19   "Release 빌드에서는 오버라이드 자체를 컴파일하지 않는다"
                        #if DEBUG 안에서만 PIGOS_API_BASE_URL 을 읽는다
AppConfig.swift:50      PIGOS_USE_MOCK_DATA 판정도 같은 조건
```

Release 에서 DEBUG 가 참이면 출시 바이너리가 환경변수로 API 호스트를 바꿀 수 있다는
뜻이다. 608b418 의 뱃지는 그 조건 위에 얹힌 것이라 같이 안전하다.

**고치지 않았다 — 결정 사항**: 34130df 가 무엇을 위해 바꿨는지(시뮬레이터에서
프로덕션 QA?) 기록이 없다. 되돌리면 그 용도가 깨진다. 두 갈래:

```
(가) 34130df 되돌림  Debug = http/localhost:8000  — 문서 7곳이 다시 맞고, 로컬 QA 는
                     PIGOS_API_BASE_URL 로 프로덕션을 가리키면 된다 (역방향 override)
(나) 문서 7곳을 현실에 맞춤  Debug = 프로덕션. MAC_VERIFY_CHECKLIST 에 env 필수 명기
```

→ `HUMAN_INPUT_QUEUE` §6 B-5. 어느 쪽이든 **MAC_VERIFY_CHECKLIST 의 env 명기는 공통**.

**두 세션 합의 권고 = (가). 근거는 "문서가 맞는다"가 아니라 잊었을 때의 실패 방향이다:**

```
env 오버라이드는 #if DEBUG 안에서 양방향 다 된다 (AppConfig.swift:19)
  Debug=localhost 에서 prod 를 가리키는 것도, 그 반대도 같은 한 줄
  → "어느 쪽이 편한가"로는 안 갈린다

(가) env 를 잊음 → localhost 를 친다 → 연결 실패. 즉시 눈에 보인다
(나) env 를 잊음 → api.pigos.io 를 친다 → 조용히 성공. 프로덕션에 계정이 하나 생긴다
```

프로덕션 쓰기 금지 규칙이 "매번 env 를 기억하기"에 걸려 있으면 안 된다. 기본값은
잊었을 때 무해한 쪽으로 실패해야 한다.

34130df 의 의도는 제목에 있다("Connect to production API"). 제목이 답하지 않는 것은
**왜 Release 가 아니라 Debug 를 바꿨는가** — Release 로도 프로덕션 QA 는 된다.
Brian 에게 확인할 한 줄은 그것이다.

이 드리프트는 **17일**(08-25 → 09-11) 조용했다. xcconfig 한 줄이 바뀌었는데 아무
테스트도 안 깨졌기 때문이다. B-5 확정 후 `AppConfig.baseURL` 의 Debug 기대값을
단위 테스트로 고정하면, 다음에 호스트를 바꾸는 사람은 결정을 기록하지 않고는
초록을 유지할 수 없다 — H13 의 strict xfail 과 같은 장치. (pigos-ios 쪽 작업,
다른 세션 담당.)

B-5 와 무관하게 지금 가능한 것: `MAC_VERIFY_CHECKLIST.md:36` 한 줄. (가)든 (나)든
지금 틀렸고, 정직하게 따르는 사람이 프로덕션 가입을 시도하게 만드는 바로 그 줄이다.

### 배포 전 확인할 것

```
1  모바일 2종이 451 응답을 어떻게 처리하는가
   - 사유 문자열을 그대로 보여주는가 (웹의 기존 동작)
   - 알 수 없는 코드를 일반 오류로 뭉개는가
   - 크래시하는가
2  US 외 법역에서 가입 시도 시 사용자가 무엇을 보는가
   웹 8 로케일 안내 · Android consent_blocked_* 8 로케일 · iOS 영문 한 문장 (§9-7-2)
3  구버전 앱이 451 을 재시도 루프로 처리하지 않는가
```

★ 이 확인 없이 배포하면 **모바일 신규 가입이 원인 불명 오류로 실패**한다.
서버는 의도대로 동작하므로 로그에는 정상으로 보인다.

관련: `docs/legal/DEPLOY_GATE_20260910.md` · `docs/legal/LEGAL_P0_FREEZE_20260910.md`

---

## 9-8. `CONSENT_DIFF` — API 계약 추가 (2026-09-11 등재)

```
GET /api/v1/consent/diff?farm_id=     인증 필요. 목적별 (required_version, recorded_version)
```

`LEGAL_P0_MANDATORY_CONSENT_LOGIN_GATE.md` 구현 메모의 계약 세 줄이 코드다:

```
1  국가는 서버가 정한다 — organization.country 와 farm.country 를 가입 경로와 **같은**
   jurisdiction.resolve() 에 태운다. 폴백 규칙 없음(FARM 우선/ORG 우선 같은 것을 두면
   같은 계정에 법역 답이 둘 — D-16 두 맵과 같은 모양). 동치 테스트로 고정.
   쿼리로 국가를 보내도 무시. 다국가 조직은 farm_id 를 바꿔 가며 부른다 — (user, farm) 한 쌍
2  판정 필드 없음 — 계정 단위 불리언을 만들지 않는다. 목적별 두 사실만 나란히
3  "동의한 적 없음"(None) 과 "철회함"(WITHDRAWN) 이 구분된다
```

★ **이 엔드포인트는 버전 동일성만 답한다.** 동의의 충분성(증적 방식·주별 요건)은 답하지
않으며, **버전이 일치해도 재동의가 필요할 수 있다** — 네브래스카 농장은 notice_version 이
같아도 WRITTEN_OPT_IN 증적이 없으면 부족하다. 판정 층을 얹는 사람이 "diff 통과 = 됐다"로
읽지 않게 하려는 문장이다.

★ 이것은 **판정을 하지 않는다.** 어느 전이가 재동의인가(H16)·어느 모드로 막는가(H11)는
결정 뒤에 이 위에 얹는다. 로그인 경로에는 여전히 동의 판정이 없다 — 그 문서의
`OPEN — NOT REMEDIATED` 는 그대로다. 이 계약은 그 판정이 읽을 **입력**이다.

US 주(state)는 저장돼 있지 않아 farm_state=None 으로 판정한다 — 주별 ui_kind 는 여기서 보이지 않는다.

| | `platform_implementation_status` | 근거 |
|---|---|---|
| Core | `DONE` | `consent_service.consent_diff` · 라우터 `/consent/diff` · 테스트 9건 (`test_consent_diff.py`, resolve 동치 포함) |
| Web | `DONE` | `AmendmentBanner` · `/settings/data` 가 `/consent/diff` 하나를 읽는다 (같은 커밋). 예전에는 `farms.list → signupPlan(farm.country)` + `current` 를 클라이언트에서 합쳐 비교했다 — 법역을 정하는 곳이 둘. 목적별 필요/기록 버전을 나란히 표시, 판정 없음. 필요 버전이 초안이면 배너 억제(초안에는 재동의 불가, G-3). 8 로케일 `consent.diff.*` 4키. 테스트 15건 |
| Android | `PLANNED` | 소비 0건. `ConsentAmendmentViewModel` 이 있으나 이 계약을 모른다 |
| iOS | `PLANNED` | 소비 0건 |

## 9-9. `SIGNUP_RATE_LIMIT_429` — API 계약 추가 (2026-09-16 등재)

```
POST /api/v1/auth/register          한도 초과 → 429 detail="RATE_LIMITED:signup"  header Retry-After
POST /api/v1/onboarding/complete    〃 (같은 버킷)
POST /api/v1/auth/login · password-reset/{request,confirm}   → "RATE_LIMITED:auth"
```

기본값·근거: `docs/runs/RATE_LIMIT_POLICY.md`. 값은 settings(env)에서 오고 0 이하면 비활성.

★ **기존 계약과 같은 모양**을 썼다 — `detail` 에 `TOKEN:{bucket}` 문자열. 모바일 두
클라이언트가 이미 `SIGNUP_BLOCKED:{reason}` 을 그 형태로 다룬다(§9-7-2). 새 status·새
포맷을 발명하지 않았다.

| | `platform_implementation_status` | 근거 |
|---|---|---|
| Core | `DONE` | `app/core/rate_limit.py` · 라우터 5곳 · 테스트 11건 (`test_rate_limit.py`) |
| Web | `DONE` | PigOS `8b7077c` (safety/pigos-20260916) — `src/lib/api/errors.ts` `rateLimited` + `parseRetryAfter` · onboarding/login/forgot-password 3화면 · 8 locale `errors.rateLimitedRetryIn` · vitest +21 (`apiErrors.test.ts` +9, `pages/rate-limit-429.test.tsx` 12) |
| Android | `DONE` | pigos-android `0e1d450` (fix/rate-limit-429) — `data/remote/RateLimited.kt` · Login/Onboarding VM + 화면 · 8 locale `rate_limited(_retry_in)` · unit 446/0 로컬 · **CI run 35555598654 green** (`746d0af` = 0e1d450 + setup-android v4 수정, Draft PR #6; 446 tests·0 failures 실측) — `docs/runs/ANDROID_CI_429_PARITY_20260921.md` |
| iOS | `DONE` | pigos-ios `7210e1c` (fix/rate-limit-429) — `APIError.rateLimited` · `APIClient` Retry-After 전달 · LoginScreen 꼬리말 제거 · `RateLimitTests.swift` 11건. Windows 에서 작성 → macOS CI run 35318843546(workflow_dispatch) **green**: SwiftLint 통과 · 216/0 (RateLimitTests 11/0) · **main 반영: PR #4 merge 61b7e54 (2026-09-21 01:45Z, foes88) · main c134c59 CI run 35555473540 green** |

### 9-9-1. 3-클라이언트 파리티 매트릭스 (2026-09-18)

정책 소스는 서버 하나다. 클라이언트는 **뜻(한도 상태)** 과 **서버가 준 Retry-After** 만 보여준다.
한도값 재현 없음(`MAX_SIGNUP=5` 류 상수 금지 — 세 저장소 모두 소스 스캔 테스트로 강제) ·
자동 재시도 없음 · 카운트다운/버튼 잠금 없음 · 429 ≠ 451 ≠ 401.

| 항목 | Web | Android | iOS |
|---|---|---|---|
| 429 → 한도 상태 매핑 (status 또는 `RATE_LIMITED` 토큰) | ✅ `resolveApiError` | ✅ `RateLimited.from(HttpException/Response)` | ✅ `APIError.from(status:detail:retryAfter:)` |
| `Retry-After` 파싱 — delta-seconds · HTTP-date · ≤0/>86400/불명 → 없음 | ✅ | ✅ | ✅ |
| 폴백 — 값 없으면 기본 문장만 (기본 대기시간 발명 금지) | ✅ | ✅ | ✅ |
| 가입(register / onboarding complete) 429 | ✅ onboarding 페이지 | ✅ `OnboardingViewModel.fail` | ✅ `errorDescription` 경로 (`/auth/register`) |
| 로그인 429 — 401 문구와 분리, 자격증명 안내 없음 | ✅ | ✅ `credentialHint=false` | ✅ `errorIsRateLimited` |
| 비번 재설정 요청 429 — 열거 안전 "발송" 문구 대신 한도 상태 | ✅ forgot-password | ✅ `requestReset` (confirm 섹션 열지 않음) | `NOT_APPLICABLE` — iOS 에 재설정 플로우 없음(관리자 문의 alert) |
| 비번 재설정 확정 429 — "코드 무효" 와 분리 | ✅ | ✅ `confirmReset` | `NOT_APPLICABLE` (同上) |
| 자동 재시도 없음 (호출 1회 단언) | ✅ | ✅ `loginCalls/completeCalls/resetRequestCalls == 1` | ✅ stub handler 1회 |
| 8 locale 문구 | ✅ 8/8 (`i18n.test.ts` 파리티) | ✅ 8/8 (`values` + 7) | ⚠️ **en 만** — 앱 자체가 `Localizable.xcstrings` en 단일 (429 와 무관한 기존 갭 · 현황/영향: `docs/runs/IOS_LOCALE_GAP_20260918.md`) |
| 화면까지 도달 검증 | ✅ RTL 페이지 테스트 | ✅ Robolectric `LoginScreenTest` (ko 실문구) | ✗ UI 테스트 없음 — 단위/클라이언트 스텁까지 |
| 정책 상수 부재 소스 스캔 | ✅ | ✅ `RateLimitedTest` | ✅ `testAppSourceNeverReplicatesServerPolicy` |

```
WEB_IMPLEMENTED = YES   WEB_TESTED = YES   (8b7077c · vitest)
ANDROID_IMPLEMENTED = YES   ANDROID_TESTED = YES   ANDROID_CI_GREEN = YES   (0e1d450 · 로컬 446/0 · CI run 35555598654 @ 746d0af 446/0 — 09-18 의 CI 실패는 setup-android@v3 기본 `tools` 패키지 제거 때문, D3 에서 해소)
IOS_IMPLEMENTED = YES   IOS_COMPILED = YES   IOS_TESTED = YES   (7210e1c · CI run 35318843546 green · 216/0)
FUNCTIONAL_429_PARITY = YES          — 세 클라이언트 모두: 429 사용자 의미 · Retry-After 해석 · missing/invalid fallback · no-auto-retry · 정책 미복제 · CI 검증
THREE_CLIENT_PARITY_VERIFIED = NO    — 성공 조건에 locale coverage 가 있고 iOS 는 en 1/8. PigOS 는 8언어 제품이고 iOS 1.1 다국어가 예정돼 있으므로(RELEASE_APPSTORE §4-1)
                                       "en 단일 = 공식 지원범위" 로 재정의하지 않는다 (판정 B). 남은 갭 = iOS locale coverage 만 (`docs/runs/IOS_LOCALE_GAP_20260918.md`)
G3 429 PARITY = PARTIAL              — Web·Android DONE · iOS 기능 DONE · iOS locale 미완. D3(Android CI) 는 DONE
                                       N/A 2건(iOS onboarding·reset = 플로우 부재)은 갭이 아니라 적용 대상 없음. 화면 도달 검증은 Web·Android 만(iOS UI 테스트 부재)
```

★ 이 트랙은 **정책·게이트를 바꾸지 않았다.** 서버 한도값·버킷·451 처리·가입 게이트 전부 그대로다.

## 10. 후속 STEP (이번 범위 아님)

```
STEP 1   D-19 v1.3 spec 검증 → 필요 시 v1.4 승격 → repo 편입 → current HEAD 재실행
STEP 2   Product v1.0 → v1.1 patch 4축
         ① Platform assumption correction  ② Offline contract
         ③ Mobile 포함 Instrumentation      ④ Country Rollout Gate + min app version
STEP 3   FEATURE_REGISTRY + code path mapping (실측 기반. 추정 금지)
STEP 4   EPIC 1 모바일 안전화 (local severity 제거 · insufficient 소비)
STEP 5   CI + Release Gate + App Version Gate
```

★ Mobile targeted audit 자체는 **GATE 0 blocker 가 아니다.**
  unsafe local judgment 제거는 **EPIC 1**, full parity 는 **국가 rollout blocker** 다.

---

## 11. 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-09-18 | §9-9 `SIGNUP_RATE_LIMIT_429` 3-클라이언트 반영 — Web `DONE`(8b7077c) · Android `DONE`(0e1d450, 446/0) · iOS `DONE`(7210e1c, CI 216/0). §9-9-1 파리티 매트릭스 신설 |
| 2026-09-21 | §9-9-1 판정 정정 — `THREE_CLIENT_PARITY_VERIFIED=YES` → **`FUNCTIONAL_429_PARITY=YES` / `THREE_CLIENT_PARITY_VERIFIED=NO` / G3 PARTIAL**. 근거: 성공 조건의 locale coverage 에서 iOS 가 en 1/8 이고 iOS 다국어(1.1) 가 예정된 제품이라 GAP 을 안고 YES 라 쓸 수 없다. Android 는 CI run 35555598654 로 `ANDROID_CI_GREEN=YES` |
| 2026-08-27 | `MOBILE_PARITY.md` 신설 |
| 2026-08-28 | `PLATFORM_PARITY.md` 로 `git mv`. STEP 0 — 기존 6행 evidence 재판정(DONE 2 → IN_PROGRESS, `done_with_sha=0`) · Track B 실측 고정 · `BACKEND_NO_JUDGMENT_STATE=PRESENT` 확인 · blocker 9건 등록 |
| 2026-09-01 | 자연 실행 acceptance 결과 기록(§9-4-7) — ARQ 73/73 OK · `j_complete` 3→6 · `j_failed=0` · snapshot 219행/73농장, `psy`·`farrowing_rate` 유입 0. `ARQ_HOTFIX = PASS_ON_SUCCESS_PATH / FAILURE_PATH_LOCALLY_VERIFIED` (CLOSED 아님) · `SNAPSHOT_WRITER = OPERATIONAL` |
| 2026-08-31 | `2e372b1` 프로덕션 배포(api·worker). ARQ false-success 해소 확인(비파괴). B-12 해소 · B-11 부분해소. snapshot 은 WRITER_OPERATIONAL 까지만 인정, reader 전환 없음. G4 완료 정의 고정(§9-3) |
| 2026-08-28 | 야간 remediation evidence 등록(§9-2) — Core/Web/Android/iOS 8개 구현 commit. B-4·B-10·B-12 해소, B-11 부분 해소. iOS 는 NOT_RUNTIME_VERIFIED 유지, Web 은 vitest 환경 blocker 로 PRESENT_BUT_NOT_EXECUTED |
| 2026-08-28 | ★ Web 행 정정 — `NOT_APPLICABLE` → `BLOCKED / WEB_LOCAL_STATUS_FALLBACK` (D-19 N-7). ACTIVE(모바일) vs DORMANT(웹) 분리. blocker B-10~B-14 등록 |
| 2026-08-28 | STEP 1 착수 전 docs-only 보완 3건 — ① rename provenance + rename commit 분리 규율 ② B-3 → `P0-1` correctness blocker 승격 · Android `FAIL_CLOSED_BY_COINCIDENCE` 명기 ③ B-8 → `CI_EXTENSION_REQUIRED` 재분류 · `ANDROID_RELEASE_ARTIFACT_RETENTION` OPEN ISSUE 등록 |
