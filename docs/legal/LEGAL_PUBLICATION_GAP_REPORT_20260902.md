# LEGAL_PUBLICATION_GAP_REPORT — 2026-09-02

> **성격**: READ-ONLY 감사. 신규 약관 작성 0건 · 코드/manifest 수정 0건 · 리서치 재실행 0건.
> **목적**: "국가별 약관을 새로 만들어야 하는가"가 아니라 **"이미 만들어 둔 것을 무엇만 채우면 게시 가능한가"** 를 확정한다.

---

## 0. 이 보고서가 폐기하는 표현

앞선 `COUNTRY_LEGAL_CONSENT_AUDIT`(같은 날 세션)의 아래 표현은 **부정확하므로 폐기**한다.

```
폐기   country_docs_ready = NO
폐기   COUNTRY_ADDENDUM_NOT_CONNECTED  (P0 bug 계열로 분류한 것)
```

두 표현 모두 **DOCUMENT_ABSENT** 와 **RUNTIME_NOT_CONNECTED** 를 뭉갠다. 실제 상태는 다르다.

```
LEGAL_DRAFT_EXISTS
        BUT
RUNTIME_NOT_CONNECTED
```

★ **placeholder 는 구현 실수가 아니다.** `docs/legal/IMPLEMENTATION_COVERAGE.md` 가 이를 설계로 명시한다 —
"약관 문구 하드코딩 안 함 — `content/legal/*.md` DRAFT placeholder, **확정본 파일 교체로 반영**",
"`any_draft=true` 가 게시 차단 신호". 즉 **승인 전 publication gate** 이며, 승인 없이 연결하는 것이
오히려 규율 위반이다.

---

## 1. 용어 — LEGAL-D13 (번호 충돌 정정)

이 저장소에는 `D-13` 이 두 개 있다. **서로 무관하다.**

| 표기 | 의미 | 소관 |
|---|---|---|
| `LEGAL-D13` | controller / processor 역할 확정 | 법무 (본 보고서) |
| `KPI-D13` / `D-13 Canonical Formula Audit` | KPI 정본 공식 감사 | KPI 트랙 |

```
LEGAL-D13
  controller / processor 역할 확정

legacy reference
  기존 legal 문서(publish_candidate·drafts·LAWYER_BRIEF·HUMAN_INPUT_QUEUE)의 "D-13"

주의
  KPI-D13 / D-13 Canonical Formula Audit 과 무관
```

기존 법무 문서의 일괄 rename 은 하지 않는다(전역 치환 금지). **본 보고서 이후 작성분에서만**
`LEGAL-D13` 표기를 사용하고, 기존 문서를 읽을 때 위 alias 로 해석한다.

---

## 2. 정본 선정 — 어느 문서가 최신인가

세 계층이 존재하며 **서로 다른 문서**다. 같은 문서의 버전 차이가 아니다.

```
docs/legal/drafts/COUNTRY_ADDENDA/     10.0–12.5 KB   내부 검토 주석 포함 작업본
        ↓ 주석 제거 · 고객 노출용 정리
docs/legal/publish_candidate/           5.5– 8.4 KB   ★ v1.0-rc (2026-08-04)  ← 최신 정본
        + publish_candidate/en/         6.8– 9.9 KB   영문 대응본
        ↓ (연결되지 않음 — 의도된 게이트)
api/content/legal/                      394–  782 B   placeholder 스텁
```

★ `docs/legal/FILE_MANIFEST.md`(2026-07-21)는 `drafts/` 를 고객 공개 대상으로 지정하고 있으나
**`publish_candidate/` 디렉터리 자체를 모른다**(그보다 먼저 작성됨). 정본은 `publish_candidate/` v1.0-rc 다.
FILE_MANIFEST 갱신은 후속 과제로 남긴다(본 감사에서 수정하지 않음).

### 게시 후보본 헤더 (전 문서 공통, 실측)

> 게시 후보본 v1.0-rc (2026-08-04) — 게시 전 최종 확정 필요. 본 문서는 내부 검토 주석을 제거한
> 고객 노출용 정리본입니다. 게시 조건: 본문 내 `[OPEN]`·`[COUNSEL]`·`[V]` 항목 확정 →
> 변호사 확인 → 대표 승인 → 공고일·시행일 기입.

---

## 3. Jurisdiction별 게시 갭

### US

```
latest_candidate      publish_candidate/ADDENDUM_US.md (8,350B) + en/ADDENDUM_US_EN.md (9,879B)
legal_draft_exists    YES — 州별 State Schedule · CA Notice at Collection · GPC/UOOM ·
                      Nebraska LB525 농업데이터 서면옵트인까지 설계 완료
ready_text            본문 전체 (아래 1건 외)
company_inputs        NONE
counsel_items         LEGAL-D13 1건 — "[OPEN — 역할 확정 후 DPA·본 조에 반영]"
                      (LAWYER_BRIEF 별도 트랙: LB525 전자동의=express written 충족 Q7 ·
                       데이터브로커 등록 · CAN-SPAM 주소 · CA ADMT/위험평가 Q8 · DOJ Rule Q10)
translation_items     NONE — 법정 우선어 = en, 이미 존재
runtime_current       api/content/legal/addendum_us.en.md (734B placeholder)
runtime_gap           CONTENT_NOT_CONNECTED (의도된 게이트)
publish_readiness     ★ 미결 최소 — LEGAL-D13 하나만 닫히면 게시 후보
```

### EU

```
latest_candidate      publish_candidate/ADDENDUM_EU.md (7,010B) + EN (8,302B)
legal_draft_exists    YES — Art.27 대리인 · Art.30 처리기록 · DPIA 검토 · LI + 이의권
company_inputs        H1  EU 대리인 명칭·주소 (rep-as-a-service 계약, 연 1~3천유로)
counsel_items         LEGAL-D13 / Art.37 DPO 해당성 / LIA 승인 / 회원국 언어
translation_items     ko·en 존재. 회원국 언어 필요 여부 = COUNSEL
runtime_current       addendum_eu.en.md (492B)
publish_readiness     BLOCKED — 대리인 계약 선행. CLAUDE.md 상 현재 타겟 아님
```

### GB

```
latest_candidate      publish_candidate/ADDENDUM_GB.md (6,767B) + EN (7,782B)
company_inputs        H2  UK 대리인 명칭·주소
counsel_items         LEGAL-D13 / DPO 해당성
translation_items     NONE (en)
runtime_current       addendum_gb.en.md (394B)
publish_readiness     BLOCKED — 대리인. 현재 타겟 아님
```

### BR

```
latest_candidate      publish_candidate/ADDENDUM_BR.md (7,184B) + EN (8,233B)
legal_draft_exists    YES — LGPD · ANPD SCC(Res. CD/ANPD 19/2024) · DPO(encarregado) 기입 완료 ·
                      LI + 이의권 · 언어 우선순위 · 인테그레이터 조항
company_inputs        NONE — DPO = 와이즈레이크(주) / wiselake@wiselake.ai (기입 완료)
counsel_items         ★ 3건 + LEGAL-D13
                      · SCC 전문 별도 첨부 필요 [OPEN]
                      · 국제이전(transferência internacional) vs 국제수집(coleta internacional)
                        구분 선행 — F1 exporter 주체 [COUNSEL]
                      · 완전 익명화 시 LGPD Art.12 제외 여부 — F3 [COUNSEL]
translation_items     ★ pt 본문 0건.  manifest legal_priority_lang="pt", pending_langs=["pt"]
runtime_current       addendum_br.en.md (541B)
publish_readiness     BLOCKED — SCC 전문 + pt 번역
```

### TH

```
latest_candidate      publish_candidate/ADDENDUM_TH.md (6,110B) + EN (7,190B)
company_inputs        H3  태국 대리인 (§37(5) 무한책임 — 대행계약 반영 조건은 COUNSEL Q9)
counsel_items         §37(5) 무한책임 대행 반영 / LEGAL-D13 / Thai SCC
translation_items     ★ th 본문 0건.  legal_priority_lang="th"
runtime_current       addendum_th.en.md (545B)
publish_readiness     BLOCKED — 대리인 + th 번역.  paid_blocked GATE_D09 유지 중
```

### VN

```
latest_candidate      publish_candidate/ADDENDUM_VN.md (5,468B) + EN (6,796B)
company_inputs        NONE
counsel_items         외부 DPO 지정 가능 여부·자격 요건 / LEGAL-D13
translation_items     ★ vi 본문 0건.  legal_priority_lang="vi"
runtime_current       addendum_vn.en.md (543B)
publish_readiness     BLOCKED — vi 번역.  paid_blocked GATE_D08 유지 중
```

### CN

```
latest_candidate      없음 (설계상 부재)
runtime               manifest 미등록 · jurisdiction._ADDENDUM["CN"]=None
gate                  signup_blocked HOLD_D07 → POST /consent/record 451
publish_readiness     N/A — 진입 자체가 HOLD (D-07, 현지 법무 필수)
```

### MASTER_TERMS

```
latest_candidate      publish_candidate/PIGOS_MASTER_TERMS.md (36,814B) + EN (40,493B)
company_inputs        3건 — 결제 통화·PG사·세금(부가세 포함) / 응대 영업일 수 / 시행일
counsel_items         1건 — 경과조치·기존 피그플랜 회원과의 관계
                      (KR_legal §8 재동의 경계선 분석 참조)
runtime_current       master_terms.en.md (782B) · master_terms.ko.md (702B)
```

### GLOBAL_PRIVACY_NOTICE

```
latest_candidate      publish_candidate/PIGOS_GLOBAL_PRIVACY_NOTICE.md (26,823B, 2026-08-27)
                      + en/PIGOS_GLOBAL_PRIVACY_NOTICE_EN.md (31,236B)
company_inputs        ★ 최다 — [V 실측 확인] 11건 + [OPEN 운영 확정] 9건
                      (탈퇴 유예·휴면 처리 / 미동기화분 보존 한도 / 원본 보관 여부·기간 /
                       백업 주기·완전삭제 시점 / 보존 근거·기간 등)
counsel_items         1건 — controller/processor 역할 = LEGAL-D13
runtime_current       privacy_notice.en.md (1,119B) · privacy_notice.ko.md (1,163B)
참고                  api/content/legal/public_privacy.{en,ko}.md 는 31KB/27KB 실문서이나
                      manifest 미등록 — /legal/privacy 렌더링 전용 (커밋 17e19b2)
```

---

## 4. 레버리지 — LEGAL-D13 하나가 7문서를 연다

```
LEGAL-D13  controller / processor 역할 확정
        ↓
US · EU · GB · BR · TH · VN   6개 부속조항 전부에 동일 문구로 대기
        "[OPEN — 역할 확정 후 DPA·본 조에 반영]"
+ GLOBAL_PRIVACY_NOTICE 제⑪조
```

변호사 판단 **1건**이 7개 문서의 미결을 동시에 해소한다. 법무 트랙의 최우선 항목이다.

★ 다만 **LEGAL-D13 을 닫았다고 바로 게시하면 안 된다.** `DOCUMENT_APPROVED` 라는 실제 승인 기록
(변호사 확인 + 대표 승인 + 공고일·시행일 기입)이 선행되어야 한다. 미결 소진 ≠ 승인.

---

## 5. RUNTIME 연결 상태

```
Backend    manifest.json 에 placeholder 9종만 등록 — publish_candidate 미연결
           consent 라우터 등록됨 (api/app/main.py:146)
           마이그레이션 d4a1b2c3e5f7 체인 포함
Web        src/app/onboarding/page.tsx:101 plan 조회 → :129 record
           placeholder 를 표시하고 동의를 기록한다
Android    OnboardingViewModel.kt:154 plan · :230 record
           동일. plan 조회 실패 시 가입 차단(커밋 f8fffd2 — 웹보다 엄격)
iOS        ✗ consent API 미사용
           OnboardingScreen.swift:13,14 체크박스는 :179 .disabled() 만 제어하고 전송되지 않음
```

### 미확인 — 별도 read-only audit 필요

```
질문   production 에서 실제로 notice_version="…@0.1-draft" 동의 기록이 발생했는가?
현재   코드 경로는 존재하나 실제 가입자가 placeholder 에 동의했는지 미확인
분류   UNVERIFIED — 본 감사 범위 밖 (production 조회 금지 조건)
```

이것이 확인되기 전까지 "placeholder 에 동의를 받고 있다" 는 **코드 경로 사실이지 운영 사실이 아니다.**

---

## 6. 독립 판정

`country_docs_ready` 단일 YES/NO 판정은 **사용하지 않는다** — 서로 다른 축을 뭉갠다.

```
legal_draft_assets_ready         YES / SUBSTANTIAL
    8개 문서 × (ko + en) = 16벌, 약 200KB
    국가별 리서치 7건 약 200KB 별도 보유
    부속조항 잔여 마커:  US 1 · EU 2 · GB 2 · BR 4 · TH 2 · VN 2

legal_approval_ready             NO
    전 문서 v1.0-rc · DOCUMENT_APPROVED 근거 없음
    회사 입력 3건(대리인) + 운영확정 9건 + 실측 11건 + COUNSEL 다건

translation_ready                NO
    보유   ko · en  (전 문서)
    부재   pt(BR) · th(TH) · vi(VN)  ← manifest 가 법정 우선어로 선언한 3개 언어
    미정   EU 회원국 언어 (COUNSEL)

runtime_connection_ready         NO
    publish_candidate ↛ manifest.json
    ★ 의도된 게이트. 승인 전 연결은 금지사항이며 결함이 아니다

consent_runtime_ready            PARTIAL
    Backend  ✓  법역 판별 · 목적×국가 매트릭스 · US 주별 분기 · append-only 원장
    Web      ✓  단, 철회 액션이 purpose_code 하드코딩(ACTION_FOR) — 법역 무시 (결함 1건)
    Android  ✓  서버 ui_kind 에서 유도 — 올바름
    iOS      ✗  미구현
    공통      locale · channel 미기록 → 동의 이력 재현 불가
```

---

## 7. 다음 순서

```
1  본 보고서 등재                                    ← 완료
2  LEGAL-D13 역할 확정                               변호사 1건 → 7문서 해소
3  회사 입력값 / COUNSEL 항목 닫기                    대리인 H1~H3 · 운영확정 9 · 실측 11
4  BR pt / TH th / VN vi 번역
5  승인된 문서만 runtime placeholder 교체              manifest version 상향
6  iOS consent 구현
7  consent auditability 보강                          locale · channel · 문서별 컬럼
```

가장 먼저 열릴 가능성이 높은 것은 **US** 다 — 회사 입력 0건, 번역 불요, 잔여 미결이 LEGAL-D13 하나뿐이며
온보딩 기본 국가이자 1차 출시 시장이다. **단, `DOCUMENT_APPROVED` 기록 없이 게시하지 않는다.**

---

## 8. 근거

```
정본 인벤토리      docs/legal/publish_candidate/**  (파일 크기·수정일 실측)
마커 추출          [OPEN · [COUNSEL · [V]  — 헤더 보일러플레이트 4행 제외 후 집계
정본 판정 근거     publish_candidate 각 문서 3행 헤더 "게시 후보본 v1.0-rc (2026-08-04)"
FILE_MANIFEST 구판  docs/legal/FILE_MANIFEST.md 헤더 "2026-07-21"
placeholder 의도    docs/legal/IMPLEMENTATION_COVERAGE.md "[하지 말 것] 준수 확인"
회사 입력 목록      docs/legal/HUMAN_INPUT_QUEUE.md  H1~H10
런타임 배선        api/app/main.py:146 · api/content/legal/manifest.json
                   src/app/onboarding/page.tsx:101,129
                   pigos-android OnboardingViewModel.kt:154,230
                   pigos-ios OnboardingScreen.swift:13,14,179
```
