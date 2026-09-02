# PIGOS_COUNTRY_LEGAL_ONBOARDING_SPEC v1.0

> PigOS 국가별 회원·농장 가입 / 약관 / 개인정보 / 동의 / 증빙 통합 설계
> 기준일: 2026-09-02
> 상태: DEVELOPMENT BASELINE / LEGAL APPROVAL PENDING
> 중요 원칙: **법무 승인되지 않은 문서는 Production에 게시하지 않는다.**

---

# 1. 결론

PigOS의 약관은 국가마다 달라져야 한다. 그러나 국가마다 이용약관 전체를 복제하는 구조로 만들지 않는다.

```text
GLOBAL
│
├─ MASTER_TERMS              전 세계 공통 서비스 이용조건
├─ GLOBAL_PRIVACY_NOTICE     전 세계 공통 개인정보 처리 기본구조
└─ COUNTRY / REGION ADDENDUM
     ├─ US  ├─ EU  ├─ GB  ├─ BR  ├─ TH  ├─ VN  └─ 향후 국가
```

실제 동의 여부는 별도의 서버 정책으로 결정한다.

```text
문서 내용 + 국가별 Consent Policy + 처리 목적 + 회원국가/농장국가
        ↓
Signup Consent Plan
```

**Legal document 와 Consent decision 은 분리한다.**

---

# 2. 회원가입과 농장가입도 분리한다

한 사용자가 여러 농장을, 향후 여러 국가의 농장을 관리할 수 있다. 약관 scope 를 `user` 하나로 만들면 안 된다.
현재 백엔드가 이미 채택한 `(user, farm, purpose)` 를 유지한다.

## 2.1 회원가입

```text
MASTER_TERMS + GLOBAL_PRIVACY_NOTICE + 계정 수준 필수 고지/동의

KR   MASTER + PRIVACY
BR   MASTER + PRIVACY + ADDENDUM_BR
US   MASTER + PRIVACY + ADDENDUM_US
```

---

# 3. 농장 생성 시 다시 법역을 판단한다

회원 국가와 농장 국가가 항상 같다고 가정하지 않는다.

```text
Create Farm → farm_country → Jurisdiction Resolver → Country Legal Policy
   → 추가 동의 필요?  NO → 농장 생성
                     YES → Consent 화면 → 기록 완료 → 농장 활성화
```

`selected_country + farm_country` 기반 authority 방향을 유지한다.
**GeoIP · 휴대폰 언어 · Device locale 을 법적 국가 결정 기준으로 사용하지 않는다.**
Device locale 은 **약관을 어떤 언어로 보여줄 것인가**에만 쓴다.

---

# 4. 국가가 충돌할 경우

더 엄격한 정책을 적용하고 `counsel_review=true` 를 생성한다(현재 구현 유지). 장기적으로는 strictness 숫자 비교보다 명시적 반환으로 간다.

```json
{
  "account_jurisdiction": "US",
  "farm_jurisdiction": "BR",
  "effective_jurisdiction": "BR",
  "reason": "FARM_COUNTRY_OVERRIDE"
}
```

---

# 5. 게시 문서 체계

| 문서 | 역할 |
|---|---|
| MASTER_TERMS | 공통 서비스 이용약관 |
| GLOBAL_PRIVACY_NOTICE | 공통 개인정보 처리 고지 |
| COUNTRY_ADDENDUM | 국가별 개인정보·권리·이전·특칙 |
| COOKIE_POLICY | 웹 쿠키/추적기술 정책 |
| SUBPROCESSOR_LIST | AWS·AI·결제 등 처리업체 공개 |
| DATA / AI NOTICE | 필요 시 데이터 분석·AI 처리 별도 고지 |

국가별로 MASTER_TERMS 를 복사하지 않는다. 차이는 최대한 `COUNTRY_ADDENDUM` 에 격리한다.

---

# 6. 기업 고객용 문서는 별도다

```text
MASTER TERMS + B2B DPA + COUNTRY ADDENDUM + 필요한 SCC / TIA
```

`drafts/PIGOS_B2B_DPA_DRAFT.md` 가 이 구조를 전제로 작성돼 있다 — **실측 확인됨.**

```
제0조②   국가별 부속(COUNTRY_ADDENDA)·SCC 가 본 DPA 에 우선 적용   [COUNSEL]
제2조     고객 입력 직원·계약농가 → 고객=controller, 회사=processor
          가입·계정·결제·보안·이용분석 → 회사=controller (DPA 미적용)
```

**LEGAL-D13 방향을 유지한다.**

```text
기업고객 경유 데이터 → 기본값 purpose_2_eligible = false → PigSignal 편입 금지
```

근거: `internal/DECISION_ONE_PAGERS.md:104,133` · `internal/LIA_PURPOSE2_DRAFT.md:19`
(LIA 대상은 직접 가입 이용자가 자기 계정으로 입력한 데이터에 한정)

---

# 7. 현재 PigOS 구현 상태 (2026-09-02)

| 영역 | 상태 |
|---|---|
| Backend jurisdiction resolver | 구현 |
| 국가별 consent matrix | 구현 |
| Web signup consent | 구현 |
| Android signup consent | 구현 |
| iOS signup consent | **미구현** |
| consent ledger | 구현. 증빙 필드 부족 |
| 국가별 실제 문서 | publish_candidate 존재 |
| Runtime 국가 부속문서 | **placeholder** |
| BR pt / TH th / VN vi | 미연결·미완성 |
| 강제 재동의 | 미구현 |
| 국가별 철회 정책 | 일부 결함(Web) |
| Legal approval | NO |

```text
법역 판단 OK · Consent Plan OK · 동의 저장 부분 OK
실제 승인 약관 NO · 정확한 언어 증빙 NO · 약관 본문 재현 NO · iOS 동의 기록 NO
```

---

# 8. 현재 가장 큰 문제

```text
사용자가 동의함 YES · DB에 남음 YES
그런데 본 문서가 placeholder YES · 표시 언어 저장 NO · 본문 snapshot/hash NO
```

> "2026-09-02 브라질 농장 사용자 A가 어떤 포르투갈어 약관을 보고 동의했는가?"

에 답할 수 없다. → `historical_reproducibility = NOT_REPRODUCIBLE`

★ 다만 실제 오염은 발생하지 않았다 — §21 CLOSED 항목 참조.

---

# 9. Consent Ledger 보강

기존 원장을 갈아엎지 않는다. 최소 다음을 추가한다.

```text
user_id · farm_id · purpose_code
jurisdiction · locale · channel
consent_status · accepted_at · withdrawn_at
document_evidence · supersedes_id
```

```json
[
  {"document_code":"MASTER_TERMS","version":"1.0","language":"pt-BR","sha256":"...","effective_at":"..."},
  {"document_code":"ADDENDUM_BR","version":"1.0","language":"pt-BR","sha256":"..."}
]
```

현재처럼 `MASTER_TERMS@x+GLOBAL_PRIVACY_NOTICE@y+ADDENDUM_BR@z` 를 **한 문자열로 저장하는 방식은 장기 증빙으로 쓰지 않는다.**

---

# 10. 문서 버전은 immutable

같은 version 으로 내용을 수정하지 않는다. `1.0 → 1.1` 로 올리고 1.0 은 보존한다.

```text
document_code · jurisdiction · version · language · content_hash
status · published_at · effective_at · requires_reconsent
```

---

# 11. Legal Document Lifecycle

```text
DRAFT → COUNSEL_APPROVED → PUBLISH_READY → PUBLISHED → SUPERSEDED → RETIRED
```

```text
runtime resolver 가 읽을 수 있는 문서  =  PUBLISHED ONLY
```

`DRAFT_LAWYER_PENDING` 문서를 사용자에게 노출하고 동의까지 받는 구조는 제거한다.

---

# 12. publish_candidate 운영방식

법무 검토용 작업공간으로 계속 사용하고, 승인 후에만 promotion 한다.

```text
publish_candidate → COUNSEL_APPROVED → validation → immutable hash
    → runtime legal content → manifest PUBLISHED
```

수동 복사·manifest 수기 수정보다 promotion command 를 권장한다.

```text
legal promote ADDENDUM_BR 1.0 pt-BR
```

자동 검사: approval 존재 · placeholder 없음 · required language 존재 · version 중복 없음 · hash 생성 · manifest validation · integration test

---

# 13. Signup API 방향

클라이언트가 국가별 법률 판단을 하지 않는다. Web/Android/iOS 모두 동일 API 만 쓴다.

```text
GET /consent/plan
```

```json
{
  "plan_id": "...",
  "jurisdiction": {"account":"BR","farm":"BR","effective":"BR"},
  "documents": [
    {"code":"MASTER_TERMS","version":"1.0","lang":"pt-BR","hash":"...","required":true},
    {"code":"GLOBAL_PRIVACY_NOTICE","version":"1.0","lang":"pt-BR","hash":"...","required":true},
    {"code":"ADDENDUM_BR","version":"1.0","lang":"pt-BR","hash":"...","required":true}
  ],
  "purposes": [],
  "gates": {"signup_blocked":false,"paid_blocked":false,"release_hold":true}
}
```

기록은 `POST /consent/record`. 클라이언트가 문서 version 을 보내는 대신 **`plan_id` + 사용자의 선택**만 보낸다. 서버가 그 plan 의 document snapshot 을 증빙으로 저장한다 — 클라이언트 변조와 플랫폼 차이를 막는다.

---

# 14. 언어 정책

```text
country → 어떤 법을 적용할지
locale  → 어떤 번역본을 표시할지
```

법정 필요 언어가 없을 때 **en 자동 fallback → 가입 성공**으로 처리하지 않는다.

```text
REQUIRED_LEGAL_LANGUAGE_MISSING → signup blocked
```

법무가 명시적으로 영어 대체 표시를 승인한 국가에만 exception 을 둔다.

---

# 15. Unsupported Country 처리

unknown → `OTHER` 로 MASTER+PRIVACY 만 받고 가입되는 현재 구조는 장기적으로 제거한다.

```text
LEGAL_READY · LIMITED · HOLD · UNSUPPORTED

BR LEGAL_READY · TH HOLD_PAID · VN HOLD_PAID · CN HOLD_SIGNUP · XX UNSUPPORTED
```

가입 가능 여부를 프론트가 추측하지 않는다. 서버 정책이 반환한다.

---

# 16. 국가 정책 Registry

```text
country_code · legal_group
signup_status · paid_status · data_release_status
master_terms_version · privacy_version · country_addendum
required_languages
representative_required · transfer_mechanism
legal_approval_status · effective_at
```

---

# 17. ID Namespace 분리

KPI 트랙과 법무 트랙의 D 번호가 **실제로 충돌한다.**

```text
LEGAL  D-07 CN 진입 HOLD          docs/legal/CONSENT_AND_DATA_USE_SPEC.md:41,53,65,77,89
       D-08 VN 게이트              api/app/services/jurisdiction.py
       D-09 TH 게이트              api/app/services/jurisdiction.py
       D-13 controller/processor  publish_candidate 6개국 부속조항 전부

KPI    D-8  외부 정의 대조·mapping  docs/kpi/CANONICAL_FORMULA_SPEC.md:52,95,98,362
       D-13 전 경로 재실사          docs/kpi/CANONICAL_FORMULA_SPEC.md:53,83
       D-19 · D-20 · D-21
```

**D-8 과 D-13 이 두 트랙에 동시에 존재한다.** 앞으로 작성하는 문서·코드는 namespace 를 붙인다.

```text
LEGAL-D07 · LEGAL-D08 · LEGAL-D09 · LEGAL-D13
KPI-D08 · KPI-D13 · KPI-D19 · KPI-D20 · KPI-D21
```

## 17.1 Legacy identifier alias

★ **전역 rename 은 하지 않는다.** 코드 상수까지 바뀌면 되돌리기 어렵고 열려 있는 PR 과 충돌한다.
기존 식별자는 legacy 로 유지하고 아래 alias 로 해석한다.

| legacy identifier | 위치 | 정본 ID |
|---|---|---|
| `HOLD_D07` | `api/app/services/jurisdiction.py` `_GATES["CN"]` | LEGAL-D07 |
| `GATE_D08` | `api/app/services/jurisdiction.py` `_GATES["VN"]` | LEGAL-D08 |
| `GATE_D09` | `api/app/services/jurisdiction.py` `_GATES["TH"]` | LEGAL-D09 |
| 법무 문서의 `D-13` | `publish_candidate/**` · `LAWYER_BRIEF` · `HUMAN_INPUT_QUEUE` | LEGAL-D13 |
| KPI 문서의 `D-8` / `D-13` | `docs/kpi/**` | KPI-D08 / KPI-D13 |

---

# 18. Re-consent

개정이 항상 재동의를 요구하면 안 되지만, 필요한 변경은 시스템이 강제할 수 있어야 한다.
문서 버전에 `requires_reconsent` 를 둔다.

```text
로그인 → Consent Status → 1.1 미동의 → needs_action=true → 재동의 화면
```

현재 Amendment Banner 만 표시하고 강제하지 않는 상태를 보완한다.

---

# 19. 철회도 서버가 결정한다

Web 의 `ANON_AGG_STATS → EXCLUSION_REQUESTED` 같은 국가 독립 하드코딩을 두지 않는다
(`src/app/(app)/settings/data/page.tsx:22-29` `ACTION_FOR`). 서버가 목적과 법역을 보고 반환한다.

```text
WITHDRAW · OBJECT · EXCLUSION_REQUEST · NOT_AVAILABLE
```

Android 가 이미 이 방향이다(서버 `ui_kind` 유도). Web/iOS 도 맞춘다.

---

# 20. Client Rule

```text
금지   if country == BR ... / if country == VN ...
허용   render(plan.documents) · render(plan.purposes) · render(plan.allowed_actions)
```

특히 iOS `InfoScreens.swift` 처럼 별도 법무 문구를 하드코딩하지 않는다.
법무 문구의 SSOT 는 backend legal content registry 다.

---

# 21. 현재 과제

★ **번호형 `P0-1`·`P0-2` 를 쓰지 않는다.** 그 번호는 이미 다른 트랙에서 오염됐다
(`PLATFORM_PARITY §9 P0-1` = iOS insufficient→success, `docs/kpi/**  P0-2` = AMBIGUOUS 산식 결정).
이 스펙의 과제는 **의미 ID** 로 쓴다.

## COMPLETED

### `LEGAL-ONBOARDING-AUDIT-CONSENT-LEDGER` — CLOSED

```text
consent_ledger rows           0
PLACEHOLDER_CONSENT_PROD      NOT_FOUND
reconsent_decision_required   NO
evidence commit               4714283
문서                          docs/legal/PRODUCTION_CONSENT_LEDGER_AUDIT_20260902.md
```

placeholder 약관에 이미 동의받은 사고는 **없었다.** 과거 사용자 정리·소급 재동의 없이,
승인된 실제 약관이 준비되는 시점부터 깨끗하게 시작할 수 있다.

> 부수 발견(별도 추적): 배포 이후 가입 ≥1건에 대응하는 원장 행이 0건이며
> `CONSENT_RECORDING_IN_PRODUCTION = INCONCLUSIVE`. 원인은 iOS 미배선 ·
> 배포 후 미재기동 · 호출 실패 중 확정 불가.

## OPEN — P0

### `LEGAL-ONBOARDING-P0-IOS-CONSENT`

iOS 도 `GET /consent/plan` → 문서 표시 → required/optional 선택 → `POST /consent/record` 를 사용한다.
현재 로컬 checkbox 만으로 가입이 진행되는 구조를 제거한다.

```text
현재   OnboardingScreen.swift:13,14  agreedToTerms · acknowledgedPrivacy
       OnboardingScreen.swift:179    .disabled() 만 제어. 서버 전송 0건
       → 원장에 iOS 사용자 기록이 존재하지 않는다
```

### `LEGAL-ONBOARDING-P0-CONSENT-EVIDENCE`

최소 `locale` · `channel` · `document evidence/hash` · `supersedes` 를 저장한다.
목표: **특정 사용자가 특정 시간에 정확히 어떤 문서·버전·언어를 보았는가**에
DB 와 immutable document store 만으로 답한다.

### `LEGAL-ONBOARDING-P0-RUNTIME-PUBLISH-GATE`

`status != PUBLISHED` 문서는 Production signup resolver 가 반환하지 않는다.
법무 승인 전이므로 **`publish_candidate` 를 바로 연결하지 않는다.**

```text
legal_draft_assets_ready = YES / SUBSTANTIAL
legal_approval_ready     = NO
```

## OPEN — P1

### `LEGAL-ONBOARDING-P1-LEGAL-PROMOTION`

promotion 파이프라인·검증 코드는 지금 만들 수 있다. 단 실제 `PUBLISHED` 승격은
`legal_approval_ready = YES` 전까지 **HOLD** 다.

기타 P1: Web withdrawal server-driven 전환 · revision/re-consent 구현 ·
unsupported country fail-closed · per-document evidence 강화 · Web/Android/iOS parity test

---

# 22. 개발 순서

```text
1. iOS consent 서버 배선        GET /consent/plan · POST /consent/record
2. Consent evidence 강화        locale · channel · document version/hash
3. Production publish gate      DRAFT/placeholder 반환 금지
        ↓  여기까지 개발 가능
   LEGAL APPROVAL 대기
        ↓
4. 승인 문서 promotion → BR pt / TH th / VN vi 연결 → Production 첫 정상 consent
```

---

# 23. 국가별 QA Matrix (CI)

| Case | 기대 결과 |
|---|---|
| US | US 문서 |
| US strict state | 해당 주 consent rule |
| BR + pt-BR | BR + 포르투갈어 |
| TH + th | TH + 태국어 |
| VN + vi | VN + 베트남어 |
| EU | EU Addendum |
| GB | GB Addendum |
| CN | signup blocked |
| unsupported | fail-closed |
| US user + BR farm | 새 BR consent |
| 문서 revision | re-consent |
| Web / Android / iOS | 동일 plan |

---

# 24. 법무 승인과 개발 승인 분리

```text
ENGINEERING_READY  ≠  LEGAL_APPROVED

ADDENDUM_BR
  document exists YES · translation exists YES · runtime compatible YES
  tests pass YES · legal approved NO · published NO
```

개발자가 문서 내용을 보고 "충분해 보인다"는 이유로 PUBLISHED 로 올릴 수 없다.

---

# 25. 국가 추가 절차

```text
1 research → 2 legal policy → 3 addendum draft → 4 번역 → 5 counsel review
→ 6 approval 기록 → 7 registry 등록 → 8 immutable publish → 9 consent plan test
→ 10 Web/Android/iOS UAT → 11 Production enable
```

코드에 국가 전용 조건문을 추가하는 과정은 없어야 한다.

---

# 26. 최종 목표 — 9개 질문

```text
WHO · WHERE · WHAT · VERSION · LANGUAGE · WHEN · PURPOSE · ACTION · EVIDENCE
```

이 9개에 즉시 답할 수 있으면 국가별 약관/동의 시스템이 완료된 것이다.

---

# 27. 현재 전체 판정

```text
LEGAL ARCHITECTURE       READY
COUNTRY RESOLUTION       READY
CONSENT POLICY           READY
WEB UI                   READY
ANDROID UI               READY

IOS INTEGRATION          P0
CONSENT EVIDENCE         P0
RUNTIME CONTENT GATE     P0

COUNTRY LEGAL CONTENT    DRAFT READY
LEGAL APPROVAL           HOLD
PUBLICATION              BLOCKED BY LEGAL APPROVAL

OVERALL
→ ARCHITECTURE_READY
→ PRODUCTION_LEGAL_READY = NO
```

**새로운 법무 시스템을 다시 설계할 단계가 아니다.** 이미 만든 구조를
실제 승인 문서 → 정확한 언어 → Runtime → 모든 플랫폼 → Immutable Evidence → Re-consent
까지 연결하여 닫는 것이 남은 일이다.

`consent_ledger = 0` 결과로 성격이 한 단계 좋아졌다 — **기존 오염 데이터를 수습하는
프로젝트가 아니라, 첫 Production 동의 전에 마지막 배선과 증빙을 만들어놓는 프로젝트**다.

---

## 부록 A. 이 스펙이 실측으로 확인한 것

```text
약관/개인정보 별도 동의는 이미 구현돼 있다 — 신규 과제가 아니다
  api/app/services/consent_service.py:119   required_acks = ["TERMS","PRIVACY"]
  api/app/services/consent_service.py:137   422 TERMS_AND_PRIVACY_ACK_REQUIRED
  src/components/consent/ConsentForm.tsx:92,93  체크박스 2개 (묶음 아님)
  src/components/consent/ConsentForm.tsx:42     canSubmit = termsAck && privacyAck
  pigos-ios OnboardingScreen.swift:12           "묶음 금지, 각각 별도 체크" 주석 존재

B2B DPA 구조 (§6)
  drafts/PIGOS_B2B_DPA_DRAFT.md:12,13   COUNTRY_ADDENDA·SCC 우선 적용
  drafts/PIGOS_B2B_DPA_DRAFT.md:28,29   controller/processor 역할 분리
  internal/DECISION_ONE_PAGERS.md:104,133 · internal/LIA_PURPOSE2_DRAFT.md:19
                                        purpose_2_eligible=false 기본값

D 번호 충돌 (§17)  실제로 D-8 · D-13 이 두 트랙에 동시 존재

철회된 관찰
  "Android 가 lang 을 안 보낸다" 는 오독이었다 — ViewModel 호출부만 보고
  리포지토리 기본값을 따라가지 않았다. ConsentRepository.kt:45,67 이
  `lang ?: appLang()` 으로 채운다. Android 는 lang 을 정상 전송한다.
  BR/TH/VN 이 영어로 폴백되는 원인은 클라이언트가 아니라 manifest 에
  pt/th/vi 파일이 없는 것이다.
```

## 부록 B. 관련 문서

```text
docs/legal/LEGAL_PUBLICATION_GAP_REPORT_20260902.md      문서·구현·승인 gap
docs/legal/PRODUCTION_CONSENT_LEDGER_AUDIT_20260902.md   운영 데이터 실측
docs/legal/TERMS_DISPLAY_SPEC.md                         표시 규칙 원본
docs/legal/CONSENT_AND_DATA_USE_SPEC.md                  목적×법역 매트릭스 원본
docs/legal/IMPLEMENTATION_COVERAGE.md                    §7 체크리스트 ↔ 코드
docs/legal/HUMAN_INPUT_QUEUE.md                          회사 입력 필요값 H1~H10
docs/PLATFORM_PARITY.md §9                               P0 correctness blockers
```
