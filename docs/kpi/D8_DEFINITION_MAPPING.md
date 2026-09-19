# D-8 — PigOS canonical ↔ 외부 evidence 정의 매핑 (1차)

```
Mode      READ-ONLY. 코드·seed·설정 변경 0
입력      CANONICAL_FORMULA_SPEC_REAUDIT.md §5 (implementation_status = CONFIRMED 7건)
정본      COUNTRY_KPI_EVIDENCE_ARCHITECTURE_v1.1 §3 (mapping 은 항상 1:1)
Date      2026-08-28
```

---

## 0-0. ★ D-8 STATUS (2026-09-01 확정)

```
D-8 STATUS
  implementation input     READY
    CONFIRMED 7

  external formula input   BLOCKED
    FORMULA claims 0

  current mapping
    NOT_EQUIVALENT           2
    UNKNOWN                  5
    EXACT                    0
    STRUCTURAL_EQUIVALENCE   0

  next trigger
    primary-source formula evidence 확보

  blocker
    PRIMARY_FORMULA_EVIDENCE_MISSING
```

★ **지금 D-8 을 다시 돌리는 것은 작업이 아니라 같은 `UNKNOWN` 을 재출력하는 행위다.**
  병목은 PigOS canonical 이 아니라 external formula evidence 다.
  우리 쪽 입력(`CONFIRMED 7`)은 이미 준비돼 있다.

### 0-0-1. KPI 별 blocker

| formula_id | 우리 입력 | 외부 산식 | blocker |
|---|---|---|---|
| `PSY_ROLLING12M v1` | READY | 없음 (분모 정의 미확보) | `PRIMARY_FORMULA_EVIDENCE_MISSING` |
| `NPD_COMPLEMENT_SOWYEAR v1` | READY | 없음 | `PRIMARY_FORMULA_EVIDENCE_MISSING` |
| `SOW_TURNOVER_FARROWINGS_PER_INV v1` | READY | 없음 | `PRIMARY_FORMULA_EVIDENCE_MISSING` |
| `WSI_WEAN_TO_SERVICE v1` | READY | 없음 | `PRIMARY_FORMULA_EVIDENCE_MISSING` |
| `WEANED_AVG_PER_WEANING v1` | READY | 없음 | `PRIMARY_FORMULA_EVIDENCE_MISSING` |
| `MSY_HEADOUT_PER_INV v1` | READY | 없음 | `PRIMARY_FORMULA_EVIDENCE_MISSING` |
| `MUMMIFIED_RATE` | READY | measure_kind 만 확보 | §0-0-2 (부분 판정 가능) |

### 0-0-2. ★ 기술 판정과 거버넌스 승격을 분리한다

`NOT_EQUIVALENT 2` 는 **사실판정**이다. 그것을 정식 `definition_mapping` record 로
승격해 **제품 게이트의 입력으로 쓰는 것**은 `decided_by` · `decided_at` · `decision_id`
가 필요한 **governance action** 이다. 둘은 다른 층이다.

```
MUMMIFIED_RATE
  technical_mapping_finding = NOT_EQUIVALENT
      PigOS  MUMMIFIED_RATE                = RATE   (mummified / total_born)
      PigCHAMP Average mummies per litter  = COUNT
      → 단위가 달라 직접 비교 불가. 이 사실 자체는 원문 없이도 확정된다.
  governed_mapping_status   = NOT_ESTABLISHED

PSY_ROLLING12M v1
  technical_mapping_finding = NOT_EQUIVALENT_CANDIDATE
      근거가 2차 인용이다(§2-1-A probe). 원문 미확보.
  evidence_status           = UNVERIFIED
  governed_mapping_status   = NOT_ESTABLISHED
```

★ **D-2026-002(승인 주체·경로)가 없다고 해서 `RATE ↔ COUNT` 비동치 같은
  명백한 기술 사실까지 기록하지 못하는 구조로 만들지 않는다.**
  반대로 그 기술 finding 을 곧바로 승인된 mapping row 처럼 사용해서도 안 된다.

승격 경로: `docs/kpi/DECISION_REGISTER.md`

---

## 0-0-3. Evidence procurement — D-8 과 분리한다

```
EVIDENCE PROCUREMENT

PigCHAMP
  - Pigs wnd/female/year denominator
  - total pigs per litter population/denominator semantics

MetaFarms
  - mated female population definition
  - latest 2021–2025 source details          ← D-15

Other primary sources
  - NPD calculation semantics (여집합 vs 간격누적)
  - WSI formula
  - MSY formula
  - weaned per litter formula
```

★ **D-15 만 끝난다고 D-8 전체가 열리지 않는다.**
  D-15 는 MetaFarms 최신판 실사이고, NPD·WSI·MSY 원문 formula 조달은
  **별도 evidence acquisition** 이다. 새 ID 를 만들지 않고 위 목록으로 관리한다.

★ 조달은 웹 리서치 트랙이며 이 저장소의 코드 작업이 아니다.

---

## 0-0-4. `performance_direction` 은 D-8 재실행 명분이 아니다

전건 `UNKNOWN` 이지만, 이 필드를 채워도 `UNKNOWN 5 → EXACT` 를 **하나도 움직이지 못한다.**
게다가 방향이 Threshold 계층에 있다면 Track 4 범위를 다시 건드리게 된다.

```
performance_direction procurement = 별도 backlog
```

---

## 0. 이 문서의 규율 — 이름으로 매핑하지 않는다

D-13 재실사가 **같은 이름 아래 다른 산식**을 여럿 찾아냈다. 그러니 D-8 에서
이름을 보고 매핑을 시작하면 그 오류를 외부 대조로 확대 재생산한다.

```
✗ PigOS PREWEANING_SURVIVAL  ↔  PigCHAMP "Pre-weaning mortality"     (이름 대조)
✓ PigOS formula_id + version ↔  external claim_id + source_edition   (산식 대조)
```

**매핑 단위**는 `formula_id + formula_version` ↔ `claim_id / source_edition` 이고,
**판정 근거**는 아래 6개를 놓고 대조한 결과다:

```
measure_kind · numerator · denominator · population_basis · time_window · unit
```

### 0-1. 두 상태를 분리한다

```
formula_mapping_status        산식이 동치인가
    EXACT | STRUCTURAL_EQUIVALENCE | APPROVED_TRANSFORM(후보) |
    NOT_EQUIVALENT | UNKNOWN | BLOCKED_BY_CANONICAL_AMBIGUITY

performance_direction_status  좋음/나쁨 방향이 확정됐는가
    CONFIRMED | UNKNOWN
```

★ `performance_direction = UNKNOWN` 이 **mapping 을 막지는 않는다.**
`survival = 1 − mortality` 처럼 구조적으로 증명되면 transform 관계는 판정할 수 있다.
다만 **방향 반전을 제품 판정에 쓰는 것은 direction evidence 확보 전까지 승인하지 않는다.**

---

## 1. ★ 가용 외부 evidence 재고 — 먼저 열거한다

매핑하기 전에 **무엇을 가지고 있는지**부터 확정한다. 없는 것으로 판정하면 그게 위조다.

| 출처 | 확보된 것 | 성격 |
|---|---|---|
| **PigCHAMP USA 2023** (167농장) | `Average total pigs per litter 15.84` · `born alive/litter 14.15` · `stillborn pigs 1.18` · `mummies per litter 0.50` · `Culling rate 42.49%` · `Liveborn/female/yr 32.22` | **BENCHMARK 값** (COUNT/RATE) |
| PigCHAMP USA 2023 | `PWM Upper 10 = 21.59` / `Lower 10 = 9.85` | BENCHMARK · percentile |
| PigCHAMP | `Pigs wnd / female / year 28.60` | 값은 있으나 **분모 정의 미확보** `[UNVERIFIED]` |
| **MetaFarms 2020–2024** (US) | `PWMFY 25.42→27.27` (5년) · 2023 = `26.51` 또는 `25.91`(edition 혼합) · `PWM 12.9→16.4%` · `Nursery FCR 1.58 / Finish 2.82 / W-F 2.60` (lb) | BENCHMARK 값 |
| `default_metric_values.source_ref` | `PigCHAMP2023` · `PigCHAMP2024` · `PorkCheckoff2024` · `Agriness2024` · `WEPIG2025` 등 | **라벨뿐.** 산식 아님 |
| `gpt_country_draft_UNVERIFIED.md` | 국가별 KPI **후보 목록** | 산식 아님 (산식 언급 1건). 격리 유지 |

### 1-1. ★★ 결론 — 외부 **산식(FORMULA) claim 은 0건**이다

위 전부가 **BENCHMARK 값**이거나 **라벨**이다. 어느 출처도
"우리는 이 지표를 이렇게 계산한다(분자·분모·포함/제외)"를 **원문으로 확보한 것이 없다.**

```
FORMULA claim 확보:  0건
BENCHMARK claim:     PigCHAMP 6 · MetaFarms 4 (값만)
```

→ **대부분의 행이 `UNKNOWN` 이 되는 것은 감사 부실이 아니라 evidence 부재다.**
   `D-15`(MetaFarms 원문 실사)·`RUN_PROMPT_E`(US 리서치)가 **D-8 의 실질 선행조건**이다.
   그 전에 판정을 만들어내면 그것이 위조다.

---

## 2. 매핑표 — CONFIRMED 7건

> 각 행은 `formula_id + version` 기준이다. KPI 이름 기준이 아니다.

### 2-1. `PSY_ROLLING12M v1`

```
PigOS canonical
  measure_kind      RATIO            unit  pigs/sow/year
  numerator         Σ weanings.weaned_count,  창 = (ref−12개월, ref]
  denominator       AVG over 12 month-starts of COUNT(sows)
                      WHERE parity >= 1 AND entry_date <= m
                        AND (exit_date IS NULL OR exit_date >= m)
  population_basis  경산돈(parity>=1). 후보돈 제외
  time_window       rolling 12 months, month-start 표본
```

| 외부 후보 | claim | 대조 결과 |
|---|---|---|
| PigCHAMP `Pigs wnd / female / year` | 28.60 · USA 2023 | **분모 정의 미확보** — 공개 변수맵의 `Total sows = Ave female inv − Ave gilt pool inv` 가 gilt pool 제외를 시사하나 **명시 산식이 아니다** `[UNVERIFIED]` |
| MetaFarms `PWMFY` (Pigs Weaned per **Mated Female** per Year) | 26.51 / 27.27 · 2020–2024 | 분모가 **mated female** 이다. 우리는 **경산돈 재고 평균**이다. `mated female` 은 교배된 후보돈을 포함할 수 있어 **모집단이 다르다** |

```
formula_mapping_status        NOT_EQUIVALENT  [UNVERIFIED — 2차 인용 근거]
                              ← §2-1-A probe. 모집단(경산돈 vs mated female)과
                                적분 방식(월초 스냅샷 vs 일 단위)이 둘 다 다르다
performance_direction_status  UNKNOWN  (NONE_IN_FORMULA_LAYER)
```

★ 원문(PigCHAMP 자사 문서) 확보 시 `[UNVERIFIED]` 를 뗀다 → **D-15 최우선 항목**.


### 2-1-A. ★ PROBE 결과 (2026-08-28) — PSY 가 `UNKNOWN` 에서 움직였다

결재 전 30분 probe: **"PigCHAMP 이 산식 정의를 공개하는가?"**

**답은 Y/N 이 아니었다. 질문이 틀렸다.**

```
확보된 것 (2차 인용)
  PigCHAMP AMFI (Average Mated Female Inventory)
    = Σ(mated female days in period) ÷ (days in period)     [PigCHAMP, 1996]
  출처: 논문이 PigCHAMP 1996 을 인용. PigCHAMP 자사 문서 원문 아님  [UNVERIFIED]
```

**우리 것과 대조:**

| | PigOS `PSY_ROLLING12M v1` | PigCHAMP AMFI |
|---|---|---|
| 표본 방식 | **월초 12개 스냅샷의 평균** | **일 단위 누적 ÷ 기간일수** (day-weighted) |
| 모집단 | `parity >= 1` — **경산돈** | `mated female` — **교배된 암컷** (교배된 후보돈 포함) |

→ **`NOT_EQUIVALENT`** 다. 모집단과 적분 방식이 둘 다 다르다.
   (근거가 2차 인용이라 `[UNVERIFIED]` 태그를 유지한다 — 원문 확보 시 확정)

#### ★★ 그런데 더 중요한 것 — 업계 PWMFY 산식이 **하나가 아니다**

```
① NPPC        (pigs weaned ÷ days × 365) ÷ (total mated sow days ÷ days)
② 구성요소식   (litters/mated female/year) × (pigs weaned/female farrowed)
③ 140일 지연   (pigs weaned ÷ days × 365) ÷ (avg mated female inventory 140 days ago)
```

그리고 **"gilt development days 를 분모에 포함하느냐"가 값을 바꾸는 주요 변수**다
— 포함하면 PSY 가 낮게 나온다.

→ **D-5 의 질문이 바뀐다.** "발주처를 어디로 할까" 가 아니라
   **"우리 PSY 를 어느 외부 산식에 맞출 것인가"** 다.
   외부 산식을 조달해도 **"그래서 어느 것?"** 이 남는다. 이건 조달이 아니라 **제품 결정**이다.

★ 이 probe 를 안 했으면, 조달만 하면 풀린다는 전제로 예산을 승인받았을 것이다.

### 2-2. `NPD_COMPLEMENT_SOWYEAR v1`

```
PigOS canonical
  measure_kind  DURATION        unit  days / sow-year
  formula       365 × (사육일 − 임신일 − 포유일) / 사육일
  population    경산돈(parity>=1) — PSY 분모와 동일
  time_window   [ref−365, ref]
```

| 외부 후보 | 결과 |
|---|---|
| — | **확보된 외부 NPD claim 없음** |

```
formula_mapping_status        UNKNOWN  (외부 evidence 부재)
performance_direction_status  UNKNOWN
```

★ 여집합 방식(사육일에서 생산일을 빼는)은 업계에서 소수다. 다수는
`이유→재교배 간격 누적` 방식을 쓴다. **둘은 다른 지표다** — D-15/E 에서
외부가 어느 방식인지 확인해야 `NOT_EQUIVALENT` 여부가 갈린다.

### 2-3. `SOW_TURNOVER_FARROWINGS_PER_INV v1`

```
PigOS canonical
  measure_kind  RATIO           unit  litters / sow / year
  numerator     COUNT(farrowings), parity>=1, [ref−365, ref]
  denominator   AVG(월초 경산 재고)  ← PSY 분모와 동일
```

| 외부 후보 | 결과 |
|---|---|
| PigCHAMP `Culling rate 42.49%` | **다른 지표다.** 도태율이지 회전율이 아니다 |
| — | 회전율 외부 claim 없음 |

```
formula_mapping_status        UNKNOWN
performance_direction_status  UNKNOWN
```

### 2-4. `WSI_WEAN_TO_SERVICE v1`

```
PigOS canonical
  measure_kind  DURATION   unit  days
  value         AVG(mating_date − 직전 weaning_date ≤ mating_date), wsi >= 0 만
  time_window   [today−365, today]
```

| 외부 후보 | 결과 |
|---|---|
| — | 확보 없음. (업계 통칭 `WEI` / `Wean-to-Service Interval`) |

```
formula_mapping_status        UNKNOWN
performance_direction_status  UNKNOWN
```

★ 주의점 기록: 우리는 `wsi >= 0` 필터로 음수를 **조용히 제외**한다(건수 미기록).
외부가 어떻게 처리하는지 확인 전에는 `EXACT` 판정 불가.

### 2-5. `WEANED_AVG_PER_WEANING v1`

```
PigOS canonical
  measure_kind  COUNT      unit  pigs / litter
  value         AVG(weanings.weaned_count), [today−365, today]
```

| 외부 후보 | 결과 |
|---|---|
| PigCHAMP `Average pigs born alive/litter 14.15` | **다른 지표** (실산이지 이유가 아님) |
| — | 이유복당두수 외부 claim 미확보 |

```
formula_mapping_status        UNKNOWN
performance_direction_status  UNKNOWN
```

### 2-6. `MUMMIFIED_RATE` — ★ measure_kind 불일치 (유일하게 판정 가능한 행)

```
PigOS canonical
  measure_kind  RATE       unit  percent_0_100
  value         Σ mummified / Σ total_born × 100
```

| 외부 | claim | measure_kind |
|---|---|---|
| PigCHAMP USA 2023 | `Average mummies per litter = 0.50` | **COUNT** (복당 두수) |

```
formula_mapping_status        NOT_EQUIVALENT
                              ← measure_kind 가 다르다. RATE ↔ COUNT
performance_direction_status  UNKNOWN
```

★ **`APPROVED_TRANSFORM` 후보로 승격 가능한가?**
`0.50 ÷ 15.84 = 3.16%` **[DERIVED_NOT_SOURCE_CLAIM]** 로 산술 변환은 가능하다.
★ 이 숫자는 **PigCHAMP 이 주장한 값이 아니라 우리가 만든 파생값**이다. 몇 주 뒤
  인용될 것이므로 태그 없이 문서에 두지 않는다. 그러나:

```
· 그 값은 PigCHAMP 이 주장한 것이 아니라 우리가 만든 파생값이다
· 변환에 쓰는 분모(15.84 = total pigs per litter)가 우리 분모(Σtotal_born)와
  같은 모집단인지 원문 확인이 안 됐다
· 아키텍처 §3-4: 구성요소 유일성이 증명되지 않았다
  (14.15 + 1.18 + 0.50 = 15.83 ≈ 15.84 는 강한 증거이나 비배타적)
```

→ **`APPROVED_TRANSFORM` 후보로만 기록하고 승인하지 않는다.**
   `transform_spec_id` 필수 동반 필드(§3-4)가 채워지지 않았다.

### 2-7. `MSY_HEADOUT_PER_INV v1`

```
PigOS canonical
  measure_kind  RATIO     unit  pigs / sow / year
  numerator     Σ finisher_groups.head_count_out, 완결 그룹, [today−365, today]
  denominator   _avg_active_inventory  ← ★ PSY 분모와 다르다 (후보돈 포함·deleted_at 게이팅)
```

| 외부 후보 | 결과 |
|---|---|
| — | 확보 없음 |

```
formula_mapping_status        UNKNOWN
performance_direction_status  UNKNOWN
```

⚠ **분모 이슈가 mapping 이전 문제다.** `_avg_active_inventory` 는 PSY 분모와 다르고,
그 차이는 `tests/unit/test_inventory_denominator_divergence.py` 로 이미 고정돼 있다.
**외부와 대조하기 전에 내부 분모부터 확정해야 한다.**

---

## 3. AMBIGUOUS 3건 — 행은 만들되 판정하지 않는다

> 표에서 빼면 나중에 "왜 FARROWING_RATE 가 US 매핑표에 없지?" 가 된다.
> 행을 남겨 두면 P0-2 → code alignment → 재실사 후 **같은 record 를 이어갈 수 있다.**

| KPI | 사유 | 외부 후보(참고용, 판정 안 함) |
|---|---|---|
| **FARROWING_RATE** | 산식 4개, ②③이 LIVE (`report_service:182` · `get_trend:788`) | — |
| **STILLBORN_RATE** | 같은 이름 2산식 (미라 포함/제외) | PigCHAMP `Average stillborn pigs 1.18` = **COUNT** |
| **PRE_WEANING_MORTALITY** | 분모 3종 (`weaned+deaths` / `born_alive` / `total_born`) | PigCHAMP `PWM Upper10 21.59 / Lower10 9.85` · MetaFarms `PWM 12.9→16.4%` |

```
formula_mapping_status = BLOCKED_BY_CANONICAL_AMBIGUITY   (3건 전부)
```

### 3-1. ★ PWM — `total_born` 분모 2경로는 자동 매핑 절대 금지

`report_service` 의 ④⑤(`total_born` 분모)는 **사산·미라를 분자에 포함**한다.
일반적인 pre-weaning mortality semantics(출생 후 이유 전 폐사)와 **다른 지표다.**

```
PigCHAMP / MetaFarms "Pre-weaning mortality" 에 자동 매핑 금지
→ NOT_EQUIVALENT 또는 AMBIGUOUS 후보가 맞다
```

이름이 같다는 이유로 매핑하면 **미국 농장에 다른 지표의 기준으로 경고가 뜬다.**

---

## 4. 1차 결과

```
CONFIRMED 7건
  NOT_EQUIVALENT              2   MUMMIFIED_RATE (RATE ↔ COUNT)
                                  PSY (모집단·적분방식 상이) [UNVERIFIED, 2차인용]
  UNKNOWN                     5   NPD·SOW_TURNOVER·WSI·WEANED_PER_LITTER·MSY
  EXACT / STRUCTURAL_EQUIV    0
  APPROVED_TRANSFORM 승인     0   (후보 1: MUMMIFIED_RATE, 동반 필드 미충족)

AMBIGUOUS 3건
  BLOCKED_BY_CANONICAL_AMBIGUITY  3

performance_direction_status  전건 UNKNOWN
```

★ **`UNKNOWN 6` 은 작업 부실이 아니다.** §1-1 대로 외부 **FORMULA claim 이 0건**이다.
값(BENCHMARK)만으로는 산식 동치를 판정할 수 없고, 판정하면 그것이 위조다.

---

## 5. 이 문서가 만든 것 — evidence 갭의 가시화

D-8 을 돌린 실질 성과는 매핑 판정이 아니라 **"무엇이 없는지"가 표로 드러난 것**이다.

| 필요한 것 | 왜 | 조달 경로 |
|---|---|---|
| **PigCHAMP `Pigs wnd/female/year` 분모 정의** | PSY 매핑의 유일한 차단 요인 | RUN_PROMPT_E |
| **MetaFarms `mated female` 모집단 정의** | PSY `NOT_EQUIVALENT` 확정에 필요 | **D-15 최우선** |
| **외부 NPD 계산 방식** (여집합 vs 간격누적) | 다른 지표일 가능성 | E |
| 외부 이유복당두수 · WSI · MSY 산식 | 매핑 자체 불가 | E |
| PigCHAMP `total pigs per litter` 모집단 | MUMMIFIED transform 승인 조건 | D-15 |

→ **D-5(리서치 발주) 결재가 D-8 진행의 실질 선행조건이다.**
   지금 상태로는 7건 중 6건이 UNKNOWN 에서 움직이지 않는다.

---

## 6. Explicit Non-Changes

코드·seed·설정·프로덕션 변경 0. 외부 수치를 새로 만들지 않았다.
`gpt_country_draft_UNVERIFIED.md` 는 격리 유지(산식 아님).
`APPROVED_TRANSFORM` 승인 0건.
