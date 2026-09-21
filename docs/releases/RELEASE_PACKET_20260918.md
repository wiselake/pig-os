# 릴리스 판단 패킷 — 2026-09-18 최종판

> **목적**: 사람이 **merge 할지, 배포할지만** 판단할 수 있게. merge·배포·가입 재개는 하지 않았다.
> **시간축**: 9/16 밤 초판(55b8534) → 9/17 오전 정정(hotfix 분리·G-3 표현·격리 보존) → 9/18 2차 검토
> (제9조 원문·D-xx 64건·결재 7·만료 기록·fail-closed 테스트). 이 판이 최종이며 이후는 결재·배포 기록만 덧붙인다.
> **기준일 2026-09-18** — 격리는 이미 만료됐다.

---

## 0. 한눈에 — 두 트랙

```
TRACK A  긴급복구 — 최우선         PR #3  hotfix/legal-markers-20260917  4d008a7  CI GREEN   (= d088e73 + main ae61369 merge, §3-5)
         quarantine already expired at 2026-09-17T23:59:59+09:00
         목표: 추가 연장이 아니라 ACTIVE incident 를 production remediation 으로 종결
TRACK B  정규 릴리스 (그 다음)     PR #2  safety/pigos-20260916          d9eeda4  159 commits CI GREEN

MAIN CHANGED    NO    origin/main = 8a80ea4
PROD CHANGED    NO    2e372b1 · 애플리케이션 쓰기 0 · DB 쓰기 0 · 배포 0
```

커밋 수는 `git rev-list --count 8a80ea4..<head>` 실측 (2026-09-18). 이전 판의 8 / 154 는 각각 9f6b8fe·d088e73 추가 전, 밤샘 후반 커밋 전 숫자였다.

### 왜 나눴나

문제는 하나다 — **공개 방침의 내부 마커 48건(D-xx 포함 64), 격리는 2026-09-17 23:59:59 KST 에 만료됐다**.
그것을 없애려고 정규 릴리스 전체(PR #2 — 속도제한·잡 의미론·ops 엔드포인트·B-9·G-3·법무 문서)를
프로덕션에 넣을 이유가 없다. 마커 제거는 형식 게시(PUBLISHED)가 아니라 **정정 복구(correction remediation)**라
Path A 로 이미 분리돼 있던 경로다.

---

## 1. TRACK A — PR #3 hotfix

### 1-1. 내용 — 런타임 변화는 "문서 본문" 하나

```
d9b8f88  content  ec99391 cherry-pick             언어별 24 → 1
91ae28e  content  V-11 행 (919a460 의 content 절반)   1 → 0   ★ 09-16 read-only 실측 근거
70cf56d  test     publish_candidate 바이트동일 제거 (cc247d6, 1파일)  — 오염 경로였던 계약
751aad5  test     날짜 의존 trend 테스트 (8dcb9cd)   main 은 CI 를 본 적이 없어 9월엔 항상 실패
6c113f2  ci       실제로 트리거되는 워크플로 (f4d684e) main 의 ci.yml 은 없는 브랜치를 가리킨다
1f9df88  ci       ci.yml @55b8534                    required check context 가 나타나야 한다
66ed080  style    ruff 47건 (b3ea993)                lint 가 required check 다
0186572  style    테스트 6건
9f6b8fe  test     마커-0 enforcer + 정본 재동기화 가드   main 에는 둘 다 없었다 — 이전 초록은 "가드 없음"
d088e73  content  [D-xx] 8건 제거 + detector 확장       격리 집계에 빠져 있던 DECISION_REGISTER 참조. 분리 가능
```

★ **게이트 변화 없음.** G-3 · rate limit · /health/ops · B-9 병합은 **이 PR 에 없다**.
US 가입 동작은 지금과 같다(201). 마이그레이션 0.

### 1-2. 검증

```
로컬 (Python 3.14 · 빈 PostgreSQL 17)
  소스 마커        ko 0 · en 0
  alembic          빈 DB 에서 head 완주 · head 1개
  pytest tests     1313 passed · 1 skipped   (main 1310 collected → 1314)
  ruff             clean · 테스트 후 tree clean
CI                 run 35293878390 @ d088e73 — backend 3.12 ✓ 3.14 ✓ frontend ✓
                   run 35553756807 @ 4d008a7 (base 갱신 후) — backend 3.12 ✓ 3.14 ✓ frontend ✓ · 1313 passed · 02:18–02:21Z = 11:18 KST (D9 GREEN 창 09:00–24:00 KST 안)
```

### 1-3. 배포 순서

```
1  api    (문서 렌더는 api 컨테이너 안에 있다)
2  worker (같은 이미지. 코드 변화 없음 — 이미지 정합만)
web·mobile  변경 없음. 배포 안 함
```

### 1-4. ★ 배포 후 종결 조건 — `grep -c "[V" == 0` 으로는 부족하다

빈 문서·잘못된 fallback 도 0 이다. 그리고 초기 48건은 V 만이 아니다. 아래 **전부**:

```
1  HTTP 200          ?lang=ko · ?lang=en
2  본문 비어있지 않음  두 언어 각각 > 20KB (지금 31,895 bytes)
3  문서 정체성       "제9조" 와 "Article 9" 가 각각 보인다 — 다른 문서가 아니다
4  전체 detector      [V — · [OPEN · [COUNSEL] · [ ] · [D-xx]   다섯 종류 모두 0, 두 언어 모두
                     ★ 격리 manifest 의 마커 종류표와 같은 정규식을 쓴다 (KNOWN_PUBLICATION_EXPOSURE "마커 종류")
5  배포 SHA          실행 중인 이미지 = PR #3 merge commit
                     (api 컨테이너 안 content/legal/public_privacy.ko.md 의 sha256 = 저장소 값)
```

다섯 개가 전부 참일 때만:

```
PUBLIC_INTERNAL_MARKER_EXPOSURE = CLOSED
```

### 1-5. ★ 격리 문서는 삭제하지 않는다

초판은 "KNOWN_PUBLICATION_EXPOSURE 삭제" 라고 적었다. 틀렸다. 이 사건의 이력이 감사 기록이다:

```
2026-08-27  6f16e41 배포     → PROD 48건 노출
2026-09-03  최초 실측         48 확인, 격리 시작
2026-09-10  저장소 정정       48 → 2  (소스)  ★ 배포 안 됨
2026-09-16  저장소 정정        2 → 0  (소스)  · 밤에 PROD 48 재확인 — "9/10 정정은 배포된 적 없다"
2026-09-17  PR #3 준비 · CI GREEN                → PROD unchanged · 23:59:59 격리 만료
2026-09-18  [D-xx] 8×2 발견(64) · 결재 7 · fail-closed 테스트  → PROD unchanged
2026-09-18+ 결재 3·4·6·7 후 배포 예정              → verify PASS 시 48/64 → 0, 그때 REMEDIATED
```

종결 시 manifest 는 **불변 사건 기록**으로 남긴다:

```json
"status": "REMEDIATED",
"observed_initial": 48,
"source_marker_total": 0,
"production_marker_total": 0,
"deployed_commit": "<PR #3 merge sha>",
"closed_at": "<검증 시각>",
"verification": "§1-4 다섯 항목 실측값"
```

`remediated_at` 은 **이때 처음 생성**한다 (`last_remediation_at` 과 다르다 — 09-16 정정).
테스트 `_UNRESOLVED_STATES` 는 종결 커밋에서 함께 바꾼다.

### 1-6. 롤백 — ★ 지점은 8a80ea4 가 아니라 2e372b1

```
프로덕션 실제 배포본   2e372b1 (2026-08-28)   ← 2026-09-18 실측: ~/pigos/api 파일 해시 4개가 2e372b1 과 일치
                                             8a80ea4 와는 consent_service·jurisdiction 이 **다르다**
main                  8a80ea4              ← Lou 의 가입 게이트 커밋. ★ 프로덕션에 없다
DB                    없음
```

★ **"main 으로 롤백" 은 롤백이 아니라 미배포 커밋 하나를 새로 배포하는 것이다.** 롤백 지점은
프로덕션이 실제로 돌리고 있는 `2e372b1` 이고, 배포 직전에 `deploy.sh` 가 찍는 롤백 이미지
태그로 다시 고정한다. 되돌리면 48건이 다시 공개된다 — 격리를 REOPEN 으로 함께 되돌린다.

### 1-8. 2026-09-18 2차 검토 — A·B·C·D

**A. 제9조 보유기간 표 — 실제 서빙 문장** (PR #3 d088e73, ko 원문 그대로)

```
①  … 본 방침에 임의의 장기 보유 기간을 기재하지 않으며, 아래에 기간을 명시하지 않은 항목은
     보유·삭제 정책을 수립하는 대로 본 방침을 개정하여 고지합니다.          ← 새 문장 (표 머리)

계정정보              탈퇴/목적 달성 시 식별정보를 파기하여 개인을 특정할 수 없도록 처리. 법정 보존은 제2항
농장 원천 데이터       이용 기간 동안 보관. 탈퇴 시 해당 농장 비활성화. 조직 고객 반환·삭제는 B2B DPA
오프라인 임시 저장본   이용자 단말에 저장. 동기화 완료/앱 삭제 시 단말에서 삭제
AI 입력·출력          회사 서버에 보관하지 않음. 학습 이용은 별도 동의 범위
접속·보안 로그        접속 로그 3개월 (통신비밀보호법)                     ← 법정, 정정 전에도 있던 값
고객지원 기록         소비자 불만·분쟁 기록 3년 (제2항)                    ← 법정, 정정 전에도 있던 값
백업 데이터           순환 주기에 따라 갱신·삭제. 원본 삭제 후 잔존분도 주기 내 삭제
동의 이력             법령이 허용·요구하는 범위에서 처리 종료 후에도 보관
결제·세금·법정 보존    제2항의 법정 기간
(삭제된 행 1)         OCR 업로드 문서·이미지 — 기능 자체가 없다 (제2조 "향후 수집 예정"에 있음)
```

세 갈래 중 답: **② "미확정" 문장으로** — 단 행마다가 아니라 **표 머리 한 문장**으로, 각 행은
실측된 동작만 남겼다. 기간을 만든 행은 없다(3개월·3년은 법정이며 정정 전 본문에도 있었다).
행 삭제는 OCR 1건뿐이고 그 항목은 기능이 없다.

★ **그러므로 이것은 결재 6(제7조 1건)의 자동 확장이 아니다 — 별도 결재 항목이다.** 아래 C 의
서명 요청에 **결재 7** 로 같이 올린다. 문안은 이미 서빙본에 들어 있으므로 "승인/반려" 만 필요하다.

**★ A 를 읽다가 나온 것 — 마커는 48 이 아니라 64 였다.** `[D-01]`·`[D-02]`×3·`[D-03]`×2·`[D-04]`×2 —
DECISION_REGISTER 참조 번호가 언어별 8건, 프로덕션·정본·정정본 세 곳 모두에 있었다. 격리의
마커 종류표(V·OPEN·COUNSEL·[ ])에 없어서 집계에서 빠졌다. `d088e73` 로 서빙본에서만 제거
(토큰만, 문장 불변) + enforcer·verify 스크립트에 `[D-xx]` 추가. **별도 커밋이라 위임 해석이
다르면 그 커밋만 뺄 수 있다.**

**B. REMEDIATED — 찍지 않았다.** manifest 는 `PARTIALLY_REMEDIATED`, `remediated_at`·`closed_at`·
`deployed_commit` 전부 없음. 순서는 배포 → verify PASS → 그때 기록. 지금 그렇게 돼 있다.

**C. 서명 요청 문안** (Brian 이 오전에 보낼 것 — 개발이 결재를 대신하지 않는다)

```
결재 3  방침 제11조 :191·:194(취약점 점검·재식별 방지 로드맵) 삭제              9/10 구두 → 서명 요청
결재 4  V-11 농장 GPS (a) 미수집 유지 — 확정조건 5개 9/16 충족                9/10 구두 → 서명 요청
결재 6  제7조 [COUNSEL] → "법률 검토 중" 공개 조항 전환 (a)                   9/10 구두 → 서명 요청
결재 7  제9조 보유기간 표 — 미확정 기간을 만들지 않고 표 머리에 "정책 수립 후 개정·고지" 명시,
        각 행은 실측 동작만 기재 (위 A 원문)                                    ★ 신규 — 승인/반려
```

★ **NOT_RECEIVED 는 승인이 아니다.** 서명 형식은 대체할 수 있어도 **실제 결정**은 대체할 수 없다.
결재 3·4·6·7 각각에 대해 아래 **전부**가 채워질 때만 "결정됨" 이다:

```
decision:               APPROVED | REJECTED
decided_by:             <해당 항목의 canonical decision authority — 실제 사람>
decided_at:             <실제 시각>
evidence:               VERBAL | SIGNED
recorded_by:            <기록자>
scope:                  <정확한 결재 항목 — 예: "결재 7 제9조 보유기간 표 문안">
written_confirmation:   RECEIVED | NOT_RECEIVED
```

`DECIDED_BY` 는 그 사람이 그 항목의 결정 권한자일 때만 성립한다. 개발 세션은 기록자일 뿐
결정자가 아니다 — 격리 문서가 존재하는 이유가 그것이다.

**D. manifest.json — 손대지 않았다.** main·hotfix 모두 8건 `DRAFT_LAWYER_PENDING`, `git diff` 0.
정정 배포는 마커를 지우는 것이지 게시 상태를 올리는 것이 아니다.

**잔여 둘**
```
테스트 수     main 8a80ea4 collected 1310 → PR #3 1314 (바이트동일 테스트 −2, enforcer +6). 1313 passed + 1 skipped
롤백 대조     배포 직전 프로덕션 실제 SHA 를 찍는다 — 지금 실측은 파일 해시 4개 = 2e372b1.
              deploy.sh 가 찍는 롤백 이미지 태그를 그 값과 대조한 뒤 배포
```

### 1-7. merge 전 답변 — 2026-09-18 검토 6항목

```
Q1  OPEN 10건에 값을 채웠나            아니오. ec99391 diff: 미확정 문장을 삭제하고 실측 사실만 남겼다
                                        ("서버에 보관하지 않습니다" · "단말에 저장" · 탈퇴 시 비활성화 등).
                                        추가된 기간은 3개월·3년뿐이며 둘 다 정정 전에도 있던 법정 기간이다.
                                        제9조① 에 "기간을 명시하지 않은 항목은 정책 수립 후 개정·고지" 를 넣었다.
                                        R-05(RETENTION) 는 그대로 OPEN — 값을 만들지 않았다
Q2  CI GREEN 의 의미                    ★ PR #3 의 초록은 9f6b8fe 이전엔 "가드 없음" 이었다 — main 에는 격리
                                        테스트도 마커 enforcer 도 없다. 9f6b8fe 로 enforcer + 재동기화 가드 추가.
                                        지운 "날짜 의존 테스트" 는 trend PSY 테스트다. 격리 만료 테스트가 아니다.
                                        기존 test_quarantine_has_not_expired 는 9/18 만료 사실을 만나 FAIL 했다(설계대로).
                                        d9eeda4 에서 만료·미배포·ACTIVE 상태를 fail-closed 로 검증하는 테스트로 교체했고,
                                        현재 final-head CI 는 GREEN 이다. 만료일은 밀지 않았다
Q3  publish_candidate 재오염            정본에 24건 그대로. public_notice.py docstring 이 "cp 하라" 고 적혀 있었다 →
                                        정본은 안 고치고(승인 전 편집 금지) "정본에 마커가 있는 동안 서빙본 == 정본" 을
                                        실패로 만드는 가드 추가 · docstring 반대로 고침. cp 재현 시 2건 실패 확인
Q4  결재 3·4·6 서명본                   ★ 없다. APPROVAL_RECORD: "서명본 없음". 3·6 = 대표 구두 위임 하의 Brian 실행
                                        선택(택일은 됐다: :191·:194 삭제 · 제7조 (a)). 4 = 조건부 승인 → 9/16 조건 충족.
                                        merge = 구두 위임 + 미서명 상태에서의 게시. 이것이 충분한지는 Brian 판단
Q5  verify PASS 증명                    PR #3 빌드를 로컬에 띄워 실행: ko/en 200 · 30KB/33KB · 제9조/Article 9 · 마커 0 →
                                        PASS. 프로덕션은 FAIL(24/24). 양방향 확인됨
Q6  롤백 SHA                            위 1-6
```

---

## 2. TRACK B — PR #2 정규 릴리스

### 2-1. Merge readiness (2026-09-18 최종)

```
HEAD                   d9eeda4 · 159 ahead of 8a80ea4
LATEST HEAD CI GREEN   YES @ d9eeda4   (run 35306785810: backend 3.12 ✓ 3.14 ✓ frontend ✓)
격리 만료 테스트        만료를 정직하게 기록했는지 + fail-closed 인지 검증하는 테스트로 교체 (d9eeda4).
                       운영 상태 RED · 테스트 GREEN — 나쁜 상태를 정확히 감지한 것이 성공
MAIN-MERGE-READY       기술적으로 YES — 단 TRACK A 가 main 에 먼저 들어가면 base 가 바뀌어 재실행 필수
```

이력: 초판 55b8534(152) → 09da4f3(154) → d9eeda4(159). 각 HEAD 에 CI 가 붙어 있었음을 확인했다.

★ **순서**: PR #3 가 먼저 merge 되면 PR #2 는 base 가 바뀐다. 10커밋 중 7개가 PR #2 에도 있는
커밋(cherry-pick)이고 3개(1f9df88·9f6b8fe·d088e73)는 PR #3 전용이라 충돌보다는 중복이 생긴다 — `git merge origin/main` 한 번이면 정리되고
CI 를 다시 돈다. `strict=true` 라 어차피 재실행 없이는 merge 못 한다.

### 2-2. DB

```
새 리비전 0 · head f3c6a8d0b2e4 = 프로덕션 백업의 alembic_version · DDL 없음
```

### 2-3. 런타임 변화 — ★ "가입 게이트 변화 없음" 정정

| 기능 | 변화 | 사용자 체감 |
|---|---|---|
| **G-3 게시 게이트** | ★ **US 가입: 201 → 451 PUBLICATION_NOT_APPROVED** (8건 DRAFT 인 동안) | **있음 — 신규 가입 전면 중단.** 9/09 (나) 결정 |
| 가입 속도 제한 | 5회/시간 · 인증 20회/분 → 429 | 정상 농가 무영향. 세 클라이언트가 429 문구를 모름 |
| 배경 잡 | 푸시 전건 실패가 성공으로 안 끝남 | 없음 |
| 운영 상태 | `/health/ready` · `/health/ops` 신설, `/health` 불변 | 없음 |
| 가입 게이트 코드 | B-9 — canonical 유지, 중복 제거 | ★ 코드 구조가 같다는 것과 프로덕션 동작이 같다는 것은 다르다 — 위 G-3 행 |

★ **"G-3 를 포함할지"는 선택지가 아니다.** PR #2 를 그대로 merge 해 그 이미지를 배포하면
G-3 는 **들어 있다**. 빼려면 별도 release 브랜치에서 선별해야 한다(TRACK A 가 그 방식이다).
초판의 "배포 여부 — 그리고 G-3 를 포함할지" 는 실제 운영에서 실수를 만드는 문장이라 삭제한다.

```
A  PR #2 전체 배포     → G-3 포함. 신규 가입 중단을 받아들이는 것 (9/09 결정과 일치)
B  선별 release 브랜치 → G-3 제외 가능. 단 그러면 초안 동의 수집이 계속된다 (B-6 모집단 증가)
```

### 2-4. 배포 후 확인

TRACK A 의 §1-4 전부 + 아래:

```
6  KR register → 451 KR_REFERENCE_ONLY
7  US register → ★ 451 PUBLICATION_NOT_APPROVED  (A 를 택했다면 이것이 정답이다)
8  같은 IP 로 register 6회 → 6번째 429 + Retry-After
9  /health/ops → checks 3개 (kpi_snapshots degraded 는 기존 상태, 정상)
10 다음 06:00 UTC 잡 로그에 OK|PARTIAL|TOTAL FAILURE 중 하나
```

---

## 3. 사람이 결정해야 하는 것

```
최우선 (격리 이미 만료 — ACTIVE incident)
  1  PR #3 hotfix — 결재 3·4·6·7 → merge · 배포 · §1-4 검증 · 격리 REMEDIATED 기록
그 다음
  2  PR #2 — base 갱신 후 Ready · merge 판단
  3  PR #2 배포 = G-3 배포 (A) 인가, 선별 (B) 인가
  4  B-10 S3 오프사이트 백업 22일 끊김 — 운영 스크립트 패치 적용
  5  B-5 iOS Debug 호스트 · H13 한 문장 · H17 · 변호사 수신처
  6  main 리뷰 필수 0 → 1
  7  429 안내 문구 3클라이언트 (가입 재개 전)
```

---

## 3-1. 순서 — 여기서부터는 개발이 아니다

```
①  결재 3·4·6·7 실제 결정 확보          (위 양식 7필드)
②  결정 원장 기록                        DECISION_REGISTER · APPROVAL_RECORD
③  PR #3 Ready for review
④  required checks 가 현재 head(4d008a7) 에 GREEN 인지 마지막 확인 — ★ 재실행은 09:00–24:00 KST 에서만 (D9, 아직 main 미반영)
⑤  merge                                ★ merge 는 remediation 이 아니다
⑥  배포 직전 PROD SHA 실측              아래 3-2
⑦  롤백 지점/태그 확인
⑧  API hotfix 배포
⑨  scripts/verify_public_notice.sh
⑩  PROD 마커 0 확인 (5항목 전부)
⑪  KNOWN_PUBLICATION_EXPOSURE → REMEDIATED (양식은 그 문서에)
```

### 3-2. 배포 직전 증거 — 하나라도 어긋나면 중단

```
expected_prod_before   2e372b1
actual_prod_before     <런타임 실측 — 컨테이너 내 파일 sha256 ↔ git show 2e372b1 대조>
release_commit         d088e73 (또는 merge commit)
rollback_commit        2e372b1
rollback_ref           <deploy.sh 가 찍는 롤백 이미지 태그>
db_migration_count     0
```

`actual_prod_before != 2e372b1` 이면 **즉시 중단** — 사이에 다른 배포가 있었다는 뜻이다.

### 3-3. 최종 판정 (2026-09-18)

```
PR #3                    d088e73 · 10 commits · FINAL HEAD CI GREEN · TECHNICALLY MERGE-READY · GOVERNANCE PENDING
PR #2                    d9eeda4 · 159 commits · FINAL HEAD CI GREEN · expiry 를 탐지하면서 GREEN
MAIN                     8a80ea4 unchanged
PROD                     2e372b1 unchanged
PUBLIC EXPOSURE          quarantine-class 48 · including D-xx 64
QUARANTINE               EXPIRED · remediation NOT_DEPLOYED · incident ACTIVE — 연장 안 함
DB                       NO MIGRATION
BLOCKER                  결재 3 / 4 / 6 / 7
```

★ **여기서 개발은 끝난다.** PR #3 에 이후 다른 개발을 섞지 않는다. 다음 상태 전이는 §3-1 ①~⑪ 뿐이다.

## 3-4. TRACK A — FROZEN (2026-09-18)

```
TRACK A   FROZEN — 이 문서와 PR #3 에 이후 어떤 개발도 넣지 않는다. 결재·배포 기록만 덧붙인다
PR #3     d088e73 / GREEN / TECHNICALLY MERGE-READY
BLOCKER   결재 3 · 4 · 6 · 7
PROD      2e372b1 / unchanged
INCIDENT  EXPIRED · ACTIVE · NOT_DEPLOYED
```

다음 개발은 별도 브랜치·트랙: B-10 오프사이트 백업 복구(22일 중단) → 429 3클라이언트 parity → H17 → Feed Intelligence.

## 4. 권고 — 오늘 오전의 **한 단계**

```
결재 3·4·6·7 의 실제 결정을 받는다 (§1-8 C 문안, §3 양식). 그 전에는 merge 하지 않는다.
```

PR #2 는 그 뒤다. 초판이 "PR #2 Ready" 를 첫 행동으로 잡은 것은 48건 발견 전의 판단이었다.

## 3-5. TRACK A — base 갱신 (2026-09-21, 개발 추가 아님)

```
계기        #4 (Anthropic 수탁자 정정) 가 main 에 merge 되어 base 8a80ea4 → ae61369. PR #3 CONFLICTING/DIRTY.
기준        CURRENT BASE ae61369 · CURRENT MERGE-BASE(4d008a7, ae61369) = ae61369 · 3-WAY ANALYSIS BASE 8a80ea4 (구 d088e73 ↔ ae61369 공통조상)
충돌        api/content/legal/public_privacy.{ko,en}.md 각 1 hunk (제3조 ① 표)
해소        문장 단위 — 행 ②~⑤ = PR #3 (D-01/D-02 토큰 제거; main 은 base 와 동일) · 행 ⑥ = main (#4 목적 ⑥ 정정; PR #3 는 base 와 동일)
            제8조 ② Anthropic PBC 행(#4) 자동 병합. ours/theirs 일괄 선택 없음. 양쪽 문안 변경 0.
검증        merged == PR #3 본문 + #4 의 교체 2줄 (바이트 동일, 프로그램 확인) · 마커 V/OPEN/COUNSEL/[ ]/D-xx = 0/0/0/0/0
            manifest 변경 0 (8 문서 DRAFT_LAWYER_PENDING 그대로) · guard 테스트 14 passed
            verify_public_notice.sh 로컬 빌드 PASS (ko 31024B · en 34287B · 제9조/Article 9 · 마커 0)
새 head     4d008a7 (merge commit) · CI run 35553756807 GREEN (11:18 KST, 창 안) · MERGEABLE/CLEAN · draft
동결        이 시점부터 PR #3 커밋 0. Ready 전환만으로는 재실행 불필요(head·base 불변이면 4d008a7 의 GREEN 유효). main 이 다시 움직이면 base 갱신+재실행 — D9 미반영 상태면 09:00–24:00 KST 에서
변경 없음   D9·G4·B-10·429 미반입. 결재 3·4·6·7 문안 그대로. main·프로덕션 변경 0.
```

