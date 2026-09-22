# Evidence Architecture — v1.1 ↔ v1.2 검토

```
검토일          2026-08-28
repo canonical  docs/specs/COUNTRY_KPI_EVIDENCE_ARCHITECTURE_v1.1.md  (ad82fbc 편입)
candidate v1.2  NOT_FOUND      ★ §1
decision        EA-C  KEEP_V1_1
downstream      D-21 진행 가능 (HARD STOP 아님) — §5
```

---

## 1. ★ v1.2 는 존재하지 않는다

지시는 "repo v1.1 과 Downloads v1.2 가 충돌한다" 였다. **충돌할 v1.2 가 없다.**

```
Downloads 전수            *EVIDENCE*ARCH*                     → 0건
Downloads 내용 grep        "EVIDENCE_ARCHITECTURE v1.2" 등      → 0건
                          (참조만 2건: PRODUCT_EXPANSION_DECISION_v1.0 ·
                                       PRODUCT_IMPLEMENTATION_HANDOFF_v1.0)
c:\tmp · c:\dev 전수                                          → v1.1 1건뿐
git log --all --name-only | grep EVIDENCE_ARCH                → v1.1 1개 경로만
대화 이력 전수 (jsonl 196MB)                                   → v1.1 붙여넣기 1건.
                                                                v1.2 본문 0건
```

### 1-1. 왜 v1.2 가 있다고 여겨졌는가 — 실제 원인

**v1.1 안에 v1.2 안건이 이미 반영돼 있다.**

```
v1.1 §2-1-A  "내부 분석 산출물에도 population_scope 를 요구한다 (v1.2 안건, 2026-08-27)"
```

즉 "v1.2" 는 **별도 문서가 아니라 v1.1 에 흡수된 개정 안건의 이름**이었다.
D-19 v1.3 과 **같은 종류의 착시**다 — 대화에서 언급된 버전명이 파일로 존재한다고 가정했다.

```
CANDIDATE_V1_2 = NOT_FOUND
DIFF_PERFORMED = NOT_APPLICABLE   (mechanical diff · semantic diff 모두 대상 부재)
```

**Downloads 를 SSOT 로 쓰지 않는다는 규율은 여기서도 유효하다** — 다만 이번엔
Downloads 에 아무것도 없었다.

---

## 2. 그래서 실제로 답해야 할 질문

diff 는 불가능하지만 **PHASE D 가 필요로 하는 질문은 그대로 남는다.**

> v1.1 구조가 D-19 v1.4 가 찾아낸 사실들을 표현할 수 있는가?
> 표현 못 하면 D-21 은 근거 없이 추정 설계가 된다.

아래는 v1.1 원문 대조 결과다.

---

## 3. C4 — v1.1 능력 평가

### 3-1. Threshold approval axis

| 요구 | v1.1 | 근거 |
|---|---|---|
| approval state | **없음** | §5 가 `threshold` 를 *"별도 승인된 판정 기준"* 이라고 **이름만 붙이고 DDL 을 주지 않는다** |
| approved_by / approved_at | 없음 | 〃 |
| basis / evidence linkage | 없음 | benchmark 에는 `selected_evidence_id` 가 있으나 threshold 엔티티가 없어 붙일 대상이 없다 |
| formula_id / formula_version | 없음(threshold 기준) | §3-0 `definition_mapping` 에는 있으나 그것은 **외부 evidence ↔ formula** 관계다 |
| threshold version | **없음** | 〃 |

```
THRESHOLD_APPROVAL_AXIS = NAMED_BUT_UNMODELED
```

★ 중요한 구분: v1.1 은 **틀린 모델을 갖고 있는 게 아니라 모델이 없다.**
§5 는 `benchmark_point / benchmark_trend / threshold` 3분리를 **선언**하고
앞의 둘만 설계했다. 세 번째는 의도적으로 비워 둔 자리다.

### 3-2. Policy ≠ Threshold 구분

| | v1.1 |
|---|---|
| 구분하는가 | **YES (부분)** |
| 근거 | §6-1 *"threshold (rule_configs 또는 operational_default) — severity 권한. **`code_default` 는 이 요건을 충족하지 않는다** — G3 ③"* |
| 문제 | §5 는 승인 판정을 `decision_status='APPROVED'` 가 한다고 못박고 *"두 개의 병렬 승인 메커니즘을 만들지 않는다"* 고 한다. 그런데 **D-19 실측: `country_kpi_policy` 에 수치 임계 컬럼이 없다.** (23컬럼 전부 정책 스위치) |

```
→ v1.1 은 "정책 승인" 과 "임계 승인" 이 같은 테이블에서 처리될 수 있다고 전제했다.
   그 전제가 D-19 로 반증됐다.  ★ v1.1 의 유일한 반증된 전제다.
```

### 3-3. Authority switch (`use_governance_benchmarks`)

```
v1.1 언급 횟수 = 0
§10 Non-goals: "operational_default 추출 / Rule Engine inline default 정비"  ← 명시적 범위 밖
```

```
AUTHORITY_SWITCH = NOT_REPRESENTABLE
```

GLOBAL scope 로 threshold authority 를 통째로 바꾸는 스위치가 존재한다는 것 자체가
v1.1 작성 시점에 알려지지 않았다. **누락이지 오류가 아니다.**

### 3-4. Formula linkage — threshold → formula

```
v1.1 §3-0 definition_mapping
  pigos_formula_id · pigos_formula_version  ← 있다
  "pigos_formula_version 이 올라가면 기존 mapping 은 자동 승계되지 않는다 — 재판정 대상"
  "mapping 자격: implementation_status 가 CONFIRMED 또는 valid NOT_APPLICABLE 만.
   AMBIGUOUS / UNRESOLVED_OUTSIDE_SCOPE 는 mapping 금지"
```

★ **AMBIGUOUS 차단 규율이 이미 존재한다.** 다만 적용 대상이
`external evidence ↔ formula` 이지 `threshold ↔ formula` 가 아니다.

```
FORMULA_LINKAGE = PATTERN_EXISTS_WRONG_SUBJECT
→ D-21 은 새 패턴을 발명할 필요가 없다. 같은 패턴을 threshold 에 적용하면 된다.
```

### 3-5. Evidence linkage 강도

| | v1.1 |
|---|---|
| immutable identity | **YES** — `claim_id` UUID 단일 PK, collector claim immutable |
| FK linkage | **YES** — serving row `selected_evidence_id FK → evidence_claim.claim_id` |
| version linkage | **YES** — `source_edition` · `event_seq` 단조증가 supersession |
| 적용 대상 | **benchmark 뿐.** threshold 는 여전히 `source_ref` 자유문자열 |

```
EVIDENCE_LINKAGE = SOLVED_FOR_BENCHMARK / ABSENT_FOR_THRESHOLD
```

### 3-6. Historical reproducibility

| 축 | v1.1 |
|---|---|
| formula version | YES (`pigos_formula_version`) |
| threshold version | **NO** |
| rule version | **NO** |
| evidence version | YES (`source_edition` · `event_seq`) |
| `as_of` | **NO** |
| source snapshot | 부분 — `effective_from`/`effective_to` 로 기간은 표현되나 값 스냅샷은 아님 |

```
HISTORICAL_REPRODUCIBILITY = 2 of 6 SOLVED
```

### 3-7. D-17 G3 — 표시 안전

```
benchmark unavailable   YES — §4 G3 "benchmark 가 없다고 카드를 숨기지 않는다.
                              농장 자기 값은 계속 보여주고 비교만 없앤다"
threshold unapproved    YES — §6-1 G3 ③ "code_default 는 요건을 충족하지 않는다"
formula ambiguous       ★ NO — mapping 은 금지하지만, 산식이 모호할 때
                              **화면에 무엇을 표시할지** 규정이 없다
```

D-19 §7-3 이 같은 결론에 도달했다: backend 에 *"산식 미확정이므로 판정 보류"* 상태가 없고
`formula_status` 를 읽는 코드가 0건이다.

### 3-8. D-19 13 source families

```
v1.1 전제      rule_configs / operational_default / code_default   (3종)
D-19 실측      13종  (S1~S13)
              그중 v1.1 이 모르는 것:
                S6  benchmarks 테이블 + severity_for()  (admin 전용)
                S7  farm_config → AlertThresholds
                S8  웹 프론트 자체 임계
                S9  scorecard 밴드
                S10 종합등급 개수 임계
                S11 질병 범주 임계
                S12 PSY 절대 밴드
                S13 DB 뷰 상수 (v_sow_npd 60일 캡)
```

```
SOURCE_FAMILY_COVERAGE = 3 / 13
```

★ 단, **S6~S13 중 KPI 카드 severity 를 만드는 것은 S8 하나뿐**(그것도 DORMANT)이다.
나머지는 별도 도메인(운영 알림·공개 스코어카드·값 상수)이다.
따라서 이것은 v1.1 의 **구조적 결함이 아니라 범위 미확장**이다.

### 3-9. D-21 overlap

```
v1.1 §8 결정 등록부에 D-21 없음.  D-19 까지만 등록돼 있다.
→ D-21 은 겹치는 것이 아니라 v1.1 이 비워 둔 자리(§3-1)를 채우는 신규 항목이다.
```

---

## 4. 판정

```
EA_DECISION = EA-C  KEEP_V1_1
canonical_version = v1.1  (변경 없음)
```

### 4-1. EA-A/EA-B 가 아닌 이유

승격·패치할 **대상 문서가 존재하지 않는다**(§1).

### 4-2. ★ EA-D 가 아닌 이유 — 중요

`EA-D NEW_VERSION_REQUIRED` 는 **구조가 현행을 담을 수 없을 때**다. 실측 결과:

| v1.1 구조 | 상태 |
|---|---|
| immutable claim + append-only verifier overlay | **건재** |
| `definition_mapping` 별도 엔티티 + version 재판정 규율 | **건재** |
| AMBIGUOUS mapping 차단 규율 | **건재. 주어만 바꾸면 재사용 가능** |
| rights × policy 2축 분리 | **건재** |
| G3 표시 안전 | **건재** (formula ambiguity 축만 미비) |
| serving provenance (`selected_evidence_id` + `effective_from/to`) | **건재. threshold 에 그대로 적용 가능** |
| `population_scope` 내부 산출물 확장 (§2-1-A) | **건재** |

**반증된 전제는 딱 하나다** — §3-2 의 "승인은 `country_kpi_policy.decision_status` 가
한다". 이것은 구조 붕괴가 아니라 **한 문장의 정정**이며, v1.1 자신이
§5 에서 threshold 를 별도 축으로 이미 선언해 두었으므로 **자기모순도 아니다.**

```
따라서 downstream HARD STOP 조건(§5 "Evidence Architecture 가
STRUCTURALLY_INCOMPATIBLE") 에 해당하지 않는다.  D-21 진행 가능.
```

---

## 5. D-21 로 넘기는 GAP — v1.1 이 비워 둔 자리

이 목록이 **D-21 의 헌장(charter)** 이 된다. 새로 발명할 것과 재사용할 것을 분리한다.

| # | GAP | v1.1 재사용 가능한 패턴 |
|---|---|---|
| **GAP-1** | threshold 엔티티 자체가 없다 (identity·scope·version) | §5 serving row 구조 |
| **GAP-2** | threshold 승인 축 없음 (`approval_state`/`approved_by`/`approved_at`) | §3-4 `APPROVED_TRANSFORM` 필수 동반 필드 패턴 |
| **GAP-3** | threshold ↔ formula linkage 없음 | §3-0 `definition_mapping` 의 `pigos_formula_id/version` + 재판정 규율 |
| **GAP-4** | threshold ↔ evidence linkage 없음 (`source_ref` 자유문자열) | §5 `selected_evidence_id` FK |
| **GAP-5** | `effective_from`/`effective_to`·supersession 없음 | §5 + §2-2 `event_seq` |
| **GAP-6** | authority switch 감사 불가 | **없음 — 신규 설계 필요** |
| **GAP-7** | formula AMBIGUOUS 시 표시 안전 미규정 | §4 G3 확장 |
| **GAP-8** | notification decision provenance 없음 | §5 serving provenance 사상 |

### 5-1. v1.1 에 남는 정정 1건 (D-21 확정 후)

```
§5 "리졸버는 decision_status='APPROVED' 행만 읽고 … 두 개의 병렬 승인 메커니즘을
    만들지 않는다"
→ country_kpi_policy 는 정책 스위치 승인이고, 수치 임계 승인은 별도 축이다.
  (병렬 승인이 아니라 서로 다른 대상에 대한 승인이다)
```

**지금 고치지 않는다.** D-21 이 threshold 승인 축을 확정한 뒤 한 번에 반영한다 —
확정 전에 문구만 바꾸면 근거 없는 서술이 된다.
