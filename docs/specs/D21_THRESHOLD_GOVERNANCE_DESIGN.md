# D-21 — Threshold Governance 설계

```
status            PROPOSED — 승인 전. 이 문서의 어떤 항목도 APPROVED 가 아니다.
design_status     COMPLETE
persistence       NOT_IMPLEMENTED  (사유 §9 — 의도적 보류)
inputs            docs/kpi/D19_THRESHOLD_SOURCE_AUDIT_v1.4.md   (사실)
                  docs/kpi/EVIDENCE_ARCHITECTURE_V1_2_REVIEW.md (GAP-1~8)
                  docs/specs/COUNTRY_KPI_EVIDENCE_ARCHITECTURE_v1.1.md (재사용 패턴)
                  docs/runs/RUNTIME_INTEGRITY_AUDIT_20260828.md (알림 재현성)
scope_boundary    D-19 는 사실만 제공했다. 여기서 identity·scope·version 을 정한다.
```

> **D-19 사실을 재감사하지 않는다.** 아래 숫자는 전부 D-19 v1.4 실측값이다.

---

## 1. 무엇을 고치는가 — 결함 목록

```
APPROVED_POLICY = 0                     승인된 임계가 0건이다
threshold approval axis 자체가 없다      ★ 결재를 해도 기록할 컬럼이 없다
DMV 임계 68행 중 UNATTRIBUTED 56행       근거 미상
threshold version 없음                   언제 무엇이 바뀌었는지 모른다
historical reproducibility 없음          과거 severity 재현 불가 (V-3)
notification provenance 없음             고객 대면 알림 468건의 판정 근거 없음
authority source switch 감사 없음        GLOBAL flag 변경이 기록되지 않는다
formula ambiguity/revocation linkage 없음 AMBIGUOUS 산식에도 임계가 붙는다
```

### 1-1. ★ 가장 중요한 한 줄

> **`APPROVED_POLICY = 0` 은 "아직 결재를 안 받았다" 가 아니라 "결재를 기록할 곳이 없다" 다.**

`country_kpi_policy` 에 `decision_status='APPROVED'` 28행이 있지만 그 테이블은
정책 스위치(`compute_enabled`·`rule_enabled`·`benchmark_exposure`)만 담고
**수치 임계 컬럼이 없다.** 대표가 오늘 사산율 8.0% 를 결재해도 그 사실을 넣을 자리가 없다.

---

## 2. P0-2 순서 정정 ★

```
금지된 순서   대표 결재 → 문서 기록
             (기록 매체가 문서면 코드·DB 와 어긋나고, 어긋난 것을 아무도 모른다)

새 순서
  1. threshold approval / version / evidence identity 를 기록할 구조를 만든다
  2. P0-2 decision (사산 산식 + 기준값)
  3. 승인 상태를 그 구조에 persistence
```

**D-21 이 P0-2 를 대신 결정하지 않는다.** 사산 산식이 A(사산만)냐 B(사산+미라)냐는
여전히 대표 결재 사항이다. D-21 은 **그 결정을 담을 그릇**만 만든다.

---

## 3. Identity model — 무엇이 threshold 하나를 식별하는가

### 3-1. 현재 관측 (D-19 V-2) — 축이 섞여 있다

```
rule_configs          key = rule_id
operational_defaults  key = (rule_id, country_code, scope)
default_metric_values key = (scope_type, scope_code, metric_code)
benchmarks            key = (country_code, kpi_code)
farm_config           key = (farm_id, config_key)
```

한 지표에 이름이 넷이다:

```
pwmr.high              rule_id
PRE_WEANING_MORTALITY  metric_code (DMV)
PWMR                   룰이 실제로 읽는 키 (로더 별칭)
prewean_mortality      governance kpi_code
```

### 3-2. 결정 — `metric_code` 를 정본 축으로 한다

| 후보 | 채택 | 이유 |
|---|---|---|
| `rule_id` | ✗ | 룰은 표현이고 임계는 지표의 속성이다. 한 지표에 룰이 여럿일 수 있다 |
| **`metric_code`** | **✓** | 현재 **live authority(DMV)** 의 축이고 `formula_id` 와 1:1로 붙는다 |
| `kpi_code` (governance) | ✗ | `benchmarks` 테이블 축. severity 경로에 연결돼 있지 않다(admin 전용) |

```
threshold_identity = (metric_code, scope_type, scope_code)
```

**별칭은 identity 가 아니라 매핑이다.** `pwmr.high → PWMR → PRE_WEANING_MORTALITY`
연결은 별도 alias 표로 명시한다(§3-3). 코드 안 로더에 숨겨 두지 않는다.

### 3-3. Alias — 지금 코드에 숨어 있는 것을 데이터로 꺼낸다

```
현재:  kpi_service._all_benchmarks 가 "PRE_WEANING_MORTALITY" → "PWMR" 을
       코드에서 별칭 처리한다 (D-19 §5-2)
목표:  metric_alias(alias, canonical_metric_code, kind)
       kind ∈ {RULE_KEY, LEGACY_NAME, GOVERNANCE_CODE}
```

★ 이것이 없으면 "이 임계가 어느 지표 것인가" 를 코드를 읽어야만 알 수 있다.

### 3-4. Scope model

`effective_metric_values()` 의 현행 순서를 **그대로 승계**한다. 새 축을 만들지 않는다.

```
farm → region → market → system
```

```
scope_type ∈ {farm, region, market, system}
scope_code   farm=farm_id · region=country_code · market=market_code · system='SYSTEM'
```

> `market` 은 프로덕션 0행이지만 함수에 이미 있다. 제거하지 않는다 — 제거는 별건이다.

---

## 4. Version model

### 4-1. 무엇이 버전을 올리는가

```
version bump 대상 = 판정 결과를 바꿀 수 있는 것
  warning_threshold / critical_threshold 값
  alert_direction
  formula_id / formula_version   ← 같은 값이라도 다른 산식이면 다른 임계다
  scope

version bump 아님 = 판정에 영향 없는 것
  note · source_ref 오탈자 · unit_code 표기
```

### 4-2. 구조 — v1.1 §2-2 append-only 패턴 재사용

```
threshold_version   단조증가 정수. (metric_code, scope_type, scope_code) 내에서.
supersedes          이전 version 을 명시. 갱신이 아니라 승계다.
effective_from / effective_to   기간. NULL end = 현재 유효.
```

**행을 UPDATE 하지 않는다.** 현재 DMV 는 `updated_at` 으로 덮어쓰기 때문에
"2026-07-08 이전에는 값이 무엇이었나" 를 답할 수 없다. 그것이 V-3 `NOT_REPRODUCIBLE`
의 한 축이다.

---

## 5. Approval axis

### 5-1. 필드

v1.1 §3-4 `APPROVED_TRANSFORM` 의 "한 줄만 저장하면 loophole 이 된다" 규율을 그대로 적용한다.

```yaml
approval_state:      DRAFT | PROPOSED | APPROVED | REVOKED | SUPERSEDED
approved_by:         # 사람. 시스템 계정 금지
approved_at:
approval_reason:     # 무엇을 근거로 승인했는가 (자유문장 아님 — §5-2)
evidence_claim_id:   # FK → evidence_claim.claim_id  (v1.1 §5 selected_evidence_id 패턴)
formula_id:          # FK → canonical formula
formula_version:
authority_source:    APPROVED_POLICY | TENANT_CONFIG | CODE_DEFAULT
                     | BENCHMARK_DERIVED | UNATTRIBUTED
```

### 5-2. `APPROVED` 부여 규율 (D-19 §9-1 승계)

```
source_ref 문자열만으로 APPROVED 를 부여하지 않는다.
evidence_claim_id 가 실제 claim 을 가리키고, formula_id/version 이
CONFIRMED 상태여야 후보가 된다.
승인 이력을 못 찾으면 UNATTRIBUTED 로 둔다. APPROVED 를 만들지 않는다.
```

### 5-3. ★ 기존 68행을 자동 승격하지 않는다

```
마이그레이션 시 전 DMV 행의 초기값:
  approval_state   = UNATTRIBUTED  (56행)  /  DRAFT (근거 있는 12행)
  approved_by      = NULL
  evidence_claim_id= NULL
```

**자동 승격은 위조다.** 지금 쓰이고 있다는 사실은 승인의 근거가 아니다.

---

## 6. Formula linkage

v1.1 §3-0 `definition_mapping` 의 규율을 **주어만 바꿔** 재사용한다
(EA 리뷰 §3-4 `PATTERN_EXISTS_WRONG_SUBJECT`).

```
v1.1:  external evidence ↔ pigos_formula_id/version
       "mapping 자격: implementation_status 가 CONFIRMED 또는 valid NOT_APPLICABLE 만.
        AMBIGUOUS / UNRESOLVED_OUTSIDE_SCOPE 는 mapping 금지"

D-21:  threshold ↔ formula_id/version
       동일 규율. AMBIGUOUS 산식에는 APPROVED threshold 를 붙일 수 없다.
       formula_version 이 올라가면 threshold approval 은 자동 승계되지 않는다 — 재판정.
```

### 6-1. 현행 적용 결과 (D-19 §5 기준)

| 지표 | formula_status | threshold 승인 가능? |
|---|---|---|
| PSY | CONFIRMED | 가능 |
| NPD | CONFIRMED | 가능 |
| FARROWING_RATE | AMBIGUOUS (산식 4개) | **불가** |
| 사산 계열 | AMBIGUOUS (산식 2개) | **불가 — P0-2 선행** |
| PWM | AMBIGUOUS (분모 3종) | **불가 — code alignment 선행** |

★ 즉 **P0-2 를 결재해도 사산 임계를 바로 APPROVED 로 만들 수 없다.**
산식 확정 → code alignment → D-13 재실사 CONFIRMED → 그 다음이 threshold 승인이다.

---

## 7. Gate semantics

### 7-1. 발화 조건

numeric threshold 가 severity 를 결정하려면:

```
formula_status ∈ {CONFIRMED, valid NOT_APPLICABLE}
AND threshold_version = current
AND approval_state = APPROVED
AND evidence linkage valid
AND scope match
AND effective_from <= as_of < effective_to
```

### 7-2. ★ enforce-on-write 를 바로 켜지 않는다

현재 `APPROVED = 0` 이므로 위 게이트를 즉시 강제하면 **전 국가 severity 가 사라진다.**
BR 파일럿 포함 71농장 전건이다.

```
Phase 1  OBSERVE   게이트를 계산해 kpi_status.reason 과 로그에만 남긴다. 발화는 그대로.
                   → "지금 발화 중인 것 중 몇 %가 게이트를 통과하는가" 를 실측
Phase 2  WARN      통과 못 하는 임계에 UI 표시(참고치) 부착
Phase 3  ENFORCE   국가 단위로 순차 적용. BR 파일럿부터.
```

`insufficient` + `reason` 어휘가 이미 있으므로(`no_policy`·`policy_pending`)
**새 상태를 만들지 않고** Phase 1 을 시작할 수 있다.

---

## 8. `use_governance_benchmarks` — GLOBAL_THRESHOLD_AUTHORITY_SWITCH

### 8-1. 분류

```
classification = GLOBAL_THRESHOLD_AUTHORITY_SWITCH
current_value  = FALSE (프로덕션 실측, 2026-08-28)
scope          = GLOBAL — 국가·테넌트·농장 분기 없음
```

D-19 §2-3 실측: 이 flag 를 켜면 국가별 DMV 임계가 글로벌 `code_default` 로 통째로
교체된다. BR 사산 8.20→8.00, US PWMR 14/18→15/20, US WSI 7/9→10/14 등 최소 8건.

### 8-2. 감사 요구

```
authority_config_event
  changed_at · changed_by(role) · old_authority · new_authority · reason
  affected_scope · affected_metric_count
```

현재는 **변경 기록이 어디에도 남지 않는다.** env 2줄 + 컨테이너 재시작이면 바뀌고
그 사실을 사후에 알 방법이 없다(D-19 실측: admin API 0 · admin UI 0 · audit log 0).

### 8-3. 이번 범위에서 하지 않는 것

```
flag 값 변경        금지 (OFF 유지)
코드에서 flag 제거   강제하지 않음
```

flag 제거는 `operational_defaults` 를 승격 경로로 쓸지 폐기할지가 정해진 뒤의 일이다.

---

## 9. ★ Persistence 를 구현하지 않은 이유 — 명시

`design_status = COMPLETE` 이지만 `persistence = NOT_IMPLEMENTED` 다.
**할 수 있었는데 안 한 것이며, 그 이유를 남긴다.**

### 9-1. 하지 않은 것

```
Alembic migration
ORM 모델 / repository / service
validation
```

### 9-2. 이유 셋

**① 스키마만 먼저 만드는 것은 금지 규율에 걸린다.**

`threshold_decision_events` 를 지금 만들어도 **쓰는 주체가 없다.** 승인 플로우
(누가 어디서 승인하는가)가 정해지지 않았고, P0-2 결정도 나지 않았다.
비어 있는 테이블은 설계를 검증하지 못한다 — 실행 지침의
*"일단 schema 를 만들고 보자 금지"* 에 정확히 해당한다.

**② DMV 는 live authority 다. 무인 실행 중에 건드릴 대상이 아니다.**

`default_metric_values` 는 지금 71농장의 severity 를 만들고 있는 테이블이다.
컬럼 추가 자체는 additive 지만, 그 위에서 도는 `effective_metric_values()` 함수와
`_all_benchmarks` 로더가 `SELECT *` 를 쓴다. 마이그레이션·호환성 계획을
**작성과 동시에 무인으로 적용**하는 것은 이 프로젝트가 지금까지 지켜온 규율에 어긋난다.

**③ formula linkage 의 대상이 아직 없다.**

§6-1 대로 5개 대표 지표 중 3개가 AMBIGUOUS 다. `formula_id` 컬럼을 만들어도
채울 값이 PSY·NPD 둘뿐이다. **P0-2 와 PWM code alignment 가 선행이다.**

### 9-3. ★ Persistence GO trigger (2026-08-31 확정)

세 조건이 **전부** 충족되면 그날 구현 단계로 넘긴다. 하나라도 비면 대기한다.

```
① P0-2 canonical 확정
     D-2026-001 이 APPROVED  (현재 PROPOSED — 사산 = (stillborn+mummified)/total_born)
   +
② threshold approver / path 확정
     D-2026-002 가 APPROVED  (현재 PROPOSED — Decision Register 를 승인 SSOT 로)
     ★ actor ID 체계가 정해져야 approved_by 를 쓸 수 있다
   +
③ formula CONFIRMED 재실사
     code alignment → regression → D-13 재실사 → formula_status = CONFIRMED
        ↓
     D-21 PERSISTENCE GO
```

승인 기록: `docs/kpi/DECISION_REGISTER.md`

### 9-4. GO 이후에도 남는 개발 선행조건

```
[ ] PWM code alignment (정책 아님. 버그 수정 트랙)
[ ] FARROWING_RATE reachability 정리 (live 산식 4개 중 무엇을 canonical 로)
[ ] DMV 마이그레이션 호환성 계획 (SELECT * 사용처 3곳 확인)
```

이 셋은 **사람 결정이 아니라 개발**이라 GO trigger 와 분리한다.

---

## 10. 최소 구조 — 확정 시 만들 것 (참고)

과잉설계 금지 규율에 따라 **신규 테이블 2 + 컬럼 추가 2** 로 끝낸다.
22개 엔티티 온톨로지를 만들지 않는다.

| # | 대상 | 성격 |
|---|---|---|
| 1 | `default_metric_values` **+ 거버넌스 컬럼** | 현재 상태. identity·approval·version·linkage |
| 2 | `threshold_decision_events` (신규, append-only) | 승인·폐기·버전 승계 이력 (v1.1 §2-2 패턴) |
| 3 | `authority_config_events` (신규, append-only) | §8-2 GLOBAL switch 감사 |
| 4 | `notifications.decision_provenance` (JSONB) | §11 |
| — | `metric_alias` | §3-3. 코드에 숨은 별칭을 데이터로 (선택) |

**새 리졸버를 만들지 않는다.** `effective_metric_values()` 가 계속 authority 다.
거버넌스 컬럼은 그 함수가 읽는 행에 **부착**되는 것이지 병렬 경로가 아니다
(v1.1 §5: *"두 개의 병렬 승인 메커니즘을 만들지 않는다"*).

---

## 11. Notification decision provenance

### 11-1. 문제

고객 대면 알림 468건(CRITICAL 318 / WARNING 150)에 판정 근거가 없다.

```
notifications 컬럼   severity 는 있다
                    threshold 값 없음 · authority 없음 · formula version 없음 · as_of 없음
→ "이 CRITICAL 은 왜 떴는가" 를 사후에 답할 수 없다
```

### 11-2. 최소 설계 — JSONB 한 덩어리

정규화 컬럼 6개를 새로 만들지 않는다. 알림은 append-only 이벤트라
스냅샷 blob 이 구조적으로 맞다.

```jsonc
notifications.decision_provenance  JSONB NULL
{
  "as_of": "2026-08-28",
  "metric_code": "WSI",
  "formula_id": "WSI_WEAN_TO_SERVICE",
  "formula_version": 1,
  "threshold": {"warning": 7.0, "critical": 9.0, "direction": "above"},
  "threshold_identity": {"scope_type": "region", "scope_code": "US"},
  "threshold_version": 3,
  "authority_source": "UNATTRIBUTED",
  "severity": "CRITICAL"
}
```

### 11-3. ★ 과거 468건을 backfill 하지 않는다

지금 임계로 역산하면 **그때 그 판정의 근거가 아니라 오늘의 추정**이 된다.
D-19 A3 로 authority 가 DMV 였음은 확인됐지만(2026-07-20~), 그것과
"각 알림이 어느 값으로 만들어졌는가" 는 다른 질문이다.

```
과거 468건  historical_reproducibility = NOT_REPRODUCIBLE   (유지)
신규 알림    provenance 저장 (구현 시점 이후)
```

---

## 12. D-19 ↔ D-21 경계 확인

| 항목 | D-19 | D-21 |
|---|---|---|
| 무엇이 severity 를 만드는가 | 사실 제공 (13 소스) | — |
| identity 축을 무엇으로 할 것인가 | 관측만 (이름 4개) | **결정** (§3-2) |
| scope model | 관측만 | **결정** (§3-4 — 현행 승계) |
| version bump 규칙 | 부재 관측 | **결정** (§4-1) |
| 승인 축 | `APPROVED=0` 실측 | **설계** (§5) |
| flag 위험 | 실측 (8건 변동) | **분류 + 감사 요구** (§8) |

---

## 13. 결정 등록부 (전건 PROPOSED)

| ID | 내용 | 선행 |
|---|---|---|
| D-21-a | identity = `(metric_code, scope_type, scope_code)` | 없음 |
| D-21-b | scope model = 현행 `effective_metric_values` 승계 | 없음 |
| D-21-c | version bump 대상 = 판정 결과를 바꾸는 것 | 없음 |
| D-21-d | approval 축을 DMV 에 부착 (병렬 리졸버 금지) | 호환성 계획 |
| D-21-e | 기존 68행 자동 승격 금지 | 없음 |
| D-21-f | gate 는 OBSERVE → WARN → ENFORCE 3단계 | D-21-d |
| D-21-g | flag = `GLOBAL_THRESHOLD_AUTHORITY_SWITCH`, 감사 필수 | 없음 |
| D-21-h | notification provenance = JSONB, backfill 금지 | D-21-d |

**어느 것도 아직 APPROVED 가 아니다.**

승인이 필요한 항목은 `docs/kpi/DECISION_REGISTER.md` 에 별도 decision 으로 등재한다.
이 표는 **설계 항목**이고, 그 문서는 **승인 기록**이다. 둘을 섞지 않는다.
