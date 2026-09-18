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
