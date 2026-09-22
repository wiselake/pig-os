# PigOS Product Expansion Decision v1.1
## GPT × Claude 심층리서치 통합 의사결정본

```yaml
version: 1.1
provenance:
  source_version: 1.0
  source_origin: Downloads (repo 사본 없었음)
  imported_at: 2026-08-28
  repository_copy_previously_existed: false
canonical_path: docs/product/PIGOS_PRODUCT_EXPANSION_DECISION.md
```

> **정본은 이 파일이다.** Downloads 사본을 SSOT 로 쓰지 않는다.

## ★ v1.1 정정 (2026-08-28) — 실행 문서와 동일 기준

상세는 `PIGOS_PRODUCT_IMPLEMENTATION_HANDOFF.md` §0-3~0-6 · §11-0 · §12-0.

```
Platform assumption   Web·Android·iOS 세 surface 전부 server decision contract
                      단독 소비 미검증이었다. Backend 가 decision SSOT 다.
Snapshot reality      kpi_snapshots 0행. 2026-05-29 이래 미동작.
                      → What Changed / snapshot-first Home / 과거비교 /
                        offline read-cache 는 pipeline correctness 선행.
Instrumentation       세 surface 계측 0. §11 14개 이벤트는 PLANNED.
                      현재 계측 근거 제품 결론 금지.
실고객 규모            3 farms / 82 farrowings (CN 1/1 · KR 2/81 · US 0).
                      기존 "2 farms / 3 farrowings" 는 OUTDATED.
Governance            APPROVED_POLICY = 0 이고 승인 기록 컬럼이 없다.
                      Phase 0 선행조건이 아직 열리지 않았다.
```

★ **개발 순서(§10)는 유지한다.** 다만 Phase 1 의 What Changed / Home 에
`SNAPSHOT_PIPELINE_CORRECTNESS` 를 선행조건으로 연결한다.

> 작성일: 2026-08-28  
> 상태: **DECISION-DRAFT — 대표 승인 후 FROZEN**  
> 성격: 시장·국가 KPI·Feed·Health·AI·역할·수익화의 상위 의사결정 문서  
> 하위 구현 문서: `PIGOS_PRODUCT_IMPLEMENTATION_HANDOFF_v1.0.md`
>
> 이 문서는 `COUNTRY_KPI_EVIDENCE_ARCHITECTURE v1.1`, `D13_CANONICAL_FORMULA_AUDIT_RUN`, `D19_THRESHOLD_SOURCE_AUDIT_RUN`을 대체하지 않는다.
> 제품 방향을 결정하고, 증거/공식/threshold/rights의 승인 여부는 기존 KPI 거버넌스 문서가 계속 SSOT다.

---

## 0. 통합 원칙

이번 GPT·Claude 심층리서치는 서로 다른 역할로 사용한다.

- **Claude 수집 결과**: 현지 KPI, farmer voice, Feed/Health 후보, 경쟁제품, 현장 신호를 넓게 확보.
- **GPT 검증 결과**: 1차 근거 재확인, 과장/충돌 제거, PigOS 현재 데이터·아키텍처·경쟁포화와 연결.
- 충돌 시 다음 우선순위를 적용한다.

```text
1차 정부/협회/학술 원문
> 실제 농장관리 benchmark/report
> 수의사/생산자 직접 voice
> vendor 자료
> industry media
> inference
```

Evidence 상태:

```text
VERIFIED_FACT
SUPPORTED_INFERENCE
HYPOTHESIS
UNVERIFIED
CONTRADICTED
```

불변조건:

```text
Pain이 크다 ≠ WTP가 검증됐다.
Vendor가 제공한다 ≠ 농가가 원한다.
Benchmark가 있다 ≠ 국가대표 benchmark다.
AI가 가능하다 ≠ AI로 처리해야 한다.
같은 KPI 이름이다 ≠ 같은 계산정의다.
```

---

# 1. PigOS의 제품 포지션

PigOS는 기존 기록 SW를 대체하는 ERP 경쟁으로 들어가지 않는다.

```text
기록
→ 국가별 KPI
→ 무엇이 달라졌는가
→ 무엇을 확인해야 하는가
→ 행동
→ 행동 기록
→ 이후 결과 확인
→ 필요한 경우 AI 설명/대화
```

### 단기 차별화

```text
Country Evidence
+ Canonical Formula
+ Approved Threshold
+ Deterministic Rule
+ What Changed
+ Action UX
```

### 장기 해자

```text
농장 Context
+ Detected Problem
+ Recommended Action
+ Action actually taken
+ Subsequent observed outcome
```

인과 표현 금지:

```text
X  "Action A 때문에 PSY가 +0.8 상승했다."
O  "Action A 실행 후 PSY +0.8 변화가 관찰됐다."
```

---

# 2. 국가 우선순위

현재 시장 우선순위의 큰 틀은 유지한다.

| Tier | 국가 | 판정 |
|---|---|---|
| Tier 1 | **BR / MX / US** | 유지 |
| Tier 2 | **VN / ES / CA** | 유지. CA는 `REQUIRES_US` |
| Tier 3/Watch | TH / PH / DK / DE / NL 등 | evidence·제품 준비도에 따라 |
| Hold | CN | 시장 크기와 진입매력도를 분리 |

주의:

- 좋은 시장과 다음 개발국가는 동일하지 않다.
- `market_score`, `prerequisite_dependency`, `development_effort`, `evidence_confidence`를 한 점수로 합치지 않는다.

---

# 3. 국가별 대표 KPI — 연구 권고 Presentation Pack

> 아래는 **연구 기반 추천 표시 우선순위**다.
> 기존 Production의 APPROVED 정책을 자동으로 변경하지 않는다.
> 실제 활성화는 canonical formula / terminology / APPROVED threshold / G3 및 필요한 경우 benchmark mapping·rights를 통과해야 한다.

## 3-1. Brazil — Tier 1

### 추천 Top 5

1. **DFA — Desmamados/Fêmea/Ano**
2. **Dias Não Produtivos (NPD)**
3. **Partos/Fêmea/Ano**
4. **Média de Desmamados**
5. **Média de Nascidos Vivos**

보조:
- Taxa de Parto
- Natimortos / Mumificados
- LPV
- FCR은 번식 Country Pack보다 Feed/Grow-Finish Pack에서 취급

판정:
- Agriness의 실제 ranking/management 문화는 강한 근거.
- Agriness 값은 **FARM_COHORT**이지 NATIONAL census가 아니다.
- 기존 BR APPROVED 행은 별도 결정 없이 교체하지 않는다.

## 3-2. Mexico — Tier 1

### 추천 Top 5

1. **DHA — Destetados por Hembra por Año**
2. **Partos por año / hembra**
3. **Nacidos vivos**
4. **Lechones destetados por camada**
5. **Días No Productivos**

중요 수정:

```text
기존 표현:
"MX 단독 benchmark 없음"

정확한 표현:
"MX NATIONAL representative benchmark 미확보.
PIC는 Mexico+CA 혼합 cohort.
Agriness 계열에는 MX-specific FARM_COHORT 관측치가 존재하나
national benchmark로 승격하지 않는다."
```

제품 함의:
- **Benchmark 부재 ≠ KPI 부재.**
- MX는 no-benchmark launch contract의 핵심 실전 사례.
- benchmark가 없어도 canonical KPI + terminology + presentation + APPROVED threshold + G3가 있으면 출시 가능.

## 3-3. USA — Tier 1

미국은 Sow와 Grow-Finish를 한 Top5로 섞지 않는다.

### US Sow Pack

1. **PW/MF/Y — Pigs Weaned / Mated Female / Year**
2. **Farrowing Rate**
3. **Pre-weaning Mortality**
4. **Sow Mortality / Death Loss**
5. **Total Born / Born Alive**

### US Grow-Finish Pack

후속:
- FCR
- ADG
- Mortality
- Days to Market
- Feed Cost / kg gain
- Marketing / carcass economics

주의:
- `PW/MF/Y`와 `Pigs weaned/female/year`를 같은 공식으로 취급하지 않는다.
- SMS Production Index는 참고체계이지 PigOS가 복제할 공개 산식이 아니다.
- packer grid/optimal marketing weight는 미국 Grow-Finish 경제성 기능으로 분리한다.

## 3-4. Vietnam — Tier 2

### Candidate Top 5

1. PSY
2. Litters/sow/year
3. Weaned/litter
4. FCR
5. Replacement / survival 계열

판정:
- 현지 terminology와 KPI 사용 자체는 유의미.
- `PSY=24` 등을 국가 공식 benchmark/threshold로 승격하지 않는다.
- 현 evidence는 vendor/research/genetic-line 성격이 섞여 있고 national applicability가 미확립.
- **표시는 후보, benchmark·threshold는 RESEARCH_MORE.**

## 3-5. Thailand — 후속 국가

### Candidate Top 5

1. **PSY**
2. **NPD**
3. **Pig Weaned/Litter**
4. **Born Alive / Total Born**
5. **Pre-weaning Mortality**

중요 보강:
- 태국 현지 자료에서 PSY 계산법이 여러 개 존재한다는 사실은 강한 evidence.
- 따라서 화면에 PSY만 보여주는 것이 아니라 **어떤 formula/version으로 계산됐는지 추적 가능해야 한다.**
- `PSY 평균 22~25` 등 국가대표 수치는 승인 근거가 부족하므로 threshold/benchmark에 사용하지 않는다.

---

# 4. Country KPI 공통 원칙

국가별 화면의 차별화는 단순 번역이 아니다.

```text
Local terminology
+ Canonical formula compatibility
+ Country presentation priority
+ Approved threshold
+ Optional benchmark context
```

Benchmark와 severity를 분리한다.

```text
Threshold Resolver          → severity/색상의 유일한 권한
Benchmark Context Resolver  → 비교 맥락만
```

No-Benchmark Country Launch:

```text
PigOS canonical KPI
+ terminology
+ presentation policy
+ APPROVED threshold
+ G3 presentation safety
= launch 가능

external benchmark
= optional
```

금지:
- benchmark=0
- GLOBAL silent fallback
- KR benchmark 대체
- benchmark만으로 severity 계산
- benchmark 미존재 시 카드 소실

---

# 5. Feed — 제품 결정

## 5-1. 연구 결론

사료비 pain은 강하게 검증됐다.
그러나:

```text
사료비가 크다
≠
IOFC/Feed SaaS에 지불의사가 검증됐다.
```

또한 FCR/Feed/Cost/Inventory는 이미 여러 경쟁사가 제공한다.
따라서 **Feed Dashboard 자체는 차별화가 아니다.**

PigOS 차별화:

```text
Feed metric
→ What Changed
→ 비용 영향
→ 확인할 원인 후보
→ Action
```

## 5-2. Feed 1단계 — 확정 추천

### Phase Feed-1

1. **FCR**
2. **Feed Cost / pig**
3. **Feed Cost / kg gain**
4. 위 3개에 대한 **What Changed**
5. 국가/생산단계별 설명과 Action 연결

필요 최소 데이터:

```text
feed_quantity
feed_unit_cost
pig/group weight
period
```

### 무료/유료 가설

- Basic FCR / 기본 변화: Free 후보
- Feed Cost / kg gain, 심층 trend/action: Paid hypothesis

**WTP는 아직 HYPOTHESIS. 가격 실험 전 VERIFIED로 표기 금지.**

## 5-3. Feed 2단계

P1.5 이후:

- IOFC
- 시나리오 비교
- Optimal Marketing Weight
- Packer grid economics (US)
- Multi-farm Feed economics

추가 prerequisite:
- 판매가격
- 판매두수/판매중량
- revenue scope
- 가격/출하 기준의 국가별 모델

## 5-4. 지금 뒤로 미룰 것

### Off-feed anomaly

연구 근거는 강하지만, peer-reviewed 연구의 off-feed는 ESF 등 고빈도 급이 데이터에 의존한다.

따라서:

```text
현재 일반 기록만으로 동일 성능을 주장하지 않는다.
ESF / feed sensor integration track으로 분리.
```

### Feed inventory / delivery

유용하지만 경쟁제품에 이미 널리 존재.
PigOS의 첫 차별화 기능으로 만들지 않는다.

---

# 6. Health — 제품 결정

## 6-1. 핵심 방향

PigOS는 질병 진단 AI를 먼저 만들지 않는다.

제공 범위:

```text
이상 신호
위험 증가
확인 대상
확인 작업
수의사에게 전달할 근거
```

진단명·처방·약물용량은 별도 수의 판단 영역으로 남긴다.

## 6-2. Health 일부를 Feed보다 앞당긴다

이유:
- PigOS에 이미 번식·폐사 관련 데이터가 존재.
- 연구에서 abortion/PWM/dead-sow 등 기존 운영 데이터의 이탈이 질병 조사 트리거로 유효.
- Feed의 고급 경제성/고빈도 off-feed보다 prerequisite가 작다.

### Health Watch 우선순위

1. **Reproductive anomaly watch**
   - abortion
   - return-to-estrus
   - farrowing-rate change

2. **Mortality / neonatal-loss anomaly**

3. **Barn / cohort watchlist**
   - 어디부터 확인할지 연결

4. **Vet-ready evidence pack**
   - 변화
   - 기간
   - 영향 개체/돈군
   - 관련 기록
   - 사용자가 한 조치

5. **Off-feed / Water integration**
   - sensor/ESF 데이터가 있을 때

### 국가 운영 Pack으로 분리

- ASF checklist
- Vaccination reminder
- Biosecurity task

이들은 국가별 규정·수의 기준 업데이트 책임이 크므로 Core Health Engine과 분리한다.

## 6-3. 안전 표현

허용:

```text
"최근 4주 평균보다 유산이 증가했습니다."
"이 돈군의 이유 전 폐사율이 평소 범위를 벗어났습니다."
"건강 이상 가능성을 확인하세요."
```

금지:

```text
"PRRS입니다."
"PRRS일 확률 82%입니다."  # 검증된 모델/의료정책 없이는 금지
"이 약을 투여하세요."
```

이 제한은 경쟁사가 못 해서가 아니라 **PigOS의 제품 안전정책**이다.

---

# 7. AI — 제품 결정

## 7-1. AI는 마지막 계산기가 아니다

KPI 값, 비교, 변화, 금액은 LLM이 생성하지 않는다.

### ENGINE_ONLY

- 오늘 문제 몇 개?
- 지난주 대비 무엇이 변했나?
- 어떤 모돈/돈사를 확인해야 하나?
- KPI 값은?
- benchmark 비교는?
- 사료효율 악화 비용은?
- 어떤 formula로 계산했나?

### ENGINE + AI_EXPLANATION

- 왜 이 변화가 중요한가?
- 가능한 원인 후보 3개는?
- 무엇부터 확인해야 하나?
- 이번 주 결과를 자연어로 요약해줘.

### AI_ASSISTED

- 개선계획 초안
- 주간/월간 보고서
- 여러 카드의 맥락 통합
- 수의사/경영자용 설명 변환

## 7-2. 첫 AI UX

빈 Chat 홈을 먼저 만들지 않는다.

```text
What Changed 카드
→ "왜?"
→ "무엇을 확인?"
→ "이번 주 계획"
```

같이 **맥락 있는 질문**부터 시작한다.

### 첫 버전 질문 10개

1. 이번 주 확인해야 할 문제는?
2. 지난주와 뭐가 달라졌어?
3. 오늘 확인할 모돈/돈사는?
4. 뭘 먼저 확인해야 해?
5. 분만율이 떨어진 원인 후보는?
6. 사료효율 악화가 비용에 얼마나 영향 줬어?
7. 비교 가능한 benchmark가 있으면 우리 위치는?
8. 목표 KPI를 개선하려면 어떤 항목부터 봐야 해?
9. 이번 주 건강 이상신호는?
10. 이 KPI는 어떤 공식으로 계산했어?

## 7-3. Proactive vs Conversational

판정:

```text
Proactive First = SUPPORTED_INFERENCE
Conversational preference 직접 양돈 연구 = 아직 미확보
```

UX 역할:

| 상황 | 우선 |
|---|---|
| 홈 | Proactive |
| 알림 | Proactive |
| 변화 탐색 | Proactive → Contextual question |
| 원인/설명 | Conversational |
| 보고서 | Conversational/AI-assisted |

---

# 8. 역할별 제품과 과금

| 역할 | 핵심 가치 | 과금 방향 |
|---|---|---|
| Worker / Manager | 오늘 할 일, 이상 개체/돈군, 빠른 입력 | Free 중심 |
| Owner | KPI, 변화, Feed economics, benchmark | Free + Paid |
| Vet / Consultant | anomaly, cohort, evidence pack, intervention history | Paid hypothesis |
| Integrator | multi-farm, outlier, portfolio benchmark | Enterprise hypothesis |

정확한 과금 원칙:

> **worker-facing input/action workflow는 별도 paywall로 막지 않는다.**
> 과금은 farm/org entitlement 단위로 하고 advanced analytics/management에 적용한다.

WTP는 아직 직접 검증되지 않았다.

---

# 9. 경쟁사와 실제 공백

이미 경쟁사가 강한 영역:

- Alert
- Tasks/Action
- Benchmark
- Multi-farm
- Feed
- Cost
- Mobile/Offline
- Vet collaboration
- 일부 AI health

따라서 아래 단독 기능은 해자가 아니다.

```text
"우리는 알림이 있다"
"우리는 FCR이 있다"
"우리는 AI가 있다"
"우리는 Multi-farm이다"
```

PigOS의 실제 결합 공백:

```text
Country Evidence
→ 정확한 Formula
→ 승인된 Threshold
→ What Changed
→ 근거가 있는 원인 후보
→ Action
→ 이후 Outcome
```

즉 **여러 나라에서 동일한 거버넌스로 설명 가능한 실행 레이어**가 핵심이다.

---

# 10. 최종 개발 순서

## Phase 0 — 선행조건

- D-13 canonical formula / LIVE_DIVERGENCE 해소
- D-17 G3를 전역 new-country launch gate로 적용
- D-19 audit 결과 소비
- D-21 threshold identity/scope/versioning 설계
- `as_of`/historical reproducibility
- formula/rule/threshold version 추적

## Phase 1 — Execution Core

1. Role-aware Home
2. What Changed
3. Action Center
4. Weekly Brief / Notification

## Phase 1B — Existing-data Health Watch

1. Reproductive anomaly
2. Mortality/neonatal-loss anomaly
3. Barn/cohort watchlist
4. Vet evidence export/brief

## Phase 2 — Feed Basic

1. FCR
2. Feed Cost / pig
3. Feed Cost / kg gain
4. Feed What Changed
5. Action 연결

## Phase 3 — Root Cause Candidate + Benchmark depth

- 가능한 원인 후보
- 확인 데이터
- 확인 작업
- cohort/farm-size benchmark
- multi-farm 기반 구축

## Phase 4 — Advanced Profitability

- IOFC
- scenario
- optimal marketing weight
- US packer-grid economics
- multi-farm economics

## Phase 5 — Contextual AI Copilot

- 카드 맥락 기반 질문
- 설명
- 계획
- 보고서
- 안전 라우팅

## Integration Track

- ESF/feed sensor
- Water sensor
- IoT high-frequency health
- 국가별 messenger channel

---

# 11. 이번 통합으로 변경된 것

| 항목 | 이전 | v1.0 |
|---|---|---|
| MX benchmark | 단독 미확보 | NATIONAL 미확보 + MX-specific FARM_COHORT evidence 존재 |
| TH | PWM 근거 중심 | PSY/NPD·multiple formula evidence 강화 |
| VN | KPI/benchmark 일부 낙관 | national benchmark/threshold 보수 유지 |
| Feed 1 | Feed/Profitability 넓게 | FCR + Feed Cost/pig + Cost/kg gain |
| Health | Feed 뒤 | existing-data anomaly를 Phase 1B로 앞당김 |
| off-feed | 일반 기능 후보 | ESF/sensor integration dependency |
| AI | P2 | 유지. Engine-first/contextual |
| Proactive | 거의 확정 | SUPPORTED_INFERENCE로 정확히 표기 |

---

# 12. 아직 결정하지 않는 것

- 모든 Paid 기능의 WTP
- VN national benchmark
- TH national PSY benchmark
- MX NATIONAL benchmark
- 국가별 messenger가 실제 retention을 높이는지
- AI Chat vs Proactive의 직접 양돈 사용자 선호
- 임의 성공률 cut-off (20%, 30%, 50% 등)

초기 beta에서는 하드 임계값보다 instrumentation baseline을 먼저 수집한다.

---

# 13. 개발 문서로 넘기는 규칙

개발자는 이 문서에서 **무엇을 만들지/무엇을 만들지 않을지**를 읽는다.

다음은 다른 SSOT가 결정한다.

| 질문 | SSOT |
|---|---|
| KPI 공식은 무엇인가 | D-13 / Canonical Formula |
| 외부 source가 동치인가 | COUNTRY_KPI_EVIDENCE_ARCHITECTURE |
| threshold 근거·버전은 | D-19 → D-21 |
| benchmark를 제품에 써도 되는가 | G1/G2/G3 + Decision Register |
| 구현 순서/제품 범위는 | **본 문서** |
| API/DB/UI acceptance는 | **PIGOS_PRODUCT_IMPLEMENTATION_HANDOFF_v1.0.md** |

두 개의 병렬 승인 메커니즘을 만들지 않는다.
