# 모바일 개발 백로그 — Android · iOS (2026-09-10)

> **성격**: **새 조사 없음.** 전부 `PLATFORM_PARITY.md` 와 법무 문서에 이미 측정돼
> 있던 항목이다. 이 문서가 하는 일은 **순서를 붙이는 것** 하나다.
> **왜 필요한가**: 미결 12건이 문서 여러 절에 흩어져 있고 **우선순위가 없었다.**
> 무엇부터 할지 물으면 매번 전 문서를 다시 읽어야 했다.

---

## 0. 읽는 법

```
근거    전부 PLATFORM_PARITY.md 의 절 번호로 건다. 여기서 사실을 새로 만들지 않는다
순서    ① 배포를 막는 것 → ② 사용자에게 틀린 값을 보이는 것 →
        ③ 심사·법무 → ④ 계약 선행 → ⑤ 관측
저장소  wiselake/pigos-android · wiselake/pigos-ios — 둘 다 PigOS 저장소 밖이다
        ★ 각 항목은 별도 저장소 작업이므로 착수 전 승인이 필요하다
```

---

## 1. ★ P0 — 배포를 막는다

### M-1. Android 가 451 사유를 버린다 — `PUBLICATION_GATE_451`

```
근거    PLATFORM_PARITY §9-7-1
현상    OnboardingRepository.kt:32  runCatching { onboardingApi.complete(...) }
        Response<T> 가 아니라 DTO 직접 수신 → Retrofit 이 비 2xx 에 throw
        errorBody 를 읽는 코드 저장소 전체 0건
결과    서버가 보낸 detail 이 어디에도 도달하지 않는다.
        사용자는 "HTTP 451" 만 본다
```

★ **이 게이트가 만든 문제가 아니다.** 기존 `SIGNUP_BLOCKED:{reason}` 도 같은
이유로 이미 사유가 사라지고 있었다. G-3 가 **드러냈을 뿐**이고, 고치면 둘 다 낫는다.

★ **서버 로그에는 451 정상 응답으로 보인다.** 장애로 인지되지 않는 침묵 실패다.

```
수정    Response<T> 로 받아 errorBody 의 detail 을 표면화
범위    작다. 다만 별도 저장소 — 승인 필요
```

### M-2. iOS 안내 문구 — 배포를 막지는 않는다

```
근거    PLATFORM_PARITY §9-7-1
현상    APIError.swift:28  451 case 없음 → default: .http(status:detail:)
        "Error occurred (451: PUBLICATION_NOT_APPROVED)."
판정    크래시·묵살 없음. 사유가 보인다 → 배포 가능
후속    웹은 f0934c0 로 8 로케일 안내를 붙였으나 iOS 는 그 문구를 모른다
```

---

## 2. P0 — 사용자에게 틀린 값을 보인다

### M-3. 벤치마크를 판정으로 변환 — `MOBILE_LOCAL_SEVERITY`

```
근거    PLATFORM_PARITY §3-3  DECISION_INTEGRITY_RISK
Android DashboardScreen.kt:238-243  meetsAvg = myValue >= b.avg → Success/Warning
iOS     DashboardScreen.swift:241-246  alert 없음 → AppColor.success
```

★ **iOS 쪽이 fail-OPEN 이다.** 판정이 없는 것을 **초록(정상)** 으로 그린다.
서버가 "판정 불가"를 보내도 사용자는 "정상"으로 읽는다.

★ 그리고 이것은 `ADR-KPI-00` §2.4 가 금지한 바로 그것이다 — **벤치마크는 설명용
비교이고 심각도는 별도로 승인된 운영 정책**이다. 모바일이 그 경계를 지우고 있다.

### M-4. `kpi_status` 미소비

```
근거    PLATFORM_PARITY §3-2   Android·iOS 둘 다 소비 0건
의미    서버가 판정을 내려보내는데 클라이언트가 자기 기준으로 다시 판정한다
관련    웹은 fdd9ca5 로 이미 자체 판정을 중단했다 — 모바일만 남았다
```

### M-5. `/kpi/presentation` 미소비

```
근거    PLATFORM_PARITY §3-1 · §9-3 (G4 완료 정의)
Android DashboardScreen.kt:100-101  KpiCard("PSY") / ("NPD") 하드코딩
        KpiDto.kt:31-33  @SerializedName 고정
iOS     DashboardScreen.swift:162-165 하드코딩
의미    ADR-KPI-00 의 "국가 추가 = INSERT 뿐"(I-2)이 모바일에서 깨진다
        국가를 추가해도 모바일 화면은 안 바뀐다
```

★ M-3·M-4·M-5 는 **한 덩어리로 보는 게 맞다.** 셋 다 "서버가 정한 것을
클라이언트가 다시 정한다"는 같은 결함의 세 얼굴이다.

---

## 3. 심사 · 법무

### M-6. iOS 계정 삭제 화면 — App Store 5.1.1(v)

```
근거    PLATFORM_PARITY §2  BLOCKED
현상    AuthService / DTO 는 있으나 View 미발견
영향    App Store 심사 차단 사유
```

### M-7. `LEGAL-P0-IOS-CONSENT` — consent 호출 0건인데 가입된다

```
근거    LEGAL_P0_MANDATORY_CONSENT_LOGIN_GATE.md:166
        "iOS 는 이 게이트가 켜지면 즉시 잠긴다"
현상    iOS 는 /auth/register → /onboarding/farm 만 호출한다.
        동의 기록 호출이 없다
```

★ **G-3 배포 후 iOS 는 register 에서 막힌다**(M-1·M-2 실측). 즉 이 항목은
"동의를 안 받고 가입되던 문제"가 **게이트로 우연히 닫히는** 상태가 된다.
근본 수정(동의 수집 경로 신설)은 여전히 남는다.

### M-8. Android 구버전 대응 — `FORCE_UPDATE / LEGACY_CONTROL`

```
근거    PLATFORM_PARITY §3-7   Android·iOS 둘 다 0건
현상    forceUpdate / minVersion / 426 처리 없음
의미    API 계약이 바뀌어도 구버전을 멈출 수단이 없다
        ★ CLAUDE.md §5 가 "모바일은 배포 주기가 길어 구버전이 오래 남는다"고
          적어둔 바로 그 위험의 대응 수단이 부재
```

---

## 4. 선행조건이 붙은 것

### M-9. `APP_VERSION_REQUEST_REPORTING`

```
근거    PLATFORM_PARITY §3-6
Android DeviceRepository.kt:26  기기등록 시 1회만. NetworkModule 인터셉터는 auth·logging 둘뿐
iOS     PushNotificationService.swift:47  1회만. Endpoint 헤더는 Authorization·Content-Type·Accept
선행    서버는 c3a46cc 로 수신·관측 준비 완료 (송출·관측만, 판정 없음)
의미    M-8 을 하려면 어느 버전이 살아 있는지 먼저 보여야 한다
```

★ **M-9 → M-8 순서다.** 버전 분포를 모르는 채 강제 업데이트를 켜면 정상
클라이언트를 차단한다(`client_version.py:10` 이 같은 경고를 적어둔다).

### M-10. `PRODUCT_INSTRUMENTATION`

```
근거    PLATFORM_PARITY §3-8   Android·iOS 둘 다 제품 계측 0건
의미    모바일에서 무슨 일이 일어나는지 관측 수단이 없다
        M-1 같은 침묵 실패를 사후에 발견할 방법도 여기에 걸린다
```

---

## 5. 착수 순서 제안

```
지금        M-1   Android 451 — ★ 배포 선행조건
배포 후     M-2   iOS 451 안내 문구
            M-3   fail-OPEN 제거          ★ 틀린 값을 보이는 것 중 가장 위험
            M-4·M-5  서버 판정 소비로 전환 (M-3 과 한 덩어리)
심사 일정   M-6   iOS 계정 삭제 화면
관측 먼저   M-9 → M-8   버전 보고 → 강제 업데이트
            M-10  계측
법무 트랙   M-7   iOS 동의 수집 경로 — LEGAL-P0-CONSENT-EVIDENCE 확정 후
```

★ **M-1 만 이번 배포를 막는다.** 나머지는 배포 후 순차 진행 가능하다.

---

## 6. 이 문서가 하지 않는 것

```
✗ 새 조사·새 측정
    전부 PLATFORM_PARITY 와 법무 문서의 기존 실측을 인용했다.
    2026-09-10 에 추가된 것은 §9-7-1(모바일 451) 하나이고 그것도 기록 완료다.

✗ 착수 승인
    모든 항목이 별도 저장소(pigos-android · pigos-ios) 작업이다.

✗ 공수 추정
    두 저장소의 구조를 구현 관점으로 읽지 않았다. 읽은 것은 해당 결함 지점뿐이다.
```

---

## 7. 관련

```
docs/PLATFORM_PARITY.md                §2 · §3-1~3-8 · §9-3 · §9-7   전 항목의 근거
docs/legal/DEPLOY_GATE_20260910.md     G-3 배포 게이트
docs/legal/LEGAL_P0_MANDATORY_CONSENT_LOGIN_GATE.md   M-7
docs/adr/ADR-KPI-00-one-engine-many-policies.md       M-3·M-5 가 깨는 불변식
```
