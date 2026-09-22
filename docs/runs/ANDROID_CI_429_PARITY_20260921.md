# D3 — Android CI 복구 → 429 3-Client Parity 최종 판정 (2026-09-21)

> 브랜치 pigos-android `fix/android-ci-tools-429-parity-20260921` = `0e1d450`(429 구현) + `746d0af`(CI 수정) · Draft PR wiselake/pigos-android#6.
> 불변: PR #3·#2·#5 변경 0 · main push 0 · 프로덕션 0 · Android 기능 확장 0 · 서버 정책 0 · 테스트 삭제/skip 0.

## 1. CI root cause (실측)

```
run            35321591116  (Draft PR #5 @ 0e1d450, 2026-09-18 07:53Z)  fail @22s, step "Set up Android SDK"
action         android-actions/setup-android@v3   (workflow 는 with: 없음 → 액션 기본값 사용)
기본 입력      cmdline-tools-version=12266719 · packages="tools platform-tools"    ← 로그 실측
최초 원인 줄   "Warning: Failed to find package 'tools'" → sdkmanager exit 1 → Gradle 실행 전 종료
분류           B. setup-android action 입력 기본값. 저장소(workflow·gradle·script) 어디에도 `tools` 요구 없음(grep 0)
왜 지금        마지막 초록 run 34430294592 (main 32b7a9f, 2026-09-10) 은 같은 기본값으로 `tools` 를 설치했고
               그 김에 emulator 까지 끌어왔다. 그 사이 Google 이 레거시 `tools` 패키지를 저장소에서 제거.
               setup-android v4.0.2 (2026-09-17) 릴리스 노트: "Fix for removed tools package" · v4 기본 packages="platform-tools"
```

## 2. 패치 (`746d0af`, workflow 1파일 +9/−1)

```yaml
- uses: android-actions/setup-android@v4
  with:
    packages: 'platforms;android-36'     # compileSdk 36. 기본값에 기대지 않고 명시
```

- 필요 SDK 컴포넌트: 유닛 테스트 + `assembleDebug` 에는 `platforms;android-36` 뿐. build-tools 는 AGP 가 라이선스 수락 상태에서 자동 설치(로그: "Set up Android SDK" 이후 Gradle 이 별도 설치 없이 빌드). adb·emulator·instrumentation 불필요 → `platform-tools` 도 넣지 않음.
- 불변: JDK 17 · Gradle 9.4.1 wrapper · AGP 9.2.1 · compileSdk/targetSdk 36 · minSdk 24 · signing · google-services · versionCode/Name · variant 전부 그대로.
- 트리거 감사: `push: [main, master]` + `pull_request` — stale 브랜치 없음. 변경 안 함.
- lint: 현재 CI 에 없음(원래부터). 로컬 `lintDebug` 는 기존 오류 4건(MissingTranslation ru ×2 `alerts_generate_result`·`cross_foster_count` · `LocalContextConfigurationRead` OnboardingScreen:78 · `PropertyEscape` local.properties=로컬 파일) 으로 실패 — **429 무관·D3 이전부터**. CI 에 lint 를 추가하려면 이 4건 정리가 선행 → 범위 밖, 별도 항목.

## 3. 검증

| 단계 | 로컬 (JDK 21 / Gradle 9.4.1) | GitHub Actions run **35555598654** (746d0af, 02:52–03:01Z) |
|---|---|---|
| Set up Android SDK | — | **PASS** (`packages: platforms;android-36`, cmdline-tools 15859902) |
| Gradle bootstrap | PASS | PASS |
| `:app:testDebugUnitTest` | **446 / 0 failed** | **446 tests · 0 failures · 1 ignored** (업로드된 unit-test-report 실측) — RateLimitedTest · LoginViewModelTest · OnboardingViewModelTest · LoginScreenTest 포함 |
| `:app:assembleDebug` | PASS (app-debug.apk 71.7MB) | PASS (BUILD SUCCESSFUL 2m52s) |
| lint | 기존 오류 4건(§2) | CI 미포함 |

→ **ANDROID_CI_GREEN = YES** — 429 코드가 실제 CI 에서 compile·test 됐다.

## 4. Android 429 재검증 (코드 재독 + 테스트 매핑)

| 항목 | 구현 | 테스트 |
|---|---|---|
| HTTP 429 식별 | `data/remote/RateLimited.from(Throwable)` (Retrofit `HttpException` 429) · `from(Response<*>)` | `RateLimitedTest` 429 매핑 ×2 |
| Retry-After 파싱 | delta-seconds 정수 · RFC 7231 HTTP-date(GMT) · 올림 | delta ×3 · HTTP-date ×2 |
| missing fallback | `retryAfterSeconds=null` → 기본 문장만 | 429 without header · VM 2건 · 화면 1건 |
| invalid / ≤0 / >86400 fallback | null (지어내지 않음) | `"soon"`,`"12.5"`,`"0"`,`"-5"`,`"86401"`,`""`,null |
| signup (Android 가입 경로 = `POST /onboarding/complete`, signup 버킷) | `OnboardingViewModel.fail` → `rate_limited`, 폼 유지, 세션 미생성 | OnboardingVM 429 ×2 + 비-429 유지 1 |
| onboarding | 同上 (Android 는 register 와 onboarding 이 같은 호출) | 同上 |
| login | `LoginViewModel.login` → `rate_limited` (+분) · 401 은 `vm_login_failed` 유지 · `credentialHint=false` | LoginVM 429/401/field-clear · Robolectric 화면 2 (실문구 ko, 꼬리말 없음) |
| password reset | 요청 429 → 열거안전 "발송" 대신 한도 상태, confirm 섹션 안 엶 · 확정 429 → "코드 무효" 와 분리 | reset request 429/500 · confirm 429/422 |
| 429 ≠ 401 ≠ 451 | 451·401·422 는 `RateLimited.from` = null | `non-429 … not rate limited` |
| auto retry 없음 | OkHttp `retryOnConnectionFailure` 기본(연결 실패만, HTTP 상태 무관) · `TokenAuthenticator` 는 401 전용(OkHttp Authenticator 계약) · `SyncRepository` retryCount 는 `/farms/{id}/sync` 항목 재큐(429 버킷 아님) · WorkManager 는 sync 전용 | `loginCalls/completeCalls/resetRequestCalls == 1` · 화면 테스트 `loginCalls == 1` |
| 서버 정책 숫자 복제 | 없음 — `MAX_*`/`RATE_LIMIT_*`/`PER_HOUR`/`retryAfter*=숫자` grep 0 | `client source never replicates the server rate-limit policy` (소스 스캔) |
| locale | 8/8 (`values` + es/ko/pt/ru/th/vi/zh) `rate_limited`·`rate_limited_retry_in`, placeholder `%1$d` 8곳 동일 | 스크립트 실측 (2026-09-21) |
| typed error | 기존 `Result<T>`/`Throwable` 모델 유지 + `RateLimited` 값 객체 — 새 아키텍처 없음 | — |

서버 contract 재확인 (PigOS `api/app/core/rate_limit.py:109-112`): status 429 · `{"detail":"RATE_LIMITED:signup|auth"}` (code 없음) · `Retry-After` delta-seconds 헤더만(본문에 없음).

## 5. 3-Client Parity Matrix (최종)

| 항목 | Web | Android | iOS |
|---|---|---|---|
| HTTP 429 식별 | PASS `resolveApiError` | PASS `RateLimited.from` | PASS `APIError.rateLimited` |
| Retry-After (delta·HTTP-date) | PASS | PASS | PASS |
| missing fallback | PASS | PASS | PASS |
| invalid fallback (≤0 · >86400 · 불명) | PASS | PASS | PASS |
| signup | PASS onboarding 페이지 | PASS `/onboarding/complete` | PASS `/auth/register` |
| onboarding | PASS | PASS (register 와 동일 호출) | N/A — iOS 는 register+createFarm, `/onboarding/complete` 미사용 |
| login | PASS (401 문구와 분리) | PASS (`credentialHint=false`) | PASS (`errorIsRateLimited`, 소스 스캔 가드) |
| reset | PASS forgot-password | PASS 요청·확정 | N/A — iOS 에 재설정 플로우 없음 |
| 429 ≠ 451 | PASS | PASS | PASS |
| auto retry 없음 | PASS | PASS (OkHttp/Authenticator/Sync 감사) | PASS (401 refresh 만) |
| locale coverage | PASS 8/8 (`i18n.test.ts`) | PASS 8/8 (`%1$d` 동일) | GAP — 앱 자체 en 단일 (`IOS_LOCALE_GAP_20260918.md`) |
| tests | PASS vitest +21 | PASS 446/0 (RateLimited 9 · VM 11 · 화면 2) | PASS RateLimitTests 11 + 소스 가드 1 |
| CI/build | PASS PR #2 run 35422553240 (8b7077c 포함) | **PASS run 35555598654** | PASS run 35321586461 (e750daa) · **main 에 merge 됨** 61b7e54, main CI run 35555473540 |

UNKNOWN 0. N/A 2건(적용 대상 없음)과 GAP 1건(iOS locale — 판정을 NO 로 잡는 원인) 은 사유 명시.

```
ANDROID_CODE_IMPLEMENTED       YES  (0e1d450)
ANDROID_LOCAL_TESTED           YES  (446/0)
ANDROID_CI_GREEN               YES  (run 35555598654 @ 746d0af)
FUNCTIONAL_429_PARITY          YES  — 의미 동일: 429 사용자 의미 · Retry-After 해석 · fallback · no-auto-retry · 정책 미복제 · 세 클라이언트 CI 검증
THREE_CLIENT_PARITY_VERIFIED   NO   — 성공 조건에 locale coverage 포함. iOS 는 en 1/8 (판정 B: iOS 1.1 다국어 예정, en 단일을 공식 범위로 재정의하지 않음)
                                     N/A 2건(iOS onboarding·reset)은 플로우 부재 = 적용 대상 없음, 갭 아님
G3 429 PARITY                  PARTIAL — 남은 갭 = iOS locale coverage 하나. D3 (Android CI) 는 DONE
```

## 6. 남은 것

- (D4 정리 2026-09-21) Android #5 **CLOSED** — #6 이 완전 포함함을 조상관계·커밋 목록·바이트 diff 로 증명. #6 = canonical Draft (MERGEABLE/CLEAN, green). iOS #4 는 이미 **MERGED**(61b7e54, main CI green).
- 남은 결정: Android #6 merge.
- Android lint 기존 오류 4건 정리 후 CI 에 lint 추가 — 별도 항목(D3 범위 밖).
- iOS 다국어 1.1 (D8 = DEFER_TO_IOS_1_1_MULTILINGUAL; 기존 `feature/1.1-localization` 브랜치가 출발점).
