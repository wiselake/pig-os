# T6 — KPI 정의 충돌 레지스터

> **RUN**: `KPI-T6-FILL-PIGOS-COLUMN` · 2026-09-08 · machine `bjh`
> **입력**: 인수인계본 v1.0(2026-09-08) §1·§2 + `docs/kpi/CANONICAL_FORMULA_SPEC.md` +
> 프로덕션 `kpi_definitions` 16행(READ-ONLY 조회)
> **산출**: 이 문서 · 코드 수정 0건
> **위치**: `ADR-KPI-00` §6 `O-1`("정의 충돌 레지스터가 없다")의 입력

---

## 0. 이 문서를 읽는 규율

```
경쟁사 열   원문 인용(≤15단어) · URL · 등급이 붙은 것만 확정(★)
            등급 D = "정의로 알려진 것"이지 확정 산식이 아니다
벤치마크    수치·평균·임계값은 어떤 출처에서도 기재하지 않는다
PigOS 열    CANONICAL_FORMULA_SPEC 과 kpi_definitions 에서만 채운다
            ★ 코드를 읽어 역산하지 않는다
```

### ★★ T6 해석 원칙 — 3축 구분 (2026-09-08 확정)

**이 절이 이 문서에서 가장 먼저 읽혀야 한다.** 지금까지의 오진 대부분이 아래 세 층을
섞은 데서 나왔다.

```
① RUNTIME
   실제 프로덕션 코드가 계산·서빙하는 값과 산식.

② DOCUMENTED
   CANONICAL_FORMULA_SPEC 및 kpi_definitions 등 현재 문서에 명시된 정의.

③ CANONICAL DECISION
   PigOS 가 향후 정본으로 채택할 정의. K-1~K-4 의 사람 결정으로 확정한다.
```

**본 T6 레지스터의 PigOS 비교 열은 원칙적으로 ② DOCUMENTED 만을 기록한다.**
코드를 읽어 ①을 역산하여 빈 문서 정의를 보충하지 않는다.
따라서 T6 의 `MATCH`/`CONFLICT`/`UNVERIFIED` 판정은 곧바로 런타임 정확성이나
canonical 확정을 의미하지 않는다.

D-19 에서 ①과 ②의 간극을 증거로 확정하고, **③ 결정에 따라 코드 또는 문서를
수렴시킨다.** ★ 수렴 방향을 ③이 정한다 — 기존 코드를 정본으로 전제하지 않는다.

```
CONFIRMED 조건
    ① RUNTIME = ② DOCUMENTED = ③ CANONICAL
    + automated test
    + manual reconciliation
```

★ 이 문서의 `NOT SPECIFIED`(예: T6-10 양모돈 귀속)는 **②에 규칙이 없다**는 뜻이지
"런타임이 아무 처리도 안 한다"는 뜻이 아니다. 코드는 무언가를 하고 있을 것이고,
그것이 무엇인지는 D-19 ①에서 확정한다.

### ★ 가장 중요한 사실 — PigOS 열의 대부분이 UNVERIFIED 인 이유

`CANONICAL_FORMULA_SPEC` §3 의 현재 상태다.

```
PSY                 PSY_ROLLING12M                    REVOKED → UNVERIFIED
NPD                 NPD_COMPLEMENT_SOWYEAR            REVOKED → UNVERIFIED (trend 오염)
SOW_TURNOVER        SOW_TURNOVER_FARROWINGS_PER_INV   PENDING_RECHECK
FARROWING_RATE      FARROWING_RATE_COHORT_110_150     REVOKED → UNVERIFIED
WSI                 WSI_WEAN_TO_SERVICE               REVOKED → UNVERIFIED
MSY                 MSY_HEADOUT_PER_INV               PENDING_RECHECK
WEANED_PER_LITTER   WEANED_AVG_PER_WEANING            REVOKED → UNVERIFIED
사산 계열            (formula_id 미부여)               AMBIGUOUS · LIVE_DIVERGENCE
PRE_WEANING_MORT    (formula_id 미부여)               AMBIGUOUS · LIVE_DIVERGENCE
```

2026-08-27 Codex 독립검증으로 `CONFIRMED 7` 이 무효화됐고, 신설된 판정 기준
(① 코드 라인 인용 ② 테스트 통과 ③ 실데이터 수기 검산)을 **소급하면 기존 7건 전부가
미충족**이다. 그래서 이 레지스터의 PigOS 판정은 대부분 `UNVERIFIED` 다.

**이것은 "PigOS 산식을 모른다"가 아니라 "문서에 적힌 산식이 검증되지 않았다"는 뜻이다.**
아래 §3 Q1~Q4 는 *문서에 적힌 내용*을 인용해 답한 것이며, 그 자체가 CONFIRMED 를
뜻하지 않는다.

---

## 1. 확정 원문 레지스터 (인수인계본 §1 그대로)

★ = 인수인계 시점 실측으로 원문 확인.

### PSY / 이유두수·모돈·년

| 출처 | 원문 | 분모 | 분자 | 시간 | 등급 |
|---|---|---|---|---|---|
| Agriness ★ | "AVG Weaned Period * FSY Period" | 주기 역산(FSY) × 이유건당 평균 | Average Weaned | period | B |
| AHDB | "Total pigs weaned in 1 year / Total number of farrowings in 1 year" | **총 분만 건수** | 이유두수 | year | A |
| InterPIG (Haxsen 2008) | "pigs born alive per litter * (100 − pre weaning mortality) * litters/sow/year" · "Based on average present sow" | **average present sow** | 생존산자×(1−이유전폐사) | year | A |
| BDporc/IRTA | "número de lechones destetados por cerda y año" · Porc d'Or "por cerda productiva y año" | cerda vs **cerda productiva** [COUNSEL-KPI] | 이유두수 | year | A/B |
| pig333 | "piglets weaned per litter x farrowings per sow per year" | 분만 기반 | 이유두수/복 | year | D |

### PWMFY / 이유두수·교배모돈·년

| 출처 | 원문 | 분모 | 등급 |
|---|---|---|---|
| MetaFarms 2024 NPB ★ | "Pigs Weaned / Mated Female / Yr"; "All KPI's reported are the measures of the data as defined by Average Mated Sow Inventory" | **Average Mated Sow Inventory** | **A**(명칭·모집단) |
| SMS via National Hog Farmer | "(pigs weaned … × 365) divided by (total mated sow days …)" | total mated sow days | D(산식) |
| PIC 2021 | "weaned pigs in a full year divided by the average inventory of mated females" | average inventory of mated females | B |

### 분만 횟수 / 모돈 / 년

| 출처 | 원문 | 방식 | 등급 |
|---|---|---|---|
| Agriness ★ | "365.25 / (Average Period of Breeding + Average Days Lactation + Average NPD)" | **주기 길이 역산** | B |
| InterPIG | "actual number of litters in a 365-day period … includes 'empty' or waste-feeding days. Based on productive sow" | 실측 / productive sow | A |
| Business Queensland | "((total litters farrowed ÷ average number of sows) x 12) ÷ number of months"; "every sow … including any gilts mated" | 실측 / 평균 모돈(후보돈 포함) | A |
| pig333 | "365 (days/year)/FI (days/farrowing)" | 주기 역산(365) | D |

### NPD

| 출처 | 원문 | 분모/기준 | 시간 | 등급 |
|---|---|---|---|---|
| Agriness ★ | "TotalNonProductiveDaysPeriod / Total Farrowing Period" | **분만 건당** | per farrowing | B |
| Agriness ★ (개념) | "sum of non-productive days, when sow … open or non producing"; "NPD will not count after the fallout of the female" | 이벤트 합산·도태 후 미가산 | — | B |
| Pork Information Gateway | "365 – ((litters/female/year) x (gestation days + lactation days))" | **잔여 역산 / 모돈·년** | year | A |
| pig333 | 잔여 역산 + "do not include the waiting days until the first mating of the gilts" | 후보돈 초교배 전 제외 | year | D |
| MetaFarms 2024 NPB ★ | "Mated Female Non Productive Days" | **교배모돈 한정** | year | A(명칭) |
| PIC | "Days where the sow is either not gestating nor lactating" | 개념만 | — | B |
| BDporc/3tres3 | "suma de los días productivos y los DNP … igual a 365 días" | 연간 균형 | year | B/D |

### 분만율

| 출처 | 원문 | 분모 | 등급 |
|---|---|---|---|
| Agriness ★ | "Total Actual Farrow / Total Expected Farrow * 100" | **예정 분만 기준** | B |
| BDporc Porc d'Or | "del total de cubriciones … el porcentaje de ellas que ha dado lugar a parto" | 완료 주기의 교배 | A |
| pig333 | "Number of farrowings / Number of sows mated in a certain period of time" | 기간 내 교배 | D |
| PigCHAMP (via pig333) | "% of mated females that reach farrowing" | 교배 모돈 | B |
| MetaFarms 2024 NPB ★ | "Farrowing Rate" (산식 미기재) | — | A(명칭)/NF(산식) |

### 이유두수 / 복

| 출처 | 원문 | 분자 | 분모 | 등급 |
|---|---|---|---|---|
| Agriness ★ | "Sum (Piglets Weaned Related Total Weaning) / Weaning Qty Total Period" | partial·total 이유 + **양모돈 자돈 포함** | 이유 건수 — null 이유 포함, **양모돈·부분이유 제외** | B |
| MetaFarms 2024 NPB ★ | "Pigs Weaned / Female Farrowed" | 이유두수 | **분만 모돈** | A(명칭) |
| SMS via NHF | "We use this number versus pigs weaned per litter weaned, which would include nurse sows" | 양모돈 배제 의도 | 분만 모돈 | D |

### 산자·사산·이유전폐사·자돈생존

| 출처 | 원문 | 등급 |
|---|---|---|
| Agriness ★ | Average Liveborn: "Sum (Live Born Period) / Number of Farrowing Period" | B |
| InterPIG | Born alive: "Excludes pigs born dead" | A |
| MetaFarms 2018 | "Birth Loss % consists of the combination of Stillborn % and Mummified %" | B |
| MetaFarms 2024 NPB ★ | **"Piglet Survival (100-% stillborn-% pre-weaning mortality)"** | **A** |
| MetaFarms 2024 NPB ★ | "Total Born / Female Farrowed", "Live Born / Female Farrowed", "Percent Stillborn", "Pre-wean Mortality" | A(명칭) |
| Business Queensland | PWM%: "((number born alive – number weaned) x 100) ÷ number born alive" | A |
| MetaFarms via Pork Business | "Calculation for version 2 prewean mortality is based on pigs born alive and weaned from sows that were weaned" | D |

### 모돈 폐사·도태·장수성 · WSI · 육성비육

| 출처 | 원문 | 등급 |
|---|---|---|
| MetaFarms 2024 NPB ★ | "Death & Euthanized Rate", "Replacement Rate", "Sow Death Loss %"; removal 6분류 | A(명칭·분류) |
| BDporc | LDCB: "cantidad total de lechones que una cerda ha destetado a lo largo de toda su vida productiva" | A |
| PIC | "Average number of weaned (or marketed) pigs until the female is culled or dead" · removal parity | B |
| MetaFarms 2024 NPB ★ | "Wean to1st Service", "% Repeats Services", "% Multiple Matings" (산식 미기재) | A(명칭)/NF |
| MetaFarms 2024 NPB ★ | 단계 = Nursery / Finish / **single-stocked Wean-to-Finish**; "Feed Conversion"(lb, 산식 미기재) | A(명칭·단계) |
| AHDB | "FCR – kg feed/kg of pork" | A |
| Business Queensland | FCR "May be expressed for growers only … or over the whole herd" | A |
| InterPIG | Pigs sold/sow/year: "pigs weaned/sow/year * (100 − rearing mortality) * (100 − finishing mortality)" | A |
| pigaxis | MSY "counts the number of pigs actually sold to market per sow per year" | D |

---

## 2. 충돌 판정표 — PigOS 열 기입 완료

`conflict_type ∈ {DENOMINATOR, NUMERATOR, TIME_BASIS, UNIT, NAME_ONLY}`

PigOS definition_id 는 **두 체계를 병기**한다 — 이유는 §4 `DRIFT-1` 참조.
`spec:` = `CANONICAL_FORMULA_SPEC` §3 · `reg:` = 프로덕션 `kpi_definitions`.

| ID | KPI | 충돌 축 | conflict_type | PigOS definition_id | PigOS 판정 |
|---|---|---|---|---|---|
| T6-01 | PSY 분모 | 모집단 | DENOMINATOR (≥4변종) | spec:`PSY_ROLLING12M` · reg:`PIGOS_PSY_V1` | **UNVERIFIED** — 스펙 REVOKED. 문서상 분모는 "12개 월초 표본의 경산돈(parity≥1) 평균"으로 PIC·NPB 의 *mated* inventory 도, InterPIG 의 *present sow* 도, AHDB 의 총 분만건도 아니다 |
| T6-02 | PSY 산출 방식 | 실측 vs 역산 | TIME_BASIS | 상동 | **UNVERIFIED** — 문서상 **실측**(이유두수 합 ÷ 평균재고). Agriness/pig333 의 역산 방식이 아니다 |
| T6-03 | 분만/모돈/년 | 실측 vs 주기역산 | DENOMINATOR | spec:`SOW_TURNOVER_FARROWINGS_PER_INV` · reg:`PIGOS_SOW_TURNOVER_V1` | **UNVERIFIED** — 스펙 `PENDING_RECHECK`. 문서상 **실측**(분만건수 ÷ 평균재고), 후보돈 제외(parity≥1) → BQ(후보돈 포함)와 모집단 상이 |
| T6-04 | 상수 365 vs 365.25 | UNIT | UNIT(상수) | 상동 | **UNVERIFIED** — 스펙은 `[ref−365, ref]` 창을 쓴다(365). 365.25 아님 |
| T6-05 | NPD 시간기준 | 년 vs 분만 | TIME_BASIS + DENOMINATOR | spec:`NPD_COMPLEMENT_SOWYEAR` · reg:`PIGOS_NPD_V1` | **UNVERIFIED** — 문서상 **per sow-year**(단위 `days/sow-year`). Agriness 의 per-farrowing 이 아니다. ★ 스펙 status 는 `trend 오염`으로 REVOKED |
| T6-06 | NPD 산출 방식 | 잔여 vs 합산 | NUMERATOR | 상동 | **UNVERIFIED** — 문서상 **여집합(complement)**: `365 × (사육일 − 임신일 − 포유일) / 사육일`. PIG 의 잔여 역산과 형태는 같으나 재고·기간 산정이 다름 |
| T6-07 | NPD 모집단 | 후보돈 포함 | DENOMINATOR | 상동 | **UNVERIFIED** — 스펙: 경산돈(parity≥1), **후보돈 제외**. 레지스트리에는 `gilt_entry_included 플래그(D-1)` 비고가 있어 **두 문서가 서로 다른 것을 말한다**(§4 `DRIFT-3`) |
| T6-08 | NPD 도태 후 | 가산 여부 | NUMERATOR | 상동 | **UNVERIFIED** — 스펙은 `exit_date` 로 재적을 끊는다(도태 후 미가산에 해당). 단 판정 기준 ②③ 미충족 |
| T6-09 | 분만율 분모 | 교배 vs 예정분만 vs 완료주기 | DENOMINATOR + TIME_BASIS | spec:`FARROWING_RATE_COHORT_110_150` · reg:`PIGOS_FARROWING_RATE_V1` | **CONFLICT(내부)** — 스펙 formula_id 는 **교배 코호트(110~150일)** 인데 레지스트리 분모는 `교배복수 / period` 다. 그리고 2026-08-27 실측상 live 경로에 **동월 `farrowings/matings`** 가 존재한다(§4 `DRIFT-4`) |
| T6-10 | 이유두수/복 — 양모돈 | 귀속 | DENOMINATOR(이유건 정의) | spec:`WEANED_AVG_PER_WEANING` · reg:`PIGOS_WEANED_PER_LITTER_V1` | **UNVERIFIED** — 문서상 **이유 이벤트당 평균**(`AVG(weanings.weaned_count)`). 양모돈·부분이유의 귀속 규칙이 **스펙에 없다**(NOT SPECIFIED). Agriness 처럼 분자/분모를 나눠 정의하지 않는다 |
| T6-11 | 이유두수/복 — 부분이유·null | 포함 | NUMERATOR | 상동 | **UNVERIFIED** — 상동. 스펙에 규칙 없음 |
| T6-12 | 이유전폐사 분모 | 생존산자 vs 총산 | DENOMINATOR(모집단 시점) | spec:formula_id **미부여** · reg:`PIGOS_PREWEAN_MORTALITY_V1` | **CONFLICT(내부)** — 스펙 `AMBIGUOUS · LIVE_DIVERGENCE`(경로 2개). 레지스트리 분모는 `포유개시두수`로 BQ 의 `born alive` 와도 MetaFarms v2 의 "이유 완료 모돈 한정"과도 다르다 |
| T6-13 | 자돈 생존율 | 합성 | NUMERATOR(합성) | **NONE** | **NONE** — `자돈생존율` 에 해당하는 정의가 스펙·레지스트리 어디에도 없다. 레지스트리에는 `prewean_survival`·`postwean_survival` 이 별도로 있으나 NPB 의 `100 − %stillborn − %PWM` 합성식과 다른 지표다 |
| T6-14 | 사산·미라 | 합성 여부 | NAME_ONLY(분해 가능) | spec:formula_id 미부여 · reg:`PIGOS_STILLBIRTH_RATE_V1`+`PIGOS_MUMMY_RATE_V1` | **CONFLICT(내부·직접모순)** ★ 레지스트리 `stillbirth_rate` 분자 = **"사산+미라"**(비고: "PigOS 비표준 분자(미라 포함)")인데, 스펙 §4-8 경로①은 `stillborn / total_born`(**미라 제외**) + `MUMMIFIED_RATE` 별도다. §4 `DRIFT-2` |
| T6-15 | 모돈 폐사 | 안락사 포함 | NUMERATOR | reg:`PIGOS_SOW_MORTALITY_V1` (spec **범위 외**) | **NONE(스펙)** — 감사 IN_SCOPE 9건에 없다. 레지스트리 분자 `모돈폐사` 는 안락사 포함 여부를 명시하지 않는다 → NPB `Death & Euthanized` 와 비교 불가 |
| T6-16 | 장수성 | 단위 | UNIT | **NONE** | **NONE** — 평생 이유두수·removal parity 어느 쪽도 스펙·레지스트리에 없다 |
| T6-17 | 육성·비육 단계 구분 | 단계 경계 | TIME_BASIS | reg:`PIGOS_POSTWEAN_MORTALITY_V1` 등 (spec **범위 외**) | **NONE(스펙)** — NPB 의 Nursery/Finish/W2F 단계 경계에 대응하는 정의가 없다 |
| T6-18 | FCR 기준 | 체중·단계 | UNIT + DENOMINATOR | reg:`PIGOS_FCR_V1` (spec **범위 외**) | **UNVERIFIED·미정의** — 레지스트리 분자 `사료급여량`(=투입) · 분모 `증체량` · 단위 `kg_per_kg`. **비고에 "체중구간 정의필요. value_scale D-13"** 이라 스스로 미완을 표시한다 |
| T6-19 | ADG·출하체중 단위 | lb vs kg | UNIT | **NONE** | **NONE** — ADG 정의가 스펙·레지스트리 어디에도 없다. FCR 단위는 kg 기준(`kg_per_kg`)이라 NPB(lb)와 상이 |
| T6-20 | MSY | 역산 vs 실측 | NUMERATOR | spec:`MSY_HEADOUT_PER_INV` · reg:`PIGOS_MSY_V1` | **UNVERIFIED** — 스펙 `PENDING_RECHECK` + `⚠ §7-3`(재고 분모 두 구현). 문서상 **실측**(총출하두수 ÷ 평균재고) → InterPIG 역산식과 NUMERATOR 충돌, pigaxis 실측과 근접 |
| **T6-22** | **"PSY" 라는 이름 자체** | 개념 | **NAME_ONLY(개념 상이)** | spec:`PSY_ROLLING12M` · reg:`PIGOS_PSY_V1` | **CONFLICT(개념)** ★ PigOS 의 PSY 는 구조상 **PWMFY 계열**(실측 이유두수 ÷ 재고)인데 모집단이 *mated* 가 아니라 경산돈이다. Agriness 의 PSY(DFA)는 **역산**이라 개념부터 다르다. 즉 브라질 고객이 보는 "PSY" 와 미국 고객이 보는 "PSY" 와 우리 "PSY" 가 **셋 다 다른 것**이다. 정의 배지 없이 `PSY` 라벨을 쓰는 것 자체가 doc-vs-reality |
| T6-21 | BDporc 생산성 분모 | cerda vs cerda productiva | DENOMINATOR [COUNSEL-KPI] | — | **비교 불가** — 경쟁 정의 자체가 미확정(G-1). PigOS 측 판정을 내리지 않는다 |

### 카운트

```
MATCH        0
CONFLICT     5   (T6-09 · T6-12 · T6-14 · T6-22 / T6-18 은 '미정의'로 별도)
UNVERIFIED  11
NONE         5   (T6-13 · T6-15 · T6-16 · T6-17 · T6-19)
비교불가      1   (T6-21)
계          22
```

★ **MATCH 가 0건인 것은 실패가 아니다.** MATCH 조건은 분모·분자·시간기준·단위 4축
전부 일치인데, 스펙의 7건이 전부 REVOKED/PENDING 이라 애초에 MATCH 를 줄 수 있는
상태가 아니다. 4축 중 3축이 맞아도 CONFLICT 라는 규칙을 그대로 적용했다.

---

## 3. 반드시 답할 4개 (스펙 인용)

### Q1. PSY 분모는 무엇인가

> **답: 어느 것도 아니다 — "12개 월초 표본의 경산돈(parity≥1) 평균 재고"다.**

`CANONICAL_FORMULA_SPEC` §4-1 (`docs/kpi/CANONICAL_FORMULA_SPEC.md:212-238`):

```
denominator       AVG over 12 month-starts of
                    COUNT(sows) WHERE parity >= 1
                      AND entry_date <= m
                      AND (exit_date IS NULL OR exit_date >= m)
population_basis  경산돈(parity>=1). 후보돈 제외 — PigPlan 035001 정합
```

제시된 5후보와 대조하면:

```
mated-female days        아니다 (일수 아니라 월초 head 표본)
avg mated inventory      아니다 (교배 여부를 보지 않는다)
avg present sow          부분 일치 — 다만 후보돈을 제외한다
total farrowings         아니다
주기 역산                아니다 (실측)
```

`InterPIG` 의 *average present sow* 에 가장 가깝되 **후보돈 제외**가 다르다.
`NPB`·`PIC` 의 *mated* inventory 와는 모집단이 다르다.

★ 스펙은 `deleted_at` 을 재고 판정에 쓰지 않고 **`exit_date` 로만** 판정한다고 명시한다
(하베스트 데이터에서 도폐사 모돈이 재고를 부풀린 이력 때문). 상태: `REVOKED → UNVERIFIED`.

### Q2. NPD — 방식·후보돈·도태 후

> **답: per sow-year 여집합(complement). 후보돈 제외. 도태 후 미가산(exit_date 로 절단).**

`CANONICAL_FORMULA_SPEC` §4-2 (`:240-264`):

```
formula           365 × (사육일 − 임신일 − 포유일) / 사육일
population_basis  경산돈(parity>=1) — PSY 분모와 동일 정의
time_window       [ref − 365, ref]
```

```
per sow-year 잔여식   ○ 형태는 이것에 해당 (여집합)
per sow-year 합산     × 이벤트를 더하는 방식이 아니다
per farrowing 합산    × Agriness 방식 아님 (T6-05 충돌)
후보돈 초교배 전 대기일   제외 (parity≥1 이므로 후보돈 자체가 빠진다)
도태 후 가산            미가산 (exit_date 로 재적 절단)
```

★ 단, 완결 이벤트에 **sanity 상한 클립**(임신 130일 / 포유 70일)을 적용하되 행을
drop 하지 않는다 — 유모돈 보존이 이유라고 코드 주석이 명시한다. 이 클립은 어느
경쟁 정의에도 대응물이 없다.

★★ 상태가 `REVOKED → UNVERIFIED (trend 오염)` 인 이유: `/kpi/trend` 가 `npd` 필드에
**WEI**(이유~교배 간격)를 담아 내보내고 있었다(스펙 서두 ②). 즉 *같은 제품 안에서*
NPD 이름으로 두 가지가 나갔다. 이건 국가 간 충돌이 아니라 내부 충돌이다.

★★★ **2026-09-08 라이브 확인 — 오염은 현재 나가지 않는다.**

```
라이브 컨테이너   KpiTrend(npd=None)          실측 (docker exec, /app 원본 대조)
수정 커밋         5abb8a4 (2026-08-27)        배포본 2e372b1 의 조상 — 포함 확인
소비 측           reports/monthly → "-" 표시
                  reports/trend   → 연도별 report 경로(스펙이 여집합 ✓ 로 확인한 쪽)
클라 폴백         값을 만들어내는 코드 없음
```

따라서 이 항목은 **법무 P0 등급이 아니다.** 다만 조치는 "노출 차단"이지 "산식 수정"이
아니며(코드 주석이 그렇게 명시한다), WEI SQL 은 계산돼 버려진다. `reports/monthly` 의
NPD 칸이 빈칸으로 보이는 것은 **옳은 동작이지만 제품 공백**이라 D-19 이후 복구 대상이다.

### Q3. 이유두수/복 — 양모돈·부분이유·null 이유

> **답: 스펙에 규칙이 없다(NOT SPECIFIED). 이유 이벤트당 단순 평균이다.**

`CANONICAL_FORMULA_SPEC` §4-7 (`:322-331`):

```
formula_id  WEANED_AVG_PER_WEANING  v1
value       AVG(weanings.weaned_count) WHERE weaning_date ∈ [today−365, today]
```

```
양모돈 자돈 귀속     규칙 없음 — 원 모돈/양모돈/별도 건 어느 것도 명시 안 됨
부분 이유            규칙 없음
null(0두) 이유       규칙 없음
```

Agriness 는 분자(양모돈 자돈 **포함**)와 분모(이유 건수에서 양모돈·부분이유 **제외**,
null 이유는 **포함**)를 나눠 정의한다. PigOS 는 그 구분 자체가 없다.

★ 스펙은 identifier 가 `WEANED_COUNT` 지만 계산은 이유 이벤트당 평균이라 **의미상
per-litter** 라고 별도로 적어뒀다 — 이름과 의미가 어긋나는 것을 알고 있다는 기록이다.

### Q4. FCR·ADG — 단계·사료기준·체중기준·단위

> **답: FCR 은 레지스트리에만 있고 스스로 "정의 필요"라고 표시한다. ADG 는 아예 없다.**

`CANONICAL_FORMULA_SPEC` §1·§2: FCR·ADG 는 **감사 IN_SCOPE 9건에 없다.**
프로덕션 `kpi_definitions`:

```
fcr   PIGOS_FCR_V1
  분자   사료급여량          ← 투입(급여)이지 소비가 아니다
  분모   증체량              ← 생체/도체 구분 없음
  기간   period
  단위   kg_per_kg           ← kg 고정 (NPB 는 lb)
  비고   체중구간 정의필요. value_scale D-13
```

```
단계 경계(nursery/finish/W2F)   정의 없음 — 비고가 "체중구간 정의필요"로 자인
사료 기준(투입 vs 소비)          투입(급여량). AHDB "kg feed/kg pork" 와 분자 의미 상이
체중 기준(생체 vs 도체)          미명시
단위                            kg 고정 → NPB(lb)와 UNIT 충돌 확정
ADG                             정의 자체가 없음 (T6-19 = NONE)
```

★ `PigOS_FCR_V1` 은 **선언은 됐고 정의는 안 된 상태**다. 이 상태로 FCR 을 유료 분석에
노출하면 위조 0 위반이다.

---

## 4. CODE_DRIFT / SPEC_DRIFT — 어느 쪽도 고치지 않음

지시대로 **기록만 한다.** 파일·행을 남긴다.

### DRIFT-1 — definition_id 체계가 둘이다

```
CANONICAL_FORMULA_SPEC §3      PSY_ROLLING12M · NPD_COMPLEMENT_SOWYEAR ·
                               FARROWING_RATE_COHORT_110_150 · WSI_WEAN_TO_SERVICE ·
                               MSY_HEADOUT_PER_INV · WEANED_AVG_PER_WEANING ·
                               SOW_TURNOVER_FARROWINGS_PER_INV
kpi_definitions.definition_id  PIGOS_PSY_V1 · PIGOS_NPD_V1 · PIGOS_FARROWING_RATE_V1 …
```

두 체계 사이 매핑 문서가 **없다**. 인수인계본 §3 규칙 1이 "스펙의 ID(예: `PIGOS_PSY_V1`)"
라고 적은 것은 이 이원화를 모른 채 쓴 것으로 보인다 — 스펙은 `PIGOS_*` 를 쓰지 않는다.
그래서 이 레지스터는 **둘 다 병기**했다.

### DRIFT-2 — 사산율 분자가 정면으로 다르다 ★

```
kpi_definitions              stillbirth_rate 분자 = "사산+미라"
                             비고: "PigOS 비표준 분자(미라 포함)"
CANONICAL_FORMULA_SPEC §4-8  경로① STILLBORN_RATE = stillborn / total_born  (미라 제외)
                             MUMMIFIED_RATE = mummified / total_born        (별도)
                             loc: services/kpi_service.py:523-524
```

거버넌스 레지스트리는 "미라 포함", 계산 경로는 "미라 제외 + 별도 지표"다.
**같은 `stillbirth_rate` 이름으로 서로 다른 값을 뜻한다.** 게다가 스펙은 이 지표를
`AMBIGUOUS · LIVE_DIVERGENCE`(live 경로 2개)로 이미 표시하고 있어, 실제로는
**세 갈래**일 수 있다.

### DRIFT-3 — NPD 후보돈 처리가 두 문서에서 다르다

```
CANONICAL_FORMULA_SPEC §4-2   population_basis = 경산돈(parity>=1). 후보돈 제외
kpi_definitions npd 비고       "gilt_entry_included 플래그(D-1)"
```

스펙은 후보돈을 제외한다고 단정하고, 레지스트리는 후보돈 편입을 **플래그로 다룬다**고
적는다. 어느 쪽이 런타임인지 이 RUN 에서는 판정하지 않았다(코드 역산 금지 규칙).

### DRIFT-4 — 분만율: 스펙 formula_id 와 레지스트리 분모가 다르고, live 경로가 더 있다

```
spec formula_id   FARROWING_RATE_COHORT_110_150   (교배 코호트 110~150일)
kpi_definitions   분자 분만복수 / 분모 교배복수 / period
spec 서두 ①      보고서 동월 farrowings/matings   report_service.py:182
                  snapshot job 별도 산식           jobs/kpi.py:138-144
```

코호트 방식과 동월 나눗셈이 같은 제품 안에 공존한다. 스펙 자신이 "같은 함수의
`farrowing_rate` 도 동월 나눗셈이라 코호트 산식이 아니다"라고 적었다.

### DRIFT-5 — NPD 분모 표기가 스펙과 레지스트리에서 다르다

```
spec              365 × (사육일 − 임신일 − 포유일) / 사육일     → 분모 = 사육일(재적일수)
kpi_definitions   분자 비생산일수합 / 분모 평균사육모돈(avg_inventory_sow)
```

★ **2026-09-08 정정.** "표기 차이"로 적었으나 부정확했다. 평균재고 = Σ사육일/365 이고
**클립 규칙이 동일하면 두 식은 대수적으로 동치**다. 따라서 실제 차이는 표기가 아니라
**클립(DRIFT-7)과 모집단(DRIFT-3)** 이다. 검산 1건으로 닫을 수 있는 항목이다.

### DRIFT-6 — 정의 레지스트리에 임계값이 섞여 있다

```
kpi_definitions wsi 비고   "KR임계7일"
```

`ADR-KPI-00` §2.4 는 벤치마크·판정 임계를 계산·정의 계층과 분리한다. 임계값이 정의
레지스트리 비고에 들어 있는 것은 그 경계를 흐린다. **값 자체는 이 문서에 옮기지
않았다**(위조 0 규율 — 임계값 기재 금지). 위치만 기록한다.

### DRIFT-7 — 데이터 품질 규칙이 산식 안에 박혀 있다 ★

```
CANONICAL_FORMULA_SPEC §4-2   완결 이벤트에 sanity 상한 클립 (임신 130일 / 포유 70일)
                              행을 drop 하지 않는다 — 유모돈 보존이 이유
```

이것은 **정의가 아니라 sanitation 규칙**이다. 그런데 산식 안에 들어가 있어서
**어떤 경쟁 정의와도 비교가 성립하지 않는다** — PIG 의 잔여 역산이나 Agriness 의
per-farrowing 합산과 대조하려 해도, 우리 쪽 분자에는 그들에게 없는 클립이 이미
적용돼 있다.

정의 계층(무엇을 세는가)과 sanitation 계층(이상치를 어떻게 다루는가)을 분리해야
`T6-05`·`T6-06` 의 비교가 의미를 갖는다. 분리 전까지 두 행의 판정은 **비교 자체가
성립하지 않는 상태**에 가깝다.

```
CODE_DRIFT 건수   7
```

---

## 5. 남은 구멍 (인수인계본 §5 승계 + 이번 추가)

| # | 항목 | 상태 |
|---|---|---|
| G-1 | BDporc 분모(cerda vs cerda productiva) | IRTA 방법론 원문 미확인 → T6-21 판정 보류 |
| G-2 | US PWMFY·WSI·분만율 대수식 | NPB PDF 는 명칭만. 모집단(avg mated inventory)만 A급 |
| G-3 | Agriness 사산·미라·자돈폐사 산식 페이지 | 미확인 |
| G-4 | PigVision/WinPig 정의 | 공개 문서 없음 — NOT FOUND |
| G-5 | 수요 근거 | 이 문서는 전부 공급·기관 측 |
| **G-6** | **PigOS 산식 CONFIRMED 승격** | **본 RUN 범위 밖.** 판정 기준 ②(테스트)·③(실데이터 수기 검산)을 충족한 KPI 가 **0건** |
| **G-7** | **DRIFT-1 매핑** | 스펙 ID ↔ 레지스트리 ID 대응표가 없다 |

---

## 5-1. ★ 사람 결정 대기 — K-1~K-4 (2026-09-08 등록)

이 레지스터가 드러낸 **내부 충돌**은 개발이 단독으로 못 정한다. 어느 쪽이 정본인지는
도메인 판단이다. 결정 전까지 해당 KPI 를 고객에게 노출하지 않는다.

| # | 결정 | 근거 | 업계 관행 참고 |
|---|---|---|---|
| **K-1** | 사산율 분자 — **미라 포함 vs 제외** | `DRIFT-2` (레지스트리 "사산+미라" vs 계산 경로 "미라 제외+별도") | NPB 는 `Percent Stillborn` 과 `Mummified` 를 **분리**하고 `Birth Loss` 를 합성으로 둔다 |
| **K-2** | 분만율 정본 — **교배 코호트 vs 동월 나눗셈** | `DRIFT-4` (두 방식이 같은 제품에 공존) | 코호트가 국제 통용. 동월 나눗셈은 관찰 미완료를 실패로 처리해 값을 왜곡 |
| **K-3** | NPD·PSY 모집단 — **후보돈 제외 유지 여부** | `DRIFT-3` (스펙은 제외 단정, 레지스트리는 플래그) | 제외하면 NPB `Mated Female` 과도 InterPIG `present sow` 와도 다른 **제3의 정의**가 된다 |
| **K-4** | 라벨 정책 — 내부 정의명 노출 여부 | `T6-22` | 예: 내부는 `WEANED_PER_SOWINV_YEAR`, `PSY` 는 **국가 표시명으로만**. 정의 배지 없이 `PSY` 라벨을 쓰면 세 시장에서 세 가지를 뜻한다 |

★ K-1~K-3 은 **국가 정책이 아니라 canonical 정본**을 정하는 결정이다. `ADR-KPI-00` 의
국가별 표시 정책은 그 위에 얹히는 층이므로, 이 넷이 먼저다.

★ **K-4 도 착수 게이트에 포함한다.** 산식만 맞고 명칭이 틀리면 `①=②=③` 이 되어도
사용자가 읽는 의미는 계속 어긋난다(T6-22).

### 실행 흐름에서의 위치

```
09-10 격리 만료
  → 법무 P0 5건 배포
    → 동의 공백 관찰

      → PRE-DECISION EVIDENCE
         K-1~K-3 현재 런타임(①) + 선택지별 영향 실측
         ※ 정의 확정·CONFIRMED 판정 금지 — 결재 입력자료일 뿐이다

        → K-1~K-4 대표 결정  (③ 확정)
          → D-19 PSY   reference implementation
            → NPD → 분만율 → 나머지 KPI
```

`PRE-DECISION EVIDENCE` 는 D-19 가 아니다. "현재 런타임이 무엇을 하는가 / 선택지별로
실제 값이 얼마나 달라지는가"까지만 보여주고 멈춘다. 그래야 결재자가 **개념적 근거와
실제 제품 영향을 함께** 보고 정의를 고를 수 있다.

---

## 6. 이 레지스터가 `ADR-KPI-00` 에 주는 것

`ADR-KPI-00` §6 `O-1` 이 "정의 충돌 레지스터가 없다"고 적어둔 자리를 이 문서가 채운다.
다만 채워 넣은 결과가 **경고**다.

```
국가 간 충돌보다 내부 충돌이 먼저다.

  DRIFT-2  사산율 분자가 거버넌스 레지스트리와 계산 경로에서 반대
  DRIFT-4  분만율이 코호트와 동월 나눗셈으로 공존
  Q2 각주  /kpi/trend 가 npd 이름으로 WEI 를 내보냈다

국가별 정의 선택(ADR-KPI-00 의 country policy)을 논하기 전에,
**한 나라 안에서 한 이름이 한 값을 뜻하는지**가 아직 아니다.
```

`ADR-KPI-00` §4 가 이미 적어둔 순서 — `UNVERIFIED → CONFIRMED(D-19) → 임계 승인(D-21)
→ 고객 노출` — 는 이 레지스터로 재확인된다. 현재 그 첫 단계에 있다.

---

## 7. 종료 보고

```
22행 판정      MATCH 0 · CONFLICT 5 · UNVERIFIED 11 · NONE 5 · 비교불가 1
Q1~Q4          §3 에 스펙 인용과 함께 답변
CODE_DRIFT     7건 (§4)
사람 결정      4건 등록 (§5-1 K-1~K-4)
코드 수정      0건
DB 쓰기        0건 (kpi_definitions 는 READ-ONLY 조회)
STOP 조건      해당 없음
```

### 2026-09-08 v1.1 갱신 내역

```
+ T6-22    "PSY" 이름 자체가 시장 간 다른 개념 — CONFLICT(개념)
+ DRIFT-7  sanity 클립(임신130/포유70)이 산식에 박혀 비교 자체를 막는다
~ DRIFT-5  "표기 차이" → 정정. 클립·모집단이 같으면 대수적 동치. 검산 1건으로 닫힘
+ §5-1     K-1~K-4 사람 결정 등록
+ Q2 각주  /kpi/trend npd=WEI 라이브 확인 → 오염 나가지 않음. 법무 P0 등급 아님
```
