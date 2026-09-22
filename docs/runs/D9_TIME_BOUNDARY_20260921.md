# D9 — CI 시간대 경계 테스트 Determinism (2026-09-21)

> 목표: 같은 commit + 같은 입력 + 실행 시각만 다름 = 항상 같은 결과.
> 브랜치 `fix/d9-time-boundary-determinism-20260921` (base `origin/main@ae61369`) · Draft PR wiselake/pig-os#5.
> 불변: PR #2·#3 수정 0 · main push 0 · 프로덕션 0 · 테스트 삭제/skip/xfail 0 · assert 완화 0 · CI TZ 변경 0.

## 1. 증상 (실측)

| PR #2 run | head | 실행(UTC) | KST | 결과 |
|---|---|---|---|---|
| 35371186151 | fe6e455 | 09-18 16:54 | 09-19 01:54 | **red** `test_future_presentation_row_ignored` `assert 10 == 30` (3.12·3.14) |
| 35394188042 | a06aa9d | 09-18 20:57 | 09-19 05:57 | red, 同 |
| 35410963895 | 85c6994 | 09-19 00:55 | 09-19 09:55 | **green** |
| 35422553240 | d5fd28d | 09-19 04:54 | 09-19 13:54 | green |
| 35541576981 | e30e64a | 09-20 22:24 | 09-21 07:24 | red, 同 |
| 35544144269 | 8ada6f3 | 09-20 23:19 | 09-21 08:19 | red, 同 |

fe6e455 → 8ada6f3 는 docs 커밋만 다르고 `api/` 는 동일하다. 결과를 가른 것은 실행 시각뿐.

## 2. Root cause

```
test:                 api/tests/integration/test_kpi_presentation_resolver.py
                        test_future_presentation_row_ignored (CI 에서 실패)
                        test_expired_presentation_row_ignored (거울상 — governance 가 host 보다 뒤일 때 실패)
                      api/tests/integration/test_us_template_lock.py::test_l6_future_and_expired_rows_are_ignored (같은 잠재 결함)
production function:  app/services/kpi_policy_resolver.py
                        resolve_kpi_presentation / resolve_kpi_policy / resolve_display_kpis
                        ref = ref or governance_today()
wall-clock dependency: 테스트가 "어제/내일" 을 date.today() (실행 호스트 로컬 날짜 = CI 러너 UTC) 로 만들고,
                      기준일(ref) 없이 리졸버를 호출 → 리졸버는 governance_today() (GOVERNANCE_TZ 기본 Asia/Seoul)
timezone boundary:    host(UTC) 날짜 ≠ governance(KST) 날짜 인 15:00–24:00 UTC (= 00:00–09:00 KST)
                      "내일" = host+1 = governance 오늘 → effective_from 행이 이미 유효 → 10 (기대 30)
```

**분류: A — 테스트만 잘못됨.** production 은 `ref` 를 받고, 기본값이 거버넌스 날짜인 이유가 모듈 docstring 에 2026-08-25 TZ 점검으로 명시돼 있다(농장 아님·호스트 아님). 테스트가 세 번째 시계(호스트)를 섞었다.

### 재현 (시간축을 실제로 바꿔서)

| 방법 | 결과 |
|---|---|
| 원본 테스트 그대로 + `governance_today` 를 host±1 로 대체(임시 하네스, 미커밋) | gov=host+1 → `test_future` **FAIL** · gov=host−1 → `test_expired` **FAIL** · gov=host → 둘 다 PASS |
| 몽키패치 없이 `GOVERNANCE_TIMEZONE=Etc/GMT+12` (UTC−12, 거버넌스 날짜가 호스트보다 하루 뒤) | `test_expired` **FAIL** `assert 10 == 30` (2026-09-21 10:46 KST 실행) |
| `GOVERNANCE_TIMEZONE=Asia/Seoul` (= 호스트) | PASS |

## 3. Canonical time semantics (코드로 확인)

| 시계 | 쓰는 곳 | 근거 |
|---|---|---|
| **거버넌스 날짜** `governance_today()` (GOVERNANCE_TZ, 기본 Asia/Seoul) | 정책·표현 **발효일 게이트** `effective_from ≤ ref ≤ effective_to` | `kpi_policy_resolver.py` docstring "기준일(ref)이 왜 서버 날짜인가" · `farm_time.py:91-103` |
| **농장 현지 날짜** `farm_today*` | 사용자에게 보이는 오늘·KPI as_of·미래일자 거부 | `farm_time.py` · `event_service.py:185` · `feed_service.py:57` |
| **명시적 as_of / ref** | KPI·트렌드·정책 계산의 canonical 입력 — SQL 에 바인드, CURRENT_DATE 안 읽음 | `kpi_service.get_trend` (as_of 전 구간 바인드) · `test_npd_as_of_determinism.py` |
| DB `CURRENT_DATE` | `CountryKpiPolicy.effective_from` **server_default** 만 | `kpi_policy.py:108` — §8 런타임 소견 |

→ 테스트 기대값은 위 어느 시계도 아닌 **테스트가 정한 고정 날짜**여야 한다.

## 4. 수정 (test-only)

| commit | 내용 |
|---|---|
| `4faec70` | 두 테스트 + L6: 모든 resolve 호출에 `ref` 명시, 날짜 고정(`2026-09-21`), 닫힌 구간 경계(effective_to 당일 유효) 단언 추가 |
| `85ccd99` | `test_time_boundary_determinism.py` 신설 (§5) |

production `fix` 커밋 없음 — 결함이 테스트에만 있었다.

## 5. Boundary matrix (실행 결과)

`test_time_boundary_determinism.py` — 시계 교체는 모듈 경계(`kpi_policy_resolver.governance_today`)에서만. 전역 datetime 패치·OS TZ·CI TZ 없음.

| 논리 실행 시각 (KST) | UTC | gov 날짜 | host(UTC) 날짜 | ① 고정 ref 결과 불변 | ② 기본 ref = gov |
|---|---|---|---|---|---|
| 2026-09-20 23:59:59 | 09-20 14:59:59 | 09-20 | 09-20 | PASS | PASS |
| 2026-09-21 00:00:00 (KST 자정) | 09-20 15:00:00 | 09-21 | **09-20** | PASS | PASS (호스트 기준이면 30, 실제 10) |
| 2026-09-21 08:59:59 | 09-20 23:59:59 | 09-21 | **09-20** | PASS | PASS |
| 2026-09-21 09:00:00 (UTC 자정) | 09-21 00:00:00 | 09-21 | 09-21 | PASS | PASS |
| 2026-09-21 23:59:59 | 09-21 14:59:59 | 09-21 | 09-21 | PASS | PASS |
| 2026-09-22 00:00:00 | 09-21 15:00:00 | 09-22 | **09-21** | PASS | PASS |
| 2026-10-01 00:00:00 (월말) | 09-30 15:00:00 | 10-01 | **09-30** | PASS | PASS |
| 2027-01-01 00:00:00 (연말) | 12-31 15:00:00 | 2027-01-01 | **2026-12-31** | PASS | PASS |
| + 닫힌 구간 양끝 | — | — | — | PASS | — |

**17 passed** (로컬, 2026-09-21 11:0x KST). 불변식: 같은 입력 + 같은 ref + 다른 실행 시각 → 같은 결과 / ref 생략 → 거버넌스 날짜, 호스트 날짜 아님.

## 6. G4 관계 — `G4_INDEPENDENT_OF_D9`

`test/trend-psy-frozen-as-of @ c17c5df` 는 `test_trend_psy_numerator.py` (KPI 트렌드, `get_trend(as_of=…)`, **농장** 시계) 에 고정 시나리오를 복원한 것. D9 는 `kpi_policy_resolver` (**거버넌스** 시계) 의 발효일 게이트 테스트다. 테스트·함수·시계가 모두 다르고 diff 가 겹치지 않는다. 같은 원칙(기준일은 테스트가 정한다)을 다른 위치에 적용한 것이며, G4 가 D9 를 해결하지 않고 D9 도 G4 를 대체하지 않는다. G4 코드는 D9 브랜치에 가져오지 않았다.

## 7. Full search — 같은 패턴 분류

| 등급 | 위치 | 판정 |
|---|---|---|
| **P0** | `test_kpi_presentation_resolver.py` expired/future · `test_us_template_lock.py` L6 | 수정 (§4) |
| P1 | `test_trend_psy_numerator.py` (PR #3 `751aad5` 판: `date.today()` 로 당월 산정, `get_trend` 기본 as_of = 농장(Asia/Seoul) 오늘) | 월말 15:00–24:00 UTC 에 host 월 ≠ farm 월이나 `months=3` 창 안이라 결과 동일. 잠재. G4 `c17c5df` 가 고정 시나리오 추가 |
| P1 | `test_sow_mortality_culling.py`(as_of 명시 전달) · `test_task_service.py`·`test_rule_detection_pipeline.py`·`test_npd_culled_and_dashboard_fr.py`·`test_dashboard_metrics_map.py` (상대 fixture, ≥30일 여유) | 실행일 상대 fixture. 호스트/농장 날짜 ±1일 차이가 결과를 바꾸지 않는 여유. 손대지 않음 |
| P1 (런타임) | `CountryKpiPolicy.effective_from server_default=current_date()` — **DB 시계**. 기본값 없이 INSERT 된 정책 행의 발효일이 DB 세션 타임존 날짜로 찍힌다. 거버넌스 TZ 가 DB TZ 보다 **서쪽**이면 그날 하루 행이 안 보인다. 현 구성(DB UTC · 거버넌스 Asia/Seoul)에서는 DB 날짜 ≤ 거버넌스 날짜라 안전. `GOVERNANCE_TIMEZONE=Etc/GMT+12` 실험에서 8개 테스트가 이 경로로 깨졌다 | **STOP 기록** — 고치려면 server_default 변경(마이그레이션) 또는 seed 경로가 거버넌스 날짜를 명시 INSERT. 정책 결정 필요. 프로덕션 DB 타임존은 미확인(접근 금지) |
| P2 | `test_feed_records.py` future=+2일 (스키마 +1일 허용) · `test_farm_timezone.py` (타임존 자체 검증) · sync/token/log 의 `datetime.now` | 정당한 current-time 사용 |
| 프론트 | `src/tests` 에 `new Date()`/`Date.now()` 0건 (node_modules 제외) | 해당 없음 |

## 8. 검증

| 항목 | 결과 |
|---|---|
| targeted (3 파일) × `GOVERNANCE_TIMEZONE` ∈ {Asia/Seoul, Etc/GMT+12, Pacific/Kiritimati} | 수정 전 Etc/GMT+12 에서 1 FAIL → 수정 후 전부 PASS |
| backend full — D9 브랜치 (base main `ae61369`) | 1323 passed · **3 failed — 전부 main 기존 결함, D9 무관** (§9) |
| backend full — D9 두 커밋을 PR #2 head `8ada6f3` 위에 임시 cherry-pick (로컬 tmp 브랜치, 검증 후 삭제) | **1547 passed · 1 skipped · 10 xfailed** |
| ruff | clean |
| alembic heads | 단일 `f3c6a8d0b2e4` · 마이그레이션 0 · DB 변경 0 |
| frontend | 결함 무관(프론트 테스트에 wall-clock 0건) — 미실행 |

## 9. PR 영향

**PR #3 `d088e73` (FROZEN)**
- 09-18 01:05 UTC green run(35293878390) 은 창 밖 실행 — 유효하나 **재실행 시 00:00–09:00 KST 창에서는 같은 테스트로 빨강**. 실제로는 그보다 앞서 **#4 merge(ae61369) 로 base 가 움직여 `CONFLICTING/DIRTY`** 가 됐다 (`api/content/legal/public_privacy.*` 를 #3 와 #4 가 함께 수정). D9 와 무관하게 base 갱신(충돌 해소)이 필요 — **PR #3 변경 = 결재 사항, 실행 안 함**.
- D9 는 hotfix 의 필수 선행이 아니다. 재실행을 09:00–24:00 KST 에 하면 D9 없이도 초록. 다만 base 갱신 시점에 D9 가 main 에 있으면 창 제약이 사라진다.

**PR #2 `8ada6f3`** (브리프의 `d9eeda4` 는 코드 head; 그 뒤 docs 커밋으로 현재 head 는 8ada6f3)
- 최근 4개 run 중 3개 red 가 전부 이 원인. §8 cherry-pick 검증으로 D9 두 커밋을 얹으면 1547/0. **PR #2 에 직접 얹지 않았다**(지시).

**main**
- `ci.yml` 이 `pull_request: branches: [development]` + unit 만 → **D9 Draft PR #5 는 CI 가 돌지 않는다**. ae61369 의 "success" run 35546332891 은 Pages(Jekyll) 워크플로다. 즉 main 의 초록은 테스트 근거가 아니다.
- main 로컬 full suite 3 failed: `test_runtime_copy_matches_canonical[ko,en]` (#4 가 런타임 사본만 고치고 publish_candidate 는 안 고침 → drift. PR #3 가 이 테스트를 대체) · `test_trend_psy_uses_weaned_count_and_monthly_inventory` (2026-06 하드코딩, PR #3 `751aad5`). **main 이 이미 빨강**이다 — D9 이전부터.

## 10. 권장 merge 순서 (제안만)

```
① PR #3 base 갱신(충돌 해소, 결재)  → 09:00–24:00 KST 에 CI → merge → 배포·verify
② D9 (#5) 를 PR #2 또는 main 에 — main 에 PR #2 의 ci.yml 이 들어온 뒤라야 CI 근거가 생긴다
③ G4 (test/trend-psy-frozen-as-of) 별도
④ §7 P1(런타임) server_default 결정
```

## 11. 상태

```
ROOT_CAUSE_IDENTIFIED        YES
LOCAL_BOUNDARY_VERIFIED      YES  (17/17 + 3 TZ 변주)
FULL_SUITE_GREEN             YES on PR#2-head+D9 (1547/0) · NO on main-base (main 기존 3건, D9 무관)
CI_24H_DETERMINISM           DESIGNED_AND_LOCALLY_PROVEN  (main 에 실CI 없음 · PR #2/#3 워크플로에서만 증명 가능)
```
