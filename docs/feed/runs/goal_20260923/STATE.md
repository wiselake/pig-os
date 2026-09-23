# GOAL RUN STATE — feed 릴리스 준비 (2026-09-23)

> 매 사이클 시작 시 먼저 읽는다. 수치는 evidence/ 파일을 가리킨다 — 여기에 숫자를 타이핑하지 않는다(SHA·run id 제외).

started_utc        2026-09-23T07:58:22Z   (evidence/w0_baseline.txt 생성 시각 07:59:22Z)
ends_utc           2026-09-26T07:58:22Z   (+72h)
current_item       HALTED (cycle 6 reanchor: V-1·V-2 → DQ-6)
current_cycle      6
last_reanchor      cycle 6 · 2026-09-23T09:02Z — 위반 2건 발견, 중단 (RUNLOG)

## 브랜치
goal 브랜치   goal/feed-release-prep-20260923   base = PR #9 head 9a8aae6 · worktree C:/dev/PigOS-wt-goal · ops(W1·W2)·문서·증거
feed 브랜치   feat/feed-read-on-main-20260923   base = origin/main 599dc55 · worktree C:/dev/PigOS-wt-feed · 코드(W3~W6)
CI           main 대상 PR 에서만 돈다(ci.yml) → 각 브랜치 draft PR 로 run id 확보. merge 0

## 마지막 green
feed d62fd82 · run 35839571370 (W5) · W6 fd8188f run 35840526271 = 3.12 green / 3.14 red ×2 (불안정 서명)
feed eeea296 · run 35838696254 (W3+W4) · PR #11 draft
goal 0636963 · run 35837521979 (W2) · PR #10 draft
goal a408e41 · run 35835357155 (W1)
PR #9 9a8aae6 · run 35824442789 (W0 기준)

## 알려진 환경 제약
CI 불안정 asyncpg 루프 연쇄(기존, main 599dc55 에도) — 실패 시 서명 대조 후 재실행. evidence/ci_flake.txt
CI concurrency: 같은 ref 에서 재실행하면 진행 중 run 이 취소된다
로컬 Node: PATH 앞에 nvm v22.23.2 (시스템 기본 v20 은 vitest 불가)
D9  main 기반 브랜치는 15:00–24:00 UTC 에 시간 경계 테스트가 빨갛다(수정은 PR #2 에만). 그 창의 red 는 D9 여부를 먼저 판정하고 기록
    → CI green 판정은 가능하면 00:00–15:00 UTC 에

## 항목 상태
W0 DONE · W1 DONE · W2 DONE (서버 ~/pigos-gate 설치, 첫 manifest 배포는 사람 GO) · W3 DONE · W4 DONE · W5 DONE · W6 UNVERIFIED(CI 3.14) · W7 NOT_STARTED
R1 DONE · R2 DONE · R3 DONE(권고 기재, 보류 자체는 DQ-2)

## 열린 질문 / 결정 큐
DECISION_QUEUE.md 참조
