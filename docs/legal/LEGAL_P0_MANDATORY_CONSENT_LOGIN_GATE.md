# LEGAL-P0-MANDATORY-CONSENT-LOGIN-GATE

> **상태**: `OPEN — NOT REMEDIATED`
> **발견**: 2026-09-03, LEGAL-P0-WEB-CONSENT-FAIL-CLOSED 구현 중 부수 판독
> **성격**: 코드 수정 없이 사실만 기록. 이 문서는 문제를 **해결하지 않는다.**

---

## 한 줄

가입 경로를 아무리 잠가도, **로그인 경로에는 동의 판정이 한 번도 없다.**
동의를 남기지 못한 계정은 다음 로그인에서 그냥 들어온다.

---

## 왜 별건인가

`LEGAL-P0-WEB-CONSENT-FAIL-CLOSED`(commit `e064e60`)는 **가입 순간**을 잠갔다.

```
/onboarding/complete 성공 → record 성공해야 → setAuth · cookie · 대시보드
```

그 계약은 유효하다. 그러나 그 앞 단계에서 이미 만들어진 계정에는 소급되지 않는다.

```
record 실패 → 화면상 가입 실패 → 그러나 서버에는 org·user·farm 이 이미 있다
           → 사용자가 /login 으로 이동 → 아이디·비번은 맞는다 → 로그인 성공
           → 동의 원장은 여전히 0행
```

즉 fail-closed 는 **한 번의 우회 시도만 막고**, 재시도 경로는 열려 있다.
가입 게이트와 로그인 게이트는 서로를 대체하지 못한다.

---

## 실측 (2026-09-03, 코드 판독)

### 1) 서버 — `/auth/login` 에 판정 없음

```
api/app/routers/base/auth.py:26   register()   eligibility.assert_country_entry_allowed(...)   ← 있음
api/app/routers/base/auth.py:40   login()      (없음)
```

`register` 에만 국가 진입 판정이 들어갔다(LEGAL-P0-CONSENT-AUTHORITY). `login` 은
자격증명만 본다. 동의 원장 조회도, 국가 게이트도 호출하지 않는다.

★ 국가 게이트조차 없다는 점에 주의. `signup_blocked` 국가로 이미 만들어진 계정은
**로그인으로 계속 접근 가능**하다. 프로덕션 KR 농장 5건이 여기에 해당한다.

### 2) 웹 — 로그인 화면에 판정 없음

```
src/app/(auth)/login/page.tsx:199   setAuth(...)
src/app/(auth)/login/page.tsx:214   document.cookie = "pigos_session=1; max-age=7d"
src/app/(auth)/login/page.tsx:219   router.replace(dest)
```

세 줄 사이에 동의 확인이 없다. `consentApi` import 자체가 없다.

### 3) 미들웨어 — 쿠키 존재만 본다

```
src/middleware.ts:61   const hasSession = request.cookies.has("pigos_session")
```

쿠키가 있으면 통과. 그 쿠키가 동의를 거쳐 발급됐는지는 묻지 않는다.

### 4) AmendmentBanner 는 게이트가 아니다

```
src/components/consent/AmendmentBanner.tsx:18   const [dismissed, setDismissed] = useState(false)
src/components/consent/AmendmentBanner.tsx:48   if (dismissed || !outdated) return null
```

개정 고지 배너는 있으나 **닫을 수 있다.** 닫으면 서비스가 정상 동작한다.
고지이지 강제가 아니다. 그리고 이것은 "동의가 낡았을 때"를 위한 것이지
"동의가 아예 없을 때"를 위한 것이 아니다.

---

## 영향 범위

```
신규 가입 실패 후 재로그인      원장 없이 서비스 사용
차단 국가 기존 계정             signup_blocked 무력화 (로그인은 안 막힘)
iOS main (동의 호출 0건)        가입·로그인 양쪽 다 원장 없이 사용
Android 구버전                  배포 주기가 길어 오래 남는다
동의 철회 후                    철회했는데 계속 로그인된다 (미확인 — 아래 참조)
```

★ **마지막 항목은 아직 검증하지 않았다.** `/consent/withdraw` 이후 세션이 어떻게
되는지 확인하지 않았으므로 사실로 적지 않는다. 확인 전까지 `UNVERIFIED`.

---

## 고치려면 결정이 필요하다 — 그래서 지금 고치지 않았다

이 P0 는 개발이 단독으로 닫을 수 없다. 최소 세 가지가 미결이다.

| # | 결정할 것 | 왜 개발이 못 정하나 |
|---|---|---|
| 1 | **기존 계정 처리** | 프로덕션에 원장 없는 계정이 이미 있다. 전부 차단할지, 다음 로그인에서 동의를 받을지, 유예를 둘지는 사업·법무 판단이다 |
| 2 | **차단 국가 기존 계정** | KR 5건·CN 계정을 로그인까지 막으면 레퍼런스 사용이 끊긴다. 막을지 말지는 대표 결정 |
| 3 | **무엇을 "동의 있음"으로 볼 것인가** | 현재 원장은 0행이다. 어떤 문서·버전에 대한 동의를 요구할지는 `CURRENT_PUBLICATION_SET` 결정에 종속된다 |

`3` 이 특히 중요하다. 지금 로그인 게이트를 넣으면 **아무도 로그인할 수 없다** —
요구할 수 있는 승인 문서가 존재하지 않기 때문이다. 게이트를 켜는 것 자체가
`CURRENT_PUBLICATION_SET` 결정 이후에만 가능하다.

---

## 구현 시 지켜야 할 것 (결정 이후)

```
서버가 판정한다        클라이언트 체크만 넣으면 iOS·구버전 Android 가 그대로 통과한다.
                       /auth/login 응답에 동의 상태를 실어 보내는 것으로는 부족하다 —
                       그 값을 무시하는 클라이언트가 실재한다(iOS main)

부분 차단이어야 한다   동의 화면 자체는 접근 가능해야 한다. 전면 401 로 막으면
                       동의를 하러 들어올 수도 없다(가입 때와 같은 순환)

철회와 구분한다        "동의한 적 없음" 과 "동의했다가 철회함" 은 다른 상태다.
                       후자를 전자와 같이 취급하면 철회가 계정 삭제가 된다

증거를 남긴다          게이트가 통과시킨 근거(문서 버전·해시·시각)를 기록하지 않으면
                       나중에 "언제부터 강제됐나" 를 답할 수 없다
```

---

## 선행/후행

```
선행   CURRENT_PUBLICATION_SET 대표 결정        요구할 문서가 없으면 게이트를 켤 수 없다
선행   LEGAL-P0-CONSENT-EVIDENCE               무엇을 원장에 남길지 확정
선행   기존 계정 처리 방침 (대표·법무)

후행   LEGAL-P0-IOS-CONSENT                     iOS 는 이 게이트가 켜지면 즉시 잠긴다
후행   Android 구버전 대응                       배포 주기상 강제 업데이트 검토 필요
```

---

## 관련

```
e064e60                                          가입 경로 fail-closed (이 문서의 대응물)
4a64da8                                          서버 국가 진입 판정 (register 에만)
docs/legal/PRODUCTION_CONSENT_LEDGER_AUDIT_20260902.md   원장 0행 실측
api/app/routers/base/auth.py:40                  판정이 없는 login
src/app/(auth)/login/page.tsx:199-219            판정이 없는 웹 로그인
src/middleware.ts:61                             쿠키 존재만 보는 라우팅 가드
```
