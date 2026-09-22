# 개발 생태 실측 — 2026-09-11

> **성격**: 코드가 아니라 **개발이 굴러가는 바탕**을 잰 것. 확장(사용자·국가·인원)을
> 앞두고 어디가 먼저 찢어지는지. 전부 이 머신(`bjh`)·저장소·프로덕션 문서에서 실측했고,
> 추정한 값은 없다. 두 세션이 교차 검증했다(거짓 경보 1건 걷어냄 — 아래 §0).
> **고친 것과 기록만 한 것을 구분한다.**

---

## 0. 거짓 경보 — 문제 아님

```
src/.env.production      추적 중이지만 NEXT_PUBLIC_API_URL · NEXT_PUBLIC_APP_URL 둘뿐 — 빌드타임 공개값
google-services.json     Firebase 클라이언트 설정. APK 에 어차피 들어간다
.gitignore               .env · .env.local · *.env.supabase 막혀 있음
→ 추적 파일 기준 시크릿 0건. push 가 이것 때문에 막히지는 않는다
```

---

## 1. 실측표

| 축 | 값 | 상태 |
|---|---|---|
| 저장소 | PigOS · pigos-android · pigos-ios · pigos-landing (4개 독립) | |
| 미푸시 | **PigOS 132** (origin/main = 8/27 `e7133fa`) · Android 5 · iOS 4 | ★ 한 PC 에만 존재 |
| 커밋 속도 | 9/8~9/11 나흘 69건 | 법무 트랙이 개발을 안 막고 있음 |
| **CI** | `ci.yml` 트리거가 `pull_request → development`. **그 브랜치는 존재한 적 없음.** `gh run list --workflow=ci.yml` → **0건** | ★ 2026-06-14 이후 한 번도 실행 안 됨 → **고침** (§2-1) |
| 백엔드 CI 범위 | unit 만 (integration 189 파일 중 다수 미실행 · `test_migration_parity` 포함) | → **고침** (§2-1) |
| Python | 로컬 3.14.2 · 프로덕션 이미지 3.12 · CI 3.12 → 매트릭스 3.12+3.14 | → **고침** |
| uv venv | `sqlalchemy-2.0.49.dist-info` RECORD 누락 → 실행마다 재설치 | → **고침** (stale dist-info 삭제) |
| Node | 22.23.2 (`.nvmrc`·CI 동일). 쉘 기본은 20.11.1 → PATH 안 잡으면 vitest 부팅 실패 | 기록 |
| Docker | postgres·redis healthy | PREFLIGHT exit 78 로 환경 실패 분리됨 |
| npm audit (prod) | critical 1 (next RCE ×2 포함) · high 5 → **0 · 0** (next 15.5.25 · axios 1.20 · postcss 8.5.28) | → **고침** (§2-2) |
| npm audit 잔여 | next 내장 postcss 8.4.31 (fix = next 16 major, 미채택) · dev: js-yaml(redocly) · vitest mocker | 기록 |
| Python deps | 마이너 뒤처짐 다수, 보안 스캔 도구 0 (T-6) | 기록 |
| **라이선스** | Python 83 pkg: GPL/AGPL/SSPL **0** (LGPL: psycopg2-binary) · npm prod 84: GPL/AGPL **0** (LGPL: sharp win32 바이너리) | ★ 서버 측 AGPL 없음 |
| 코드 | API 23.9k · 웹 17.4k · alembic 53 | |
| 테스트 | 백엔드 1481 · 프론트 223 · Android 427 · iOS 컴파일 불가(PC) | |
| rate limit | `/auth/register` · `/onboarding/complete` **0건** (slowapi·limiter 없음) | ★ 마감: 가입 재개 전 (§3) |
| i18n 정합 | 웹 `i18n.test.ts` 8로케일 키 파리티 있음. iOS 체크리스트가 가리키는 `scripts/validate_i18n.py` **없음**. Android 639 문자열 × 8 로케일 교차 검사 0 | 기록 (§3) |
| 관측 | Sentry/OTel/Prometheus 0 · 제품 계측 0 (F-0005) · ARQ 인시던트(§9-6) | 기록 |
| 인프라 | 공유 EC2 1대 · self-host PG17 · failover 없음 · PITR 없음 · S3 백업 | RDS 트리거 = 유료 고객 (INFRA §5) |
| **백업 복구** | 복원 실행 기록 **0** — 복구해본 적 없는 백업은 백업이 아니다 | → EC2 세션 B-8 |
| **공개 사이트** | `pigos.io/privacy` 5/30 자 한국어 구본 · `/terms` 피그플랜 문안 · 푸터 5곳이 거기로 | ★ 격리 밖 법무 노출 → H17 |

---

## 2. 오늘 고친 것

### 2-1. CI 를 실제로 돌게 (`f4d684e`)

```
트리거      push · pull_request → main
백엔드      postgres:17 + redis:7 서비스 · pigos_test 생성 · ★ 빈 DB 에 alembic upgrade head
            → pytest tests (unit + integration) · Python 3.12 × 3.14 매트릭스
리허설      이 머신에서 빈 DB 2개로 같은 env 그대로: 마이그레이션 완주 → 1481 passed · 1 skipped · 12 xfailed
```

`test_migration_parity` 는 8/25 부터 있었고 로컬에서는 통과했지만 CI 는 한 번도
안 돌렸다. 새 안전장치가 아니라 **쓰여 있던 것을 켠 것**이다.

★ **2026-09-16 실전 결과** (safety/pigos-20260916 → PR #2, base ci-base/pigos-20260827):
```
run 35049601480   backend ✗ ruff 47건 (로컬도 47 — "3건"은 변경파일 기준) · frontend ✓
run 35049978252   backend 3.12 ✓ 1481/1/12 (2:16) · 3.14 ✓ (2:01) · frontend ✓   ← 기준점
```
CI 가 큐잉조차 안 되던 원인이 하나 더: origin/main 이 갈라져(8a80ea4) merge ref 를 못 만들면
pull_request 워크플로는 **조용히 안 돈다**. 그래서 ci-base/* 리허설 base 를 두었다 (B-9).

### 2-2. 취약 의존성 (`21a2ad7`)

`npm audit fix` 는 이 lockfile 에서 크래시(arborist `edgesOut` null). 직접 올렸다.
tsc · 223 tests · production build 통과.

### 2-3. venv 복구

`sqlalchemy-2.0.49.dist-info` (RECORD 없음) 를 지웠다. `uv sync` 가 "Audited 83 packages" 로 조용해짐.

---

## 3. 기록만 — 결정이나 마감이 붙은 것

```
rate limit        가입 재개(약관 승인) 전에 /auth/register · /onboarding/complete 에 붙인다
                  스팸 가입 = 개인정보 대량 수집이라 법무 축과 같다. 지금은 G-3 가 막을 예정이라 노출 없음
i18n 스크립트     pigos-ios/docs/MAC_VERIFY_CHECKLIST.md:33 이 없는 파일을 가리킨다 — 만들거나 참조를 뺀다 (iOS 저장소, 다른 세션)
                  Android ↔ 웹 문자열 교차 검사는 아직 없다. 늘어나는 중(오늘 +4키×8)
관측              Sentry(api+web) + /health 에 DB·redis·worker 상태 — 하루
국가 추가 리허설  가상국 1개를 INSERT 만으로 넣고 서버·웹 전 경로 통과 테스트 (ADR-KPI-00 I-2)
push              main 만인지 개발 브랜치까지인지 — Brian 한 줄. 시크릿 기준으로는 막을 이유 없음(§0)
```

---

## 4. 관련

```
.github/workflows/ci.yml                     §2-1
docs/runs/RUN_COMMON_RULES.md §0-5           환경 노트
docs/INFRA_DB_STRATEGY.md                    인프라 §1 · §3 · §5
docs/legal/HUMAN_INPUT_QUEUE.md              B-8 백업 복구 · H17 공개 사이트
docs/legal/KNOWN_PUBLICATION_EXPOSURE.md     "격리 밖 노출"
docs/legal/closure/CLOSURE_DPA.md            T-6 취약점 스캐닝 (도구는 여전히 없음 — 오늘은 1회 수동)
```
