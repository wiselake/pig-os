# [D-19] PigOS Threshold Source Audit — Gate Run Spec v1.4

```yaml
document: D19_THRESHOLD_SOURCE_AUDIT_RUN
version: 1.4
document_status: ACCEPTED_SPEC

source_provenance:
  origin: conversation_paste          # 파일이 아니라 대화 붙여넣기였다
  source_version: 1.3
  source_form: RUN_WRAPPER_ONLY       # ★ v1.3 본문은 존재하지 않는다 (§0-1)
  source_received_at: 2026-08-28T04:22:57Z   # = 2026-08-28 13:22 KST
  imported_at: 2026-08-28
  repository_copy_previously_existed: false
  predecessor: NOT_FOUND            # v1.3 본문은 어디에도 존재하지 않는다 (§0-1)
  spec_lineage: RECONSTRUCTED_CANONICAL_SPEC
                                    # v1.3 을 읽고 patch 한 것이 아니다.
                                    # 래퍼의 규율을 승계하고 나머지는 신규 저작이다.
  validation_basis:
    - current repository HEAD (56bddaf)
    - docs/runs/RUN_PROMPT_D13_canonical_formula_audit.md v1.4 (70a56a9)
    - docs/kpi/CANONICAL_FORMULA_SPEC.md (a27afd8)
    - docs/kpi/CANONICAL_FORMULA_SPEC_REAUDIT.md (0bc8bc9)
  spec_case: CASE_B_UPGRADE_REQUIRED
```

> **정본은 이 파일이다.** Downloads·대화 붙여넣기를 SSOT 로 삼지 않는다.

---

## 0. v1.3 → v1.4 승격 근거

### 0-1. ★ v1.3 본문은 존재하지 않는다 — 먼저 이 사실부터

2026-08-28 에 전달된 v1.3 은 **실행 래퍼(run wrapper)** 였고, 그 첫 줄이

```
docs/runs/D19_THRESHOLD_SOURCE_AUDIT_RUN.md (v1.3) 를 먼저 전문 읽고,
그 스펙대로 실행한다.
```

였다. **그 파일은 어디에도 없다.**

```
repo working tree   find -iname "*THRESHOLD_SOURCE_AUDIT_RUN*"    → 0건
git 전 브랜치 이력   git log --all --name-only | grep …            → 0건
Downloads / c:\tmp / c:\dev (depth 4)                             → 0건
```

따라서 래퍼가 참조한 `§2~§8-B`, `§10 출력 형식`, `V-1~V-6 정의` 는 **판독 불가**다.

> ★ 이 사실을 숨기고 "v1.3 스펙대로 실행했다" 고 쓰면 **감사 자체가 위조**가 된다.
> v1.4 는 v1.3 래퍼에 담긴 규율을 승계하되, 판독 불가한 부분은 **신규 저작임을 명시**한다.

### 0-2. 그럼에도 CASE C 가 아닌 이유

CASE C 판정 기준은 **구조적 비호환**이다. 실측 결과 다음이 전부 유지된다.

| 전제 | v1.3 래퍼 | current HEAD | 판정 |
|---|---|---|---|
| 감사 단위 = rule | 40룰 전수 | 룰 레지스트리 존재 | 유지 |
| threshold data model | `rule_configs` / `operational_defaults` / DMV / code const / benchmark loader | 동일 5종 (+6번째 탐색 지시) | 유지 |
| resolution architecture | resolver chain + helper 관통 | 동일 | 유지 |
| provenance 축 | APPROVED / TENANT / CODE_DEFAULT / UNATTRIBUTED | 표현 가능 | 유지 |

**rule universe · threshold data model · resolution architecture 중 깨진 전제가 없다.**
부족한 것은 전부 **축 추가로 해결되는 확장**이다 → `CASE_B_UPGRADE_REQUIRED`.

### 0-3. v1.4 에서 추가한 것 (감사 결과는 쓰지 않는다)

| # | 추가 | 왜 |
|---|---|---|
| 1 | `formula_id` / `formula_version` / `formula_status` 필드 | v1.3 래퍼에 산식 축이 **아예 없다.** D-13 재실사(AMBIGUOUS 3)를 표현할 수단이 없음 |
| 2 | `migration_blocker` 에 `BLOCKED_BY_CANONICAL_AMBIGUITY` 추가 | v1.3 enum 4종은 사산(P0-2)·PWM(code alignment)·미판독(P0-1B)만 커버. FARROWING_RATE 같은 **산식 자체 모호**를 담을 값이 없다 |
| 3 | Path A / Path B **양방향** 전수 + `A ∩ B` 교차대조 | v1.3 은 "40룰 전수 추적"(Path A) 뿐. 과거 3회 오진이 전부 **한 방향만 본 것**이 원인이었다 |
| 4 | 상태축 명칭 분리 `D19_audit_status` / `D19_migration_status` / `G0C_gate_status` | 단독 `status` 가 `formula_status`·`platform_implementation_status` 와 충돌 |
| 5 | `provenance` enum 에 `BENCHMARK_DERIVED` · `NO_THRESHOLD` 명시 | v1.3 은 4종만. A-bench 룰과 무임계 룰을 넣을 칸이 없다 |
| 6 | `rule_count_confidence` (`CONFIRMED` / `PROVISIONAL`) | "더 있을 수 있음" 을 남긴 채 COMPLETE 선언하는 것을 구조적으로 차단 |
| 7 | Historical reproducibility 점검 항목 명시 | v1.3 은 V-3 이름만 있고 정의 판독 불가 |
| 8 | D-21 경계 명문화 | threshold identity / scope / version bump 를 D-19 가 결정하지 않는다 |

**금지**: 감사 결과를 스펙에 미리 써 넣지 않는다. current HEAD 에서 확인되지 않은
사실을 결과처럼 기록하지 않는다.

### 0-4. v1.3 래퍼에서 **그대로 승계**한 것

머신 게이트 · 실행환경 고정 · 절대 금지 목록 · Baseline 기록 · provenance 판정 규율
(특히 `source_ref` 만으로 APPROVED 부여 금지) · 모집단 규율 · US 주의 · 종료 검증 ·
판정 원칙(`APPROVED_POLICY 0건은 실패가 아니다`).

---

## 1. 목적

> 현재 PigOS HEAD 기준 threshold source / resolution / provenance /
> formula linkage / migration blocker 를 **사실감사** 하여
> **G0-C 와 D-21 의 유효 입력**을 만든다.

D-19 는 **사실만 제공한다.** §17 의 D-21 경계를 넘지 않는다.

---

## 2. 하드 게이트

### 2-1. 머신 게이트 (다른 어떤 명령보다 먼저)

`hostname` 이 `bjh` 가 아니면 즉시 중단.
`STOP_REASON: MACHINE_GATE_FAIL / hostname=<값>` 만 출력.
특히 `brian` 이면 무조건 중단 — pull-only 미러다. **부분 수행 금지.**

### 2-2. 실행 환경 고정

```
$env:PYTHONDONTWRITEBYTECODE = '1'
pytest 사용 시 -p no:cacheprovider
```

세션 동안 해제하지 않는다. `__pycache__`/`.pytest_cache` 는 gitignore 라
`git status` 대조를 그대로 통과하므로 환경변수 외에 막을 방법이 없다.

### 2-3. 절대 금지

```
소스 수정 / 테스트 수정 / migration / seed 변경
DB 쓰기 전건 (SELECT only)
feature flag 값 변경 — 특히 stillborn.rate_high
  (켜면 BR 이 8.20 → 8.00 으로 조여진다. 유일한 파일럿 국가다)
formatter / 자동 fix / refactor
```

### 2-4. 선행 확인

`docs/kpi/CANONICAL_FORMULA_SPEC.md` 부재 → `STOP_REASON: D13_NOT_COMPLETE`.
D-19 는 D-13 산출물을 기준으로 한다.

### 2-5. 산출물 경로

```
docs/kpi/D19_THRESHOLD_SOURCE_AUDIT_v1.4.md
```

기존 `docs/kpi/D19_THRESHOLD_SOURCE_AUDIT.md` 는 **1차 감사 기록이다. 덮어쓰지 않는다.**
(`prior_status = HISTORICAL_EVIDENCE`, `prior_reusable = NO`)

---

## 3. Baseline (분석 전 기록)

```
machine · pigos_commit · working_tree_before(git status --short 전문)
alembic_heads · canonical_spec_present · db_connection
test_collection_cmd · collected_tests
flag_states_before      ← 없으면 종료 시 "flag 안 건드렸다" 를 증명 못 한다
```

추가 (v1.4):

```
D19_audit_target_commit
D19_audit_date
D19_spec_version
D13_reference_version = repository canonical run spec v1.4
D13_reference_commit
```

**prior run 의 숫자를 복사하지 않는다.**

---

## 4. 상태 축 — 명칭 분리 (v1.4 신설)

단독 `status` 사용 금지.

```
D19_audit_status       COMPLETE | PARTIAL | BLOCKED
D19_migration_status   READY | BLOCKED_BY_* | NOT_APPLICABLE
G0C_gate_status        PASS | BLOCKED
```

기존 축과 혼동 금지:
`formula_status` · `runtime_verification_status` ·
`platform_implementation_status` · `parity_result`.

### 4-1. 세 축은 독립이다

다음 조합은 **정상**이다.

```
D19_audit_status      = COMPLETE
FARROWING_RATE
  D19_migration_status = BLOCKED_BY_CANONICAL_AMBIGUITY
G0C_gate_status       = BLOCKED
```

AMBIGUOUS 가 있다고 감사를 중단하거나 행을 제거하지 않는다.

---

## 5. STEP 1 — Threshold source discovery

기확인 5종을 **완전한 목록으로 확정하지 말 것.**

```
rule_configs
operational_defaults
룰 내 code_default 폴백
default_metric_values
kpi_service.py 벤치마크 로더
```

**6번째 소스가 있다는 전제로 탐색한다.**
대상: DB view/trigger · 시드 스크립트 · 환경변수 · 프론트 자체 임계 · feature flag.

---

## 6. STEP 2 — Resolution order

**코드 본문에서 도출한다.** 실제 call graph 로 단일 순서를 확정할 수 없으면

```
AMBIGUOUS_ORDER
```

로 기록한다. **추정 order 생성 금지.**

---

## 7. STEP 3 — 룰 전수 재실측 (★ v1.4 강화)

> prior 결과(`B-resolve 29 / A-bench 3 / no-threshold 8`)를 **답으로 가정하지 않는다.**
> 표본 추출 금지.

### 7-1. Path A — rule 정의에서 시작

```
rule definition → handler/helper → threshold reference → resolver → source
```

결과 `A = 전 rule 의 threshold source mapping`

### 7-2. Path B — severity 산출지점에서 시작 (역방향)

```
severity output → comparison → threshold read → resolver/helper → source → owning rule
```

결과 `B = 전 severity path 의 threshold/rule mapping`

> ★ Path B 를 신설한 이유: 과거 3회 오진이 전부 **한 방향만, 한 단계만** 본 결과였다.
> 핸들러 본문만 grep 해 `_common.resolve()` 를 놓친 것이 대표 사례다.

### 7-3. ★ 전수 완료 기준

다음을 **모두** 충족해야 `rule_count` 를 확정한다.

```
[ ] 모든 rule definition 이 A 에 포함
[ ] 모든 severity output path 가 B 에 포함
[ ] A 에는 있는데 B 에 없는 항목 설명 완료
[ ] B 에는 있는데 A 에 없는 항목 설명 완료
[ ] no-threshold rule 설명 완료
[ ] helper/indirect resolver 경유 추적 완료
[ ] A ∩ B 교차대조 완료
[ ] orphan rule 0 또는 orphan 사유 기록
[ ] orphan severity path 0 또는 orphan 사유 기록
```

전부 충족 → `rule_count_confidence = CONFIRMED`
하나라도 미충족 → `rule_count_confidence = PROVISIONAL` · `D19_audit_status = PARTIAL`

**보고서에 "더 있을 수 있음" 을 남긴 상태로 COMPLETE 를 선언하지 않는다.**

---

## 8. 룰별 필수 데이터

각 applicable rule 에 대해:

```
rule_id
rule_name
threshold_source
threshold_source_type
source_location
resolution_order
fallback
formula_id            ← v1.4 신설
formula_version       ← v1.4 신설
formula_status        ← v1.4 신설 (D-13 canonical 참조)
data_origin
evidence_link
approval_status
tenant_config
D19_migration_status
migration_blocker
notes
```

---

## 9. Provenance 정규화

```
APPROVED_POLICY
UNATTRIBUTED
TENANT_CONFIG
CODE_DEFAULT
BENCHMARK_DERIVED     ← v1.4 명시
NO_THRESHOLD          ← v1.4 명시
```

### 9-1. APPROVED_POLICY 부여 규율 (v1.3 승계 — 이 감사의 핵심)

- `operational_defaults.origin` 은 스키마 사실이므로 그대로 신뢰
- **`default_metric_values.source_ref` 만으로 `APPROVED_POLICY` 를 부여하지 말 것.**
  `threshold_basis`(유도 근거)가 함께 있고 값과 정합할 때만 후보다.
  > 관찰: `STILLBORN_RATE` 4행 중 BR 만 8.20 이고 KR/US/SYSTEM 이 8.00 으로 동일,
  > `threshold_basis` 는 SYSTEM 한 행에만 있다. 서로 다른 출처가 소수점 둘째 자리까지
  > 같은 값을 독립 산출할 개연성은 낮다 → `source_ref` 가 **사후 귀속**일 가능성을
  > 배제할 수 없다. 이 가설을 판정하라는 게 아니라, **판정 불가하므로 UNATTRIBUTED
  > 로 둔다**는 뜻이다.
- 코드 상수는 무조건 `CODE_DEFAULT`
- 결재 이력을 못 찾으면 `APPROVED_POLICY` 로 만들지 않는다.
- **`APPROVED_POLICY = 0` 이 나오는 것이 정상적인 결과다.** 0 을 억지로 실패 처리하지
  않는다. 대신 현재 severity source 를 정확히 기술한다.

---

## 10. `migration_blocker` — 하나로 뭉개지 말 것

```
NONE
BLOCKED_BY_P0_2_DECISION          사산 계열 — 미라 포함 여부는 정책 선택
BLOCKED_BY_CODE_ALIGNMENT         PWM — 정책 선택 아님. 버그 수정 트랙.
                                  결재 대기열에 넣지 말 것
BLOCKED_BY_P0_1B_TRACE            본문 미판독
BLOCKED_BY_CANONICAL_AMBIGUITY    ← v1.4 신설.
                                  D-13 canonical 에서 formula_status = AMBIGUOUS
                                  라 threshold 를 어느 산식에 붙일지 특정 불가
```

---

## 11. 모집단 규율 (필수)

통계는 `farms.data_origin` 으로 **반드시 분리**한다.

```
pigplan_migration = INTERNAL_REFERENCE
native_signup     = LIVE_CUSTOMER
```

합산 수치는 **합산 사실을 명시하지 않으면 기재 금지.**
운영 영향 판정은 `LIVE_CUSTOMER` 모집단으로만 한다.

---

## 12. Formula linkage 교차검증

대상: `PSY` · `NPD` · `FARROWING_RATE` · **사산 계열** · `PWM`

**repository D-13 canonical 의 현재 상태를 사용한다. prior run 상태 복사 금지.**

`formula_status = AMBIGUOUS` 인 지표는 threshold 를 어느 산식에 귀속시킬지
특정할 수 없으므로 `BLOCKED_BY_CANONICAL_AMBIGUITY` 로 기록하되,
**감사 자체는 수행한다**(§4-1).

---

## 13. US Activation

current HEAD 에서 추적:

```
어떤 threshold 가 발화하는가
formula_id / formula_version 은 무엇인가
formula_status 는 무엇인가
APPROVED evidence 가 있는가
benchmark 가 severity 에 사용되는가
CODE_DEFAULT 가 발화하는가
```

**prior 판정 재사용 금지.**

> ★ 과거 3회 오류난 지점: `country_kpi_policy` 에 US 행이 없다는 사실로부터
> `default_metric_values` 에도 없다고 **추론하지 말 것. 다른 테이블이다.**
> 실측으로 확인하고 기록한다.

---

## 14. BR / G3

다음 상태에서 **backend 판정 경로**를 감사한다.

```
benchmark unavailable
threshold unapproved
formula ambiguous
```

Mobile rendering 은 **범위 밖** — `docs/PLATFORM_PARITY.md` 가 별도 관리한다.

---

## 15. Versioning Design Input V-1 ~ V-6

> ★ **정직 고지**: v1.3 본문 부재로 V-1~V-6 의 **원문 정의를 판독할 수 없었다**(§0-1).
> 아래는 v1.4 에서 **새로 정의한 것**이다. v1.3 래퍼에서 유일하게 판독된 것은
> V-6 의 산출 요구뿐이며, 그 문장은 §15-6 에 원문 그대로 보존한다.

| # | 정의 | 산출물 |
|---|---|---|
| **V-1** | code-default ↔ rule mapping | 어떤 룰이 코드 상수에 의존하는가 |
| **V-2** | current threshold identity observation | 지금 threshold 를 무엇으로 식별하는가 (key 구성) |
| **V-3** | historical reproducibility | 과거 severity 를 지금 재현할 수 있는가 (§16) |
| **V-4** | migration dependency / blocker | 무엇이 먼저 풀려야 승격 가능한가 |
| **V-5** | evidence linkage state | threshold ↔ 근거 문서 연결 상태 |
| **V-6** | snapshot versioning 관측 | 아래 원문 요구 |

### 15-6. V-6 — v1.3 래퍼 원문 (유일하게 판독된 V 정의)

```
V-6(스냅샷 versioning) 결과에 What Changed 착수 판정을 반드시 병기할 것:
  VERSIONED → 병렬 가능 / TIMESTAMPED_ONLY|OVERWRITTEN → as_of 선행 필요
```

**V-6 를 추정하지 않는다.** 위 원문대로 산출한다.

---

## 16. Historical reproducibility (V-3 세부)

**현재 severity 계산 가능성**과 **과거 동일 결과 재현 가능성**을 구분한다.

각 항목의 **존재 여부**를 기록한다.

```
[ ] formula version
[ ] threshold version
[ ] rule version
[ ] evidence version
[ ] as_of
[ ] historical source data state
```

---

## 17. D-21 경계

D-19 는 **사실만 제공**한다. 다음을 **최종 결정하지 않는다.**

```
threshold identity model
scope model
version bump rule
```

전부 **D-21 소관**이다.

---

## 18. 종료 검증

```
git status --short 를 baseline 과 대조 → 차이는 산출물 1건뿐
flag_states_after == flag_states_before
DB write count = 0 (실행 쿼리 전부 SELECT 임을 명시)
```

소스 수정 흔적 → `STOPPED / UNEXPECTED_SOURCE_MODIFICATION`. **직접 되돌리지 말 것.**
flag 값 변경 → `STOPPED / FLAG_STATE_CHANGED`. **임의 복구 금지. 즉시 보고.**

---

## 19. 판정 원칙

```
APPROVED_POLICY 0건 / AMBIGUOUS_ORDER / NOT_REPRODUCIBLE 은 실패가 아니다.
근거 없이 APPROVED_POLICY 를 만들거나 순서를 추론하는 것이 실패다.
```

---

## 20. 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| 1.3 | 2026-08-28 | 대화 래퍼로만 전달. **본문 부재**(§0-1) |
| 1.4 | 2026-08-28 | repo 정본화. 산식 축(`formula_id`/`version`/`status`) 신설 · `BLOCKED_BY_CANONICAL_AMBIGUITY` 추가 · Path A/B 양방향 전수 + `A ∩ B` 완료 기준 · 상태축 명칭 분리 · provenance enum 2종 명시 · `rule_count_confidence` · V-1~V-5 신규 정의(V-6 원문 보존) · D-21 경계 명문화 |
