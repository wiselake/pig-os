# D-19 — Threshold Source 감사 (v1.4 · current HEAD 재감사)

```
D19_spec_version        1.4   docs/runs/D19_THRESHOLD_SOURCE_AUDIT_RUN.md (c2f7915)
D19_audit_target_commit c2f7915
D19_audit_date          2026-08-28
D13_reference_version   RUN_PROMPT_D13_canonical_formula_audit.md v1.4
D13_reference_commit    70a56a9 (run spec) · a27afd8 (SPEC) · 0bc8bc9 (REAUDIT)
machine                 bjh
mode                    READ-ONLY — 코드 정적분석 + 런타임 registry 열거 + 프로덕션 SELECT
prior run               docs/kpi/D19_THRESHOLD_SOURCE_AUDIT.md
                        prior_status = HISTORICAL_EVIDENCE · prior_reusable = NO
                        → 숫자 복사 0. 전 항목 재실측.
```

> **이 문서는 1차 감사를 대체하지 않는다.** 1차는 그대로 두고, 이 문서가 current HEAD 의 사실이다.

---

## 0. Baseline

| 항목 | 값 |
|---|---|
| `working_tree_before` | 비어 있음 (clean) |
| `working_tree_after` | 비어 있음 (clean) — 산출물은 이 파일 1건 |
| `flag_states_before` | `use_governance_benchmarks = False` (`config.py:77` 기본값. 로컬 `api/.env`·프로덕션 `~/pigos/.env` 어디에도 키 없음) |
| `flag_states_after` | 동일 — 변경 0 |
| DB write count | **0** — 실행 쿼리 전부 `SELECT` / `information_schema` / `pg_get_*def` |
| 프로덕션 | `52.78.65.6` PostgreSQL 17 `:5434` db=`pigos` (SSH, `sudo -u postgres psql`) |
| 룰 열거 방식 | `RuleRegistry.all()` **런타임 열거** — grep 추정 아님 |

---

## 1. STEP 1 — Threshold source discovery

> 스펙 §5: "기확인 5종을 완전한 목록으로 확정하지 말 것. **6번째 소스가 있다는 전제로 탐색한다.**"

**결과: 6번째가 아니라 8번째까지 있었다.** 아래 13종이 current HEAD 의 판정상수 소스다.

### 1-1. KPI 카드 severity 에 직접 관여하는 소스 (5종)

| # | 소스 | 위치 | 프로덕션 실적재 | 발화 |
|---|---|---|---|---|
| S1 | `rule_configs` | `rule_config_service.load_rule_configs` | **0행** | 없음 |
| S2 | `operational_defaults` | `threshold_resolver.gov_resolve_thresholds` | **29행 · 전부 `origin='code_default'` · `scope=global`** | **DORMANT** (flag OFF) |
| S3 | 룰 내 인라인 코드 상수 | `_common.resolve(ctx, rule_id, kpi, default_w, default_c)` 호출부 리터럴 | 코드 | **LIVE** |
| S4 | `default_metric_values` | DB 함수 `effective_metric_values(farm, region, market)` | **87행** (farm 2 · BR 9 · CN 7 · KR 27 · US 11 · VN 8 · SYSTEM 23) | **LIVE** |
| S5 | 로더 주입 상수 | `kpi_service._all_benchmarks:337-341` — `FARROWING_RATE` 없으면 `85.0/80.0` 주입, `PRE_WEANING_MORTALITY → PWMR` 별칭 | 코드 | **LIVE** |

### 1-2. ★ 신규 발견 — 1차 감사가 잡지 못한 소스 (8종)

| # | 소스 | 위치 | 성격 | 발화 |
|---|---|---|---|---|
| **S6** | `benchmarks` 테이블 + `benchmark_thresholds.severity_for()` | `benchmark_service.evaluate_severity` ← `routers/admin/benchmarks.py:78` | **완전히 별개의 severity 메커니즘.** `warning_min/max`·`critical_min/max`·`direction ∈ {higher_better, lower_better, range_target}` + `can_fire()` 게이트 | **ADMIN_ONLY** — 호출자가 admin 라우터 1곳뿐 |
| **S7** | `farm_config` → `AlertThresholds` | `alert_service.py:59,153-167` | `gilt_first_mating_age=240` 등 **운영 알림 임계.** farm_config 키 → 코드 기본. `notification_service:148,160` 이 이 판정에 `severity="WARNING"` 을 **하드코딩** | **LIVE** |
| **S8** | 웹 프론트 자체 임계 | `src/lib/kpi/status.ts` — `psyTier ≥28/≥22` · `npdTier ≤35/≤50` · `farrowingRateTier ≥90/≥80` | 프론트 하드코딩 판정 | **CONDITIONAL** — §4-3 |
| **S9** | 스코어카드 밴드 | `scorecard_service.py:79-80` — `≥90 TOP / ≥70 GOOD / ≥50 FAIR / else LOW` | 무가입 공개 스코어카드 | **LIVE** |
| **S10** | 종합등급 카운트 임계 | `rules/composite.py:24` — `crit>=1 or warn>=3 → RED`, `warn>=1 → YELLOW` | **개수 임계** (KPI 수치 임계 아님) | **LIVE** |
| **S11** | 질병 범주 임계 | `rules/disease.py:12-14` — `_CRITICAL_STATUSES`·`_WARNING_STATUSES`·`_FREE_STATUSES` | **범주형 임계** | LIVE (`ctx.extra` 필요) |
| **S12** | PSY 절대등급 밴드 | `rules/base.py:38-42` — `PSY_GRADES 28/24/20` | `Finding.grade` (severity 아님) | **LIVE** |
| **S13** | DB 뷰 상수 | `v_sow_npd` — `LEAST(60, …)`, `weaning_date <= CURRENT_DATE-60 → 60` | **WEI 60일 캡** (값 상수, severity 아님) | **LIVE** |

**DB trigger**: `default_metric_values`·`operational_defaults`·`rule_configs` 위 트리거 **0건**.
**DB view**: `v_sow_npd` 1건뿐. **DB function**: `effective_metric_values` 1건뿐.

---

## 2. STEP 2 — Resolution order

### 2-1. ★ 단일 order 가 아니다 — **네 개가 공존한다**

```
① _common.resolve()          (flag OFF · 현재 운영)
     rule_configs → ctx.benchmarks(=S4 DMV) → 호출부 코드 상수

② gov_resolve_thresholds()   (flag ON · 현재 미발화)
     rule_configs → operational_defaults → 호출부 코드 상수
     ★ DMV 를 threshold source 에서 제외한다 (docstring §14.6)

③ effective_metric_values()  (DB 함수 · ①의 두 번째 단계 내부)
     farm → region → market → system
     ※ market scope 는 프로덕션 0행

④ insight_service._load_benchmark()
     farm > region > system  — ③과 "동일 체인" 이라고 주석하지만 별도 구현
```

### 2-2. 판정

```
resolution_order = DETERMINED_UNDER_CURRENT_FLAG
```

**`AMBIGUOUS_ORDER` 는 아니다.** flag 상태(`False`)가 관측 가능하므로 현재 live order 는
①+③ 으로 **하나로 특정된다.** 추정하지 않았다.

### 2-3. ★ 그러나 flag 는 no-op 이 아니다 — **권위 테이블이 통째로 바뀐다**

`operational_defaults`(S2) 와 현행 DMV(S4) 를 실측 대조했다.

| rule_id | ② opdef (flag ON) | ① 현행 DMV (flag OFF) | 변화 |
|---|---|---|---|
| `stillborn.rate_high` | 8 / 12 | **BR 8.20** / 12 | BR 이 **8.20 → 8.00 으로 조여진다** |
| `pwmr.high` | 15 / 20 | **US 14 / 18** | 느슨해진다 |
| `sow_mortality.high` | 8 / 12 | **US 12 / 15** | 조여진다 |
| `rts.rate_high` | 15 / 25 | **US 10 / 15** | 느슨해진다 |
| `wsi.overdue` | 10 / 14 | **US 7 / 9** | 느슨해진다 |
| `born_alive.low` | 11 / 10 | **US 13 / 12** | 느슨해진다 |
| `weaned.low` | 10 / 9 | **US 11 / 10** | 느슨해진다 |

★ **boolean 하나가 국가별 임계를 글로벌 코드 기본으로 갈아치운다.** 그리고 그 글로벌 값은
`origin='code_default'` **29행 전부** 다 — 즉 flag ON 은 **국가정책을 끄고 코드 기본으로
되돌리는 스위치**다. 스펙이 이 flag 변경을 금지한 이유가 실측으로 확인됐다.

---

## 3. STEP 3 — 룰 전수 재실측 (Path A / Path B 양방향)

### 3-1. Path A — rule 정의 → threshold source

`RuleRegistry.all()` **런타임 열거 = 40룰, rule_id 중복 0.**

| 분류 | 수 | 메커니즘 |
|---|---|---|
| **A-resolve** | **29** | `_common.resolve()` → ① 체인 → `sev_above/sev_below` 또는 인라인 비교 |
| **A-bench** | **3** | `base.py::_severity_from_bench(value, ctx.benchmarks[kpi], direction)` — `npd.overdue` · `psy.below_target` · `farrowing.low_rate` |
| **A-inline** | **8** | resolver 미경유 |

**A-inline 8 의 내역 — 1차의 "no-threshold 8" 은 부정확하다:**

| rule_id | 실제 | provenance |
|---|---|---|
| `farm.health_class` | **개수 임계 있음** (`crit>=1` / `warn>=3`) | **CODE_DEFAULT** (non-KPI) |
| `disease.endemic_risk` | **범주 임계 있음** (status 집합 3종) | **CODE_DEFAULT** (categorical) |
| `inventory.zero` | 존재판정 (`active == 0`) | NO_THRESHOLD |
| `farm.weakest_kpi` | INFO 만. 선택이지 판정 아님 | NO_THRESHOLD |
| `loss.preweaning_mortality` | INFO 만 | NO_THRESHOLD |
| `loss.pregnancy_accident` | INFO 만 | NO_THRESHOLD |
| `loss.npd` | INFO 만 | NO_THRESHOLD |
| `loss.sow_culling` | INFO 만 · **KR 전용 게이트** (`country != "KR" → []`) | NO_THRESHOLD |

```
정정:  no-threshold 8  →  NO_THRESHOLD 6 + CODE_DEFAULT(non-KPI) 2
```

> 1차의 `29 / 3 / 8` 이라는 **숫자는 우연히 같지만 8의 내용이 다르다.** 숫자만 대조했다면
> 이 차이를 놓쳤을 것이다.

### 3-2. Path B — severity 산출지점 → 소유 rule (역방향)

`app/` 전수 + `src/` 프론트 전수. **17개 산출지점.**

| # | 산출지점 | 임계 소스 | 소유 rule | 도달성 |
|---|---|---|---|---|
| B1 | `base.py::_severity_from_bench` | S4 | 3 rules | LIVE |
| B2 | `_common.resolve` + `sev_above/below` | S3+S4 | 29 rules | LIVE |
| B3 | `gov_resolve_thresholds` | S2 | 동일 29 rules | **DORMANT** |
| B4 | `composite.py::_farm_health_class` | S10 | `farm.health_class` | LIVE |
| B5 | `disease.py::_disease_endemic_risk` | S11 | `disease.endemic_risk` | LIVE |
| B6 | `base.py::_inventory_zero` | — | `inventory.zero` | LIVE |
| B7 | `loss.py` × 4 | — | 4 loss rules | LIVE |
| B8 | `composite.py::_farm_weakest_kpi` | — | `farm.weakest_kpi` | LIVE |
| B9 | `insight_service._evaluate` | S4 (자체 로더 ④) | **없음** ← orphan | **LIVE** |
| B10 | `benchmark_service.evaluate_severity` | S6 | **없음** ← orphan | ADMIN_ONLY |
| B11 | `kpi_status_assembler.assemble_kpi_status` | 없음 (변환 전용) | rule findings 소비 | LIVE |
| B12 | `notification_service:148,160` `severity="WARNING"` | S7 | **없음** ← orphan | **LIVE** |
| B13 | `report_service:1054-1169` 데이터정합성 CRITICAL/WARNING | 구조 판정 | **없음** ← orphan | LIVE |
| B14 | `scorecard_service:79-80` 밴드 | S9 | **없음** ← orphan | LIVE (공개) |
| B15 | `src/lib/kpi/status.ts` tier 함수 3종 | S8 | **없음** ← orphan | **CONDITIONAL** |
| B16 | `src/app/(app)/page.tsx:199` `quality>=66/33` | 프론트 상수 | **없음** ← orphan | LIVE (데이터품질, KPI 아님) |
| B17 | `base.py::psy_grade` | S12 | `psy.below_target` 에 부착 | LIVE (grade) |

### 3-3. ★ A ∩ B 교차대조

```
A → B    40룰 전부 B 에 존재.  B1(3)+B2(29)+B4(1)+B5(1)+B6(1)+B7(4)+B8(1) = 40  ✓
         A ∖ B = 0
B → A    B3·B11 은 A 의 재표현. 나머지 orphan 7건:
         B9 · B10 · B12 · B13 · B14 · B15 · B16
         B ∖ A = 7  (전부 아래 사유 기록)
```

**orphan severity path 7건 사유**

| # | 왜 rule 이 없는가 |
|---|---|
| B9 | 이벤트 입력 직후 인사이트. `metric_code` 단위로 동작하며 RuleRegistry 를 거치지 않는다. **DMV 를 직접 읽어 자체 severity 를 낸다** — 룰엔진과 병렬 판정자 |
| B10 | 관리자 진단 엔드포인트. 제품 화면 경로 아님 |
| B12 | 과기한/도태 알림. 판정 근거가 KPI 가 아니라 `farm_config` 일정값이라 룰 도메인 밖 |
| B13 | 데이터 정합성 이슈. KPI severity 와 어휘만 같고 도메인이 다르다 |
| B14 | 무가입 공개 스코어카드. 인증 전 경로 |
| B15 | 백엔드 `kpi_status` 부재 시 폴백 (ADR-KPI-08 Phase 3). 제거 예정(Phase 4) |
| B16 | KPI 가 아니라 데이터 품질 % 색상 |

### 3-4. ★ orphan **finding rule_id** — 레지스트리 밖 id 가 발화한다

```
psy.no_data                       base.py:105  — 등록 안 됨. 레지스트리 40 에 없다
disease.{code}.{status}           disease.py:66 — 런타임 생성. 등록된 것은
                                  disease.endemic_risk 하나뿐
```

이 id 들이 `Finding.rule_id` → `Alert.rule_id` → `notification.alert_type` 까지 흘러간다.
**`rule_id` 로 임계를 조회하는 S1·S2 경로에서는 영구히 매칭되지 않는다.**

### 3-5. 전수 완료 기준 (스펙 §7-3)

```
[x] 모든 rule definition 이 A 에 포함      RuleRegistry.all() 런타임 열거 40
[x] 모든 severity output path 가 B 에 포함  app/ 전수 + src/ 전수, 17건
[x] A ∖ B 설명 완료                        0건
[x] B ∖ A 설명 완료                        7건 · §3-3 표
[x] no-threshold rule 설명 완료            6건 · §3-1 표 (+ CODE_DEFAULT 2 분리)
[x] helper/indirect resolver 관통 완료     _common.resolve → gov_resolve_thresholds,
                                           effective_metric_values DB 함수,
                                           insight_service 자체 로더
[x] A ∩ B 교차대조 완료                    §3-3
[x] orphan rule 0                          A ∖ B = 0
[x] orphan severity path 사유 기록          7건 전부
```

```
rule_count            = 40
rule_count_confidence = CONFIRMED
```

★ 단, **`rule_count` 는 레지스트리 기준이다.** 발화하는 `finding.rule_id` 의 모집단은
40 보다 크다(§3-4). 이 둘은 다른 집합이며 **D-21 의 identity model 입력**이다.

---

## 4. Provenance

### 4-1. 집계

| provenance | 수 | 근거 |
|---|---|---|
| **APPROVED_POLICY** | **0** | 아래 §4-2 |
| **UNATTRIBUTED** | DMV 임계 68행 중 `threshold_basis` 있는 것 12행 뿐 → **56행이 근거 미상** | 실측 |
| **TENANT_CONFIG** | **유효 0** (행은 2건) | §4-4 |
| **CODE_DEFAULT** | 인라인 29 × 2 + `operational_defaults` 29행(전부 `origin='code_default'`) + S5·S8·S9·S10·S11·S12 | 실측 |
| **BENCHMARK_DERIVED** | 3 (A-bench 룰) | §3-1 |
| **NO_THRESHOLD** | 6 | §3-1 |

### 4-2. `APPROVED_POLICY = 0` — 이것이 정상 결과다

```
operational_defaults.origin  →  29행 전부 'code_default'.  APPROVED 0.
default_metric_values        →  87행 중 threshold_basis 12행.
                                그중 임계와 정합하는 것은 SYSTEM STILLBORN_RATE 1건
                                (basis = investigate_gt7_normal_5_10)
rule_configs                 →  0행
```

`country_kpi_policy` 에 `decision_status='APPROVED'` 28행(BR 14 + GLOBAL 14)이 있지만
**이 테이블은 threshold 를 담지 않는다** — 컬럼은 `compute_enabled`·`display_role`·
`rule_enabled`·`benchmark_exposure` 등 **정책 스위치**이고, 수치 임계 컬럼이 없다.
`kpi_policy_resolver` 도 임계를 읽지 않는다.

→ **결재된 임계는 시스템에 0건이다.** 스펙 §19 대로 실패로 처리하지 않는다.

### 4-3. ★ `source_ref` 는 APPROVED 근거가 아니다 — v1.3 관찰 재확인

```
scope   code   metric          warn  crit  source_ref                   threshold_basis
region  BR     STILLBORN_RATE  8.20  12    Agriness2024                 (없음)
region  KR     STILLBORN_RATE  8.00  12    PigPlan:PIGLET_DEATH_KPI_V1  (없음)
region  US     STILLBORN_RATE  8.00  12    PigCHAMP2023                 (없음)
system  SYSTEM STILLBORN_RATE  8.00  12    PigCHAMP2023/NADIS/Le2022    investigate_gt7_normal_5_10
```

v1.3 이 기술한 패턴이 **그대로 재현됐다**: 서로 다른 출처(PigPlan / PigCHAMP / 3자 합성)가
소수점 둘째 자리까지 `8.00` 으로 동일하고, `threshold_basis` 는 SYSTEM 한 행에만 있다.
BR `8.20` 만 다르다. → **사후 귀속 가능성을 배제할 수 없으므로 전부 `UNATTRIBUTED`.**

### 4-4. TENANT_CONFIG — 행은 있으나 유효값 0

```
scope_type  scope_code                            metric_code  warn  crit  source_ref
farm        c24f7ca5-…-ea5826d204ec (KR, native)  ZZZ          NULL  NULL  farm_override
farm        c24f7ca5-…-ea5826d204ec (KR, native)  ZZZ_DUMMY    NULL  NULL  farm_override
```

**메트릭 코드가 `ZZZ`·`ZZZ_DUMMY` 이고 임계가 전부 NULL.** 실 테넌트 설정이 아니라
**프로덕션에 남은 테스트 잔여물**이다.

```
tenant_config_rows      = 2
tenant_config_effective = 0
finding                 = PRODUCTION_TEST_RESIDUE   (신규 · 별도 처리 필요)
```

단, **기능으로서의 tenant override 는 살아 있다** — `routers/base/thresholds.py` 가
`set_override`/`clear_override` 를 노출하고 `effective_metric_values` 가 `farm` 을 최우선으로
읽는다. 즉 **농장이 자기 임계를 덮어쓸 수 있고, 그 경로에 결재 게이트가 없다.**

---

## 5. Formula linkage (스펙 §12)

D-13 canonical 현재 상태(`CANONICAL_FORMULA_SPEC_REAUDIT.md` §5-1, `0bc8bc9`)를 사용했다.
**prior run 상태 복사 0.**

| KPI | `formula_status` (D-13) | threshold source | `D19_migration_status` | `migration_blocker` |
|---|---|---|---|---|
| **PSY** | CONFIRMED | S4 (US 26/23 · `psy.below_target` A-bench) | **READY** | NONE |
| **NPD** | CONFIRMED | S4 (US 38/53 · `npd.overdue` A-bench) | **READY** | NONE |
| **FARROWING_RATE** | **AMBIGUOUS** — 산식 4개, ②③ LIVE | S4 (US 82/78) + **S5 코드 폴백 85/80** | **BLOCKED** | `BLOCKED_BY_CANONICAL_AMBIGUITY` |
| **사산 계열** | **AMBIGUOUS** — 같은 이름 2산식 | S4 (BR 8.20 · KR/US/SYSTEM 8.00) | **BLOCKED** | `BLOCKED_BY_P0_2_DECISION` |
| **PWM** | **AMBIGUOUS** — 분모 3종 | S4 `PRE_WEANING_MORTALITY` → **S5 별칭으로 `PWMR` 키 연결** (US 14/18) | **BLOCKED** | `BLOCKED_BY_CODE_ALIGNMENT` |

### 5-1. ★ FARROWING_RATE 는 산식만 모호한 게 아니다 — 임계도 이중이다

```
S4  DMV region=US   FARROWING_RATE  82 / 78
S5  코드 폴백        kpi_service.py:337-341  → 없으면 85 / 80 주입
```

**국가행이 있으면 82/78, 없으면 85/80.** 그리고 어느 산식(코호트 ① / 동기간 ② / 동월 ③)의
값에 이 임계를 적용하는지가 canonical 에서 미정이다. → 임계·산식 **양쪽이 모호**하다.

### 5-2. PWM 별칭 — 이름이 다른 두 키가 같은 행을 가리킨다

```
DMV metric_code = PRE_WEANING_MORTALITY
룰 pwmr.high    는 ctx.benchmarks["PWMR"] 을 읽는다
kpi_service:342-343 이 별칭으로 연결
```

정책 선택이 아니라 **코드 정렬 문제**다. 결재 대기열에 넣지 않는다(스펙 §10).

---

## 6. US Activation (스펙 §13)

> ★ 과거 3회 오류난 지점 — `country_kpi_policy` 부재로부터 DMV 부재를 추론하지 않았다.
> **실측했다.**

```
country_kpi_policy      US = 0행       (APPROVED 는 BR 14 + GLOBAL 14 뿐)
country_kpi_presentation US = 0행       (BR 3 + GLOBAL 4 뿐)
default_metric_values   US = 11행 ★ 존재한다
```

### 6-1. 프로덕션 US 임계 실측 (11행 전량)

| metric_code | warning | critical | direction | source_ref | threshold_basis |
|---|---|---|---|---|---|
| PSY | 26.00 | 23.00 | below | PigCHAMP2024 | — |
| NPD | 38.00 | 53.00 | above | **(없음)** | — |
| FARROWING_RATE | 82.00 | 78.00 | below | PorkCheckoff2024 | — |
| STILLBORN_RATE | 8.00 | 12.00 | above | PigCHAMP2023 | — |
| PRE_WEANING_MORTALITY | 14.00 | 18.00 | above | PorkCheckoff2024 | — |
| BORN_ALIVE | 13.00 | 12.00 | below | PorkCheckoff2024 | — |
| WEANED_COUNT | 11.00 | 10.00 | below | PorkCheckoff2024 | — |
| SOW_MORTALITY | 12.00 | 15.00 | above | PorkCheckoff2024 | — |
| WSI | 7.00 | 9.00 | above | PorkCheckoff2024 | — |
| RTS_RATE | 10.00 | 15.00 | above | PigCHAMP2023 | — |
| MARKET_PRICE_HEAD | — | — | below | USDA lean hog 2024 | market_reference |

### 6-2. 판정

```
발화하는 threshold        S4 (DMV region=US) 10종 + S3 코드 상수(DMV 미보유 룰)
                          + S5 폴백(FARROWING_RATE 국가행이 있으므로 이번엔 미발동)
APPROVED evidence         0 — threshold_basis 전무 (MARKET_PRICE_HEAD 제외, 임계 아님)
provenance                UNATTRIBUTED (source_ref 만 있음)
benchmark 가 severity 에 사용되는가
                          YES — PSY·NPD·FARROWING_RATE 3종은 A-bench 라
                          DMV 의 warning/critical 을 그대로 severity 로 쓴다
CODE_DEFAULT 발화 여부      YES — DMV 에 없는 룰(예: batch.aiao_detect,
                          conception.rate_low 등)은 인라인 상수로 발화
US_ACTIVATION_RESULT      THRESHOLDS_PRESENT_BUT_UNATTRIBUTED
```

### 6-3. 모집단 (스펙 §11)

```
INTERNAL_REFERENCE (pigplan_migration)  42농장 · US 10농장 · 최근365일 분만 16,395건
LIVE_CUSTOMER      (native_signup)      31농장 등록 · US 9농장
                                        ★ 그중 분만 데이터 보유 = 4농장
                                        ★ 최근 365일 분만 = CN 1농장 1건 · KR 2농장 81건
                                        ★ US native_signup 농장의 최근365일 분만 = 0건
```

> ★ **1차의 "실고객 2농장 · 최근365일 분만 3건" 은 현재 수치가 아니다.**
> HEAD 기준 3농장 · 82건이다. prior 숫자를 복사하지 않아서 잡혔다.
>
> ★ **미국 실고객 발화 실적은 아직 0이다.** US 임계 11행은 전부
> `INTERNAL_REFERENCE` 모집단에서만 발화하고 있다. 합산하지 않았다.

---

## 7. BR / G3 (스펙 §14) — backend 판정 경로

Mobile rendering 은 범위 밖 (`docs/PLATFORM_PARITY.md` 소관).

### 7-1. benchmark unavailable

| 경로 | 동작 |
|---|---|
| A-bench 3룰 | `_severity_from_bench`: `warning is None → return None` → **미발화(fail-closed)** ✓ |
| A-resolve 29룰 | `_common.resolve`: 벤치마크 None → **인라인 코드 상수로 폴백(fail-open)** ✗ |
| `FARROWING_RATE` | S5 가 **85/80 을 주입** → 벤치마크가 없어도 발화한다 ✗ |
| `kpi_status_assembler` | rule 없음 → `insufficient/no_policy`, 값 없음 → `insufficient/no_data` ✓ |

★ **backend 는 한 가지로 동작하지 않는다.** A-bench 는 침묵하고 A-resolve 는 코드 기본으로
계속 판정한다. G3 ③("근거 없으면 판정하지 않는다")를 만족하는 것은 **3룰뿐**이다.

### 7-2. threshold unapproved

`APPROVED_POLICY = 0` 이므로 **현재 발화 중인 모든 severity 가 unapproved 임계 기반**이다.
승인 여부를 확인하는 게이트가 severity 경로에 **존재하지 않는다** —
`can_fire()`(S6)가 그 게이트지만 **admin 라우터에서만 호출된다**(§1-2 B10).

★ **품질 게이트는 구현돼 있으나 제품 경로에 연결돼 있지 않다.** 이것이 D-0(벤치마크
동치검증 부재)과 같은 뿌리다.

### 7-3. formula ambiguous

`FARROWING_RATE`·사산 계열·PWM 3종은 **산식이 정해지기 전에 이미 임계로 판정하고 있다.**
backend 에 "산식 미확정이므로 판정 보류" 상태가 없다 — `formula_status` 를 읽는 코드가 0건.

### 7-4. BR 실측

```
country_kpi_policy   BR 14행 전부 APPROVED       ← 유일한 파일럿
default_metric_values BR 9행
  STILLBORN_RATE 8.20 / 12   source_ref=Agriness2024   threshold_basis=(없음)
benchmarks 테이블      BR 0행   (KR 15 · US 3 뿐)
```

★ **BR 은 정책은 APPROVED 인데 임계는 UNATTRIBUTED 다.** 정책 결재와 임계 결재가
서로 다른 테이블이고, 후자에는 결재 개념 자체가 없다.

---

## 8. Versioning Design Input V-1 ~ V-6

> 스펙 §15 고지: v1.3 본문 부재로 V-1~V-5 는 v1.4 신규 정의. **V-6 만 v1.3 원문.**

### V-1 — code-default ↔ rule mapping

| 의존 형태 | rule 수 |
|---|---|
| 인라인 코드 상수가 **최종 폴백** | 29 (A-resolve 전부) |
| 인라인 코드 상수가 **유일 소스** | 2 (`farm.health_class` · `disease.endemic_risk`) |
| `operational_defaults`(전부 `code_default`)가 소스 | 29 — **flag ON 시에만** |
| 코드 상수 없음 | 3 (A-bench) + 6 (NO_THRESHOLD) |

★ **코드 배포 없이 임계를 바꿀 수 없는 룰이 최소 2개, 폴백까지 세면 31개다.**

### V-2 — current threshold identity observation

지금 threshold 를 식별하는 키가 **경로마다 다르다.**

```
S1 rule_configs          key = rule_id
S2 operational_defaults  key = (rule_id, country_code, scope)
S4 default_metric_values key = (scope_type, scope_code, metric_code)
S6 benchmarks            key = (country_code, kpi_code) + benchmark_status/comparison_status
S7 farm_config           key = (farm_id, config_key)
```

★ **`rule_id` 축과 `metric_code` 축이 섞여 있다.** `pwmr.high`(rule_id) ↔
`PRE_WEANING_MORTALITY`(metric_code) ↔ `PWMR`(룰이 읽는 키) ↔ `prewean_mortality`
(governance kpi_code) — **한 지표에 이름이 4개**다. identity model 확정은 **D-21 소관**.

### V-3 — historical reproducibility

| 항목 | 존재 |
|---|---|
| formula version | **없음** — `formula_id`/`formula_version` 을 저장하는 컬럼이 어디에도 없다 |
| threshold version | **없음** — DMV·operational_defaults 에 버전/유효기간 컬럼 없음 |
| rule version | **없음** — `Rule` 데이터클래스에 version 필드 없음 |
| evidence version | **없음** — `source_ref` 는 자유 문자열 |
| `as_of` | **부분** — `RuleContext.as_of` 는 있으나 `build_herd_kpis` 가 wall-clock (D-13 §7-1) |
| historical source data state | **없음** — `kpi_snapshots` 0행 |

```
V3_RESULT = NOT_REPRODUCIBLE
```

**과거 severity 를 재현할 수 없다.** 실패가 아니라 사실이다(스펙 §19).
현재 severity 계산은 가능하다 — 둘은 다른 질문이다.

### V-4 — migration dependency / blocker

```
READY                            PSY · NPD
BLOCKED_BY_CANONICAL_AMBIGUITY   FARROWING_RATE
BLOCKED_BY_P0_2_DECISION         사산 계열
BLOCKED_BY_CODE_ALIGNMENT        PWM
BLOCKED_BY_P0_1B_TRACE           0건 — 미판독 본문 없음
```

승격 자체의 선행조건(전 지표 공통):

```
1. threshold 에 결재 축이 없다        → 승인 개념을 만들어야 APPROVED_POLICY 가 가능
2. flag 가 권위 테이블을 갈아치운다   → §2-3. 승격 전에 이 스위치를 정리해야 한다
3. tenant override 에 게이트가 없다   → §4-4
```

### V-5 — evidence linkage state

```
DMV 87행
  ├ source_ref 있음        74
  ├ threshold_basis 있음   12
  └ 임계 보유              68
       └ 그중 basis 있음    1  (SYSTEM STILLBORN_RATE)

EVIDENCE_LINKAGE = SOURCE_REF_ONLY
```

`source_ref` 는 문자열이고 evidence 문서와 **FK 도 URI 도 아니다.** 대조 불가.

### V-6 — snapshot versioning (v1.3 원문 요구)

```
kpi_snapshots 컬럼
  id · farm_id · period_type · period_start · period_end
  psy · msy · npd · mortality_rate · fcr · avg_daily_gain
  active_sow_count · gestating_count · lactating_count
  is_stale · calculated_at

version 컬럼        없음
formula_version     없음
threshold_version   없음
행 수                0
```

```
V6_RESULT = TIMESTAMPED_ONLY
```

**v1.3 원문 요구에 따른 병기:**

```
TIMESTAMPED_ONLY  →  What Changed 착수에 as_of 선행 필요.  병렬 불가.
```

★ 덧붙여 `kpi_snapshots` 는 **0행이고 reader 도 0건**이다(D-13 §4-1 `LATENT_WRITER`).
`is_stale`+`calculated_at` 만으로는 "그때 그 값이 왜 그랬는가" 를 복원할 수 없다.

---

## 9. D-21 경계 (스펙 §17)

D-19 는 사실만 제공했다. **결정하지 않은 것:**

```
threshold identity model   — V-2 가 이름 4개를 관측했을 뿐, 정본 축을 고르지 않았다
scope model                — farm/region/market/system 과 rule_id/metric_code 의 관계 미정
version bump rule          — V-3 이 버전 축 부재를 관측했을 뿐, 규칙을 만들지 않았다
```

---

## 10. 상태 판정

```
D19_audit_status  = COMPLETE
                    §3-5 전수 기준 9개 전부 충족. "더 있을 수 있음" 없음.

D19_migration_status (지표별)
  PSY               READY
  NPD               READY
  FARROWING_RATE    BLOCKED_BY_CANONICAL_AMBIGUITY
  사산 계열          BLOCKED_BY_P0_2_DECISION
  PWM               BLOCKED_BY_CODE_ALIGNMENT

G0C_gate_status   = BLOCKED
                    사유: APPROVED_POLICY = 0 이고, 승인 개념을 담을 컬럼이
                    threshold 테이블에 존재하지 않는다. 결재를 해도 기록할 곳이 없다.
```

세 축은 독립이다(스펙 §4-1). **감사 완료 ≠ 승격 가능 ≠ 게이트 통과.**

---

## 11. 신규 발견 — 별도 처리가 필요한 것

| # | 발견 | 성격 |
|---|---|---|
| N-1 | flag `use_governance_benchmarks` 가 **국가 임계 → 글로벌 code_default** 로 권위를 통째로 교체 (§2-3, 실측 8건) | 설계 결함 후보 |
| N-2 | `can_fire()` 품질 게이트가 **admin 경로에만** 연결 (§7-2) | D-0 과 동일 뿌리 |
| N-3 | 프로덕션 DMV 에 테스트 잔여물 2행 (`ZZZ`·`ZZZ_DUMMY`) (§4-4) | 운영 데이터 정리 |
| N-4 | tenant override API 에 결재 게이트 없음 (§4-4) | 정책 공백 |
| N-5 | orphan severity path 7건 — 특히 `insight_service` 가 **룰엔진과 병렬로 판정** (§3-3 B9) | 판정 이중화 |
| N-6 | 레지스트리 밖 `rule_id` 발화 (`psy.no_data`, `disease.*.*`) (§3-4) | identity 결함 → D-21 |
| N-7 | **웹 프론트에 자체 임계가 있다** (`status.ts` PSY≥28/NPD≤35/FR≥90). `kpi_status` 부재 시 폴백. `PLATFORM_PARITY.md §3-3` 의 Web 행 `NOT_APPLICABLE · 자체 판정 경로 없음` 과 **불일치** | ★ SSOT 정정 필요 |
| N-8 | `loss.sow_culling` 이 `country != "KR"` 로 하드 게이트 (§3-1) | 국가 분기가 코드에 있음 |

### ★ N-7 상세 — 도달성까지 확인했다

```
resolveTier(backend, metric, legacy)   statusObservation.ts:53
  backend[metric] 있으면  → 서버 status 사용 ✓
  없으면                  → legacy (프론트 하드코딩 임계) ✗

현재 backend kpi_status 키 = PSY · NPD · FARROWING_RATE · SOW_TURNOVER
현재 KPI_CARD_REGISTRY     = 동일 4종
presentation 의 미지 코드   = unknownCodes 로 분리돼 렌더 안 됨

→ 오늘은 폴백이 발동하지 않는다.
→ 그러나 kpi_status 필드가 응답에서 빠지는 순간(구버전 API·배포 스큐)
   웹이 조용히 자체 임계로 판정한다.  FAIL-OPEN 잠복.
```

`PLATFORM_PARITY.md §3-3` 정정은 **이번 STEP 범위 밖**이라 하지 않았다. 승인 대기.

---

## 12. 종료 검증

```
git status --short (before)   비어 있음
git status --short (after)    이 파일 1건만 (untracked → commit)
flag_states_after == before   YES  (use_governance_benchmarks = False, 양쪽 .env 에 키 없음)
DB write count                0    (SELECT · information_schema · pg_get_*def 만)
소스 수정                      0
테스트 수정                    0
migration / seed 변경          0
```
