# RUNLOG — 2026-09-18 (Fri) 19:00 → 2026-09-21 (Mon) 09:00 KST

> 형식: "했다" 가 아니라 "이 SHA 에서 이 run 이 초록". 추정값·예시값을 실측처럼 적지 않는다.
> 불변: merge 0 · 배포 0 · main 직접 push 0 · 프로덕션 쓰기 0 · **프로덕션 읽기 0**(pigos_ro 결재 5 미승인) ·
> 법무 문안 0 · manifest status 0 · 정책/게이트/451/한도값 0 · 마이그레이션 0 · 타 세션 워크트리 0.

## CP-0 · 2026-09-18 16:45 KST — 착수 (예정 19:00 보다 앞당겨 시작)

| 항목 | 상태 | 근거 |
|---|---|---|
| G1 PR #3 | **DONE (유지 중)** | head `d088e73` · base `main@8a80ea4`(변동 없음) · checks backend(3.12)/backend(3.14)/frontend 모두 SUCCESS · `mergeable=MERGEABLE` · `mergeStateStatus=CLEAN` · draft. 코드 변경 0 |
| G1 제9조 10행 | 발췌 확보 | `docs/legal/publish_candidate/PIGOS_GLOBAL_PRIVACY_NOTICE.md:143-153` — main `8a80ea4` · PR #3 `d088e73` · safety `7d13e26` 세 곳 md5 동일 (`0064210d…`) |
| G2 Feed PHASE 0 | NOT_STARTED | — |
| G3 429 잔여 | NOT_STARTED | 선행: Android `0e1d450` 로컬 446/0 · iOS `7210e1c` CI run 35318843546 green 216/0 (PROGRESS.md 2026-09-18) |
| G4 테스트 부채 | NOT_STARTED | — |
| G5 제안서 | NOT_STARTED | — |

환경: hostname `bjh` ✓ · PigOS local main = safety/pigos-20260916 `7d13e26` (origin/main 대비 ahead 163) · Docker 상태 미확인(G2 에서 확인).

## CP-1 · 2026-09-18 17:05 KST

| 항목 | 상태 | 근거 (SHA · run) |
|---|---|---|
| G1 PR #3 | **DONE (유지)** | 변동 없음: head `d088e73` · base `8a80ea4` · MERGEABLE/CLEAN · 3 checks SUCCESS |
| G2 Feed PHASE 0 | **DONE (조건부)** | PigOS `4fb3aca` — `scripts/feed_coverage_audit.sql`(61지표+3표, BEGIN READ ONLY) · `scripts/run_feed_audit.sh`(프로덕션 패턴 exit 3) · `scripts/feed_audit_fixture_synthetic.sql` · `docs/feed/PHASE0_AUDIT_PLAN.md`(임계 선정의) · 샘플 `docs/feed/reports/feed_audit_synthetic_20260918T075017Z.txt`. 로컬 docker pg16.15 alembic `f3c6a8d0b2e4`: 빈 DB 에러 0 · 합성 fixture 에러 0 · scratch DB DROP 확인. **조건**: 별도 스테이징 환경 없음(실측) → "스테이징" = 로컬 동일 스키마. 실데이터 실행 0 (결재 5) |
| G3 iOS 소스 스캔 테스트 | **DONE** | pigos-ios `e750daa` `LoginScreenRateLimitSourceTests` — Draft PR #4 CI run 35321586461 **green** (pull_request, build-test-lint pass) |
| G3 Android Draft PR CI | **BLOCKED (인프라)** | pigos-android Draft PR #5 @ `0e1d450` run 35321591116 **fail @22s** — `android-actions/setup-android@v3` `packages: tools platform-tools` → `Warning: Failed to find package 'tools'` → sdkmanager exit 1. **빌드/테스트 단계 도달 전.** 같은 workflow 가 main `32b7a9f` 에서 2026-09-10 run 34430294592 green → 러너 환경 변화(cmdline-tools 16.0 에서 legacy `tools` 패키지 제거). 코드 원인 아님. 임의 수정 금지 → 원인만 기록. ANDROID_TESTED 근거는 로컬 446/0 유지 |
| G3 iOS locale 갭 | **DONE (문서화까지)** | PigOS `481cd4e` `docs/runs/IOS_LOCALE_GAP_20260918.md` — xcstrings 265키 · 번역 0언어 · `CFBundleLocalizations=[en]`(1.0 결정, RELEASE_APPSTORE §4-1) · LANDING_SYNC §1 "iOS 미출시" 라 현재 위조 아님, 출시 시 §1·§2 동시 수정 필요. 번역 추가 0 |
| G4 | NOT_STARTED | — |
| G5 | NOT_STARTED | — |

push: PigOS safety/pigos-20260916 은 `7d13e26` 까지 push 됨 (이후 `698bda3`·`4fb3aca`·`481cd4e` 로컬). mobile 두 Draft PR 개설(#4 iOS, #5 Android) — merge 아님.

## CP-2 · 2026-09-18 17:40 KST — G1~G5 1차 완료, 주말은 유지 모드

| 항목 | 상태 | 근거 |
|---|---|---|
| G4 | **DONE** | branch `test/trend-psy-frozen-as-of` `c17c5df` (origin push) — 2026-06 고정 시나리오를 `as_of=2026-06-30` 로 복원. 로컬 2 passed · ruff clean. PR 없음, PR #3 무관 |
| G5 | **DONE (제안만)** | `5a356a3` `docs/runs/PROPOSAL_MARKER0_REQUIRED_CHECK_20260918.md`. 실측: enforcer 파일은 통합 conftest PREFLIGHT 로 DB 필요. ci.yml·protection 변경 0 |
| 인계 패킷 | 초안 확정 | `e8c2bfd` `docs/HANDOVER_20260921.md` — G1~G5 · 결정 D1~D8 · 제9조 10행 발췌(md5 `0064210d…`) · 다음 한 수 = D1 |
| push | safety/pigos-20260916 @ `e8c2bfd` (= PR #2 head → PR #2 CI 재실행 중) | |
| 유지 모드 | 4시간 주기 체크포인트 예약(세션 cron `d36c6bbe`, 01/05/09/13/17/21시 :23) — G1 재확인 · CI 결과 기록 · runlog append. 코드 변경 없음 | |

## CP-3 · 2026-09-18 17:53 KST

| 항목 | 상태 | 근거 |
|---|---|---|
| G1 PR #3 | **DONE (유지)** | head `d088e73` · base `origin/main@8a80ea4` 미변동 · MERGEABLE/CLEAN · backend(3.12)/backend(3.14)/frontend = SUCCESS. 재실행 불필요, 코드 변경 0 |
| PR #2 (safety/pigos-20260916) | green | head `4f43d68` run **35322258960 success** (e8c2bfd 의 run 35322205796 은 concurrency 로 cancelled — 후속 push 에 대체됨). MERGEABLE/CLEAN |
| pigos-ios #4 | green | `e750daa` run 35321586461 success (변동 없음) |
| pigos-android #5 | fail (인프라) | `0e1d450` run 35321591116 failure — CP-1 원인 그대로(setup-android `tools`). 재실행·수정 안 함 |

변경 0 · push 는 이 runlog 커밋만.

## CP-4 · 2026-09-18 21:53 KST

| 항목 | 상태 | 근거 |
|---|---|---|
| G1 PR #3 | **DONE (유지)** | head `d088e73` · base `origin/main@8a80ea4` 미변동 · MERGEABLE/CLEAN · 3 checks SUCCESS. 재실행 불필요, 코드 변경 0 |
| PR #2 | green | head `0e3e8db` run **35326718691 success** · MERGEABLE/CLEAN |
| pigos-ios #4 | green | `e750daa` run 35321586461 (변동 없음) |
| pigos-android #5 | fail (인프라) | `0e1d450` run 35321591116 (변동 없음, 수정 안 함) |

변경 0 · 인계 패킷 갱신 불필요.

## CP-5 · 2026-09-19 01:53 KST

| 항목 | 상태 | 근거 |
|---|---|---|
| G1 PR #3 | **DONE (유지)** | head `d088e73` · base `origin/main@8a80ea4` 미변동 · MERGEABLE/CLEAN · 3 checks SUCCESS. 코드 변경 0 |
| PR #2 | green | head `950e49d` run **35347118078 success** · MERGEABLE/CLEAN |
| pigos-ios #4 | green | `e750daa` run 35321586461 (변동 없음) |
| pigos-android #5 | fail (인프라) | `0e1d450` run 35321591116 (변동 없음, 수정 안 함) |

변경 0.

## CP-6 · 2026-09-19 05:53 KST — PR #2 빨강 (시간대 경계 날짜 의존, 코드 변경 없이 발생)

| 항목 | 상태 | 근거 |
|---|---|---|
| G1 PR #3 | **DONE (유지)** | head `d088e73` · base `origin/main@8a80ea4` 미변동 · MERGEABLE/CLEAN · 3 checks SUCCESS. 코드 변경 0 |
| PR #2 | **red** | head `fe6e455`(docs-only) run **35371186151 failure** — backend(3.12)·(3.14) 둘 다 `tests/integration/test_kpi_presentation_resolver.py::test_future_presentation_row_ignored` `assert 10 == 30`. frontend success. mergeStateStatus=BLOCKED |
| pigos-ios #4 | green | `e750daa` run 35321586461 (변동 없음) |
| pigos-android #5 | fail (인프라) | `0e1d450` run 35321591116 (변동 없음) |

**PR #2 실패 원인(기록만, 수정 안 함)**
- 테스트는 `tomorrow = date.today() + 1`(러너 로컬 = UTC)로 미래 행을 만들고, 리졸버는 `governance_today()` = `GOVERNANCE_TZ` 기본 `Asia/Seoul` 로 발효일을 판정한다(`kpi_policy_resolver.py:230`, `farm_time.py:98-103`).
- run 시각 2026-09-18 **16:54 UTC** = 09-19 01:54 KST → KST 의 "오늘" 이 UTC 의 "내일" 과 같아 미래 행이 이미 발효 → 10.
- 즉 **15:00–24:00 UTC(00:00–09:00 KST) 창에서만 깨지는 시간대 경계 날짜 의존**. 같은 테스트가 `origin/main` 에도 그대로 있다(grep 1건) → PR #3 도 동일 위험. PR #3 의 green run 35293878390 은 01:05 UTC(10:05 KST) 실행이라 창 밖이었다.
- docs-only 커밋이 트리거했을 뿐 코드 원인 아님. 임의 수정 금지 지시 → **재실행도 하지 않는다**(KST 낮에 재실행하면 초록이 되겠지만 그것은 문제를 가리는 것). 결정 큐 D9 로 올린다.

**G1 영향**: PR #3 head 는 green 그대로이고 base 도 안 움직였다 → merge-ready 유지. 단 **base 가 움직여 CI 재실행이 필요해지면 KST 09:00–24:00 에 돌려야 한다**(그 외 시간엔 이 테스트로 빨강). 인계 패킷에 명시.

## CP-7 · 2026-09-19 09:53 KST

| 항목 | 상태 | 근거 |
|---|---|---|
| G1 PR #3 | **DONE (유지)** | head `d088e73` · base `origin/main@8a80ea4` 미변동 · MERGEABLE/CLEAN · 3 checks SUCCESS. 코드 변경 0 |
| PR #2 | **red (같은 원인)** | head `a06aa9d` run **35394188042 failure** — 20:57 UTC(05:57 KST) 실행, 같은 테스트 `assert 10 == 30` ×2(3.12/3.14). CP-6 진단 그대로(창 안) |
| pigos-ios #4 | green | `e750daa` run 35321586461 (변동 없음) |
| pigos-android #5 | fail (인프라) | `0e1d450` run 35321591116 (변동 없음) |

이 CP 의 push 는 00:5x UTC(창 밖) 에 실행된다 — 코드 변경 없이 초록이면 CP-6 진단(시간대 경계)이 실측으로 확정된다. 다음 CP 에서 기록.

## CP-8 · 2026-09-19 13:53 KST — 시간대 경계 진단 실측 확정

| 항목 | 상태 | 근거 |
|---|---|---|
| G1 PR #3 | **DONE (유지)** | head `d088e73` · base `origin/main@8a80ea4` 미변동 · MERGEABLE/CLEAN · 3 checks SUCCESS. 코드 변경 0 |
| PR #2 | **green** | head `85c6994` run **35410963895 success** (00:55 UTC = 09:55 KST, 창 밖). MERGEABLE/CLEAN |
| pigos-ios #4 | green | `e750daa` run 35321586461 (변동 없음) |
| pigos-android #5 | fail (인프라) | `0e1d450` run 35321591116 (변동 없음) |

**확정**: fe6e455 → a06aa9d → 85c6994 는 docs 커밋만 다르고 api/ 는 동일한데,
16:54 UTC red · 20:57 UTC red · 00:55 UTC green. `test_future_presentation_row_ignored` 의
UTC/KST 경계 의존(CP-6) 이 코드 변경 없이 실측으로 확인됐다. D9 근거로 충분. 수정 안 함.
