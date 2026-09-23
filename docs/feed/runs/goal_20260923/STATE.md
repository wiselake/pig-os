# GOAL RUN STATE — feed 릴리스 준비 (2026-09-23)

> 매 사이클 시작 시 먼저 읽는다. 수치는 evidence/ 파일을 가리킨다 — 여기에 숫자를 타이핑하지 않는다(SHA·run id 제외).

started_utc        2026-09-23T07:58:22Z   (evidence/w0_baseline.txt 생성 시각 07:59:22Z)
ends_utc           2026-09-26T07:58:22Z   (+72h)
current_item       W2
current_cycle      2
last_reanchor      cycle 0 (start)

## 브랜치
goal 브랜치   goal/feed-release-prep-20260923   base = PR #9 head 9a8aae6 · worktree C:/dev/PigOS-wt-goal · ops(W1·W2)·문서·증거
feed 브랜치   feat/feed-read-on-main-20260923   base = origin/main 599dc55 · worktree C:/dev/PigOS-wt-feed · 코드(W3~W6)
CI           main 대상 PR 에서만 돈다(ci.yml) → 각 브랜치 draft PR 로 run id 확보. merge 0

## 마지막 green
goal a408e41 · run 35835357155 (W1) · PR #10 draft
PR #9 9a8aae6 · run 35824442789 (W0 기준)

## 알려진 환경 제약
D9  main 기반 브랜치는 15:00–24:00 UTC 에 시간 경계 테스트가 빨갛다(수정은 PR #2 에만). 그 창의 red 는 D9 여부를 먼저 판정하고 기록
    → CI green 판정은 가능하면 00:00–15:00 UTC 에

## 항목 상태
W0 DONE · W1 DONE (ops 코드; 서버 설치는 W2 와 함께) · W2 IN_PROGRESS

## 열린 질문 / 결정 큐
DECISION_QUEUE.md 참조
