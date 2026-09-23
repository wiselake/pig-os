# RUNLOG — append only

## cycle 0 · W0 베이스라인 · 2026-09-23T07:58Z
① 질문   무엇이 참이면 W0 가 끝났나? → 기준 SHA 4개와 서버 게이트 파일 sha 가 명령 출력으로 파일에 있고, 로컬 main == origin/main
② 분류   TECH
③ DONE   evidence/w0_baseline.txt 에 origin/main · PR #9 head(+CI run) · core SHA · 서버/main ops sha 가 생성돼 있고,
         로컬 main 의 rev == origin/main 이며 옮기기 전 로컬 main 의 로컬 전용 커밋 수 = 0 (0 이 아니면 옮기지 않는다)
④ BUILD  로컬 main → origin/main (backup ref `backup/local-main-e0286de` 보존) · worktree 2개 생성
⑤ CRITIC 1) 로컬 main 을 옮기며 잃은 커밋이 있나? 2) 서버 sha 가 "지금" 값인가, 캐시인가? 3) 불변 제약 중 가장 가까이 간 것 — 로컬 브랜치 포인터 이동(원격·main push 아님)
⑥ VERIFY 1) w0_baseline "local-only" 줄(rev-list --not --remotes) · backup ref 존재 2) ssh 로 실행 시점에 sha256sum — 같은 파일 3) push 0, 원격 변경 0
         관찰: 서버 ops 6개 sha == origin/main ops sha (evidence 두 블록 대조)
         음성 증명: 해당 없음(새 가드 없음)
⑦ RECORD 커밋 = 이 사이클 커밋 · CI 해당 없음 · 다음 질문: W1 — "DB 가 코드보다 앞설 때 앞선 리비전이 전부 허용 목록에 있으면 통과, 하나라도 없으면 거부" 를 입력별로 어떻게 증명하나

## cycle 1 · W1 D-A additive 허용 목록 · 2026-09-23T08:00Z–08:11Z
① 질문   무엇이 참이면 W1 이 끝났나? → 게이트가 "DB 가 코드보다 앞섬" 을 목록 기준으로만 통과시키고, 목록이 없거나 깨지면 무조건 거부하며,
         그 동작이 실제 셸 진입점에서 확인되고, a7c9 가 목록에 오르기 전에 additive 로 실증됐다
② 분류   TECH (메커니즘은 결정 D-A GO 로 확정 — 목록에 무엇을 올릴지는 코드 실증으로)
③ DONE   입력별: 같음→0 · 미적용→3 · 앞섬+목록 밖→3 · 앞섬+목록(연쇄 포함)→0 · 연쇄 중간 누락→3 · 목록 리비전이 head 아닌 곳에 붙음→3 ·
         루프→3 · head 2개→3 · DB 못읽음(빈값/None)→3 · 목록 손상/중복/부재/인자 누락→3.
         판정기: drop/alter/execute/NOT NULL add_column/기존 테이블 unique index·제약→NOT_ADDITIVE, a7c9→ADDITIVE.
         CI: 목록의 모든 줄이 실제 파일·parent 일치·ADDITIVE 가 아니면 실패
④ BUILD  0a54cbc (게이트·판정기·목록·테스트·ROLLBACK C-0) · a408e41 (음성 증명 기록)
⑤ CRITIC 1) 이 체크가 실패하는 걸 본 적 있나?
         2) CI green 이 "셸 게이트 테스트가 돌아서" 인가 "skip 돼서" 인가? (로컬 win32 에선 skip)
         3) 로컬에서만 참이고 CI/서버에서 다를 수 있는 것 — 허용 목록 경로. 롤백 때 배포되는 옛 트리의 목록을 읽으면 D-A 가 무너진다
⑥ VERIFY 1) evidence/w1_negative_proofs.txt — M1(fail-closed 끔)·M2(연쇄 검사 끔)·M3(drop 허용)·M4/M4b(비additive 리비전 목록 오염) 각각
            대상 테스트 FAIL 확인 후 git checkout 복원·재green. 판정기는 repo 실제 migration 에서도 NOT_ADDITIVE 를 낸다(w1_a7c9_additive.txt §3)
         2) evidence/w1_ci.txt — 기준 run 과 goal run 의 skip 수가 같다 → 셸 테스트 4건이 CI 에서 실행됨. 또 테스트는 CI 환경에서 skip 대신
            assert 하도록 작성(`_CAN_SHELL` 없으면 CI 에서 실패)
         3) check_migration_drift.sh 가 목록을 `$HERE`(게이트 설치 위치)에서만 읽고 경로를 바꾸는 env/인자를 두지 않음(우회 스위치 제거) ·
            실제 .sh 로 옛 트리 vs DB a7c9: 목록 있음→0 / 부재·손상·a7c9 빠짐→3 / origin/main 의 옛 게이트→3 (w1_negative_proofs.txt §S).
            서버 설치 시 게이트를 앱 트리 밖에 둘지는 W2 에서 다룬다
         a7c9 실증: evidence/w1_a7c9_additive.txt (판정기 + 독립 grep + farms FK REVIEW 확인)
⑦ RECORD 커밋 0a54cbc · a408e41 · CI run 35835357155 (head a408e41, success) · draft PR #10
         다음 질문: W2 — "서버 소스가 배포 대상 SHA 와 파일 단위로 같다" 를 무엇으로 증명하고, 게이트 자체가 롤백으로 옛것이 되지 않게 어디에 두나
