# iOS 로케일 갭 — 현황·영향 범위 (2026-09-18)

> 범위: **문서화까지.** 번역 추가는 STOP 대상(주말 런 G3). 값은 전부 pigos-ios `e750daa` 실측.
> 429 트랙에서 드러났지만 429 와 무관하게 앱 1.0 결정에서 온 갭이다.

## 1. 현황 (실측)

| 항목 | 값 | 근거 |
|---|---|---|
| 선언 언어 | `CFBundleLocalizations: [en]` | `project.yml:52-53` — 주석 "1.0 은 영어 단독 … 다국어는 안드로이드 555개 문자열 이식 후 1.1" |
| 결정 기록 | 1.0 영어 단독 ✅ 반영 완료 · 후속 = 1.1 | `docs/RELEASE_APPSTORE.md` §4-1 |
| 문자열 카탈로그 | `PigOS/Resources/Localizable.xcstrings` · `sourceLanguage=en` · 키 265 | 파일 실측 |
| 실제 번역 | **0 언어** — `localizations` 에 `en` 항목이 있는 키 8개(전부 포맷 문자열), 나머지 257 키는 localization 없음(원문=키) | JSON 파싱 |
| 문자열 사용 방식 | `Text("…")` 199곳(LocalizedStringKey 암묵) · `String(localized:)` 2곳(429 문구) · `NSLocalizedString` 0 | swift grep |
| 런타임 언어 결정 | UI = 번들 언어(en 고정). AI 챗 응답 언어 = `Bundle.main.preferredLocalizations`(→ en). 음성인식 = `Locale.current`(폴백 en-US) | `ChatRepository.swift:9-14` · `SpeechRecognizer.swift:18` |
| 농장 설정 언어 | 서버 농장 설정(`PATCH /farms/{id}` language) — UI 언어와 별개, 실제 동작 | RELEASE_APPSTORE §4-1 |

비교: Web 8 locale(`src/messages/*.json`, `i18n.test.ts` 파리티 강제) · Android 8 locale(`values` + es/ko/pt/ru/th/vi/zh, 639 문자열).

## 2. 영향 범위

| 영역 | 영향 | 비고 |
|---|---|---|
| 타겟 시장 5개 × 8언어 (CLAUDE.md, LANDING_SYNC §2·§3 "5 global markets · 8 languages") | iOS 사용자는 UI 를 영어로만 본다 | LANDING_SYNC §1 실측: "iOS = 개발 중(미출시). coming soon 으로만" · §2 8언어 근거 = `src/messages`(웹). **iOS 출시 시점에 §1·§2 를 함께 고쳐야 한다** — 지금은 iOS 가 노출 대상이 아니라 위조 아님 |
| 법무 고지·동의 화면 | 동의 문안은 서버가 국가/언어별로 내려주는 구조(`/consent/*`) 라 iOS 도 서버 언어를 받는다. **UI 라벨(버튼·안내)만 영어** | 서버 문안 언어 ≠ 앱 UI 언어 혼재 가능 |
| 429 트랙 | `rate_limited` 2문장은 `String(localized:)` 로 넣어 카탈로그에 잡히지만 en 만 존재 | 파리티 매트릭스 locale 행 "iOS en 단일" |
| 파리티 판정 | `THREE_CLIENT_PARITY_VERIFIED=YES` 는 이 갭을 **별도 항목으로 분리**한 조건부 판정 | PLATFORM_PARITY §9-9-1 |
| App Store 심사 | 1.0 은 en 단독 선언과 실제가 일치 — 심사 리스크 없음 | 선언과 실제가 어긋나는 쪽이 리스크 |

## 3. 갭을 메우는 데 필요한 것 (착수 아님 — 견적만)

| 단계 | 내용 | 규모(실측 기반) |
|---|---|---|
| ① 키 정규화 | `Text("영문 문장")` 199곳이 키=원문 구조. 그대로 두고 xcstrings 에 번역만 추가 가능 (Xcode 가 빌드 시 추출) | 코드 변경 0~소 |
| ② 번역 소스 | Android `values-*/strings.xml` 7언어 639 문자열 ↔ iOS 265 키. 1:1 아님 — 매핑표 필요 | 매핑 작업 |
| ③ 선언 | `CFBundleLocalizations` 에 7언어 추가 | 1줄 |
| ④ 검증 | `Localizable.xcstrings` 키 파리티 테스트(웹 `i18n.test.ts` 대응) 신설 | 테스트 1건 |
| ⑤ 포맷 문자열 | `%lld`/`%@` 8키는 언어별 어순 확인 | 소 |

## 4. 결정 필요 (Brian)

- 1.1 다국어 착수 시점 — RELEASE_APPSTORE §4-1 "후속" 이 일정에 없다.
- iOS 출시(App Store 공개) 시 LANDING_SYNC §1 "iOS coming soon" 을 지우면서 §2 에 **"iOS 앱 UI 는 영어"** 단서를 함께 넣을지, 아니면 1.1 다국어 이후에 출시를 랜딩에 올릴지 (LANDING_SYNC 위조 0 규율).

번역 추가는 이 문서 범위가 아니다.
