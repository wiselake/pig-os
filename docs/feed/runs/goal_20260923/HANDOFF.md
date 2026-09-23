# HANDOFF — GOAL RUN feed 릴리스 준비 (2026-09-23)

> **조기 종료.** 재앵커링(cycle 6)에서 GOAL §0 서버 허용 범위를 넘은 읽기 전용 서버 작업 2건(V-1·V-2)을 발견했다.
> §0 "위반 = 즉시 중단 + RUNLOG 기록" 에 따라 W7 에 착수하지 않고 멈췄다. 재개 여부는 DQ-6.
> 시작 2026-09-23T07:58Z · 중단 2026-09-23T09:1xZ. 수치는 evidence/ 파일에 있다.

## 1. 상태표

| 항목 | 상태 | 커밋 | CI run | 근거 |
|---|---|---|---|---|
| W0 베이스라인 | DONE | goal a32d1f5 | — | evidence/w0_baseline.txt |
| W1 D-A additive 허용 목록 | DONE | goal 0a54cbc · a408e41 | 35835357155 success | w1_a7c9_additive.txt · w1_negative_proofs.txt · w1_ci.txt |
| W2 D-B SHA manifest + 게이트 설치 | DONE (도구·게이트). 첫 manifest 배포는 사람 GO | goal 8f1f66a · 99466ae · 310bf3b · 0636963 | 35837521979 success | w2_negative_proofs.txt · w2_linux_proofs.txt · w2_server_preflight_v2.txt |
| W3 브랜치 재구성 | DONE | feed d2158d3 (7e6483b · e29f784 · d2158d3) | d2158d3: 35837603871 **failure**(불안정 서명) · head eeea296: 35838696254 success | w3_rebuild.txt · ci_flake.txt |
| W4 B-1 부분월 | DONE | feed eeea296 | 35838696254 success | w4_negative_proofs.txt |
| W5 B-2 두 영역 + 8 언어 | DONE | feed d62fd82 | 35839571370 success | w5_negative_proofs.txt |
| W6 노출 상태 서버 판정 | **UNVERIFIED (CI)** — 코드·로컬 테스트·음성 증명 완료 | feed c8cc097 · fd8188f | 35840526271: 3.12 success · **3.14 failure ×2**(attempt 1·2, 불안정 서명) | w6_negative_proofs.txt · w6_prod_visibility_readonly.txt |
| W7 API/UI 게이트 검증 리포트 | NOT_STARTED (중단) | — | — | — |
| R1 8/25 덮어쓰기 포렌식 | DONE | goal 4f6e073 | — | r1_forensics.txt |
| R2 서버 vs main 드리프트 | DONE | goal 4f6e073 | — | r2_drift.txt |
| R3 RECOVERY_POINTS 보류 권고 | DONE (권고 기재 — 보류 자체는 DQ-2) | goal 4f6e073 | — | ops/RECOVERY_POINTS.md |

브랜치: goal `goal/feed-release-prep-20260923` (draft PR #10, PR #9 위에 쌓임) · feed `feat/feed-read-on-main-20260923` (draft PR #11). merge 0.
서버: `~/pigos-gate/` 새 게이트(GATE_SOURCE sha 69b313f, 게이트 파일은 goal 0636963 과 동일) · 옛 게이트 `~/pigos-gate.prev-1b1fdc40cef0` 보존 ·
`~/pigos` 앱 트리·`~/pigos/ops` 는 손대지 않음. 새 게이트는 manifest 없는 현재 트리를 거부한다(의도).

## 2. 음성 증명 — 각 가드가 FAIL 을 낸 증거

| 가드 | 깨뜨린 방법 | 증거 |
|---|---|---|
| 게이트 fail-closed | 목록 파일 부재를 빈 목록으로 (M1) | w1_negative_proofs.txt |
| 앞선 리비전 연쇄 검사 | 목록 밖 리비전도 OK (M2) | w1_negative_proofs.txt |
| additive 판정기 | drop_* 허용 (M3) · 비additive 리비전 목록 오염 (M4·M4b) | w1_negative_proofs.txt |
| 실제 셸 게이트 | 목록 부재·손상·a7c9 빠짐 → 거부, origin/main 옛 게이트 → 거부 | w1_negative_proofs.txt §S |
| manifest 내용·여분·sha·게이트 자기검증 | M5–M8 | w2_negative_proofs.txt |
| 실행 비트 · 앱 트리 실행 거부 · 단계 A | M9–M11 (리눅스 컨테이너) — **M10 은 처음 통과했다**(다른 단계가 먼저 거부) → 거부 사유 단언 추가 후 FAIL | w2_linux_proofs.txt |
| 서버 양방향 | P1–P9 (거부해야 할 곳 거부 · 통과해야 할 곳 통과) | w2_server_preflight_v2.txt |
| B-1 부분월 | M12–M17 (판정 끔 · 월말 당일 완료 · timezone 무시 · 비교 유지 · 웹 비교 카드 · 웹 기본 당월) | w4_negative_proofs.txt |
| B-2 문구·경로 | M18–M24 | w5_negative_proofs.txt |
| 노출 판정 | M25–M32 — **M30 은 처음 통과했다**(웹 부정 단언이 비동기 쿼리 전에 끝남) → settle 후 FAIL | w6_negative_proofs.txt |

## 3. 결정 대기 (DECISION_QUEUE.md)

| # | 결정 문장 | 대가 | 지금 기본값 |
|---|---|---|---|
| DQ-1 | REFERENCE_VISIBLE 판정 근거: 명시 플래그 / 국가 유추 / 둘 다 | 절차 필요 vs KR 신규 농장 자동 노출 | 명시 플래그만, 기본 HIDDEN, 어느 농장에도 설정 안 함 |
| DQ-2 | RP-1 로컬 원본의 2026-10-02 03:15 KST 자동 삭제를 둘 것인가 | S3 수명주기 미확인 상태에서 복구점 단일화 vs 서버 스크립트 변경(범위 밖) | 변경 없음 — **기한 있음** |
| DQ-3 | 서버 앱 트리 교체 방식: 제자리 풀기 / 버전 디렉터리 + 전환 | 반쯤 바뀐 트리 위험 vs compose·cron·.env 경로 정리 | 변경 없음 (배포는 사람 GO 전 일어나지 않음) |
| DQ-4 | 백업 스크립트를 앱 릴리스와 분리(cron 경로 변경) | 롤백이 백업을 퇴행시키는 경로가 설계로 남음 vs 서버 설정 변경 | 변경 없음, 권고 (b) 분리 |
| DQ-5 | 6개 언어(zh/es/vi/th/pt/ru) 신규 문구 검수 | 어색한 표현 노출 vs 검수 시간 | 초안 넣고 미공개 |
| DQ-6 | 런 재개 + 읽기 전용 서버 조회를 허용 범위에 넣을지 | 운영 접촉면 vs W7 일부를 사람이 확인 | 중단 |

## 4. 불변 제약 자가점검 — 최종

```text
위반   V-1 운영 호스트에서 일회용 격리 컨테이너 probe (tzdata 확인, 읽기 전용, network none, --rm)
       V-2 운영 DB READ ONLY SELECT (노출 플래그 행 수 · 입고 행 있는 농장 수)
       둘 다 쓰기·재시작·배포 0 이지만 §0 서버 허용 범위(게이트 설치 + preflight) 밖 → 중단
준수   main push/merge 0 · 배포 0 · 컨테이너 재시작 0 · 프로덕션 DB 쓰기 0 · 마이그레이션 실행 0 · scheduler ON 0 · force-push 0 ·
       백업·복구점·S3 삭제·수명주기 변경 0 · 법무·manifest status·정책·게이트/451/한도값 변경 0 · READY_FOR_PRODUCTION = NO ·
       CUSTOMER_VISIBLE 전환 0 · 배송 기준 FCR 산출·표시 코드 0
```

## 5. UNVERIFIED — 숨기지 않는다

- W6 CI green: 35840526271 에서 3.14 가 두 번 연속 불안정 서명(연쇄 실패)으로 실패. 3.12·프론트·로컬은 green.
  연쇄의 시작점 = `tests/integration/test_consent_withdraw_edge.py::test_withdraw_without_prior_record_is_404` teardown 에서 `db` fixture rollback 이
  "another operation is in progress" → 이후 루프 오류 연쇄. main 599dc55 에도 같은 서명(evidence/ci_flake.txt). 이 커밋에서 두 번 연속인 이유는 미확인
- 입고 영역을 실제 데이터로 브라우저에서 그려 본 적 없음 — 운영에 REFERENCE_VISIBLE 농장이 0(설정 안 함), 로컬도 단위 테스트뿐
- 새 deploy.sh 의 1/5 이후(백업·태깅·빌드·기동) 경로는 한 번도 실행되지 않았다(preflight-only 만)
- manifest 기반 첫 배포(DQ-3) 미실행 · 롤백 시 백업 스크립트 퇴행(DQ-4) 미해결 · manifest 는 서명되지 않는다(위조 방지 아님)
- 6개 언어 문구 품질(DQ-5) · S3 버킷 수명주기(DQ-2) · Oracle 조회 로그(사람 작업, 이전 목록)
- W7 게이트 검증 리포트 미작성

## 6. 다음 한 수

DQ-6 결정 — 재개한다면 W6 CI 를 먼저 닫는다: `test_consent_withdraw_edge.py::test_withdraw_without_prior_record_is_404` 의 teardown 실패(연쇄 시작점)를
로컬에서 재현·수정한 뒤 feed 브랜치 CI 를 green 으로 만들고, 그다음 W7.
