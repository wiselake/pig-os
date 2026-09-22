# AI 기능 확장 — CURRENT_STATE_AUDIT (§13-A)

```
Mode      READ-ONLY 코드 실측. 추정 금지 (설계 프롬프트 §1)
Date      2026-08-28
Baseline  main @ 815ee1f
판정      CONFIRMED / PARTIAL / MISSING / AMBIGUOUS
```

> **질문에 대한 답부터**: 설계 프롬프트의 내용은 **대부분 반영돼 있지 않습니다.**
> 다만 **원칙(§0)과 일부 기반은 이미 서 있고**, 몇 가지는 예상보다 많이 돼 있습니다.
> 아래는 추정이 아니라 코드에서 확인한 결과입니다.

---

## 0. 요약

| 영역 | 판정 | 한 줄 |
|---|---|---|
| §0-1 AI 판정 금지 원칙 | **CONFIRMED** | 구조로 강제됨. Rule Engine이 판정, LLM은 번역만 |
| §0-2 국가 계층 | **CONFIRMED** | GLOBAL→COUNTRY→FARM_TYPE→TENANT 리졸버 동작 |
| §0-3 Evidence 메타데이터 | **PARTIAL** | 컬럼은 있으나 **서빙이 무시**. 승인 이력 0건 |
| Stage 1 Basic Analysis | **PARTIAL** | KPI Summary 있음 · **What Changed 없음** |
| Stage 2 Root Cause / Action | **PARTIAL** | Finding에 causes/actions 있음 · **Diagnosis 모델 없음** · Task 모델 **있음** |
| Stage 3 Goal / Plan / Simulation | **MISSING** | 전부 없음 |
| Stage 4 Copilot | **PARTIAL** | 챗 엔드포인트·intent 분류 있음 · orchestrator/tool 계층 없음 |
| §3 Vendor 추상화 | **MISSING** | `anthropic` SDK 직접 호출 |
| §4 과금·Entitlement | **PARTIAL** | `addon_subscriptions` 있음 · **credit/ledger/plan tier 없음** |
| §8 AI Response Contract | **MISSING** | 문자열 반환. 재현·감사 불가 |
| §10 Fallback | **CONFIRMED** | 3단 폴백 동작 |
| §11 보안 | **PARTIAL** | 화이트리스트 있음 · retention/injection 미검토 |
| §12 테스트 invariants | **PARTIAL** | 일부 있음 |

---

## 1. 이미 되어 있는 것 — 예상보다 많다

### 1-1. §0-1 AI 판정 금지 — **CONFIRMED. 구조로 강제됨**

```
chat_service.py:88   answer, used_renderer = await llm_render(result, ...)
                     ← result 는 RuleEngine.evaluate() 가 만든 StructuredResult
llm_renderer.py:98   _call_llm(result, locale)
                     ← LLM 은 이 JSON 만 받는다. 원시 DB 접근 없음
```

★ **LLM 에게 넘기는 payload 가 화이트리스트로 제한돼 있다** (`llm_renderer.py:_DETAIL_WHITELIST`):
```python
("loss", "grade", "ear_tag", "weakest_kpi", "weakest_rule",
 "method", "benchmark_avg", "accidents", "per_litter", "head", "matings")
```
주석: *"룰엔진 계산값, raw DB 아님"*

→ 설계 프롬프트 §0-1 은 **새로 만들 것이 아니라 이미 지켜지고 있다.**

### 1-2. §10 Fallback — **CONFIRMED. 3단 동작**

```python
llm_renderer.py:118  if not use_llm or not has_api_key() or not within_quota(usage_count):
                         return render_text(result, locale), "template"
                     try:    return await _call_llm(...), "llm"
                     except: return render_text(result, locale), "template"
```

키 없음 / 쿼터 초과 / 미구독 / 예외 — **전부 템플릿으로 떨어진다.**
설계 프롬프트 §10 의 `AI prose → Template → Structured facts` 중 앞 2단이 있다.

### 1-3. §0-2 국가 계층 — **CONFIRMED**

`kpi_policy_resolver.py` 가 `GLOBAL → COUNTRY → FARM_TYPE → TENANT` 상속을 구현하고,
`decision_status='APPROVED'` fail-closed 다. **국가 추가 = INSERT** 임이 테스트로 잠겨 있다
(`test_us_template_lock.py` L1~L6).

### 1-4. 예상 밖 — **`Task` 모델이 이미 있다** (Stage 2 Action Center 기반)

```python
ops.py:  class Task
  """Phase 2: 자동배정 작업. Rule/Alert(지연모돈·도태권고)에서 생성되어
     담당자에게 배정되고 모바일 "오늘 할 일"에 노출된다.
     멱등 생성: 같은 (farm_id, sow_id, task_type)의 OPEN task는 1개만 유지."""
```

→ 설계 프롬프트 §2-2 Action Center 의 **상태 관리 모델이 이미 설계돼 있다.**
  "단순 경고 리스트인지 Task 모델까지 갈지" 를 검토하라 했는데 **후자가 이미 있다.**

### 1-5. `Finding` 에 causes / recommended_actions 가 이미 있다

```python
Finding(rule_id, kpi, severity, current_value, target_value,
        causes=[...], recommended_actions=[...], detail={...})
```

→ Stage 2 Root Cause 의 **출력 형태 일부가 이미 존재**한다.
  다만 **causes 는 룰이 하드코딩한 문자열 키**이지 계산된 기여도가 아니다(§2-1 참조).

### 1-6. AI 사용량 로그가 있다 — 단, 최소한만

```python
ops.py:227  class LlmUsageLog
  farm_id · year · month · intent · tokens · created_at
  """per farm per month, for quota enforcement.
     chat_service counts current-month rows to decide template fallback."""
```

---

## 2. 없는 것 — 설계 프롬프트가 요구하는 것 대비

### 2-1. §1 "What Changed" — **MISSING**

기간 비교 delta 를 계산하는 backend 가 **없다.** `get_trend` 가 월별 시계열을 주지만
`{metric, previous, current, delta, direction, severity}` contract 를 만드는 곳이 없다.

★ 그리고 **`get_trend` 는 지금 `npd=None` 이다**(WEI 오노출 차단, `5abb8a4`).
  What Changed 를 trend 위에 세우면 **NPD 변화를 못 낸다.** 선행 정리가 필요하다.

### 2-2. §2-1 Root Cause — **PARTIAL → 사실상 MISSING**

| 요구 | 현재 |
|---|---|
| `Diagnosis` / `DiagnosisFactor` 모델 | **없음** |
| KPI decomposition | **없음** |
| dependency graph | **없음** |
| cohort comparison | **없음** |
| `contributor` / `associated_factor` / `likely_driver` 구분 | **없음** |

현재 `causes` 는 **룰 안에 하드코딩된 문자열**이다:
```python
base.py:74  causes = ["high_weaning_to_mating_interval"]
base.py:79  if severity == CRITICAL: causes.append("extended_return_to_estrus")
```
→ **계산된 기여도가 아니라 조건부 상수다.** Root Cause 라고 부를 수 없다.

### 2-3. §3 Vendor 추상화 — **MISSING**

```python
llm_renderer.py:98   import anthropic
llm_renderer.py:100  client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
llm_renderer.py:25   LLM_MODEL = "claude-haiku-4-5-20251001"    ← 하드코딩
```

`AIProvider` 인터페이스 없음. `has_api_key()` 가 `OPENAI_API_KEY` 도 보지만
**실제 OpenAI 호출 경로는 없다** — 이름만 있고 구현이 없다.

### 2-4. §3 사용량/비용 추적 — **PARTIAL**

| 요구 필드 | 현재 |
|---|---|
| `provider` · `model` | **없음** |
| `input_tokens` / `output_tokens` | `tokens` 하나뿐 (구분 없음) |
| `latency_ms` · `cost` | **없음** |
| `request_id` · `tenant_id` | **없음** |
| `farm_id` · `feature`(intent) | 있음 |

→ **원가를 계산할 수 없다.** §4 "실측 원가 전에는 확정하지 않는다" 를 지키려면
  이 로그부터 확장해야 한다.

### 2-5. §4 Entitlement — **PARTIAL**

```python
platform.py:231  class AddonSubscription
  farm_id · addon_code · is_active · started_at · cancelled_at · plan_price_usd
```

| 요구 | 현재 |
|---|---|
| addon 단위 구독 | **있음** |
| `FREE/STANDARD/PRO/PREMIUM` plan tier | **없음** |
| `ai_credit_ledger` | **없음** |
| `entitlement` 조회 계층 | **없음** — `_has_ai_insight(db, farm_id)` 가 애드온 1개를 직접 조회 |
| feature flag | **없음** |
| billing 연동 | **없음** |

★ `MONTHLY_LIMIT = 100` 이 `llm_renderer.py:24` 에 **하드코딩**돼 있다.
  Entitlement 문서의 `OPEN-4 무료 티어 월 크레딧` 이 미결인데 **코드에는 이미 값이 있다** —
  임계값과 같은 문제(승인 이력 없는 상수).

### 2-6. §8 AI Response Contract — **MISSING**

`_call_llm` 은 `msg.content[0].text.strip()` — **평문 문자열**을 반환한다.

```
요구: {summary, facts_used, evidence_refs, suggested_actions, disclaimer_type}
      + model · prompt_version · input_context_version · rule_result_ids · evidence_ids
현재: str
```

→ **AI 답변을 재현·감사할 수 없다.** 어떤 룰 결과로 그 문장이 나왔는지 추적 불가.

### 2-7. §11 보안 — **PARTIAL**

| 항목 | 상태 |
|---|---|
| LLM 전달 데이터 최소화 | **CONFIRMED** — `_DETAIL_WHITELIST` |
| 개인정보 포함 여부 | `ear_tag`(개체 식별자) 전달. 사람 식별정보는 없음 |
| tenant isolation | 챗 경로는 `FarmDep` 통과 후 호출 — **구조상 유지** |
| vendor retention 설정 | **미검토** |
| prompt injection | **미검토** — 사용자 질문이 그대로 들어가는 경로 확인 필요 |
| evidence 경유 injection | **미검토** |

### 2-8. Stage 3 (Goal / Plan / Simulation) — **전부 MISSING**

`goal` · `improvement_plan` · simulation engine 어느 것도 없다.

### 2-9. Stage 4 Orchestrator — **PARTIAL**

`chat_service.py` 에 intent 분류가 있으나, 설계 프롬프트가 요구한
**intent별 허용 tool 정의 / AI Orchestrator 계층**은 없다.
LLM 이 직접 SQL 을 만들지는 않으므로(§0-1 준수) **위험한 구조는 아니다.**

---

## 3. ★ 설계 프롬프트가 전제한 것 중 **사실과 다른 것**

> 프롬프트 §목적: "Evidence/출처/승인/권리/유효기간 관리 방향" 을 보유했다고 전제.

**보유한 것은 컬럼이고, 동작하지 않는다.**

| 전제 | 실제 (2026-08-27~28 감사) |
|---|---|
| Evidence 관리 방향 보유 | 아키텍처 문서는 있으나 **PROPOSED**. 구현 0 |
| 승인 관리 | `operational_defaults.origin` **29/29 = `code_default`** — 승인된 임계 0건 |
| 출처 관리 | `default_metric_values.threshold_basis` **61/68 NULL** |
| 권리 관리 | `rights_scope`/`policy_scope` **미구현** (D-18 PROPOSED) |
| 서빙에서 활용 | **`is_proxy`·`confidence`·`mapping_status` 참조 0건** — 로더가 버림 |

→ **Stage 2 이후가 전부 이 위에 서 있다.** Root Cause 가 "근거 있는 원인"을 말하려면
  근거 체계가 동작해야 하는데, 지금은 **컬럼만 있고 읽지 않는다.**

---

## 4. 판정 — "다 반영돼 있나?"

```
원칙 (§0-1 AI 판정금지 · §0-2 국가계층 · §10 fallback)   CONFIRMED — 이미 지켜짐
기반 (Task 모델 · Finding causes/actions · 사용량 로그)    PARTIAL  — 뼈대 존재
Stage 1 What Changed                                      MISSING
Stage 2 Diagnosis / Root Cause                            MISSING (Task 만 있음)
Stage 3 Goal / Plan / Simulation                          MISSING
Stage 4 Orchestrator / tool 계층                          MISSING
Vendor 추상화 · Response Contract · Credit/Entitlement    MISSING
Evidence 체계 (Stage 2+ 의 전제)                          컬럼만 있고 미동작
```

★ **좋은 소식**: 지키기 어려운 원칙(AI가 판정 안 함 · 국가 격리 · fallback)은 이미
  구조로 서 있다. 설계 프롬프트가 "변경하지 않는다" 고 한 것들이다.

★ **나쁜 소식**: Stage 2 이상이 전제하는 **evidence·승인 체계가 동작하지 않는다.**
  Root Cause 를 지금 만들면 **근거 없는 원인을 말하게 된다.**

---

## 5. 다음 산출물

설계 프롬프트 §13 의 B~G 는 이 감사 위에서 작성한다.

```
B. AI_FEATURE_ARCHITECTURE
C. STAGED_IMPLEMENTATION_PLAN
D. MINIMUM_SCHEMA_CHANGE
E. API_CONTRACT_DRAFT
F. ENTITLEMENT_DESIGN
G. TOP_10_IMPLEMENTATION_BACKLOG
```

**우선순위 제안 — 프롬프트 §14 와 다른 점 하나:**

프롬프트는 `P0-1 Structured Insight Contract` 부터다. 동의한다. 다만
**`Evidence 체계 동작화`를 P0-0 으로 앞에 둘 것을 제안한다.**

이유: Stage 2 Root Cause·Stage 3 Plan 이 모두 "근거 있는" 을 전제하는데,
지금은 서빙이 `is_proxy`·`confidence`·`mapping_status` 를 **읽지 않는다.**
그 위에 Diagnosis 를 얹으면 **근거 없는 진단을 구조적으로 생산**하게 된다.

이건 §15 "하지 말아야 할 것" 의 첫 줄(*LLM이 직접 severity 결정*)과 같은 종류의
위험이다 — 주체가 LLM 이 아니라 우리 코드일 뿐이다.
