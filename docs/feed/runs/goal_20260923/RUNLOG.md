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

## cycle 2 · W2 D-B 서버 소스 SHA manifest · 08:12Z–08:31Z
① 질문   무엇이 참이면 W2 가 끝났나? → 서버 앱 트리가 배포 대상 커밋과 파일 단위(실행 비트 포함)로 같지 않으면 배포가 거부되고,
         게이트가 앱 트리 밖에서 자기 자신을 검증하며, 서버에서 거부해야 할 상태에서 거부·통과해야 할 상태에서 통과한다
② 분류   TECH (방식은 D-B GO: tarball + manifest). 트리 교체 방식·백업 스크립트 위치는 DECISION → DQ-3·DQ-4, 기본값 = 변경 없음
③ DONE   verify: 일치→0 · sha 불일치/짧은 sha→3 · 파일 변조/누락→3 · 대조 디렉터리 안 여분→3 · 여분 migration→3 · manifest 부재/손상/형식/
         executables 키 누락→3 · 캐시 디렉터리·대조 범위 밖 파일→0 · 실행 비트 상실→3(POSIX).
         verify-gate: 변조/누락/GATE_SOURCE 부재·손상→3. deploy.sh: --expect-sha 없음→2 · 앱 트리 사본 실행→3(APP_TREE) · 위 거부가 각 단계의 사유로.
         서버: 현재 트리→거부 · main 릴리스→통과 · 옛 릴리스(DB a7c9 앞섬)→허용 목록으로 통과
④ BUILD  8f1f66a (manifest·게이트·deploy.sh) · 99466ae (실행 비트 — 서버 preflight 가 찾은 결함) · 310bf3b (거부 사유 단언 — 리눅스 변이가 찾은 공백)
         · 0636963 (절차 문서·DQ-3/4·서버 증거)
⑤ CRITIC 1) 이 green 이 "가드가 켜져서" 인가 "다른 단계가 먼저 거부해서" 인가?
         2) 로컬(Windows)에서만 참이고 서버(Linux)에서 다른 것 — 실행 비트·tar 권한·python3 경로
         3) 불변 제약에 가장 가까이 간 것 — 서버에 게이트 설치(허용: ops 게이트 파일 + preflight). 배포·재시작·앱 트리 변경은 0 인가
⑥ VERIFY 1) 첫 리눅스 변이 실행에서 M10(앱 트리 검사 끔)이 **통과** — 게이트 자기검증이 먼저 거부했다. 거부 사유 단언을 추가한 뒤 M10 FAIL
            (evidence/w2_linux_proofs.txt). 서버 P6 도 v2 에서 APP_TREE 사유로 거부(w2_server_preflight_v2.txt)
         2) 첫 서버 실행(w2_server_preflight.txt)이 실행 비트 결함을 드러냄: 릴리스가 모든 파일을 0644 로 담아 cron 백업 스크립트가
            실행 불가가 될 뻔했다. git 에도 100644 였다 → ops/*.sh 100755 + manifest executables + verify 거부. 서버 v2 P9a/P9b 로 확인
         3) 서버 v2: 게이트는 ~/pigos-gate(앱 트리 밖) 설치, 옛 판은 ~/pigos-gate.prev-1b1fdc40cef0 보존, ~/pigos/ops sha 불변 출력,
            컨테이너 Up 시간 불변, 임시 디렉터리 삭제·시간 스윕 0. 음성 증명 evidence/w2_negative_proofs.txt(M5–M8, 로컬 deploy.sh 매트릭스)
⑦ RECORD 커밋 위 4개 · CI run 35837521979 (goal 0636963 success) · 서버 게이트 GATE_SOURCE sha 69b313f(게이트 파일은 0636963 과 동일)
         CI 사건: 1b1fdc4 run 35836540047 attempt 1 이 3.12 에서 연쇄 실패 → 재실행 통과. main 599dc55 에도 같은 서명 → 기존 불안정(evidence/ci_flake.txt)
         다음 질문: W3 — feed 전용 커밋만 main 위로 옮기고 main 쪽 변경을 되돌리지 않았음을 무엇으로 증명하나

## cycle 3 · W3 브랜치 재구성 · 08:29Z–08:47Z
① 질문   무엇이 참이면 W3 가 끝났나? → 새 브랜치가 origin/main 위에 core 전용 커밋만 얹었고, main 과의 차이가 그 커밋들이 건드린 경로에만 있으며, CI green
② 분류   TECH
③ DONE   옮긴 커밋의 patch-id == 원본 · main 과 다른 경로 ⊆ 옮긴 커밋이 건드린 경로 (차집합 공집합) · 기존 브랜치 force-push 0 · CI green run id
④ BUILD  feat/feed-read-on-main-20260923 = 599dc55 + 7e6483b · e29f784 · d2158d3 (cherry-pick -x, 충돌 0) · draft PR #11
⑤ CRITIC 1) 충돌이 없었다는 것이 "main 변경 보존" 의 증거인가? (아니다 — 조용히 덮을 수 있다)
         2) CI red 가 내 변경 때문인가?
         3) 불변 제약 — 공유 브랜치 force-push
⑥ VERIFY 1) evidence/w3_rebuild.txt: patch-id 3쌍 동일 · 차집합 공집합 · main 에서도 바뀐 파일은 main 쪽 변경 존재 확인 · 새 트리 == 옛 core 트리 끝(diff 0)
         2) d2158d3 run 35837603871 이 3.14 에서 같은 연쇄 서명으로 실패, 3.12 통과(evidence/ci_flake.txt). 다음 커밋 eeea296 run 35838696254 전 job green
         3) feat/feed-engine-v1-core 는 건드리지 않음(새 브랜치 push 만)
⑦ RECORD CI run 35838696254 (eeea296 — W3 내용 포함 head) · 다음 질문: W4 — 진행 중인 달을 비교하지 않는다는 것을 경계 시각별로 어떻게 증명하나

## cycle 4 · W4 B-1 부분월 · 08:32Z–08:47Z
① 질문   무엇이 참이면 W4 가 끝났나? → 진행 중인 달은 값은 보이되 전월 대비가 API 에서 null+사유, 웹에서 비교 UI 0 이고, 기본 기간이 직전 완료월
② 분류   TECH (정책은 B-1 결정 확정)
③ DONE   농장 현지 날짜 기준: 월말이 지나야 완료(월말 당일=진행 중) · 서울 농장은 9/30 15:00Z 에 9월 완료, 같은 순간 UTC 농장은 진행 중 ·
         알 수 없는 timezone → UTC-12 · 부분월: FEED_QTY_CHANGE·FEED_COST_CHANGE = null + partial_period(키 유지) · 0행 달은 값 no_data / 비교 partial_period ·
         /months 에 partial · 웹 기본 = 직전 달(연 경계 포함) · partial → 배지, 비교 카드 없음 · 8 로케일
⑤ CRITIC 1) 이 체크가 실패하는 걸 본 적 있나?
         2) 로컬에서만 참이고 서버에서 다를 수 있는 것 — 운영 이미지에 tzdata 가 없으면 모든 농장이 UTC-12 로 떨어진다
         3) 기존 동작의 결함을 새 테스트가 실제로 잡는가 — `end > date.today()` (서버 날짜·월말 당일 완료 처리)
⑥ VERIFY 1) evidence/w4_negative_proofs.txt: M12(판정 끔)·M13(월말 당일 완료)·M14(timezone 무시)·M15(비교 유지)·M16(웹 비교 카드)·M17(웹 기본 당월) 모두 FAIL → 복원 green
         2) 운영 api 이미지(pigos-api:latest)를 network none 일회용 컨테이너로 띄워 tzdata 존재·ZoneInfo('Asia/Seoul') 확인 (의존성 tzdata>=2026.2)
         3) M13 이 옛 판정(`<`)을 되살리면 월말 당일·UTC-12 테스트가 실패 — 옛 결함을 잡는다
         기존 테스트가 실제 날짜에 기대던 것(8월=완료월)을 모듈 고정 시계로 바꿈
⑦ RECORD 커밋 eeea296 · CI run 35838696254 (success) · MOBILE_PARITY 1-5 · 번역 초안은 DQ-5
         다음 질문: W5 — 입고/급여 두 영역 분리 + FCR 문자열·계산 경로 0 을 소스 스캔으로 강제하려면
