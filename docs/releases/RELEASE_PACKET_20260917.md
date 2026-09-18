# 릴리스 판단 패킷 — 2026-09-17 아침 (밤샘 작업 + 오전 정정)

> **목적**: 사람이 **merge 할지, 배포할지만** 판단할 수 있게. merge·배포·가입 재개는 하지 않았다.
> **2026-09-17 오전 정정판** — 초판(55b8534 기준)의 네 가지를 고쳤다: ① HEAD/CI 불일치
> ② 긴급복구를 전체 릴리스에서 분리 ③ "G-3 포함 여부" 표현 ④ 격리 문서 삭제 → 보존.

---

## 0. 한눈에 — 두 트랙

```
TRACK A  긴급복구 (오늘)          PR #3  hotfix/legal-markers-20260917  8 commits  ← ★ 오늘 절대시한
TRACK B  정규 릴리스 (그 다음)     PR #2  safety/pigos-20260916          154 commits

MAIN CHANGED    NO    origin/main = 8a80ea4
PROD CHANGED    NO    애플리케이션 쓰기 0 · DB 쓰기 0 · 배포 0
```

### 왜 나눴나

절대시한이 걸린 문제는 하나다 — **공개 방침의 내부 마커 48건, 격리 만료 2026-09-17 23:59:59 KST**.
그것을 없애려고 154커밋(속도제한·잡 의미론·ops 엔드포인트·B-9·G-3·법무 문서)을 오늘 프로덕션에
넣을 이유가 없다. 마커 제거는 형식 게시(PUBLISHED)가 아니라 **정정 복구(correction remediation)**라
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
```

★ **게이트 변화 없음.** G-3 · rate limit · /health/ops · B-9 병합은 **이 PR 에 없다**.
US 가입 동작은 지금과 같다(201). 마이그레이션 0.

### 1-2. 검증

```
로컬 (Python 3.14 · 빈 PostgreSQL 17)
  소스 마커        ko 0 · en 0
  alembic          빈 DB 에서 head 완주 · head 1개
  pytest tests     1307 passed · 1 skipped   ★ main 기준 트리라 개수가 PR #2 와 다르다
  ruff             clean · 테스트 후 tree clean
CI                 run 35183930189 — §1-4 참조
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
4  전체 detector      [V — · [OPEN · [COUNSEL] · [ ]   네 종류 모두 0, 두 언어 모두
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
2026-09-17  PR #3             PROD 48 → 0  (예정)
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
                                        PR #2 의 만료 테스트는 오늘(9/18) 실제로 FAIL 한다 — 설계대로. 연장하지 않는다
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

### 2-1. Merge readiness — ★ 초판 불일치 정정

```
초판   HEAD 55b8534 · 152 ahead · CI 35076804473@55b8534   ← 패킷을 쓴 시점
실제   HEAD 09da4f3 · 154 ahead · CI 35077436431@09da4f3 GREEN
       PR #2 statusCheckRollup @09da4f3: backend(3.12) ✓ backend(3.14) ✓ frontend ✓
```

두 커밋(189bc6a 패킷, 09da4f3 48건 발견)은 문서만이지만, GitHub 은 SHA 로 본다.
최신 HEAD 에 required check 가 붙어 있는지 확인했고 붙어 있다.

```
CI BASELINE GREEN      YES @ 55b8534
LATEST HEAD CI GREEN   YES @ 09da4f3   (run 35077436431)
MAIN-MERGE-READY       YES — 단 TRACK A 가 main 에 먼저 들어가면 PR #2 를 rebase/merge 해서 다시 봐야 한다
```

★ **순서**: PR #3 가 먼저 merge 되면 PR #2 는 base 가 바뀐다. 8커밋 중 7개가 PR #2 에도 있는
커밋(cherry-pick)이라 충돌보다는 중복이 생긴다 — `git merge origin/main` 한 번이면 정리되고
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
오늘
  1  PR #3 hotfix — merge · 배포 · §1-4 검증 · 격리 REMEDIATED 기록      ★ 23:59:59 KST
그 다음
  2  PR #2 — base 갱신 후 Ready · merge 판단
  3  PR #2 배포 = G-3 배포 (A) 인가, 선별 (B) 인가
  4  B-10 S3 오프사이트 백업 22일 끊김 — 운영 스크립트 패치 적용
  5  B-5 iOS Debug 호스트 · H13 한 문장 · H17 · 변호사 수신처
  6  main 리뷰 필수 0 → 1
  7  429 안내 문구 3클라이언트 (가입 재개 전)
```

---

## 4. 권고 — 오늘 오전의 **한 단계**

```
PR #3 의 CI 결과(run 35183930189)를 확인한다. 초록이면 Ready → merge → api 배포 → §1-4 다섯 항목.
```

PR #2 는 그 뒤다. 초판이 "PR #2 Ready" 를 첫 행동으로 잡은 것은 48건 발견 전의 판단이었다.
