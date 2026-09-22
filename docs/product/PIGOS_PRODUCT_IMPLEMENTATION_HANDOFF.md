# PigOS Product Implementation Handoff v1.1
## 제품 전략 → 개발 실행 명세

```yaml
version: 1.1
document_status: IMPLEMENTATION-DRAFT
provenance:
  source_version: 1.0
  source_origin: Downloads (repo 사본 없었음)
  imported_at: 2026-08-28
  repository_copy_previously_existed: false
canonical_path: docs/product/PIGOS_PRODUCT_IMPLEMENTATION_HANDOFF.md
```

> **정본은 이 파일이다.** Downloads 사본을 SSOT 로 쓰지 않는다.

## ★ v1.1 정정 요약 (2026-08-28)

v1.0 은 아래 다섯 가지를 사실과 다르게 전제하고 있었다. 실측으로 정정한다.

| # | v1.0 전제 | 실측 |
|---|---|---|
| 1 | 모바일만 서버 판정을 안 따른다 | **세 surface 전부** 미검증 — §0-3 |
| 2 | `kpi_snapshots` 가 동작한다 | **0행. 2026-05-29 이래 한 번도 동작한 적 없다** — §0-4 |
| 3 | §11 이벤트 14개 = 계측 baseline | **PLANNED. 세 surface 전부 계측 0** — §11-0 |
| 4 | 실고객 2농장 / 분만 3건 | **3농장 / 82건** (CN 1/1 · KR 2/81, US 0) — §0-5 |
| 5 | 오프라인 계약 미기술 | Action Center / What Changed / Health Watch 별로 명시 — §0-6 |

근거: `docs/kpi/D19_THRESHOLD_SOURCE_AUDIT_v1.4.md` ·
`docs/runs/RUNTIME_INTEGRITY_AUDIT_20260828.md` · `docs/PLATFORM_PARITY.md`


> 작성일: 2026-08-28  
> 상태: **IMPLEMENTATION-DRAFT — 상위 의사결정 승인 후 실행**  
> 상위 문서: `PIGOS_PRODUCT_EXPANSION_DECISION_v1.0.md`
>
> 목적: GPT·Claude 심층리서치 통합 결론을 실제 개발 Epic, Gate, Acceptance Criteria로 변환한다.
> 이 문서는 KPI formula/threshold/evidence를 새로 정의하지 않는다. 기존 SSOT를 소비한다.

---

# 0. 개발 불변조건

## 0-1. 판단 권한

```text
KPI value           = deterministic calculation
severity            = Threshold Resolver
benchmark context   = Benchmark Context Resolver
change              = deterministic comparison
root-cause output   = bounded candidate generation
AI                  = explanation / plan / report
```

LLM 금지:

- KPI 숫자 생성
- severity 생성
- threshold 생성
- benchmark 숫자 추정
- 질병 확진
- 약물/용량 처방
- 근거 없는 인과 단정

## 0-2. 기존 SSOT 우선

개발 전에 반드시 참조 (**실제 repo 경로**):

1. `docs/runs/RUN_PROMPT_D13_canonical_formula_audit.md` v1.4 + `docs/kpi/CANONICAL_FORMULA_SPEC_REAUDIT.md`
2. `docs/specs/COUNTRY_KPI_EVIDENCE_ARCHITECTURE_v1.1.md` (+ `docs/kpi/EVIDENCE_ARCHITECTURE_V1_2_REVIEW.md`)
3. `docs/runs/D19_THRESHOLD_SOURCE_AUDIT_RUN.md` v1.4 + `docs/kpi/D19_THRESHOLD_SOURCE_AUDIT_v1.4.md`
4. `docs/specs/D21_THRESHOLD_GOVERNANCE_DESIGN.md` (design COMPLETE / persistence NOT_IMPLEMENTED)
5. `docs/PLATFORM_PARITY.md` — **플랫폼 구현 상태의 유일한 SSOT**
6. 기존 country_kpi_policy / presentation ADR

새 DB/서비스가 이 문서와 충돌하면 기존 거버넌스를 우회하지 않는다.

---

## 0-3. ★ Platform assumption correction (v1.1 신설)

v1.0 은 "모바일이 서버를 따르지 않는다" 로 좁게 썼다. **더 넓다.**

> 현재 Web · Android · iOS **어느 surface 도 server decision contract 의
> 단독 소비가 검증되지 않았다.**

| surface | 자체 판정 경로 | 상태 |
|---|---|---|
| **Web** | `src/lib/kpi/status.ts` — `psyTier>=28` · `npdTier<=35` · `farrowingRateTier>=90`. **국가 구분 없음** | 2026-08-28 fail-closed 로 수정. `CROSS_COUNTRY_DECISION_RISK` 해소 |
| **Android** | `meetsAvg = myValue >= benchmark.avg` → Success/Warning | 2026-08-28 수정 (feature branch) |
| **iOS** | alert 없음 → `AppColor.success` | 2026-08-28 수정 (feature branch). P0 correctness 였다 |

```
Backend = decision SSOT
Web     = reference UI 일 수는 있으나 decision SSOT 아니다
```

★ 폐기하는 전제 둘:
```
"Web 은 판정 reference implementation 이다"
"서버가 맞으면 모바일도 맞다"          (D-13 B′ 로 반증됨)
```

canonical contract 는 하나다 — `normal | warning | critical | insufficient`.
**신규 enum(neutral/unknown/no_alert)을 만들지 않는다.**

---

## 0-4. ★ Snapshot reality (v1.1 신설)

```
kpi_snapshots 행 수                0
daily/weekly/monthly 집계          매일 실행되나 71농장 전건 실패
실패 원인                          KpiSnapshot 에 farrowing_rate 컬럼 없음
                                   (jobs/kpi.py 와 models/ops.py 가 같은 커밋
                                    26c2e68 에서 태어나며 어긋남 — 2026-05-29)
대시보드 실제 동작                  요청 시 계산 + Redis 30초 캐시
ARQ 보고                           성공(●)
```

→ **다음 기능은 snapshot pipeline correctness 가 선행이다.**

```
What Changed
snapshot-first Home
historical comparison
offline read-cache
```

계획과 현재 구현을 구분한다. "스냅샷을 읽으면 된다" 고 쓰지 않는다.

---

## 0-5. ★ 실고객 규모 정정 (v1.1)

```
OUTDATED   2 farms / 3 farrowings
CURRENT    native_signup 3 farms / 최근 365일 분만 82건
             CN  1 farm  /  1 farrowing
             KR  2 farms / 81 farrowings
             US  native_signup 최근365일 분만 = 0
INTERNAL   pigplan_migration 42 farms (참조용. 운영 판정에 합산 금지)
```

★ **KR 이 81/82 라는 이유만으로 우선순위를 자동으로 올리거나 내리지 않는다.**
영향 규모 · 산식 모호성 · 현재 사용 여부는 각각 별개 축이다.

---

## 0-6. ★ Offline contract (v1.1 신설)

| 기능 | 계약 |
|---|---|
| **Action Center** | `WRITE_QUEUE` · 기존 sync queue 재사용 · `SERVER_WINS` · `CLIENT_UUID` 멱등 · conflict 는 사용자에게 observable |
| **What Changed** | `SERVER_ONLY` 계산 · `READ_CACHE` 만 · `as_of`/`last_synced`/stale 표시 필수 · **오프라인 재계산 금지** |
| **Health Watch** | `SERVER_ONLY` 계산 · `READ_CACHE` 만 · **오프라인 신규 anomaly 생성 금지** |

근거: 값 계산이 클라이언트로 내려가는 순간 §0-3 의 판정 분기와 같은 문제가 값에서 재현된다.
현재 실측상 모바일에 **산식 하드코딩은 0건**이다 — 그 상태를 유지한다.

---

# 1. 전체 Dependency

```text
GATE 0
  Formula / G3 / Threshold version / as_of
      ↓
EPIC 1  Country Presentation Packs
      ↓
EPIC 2  Execution Core
      ↓
EPIC 3  Existing-data Health Watch
      ↓
EPIC 4  Feed Basic
      ↓
EPIC 5  Root Cause Candidate
      ↓
EPIC 6  Benchmark Depth / Multi-farm / Advanced Profitability
      ↓
EPIC 7  Contextual AI
```

센서/IoT는 별도 Integration Track.

---

# 2. GATE 0 — 구현 선행조건

## G0-A. D-17 G3 전역화

No-benchmark new-country launch contract:

```json
{
  "kpi_code": "example",
  "value": 42,
  "benchmark_enabled": false,
  "benchmark_value": null,
  "benchmark_status": "NO_VERIFIED_BENCHMARK",
  "comparison_status": "UNAVAILABLE"
}
```

Acceptance:

- HTTP 200
- farm value 유지
- benchmark `null`
- GLOBAL silent fallback 없음
- KR value fallback 없음
- benchmark 기반 severity 없음
- 모바일 카드 소실 없음
- registry 신규 KPI가 presentation 승인 없이 자동노출되지 않음

D-17은 US 전용이 아니라 **모든 new-country launch prerequisite**다.

## G0-B. Approved threshold path

국가 카드가 severity를 표시하려면:

```text
canonical KPI
+ country presentation
+ APPROVED threshold
```

가 있어야 한다.

threshold 없으면:
- 값 표시 가능
- severity/color 없음

## G0-C. D-21 threshold versioning

최소 요구:

- threshold identity
- scope
- version
- effective_from/effective_to
- evidence linkage
- rule mapping

D-19의 사실감사 결과를 재사용하고 새로운 감사 프레임워크를 만들지 않는다.

> ### v1.1 현황 (2026-08-28)
>
> ```
> D21 design_status = COMPLETE   docs/specs/D21_THRESHOLD_GOVERNANCE_DESIGN.md
> D21 persistence   = NOT_IMPLEMENTED
> G0C_gate_status   = BLOCKED
> ```
>
> ★ `APPROVED_POLICY = 0` 이고 **승인을 기록할 컬럼 자체가 없다.**
> 따라서 G0-B "APPROVED threshold" 조건은 현재 **어느 국가도 충족하지 못한다.**
> BR 파일럿 포함이다.
>
> gate 를 즉시 enforce 하면 71농장 severity 가 전부 사라진다 →
> D-21 §7-2 `OBSERVE → WARN → ENFORCE` 순서를 따른다.

## G0-D. `as_of`

What Changed / Outcome을 위해 동일 KPI를 과거 시점으로 재현 가능하게 한다.

최소 요구:

```text
as_of
formula_id + formula_version
rule version
threshold version
```

가능하면 당시 source state까지 재현 가능해야 한다.

> ### v1.1 현황 — 6축 중 2축만 존재
>
> ```
> formula version    없음        threshold version  없음
> rule version       없음        evidence version   없음(source_ref 자유문자열)
> as_of              부분(build_herd_kpis 가 wall-clock)
> source snapshot    없음(kpi_snapshots 0행)
> → V-3 NOT_REPRODUCIBLE
> ```
>
> 고객 대면 알림 468건도 판정 근거가 저장돼 있지 않다.
> **과거 알림을 backfill 로 재구성하지 않는다** — 오늘의 추정이지 그때의 근거가 아니다.

## G0-E. LIVE_DIVERGENCE

- stillborn 계열
- PRE_WEANING_MORTALITY

AMBIGUOUS/LIVE_DIVERGENCE 상태의 KPI는 신규 outcome 비교와 신규 국가 mapping에서 차단한다.

---

# 3. EPIC 1 — Country Presentation Packs

## 목표

농장 국가에 따라 **대표 KPI의 우선순위·현지 명칭·benchmark 유무를 안전하게 표현**한다.

## 초기 대상

1. BR
2. MX
3. US

VN/TH는 evidence gate 완료 후.

## Research-recommended candidate order

### BR

```text
DFA
NPD
Partos/Fêmea/Ano
Média de Desmamados
Média de Nascidos Vivos
```

주의: 기존 BR APPROVED policy를 자동 교체하지 않는다.
candidate diff를 Decision Register에 올리고 승인 후 반영.

### MX

```text
DHA
Partos/año/hembra
Nacidos vivos
Destetados/camada
DNP
```

MX benchmark 상태:
- NATIONAL = 없음/미확보
- PIC = mixed cohort
- MX-specific FARM_COHORT evidence = context 후보
- G1/G2/G3 승인 전 product benchmark 활성화 금지

### US

Sow Pack:

```text
PW/MF/Y
Farrowing Rate
Pre-weaning Mortality
Sow Mortality
Total Born / Born Alive
```

Grow-Finish Pack은 Feed/Profitability Epic 이후.

## UI Acceptance

각 KPI 카드:

- local display name
- farm value
- unit
- period
- severity if approved threshold exists
- benchmark context if approved
- formula/info link
- benchmark unavailable 상태 정상 표시

UI에 country `if/else`를 하드코딩하지 않는다.
Presentation policy를 소비한다.

---

# 4. EPIC 2 — Execution Core

## 4-1. Role-aware Home

### Worker / Manager

- 오늘 할 일
- 놓친 기록/작업
- 확인할 개체/돈군
- 가장 중요한 변화 1~3개

### Owner

- 핵심 KPI
- 이번 주 변화
- 비용 영향 후보
- benchmark/context

### Vet / Consultant

- Health Watch
- 변화 추세
- affected group
- evidence pack

### Integrator

- farm outlier
- multi-farm status
- portfolio KPI

첫 버전은 역할 템플릿 수준. 개인화 ML 금지.

## 4-2. What Changed

입력:

```text
current KPI snapshot
previous comparable KPI snapshot
same formula version
comparable threshold/rule context
```

출력 예:

```json
{
  "kpi_code": "farrowing_rate",
  "current_value": 82.3,
  "previous_value": 86.1,
  "delta": -3.8,
  "direction": "WORSE",
  "severity": "WARNING",
  "comparison_basis": "PREVIOUS_4_WEEKS",
  "formula_version": "..."
}
```

금지:
- 정의가 다른 snapshot 비교
- threshold 변경을 KPI 변화처럼 표현
- causal explanation 자동 생성

## 4-3. Action Center

Change → Action 연결.

Logical contract:

```text
change_id
what_changed
why_it_matters
check_items[]
recommended_actions[]
priority
evidence_refs[]
status
```

Action 상태 최소:

```text
OPEN
IN_PROGRESS
DONE
DISMISSED
```

사용자가 실제로 수행한 Action은 별도 기록 가능해야 한다.

## 4-4. Weekly Brief

내용:

1. 가장 중요한 변화 3개
2. 확인할 일
3. 완료/미완료 Action
4. 좋아진 항목
5. benchmark/context가 있으면 보조 설명

초기 delivery:
- in-app
- email/push 등 기존 채널

WhatsApp/Zalo 등은 국가별 검증 후 integration.

---

# 5. EPIC 3 — Existing-data Health Watch

## 목표

질병명을 맞히는 것이 아니라 **평소와 다른 건강 관련 운영신호를 빨리 보여준다.**

## 5-1. Reproductive anomaly

대상:

- abortion
- return-to-estrus
- farrowing-rate
- reproductive loss 계열

출력:

```text
"최근 기준기간 대비 유산 기록이 증가했습니다."
"번식 이탈이 평소 범위를 벗어났습니다."
```

병명 금지.

## 5-2. Mortality / neonatal-loss anomaly

- sow mortality
- piglet/neonatal loss
- pre-weaning mortality

approved threshold가 없으면:
- statistical/change context만
- severity 금지

## 5-3. Cohort/Barn Watchlist

가능한 범위에서:
- 돈사
- parity
- batch/cohort
- age/production stage

별로 변화가 집중되는지 보여준다.

## 5-4. Vet-ready Evidence Pack

Export/display:

```text
farm
period
changed indicators
affected groups
event timeline
recent actions
notes/photos if existing capability supports
formula/threshold provenance
```

AI 진단 없이 수의사 판단을 돕는다.

## 5-5. Off-feed / Water

Core Health v1에 강제하지 않는다.

분류:

```text
REQUIRES_SENSOR_OR_HIGH_FREQUENCY_INPUT
```

ESF/water telemetry connector가 생기면 별도 Epic으로 활성화.

---

# 6. EPIC 4 — Feed Basic

## 목표

Feed ERP를 만드는 것이 아니라 **사료효율 변화가 비용에 어떤 의미인지 빠르게 보여준다.**

## 6-1. 최소 입력

```text
feed_quantity
feed_unit_cost
period
group/pig reference
weight_start
weight_end
```

데이터 없을 때 추정값으로 채우지 않는다.

## 6-2. v1 계산

1. FCR
2. Feed Cost / pig
3. Feed Cost / kg gain

각 계산은 canonical formula/version을 가진다.

## 6-3. What Changed 연결

예:

```text
"FCR이 이전 기간 2.55 → 2.72로 악화됐습니다."
"현재 입력 단가 기준 Feed Cost/kg gain이 증가했습니다."
```

## 6-4. Action 연결

첫 버전은 bounded checklist:

- feed amount/source record 확인
- weight measurement 확인
- mortality/health change 확인
- feed phase 변경 여부 확인
- 가격 입력 변경 확인

"사료를 X% 줄이세요" 같은 자동 처방 금지.

## 6-5. Entitlement

제안:
- Basic FCR: Free 후보
- Cost analytics/deep trend/action: Paid hypothesis

실제 paywall은 가격 실험 후 확정.

---

# 7. EPIC 5 — Root Cause Candidate

## 목표

"원인을 알아냈다"가 아니라 **확인할 가능성 높은 후보를 정리**한다.

출력 계약:

```text
possible_contributors[]
data_to_check[]
check_actions[]
supporting_signals[]
confidence = NOT_CAUSAL
```

예:

```text
분만율 하락과 동시에
- 재발정 증가
- NPD 증가
가 관찰됐습니다.

확인 후보:
1. 교배/재발정 기록
2. 최근 parity 분포
3. 건강 이벤트
```

금지:
- causal certainty
- LLM 단독 후보 생성
- evidence 없는 veterinary diagnosis

---

# 8. EPIC 6 — Benchmark Depth / Multi-farm / Advanced Profitability

## 8-1. Benchmark Depth

- cohort
- farm size
- percentile
- trend

`benchmark_point`, `benchmark_trend`, `threshold`를 섞지 않는다.

## 8-2. Multi-farm

Integrator/consultant용:

- outlier farm
- KPI rollup
- comparable cohort
- unresolved alerts/actions

## 8-3. Advanced Profitability

Feed Basic 데이터 품질이 충분한 뒤:

- IOFC
- scenario
- optimal marketing weight
- US packer-grid economics

국가별 가격/출하 모델을 분리한다.

---

# 9. EPIC 7 — Contextual AI Copilot

## 9-1. 시작점

메인 빈 Chat 금지.

Entry point:

```text
What Changed
Action
Health Watch
Feed card
Report
```

## 9-2. Router

### ENGINE_ONLY

- status
- change
- entity
- KPI value
- benchmark
- money calculation
- formula definition

### ENGINE + AI_EXPLANATION

- why this matters
- possible contributors
- action prioritization explanation
- weekly summary

### AI_ASSISTED

- plan draft
- report
- cross-card narrative
- role-based wording

## 9-3. Safety Router

수의사 이관:

- disease identification
- treatment protocol
- drug selection/dose
- prognosis

답변 템플릿은 "확인 필요"와 evidence summary 중심.

---

# 10. Outcome Loop — 저장할 최소 정보

새 테이블명은 코드 실사 후 결정.
논리적으로 아래 4개는 추적 가능해야 한다.

```text
Detected Change
Recommended Action
Action actually taken
Observed Outcome
```

최소 linkage:

```text
farm_id
change_id
action_id
action_taken_at
outcome_as_of
formula_version
rule_version
threshold_version
observed_delta
```

`observed_delta`는 인과효과가 아니다.

---

# 11. Instrumentation — 먼저 baseline을 만든다

## 11-0. ★ 현황 — 아래 14개는 baseline 이 아니라 PLANNED 다 (v1.1)

```
Web       lib/analytics.ts 존재. PostHog key 미설정 → enabled() false → 전면 no-op
          배포 번들 12청크 검사에서 phc_ 키 0건
Android   제품 계측 0건
iOS       제품 계측 0건
```

```
status = PLANNED_INSTRUMENTATION      (EXISTING_BASELINE 아님)
```

★ **현재 계측 데이터에 근거한 제품 결론을 내리지 않는다.** 데이터가 없다.
★ 세 surface 전부 transport 가 없으므로 **밤샘에 대규모 analytics subsystem 을
  신설하지 않는다.** 먼저 event contract 를 platform-neutral 하게 확정한다
  (`docs/FEATURE_REGISTRY.md` analytics_events 열).
★ PostHog secret/key 를 생성하지 않는다.

임의의 20%/30%/50% 성공기준을 Freeze하지 않는다.

초기 이벤트 (**PLANNED**):

```text
home_open
change_card_view
change_card_expand
action_open
action_start
action_done
weekly_brief_view
health_watch_open
vet_pack_export
feed_input_start
feed_input_complete
feed_card_view
ai_entry_open
ai_question_submit
```

분석할 것:

- 어떤 역할이 무엇을 보는가
- change → action 전환
- action 완료
- Feed 입력 중단 위치
- AI 진입 맥락
- 국가별 차이

beta baseline 이후 activation/retention threshold를 결정한다.

---

# 12. 국가 rollout

## 12-0. ★ Country Rollout Gate (v1.1 신설)

국가를 켜기 전에 **전부** 충족해야 한다. 하나라도 미충족이면 rollout 하지 않는다.

```
[ ] evidence                     claim + verifier state
[ ] formula                      formula_status = CONFIRMED (AMBIGUOUS 차단)
[ ] threshold approval           APPROVED_POLICY. 현재 전 국가 미충족(G0-C)
[ ] D-17 G3                      benchmark 없어도 정상 렌더
[ ] Web parity                   server kpi_status 단독 소비
[ ] Android parity               required platform 인 국가만
[ ] iOS parity                   required platform 인 국가만
[ ] min_supported_app_version    선언 + 서버가 관측 중
[ ] legacy-client control        구버전 제한 또는 강제 업데이트
[ ] benchmark unavailable 처리    비교만 사라지고 값은 남는다
[ ] no local severity            세 surface 전부
```

★ iOS 는 **iOS 가 required platform 인 국가에 한해서만** prerequisite 다.
  `IOS_RELEASE_CAPABILITY = CI_EXTENSION_REQUIRED` (build/test 는 되고 distribute 경로가 없다).

## 12-1. ★ Legacy client 활성화 순서 (v1.1 신설) — 역순 금지

```
1. Web    platform/version 헤더 송출
2. Android 헤더 송출
3. iOS     헤더 송출
4. 서버가 세 surface 전부에서 수신·관측 확인
5. 그 다음에야  missing-version = LEGACY fail-closed 활성화
```

**4번 없이 5번을 켜면 정상 클라이언트가 전부 차단된다.**
enforcement 보다 송출·관측이 먼저다.

## 1차

### BR
- 기존 정책 안정성 유지
- candidate KPI order는 별도 Decision Register
- What Changed/Action 적용

### MX
- G3가 핵심
- benchmark 없이 정상 동작
- DHA 중심
- MX FARM_COHORT benchmark는 승인 전 context에 사용 금지

### US
- Sow Pack 우선
- Grow-Finish/Feed economics 후속
- VFD 등 조건부 규제 기능은 별도 트랙

## 2차

VN:
- terminology/presentation 가능
- national benchmark/threshold 과장 금지
- 오프라인/현지화 비용 별도

TH:
- PSY formula/version 설명 강화
- national benchmark 미확보는 정상 상태

---

# 13. Regression / Acceptance Matrix

## Country KPI

- [ ] benchmark 없음 → 200 + value 유지
- [ ] silent GLOBAL fallback 없음
- [ ] KR benchmark leak 없음
- [ ] unapproved KPI 자동 노출 없음
- [ ] formula mismatch benchmark 비교 차단
- [ ] COUNT/RATE 단위 혼동 차단

## What Changed

- [ ] 동일 formula/version만 비교
- [ ] as_of 재현
- [ ] threshold version 추적
- [ ] LIVE_DIVERGENCE KPI 차단

## Health

- [ ] anomaly 문구에 병명 없음
- [ ] threshold 미승인 시 severity 없음
- [ ] affected cohort 근거 표시
- [ ] vet export에 provenance 포함

## Feed

- [ ] 누락 data 추정 금지
- [ ] FCR/cost formula version 추적
- [ ] currency/unit 명확
- [ ] 미국 가격모델을 BR/MX에 재사용하지 않음

## AI

- [ ] numeric answer는 engine result만 사용
- [ ] severity를 LLM이 만들지 않음
- [ ] causal certainty 금지
- [ ] veterinary safety routing
- [ ] source/formula context 표시 가능

---

# 14. Do Not Build — 현재

- 대형 통합기업 ERP 대체
- 센서 전제 실시간 Health AI를 core로
- 자유 Chat first
- AI 질병 진단/처방
- SMS Production Index 복제
- benchmark 없는 국가에 GLOBAL 값 대체
- Feed inventory ERP 전체
- 국가별 기능 하드코딩
- WTP 검증 전 과도한 paywall 세분화

---

# 15. Definition of Done — 이 제품 트랙

v1 개발 완료라고 부르려면 최소:

```text
[ ] BR/MX/US Country Pack이 presentation policy로 동작
[ ] MX benchmark 0 상태가 안전
[ ] What Changed가 version-compatible snapshot으로 동작
[ ] Action Center에 change linkage 존재
[ ] Weekly Brief가 deterministic 결과를 요약
[ ] Existing-data Health Watch 2종 이상 동작
[ ] Feed Basic(FCR + Cost/pig + Cost/kg gain) 동작
[ ] 모든 숫자/판정이 engine provenance 보유
[ ] AI는 contextual entry만, engine 우회 없음
[ ] instrumentation이 켜져 baseline 수집 가능
```

이후 Root Cause / Advanced Profitability / Multi-farm / AI depth를 순차 확대한다.
