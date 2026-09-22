# 2026-09-10 법무 P0 배포 게이트 — 배포 전 확정 사항

> **작성**: 2026-09-09 · machine `bjh` · 실측 기반
> **성격**: **법무 배포의 기준 문서.** 앞으로 진행 상황은 "P0 5건" 이 아니라
> **G-1~G-6 중 무엇이 충족됐는가**로 말한다 (2026-09-09 확정).
> 코드 수정 0건 · 배포 0건
> **결론 한 줄**: **지금 코드만 배포하면 "약관 배포"가 아니라
> "미승인 초안에 대한 동의 기록 생성 개시"가 된다.**

---

## 1. 왜 이 문서가 필요한가

`법무 P0 코드 배포` 와 `약관 문서의 정식 게시` 는 같은 사건이 아니다. 지금까지
두 개가 한 덩어리로 이야기돼 왔는데, 코드를 읽어보면 **서로 독립**이고 순서가 있다.

```
코드 배포가 바꾸는 것   동의가 "어떻게" 기록되는가
                        (실패 시 가입 차단 · 농장 권한 검사 · 원장 commit)

코드 배포가 바꾸지 않는 것   사용자가 "무엇에" 동의하는가
                             = 문서 세트와 그 승인 상태
```

---

## 2. ★ 배포를 막는 사실 — 문서가 전부 초안이다

```
api/content/legal/manifest.json — 8건 전부

  MASTER_TERMS            master    v0.1-draft  DRAFT_LAWYER_PENDING  [en, ko]
  GLOBAL_PRIVACY_NOTICE   privacy   v0.1-draft  DRAFT_LAWYER_PENDING  [en, ko]
  ADDENDUM_US             addendum  v0.1-draft  DRAFT_LAWYER_PENDING  [en]
  ADDENDUM_EU             addendum  v0.1-draft  DRAFT_LAWYER_PENDING  [en]
  ADDENDUM_GB             addendum  v0.1-draft  DRAFT_LAWYER_PENDING  [en]
  ADDENDUM_BR             addendum  v0.1-draft  DRAFT_LAWYER_PENDING  [en]
  ADDENDUM_TH             addendum  v0.1-draft  DRAFT_LAWYER_PENDING  [en]
  ADDENDUM_VN             addendum  v0.1-draft  DRAFT_LAWYER_PENDING  [en]

status 분포: DRAFT_LAWYER_PENDING 8 / 그 외 0
```

### 그런데 초안이어도 동의는 진행된다

```
terms_renderer.py:99    any_draft = any(d.status.startswith("DRAFT") …)
                        주석: "하나라도 DRAFT → 실서비스 게시 불가 신호"

consent_service.py:153  any_draft 를 응답에 실어 보낸다
ConsentForm.tsx:71      any_draft → 경고 배너 1개
```

★ **배너뿐이다. 제출을 막지 않는다.** 백엔드 `record_consents` 어디에도
`any_draft` 로 차단하는 분기가 없다. 즉 사용자는 초안 문서에 체크하고 가입할 수 있고,
`consent_ledger.notice_version` 에는 **초안 버전이 그대로 적힌다.**

### 이것이 왜 배포 전 결정 사항인가

배포될 두 변경이 이 경로를 **정확히 되살린다.**

```
557a347  consent 원장을 commit 한다        → 지금까지 0행이던 기록이 실제로 남는다
e064e60  동의 기록 실패 시 가입을 막는다   → 기록 없는 가입이 사라진다
```

둘 다 옳은 수정이다. 다만 이 둘이 켜지는 순간 **"미승인 초안에 대한 동의"가
증빙으로 축적되기 시작한다.** 증빙 관점에서는 기록이 없는 것보다 나쁠 수 있다 —
없는 것은 공백이지만, 있는 것은 회사가 승인하지 않은 문서에 동의를 받았다는
적극적 기록이다.

★ **그러므로 배포 순서는 "코드 먼저, 문서 나중"이 될 수 없다.**

---

## 3. 런타임 게시 게이트는 존재하지 않는다

`test_publication_gate.py` 는 CI 가드이지 런타임 차단이 아니다.

```
tests/integration/test_publication_gate.py
  test_quarantine_has_not_expired                     격리 만료 감시
  test_manifest_documents_are_not_claimed_published   "게시됨" 주장 금지
  test_runtime_code_never_reads_publish_candidate     후보본을 런타임이 읽지 못하게
```

**"게시됐다고 주장하지 못하게" 막을 뿐, "초안에 동의받지 못하게" 막지는 않는다.**
둘은 다른 가드다. 후자는 지금 없다.

---

## 4. 격리는 배포를 열어주지 않는다 — 닫히는 쪽이다

```
KNOWN_PUBLICATION_EXPOSURE.md:10
  expires_at = 2026-09-10T23:59:59+09:00
  "이 시각이 지나면 무조건 CI FAIL. 자동 연장 없음"
```

★ 격리 만료는 **배포 허가 신호가 아니라 강제 마감**이다. 9/10 이 지나면 해소하든
사유를 적고 `expires_at` 을 옮기든 해야 CI 가 돈다. "만료됐으니 이제 배포한다"는
읽기는 틀렸다.

---

## 5. 배포 범위 — 실측 (2026-09-09)

### 5-1. 67커밋 중 런타임에 닿는 것은 15건이다

```
배포본 2e372b1 .. HEAD      67 커밋
  런타임 영향                15
  문서·테스트 전용           52
  ★ 마이그레이션             0        ← prod alembic 실행할 것이 없다
```

★ 이 사실이 위험도를 크게 낮춘다. 초판에 "66커밋이 통째로 실린다"고 적었으나
**대부분이 문서와 테스트**다. 스키마 변경은 없다.

### 5-2. ★ "법무 P0 5건" 의 실체 — 이 5개다

```
90e1284  api/app/policy/consent_matrix.py
         미지원국 기본 목적② OFF (MASTER §10③)
4a64da8  routers/base/auth.py · onboarding.py · services/consent_service.py · eligibility.py
         국가 진입을 서버에서 강제 (consent API 안이 아니라)
e064e60  src/app/onboarding/page.tsx · lib/api/endpoints/consent.ts · messages ×8
         웹 가입을 동의 기록에 대해 fail-closed
f4d9c3f  api/app/services/consent_service.py
         동의 원장 쓰기 전 농장 접근 권한 검사
557a347  api/app/services/consent_service.py
         동의 쓰기를 commit — 요청이 끝나도 남도록
```

**이 목록이 정본이다.** 앞으로 "5건"은 이 5개 sha 를 뜻한다. 흩어진 9종 식별자
(§5-4)는 결함 이름이지 배포 단위가 아니다.

### 5-3. 배포 단위 / 롤백 단위

같이 실리지만 **성격이 다르므로 롤백 판단은 따로 한다.**

```
A  법무          90e1284 · 4a64da8 · e064e60 · f4d9c3f · 557a347
                 ★ G-1~G-3 미충족이면 이 묶음이 곧 위험원이다(§2)

B  KPI·AI        fdd9ca5  웹이 KPI status 를 자체 판정하지 않도록
                 804ef63  LLM 출력 검증(설명만, 판단 금지)
                 ★ 사용자 표시 수치가 바뀐다. 별도 관찰 필요

C  엔진 텍스트   f3e00ce  심각도 라벨에서 이모지 제거 (7개 언어)
                 8f57d1d  로케일 카탈로그 파리티
                 ★ 챗 응답 본문이 바뀐다

D  웹 UI         44ded3f · 6165306   이모지 → 아이콘 · 크기 스케일
                 ★ 표시만. 계약·수치 불변

E  환경·관측     aeca20d · d652af8 · 60c9545   Node 고정 · preflight
                 c3a46cc  클라이언트 앱버전 보고(송출·관측만)
                 ★ 런타임 동작 변화 없음
```

**롤백 지점**: 현재 배포본 `2e372b1`. 마이그레이션이 0건이므로 코드만 되돌리면
되고 스키마 되감기가 없다.

**롤백 정책 — 무엇이 문제인지로 갈린다.**

```
A(법무) 자체에 문제      → 우선 전체 rollback to 2e372b1 검토
                          ★ A 를 남기는 선택지가 아니다

B~E 에 문제 · A 는 정상   → A 유지 + 문제 묶음만 선택 rollback 검토
```

★ 초판은 "A 를 남기고 B~E 를 되돌리는 방향이 충돌이 적다"만 적어서, **A 가
문제일 때도 A 를 남기라는 뜻으로 읽힐 여지가 있었다.** 그 문장은 두 번째 경우에만
해당한다. 파일 충돌 사정(`e064e60` 과 `44ded3f` 가 같은 `messages/*.json` 8개를
건드린다)은 선택 롤백을 어렵게 만드는 요인이지, A 를 보존할 이유가 아니다.

### 5-4. P0 식별자는 여전히 정리되지 않았다

문서에 흩어진 식별자 9종. 두 쌍은 같은 결함의 다른 이름으로 보인다.

```
LEGAL-P0-CONSENT-FARM-AUTHORITY      6회  ↔ LEGAL-P0-CONSENT-AUTHORITY       2회
LEGAL-P0-CONSENT-LEDGER-PERSISTENCE  3회  ↔ LEGAL-P0-CONSENT-LEDGER-NOT-PERSISTED 2회
LEGAL-P0-WEB-CONSENT-FAIL-CLOSED     5회
LEGAL-P0-CONSENT-EVIDENCE            4회      미착수
LEGAL-P0-MANDATORY-CONSENT-LOGIN-GATE 3회     OPEN — NOT REMEDIATED
LEGAL-P0-ORPHAN-ACCOUNT-STATE        1회      = H11
LEGAL-P0-LIVE-PUBLICATION-EXPOSURE   1회      격리 중
LEGAL-P0-IOS-CONSENT                 1회      미착수
```

★ 배포 단위는 §5-2 로 확정됐으므로 이 정리는 **배포를 막지 않는다.** 다만 결함
추적용 이름 통일은 남은 숙제다.

### 5-5. 문서에 적힌 상태 (실측)

```
CODE_COMPLETE / TESTED · PROD_NOT_DEPLOYED
  LEGAL_P0_CONSENT_FARM_AUTHORITY.md
  LEGAL_P0_CONSENT_LEDGER_NOT_PERSISTED.md

OPEN — NOT REMEDIATED
  LEGAL_P0_MANDATORY_CONSENT_LOGIN_GATE.md    ← 기존 사용자 재동의를 강제하는 그 건
  SYNC_AUDIT_ATTRIBUTION_GAP.md
```

★ **`MANDATORY-CONSENT-LOGIN-GATE` 가 미해결이므로, 배포해도 기존 사용자는
재동의를 요구받지 않는다.** 바뀌는 것은 신규 가입 경로뿐이다(H11·H12).

## 6. "약관 배포 완료"의 성립 조건

코드만으로는 성립하지 않는다. 아래가 **한 세트**다.

```
G-1a 문안·구조     대표 승인 — 문안 정정(T-6·T-7·V-11) · 문서 구조(D-16) · 개시 법역(H13)
                    ★ 사실을 사실대로 고치는 것은 법률 판단이 아니다. 변호사 확인 불요
G-1b 법률 확인     변호사 — D-13(controller/processor) · Q-B(US 3종 최소 세트)
                    manifest 8건이 DRAFT_LAWYER_PENDING 을 벗어나는 조건
                    ★ publish_candidate 8종 헤더가 스스로 "변호사 확인 → 대표 승인" 순서를
                      게시 조건으로 적어놓았다. 대표 승인만으로 APPROVED 를 붙이면
                      그 문서가 자기 게시 조건을 어긴 채로 게시된다
G-2  게시 언어      현재: 국가 addendum 전부 en 단일  +  공개 고지 자체도 ko·en 뿐
                    결정: BR·TH·VN 을 **열 것인가**를 H14 에서 확정 (§6-2)
G-3  런타임 차단    초안 상태에서 동의를 받지 않는 게이트
                    → **CODE_COMPLETE / TESTED · PROD_NOT_DEPLOYED** (320baea)
                    eligibility.assert_publication_approved
                    /auth/register · /onboarding/complete 첫 write 이전
                    + record_consents 심층 방어. 철회·농장추가는 제외
G-4  코드 배포      §5-2 법무 5건 + 런타임 10건 (마이그레이션 0)
G-5  기존 사용자    재동의 경로 = MANDATORY-CONSENT-LOGIN-GATE
                    → 현재 OPEN. H11(원장 없는 기존 계정)·H12 와 함께 결정
G-6  적재 확인      consent_ledger 실제 행 · notice_version 이 승인본을 가리키는지
```

### 각 게이트의 성격

```
G-1a HUMAN DECISION REQUIRED — 대표 (2026-09-10 구두 승인, 서명본 대기 · 택일 3건 미확정)
G-1b LEGAL CONFIRMATION REQUIRED — 변호사 (COUNSEL_REQUEST_US_FIRST v2.3)
G-2  HUMAN / LEGAL DECISION REQUIRED
G-3  CODE_COMPLETE / TESTED · PROD_NOT_DEPLOYED  (320baea · 2026-09-09)
     ★ 코드가 닫혔다는 뜻이지 서비스가 막혔다는 뜻이 아니다.
       프로덕션은 아직 초안 동의를 받는다 — 다만 557a347 이 없어 원장 적재는 계속 0행
G-4  READY
G-5  HUMAN DECISION REQUIRED — ★ 이번 배포 완료 판정에서 분리 (§6-1)
G-6  배포 후 검증
```

★ 초판은 "G-1~G-3 이 코드로 못 닫는다"고 적었다. **G-3 은 닫을 수 있다.**
상태 추적에서 혼동되지 않도록 정정한다.

### 6-0. ★ 배포는 두 종류다 — 범위별 조건 (2026-09-10 신설)

기존 문서는 배포를 하나로 봤다. **"거짓 문장을 지우는 배포"와 "신규 가입을 여는 배포"는
필요한 조건이 다르다.** 둘을 묶어두면 변호사 회신이 늦을 때 전자까지 멈춘다.

| 배포 | 무엇을 하나 | 조건 | 닫히는 리스크 |
|---|---|---|---|
| **A. 정정 배포** | 방침의 사실과 다른 문장 삭제·정정 + 격리 마커 해소 + `/legal/terms` 라우트 | **G-1a 만** | R-01(마커 24건 노출) · R-03(거짓 문장 3곳) · **R-14(9-17 격리 만료)** |
| **B. 개시 배포** | G-3 게이트 ON · manifest PUBLISHED · 신규 가입 개방 | **G-1a + G-1b + G-2 + G-4** | R-02 · R-07 (회신 후) |

```
A 가 여는 것    9-17 격리 만료 문제가 사라진다.
                "3차 연장 vs 게시 문서 없이 열어두기" 질문 자체가 없어진다
A 가 안 여는 것 신규 가입. 문서는 여전히 DRAFT — 아무도 새로 가입하지 않는다
```

★ **A 에 포함하지 않는 것**: 격리 24건 중 `OPEN` 10건(보유기간)은 **집행 잡이 선행**이다.
잡 없이 기간을 쓰면 R-05(게시 즉시 거짓 문장)가 그대로 살아난다. A 는 `[V]` 11 · `[ ]` 2 ·
`[COUNSEL]` 1(조항 명시 전환)만 다루고, `OPEN` 10건은 잡과 함께 별도 배포한다.

★ **A 의 선행조건**: 결재 3(:191·:194) · 결재 6(제7조 문안) 은 2026-09-10 실행 완료.
결재 4(V-11)는 정책 (a) 로 정해졌으나 **사실 확인 조건 1·6 이 남아 있다** — 이것이 A 의 유일한 blocker다 (APPROVAL_RECORD §3·§4).
셋 중 하나라도 미확정이면 **A 도 STOP** 이다 — 어느 문안으로 고칠지가 정해지지 않는다.

### 6-2. ★ G-2 는 "en 단일로 열 것인가"가 아니다

두 층이 함께 en 이다.

```
국가 addendum        전부 en 단일           manifest.json
공개 개인정보 고지    ko · en 뿐             public_notice.py (§H14)
```

★ **BR 은 자기 문서와 모순된다.** `ADDENDUM_BR` 이 스스로 **pt-BR 을 정본으로
지정**해두었다. 그 문서를 en 으로 게시하면 문서가 선언한 정본과 실제 게시본이
어긋난다 — 법정 요건 판단 이전에 **자기모순**이다.

따라서 H14 에서 물어야 할 질문의 모양이 다르다.

```
✗  "en 단일로 열 것인가"
✔  "BR · TH · VN 을 열 것인가"
```

★ **US 는 en 이 정본이라 이 문제가 없다.** 그래서 **US 만 먼저 여는 선택지가
실질적으로 존재한다** — G-1 이 US 문서만 승인돼도 그 법역은 열 수 있고,
`assert_publication_approved` 는 법역별로 판정하므로 코드가 이미 그것을 지원한다.

### 6-3. ★★ "US 만 먼저" 의 실제 범위 — US 하나가 아니다 (2026-09-10 실측)

부분 승인이 가능하다는 것은 맞다. `build_document_set` 은 MASTER + PRIVACY +
**그 법역의 addendum 하나**만 담으므로(`terms_renderer.py:92-95`), US 부속조항만
승인해도 US 는 열리고 BR·VN·TH·EU·GB 는 닫힌 채 남는다.

**그런데 부속조항이 없는 국가가 함께 열린다.**

```
시나리오: MASTER_TERMS + GLOBAL_PRIVACY_NOTICE + ADDENDUM_US 만 승인

country  group   문서 세트                            결과
US       US      MASTER + PRIVACY + ADDENDUM_US      열림
MX       OTHER   MASTER + PRIVACY                    ★ 함께 열림
CL       OTHER   MASTER + PRIVACY                    ★ 함께 열림
CO       OTHER   MASTER + PRIVACY                    ★ 함께 열림
JP       OTHER   MASTER + PRIVACY                    ★ 함께 열림
BR       BR      MASTER + PRIVACY + ADDENDUM_BR      451
VN       VN      MASTER + PRIVACY + ADDENDUM_VN      451
TH       TH      MASTER + PRIVACY + ADDENDUM_TH      451
DE       EU      MASTER + PRIVACY + ADDENDUM_EU      451
GB       GB      MASTER + PRIVACY + ADDENDUM_GB      451
```

`_GROUP_ADDENDUM` 에 없는 국가는 전부 `group=OTHER` 이고 문서 세트가 두 건뿐이다.
그 둘이 승인되는 순간 완전한 세트가 된다.

★ **설계상 틀린 동작이 아니다.** OTHER 에는 적용할 국가별 부속조항이 애초에
없으므로, 마스터와 방침이 곧 그 법역의 전부다. 게이트는 정확히 동작하고 있다.

★ **다만 결재 문장이 달라진다.**

```
✗  "US 부속조항 3종을 승인한다"          → 실제 효과를 과소 표현
✔  "US + 국가별 부속조항이 없는 모든 국가를 연다"
```

여기에 걸리는 사실이 하나 더 있다 — `CLAUDE.md` 는 **스페인어권(멕시코·콜롬비아
등)·러시아어권 CIS 는 리서치·부속조항 미비**라고 적어두었다. 그 국가들이 바로
`OTHER` 다. 즉 이 승인은 **리서치가 안 된 시장을 함께 여는 결정**이 된다.

★ 선택지는 셋이다. 어느 쪽도 개발이 정하지 않는다.

```
(1) 그대로 연다        OTHER 에는 마스터·방침이 완전한 세트라는 판단을 수용
(2) OTHER 를 따로 막는다  jurisdiction gate(signup_blocked)로 국가를 지정해 차단
                       ★ 코드 변경 없음 — 기존 국가 게이트가 이미 그 일을 한다
(3) US 만 정확히 연다   OTHER 전용 addendum 을 신설해 DRAFT 로 둔다
                       ★ 문서 신설이 필요하다. 오늘 안에는 불가
```

이 동작은 `test_publication_consent_gate.py` 의
`test_us_first_also_opens_every_country_without_an_addendum` 가 붙잡고 있다.
전제가 바뀌면 그 테스트가 먼저 깨진다.

### 6-1. ★ G-5 는 이번 배포의 완료 조건이 아니다

```
이번 배포가 닫는 것
  "신규 가입에 대해 승인된 약관 동의를 정상적으로 증빙하기 시작했다"

이번 배포가 닫지 않는 것
  기존 사용자의 재동의
  → LEGAL-P0-MANDATORY-CONSENT-LOGIN-GATE 로 별도 추적 (H11 · H12)
```

둘을 묶으면 이번 배포가 영영 끝나지 않는다. 분리해서 각자 판정한다.

---

## 7. 확정된 실행 순서 (2026-09-09)

```
1  H13   게시 문서 승인 여부 결정                        대표+법무
2  H14   게시 언어 법정 요건 결정                        대표+법무
3  G-3   DRAFT·미승인 문서에는 동의를 받지 못하게 fail-closed
4  §5-2  배포 대상 sha 목록 확정                          ← 완료
5  §5-3  배포 단위·롤백 단위 확정                          ← 완료
6  코드 배포
7  smoke — 신규 가입 동의 경로
8  ledger 검증 — document · version · status
9  기존 사용자 재동의                                    H11 · H12 별도
```

★ **9/10 의 정상 시나리오는 "격리 만료 → 바로 배포"가 아니다.**
`G-1`·`G-2` 를 재확인하고 **미충족이면 멈추는 것**이다.

### ★ G-3 에는 판단이 필요하다 — 지금 넣으면 신규 가입이 전면 중단된다

`any_draft` 로 fail-closed 하는 것은 코드로 닫을 수 있다. 다만 **지금 문서 8건이
전부 DRAFT 이므로, 그 게이트를 켜는 즉시 아무도 가입할 수 없다.**

두 순서가 가능하고 성격이 다르다.

```
(가) G-1 먼저 → G-3 나중
     문서가 승인된 뒤 게이트를 넣는다. 서비스 중단 없음.
     단 승인~게이트 사이 구간은 여전히 무방비다.

(나) G-3 먼저 → G-1 나중
     지금 게이트를 넣는다. 신규 가입이 승인 시점까지 멈춘다.
     대신 초안 동의 기록이 단 한 건도 생기지 않는다.
```

### ★ 2026-09-11 추가 — 배포 전 재동의 모집단을 센다

(나) 는 결정됐고 배포만 남았다 — **이틀째**. 그동안 프로덕션은 결정이 금지한 일을 하고
있다. `HUMAN_INPUT_QUEUE` B-6 집계를 **배포 직전(의사결정용)과 직후(확정 모집단)** 두 번
뜬다. 게이트가 동결선이다. 9/09 전후로 나눠 센다 — 앞은 유산, 뒤는 집행 지연분.
프로덕션 실측(9/11): US·BR·DE·CL 열림 · KR·CN 차단 · 8건 전부 DRAFT · any_draft=True.

### ★ 결정: (나) — 2026-09-09 대표 판단

```
승인 안 된 문서에 동의받는 것보다 신규 가입을 잠시 막는 쪽을 선택한다.
★ 이것은 법률 판단이 아니라 제품·운영 리스크 판단이다.
```

근거.

```
비용   신규 가입 월 2~3건 (2026-08 월간보고) → 중단 손실이 제한적이다
위험   (가)는 "승인은 됐는데 런타임 게이트는 아직 없는 시간창"을 의도적으로 만든다
       짧더라도 의도해서 만드는 공백이다
```

그리고 지금 발견된 가장 위험한 상태가 이것이다.

```
DRAFT  +  consent 가능  +  ledger commit  +  registration fail-closed
```

`557a347`·`e064e60` 자체는 옳은 수정인데, **게시 정본이 잘못된 상태에서 증거
능력만 강화한다.** 그래서 게이트가 먼저다.

### 확정 실행안

```
오늘 / 배포 전                                            ← ★ 1~4 완료 (320baea)
  1  G-3 구현 — DRAFT·미승인 문서에는 동의 자체가 실패        ✔
  2  negative test — DRAFT 상태에서 실제로 실패하는가          ✔
  3  positive test — 승인본에서는 통과하는가                   ✔
  4  백엔드가 authoritative 인지 확인                          ✔
     ★ 구현 중 확정된 것: record_consents 만 막으면 계정이 먼저 생겨
       고아 계정이 쌓인다(H11). 그래서 가입 진입점 두 곳에서 먼저 막는다.

9/10
  5  H13 확인
  6  H14 확인
  7  둘 중 하나라도 미결정  →  배포 STOP
  8  둘 다 확정            →  manifest / publication set 갱신
  9  ★ G-3 게이트가 실제로 **열리는지** 확인 — **두 법역으로** 확인한다
     승인 법역 1건 성공(예: US 201) + 미승인 법역 1건 차단(예: BR 451)
     ★ 열림만 보면 게이트가 통째로 꺼진 것과 구분되지 않는다
     ★ §6-3 — "US 만" 승인 시 MX 등 OTHER 도 열린다. 차단 확인은
       OTHER 가 아니라 **addendum 이 있는 법역**(BR·VN·TH·EU·GB)으로 해야 한다
     게이트가 닫힌 채 배포되면 서비스가 전면 중단되고, 그것은 코드가
     의도대로 동작한 결과라 **롤백 판단이 늦어진다.** 장애처럼 보이지 않는다.
     스테이징이 없으므로 배포 직후 첫 확인 항목으로도 반복한다.
  10 full test
  11 deploy
  12 신규 가입 smoke — ★ 배포 직후 첫 항목. 9 와 같은 확인을 프로덕션에서 반복
  13 consent_ledger 의 document / version 확인
  14 가입 재개
```

---

## 8. 이 문서가 주장하지 않는 것

```
✗ "배포하면 안 된다"
    코드 수정은 옳고 배포 대기 상태다. 순서 문제를 지적할 뿐이다.

✗ G-2 의 현지어 게시가 법적으로 필요한지에 대한 판단
    확인된 사실은 "addendum 이 en 단일" 까지다. 필요 범위는 H14.

✗ 문서 승인 여부에 대한 판단
    manifest 의 status 값을 읽었을 뿐이다. 변호사 검토 진행 상황은 모른다.
```

---

## 9. 관련

```
api/content/legal/manifest.json                   문서 8건 status
api/app/services/terms_renderer.py:99             any_draft 산출
src/components/consent/ConsentForm.tsx:71         배너만 — 차단 없음
api/tests/integration/test_publication_gate.py    CI 가드(런타임 아님)
docs/legal/KNOWN_PUBLICATION_EXPOSURE.md:10       격리 만료 2026-09-10
docs/legal/HUMAN_INPUT_QUEUE.md                   H11·H12·H13·H14·H15
docs/legal/LEGAL_P0_MANDATORY_CONSENT_LOGIN_GATE.md   G-5 미해결
```
