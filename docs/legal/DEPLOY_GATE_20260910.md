# 2026-09-10 법무 P0 배포 게이트 — 배포 전 확정 사항

> **작성**: 2026-09-09 · machine `bjh` · 실측 기반
> **성격**: 배포 판단용 사실 정리. **코드 수정 0건 · 배포 0건**
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

## 5. 배포 범위 — P0 5건이 아니다

### 5-1. 미배포 커밋은 66개다

```
배포본 2e372b1 .. HEAD   66 커밋
그중 법무 계열            약 16 커밋
나머지                    KPI·환경·i18n·UI 아이콘·가드 등
```

법무 P0 만 올라가는 것이 아니다. **KPI trend 억제, 심각도 라벨 변경, 아이콘 전면
교체, Node 환경 변경이 같은 배포에 실린다.** 롤백 단위를 미리 정해야 한다.

### 5-2. ★ P0 정본 목록이 없다

문서에 흩어진 식별자가 **9종**이고, 이름이 서로 다르게 쓰인 것도 있다.

```
LEGAL-P0-CONSENT-FARM-AUTHORITY      6회   ← LEGAL-P0-CONSENT-AUTHORITY(2회) 와 동일?
LEGAL-P0-WEB-CONSENT-FAIL-CLOSED     5회
LEGAL-P0-CONSENT-EVIDENCE            4회
LEGAL-P0-MANDATORY-CONSENT-LOGIN-GATE 3회
LEGAL-P0-CONSENT-LEDGER-PERSISTENCE  3회   ← LEGAL-P0-CONSENT-LEDGER-NOT-PERSISTED(2회) 와 동일?
LEGAL-P0-ORPHAN-ACCOUNT-STATE        1회
LEGAL-P0-LIVE-PUBLICATION-EXPOSURE   1회
LEGAL-P0-IOS-CONSENT                 1회
```

**"5건"이 어느 5건인지 고정된 곳이 없다.** 배포 후 "5건 배포 완료"를 검증할 수 없다.

### 5-3. 문서에 적힌 상태 (실측)

```
CODE_COMPLETE / TESTED · PROD_NOT_DEPLOYED
  LEGAL_P0_CONSENT_FARM_AUTHORITY.md
  LEGAL_P0_CONSENT_LEDGER_NOT_PERSISTED.md

OPEN — NOT REMEDIATED
  LEGAL_P0_MANDATORY_CONSENT_LOGIN_GATE.md    ← 기존 사용자 재동의를 강제하는 그 건
  SYNC_AUDIT_ATTRIBUTION_GAP.md

전용 문서 없음 (커밋으로만 존재)
  LEGAL-P0-WEB-CONSENT-FAIL-CLOSED   e064e60
  국가 진입 서버 강제                4a64da8
  미지원국 목적② OFF (MASTER §10③)  90e1284
```

★ **`MANDATORY-CONSENT-LOGIN-GATE` 가 미해결이라는 점이 중요하다.** 이 건이 열려
있는 한, 배포해도 **기존 사용자는 재동의를 요구받지 않는다.** 바뀌는 것은 신규
가입 경로뿐이다.

---

## 6. "약관 배포 완료"의 성립 조건

코드만으로는 성립하지 않는다. 아래가 **한 세트**다.

```
G-1  문서 승인      manifest 8건이 DRAFT_LAWYER_PENDING 을 벗어난다
                    → H13 CURRENT_PUBLICATION_SET 확정이 선행
G-2  게시 언어      법정 요건 충족 (BR pt-BR · TH th · VN vi)
                    → 현재 addendum 은 전부 en 단일. H14
G-3  런타임 차단    초안 상태에서 동의를 받지 않는 게이트
                    → 현재 없음. 배너뿐
G-4  코드 배포      P0 5건 + 나머지 61커밋
G-5  기존 사용자    재동의 경로 = MANDATORY-CONSENT-LOGIN-GATE
                    → 현재 OPEN. H11(원장 없는 기존 계정)·H12 와 함께 결정
G-6  적재 확인      consent_ledger 실제 행 · notice_version 이 승인본을 가리키는지
```

★ **G-1~G-3 이 사람 결정이고 코드로 못 닫는다.** G-4 만 오늘 준비돼 있다.

---

## 7. 9/10 배포일에 확인할 것

대표 GO 이후 순서. **각 단계는 앞 단계가 참일 때만 의미가 있다.**

```
1  격리 상태 확인          expires_at 경과 여부 · 해소/연장 결정
2  G-1 문서 승인 상태      manifest status 재확인 — 여전히 DRAFT 면 3~7 을 하면 안 된다
3  롤백 지점 고정          현재 배포본 2e372b1 을 기록. 66커밋 단위 롤백 가능 여부 확인
4  원격 반영              push (아직 0건)
5  프로덕션 배포           prod alembic 금지 — 스키마 수동 확인
6  smoke — 신규 가입       동의 실패 시 계정이 생기지 않는가 (e064e60)
7  smoke — 원장 적재       consent_ledger 행 생성 · notice_version 값 확인 (557a347)
8  smoke — 농장 권한       타 농장 farm_id 로 동의 기록 시 403 (f4d9c3f)
9  smoke — 국가 차단       KR·CN 가입 차단 유지 (4a64da8)
10 관찰                   9/2 감사에서 확인된 "동의 기록 없는 신규 가입 2건" 재발 여부
```

★ **2번에서 멈추는 것이 정상 시나리오다.** 문서가 승인되지 않은 상태에서 6~8 을
통과시키면, 그 smoke test 자체가 초안 동의 기록을 만든다.

---

## 8. 이 문서가 주장하지 않는 것

```
✗ "배포하면 안 된다"
    코드 수정은 옳고 배포 대기 상태다. 순서 문제를 지적할 뿐이다.

✗ "P0 5건이 틀렸다"
    5건이 무엇인지 고정된 목록이 없다는 것까지가 확인된 사실이다.

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
