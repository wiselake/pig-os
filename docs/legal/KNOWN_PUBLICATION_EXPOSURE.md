# KNOWN_PUBLICATION_EXPOSURE — 공개 법무문서 미해결 마커 한시 격리

> **성격**: allowlist 가 아니라 **quarantine** 이다. 현재 오염 상태를 정확히 고정해
> 두고 그 밖의 모든 변화를 실패시킨다. 신규 1건 추가도, 기존 1건 감소도 실패다.
>
> **★ 이 문서는 문제를 해결하지 않는다.** 노출은 지금도 진행 중이다
> (`CONTAINED_NOT_REMEDIATED`). 해결은 `CURRENT_PUBLICATION_SET` 대표 결정 후
> 승인본 등록으로만 가능하다.
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
  "status": "CONTAINED_NOT_REMEDIATED",
  "observed_at": "2026-09-03T11:19:00+09:00",
  "expires_at": "2026-09-17T23:59:59+09:00",
  "extension_no": 1,
  "extended_at": "2026-09-10T09:00:00+09:00",
  "owner": "Brian (PigOS legal track)",
  "remediation_condition": "CURRENT_PUBLICATION_SET 대표 결정 → 승인본을 PUBLISHED 로 등록 → runtime 이 그 artifact 를 서빙 → 본 격리 삭제",
  "reason": "문안 수정은 미승인 법무문서 편집이므로 개발이 임의로 할 수 없다. 대표/변호사 결정 전까지 노출 사실을 명시 고정하고 신규 오염만 차단한다.",
  "entries": [
    {
      "source_path": "api/content/legal/public_privacy.en.md",
      "runtime_url": "https://api.pigos.io/legal/privacy?lang=en",
      "source_sha256": "637a7d50785452ca240ec508140886bec9aec13f129e020f37855da08732d081",
      "markers": { "V": 11, "OPEN": 10, "COUNSEL": 1, "EMPTY_BRACKET": 2 },
      "expected_total": 24
    },
    {
      "source_path": "api/content/legal/public_privacy.ko.md",
      "runtime_url": "https://api.pigos.io/legal/privacy?lang=ko",
      "source_sha256": "badf088da8665004841bbb991290cbe928c0220e3d7ad8ee8884a90c847645c8",
      "markers": { "V": 11, "OPEN": 10, "COUNSEL": 1, "EMPTY_BRACKET": 2 },
      "expected_total": 24
    }
  ]
}
```
<!-- QUARANTINE_MANIFEST_END -->

```
합계   48건   (en 24 + ko 24)
```

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
기존 마커 1건 감소           FAIL   ← green 으로 넘기지 않는다. 문서가 바뀐 것이므로
                                    왜 줄었는지 기록하며 명세를 갱신해야 한다
종류 구성 변경               FAIL   예: V 11 → 10, OPEN 10 → 11 (합계 같아도)
등록되지 않은 파일에 마커     FAIL
source_sha256 불일치         FAIL   ← 본문이 바뀌었는데 명세가 그대로면 격리가 무의미
2026-09-17 23:59:59 KST 경과  FAIL   무조건. 자동 연장 없음 (manifest expires_at 기준)
```

**wildcard·정규식 예외는 두지 않는다.** 파일·해시·종류·개수 전부 명시값이다.

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

## 해소 절차

```
1  CURRENT_PUBLICATION_SET 대표 결정        신규 가입자·공개 URL 에 무엇을 서빙할지
2  그 문서의 [OPEN]·[V]·[COUNSEL] 확정       운영 결정 + 실측 + 변호사 회신
3  승인 기록 (DOCUMENT_APPROVED)
4  immutable 등록 → status = PUBLISHED
5  runtime 이 그 artifact 를 서빙
6  ★ 본 문서 삭제 + 테스트를 hard fail 로 전환
```

`5` 까지 끝나야 격리를 풀 수 있다. `1`~`4` 는 개발이 할 수 없는 일이다.

---

## 관련

```
docs/legal/PRIVACY_NOTICE_FACT_FINDING_20260902.md   [V]·[OPEN] 20건 실측 초안
docs/legal/COUNSEL_QUESTION_QUEUE_20260902.md        [COUNSEL] = LEGAL-D13
docs/legal/LEGAL_PUBLICATION_GAP_REPORT_20260902.md  publish_candidate 가 정본인 이유
api/tests/integration/test_publication_gate.py       본 명세를 집행하는 테스트
```
