# KNOWN_PUBLICATION_EXPOSURE — 공개 법무문서 미해결 마커 한시 격리

> **성격**: allowlist 가 아니라 **quarantine** 이다. 현재 오염 상태를 정확히 고정해
> 두고 **기록 없는** 모든 변화를 실패시킨다. 신규 1건 추가도, 무기록 1건 감소도 실패다
> (감소 자체가 금지는 아니다 — "실패 조건" 절).
>
> **★ 이 문서는 문제를 해결하지 않는다.** 노출은 지금도 진행 중이다
> (`PARTIALLY_REMEDIATED`, 언어별 24 → 1).
>
> **★ 이 격리의 종료조건은 하나다 — `PUBLIC_INTERNAL_MARKER_EXPOSURE = 0`.**
> 공개 URL 에 사내 검토 마커가 보이지 않으면 끝난다. 변호사 회신도, 게시 세트 결재도
> 이 조건의 입력이 아니다 (2026-09-10 재정의 — "해소 절차" 절, 경로 A).
> 초판이 "`CURRENT_PUBLICATION_SET` 결정 후 승인본 등록으로만 해결" 이라 적은 것은
> 문제 하나를 넷으로 나누기 전의 문장이며 **폐기**한다. 지금은 네 표면이 따로 간다:
>
> ```
> A  PUBLIC_INTERNAL_MARKER_EXPOSURE   48 → 2 (V-11 en/ko)   ← 이 문서. 종료 = 0
> B  PUBLICATION_VALIDITY              CURRENT_PUBLICATION_SET · 변호사 · PUBLISHED   ← 신규 가입·정식 공표 게이트 (G-1 · H13)
> C  RETENTION                         RETENTION_POLICY = OPEN · RETENTION_ENFORCEMENT = NOT_IMPLEMENTED   ← R-05
> D  pigos.io/privacy · /terms         구본·피그플랜 문안 공개 서빙   ← H17 (격리 밖, 아래 절)
> ```
>
> A 를 닫았다고 B·C·D 가 닫힌 게 아니고, B 가 늦는다고 A 를 계속 노출할 이유도 없다.
>
> **★ 절대 만료가 있다.** `2026-09-17T23:59:59+09:00` 이 지나면 무조건 CI FAIL 이다 (1차 연장 후 값 — manifest `expires_at` 과 동일).
> 자동 연장 없음. 연장하려면 사유를 적고 `expires_at` 을 바꾸는 **별도 커밋**이
> 필요하며, 그 커밋 자체가 감사 흔적이 된다.

---

## 무슨 일이 있었나

`https://api.pigos.io/legal/privacy` — **App Store 제출에 등록된 개인정보 URL** — 이
내부 검토 마커를 그대로 노출하고 있다. 2026-09-03 HTTP 실측으로 확인했다.

```
"…final confirmation requires legal counsel's review [COUNSEL]"
"[OPEN — to be confirmed operationally: whether to apply a withdrawal grace period·dormancy handling]"
"Payment processing results, payment·refund status information [V — actual verification required]"
```

### 왜 생겼나 — 테스트가 오염 경로를 고정하고 있었다

```
api/tests/integration/test_public_notice.py::test_runtime_copy_matches_canonical

    api/content/legal/public_privacy.{ko,en}.md
            ==  (바이트 동일 강제)
    docs/legal/publish_candidate/PIGOS_GLOBAL_PRIVACY_NOTICE{,_EN}.md
```

`publish_candidate` 는 **후보**다. `[OPEN]`·`[COUNSEL]` 이 남아 있는 것이 정상인
작업물이다. 그것과 런타임 서빙본의 바이트 동일성을 강제하면 후보의 미완성이 그대로
공개본의 미완성이 된다. 테스트가 안전장치가 아니라 오염 경로를 보장하고 있었다.

★ 이 테스트가 잘못 만들어진 것은 아니다. 2026-08-26 에 막으려던 것(개인 메일 공개·
FCM 오기·상호 오기)은 실재했고 지금도 `_FORBIDDEN` 이 잘 막고 있다. **비교 대상을
`publish_candidate` 로 잡은 것 하나**가 문제다.

---

## 연장 이력 — ★ 값만 바꾸지 않는다

연장할 때마다 **사유 · 새 만료일 · 그날까지 닫혀야 하는 항목**을 함께 적는다.
셋 중 하나라도 빠지면 다음 연장이 "또 기다린다"로 반복된다. 자동 연장 로직은
만들지 않는다 — 사람이 다시 적게 하는 것이 이 격리의 설계다.

### 1차 연장 — 2026-09-10 → 2026-09-17

```
사유        H13(CURRENT_PUBLICATION_SET) 대표 결재 미도착
            + 변호사 회신 미도착 (US 3종으로 범위를 좁혀 요청한 상태)
            ★ 문안 수정은 미승인 법무문서 편집이라 개발이 진행할 수 없다.
              기다리는 대상이 개발 산출물이 아니므로 연장 외에 선택지가 없다.

새 만료일   2026-09-17T23:59:59+09:00
            근거: 범위를 US 3종으로 좁힌 회신 요청 기준. 8종 전건 대기가 아니다.

그날까지 닫혀야 하는 것
  1  H13 결재 — (1) 그대로 연다 / (2) OTHER 차단 + US만 / (3) OTHER addendum 신설
     ★ 셋 중 무엇인지가 결재문에 명시돼야 한다. 불명확하면 개발이 STOP 한다
  2  변호사 회신 — MASTER_TERMS · GLOBAL_PRIVACY_NOTICE · ADDENDUM_US 3종
  3  manifest status 갱신 → G-1 충족
  4  배포 (G-4) + 배포 순서 9번 두 법역 확인
     승인 법역 성공 1건 + addendum 보유 법역 차단 1건 (★ OTHER 로 확인 금지)

담당        1 Brian · 2 변호사 · 3~4 개발(1·2 완료 후)
```

★ **9-17 까지도 1·2 가 안 오면 그때는 연장이 답이 아니다.** 두 번째 연장을 적기
전에 "게시 문서 없이 서비스를 계속 열어둘 것인가"를 먼저 결정해야 한다.
`docs/legal/LEGAL_P0_FREEZE_20260910.md` §6 참조.

---

## 등록 — 이 목록과 정확히 일치해야 한다

<!-- QUARANTINE_MANIFEST_BEGIN -->
```json
{
  "status": "PARTIALLY_REMEDIATED",
  "observed_at": "2026-09-10T00:00:00+09:00",
  "expires_at": "2026-09-17T23:59:59+09:00",
  "extension_no": 1,
  "extended_at": "2026-09-10T09:00:00+09:00",
  "owner": "Brian (PigOS legal track)",
  "remediation_condition": "V-11 사실 확인 완료 → 해당 행 정정 → 마커 0 → 본 격리 종료 + hard-fail 테스트로 전환. ★ 2026-09-10 기준 6조건 중 4건 종결(API·Web·모바일 권한·SDK write path 전부 0건, EXIF 유입 경로 없음 — APPROVAL_RECORD §3-1). 남은 것은 조건 1(farms.gps_lat/gps_lng non-null 집계)과 조건 6(backup·log 보유)뿐이며 둘 다 EC2 SSH 세션 1회로 닫힌다",
  "reason": "문안 수정은 미승인 법무문서 편집이므로 개발이 임의로 할 수 없다. 대표/변호사 결정 전까지 노출 사실을 명시 고정하고 신규 오염만 차단한다.",
  "entries": [
    {
      "source_path": "api/content/legal/public_privacy.en.md",
      "runtime_url": "https://api.pigos.io/legal/privacy?lang=en",
      "source_sha256": "bdb3e9699bb290c9db3badc7dd5db722afa79ef48decaf0d71892b29523b76fe",
      "markers": {},
      "expected_total": 0,
      "remaining": "none — V-11 조건 6건 전부 실측 종결 (2026-09-16). ★ 단 이것은 SOURCE 기준이다"
    },
    {
      "source_path": "api/content/legal/public_privacy.ko.md",
      "runtime_url": "https://api.pigos.io/legal/privacy?lang=ko",
      "source_sha256": "b309f8d17272a706f97bd3266dff3836b6b1cd5f238ffeeac2e48930eeca6b18",
      "markers": {},
      "expected_total": 0,
      "remaining": "none — V-11 조건 6건 전부 실측 종결 (2026-09-16). ★ 단 이것은 SOURCE 기준이다"
    }
  ],
  "last_remediation_at": "2026-09-16T17:30:00+09:00",
  "remediation_note": "★ 키 이름: last_remediation_at 은 가장 최근 부분 정정일이다. 종료(마커 0) 시에만 remediated_at 을 새로 만든다. 2026-09-16: V-11 조건 1·6 을 프로덕션 read-only 로 실측해 종결하고 [확인 중] 행을 [수집하지 않음] 으로 병합했다 — 조건 1: farms 80행 중 gps_lat·gps_lng non-null 0건(둘 중 하나만 있는 행도 0건, 좌표값 미출력) / 조건 6: 2026-09-16 03:40 전체 백업을 격리된 PostgreSQL 17 에 복원해 farms 79행 lat 0 lng 0 확인, audit_log 390행 중 farms 관련 0건·gps 언급 0건, public 스키마에 다른 좌표 컬럼 없음. 결재 4 (a) '사용하지 않는다' 의 확정조건 5개가 이로써 전부 충족됐다. ★ 그럼에도 status 는 PARTIALLY_REMEDIATED 다 — SOURCE 마커 0 ≠ PRODUCTION 마커 0. api.pigos.io/legal/privacy 는 배포 전까지 정정 전 본문을 서빙하며, 격리 종료는 프로덕션 엔드포인트에서 마커 0 이 확인된 뒤에만 가능하다. 이전 정정(2026-09-10): 언어별 24건 → 1건. 실행 결정 Brian(대표 구두 포괄 승인 하의 위임): [V] 11건 문안 정정 · [OPEN] 10건은 임의 기간을 만들지 않고 마커만 제거 (보유기간 정책 자체는 RETENTION_POLICY=OPEN 으로 별도 유지) · [COUNSEL] 1건은 제7조를 '법률 검토 중' 공개 조항으로 전환 · [ ] 2건은 부칙을 확정본 게시 시 기재로 변경.",
  "source_marker_total": 0,
  "production_marker_total": "★ 48 (언어별 24) — 2026-09-16 17:4x KST HTTP 실측. V 11 · OPEN 10 · COUNSEL 1 · 빈 대괄호 2, ko/en 동일. 즉 2026-09-10 의 24→1 정정은 저장소에만 있고 프로덕션에 배포된 적이 없다 (프로덕션 api/content/legal/public_privacy.ko.md 는 6f16e41, 2026-08-27 자). 공개 노출은 2026-09-03 최초 실측 이래 줄어든 적이 없다."
}
```
<!-- QUARANTINE_MANIFEST_END -->

```
SOURCE      0건   ← 48건(en 24 + ko 24) → 2건(9/10 정정) → 0건(9/16 V-11 종결)
PRODUCTION  ★ 48건 — 줄어든 적이 없다 (2026-09-16 HTTP 실측)
```

### ★★ 2026-09-16 발견 — 9/10 정정은 배포된 적이 없다

오늘 처음으로 **공개 URL 을 직접 세어봤다.** 문서들이 "24 → 1" 이라고 적어온 동안
공개본은 한 번도 바뀌지 않았다.

```
실측 (2026-09-16, curl)
  api.pigos.io/legal/privacy?lang=ko    V 11 · OPEN 10 · COUNSEL 1 · [ ] 2  = 24
  api.pigos.io/legal/privacy?lang=en    동일 = 24                            합계 48

프로덕션 파일    ~/pigos/api/content/legal/public_privacy.ko.md
                 mtime 2026-08-28 17:12 · sha256 badf088d… · 마커 11건
                 = 커밋 6f16e41 (2026-08-27) 의 내용
정정 커밋        ec99391 (2026-09-11) — 저장소에만 있다. 배포 0회
```

★ **이것이 SOURCE 와 PRODUCTION 을 나눈 이유 그 자체다.** 오늘 상단 정의를 고치면서
"소스 0 ≠ 공개 0" 이라고 적었는데, 실제로는 그 간극이 **6일이 아니라 2주**였고 크기도
2건이 아니라 48건이었다. 어제까지의 모든 보고에서 "언어별 24 → 1" 은 저장소 상태였다.

```
정정 전 서술    "PARTIALLY_REMEDIATED (언어별 24 → 1)"
정확한 서술     "소스는 정정됐고 공개본은 2026-09-03 실측 그대로다"
```

**만료(2026-09-17)까지 배포가 없으면 격리는 노출 48건인 채로 만료된다.** 이것은
"거의 다 고쳤는데 하나 남았다" 가 아니라 **아무것도 공개적으로 고쳐지지 않았다** 이다.

★ **이 둘을 섞지 않는다.** 소스에서 마커를 지운 것과 공개 URL 에서 사라진 것은 다르다.
격리 종료 조건은 후자다("상단 정의" 절).

### V-11 종결 실측 — 2026-09-16 (프로덕션 read-only)

결재 4 **(a) 사용하지 않는다** 의 확정조건 5개가 전부 충족됐다.

```
① DB non-null 0건        farms 80행 · gps_lat non-null 0 · gps_lng non-null 0 · 한쪽만 있는 행 0
                         ★ 좌표값은 출력하지 않았다. 집계만 (SET default_transaction_read_only=on)
② API·웹 write path      0건 (2026-09-10 실측)
③ 모바일 위치 권한       0건 (2026-09-10 실측 — 권한이 없으면 OS 가 정밀 위치를 주지 않는다)
④ analytics/SDK          0건 (2026-09-10)
⑤ 백업·로그·EXIF         ★ 오늘 닫혔다 —
                         백업: 2026-09-16 03:40 전체 덤프를 격리 PG17 에 복원 → farms 79행 lat 0 lng 0
                         로그: audit_log 390행 중 farms 관련 0건 · gps 문자열 언급 0건
                         스키마: public 에 다른 좌표 컬럼 없음 (매칭된 이름은 platform·calculated_at 등 오탐)
                         EXIF: 유입 경로 없음 (2026-09-10)
```

프로덕션 80행 / 백업 79행 차이는 백업 시각(03:40) 이후 생성된 농장 1건으로 설명된다 —
불일치가 아니다.

**정정 내용**: `[확인 중] 정밀 위치정보` 행을 삭제하고 `[수집하지 않음]` 에 병합하되,
**컬럼이 남아 있다는 사실을 문장에 넣었다.** "수집하지 않음" 만 적고 컬럼을 숨기는 것이
CLOSURE_COMMON V-11 이 지적한 부정확 고지 그 자체이기 때문이다.

★ 최초 실측은 en 라이브 HTML 24건이었으나, `?lang=ko` 도 동일하게 공개 서빙되므로
**양쪽 모두 등록**했다. 한쪽만 걸면 나머지가 무방비가 된다.

### 마커 종류

| 키 | 패턴 | 의미 |
|---|---|---|
| `V` | `[V — actual verification required]` | 우리 시스템이 실제로 그 항목을 수집·처리하는지 미확인 |
| `OPEN` | `[OPEN — to be confirmed operationally…]` | 보존기간 등 운영 정책 미확정 |
| `COUNSEL` | `[COUNSEL]` | 변호사 판단 필요 (controller/processor 역할 = LEGAL-D13) |
| `EMPTY_BRACKET` | `[ ]` | 값 미기입 자리표시자 (시행일 등) |

---

## 실패 조건 — 하나라도 어긋나면 CI FAIL

```
신규 마커 1건 추가           FAIL
무기록 마커 1건 감소         FAIL   ← green 으로 넘기지 않는다. 문서가 바뀐 것이므로
                                    왜 줄었는지 기록하며 명세를 갱신해야 한다
종류 구성 변경               FAIL   예: V 11 → 10, OPEN 10 → 11 (합계 같아도)
등록되지 않은 파일에 마커     FAIL
source_sha256 불일치         FAIL   ← 본문이 바뀌었는데 명세가 그대로면 격리가 무의미
2026-09-17 23:59:59 KST 경과  FAIL   무조건. 자동 연장 없음 (manifest expires_at 기준)
```

**wildcard·정규식 예외는 두지 않는다.** 파일·해시·종류·개수 전부 명시값이다.

★ **마커 감소 자체가 금지된 것이 아니다.** 정상 remediation 은 이렇게 한다 — 한 변경세트에서
**원자적으로**:

```
1  source 수정 (api/content/legal/public_privacy.{en,ko}.md)
2  변경 사유 (무엇을 어떤 실측 근거로 고쳤나)
3  manifest 의 markers · expected_total · remaining 갱신
4  source_sha256 재계산
5  last_remediation_at + remediation_note 에 기록
```

다섯 개가 같은 커밋에 있으면 테스트는 통과한다. 테스트가 막는 것은 **1 만 하고 2~5 를
안 한 것** — 누군가 문구만 지워 green 을 만드는 경우다. 2026-09-10 의 24 → 1 정정이
정확히 이 절차로 통과했다. "정상 remediation 도 테스트가 막는가" 라는 질문의 답은 아니오다.

---

## 격리에 포함되지 **않는** 것

가입 동의 화면(`/consent/signup-plan`)이 서빙하는 문서들도 미해결 마커를 갖는다.

```
privacy_notice.{en,ko}.md    5건   OPEN 1 · PLACEHOLDER 4
master_terms.{en,ko}.md      5건   OPEN 1 · PLACEHOLDER 4
addendum_us.en.md            4건   PLACEHOLDER 4
addendum_br.en.md            3건   PLACEHOLDER 3
```

**이것들은 다른 문제다.** 전부 `status: DRAFT_LAWYER_PENDING` 이며 애초에 미승인
문서로 표시돼 있다. 해결 경로는 "마커 제거"가 아니라 **`status != PUBLISHED` 는
runtime resolver 에 들어가지 못하게 하는 것**이다(같은 RUN 의 별도 계약).

공개 URL 노출과 동의화면 draft 노출을 한 목록에 섞으면 해소 조건이 달라 관리가 깨진다.

---

## ★ 격리 밖에서 새로 실측된 공개 노출 — pigos.io (2026-09-11)

이 문서는 `api.pigos.io/legal/privacy` 만 다뤄 왔다. 공개 사이트 저장소(`pigos-landing`,
HEAD `ec08df5` 2026-08-27)를 읽으니 **다른 방침·약관이 공개 서빙 중**이다.

```
pigos.io/privacy          src/pages/privacy.astro   115줄 · 한국어 전용 정적 본문 · "시행일 2026년 05월 30일"
                          ★ api.pigos.io/legal/privacy(격리 중인 정본)와 다른 문서다
pigos.io/terms            src/pages/terms.astro     104줄 · 한국어 · "피그플랜" 3회 · 시행일 2026-05-30
                          ★ PigOS 마스터 약관(publish_candidate)이 아니라 피그플랜 계열 문안
pigos.io/legal/privacy    302 → api.pigos.io/legal/privacy   (ec08df5, App Store 제출용)
푸터·쿠키 배너 링크       /privacy 로 간다 (GoogleAnalytics.astro:34 등 5곳) — /legal/privacy 가 아니다
앱                        Android·iOS 소스에 pigos.io/privacy·/terms 링크 0건 (api 호스트만) → PLATFORM_PARITY §2 PENDING_RECHECK 해소
```

즉 지금 공개 상태는 **방침 두 벌**이다 — 하나는 격리 마커가 붙은 정본(api), 하나는
5/30 자 한국어 구본(landing). 사용자가 푸터에서 누르면 구본이 열린다. 8건 전부 DRAFT 인
상태에서 공개 사이트가 피그플랜 문안 약관을 PigOS 약관처럼 내고 있다.

```
성격    격리 항목이 아니라 **격리 밖 노출**. 마커가 없어서 CI 가 못 잡는다
소유    법무(내용) + 개발(라우팅). 개발이 할 수 있는 건 /privacy·/terms → /legal/* 리다이렉트 한 줄이나,
        그러면 공개 사이트가 마커 붙은 격리본을 가리키게 된다 — 그것도 결정이다
결정    HUMAN_INPUT_QUEUE H17
```

## 해소 절차 — ★ 2026-09-10 재정의

초판은 "변호사 회신 → PUBLISHED → 해제" 한 경로만 두었다. 그래서 회신이 늦으면 **격리 연장
외에 선택지가 없었다.** 마커 24건의 소유자를 뜯어보니 그렇지 않다.

### 마커 24건(언어별)의 실제 소유자

| 마커 | 건수 | 누가 닫나 | 변호사 필요? |
|---|---|---|---|
| `[V — 실측 확인 필요]` | 11 | **10건 실측·정정 완료**(2026-09-10) · **1건(V-11 정밀 위치정보) 사실확인 미완** — 조건 1·6, EC2 read-only 1회 → 대표 문안 승인 | 아니오 |
| `[OPEN — 운영 확정]` | 10 | 대표·운영 값 확정 + **★ 집행 잡** | 아니오 |
| `[COUNSEL]` | 1 | 제7조 controller/processor = D-13 | **예** |
| `[ ]` 빈 대괄호 | 2 | 공고일·시행일 — 대표 | 아니오 |

**23 / 24 가 변호사 없이 닫힌다.** 그중 22 는 닫혔고, V-11 1건(언어별 2)이 남아 manifest 와 일치한다.

### 남은 1건 — 마커에서 조항으로

`[COUNSEL]` 1건은 값을 채울 수 없다. 대신 **마커를 노출하는 대신 조항으로 명시**한다.

```
현재   "…확정된 법적 역할은 [COUNSEL]"        ← 사내 검토 표기가 그대로 보인다
전환   "본 조의 역할 구분은 법률 검토 중이며     ← 검토 중임을 밝힌 조항
        확정 시 제15조에 따라 개정 고지합니다"
```

★ **미완성 마커를 노출하는 것과, 검토 중임을 밝히는 것은 다르다.** 전자는 사내 문서가 새어
나간 것이고, 후자는 정보주체에게 상태를 알리는 것이다. 문안은 **결재 6**(대표).

### 두 경로

```
경로 A — 정정 배포 (변호사 회신 불요)          ★ 이쪽으로 격리를 푼다
  1  대표 결재 — 결재 3(:191·:194) · 결재 4(V-11) · 결재 6(제7조 문안)
  2  [V] 11 · [ ] 2 · [COUNSEL] 1 → 문안 정정  (OPEN 10 은 제외 — 아래)
  3  정정본 게시 → 마커 0
  4  ★ 본 문서 삭제 + 테스트를 hard fail 로 전환
     → 9-17 만료 문제 소멸. 3차 연장 질문 자체가 없어진다

경로 B — 개시 배포 (변호사 회신 필요)
  변호사 회신 → manifest PUBLISHED → 신규 가입 개방
  ※ 격리와 무관. A 가 끝나면 B 는 급하지 않다
```

### ★ 앞선 판의 논리 오류 — 정정 (2026-09-10)

이전 판은 두 문장을 함께 적었다. 둘은 동시에 참일 수 없다.

```
(가)  "OPEN 10건은 A 에서 제외한다"
(나)  "A 완료 → 마커 0 → 본 문서 삭제"
```

`[OPEN — 운영 확정]` 이 런타임 공개본에 남아 있으면 마커는 0 이 아니고, 따라서 격리를
삭제할 수 없다. **문제를 하나로 본 것이 원인이다.** 둘로 나눈다.

| | 문제 | 무엇이 잘못됐나 | 어떻게 닫히나 |
|---|---|---|---|
| **P1** | 공개 URL 에 사내 작업 표기가 보인다 | `[V]` `[OPEN]` `[COUNSEL]` `[ ]` 가 정보주체에게 노출 | **문안에서 제거** — 본 격리의 대상 |
| **P2** | 보유기간 정책과 purge 집행이 미확정 | 기간을 정하지 않았고 삭제하는 잡도 없다 | 정책 확정 + 집행 잡 + 테스트 — **R-05, 별건** |

★ **마커 제거 ≠ retention 문제 해결.** P1 을 닫아도 P2 는 그대로 열려 있다.

### `[OPEN]` 10건을 실제로 어떻게 처리했나

임의의 기간을 만들어 채우지 않았다. **마커를 지우면서 확정되지 않은 기간을 사실처럼
주장하지도 않았다** — 해당 문장에서 기간 주장 자체를 빼고, 실측으로 확인된 사실만 남겼다.

```
계정정보      "지체 없이 파기" → "식별정보를 파기하여 개인을 특정할 수 없도록 처리"
                (account_deletion_service 실측 — 행 DELETE 가 아니다)
농장 데이터    "파기 또는 반환" → "탈퇴 시 해당 농장을 비활성화"  (farms.active=false 실측)
AI 입출력      "필요 기간 보관 후 삭제" → "회사 서버에 보관하지 않습니다"  (저장 모델 0건)
OCR           행 삭제  (기능 자체가 없다)
접속·보안로그  법정 3개월만 남기고 "그 밖의 로그" 미정 문구 삭제
고객지원      법정 3년만 남김
백업·동의이력  기간 주장 없이 동작만 기술
오프라인      단말 저장 사실만 기술
```

그리고 표 서두에 **"기간을 명시하지 않은 항목은 정책 수립 후 개정·고지한다"** 를 넣었다.
없는 것을 없다고 말하는 문장이지, 있는 척하는 문장이 아니다.

### 그래서 지금 상태

```
A  PUBLIC_INTERNAL_MARKER_EXPOSURE   = PARTIALLY_REMEDIATED   (언어별 24 → 1)   ← 이 격리
B  PUBLICATION_VALIDITY              = 8건 전부 DRAFT_LAWYER_PENDING            ← G-1 · H13, 별건
C  RETENTION_POLICY                  = OPEN                    ← 닫히지 않았다   ← R-05, 별건
   RETENTION_ENFORCEMENT             = NOT_IMPLEMENTED         ← purge 잡 0건
D  pigos.io 구본·피그플랜 문안        = 공개 서빙 중                              ← H17, 별건
```

★ 이 격리를 닫아도 **R-05 는 살아 있다.** 보유기간에 숫자를 쓰려면 그때 다시
`정책값 + 집행 잡 + 테스트 + 문서 승인` 네 개가 함께 있어야 한다.

### 경로 A 가 STOP 하는 조건

```
V-11 사실 확인 미완                      →  ★ 현재 여기. 마커 1건이 남는다
결재 3 · 4 · 6 중 하나라도 택일 미확정    →  어느 문안으로 고칠지 정해지지 않는다
보유기간에 임의의 숫자를 넣으려 함        →  R-05 재생산. 거절
```

---

## 관련

```
docs/legal/PRIVACY_NOTICE_FACT_FINDING_20260902.md   [V]·[OPEN] 20건 실측 초안
docs/legal/COUNSEL_QUESTION_QUEUE_20260902.md        [COUNSEL] = LEGAL-D13
docs/legal/LEGAL_PUBLICATION_GAP_REPORT_20260902.md  publish_candidate 가 정본인 이유
api/tests/integration/test_publication_gate.py       본 명세를 집행하는 테스트
```
