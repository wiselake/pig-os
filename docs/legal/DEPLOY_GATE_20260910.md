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

★ A 만 떼어 되돌리는 것은 **깨끗하지 않다.** `e064e60` 이 `messages/*.json` 8개를
건드리고 `44ded3f`(D)도 같은 파일을 건드린다. 부분 롤백이 필요하면 A 를 남기고
B~E 를 되돌리는 방향이 충돌이 적다.

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
G-1  문서 승인      manifest 8건이 DRAFT_LAWYER_PENDING 을 벗어난다
                    → H13 CURRENT_PUBLICATION_SET 확정이 선행
G-2  게시 언어      법정 요건 충족 (BR pt-BR · TH th · VN vi)
                    → 현재 addendum 은 전부 en 단일. H14
G-3  런타임 차단    초안 상태에서 동의를 받지 않는 게이트
                    → 현재 없음. 배너뿐
G-4  코드 배포      §5-2 법무 5건 + 런타임 10건 (마이그레이션 0)
G-5  기존 사용자    재동의 경로 = MANDATORY-CONSENT-LOGIN-GATE
                    → 현재 OPEN. H11(원장 없는 기존 계정)·H12 와 함께 결정
G-6  적재 확인      consent_ledger 실제 행 · notice_version 이 승인본을 가리키는지
```

★ **G-1~G-3 이 사람 결정이고 코드로 못 닫는다.** G-4 만 오늘 준비돼 있다.

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

★ **어느 쪽이 옳은지는 개발이 정할 문제가 아니다.** (나)는 서비스 중단을
감수하는 결정이고, (가)는 그 사이 유입을 감수하는 결정이다. 실고객 신규 가입이
월 2~3건 수준(2026-08 월간보고)이라는 사실이 판단 재료가 된다.

**미결정 상태에서는 배포하지 않는다** — 게이트 없이 `557a347`+`e064e60` 만 나가는
것이 §2 에서 지적한 최악의 조합이다.

---

## 8. 이 문서가 주장하지 않는 것

```
✗ "배포하면 안 된다"
    코드 수정은 옳고 배포 대기 상태다. 순서 문제를 지적할 뿐이다.

✗ G-3 를 어느 순서로 넣을지에 대한 판단
    §7 의 (가)/(나) 는 선택지 제시이지 권고가 아니다.
    서비스 중단 여부는 사업 결정이다.

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
