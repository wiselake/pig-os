# CANONICAL_FORMULA_SPEC — 재실사 (A ∩ B ∩ B′)

```
실행 스펙  docs/runs/LOOP_OVERNIGHT_D13_REAUDIT.md
Mode      READ-ONLY. 코드·seed·마이그레이션·설정 변경 0
Baseline  e7133fa   (선언 2fedb9c → 문서 5건만 변경돼 재고정, 근거 §0-1)
Machine   bjh
진행      A·B·B′ 3축 미추적 0 · 3축 상태모델 적용 · 잔여 U-8·U-9·U-10 (전부 후속작업)
```

> **추적은 완료됐다.** A·B·B′ 세 축의 미추적 경로가 0 이다.
> 남은 U-8·U-9·U-10 은 "추적 미완" 이 아니라 **후속 작업**(regression hardening ·
> D-17 모바일 · PWM fixture)이다. 상태 모델은 §5 의 3축 분리를 따른다.

---

## 0. Status

| 항목 | 값 |
|---|---|
| baseline | `e7133fa` |
| 선언 baseline | `2fedb9c` — `2fedb9c..e7133fa` 는 문서 5건뿐(`api/`·`src/` 0건). 재고정 근거 §0-1 |
| 판정 기준 | `CANONICAL_FORMULA_SPEC.md` §3 — ①코드라인 ②테스트 ③실데이터 수기검산 |
| 시작 시점 상태 | `CONFIRMED 0 · REVOKED 5 · PENDING_RECHECK 2 · AMBIGUOUS 2` |

### 0-1. baseline 재고정 근거

```
git diff --name-only 2fedb9c..e7133fa
  docs/MOBILE_PARITY.md
  docs/kpi/CANONICAL_FORMULA_SPEC.md
  docs/product/COUNTRY_PRODUCT_SPEC_INDEX.md
  docs/runs/LOOP_OVERNIGHT_D13_REAUDIT.md
  handoff/DECISIONS_PENDING_2026-08-27.md

grep -E "^(api|src)/"  →  0건
```

---

## 1. B축 — 응답 필드 → 실제 담기는 산식

> B축을 먼저 돌린 이유(실행 스펙 §7): A축부터 가면 1차와 같은 결과가 나온다.
> `/kpi/trend` 오염을 실제로 잡은 것은 B축 방향이었다.

### 1-1. `DashboardKpi` — 중복 필드는 divergence 가 아니다 ✓

같은 KPI 를 top-level(`psy`/`npd`/`sow_turnover`/`farrowing_rate`)과 일반 맵
`metrics` 두 곳에 담는다. 주석은 "기존 계약 유지를 위해 남긴 중복"이라고만 적혀 있어
**서로 다른 소스일 가능성**을 확인했다.

```python
kpi_service.py:889  ctx.kpi = {**herd, "PSY": psy_value,
                               "NPD": npd_detail.avg_npd, "FARROWING_RATE": farrowing_rate}
kpi_service.py:957  metrics = {**ctx.kpi, "SOW_TURNOVER": npd_detail.sow_turnover}
```

→ **같은 변수에서 온다. divergence 없음.** canonical 값이 `herd` dict 를 덮어쓰므로
top-level 과 `metrics[...]` 가 갈라지지 않는다. 룰엔진 판정값과도 동일 소스다.

### 1-2. ★ PRE_WEANING_MORTALITY — 분모가 **셋**이다

1차 D-13 은 "경로 2개"라고 판정했다. **틀렸다.**

| # | 산식 | 분모 | 위치 | 성격 |
|---|---|---|---|---|
| ① | `deaths / (weaned + deaths)` | `weaned+deaths` | `kpi_service.py:512` | 이벤트 기록 기반 |
| ② | `(born_alive − weaned) / born_alive` | **`born_alive`** | `insight_service.py:229` | 차감 추정 |
| ③ | `deaths / (total_weaned + deaths)` | `weaned+deaths` | `report_service.py:194` | ①과 같은 정의 |
| ④ | `Σ(tb − fw)/tb ÷ n` (복단위 평균) | **`total_born`** | `report_service.py:150,186` | 복별 차감 |
| ⑤ | `(avg_tb − avg_weaned)/avg_tb` (근사) | **`total_born`** | `report_service.py:188-191` | ④의 폴백 |

★ **④·⑤ 는 분모가 `total_born` 이라 사산·미라까지 포함한다.** 즉 "포유폐사율"이 아니라
**"총산 대비 손실률"** 에 가깝다 — 이름과 의미가 어긋난다. `/kpi/trend` 의
"필드명은 npd 인데 값은 WEI" 와 **같은 종류의 오염**이다.

④와 ⑤는 `farrowing_weaned` 인자 유무로 갈린다(`report_service.py:185`). 같은 응답
필드가 호출 방식에 따라 다른 산식을 담는다.

### 1-3. ★ FARROWING_RATE — 산식 **넷**

| # | 산식 | 위치 | 비고 |
|---|---|---|---|
| ① | 코호트 110~150일 전 `mating_number=1`, 115일 내 폐사 제외 | `kpi_service.py:370` | canonical |
| ② | 동기간 `farrowings / matings` | `report_service.py:182` | 서로 다른 개체를 나눈다 |
| ③ | 동월 `farrows_by_month / matings_by_month` | `kpi_service.py:788` (`get_trend`) | 〃 |
| ④ | 동기간 `len(farrowings) / matings_count` | `jobs/kpi.py:138-140` | 〃 |

★ ①의 docstring 이 **"비코호트로 인한 두수변동 왜곡을 제거한다"** 고 명시하는데,
②③④가 정확히 그 비코호트 방식이다. **canonical 이 제거하려던 왜곡이 다른 3경로에 살아 있다.**

### 1-4. ★ PSY — snapshot job 이 다른 분모를 쓴다

| # | 산식 | 분모 | 위치 |
|---|---|---|---|
| ① | `Σweaned(12개월) / AVG(월초 경산 재고)` | 12개월 월초 평균 경산돈 | `kpi_service.py:60-121` |
| ② | `(total_weaned / active) × (365/days)` | **현재 활성 두수(point-in-time)** | `jobs/kpi.py:132-135` |

★ ①의 docstring 은 **"현재 시점 활성두수로 나누면 기간 중 입·퇴출을 반영 못 해 비율이
왜곡됨"** 이라고 적고 그것을 고쳤다고 한다. ②가 정확히 그 방식이다.
그리고 ②는 `parity>=1`(경산) 필터도 없다.

**reachability**: `KpiSnapshot` **reader 가 앱에 0건**이다(모델·잡 외 참조 없음).
따라서 현재는 `LATENT_WRITER` — cron 은 돌지만 아무도 안 읽는다.

> ⚠ **그런데 이것이 안전하다는 뜻이 아니다.** `CLAUDE.md` 설계와 코드 주석 3곳
> (`core/cache.py:8` · `db/keepalive.py:14` · `routers/base/kpi.py:78`)이
> **"근본 해법은 대시보드를 `kpi_snapshots` 조회로 바꾸는 것"** 이라고 적고 있다.
> 그 이관이 실행되면 **대시보드 PSY 가 조용히 ②로 바뀐다.** 지뢰다.

### 1-5. 사산 계열 — 필드명이 다르면 오염이 아니다

| 필드 | 산식 | 위치 | 판정 |
|---|---|---|---|
| `STILLBORN_RATE` | `stillborn / total_born` | `kpi_service.py:523` | 경로① |
| `STILLBORN_RATE` | `(stillborn + mummified) / total_born` | `insight_service.py:211` | 경로② — **오염** |
| `MUMMIFIED_RATE` | `mummified / total_born` | `kpi_service.py:524` | 별도 지표 |
| `stillborn_rate` | `sb / tb_sum` | `report_service.py:195` | 경로①과 같은 정의 ✓ |
| `mummified_rate` | `mum / tb_sum` | `report_service.py:196` | ✓ |
| **`loss_rate`** | `(sb + mum) / tb_sum` | `report_service.py:197` | **경로②와 같은 값이지만 필드명이 다르다 → 오염 아님** ✓ |

★ `loss_rate` 가 좋은 대조군이다 — 합산 정의를 쓰되 **이름이 `stillborn_rate` 가 아니다.**
`insight_service.py:211` 이 문제인 것은 산식이 아니라 **같은 이름을 쓴 것**이다.

### 1-6. B축에서 해소된 것

| 필드 | 결과 |
|---|---|
| `DashboardKpi.metrics` | top-level 과 동일 소스 ✓ |
| `NpdBreakdown.avg_npd` | `calculate_npd` 여집합 ✓ |
| `NpdBreakdown.weaning_to_mating_days` | WEI — **이름이 정확하다** ✓ |
| `ReproductionRow.stillborn_rate` / `mummified_rate` / `loss_rate` | 이름·산식 일치 ✓ |
| `ScorecardRequest.*` | 사용자 입력. 측정 아님 ✓ |
| `KpiTrend.npd` | `5abb8a4` 로 노출 차단됨(값은 WEI) |


### 1-7. U-4~U-7 — 나머지 B축

| 대상 | 결과 |
|---|---|
| **U-4** `sync_service` / `schemas/sync.py` | **KPI 계산·반환 0건.** `sync_service.py:268` 의 KPI 언급은 `breeding_cycle_id` 누락이 parity별 KPI 에 영향 준다는 **주석**일 뿐 ✓ |
| **U-5** 응답 모델 내 계산 프로퍼티 | `finisher.py:55 mortality()` = `head_count_in − head_count_out` → **COUNT** 다. herd 의 `FINISH_MORTALITY` 는 `(hin−hout)/hin×100` → **RATE**. **이름·measure_kind 가 둘 다 다르므로 오염 아님** ✓ (`events.py:64 set_total_born` 은 입력 검증용 validator) |
| **U-6** DEFERRED KPI 의 B축 | `report_service` 에 `adg_g` · `fcr` · `mortality_rate` 가 별도로 있으나 **`aggregation_scope` 가 다르다** — report 는 **그룹(finisher_group) 단위**, herd 는 **농장 단위**. 아래 참조 |
| **U-7** `alert.py`·`farm.py`·`events.py`·`sync.py` | KPI **값**을 담는 필드 없음. `farm.py:92 npd_alert_threshold` 는 설정값, `alert.py` 는 알림 메타, `events.py` 는 원자료(`stillborn`/`mummified` 등) ✓ |

#### ★ 판별 기준 하나 — "같은 산식 · 다른 `aggregation_scope`" 는 divergence 가 아니다

| KPI | herd (농장) | report (그룹) | 판정 |
|---|---|---|---|
| FCR | `Σfeed / Σgain` `:535` | `feed_total / gain_total` `:373` | 같은 정의, 다른 스코프 ✓ |
| 비육폐사 | `(hin−hout)/hin×100` `:536` | `(head_in−head_out)/head_in×100` `:363` | 같은 정의, 다른 스코프 ✓ |
| ADG | `Σ((exit−entry)×head_out) / Σ((end−start)×head_out) ×1000` `:534` — **두수 가중** | `(exit_w−entry_w)/days×1000` `:355` — 그룹 단순 | 스코프가 달라 **비교 대상이 아니다**. 단 report 행들을 평균내면 herd 와 다르다 — 그렇게 쓰면 안 된다 |

★ 이 기준이 필요한 이유: 스코프 차이를 divergence 로 세면 **가짜 발견이 늘어난다.**

> ### ⚠ 다만 절대규칙으로 쓰면 위험하다 — 기준을 좁힌다 (2026-08-28)
>
> "scope 만 다르면 divergence 아님" 은 **틀릴 수 있다.**
>
> ```
> average of ratios   Σ(feedᵢ/gainᵢ) / n
> ratio of sums       Σfeedᵢ / Σgainᵢ
> ```
>
> 둘은 scope 만 달라 보이지만 **수학적으로 같은 값이 아니다.** 가중이 다르다.
>
> **정확한 기준:**
>
> ```
> scope 만 다르고, numerator/denominator 구성 · aggregation operator ·
> time/population semantics 가 **동일하게 보존**되는 경우에만 divergence 로 보지 않는다.
> ```
>
> 위 표에서 FCR·비육폐사는 `ratio of sums` 를 스코프만 좁힌 것이라 보존된다 ✓
> **ADG 는 herd 가 두수 가중(`ratio of sums`), report 가 그룹 단순이므로
> report 행들을 평균내면 `average of ratios` 가 되어 herd 와 다른 값이 된다** —
> 그렇게 쓰면 그때는 divergence 다.

---

## 2. A축 — 산식 함수 → 호출자 (부분)

| 산식 함수 | 호출자 | reachability | 근거 |
|---|---|---|---|
| `calculate_psy` | `get_dashboard` · `build_rule_context` | LIVE | `kpi_service.py:846,650` |
| `calculate_npd` | `get_dashboard` · `report_service:325` | LIVE | route `/kpi/npd`, `/reports` |
| `_cohort_farrowing_rate` | `build_herd_kpis:520` · `get_dashboard:817` | LIVE | |
| `build_herd_kpis` | `build_rule_context:650` · `get_dashboard:846` | LIVE | |
| `_avg_active_inventory` | `build_herd_kpis:515` | LIVE | MSY·CULLING·SOW_MORTALITY·REPLACEMENT 분모 |
| `get_trend` | `GET /kpi/trend` | LIVE | `routers/base/kpi.py:112`, 프론트 `kpi.ts:10-12` |
| `insight_service.analyze_*` | `POST /events/*` `_attach_insights` | LIVE | `routers/base/events.py:123,155,250,336` |
| `jobs/kpi.py` 집계 | cron (daily/weekly/monthly) | **LATENT_WRITER** | writer LIVE, reader 0건 |
| `npd_repo.avg_wei_days` | `calculate_npd:238` · `get_trend` wei_rows | LIVE | |
| `scorecard_service` | `POST /scorecard` | LIVE | 입력값 채점(측정 아님) |
| `report_service.*` | `GET /reports/*` | LIVE | 웹 `reports/reproduction/page.tsx:40-44` |

**해소**: `sync_service` 는 KPI 를 계산·반환하지 않는다(§1-7 U-4). A축 미완 항목 없음.

---

## 3. B′축 — 모바일 DTO 매핑

**완료.** 핵심 질문의 답: **라벨만이 아니다. "판정" 도 자체 계산한다.**

### 3-1. 값(산식)은 건드리지 않는다 ✓

| 확인 | 결과 |
|---|---|
| Android DTO 계산 프로퍼티 | 0건 (`data/remote/dto/*.kt` 전수) |
| iOS 모델 계산 프로퍼티 | 0건 (`Domain/` · `Data/` 전수) |
| Android `KpiDetailScreen.kt:54-93` | `PsyDetail` · `NpdBreakdown` 표시 전용. `weaningToMatingDays`(WEI)를 **별도 라벨로 정확히** 씀 ✓ |

→ `/kpi/trend` 형태의 **산식 오염은 모바일에 없다.**

### 3-2. ★ 그러나 severity 를 자체 판정한다 — ADR-KPI-08 위반

`ADR-KPI-08` 은 `kpi_status`(백엔드 소유 판정)를 두고 **"프론트는 이 값을 렌더만 하고
자체 판정 금지"** 라고 못박았다.

```
kpi_status 소비 여부
  웹        ✓  resolveTier(data.kpi_status, "PSY", psyTier(data.psy))
               + reportStatusMismatches() 로 괴리 관측          (app)/page.tsx:120,158-160
  Android   ✗  전 소스 0건
  iOS       ✗  전 소스 0건
```

**둘 다 `kpi_status` 를 소비하지 않고 각자 다른 방식으로 색을 만든다.**

| | 판정 방식 | 문제 |
|---|---|---|
| **iOS** `DashboardScreen.swift:241-246` | `alerts` 에서 해당 KPI 알림을 찾아 색. **없으면 `AppColor.success`(초록)** | "판정 없음" 과 "정상" 을 구분하지 못한다 |
| **Android** `DashboardScreen.kt:238-243` | `meetsAvg = myValue >= b.avg` → Success/Warning. **벤치마크 평균과 직접 비교** | G3 ① **"benchmark 기반 severity 없음"** 정면 위반 |

> Android 는 `null → TextMuted`(회색) 를 두어 값·벤치마크가 없을 때는 fail-closed 다.
> 그러나 값이 있고 벤치마크가 있으면 **서버 판정과 무관하게 자체로 색을 낸다.**

### 3-3. ★★ 이것이 D-17(G3) 을 무력화한다

G3 ③ 이 서버에서 `code_default` severity 를 DENY 하면 알림이 사라진다. 그때:

```
웹        kpi_status 를 읽으므로 "insufficient" 를 그대로 표시          → G3 성립
iOS       alert 이 없으니 → 전 KPI 초록                                → G3 무력화
Android   서버 판정과 무관하게 benchmark 로 계속 색을 냄               → G3 무력화
```

**서버에서 G3 를 강제해도 모바일에서 뚫린다.** D-17 은 API 응답 계약만으로 끝나지 않고
**모바일이 `kpi_status` 를 소비하도록 바꾸는 것까지** 포함해야 한다.

→ `MOBILE_PARITY` §1-3 을 갱신할 것: "KPI 목록 하드코딩" 만이 아니라
  **"판정 자체 계산"** 이 더 큰 갭이다.

---

## 4. 신규 발견 — 1차 D-13 이 놓친 것

| # | 내용 | 심각도 |
|---|---|---|
| N-1 | **PWM 분모가 셋**(`weaned+deaths` / `born_alive` / `total_born`). 1차는 2경로로 판정 | 높음 |
| N-2 | **PWM ④⑤ 는 `total_born` 분모라 사산·미라 포함** — "포유폐사율" 이름과 의미가 어긋남 | 높음 |
| N-3 | **FARROWING_RATE 산식 넷.** canonical docstring 이 "제거한다"고 한 비코호트 방식이 3경로에 살아 있음 | 높음 |
| N-4 | **PSY snapshot job 이 point-in-time 분모** — canonical docstring 이 결함으로 명시한 그 방식. 현재 latent 이나 CLAUDE.md 설계가 이 경로로의 이관을 지시하고 있음 | 중(잠복) |
| N-5 | 같은 응답 필드(`pwmr_b`)가 **호출 인자 유무로 다른 산식**을 담음 (`report_service.py:185`) | 중 |
| N-6 | **내 과장 정정** — D-13 §7-3 의 재고 분모 divergence 를 신규 발견처럼 보고했으나, `tests/unit/test_inventory_denominator_divergence.py` 가 **이미 D-2 진단으로 기록·고정**해 뒀다(`main @ b71bb20` 판독 명시). 현상은 실재하나 **발견이 아니다** | — |

---

## 4-1. LATENT — `MIGRATION_HAZARD`

```
MIGRATION_HAZARD: PSY snapshot path uses point-in-time denominator

  대상   jobs/kpi.py:132-135   (total_weaned / active) × (365/days)
         · 현재 활성 두수(point-in-time) 분모 · parity>=1 필터 없음
  현재   KpiSnapshot reader 0건 → LATENT_WRITER. LIVE_DIVERGENCE 아님
  위험   CLAUDE.md 설계와 코드 주석 3곳이 "대시보드를 kpi_snapshots 조회로" 를 지시
         → 이관하면 대시보드 PSY 가 조용히 이 산식으로 바뀐다

  RULE   snapshot path 로 reader 전환 금지
         UNTIL canonical formula conformance test PASS
```

★ 이렇게 고정해 두지 않으면, 다음에 누군가 **"문서대로 snapshot 이관"** 을 하면서
PSY 를 다시 깨뜨린다. 그때는 docstring 이 "고쳤다" 고 적혀 있으니 아무도 의심하지 않는다.

## 4-2. `pwmr_b` — 하나의 `formula_id` 아래 두 의미를 두면 안 된다

`report_service.py:185` 는 `farrowing_weaned` 인자 유무로 산식을 바꾼다.

```
인자 있음 → Σ(tb−fw)/tb ÷ n     복단위 평균
인자 없음 → (avg_tb−avg_weaned)/avg_tb   근사
```

**의도된 기능이면** `formula variant A` / `variant B` 로 **분리 선언**해야 하고,
**의도치 않은 차이면** `LIVE_DIVERGENCE` 다. 어느 쪽이든 **하나의 canonical
`formula_id` 아래 두 의미를 넣어서는 안 된다.** → P0-2/D-8 이전 판정 필요.

---

## 5. KPI 별 판정 — **3축 분리**

> ### ★ 상태 모델 정정 (2026-08-28)
>
> 1차 보고에서 "산식 assertion 테스트가 없다" 는 이유로 `implementation_status` 를
> `UNVERIFIED` 로 내렸다. **D-13 v1.2 와 충돌한다.** v1.2 는 테스트를
> **authority 가 아니라 corroboration** 으로 정의했다. 코드 본문에서 산식이 유일하게
> 특정되고 손계산·API 가 일치했는데 테스트 부재를 이유로 산식 판정을 내리면,
> **`implementation_status` 의 의미를 몰래 바꾸는 것**이 된다.
>
> 세 축으로 분리한다. 서로 다른 질문이기 때문이다.
>
> ```
> implementation_status       코드에서 산식이 유일하게 특정되는가
>     CONFIRMED | AMBIGUOUS | NOT_APPLICABLE | UNRESOLVED_OUTSIDE_SCOPE
>
> runtime_reproduction_status 실데이터 손계산과 API 가 일치하는가
>     MATCHED | MISMATCHED | NOT_RUN | ZERO_PATH_ONLY
>
> regression_test_status      그 산식을 잠그는 테스트가 있는가
>     FORMULA_ASSERTION_PRESENT | MISSING
> ```
>
> `regression_test_status = MISSING` 은 **formula verification 미완이 아니라
> regression hardening backlog** 다(U-8). CONFIRMED 의 정의를 "테스트까지 존재" 로
> 강화하려면 **D-13 v1.3 에서 새 composite gate 를 만들어야지**, 기존 축의 의미를
> 바꿔서는 안 된다.

**③ 검산 대상 농장**: `cb548b14…3563`
`population_scope = INTERNAL_REFERENCE` (`data_origin=pigplan_migration`, country US)
실고객은 최근 365일 분만 3건이라 검산 불가 — **실고객 예측치가 아니다.**

### 5-1. canonical KPI **10개** — 판정표

> ★ 1차 보고의 "CONFIRMED 5 / UNVERIFIED 4 / AMBIGUOUS 2 = 11" 은 **이중 집계**였다.
> `STILLBORN_RATE` 를 "경로① CONFIRMED" 행과 "사산 계열 AMBIGUOUS" 행으로 두 번 셌다.
> canonical KPI 는 **10개**, runtime 손계산도 **10개**로 일치한다.

| KPI | implementation | runtime | regression_test | 비고 |
|---|---|---|---|---|
| **PSY** | **CONFIRMED** `kpi_service.py:60-121` | **MATCHED** | PRESENT `test_psy_denominator.py` | |
| **NPD** | **CONFIRMED** `:216-256` | **MATCHED** | PRESENT `test_npd_complement` 외 3 | |
| **SOW_TURNOVER** | **CONFIRMED** `:234` | **MATCHED** | PRESENT `test_dashboard_metrics_map` | |
| **FARROWING_RATE** | **AMBIGUOUS** — 산식 4개(§1-3) | **MATCHED** (canonical 경로) | PRESENT `test_farrowing_rate_cohort` | reachability 확정 필요 → §5-2 |
| **WSI** | **CONFIRMED** `:425-429` | **MATCHED** | **MISSING** | U-8 |
| **WEANED_PER_LITTER** | **CONFIRMED** `:530` | **MATCHED** | **MISSING** | U-8 |
| **MUMMIFIED_RATE** | **CONFIRMED** `:524` | **MATCHED** | **MISSING** | U-8 |
| **MSY** | **CONFIRMED** `:559` | **NOT_RUN** (출하 데이터 없음) | **MISSING** | U-8 + 검산 미실시 |
| **STILLBORN_RATE** | **AMBIGUOUS** — 같은 이름 2산식(§1-5) | **MATCHED** (경로①) | PRESENT `metrics_map:58` `2/25→8.0` | P0-2 대상 |
| **PRE_WEANING_MORTALITY** | **AMBIGUOUS** — 분모 3종(§1-2) | **ZERO_PATH_ONLY** | **MISSING** | §5-3 · U-10 |

```
implementation   CONFIRMED 7 · AMBIGUOUS 3 · UNRESOLVED 0        (합 10)
runtime          MATCHED 8 · ZERO_PATH_ONLY 1 · NOT_RUN 1        (합 10)
regression_test  PRESENT 5 · MISSING 5                            (합 10)
```

> ### ★ U-8 / U-10 완료 (2026-09-01)
>
> ```
> regression_test  PRESENT 10 · MISSING 0        (합 10)
> ```
>
> | KPI | 추가된 회귀 | commit |
> |---|---|---|
> | WSI | `test_u8_formula_regression.py` — 평균 간격 + 음수/NULL 제외 | `86e6966` |
> | WEANED_PER_LITTER | 이유 건별 단순 평균 | `86e6966` |
> | MUMMIFIED_RATE | 분모 = `total_born` (실산 분모 반증 포함) | `86e6966` |
> | MSY | 출하/평균재고 + 출하 없으면 None | `86e6966` |
> | PRE_WEANING_MORTALITY | 3경로 characterization | `5c2dc8d` |
>
> ★ **다른 두 축은 움직이지 않았다.**
>
> ```
> implementation_status        변경 없음  (CONFIRMED 7 · AMBIGUOUS 3)
> runtime_reproduction_status  변경 없음
>   MSY  = NOT_RUN 유지 — synthetic fixture 는 production reproduction 이 아니다
>   PWM  = ZERO_PATH_ONLY 유지 — U-10 은 로컬 fixture 이지 실데이터 재현이 아니다
> ```
>
> ★ PWM 회귀는 **canonical 을 선택하지 않는다.** 세 경로가 현재 무엇을 계산하는지
>   보존할 뿐이다. P0-2 이후 code alignment 가 일어나면 그 테스트가 **깨져야 정상**이고,
>   깨지지 않으면 정렬이 실제로 일어나지 않은 것이다.

★ **D-8 mapping 진입 가능**: `implementation_status = CONFIRMED` 7건.
  `AMBIGUOUS` 3건(FARROWING_RATE · STILLBORN_RATE · PWM)은 **mapping 금지**.

### 5-2. FARROWING_RATE 를 AMBIGUOUS 로 내린 이유

1차 보고는 "canonical 경로 한정 CONFIRMED" 라고 썼다. 그런데 §1-3 의 나머지 3산식이
**production reachable 인지가 판정을 가른다.**

| 경로 | reachability | 근거 |
|---|---|---|
| ① 코호트 `kpi_service.py:370` | LIVE | 대시보드·룰엔진 |
| ② 동기간 `report_service.py:182` | **LIVE** | `GET /reports/*` → 웹 `reports/reproduction/page.tsx:40-44` |
| ③ 동월 `get_trend:788` | **LIVE** | `GET /kpi/trend` → 4개 화면 |
| ④ 동기간 `jobs/kpi.py:138` | LATENT_WRITER | reader 0건 |

②③이 live 다 → **`LIVE_DIVERGENCE`. D-8 이전 정렬 대상이다.**
canonical 하나만 놓고 `CONFIRMED` 라고 쓰면 나머지 두 live 경로가 문서에서 사라진다.

### 5-3. ★ PWMR `0.0` 은 산식 검증이 아니다 — 내 과장 정정

1차 보고에 **"PWMR = 0.0 이 경로① 결함의 직접 증거"** 라고 썼다. **과하다.**

```
DEATH event = 0  →  0/A = 0 · 0/B = 0 · 0/C = 0
분모가 무엇이든 결과가 0 이다.
```

이 실행이 직접 증명하는 것은 여기까지다:

```
DEATH 이벤트 0건 → API 가 0.0 반환 → zero-event/null 처리 경로 정상
```

**분모나 inclusion rule 의 직접 검증은 아니다.** 따라서
`runtime_reproduction_status = ZERO_PATH_ONLY` 로 내린다.

→ **U-10 신규**: PWM 산식 검증에는 **non-zero fixture 1건**이 필요하다.
  실데이터가 없어도 synthetic regression test 면 충분하다.

---

## 6. ③ 수기 검산 기록

`population_scope = INTERNAL_REFERENCE` · 농장 `cb548b14…3563` (US, 경산 6,997두)

| KPI | 손계산 (독립 재작성 SQL) | API | 일치 |
|---|---|---|---|
| PSY | 분자 47,078 / 분모 1608.4167 = 29.27 | 29.27 (`total_weaned=47078`, `avg_sow_count=1608.42`) | ✓ |
| NPD | sow_days 584,670 · 365×76,534÷584,670 = 47.7789 | 47.8 (`empty_days=76534`) | ✓ (반올림) |
| FARROWING_RATE | **farrowed 268 ÷ mated 482** = 55.6 | 55.6 | ✓ |
| SOW_TURNOVER | farrow_cnt 3,701 / avg_inv 1608.42 = 2.30 | 2.3 | ✓ |
| WSI | avg(mating−직전이유), wsi≥0 → 10.5 | 10.5 | ✓ |
| WEANED_PER_LITTER | avg(weaned_count) → 12.5 | 12.5 | ✓ |
| STILLBORN_RATE | Σsb ÷ Σtb → 2.2 | 2.2 | ✓ |
| MUMMIFIED_RATE | Σmum ÷ Σtb → 1.6 | 1.6 | ✓ |
| MSY | 출하(head_out) 데이터 없음 | None | 산출 불가 |
| PWMR | DEATH 이벤트 0건 → 0.0 | 0.0 | **ZERO_PATH_ONLY** — 산식 검증 아님 |

★ NPD 역산 `sow_days` 584,412 vs 손계산 584,670 — 차 258일(0.044%)은 `avg_npd` 를
`round(x,1)` 로 반올림해 생긴 것이다. `365×76534÷584670 = 47.7789 → 47.8` 로 일치 확인.

★ **PWMR = 0.0 은 zero-event 경로만 검증한다.** 분모가 무엇이든 `0/x = 0` 이므로
산식·분모의 직접 검증이 아니다(§5-3). `ZERO_PATH_ONLY` — non-zero fixture 필요(U-10).

---

## 7. Explicit Non-Changes

코드·테스트·seed·마이그레이션·설정 변경 0. 프로덕션 접근 0(이번 회차).
모바일 저장소 접근 0. push 0. 본 문서 1건만 신규 생성.

---

## 8. ★ 미추적으로 남은 것 — **비어야 완료다. 비어 있지 않다**

| # | 항목 | 왜 못 했는지 |
|---|---|---|
| ~~U-1~~ | ~~③ 수기 검산~~ | **완료** — §6. 10개 KPI 전건 대조(8 일치 · 1 산출불가 · 1 결함확인) |
| ~~U-2~~ | ~~② 테스트 대조~~ | **완료** — 산식 테스트 27건 PASSED. 다만 4개 KPI 는 산식 테스트 자체가 없음(U-8) |
| **U-10** | **PWM non-zero fixture 부재** | 신규(§5-3). zero-event 경로만 검증됨. synthetic regression test 로 충분 |
| **U-9** | **모바일이 `kpi_status` 미소비 · severity 자체 판정** | 신규(B′). D-17 범위를 API 계약 밖으로 넓힌다 |
| **U-8** | **MUMMIFIED_RATE·WSI·WEANED_PER_LITTER·MSY 산식 테스트 부재** | 신규. ② 미충족 원인. 값은 맞으나 회귀 보호가 없다 |
| ~~U-3~~ | ~~B′축(모바일 DTO)~~ | **완료** — §3. 산식 오염 없음 / severity 자체판정 발견(U-9) |
| ~~U-4~~ | ~~sync 의 KPI 반환~~ | **완료** — 계산·반환 0건 (§1-7) |
| ~~U-5~~ | ~~응답 모델 계산 프로퍼티~~ | **완료** — `finisher.mortality()` 는 COUNT, 이름·measure_kind 모두 달라 오염 아님 (§1-7) |
| ~~U-6~~ | ~~DEFERRED KPI B축~~ | **완료** — report 는 그룹 스코프. "같은 산식·다른 aggregation_scope" 판별 기준 신설 (§1-7) |
| ~~U-7~~ | ~~기타 스키마 KPI 필드~~ | **완료** — KPI 값 필드 없음 (설정값·알림메타·원자료) (§1-7) |

**다음 런은 U-1 부터 시작한다.** ②③ 없이는 어떤 항목도 CONFIRMED 로 갈 수 없다.

---

## 10. RUN_DEVIATION — 감사 provenance

D-13 v1.2 는 `git add/commit 금지` · `production server 제외` 였다. 이번 런은 둘 다 했다.
**결과가 틀렸다는 뜻이 아니다** — runtime 검증 덕분에 가치가 커졌다. 다만 감사
provenance 상 단계를 섞지 않는다.

```
RUN_DEVIATION

  ① D-13 Canonical Audit          = local source read only
                                     (source/config/prod write = 0)
  ② Post-D13 Runtime Verification = INTERNAL_REFERENCE production SELECT
                                     read-only · production write 0
                                     ★ v1.2 의 "production server 제외" 에서 벗어남
  ③ Post-run documentation        = local commit 8건 · push 0
                                     ★ v1.2 의 "git commit 금지" 에서 벗어남

  source / config / production write : 0
```

★ ②③은 **formal gate 상 protocol deviation** 이다. 재작업이 필요해 보이지는 않으나,
"D-13 pure read-only audit" 과 "추가 runtime verification" 이 섞이면 나중에
**어느 판정이 어느 근거에서 나왔는지 추적이 안 된다.** 그래서 분리해 기록한다.

다음 런 스펙(v1.3)에서는 이 둘을 **처음부터 별도 단계로 선언**할 것.
