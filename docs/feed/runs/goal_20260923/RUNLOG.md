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
