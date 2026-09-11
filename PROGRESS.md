# PigOS 진행 상황

## [현재상태 2026-09-10] — 법무 P0 게시 게이트 + 환경 결정론화 (로컬 커밋만, **push·배포 0**)

★ **개발이 멈춘 것이지 법무 트랙이 끝난 게 아니다.** 아직 첫 단계 앞이다.

### 프로덕션에서 지금 이 순간 참인 것

```
게시 고지에 미해결 표기 노출     api.pigos.io/legal/privacy — V 11 · OPEN 10 · COUNSEL 1
                                 격리 중, 2026-09-17 로 1차 연장(b2eb30c)
동의 원장                        0행. 지금도 계속 그렇다 (557a347 미배포)
승인 문서                        0건. 마스터·방침·부속조항 8종 전부 DRAFT
초안 동의 수집                   ★ 계속되고 있다. G-3 는 로컬에만 있다 ((나) 결정, 미배포)
국가별 문서 분기                 동작 중 (9/11 API 실측) — US·BR·DE·CL 열림, KR·CN 차단
                                 ★ CL=OTHER 가 부속 없이 열려 있다 — H13 (4) 미배포
KR·CN 차단 법역 기존 계정        존재 (H12)
```

### 이번 라운드에 닫힌 것 (코드)

```
320baea  G-3 게시 게이트 — 미승인 문서에는 동의 자체를 받지 않는다
         가입 진입점 2곳 첫 write 이전 + record_consents 심층 방어
         ★ record_consents 만 막으면 계정이 먼저 생겨 고아 계정이 쌓인다(H11)
587dfed  부분 승인 동작 고정 — US 3종 승인이 OTHER 그룹까지 연다는 사실
f0934c0  차단 안내 8 로케일 — 원문 코드 대신 사유
60c9545  ENV-1 Node 고정 + PREFLIGHT — 환경 실패를 테스트 실패와 분리(exit 78)
8f57d1d  백엔드 로케일 카탈로그 파리티 가드
44ded3f · 6165306   이모지 → lucide + 아이콘 스케일
(9/11)   H13 (4) US 허용목록 — 해석 충돌 10건 xfail(strict) 로 고정, 결재 문장 대기
(9/11)   모바일 T3 — pigos-android b88c571 (451 → 지역 차단 문구) DONE,
         pigos-ios 608b418 (사유코드 뱃지 DEBUG) PENDING_RECHECK(Xcode 없음)
         ★ PLATFORM_PARITY §9-7-1 의 전제 3개가 틀렸음을 §9-7-2 에 기록.
           사유코드→문구 테이블은 D-13·Q-B 답 전이라 만들지 않기로 결정
```

### 사람이 닫아야 하는 것

```
H13  CURRENT_PUBLICATION_SET — (1)/(2)/(3) 택일          Brian  ← 오늘 가능
—    변호사 US 3종 우선 회신 요청                        Brian
H14  게시 언어 BR·TH·VN                                  Brian+변호사 (US 경로면 마감 없음)
H11  원장 없는 기존 계정 처리                            배포 후
```

### 검증

```
백엔드   1456 passed · 1 skipped · 12 xfailed(strict)   (수집 1469, 9/11)
프론트   40 파일 · 219 tests · tsc 통과   (node 22.23.2)
ruff     F841 3건만 (선존)
```

### 진입점

```
docs/legal/DEPLOY_GATE_20260910.md     법무 배포 기준 — G-1~G-6
docs/legal/LEGAL_P0_FREEZE_20260910.md 동결 상태 · 재개 조건
docs/runs/RUN_COMMON_RULES.md          §0 PREFLIGHT · 기준값
docs/PIGOS_SPEC_INDEX.md §1-2          이번 라운드 신규 문서 8종
```

---

## [현재상태 2026-08-25] — 운영 DB 이전(Supabase → EC2 로컬 PG17) + 대시보드 성능 복구
> 장애 대응 세션. 프로덕션 반영됨(DB 전환·인덱스). 코드는 로컬 커밋만, push·배포 미실시.

- **DB 이전 완료**: Supabase 풀러가 쿼리 도중 연결을 끊는 상태(`ConnectionDoesNotExistError`)
  까지 악화 — 앱에서 고칠 수 없어 **같은 EC2 의 PostgreSQL 17(포트 5434)** 로 옮겼다.
  복원 24.7초 / 59테이블·sows 141,359·farms 66·marker `c9f3e5a7b1d4`.
  덤프 목록 대조로 누락 0 확인. 도커 브리지만 ufw 허용(인터넷 비노출), 부팅 자동시작 고정.
  - 실측: 커넥션 획득 **0.001s**(이전엔 절단) · 로그인 17초→**0.34초** · 동시 20 로그인 500 0건
  - 같은 143M 덤프: Supabase **67분 35초** vs 로컬 **29초**
- **대시보드 5.67초 → 0.57초** (`c262f5f`): DB 를 옮기고도 느렸다 — **원인이 둘이었다.**
  `_NPD_SQL` 의 `lact_open` LATERAL 이 모돈마다 `MAX(farrowing_date)` 를 조회하는데
  `farrowings` 에만 `(sow_id, farrowing_date)` 인덱스가 없어 3,691ms 를 썼다
  (matings·weanings 는 2026-07 에 같은 이유로 받았고 farrowings 만 누락).
  NPD 10,251두 5.447→0.269s / 1,508두 2.634→0.056s. 값 불변, 관련 59테스트 green.
- **백업 체계 재구성** (`de4e68d`·`694ff1a`): 대상을 `MIGRATION_DATABASE_URL`(이전 후
  죽은 Supabase) → **앱이 실제로 쓰는 `DATABASE_URL`** 로 뒤집었다. egress 제약이
  사라져 전체 덤프를 매일로 상향. schema 37K / full 143M·30초 / 증분 20K·22초 검증.
- **문서**: `ops/ROLLBACK.md` 로컬 PG 전제로 개정(§E "관리형 자동 백업 없음"이 핵심),
  `docs/INFRA_DB_STRATEGY.md` 전면 개정 — 이전 판이 "비추"로 분류했던 EC2 self-host 를
  택한 것이므로 **포기한 것**(PITR·오프사이트·이중화)을 표로 명시.
- **테스트**: `test_db_pool_budget.py` 가 지키는 제약 교체 — 풀러 15 슬롯 → PG
  max_connections(200)·work_mem 메모리 예산.
- **오프사이트 백업 완료** (`e530dca`): 대표 승인으로 S3 `pigos-db-backup` + EC2 역할
  `pigos-ec2-backup-role` 생성 → 전체·스키마·증분 모두 업로드. 143M 30.8초, SSE AES256,
  객체 크기 149,553,529 = 로컬과 일치. ★ 크론 PATH(`/usr/bin:/bin`)에 aws CLI v2 경로가
  없어 **손으로는 되고 크론에서만 조용히 실패**할 뻔한 것을 `env -i` 실측으로 잡았다.
- **데이터 손실 0 확정**: Supabase 마지막 쓰기 = **08:26:12 KST**, 덤프(09:43)보다 1h17m 전.
  audit_log 기준(`after_dump = 0`)이며, REST 이벤트·오프라인 sync·모돈 등록 **모든 쓰기
  경로가 같은 트랜잭션에 AuditLog 를 남기는 것**을 코드로 확인해 근거로 삼았다.
- **마이그레이션 배포 완료**: `d1a4c6e8b2f5` + `e2b5d7c9a1f3` → marker `e2b5d7c9a1f3`.
  GLOBAL PRIMARY 3 / HIDDEN 11, `compute_enabled` 는 14개 전부 유지(표시만 숨김).
  리졸버 실측: BR 3개(PSY·FARROWING_RATE·NPD, headline=PSY) / 그 외 전부 GLOBAL 3개.
  api·worker 재빌드로 이미지에 리비전을 심어 `alembic current`=`heads` 일치시킴 —
  안 하면 컨테이너 재생성 시 "Can't locate revision" 으로 장애 때 오진을 부른다.
- **복원 리허설 완료** (`ea13fd7`): 143M → 24.1초·ERROR 0, 인덱스까지 복원 확인. 절차는
  `ops/ROLLBACK.md` E-4 에 고정(운영 DB 를 건드리지 않는 방식).
- **⚠️ 남은 것**
  1. **에러 메시지 정형화** — `Server error. Please try again` 이 모든 실패에 동일하게 뜬다
  2. 버킷 수명주기·버전관리 미설정 (매일 143MB 누적, 1년 ≈ 52GB) — 대표 콘솔 작업
  3. S3 **복원 경로** 미검증 — 다운로드가 훅 정책(AWS 조회만 허용)에 막혀 head-object
     크기 대조까지만 함. 다음 리허설 때 실제로 받아봐야 한다
  4. 이중화 부재 — DB 가 죽으면 복구 시간만큼 서비스 정지(RDS 전환 트리거는 INFRA 문서 §5)

## [현재상태 2026-07-23] — 동의 인프라 + KPI PigPlan 정합 + i18n 규칙4 (브랜치 feat/consent-infra, **PR #1 draft push됨, 배포 미실시**)
> 원격 https://github.com/wiselake/pig-os/pull/1 (draft). 11커밋. prod 배포·게시 안 함.

- **글로벌 동의 인프라(consent)** — TERMS_DISPLAY §7 / CONSENT §2·§5: 법역판별(국가+US주)·목적6×법역9 매트릭스 SSOT·consent_ledger(모델+마이그레이션 `d4a1b2c3e5f7`)·약관렌더러(notice_version)·API 4종·온보딩 연결·재고지 배너. **문구 전부 DRAFT placeholder**, 게이팅=기능플래그. 커버리지 `docs/legal/IMPLEMENTATION_COVERAGE.md`. (커밋 5a08bee·01863ef)
- **KPI PigPlan 정합 정정(용암축산 2807 실측)**:
  - `e9a97df` **NPD**: WEI 오표시(≈10일) → **여집합 비생산일수** 정정 + **모돈회전율 신규**. 듀얼리뷰 5개 finding 근본수정(parity≥1 통일·clip·entry클립·PSY캐스트·event기반 open-tail).
  - `6f8e090` **하베스트 orphan 분만 9% 누락 복구**(선행교배 없는 분만 폐기 → 교배 합성) + 타겟 백필. 2807 prod 백필 완료(분만 +469/이유 +465).
  - 실측 대조: **PSY 29.0≈PigPlan 29.1·임신·포유 일치**. NPD 52.7 vs 30.4·회전율 2.29 vs 2.42는 **관례차**(PigPlan=한국 NIAS 항등식, 우리=count/여집합) — deep-research(21소스)로 우리 방식이 US NPPC/SMS·NIAS 표준임을 검증. **역-피팅 금지(위조0)**.
  - 국가별 산식 차이 매트릭스 `docs/specs/COUNTRY_KPI_DEFINITION_MATRIX.md`(Phase B 준비, 미확보=빈칸). 스펙 §3 NPD 재정의 정본화. (9dd393d·e240684·9f94841)
- **i18n 규칙4 완결**: 인라인 딕셔너리 3개(대시보드·forgot-pw·온보딩) → messages 8개어 이관 + 하드코딩 placeholder·aria-label 이관. admin=ko전용(설계) 명시. (0fc7699·811a6a0·3a8546d·a5f66e2)
- **게이트**: 백엔드 unit 418 + KPI integration 56 + consent 17 통과. 프론트 vitest 69/69·tsc·i18n 파리티 8/8.
- **대기(사람 액션)**: consent 국가별 표시 개발(md 문서) / KPI Phase B(국가 1차출처 조사) / PR 머지 / 배포.

## [현재상태 2026-07-02] — DB 무결성/수치 정합성 집중 검증 라운드 (로컬 커밋만, push 미실시)
- **라이브 무결성 배터리 33종**(참조/고아·도메인·상태·미래일·farm 격리): 5건 시드 아티팩트(QA-* gestation=0·사이클없는 LACTATING, 서비스층 우회 직접삽입 — 현재 코드로 재현불가) 外 **위반 0**. 검증층 견고.
- **교차농장 KPI sanity 스윕(96농장)**: 크래시 0. 발견·수정:
  - `0641cb0` **모돈폐사율·도태율 상시 0 버그** — 도폐사 모돈이 소프트삭제라 sows deleted_at IS NULL 집계가 항상 0 → removals 원장 소스로 정정 + 분모 평균재고(스펙 §7).
  - `565642a` **신생/저재고 농장 폭발값 가드** — 평균재고<1이면 연간비율·PSY None(1300% 등 방지). 실데이터 고회전(avg≥1)의 정당한 >100%는 유지.
  - `8184db8` **C2** NPD 도태모돈 이력 포함(deleted_at 필터 제거, 211/249 제외되던 표본 복원) · **C4** 대시보드 분만율을 코호트로 통일(룰엔진과 71.9% vs None 불일치 해소) · **C6** 죽은 v_farm_psy 드롭.
- **보고서↔원시 카운트 대조**: 교배/분만/이유복/이유자돈 **완전 일치**(중복·누락 0).
- **CRUD+권한(RBAC) 계정별 라이브 매트릭스**(role×작업): **권한 홀 0** — WORKER+ 입력/VET·VIEWER 차단/OWNER·org-admin 삭제, 권한상승 양방향 422, 크로스테넌트 403, DELETE 롤백 정상. 경미: 중복 ear_tag 422 vs username 409 불일치.
- **테스트 인프라**: 테스트 DB(create_all)에 KPI 뷰(v_sow_npd)·함수(effective_metric_values) 부재로 get_trend/NPD/get_dashboard가 미검증이었음 → conftest에 생성 추가.
- **게이트**: 백엔드 **814 pass**, ruff clean. KPI 마이그레이션 3종(updated_at 무관, e5c9d1/f7a1c3=NPD뷰).

## [현재상태 2026-07-01] — KPI 수치 정합성 대수술(스펙대로) + 코드리뷰 후속 (로컬 커밋만, push 미실시)
- **KPI/보고서 수치 감사(에이전트 3개, 라이브 실증) → 스펙(`docs/specs/2026-03-19_kpi-calculation-specs.md`)대로 8종 전면 수정**:
  - `1c2a315` **PSY #1**: 대시보드 분모가 '그 해 이유한 모돈수'(v_farm_psy 뷰) → **평균 사육 모돈 재고**(스펙 §1). 라이브 실증: 20두 농장 9/1=9.0 왜곡.
  - `9d86bbd` **PSY #2 트렌드**: 분자 COUNT(이유건수)→**SUM(자돈수)**, 분모 전체sows→**월별 활성재고**(~10× 과소 + 대시보드와 불일치 해소).
  - `5842799` **NPD #3**: 60일 넘게 미재교배한 유휴 모돈이 제외돼 과소·경고무력 → **60일 cap 포함**(마이그레이션 e5c9d1a3f7b8).
  - `fbff9b7` **분만율 #4**: 같은기간 farrowings/matings(다른 개체) → **코호트(110~150일 전 초교배, 교배후폐사 제외)**(스펙 §4).
  - `e0ff0bc` **부분이유 #5·#6**: 이유'건수' 기준 → **복(litter)단위** — avg_weaned/total_weanings/sow_history 정정.
  - `77aacbd` **FCR 대시보드**: 농장전체 사료(record_date)/CLOSED그룹 증체 불일치 → **그룹당 전생애 사료**(스펙 §5, 보고서 경로와 일치).
  - `c276d98` **pwmr_b #7**: 무관한 분만/이유 세트 평균 → **복단위 (tb-weaned)/tb**.
- **테스트 인프라**: 테스트 DB(create_all)에 KPI 뷰(v_sow_npd) 부재로 get_trend/NPD가 미검증이었음 → conftest에 뷰 생성 추가.
- **검증 정합**: 각 수정 TDD(스펙 손계산 테스트→수정→회귀). 백엔드 **809 pass**, ruff clean. 라이브 로그인 E2E 정상(role/system_role).
- **PigOS 각 항목 정상 확인**: PWMR-A·WSI·RTS율·수태율·ADG·비육폐사율·/reports 비육FCR·기간버킷팅·룰 임계값은 감사에서 검증완료(정상).

## [현재상태 2026-06-30] — V&V/UAT 하드닝 라운드 (로컬 커밋만, push 미실시)
- **적대적 버그헌트 → 재현테스트+회귀 게이트 후 1변수=1커밋** 원칙으로 결함 수정 진행 중.
- **이번 라운드 커밋 8건**:
  - `1e0f9d5` #7 이벤트 7테이블 `updated_at` — 오프라인 sync pull이 서버측 수정·소프트삭제 감지(양방향 동기화 누락).
  - `e026320` G4 마스터데이터 제네릭 CRUD 타입/제약 위반 **500→422** + JSONB·ARRAY 손상저장 차단.
  - `913b468` CSV 내보내기 인젝션·필드붕괴 차단(toCsv 이스케이프 + 수식 중화).
  - `6c2d310` record 이벤트 기록 후 모돈 상태/최근이벤트 stale → 쿼리 무효화.
  - `eeb338d` **월마감 잠금 우회 3종**(cull / finisher-group / 분만·이유 PATCH 도착월).
  - `4900815` F1 sync 멱등성 by-id 교차농장 PK → ID_CONFLICT 거부(무성 데이터 손실·PK충돌 차단).
  - `ddc378a` F2 리프레시 토큰 재사용 패밀리 회수(OWASP) + F3 로그인 타이밍 평준화(더미 bcrypt).
  - `08e7732` 양자(cross-foster) 출처/대상 모돈 농장 소속 검증.
- **R2 라운드 추가 커밋 8건**(헌트 3개: KPI/잠금·번식로직·관리자콘솔):
  - `386e010` alert days-overdue 농장 tz 적용(UTC 1일 과소계산) + analytics PRRS 소프트삭제 모돈 분자 제외(>100% 방지).
  - `57dd8a8` cull last_weaned 동일날짜 tie-break 결정성.
  - `0243b36` KPI 알림 승격 시 옛 낮은 심각도 미읽음 supersede(중복 unread 방지).
  - `aa49ca8` **관리자 보안 4종**: pilot 승인 SUPER_ADMIN 발급 차단(권한상승) + 마지막/자기 super_admin 비활성화 락아웃 차단 + 승인 감사에 권한기록 + orgs UUID 500→422.
  - `963cc8d` 프론트 admin 게이트를 백엔드 require_super_admin 기준(system_role)과 일치(half-render 차단).
  - `e1034fc` **F5** 도폐사/종료 시 진행 BreedingCycle FAILED 종료(고아 사이클 방지, cull_sow+apply_terminal 2경로).
  - `e933a08` **F1-F4** 오프라인 sync에 REST 번식 검증 패리티(임신기간 100~130/이유 날짜순서/포유 10~60/국가 이유일령/사이클당 교배상한5/재교배>이유일).
- **게이트 GREEN**: 백엔드 회귀 **790 pass**(py3.14 정식 로컬DB), ruff clean. 프론트 **66 pass**(Node 22.11.0).
- 2라운드(헌터 6개) 결론: **크로스테넌트 누수 P0/P1 0건**(격리 견고). 최대 위험군은 ① 월마감 잠금 우회 ② 관리자 권한상승/락아웃 ③ sync 검증 누락 — 모두 처리.
- 보류(정보성·제품판단, P3/feature-gap): 마스터데이터 도메인검증(음수 등), 일부 alert 임계값 비설정, KPI 스냅샷 잡 미가동 latent, period-lock create/unlock API 부재, rule_config/master 감사 entity_id(문자열PK), 마스터데이터 UI 일부 컬럼, LLM 쿼터 TOCTOU, parity vs cycle.parity divergence.
- **코드리뷰(8파인더) 후속 4커밋**: `0be833a` #1 sync deleted_ids에 repro/health/piglet 소프트삭제 전파(#7 미완성분) · `d60f97b` #4 piglets 날짜이벤트 월마감 잠금 · `bc42ffc` #2 ko 로케일 게이트 system_role 일치 · `b2b4794` #3 admin-org 15키 5로케일 실번역.
- **최종 게이트 GREEN**: 백엔드 **792 pass**, 프론트 **66 pass**, tsc 0, ruff clean. origin/main 대비 **54커밋 ahead**(전부 미푸시).
- 코드리뷰 잔여(사람 판단, 미수정): kpi_service FCR 사료(record_date)·증체(end_date) 윈도우 불일치(기존 latent), master_data `_check_type` 이색타입 방어, sync mating COUNT 중복(cycle.mating_count 존재), 구조 리팩터(sync 검증 인라인 복제→공유 validator, 잠금 분산→공통 enforcement, 전역 SQLAlchemyError 핸들러).
- 제약 유지: push/배포는 사람 명시 승인 시만(현재 push=0), 수치 임의생성 0, 로컬 docker DB만.

## [현재상태 2026-06-24] — Rule Engine 40종 + D1~D4 + 배포준비 + UAT (origin/main 푸시 완료)
- **Rule Engine 8→40종**: 피그플랜 136룰 본문 재검증(handoff/pigplan-rules/) 기반. 번식·자돈·비육·모돈군·웅돈·손실·종합·건강 + 임신감정/MSY/배치. 국가 차등은 seed(default_metric_values, `if country==` 0), AI Insight(LLM Renderer) 7개어.
- **신규 입력기능**: D1 임신감정(pregnancy-check 풀스택+conception.rate_low) · D2 자돈폐사 사유/일령(룰2+mortality 리포트 일령분해) · D3 MSY · D4 배치(AIAO).
- **배포 사전점검**: 블로커 2건 수정(CORS admin 오리진 / NEXT_PUBLIC build ARG), root .env.example, 런북 보강. 실서버 배포는 사람(런북 §0~6).
- **UAT**: live E2E 35/35 · 탐지 라운드트립 테스트(실데이터→탐지→알림 RED) · pytest **485** · ruff/tsc/build green.
- **i18n 7개어**: en/zh/es/vi/th/pt + ko(관리자). 1337키 누락0, th/pt 잔여 ~650키 실번역 완료(잔량 th17·pt51=acronym/코드).
- **모바일**: docs/contract(openapi·catalog·validation-ref) 동기화 + 핸드오프 공지. **origin/main 푸시됨** → 모바일 `git pull` 가능.
- **보류(7월 이후)**: D5(BCS)·D6(치료) = 신규 입력기능(인프라 0, KR 임계값 로드맵 보존). E(전국벤치·크롤러·예측)=네이티브 피드 선행.

## [야간스프린트 시작 2026-06-15 / DB_OK=false (partial)]
- 환경: Cowork 샌드박스(리눅스). Docker/Postgres/psql 없음, root 불가 → 운영 DB·테스트 DB 연결 불가.
- 그러나 시스템 Python 3.10 + `datetime.UTC` shim(/tmp/shim, 저장소 미변경)으로 **import-smoke + unit 테스트 실제 실행 가능**.
- 베이스라인 green: `import app.main` OK / unit **219/219 pass** / ruff clean / `tsc --noEmit` EXIT 0.
- 검증 게이트(이번 스프린트): ruff + tsc + import-smoke + unit pytest. **통합(integration)·Alembic은 DB 필요 → 사용자 머신에서 `uv run pytest tests/` 재검증 필요.**
- 작업 트리 노트: 윈도우 마운트로 ~101개 파일이 CRLF 노이즈로 표시됨. 실제 WIP는 settings/users·login·onboarding·members.ts 4개(사용자 작업, 미변경 유지). 커밋 시 건드린 파일만 LF 정규화 후 add.

## 2026-06-15 야간스프린트 — N1 알림 영구화 Producer (P12-6 백엔드)
- [x] `notification_service.create_from_alerts(db, farm_id, today=None)` — 과기한 모돈(6유형)+도태권고+KPI(WARNING/CRITICAL) → OWNER/MANAGER 멤버에게 IN_APP Notification 적재. KPI 집계 실패는 격리(try/except)하여 과기한/도태 알림은 계속 생성.
- [x] 멱등성: 같은 (user_id, alert_type, related_entity_id) 미읽음 알림 존재 시 재생성 안 함. related_entity_type/id 채워 클릭 이동 가능.
- [x] 수신자: user_farms 조인, 유효역할=COALESCE(role_override, system_role)∈{FARM_OWNER,FARM_MANAGER}, 활성 유저.
- [x] `POST /api/v1/farms/{farm_id}/notifications/generate` (farm_router 분리, require_role OWNER/MANAGER/SUPER_ADMIN) — OpenAPI 등록 확인.
- [x] 통합 테스트 `tests/integration/test_notification_producer.py` (생성/멱등/수신자없음 3케이스) 작성.
- 검증: ruff clean / import-smoke OK / unit 219/219 / 라우트 OpenAPI 등록 확인. **integration은 DB 필요 → 사용자 머신 재검증.** [degraded: no-db]

## 2026-06-15 야간스프린트 — N2 웹 알림 페이지 연동 (P12-6 프론트)
- [x] `lib/api/endpoints/notifications.ts` (list/markRead/markAllRead) + api.types.ts(NotificationItem/ListResponse/MarkReadResult) + queryKeys.notifications.
- [x] notifications/page.tsx: 실시간 KPI 알림 유지 + 영구 알림 섹션(개별 읽음/전체읽음/미읽음 필터/related_entity 클릭 이동/더보기 페이지네이션).
- [x] 배지 unread 연결: Sidebar(/notifications 항목 unread 배지) + Topbar Bell(alertCount=unread, onBell→/notifications) + BottomNav(alertCount=unread).
- [x] i18n 5개 언어 +9키(realtimeSection/savedSection/markAllRead/filterUnread/savedEmpty/unreadBadge/markRead/loadMore/realtimeEmpty). 전수 정합성 873키 일치.
- 검증: tsc --noEmit EXIT 0 / i18n 5×873 일치.

## 2026-06-15 야간스프린트 — N3 Task/알림 잡 자동화 (ARQ)
- [x] `jobs/tasks.py::generate_tasks_job` — 전 활성 농장 순회 → task_service.generate_tasks (멱등). 농장별 오류 격리.
- [x] `jobs/notifications.py::generate_notifications_job` — 전 활성 농장 순회 → notification_service.create_from_alerts (멱등).
- [x] worker.py cron 등록: tasks 05:30 UTC, notifications 06:00 UTC (cron 5개, functions 6개).
- 검증: ruff clean / import-smoke(WorkerSettings 로드·잡 등록 확인) / unit 219/219. [degraded: no-db — 실제 잡 실행은 DB+Redis 필요]

## 2026-06-15 야간스프린트 — N4 PRRS 유전자 성과 추적 (Phase 2)
- [x] 선행 스키마 확인: health_events(disease_code) + sow.breed/breed_company/genetics_id 모두 존재 → 구현 진행.
- [x] `analytics_service.prrs_by_genetics(db, farm_id)` — 품종/유전자 그룹별 전체모돈 × PRRS(disease_code ILIKE 'PRRS%') 집계, 발생률(affected/total*100) 계산, 발생률 내림차순.
- [x] `GET /api/v1/farms/{farm_id}/analytics/prrs-by-genetics` + schemas/analytics.py + main.py 등록.
- [x] 통합 테스트 `tests/integration/test_prrs_analytics.py` (PRRS 집계/비-PRRS 제외/발생률).
- 검증: ruff clean / import-smoke / 라우트 OpenAPI 등록 / unit 219/219. [degraded: no-db — integration은 사용자 머신 재검증]

## 2026-06-15 야간스프린트 — N5 프론트 스모크 테스트 (Phase 13 연장)
- [x] `lib/utils/csv.ts` 공용 CSV 유틸(toCsv/downloadCsv) 추출 + reports reproduction·grow-finish 페이지 연결(동작 동일, 무회귀).
- [x] `tests/utils/csv.test.ts` (toCsv 3케이스), `tests/components/RecentEventsSection.test.tsx` (제목/빈상태), `tests/pages/tasks.test.tsx` (제목/allClear). next-intl 모킹으로 견고화.
- 검증: tsc --noEmit EXIT 0 (리팩터 페이지+신규 테스트 타입 통과). 
- ⚠ **vitest 실행 불가(샌드박스)**: node_modules가 윈도우용 + vitest4 rolldown 네이티브 바이너리가 Bus error(core dumped). 리눅스 바이너리 추가해도 크래시. → **사용자 머신에서 `npm run test` 실행 필요.** [exec-blocked: sandbox]

## 2026-06-15 야간스프린트 — N6 법무 문서 검토·보강 (/legal)
- [x] 이용약관 4→10개 조항 (정의/계정·권한/요금·애드온/소유권vs사용권/데이터수익화·농가배분/금지행위/면책·책임제한/준거법/해지·반출).
- [x] 개인정보보호 4→10개 섹션 (수집항목·방법/목적/제3자·국외이전/보관·파기/이용자권리/쿠키/보안 k≥10/아동/책임자·privacy@pigos.io/GDPR·CCPA·PIPA 요약).
- [x] disclaimer 키 신설 + 페이지 상단 "법무 검토용 초안" 배너. revised→2026-06-15 v2.4. 법적효력 주장 없음.
- [x] 5개 언어(en/ko/zh/es/vi) 동일 키구조·조항수(terms10/privacy10) 동시 작성. 전수 키 정합성 OK.
- [x] docs/legal-review-notes.md (보강 조항/변호사 확정 필요/지역별 추가 검토 5개 시장).
- 검증: tsc EXIT 0 / 5개 로케일 legal.terms·privacy 길이 동일(10/10) / 전체 i18n 키 정합성.

## 2026-06-15 야간스프린트 — N7 QA/QC 종합 + 최종 요약
### 최종 게이트 (전부 GREEN, 회귀 0)
- 백엔드: ruff clean / `import app.main`+`app.jobs.worker` OK / **unit pytest 219/219** / integration 50개 수집(구문) OK.
- 프론트: `tsc --noEmit` EXIT 0.
- i18n: en 기준 **927키 × 5개 언어(en/ko/zh/es/vi) 완전 일치(누락/초과 0)**.

### 오늘 한 일 (N1~N7 전부 완료)
- N1 알림 영구화 Producer(create_from_alerts 멱등) + POST /notifications/generate
- N2 웹 알림 페이지 영구알림 섹션 + 배지 unread 연동 + i18n
- N3 ARQ 잡 자동화(generate_tasks_job 05:30 / generate_notifications_job 06:00)
- N4 PRRS 유전자 성과 추적(analytics_service + /analytics/prrs-by-genetics)
- N5 프론트 스모크 테스트 3종 + CSV 유틸 추출
- N6 이용약관/개인정보보호 각 10개 조항 확장 + 5개 언어 + 검토노트
- N7 종합 QA/QC
- 커밋: STEP0→N1→…→N7 (모두 git push 안 함, 사람이 직접 push).

### 막힌 것 / 환경 제약 (사람 확인 필요)
- **DB 미연결**: Cowork 리눅스 샌드박스에 Docker/Postgres 없음 → integration·Alembic 미실행. **사용자 머신에서 `cd api && uv run alembic upgrade head && uv run pytest tests/` 재검증 필요.** (Python 3.10 + UTC shim로 unit/import는 샌드박스에서 실측 통과)
- **vitest 미실행**: node_modules가 윈도우용 + vitest4 rolldown 네이티브가 Bus error → **사용자 머신에서 `cd src && npm run test` 재검증 필요.** (tsc로 타입은 통과 확인)
- **N6는 법무 검토용 초안**: 변호사 확정 필요(docs/legal-review-notes.md 참고).
- BLOCKED 항목 없음.

### 작업 트리 메모
- 윈도우 마운트 CRLF 노이즈 ~96개 파일 + 사용자 WIP 4개(settings/users·login·onboarding·members.ts)는 **건드리지 않음**. 본 스프린트가 만진 파일만 LF 정규화 후 커밋됨.

### 다음 추천
1. 사용자 머신에서 DB 기동 후 `uv run pytest tests/`(integration 포함) + `npm run test`(vitest) 풀 그린 확인.
2. N2 알림 생성 트리거(N1 endpoint 또는 N3 잡)를 운영 스케줄(ARQ worker)에 배포.
3. N6 법무 초안 외부 변호사 검토 → 준거법/데이터배당/국외이전 확정.
4. N4 PRRS 분석을 프론트 화면(분석 탭)으로 노출 검토.

## 2026-06-15 야간스프린트(품질 순환) — Q1 테스트 엣지케이스
- [x] N1: test_worker_role_not_recipient(WORKER 수신 제외), test_regenerate_after_read(읽음 후 재생성).
- [x] N4: test_prrs_genetics_grouping(동일 breed·다른 genetics_id 분리 집계).
- 검증: ruff clean / 통합 7개 수집 OK. [degraded: no-db — 실행은 사용자 머신]

## 2026-06-15 야간스프린트(품질 순환) — Q2 PRRS 분석 프론트 노출
- [x] `lib/api/endpoints/analytics.ts` + api.types.ts(PrrsGeneticsRow/PrrsByGeneticsResponse) + queryKeys.analytics.
- [x] `/reports/prrs` 페이지: 요약카드(전체/감염/PRRS건수) + 품종·유전자별 발생률 표 + CSV 내보내기.
- [x] Sidebar 분석 그룹에 "PRRS 유전자" 링크(Dna 아이콘) 추가. i18n 5개 언어 prrsReport(15키).
- 검증: tsc EXIT 0 / i18n 942키 5개 언어 일치.

## 2026-06-15 야간스프린트(품질 순환) — Q3 알림 페이지 스모크 테스트
- [x] `tests/pages/notifications.test.tsx` — 제목/실시간·영구 섹션 렌더 + 빈상태(savedEmpty) 스모크. next-intl·navigation·auth·kpiApi·notificationsApi 모킹.
- 검증: tsc EXIT 0. [exec-blocked: sandbox vitest → 사용자 머신 npm run test]

## 2026-06-15 야간스프린트(품질 순환) — Q4 코드 리뷰/리팩터
- [x] **버그 수정(N1)**: create_from_alerts 멱등성 검사를 farm 스코프로 한정(Notification.farm_id == farm_id 추가). 다농장 소유자에게 KPI 알림(related_entity_id=None)이 농장 간 충돌로 누락되던 문제 해결.
- [x] 전체 변경 리뷰 — analytics/jobs/csv 유틸/프론트 일관성 점검, 추가 결함 없음.
- 최종 게이트 GREEN: ruff clean / import OK / unit 219/219 / integration 53 수집 / tsc EXIT 0 / i18n 942키 5개 언어 일치.

### 품질 순환(Q1~Q4) 종료
- 정의된 백로그(N1~N7) + 품질 순환(Q1~Q4) 모두 완료. BLOCKED 없음.
- 재확인 필요(사용자 머신): `cd api && uv run alembic upgrade head && uv run pytest tests/` / `cd src && npm run test` / `git push`.

## 현재 작업
**MVP 스프린트 진행 중** — 디자인 구현 + Rule Engine DB화 완료

## UI Shell 체크리스트

- [x] `globals.css` 라이트 테마 CSS 변수 토큰 (`bg-surface`, `text-text`, `border-border`, `bg-navy` 등)
- [x] `src/components/Sidebar.tsx` — props: `{ lang?, onAskAI? }`, collapsed 내부 state
- [x] `src/components/Topbar.tsx` — props: `{ lang?, onLangToggle?, onQuickInput?, onBell?, alertCount? }`
- [x] `src/components/BottomNav.tsx` — props: `{ lang?, onAskAI?, alertCount? }`, md:hidden
- [x] `src/components/QuickInputDrawer.tsx` — props: `{ open, onClose, lang? }`
- [x] `src/components/AskAiDrawer.tsx` — props: `{ open, onClose, context?, lang? }`
- [x] **7단계: Shell 통합** — `(app)` 라우트 그룹 신설 + 파일 이동 + `(app)/layout.tsx` 작성
  - [x] `src/app/(app)/layout.tsx` 생성 (lang/collapsed/askAiOpen/quickInputOpen 상태 보유)
  - [x] 페이지 8개 `(app)/`로 이동 + 각 페이지에서 `<Sidebar>` + `ml-[220px]` wrapper 제거
  - [x] `Sidebar` 의 `/dashboard` 링크를 `/`로 수정
  - [x] `BottomNav` 의 `/dashboard` 링크를 `/`로 수정
  - [x] `Sidebar` 에서 collapsed 상태를 Shell로 lift-up + `hidden md:flex` 모바일 대응
- [x] **8단계: 검증·커밋** — `tsc --noEmit` 통과 (기존 badge 타입 에러 포함 수정) + commit 완료
- [x] **백엔드 /chat 엔드포인트** 연결 확인 + 프론트-백 타입 계약 완전 일치
- [x] **Record 페이지 리디자인** — Event Flow 레이아웃 (좌: 모돈 목록+검색, 우: 이벤트 드로어), 분만 스테퍼+자동계산+난이도+양자조정
- [x] **Essential 페이지 10종** — /legal, /verify-email, /settings/(profile·billing·delete-account), /announcements, /support, /maintenance, /update
- [x] **Rule Engine DB화** — `default_metric_values`에 warning/critical/direction 컬럼 추가, `effective_metric_values()` 업데이트, KR/US/BR/CN/VN 5개국 시드, base.py 하드코딩 완전 제거, 76/76 unit test pass
- [x] **KPI trend 엔드포인트** — GET /kpi/trend (월별 PSY/NPD/FR), unit 15개 추가, 91/91 pass
- [x] **Weaning 버그 수정** — farrowing_id Optional 처리 + 최근 분만 자동 조회
- [x] **모돈 도폐사 관리** — removals 테이블 + cull_sow (AuditLog 연동) + GET /sows/removals 이력 조회
- [x] **Supabase 운영 DB 마이그레이션** — SQL Editor로 전체 스키마(e3f9a2b4c8d1) 적용 완료
- [x] **번식기록 6종 완성** — 교배/분만/이유/임신사고/도폐사/포유자돈폐사 API 연동 + CullPanel 필드 수정
- [x] **포유자돈폐사 API** — POST/GET /events/piglet_events, farrowing_id 자동조회, AuditLog
- [x] **웅돈관리** — /boars 페이지 + boarsApi 신규, Sidebar 메뉴 추가
- [x] **Sidebar 메뉴 추가** — /record, /kpi, /chat, /boars(웅돈) 추가 (총 10개 메뉴)
- [x] **/farrowing · /reports 페이지** — API 연결 완료 (이전 세션에서 완성됨 확인)
- [x] **Codex 교차검증 체크리스트** — `docs/CODEX_VALIDATION.md` (8개 섹션, P0~P2 우선순위)
- [x] **sync piglet_events 푸시** — SyncChanges.piglet_events + _process_piglet_event()
- [x] **sync removals 풀** — ServerChanges.removals + _pull_server_changes() 보완
- [x] **api.types.ts 보완** — SyncPigletEvent, SyncChanges.piglet_events, ServerChanges.removals
- [x] **/notifications 페이지** — KPI 알림 목록 (CRITICAL/WARNING/INFO/OK 구분, dashboard.alerts 연동)
- [x] **/addons 페이지** — Addon 스토어 (8종 카드, AI Insight Beta + 출시예정 7종)
- [x] **/reports 페이지 강화** — SVG 바차트 + 차트/표 전환, KPI 카드 클릭으로 트렌드 전환
- [ ] **다음**: i18n (5개 언어), 배포 (Vercel/AWS)

## 전략 메모 (월간 보고 포함 대상)

### pigos.io 랜딩페이지
- 아직 미존재 — 별도 Next.js 프로젝트로 신규 생성 필요
- blog-pigos는 블로그 파이프라인, blog-pigsignal은 pigsignal 블로그 (별개)
- 언어: en/ko 우선 출시 → zh/es/vi 순차 추가 (번역 품질 주의)
- 구성: Hero + Features + Pricing + CTA + 시장별 현지화

### SEO / 유입 전략
- 타겟 키워드: "pig farm management software", "양돈 관리 프로그램", "软件猪场管理", "phần mềm quản lý trang trại heo" 등 시장별
- 콘텐츠 마케팅: blog-pigos 파이프라인 활용 가능
- 지역별 검색엔진: 중국(바이두), 베트남/동남아(구글), KR(네이버+구글)
- 결정 필요: 도메인 구조 (pigos.io/ko vs pigos.io?lang=ko vs ko.pigos.io)

## Phase 2 예정 항목

### 다국어 (i18n)
- **랜딩페이지 (blog-pigos)**: en/ko 우선 출시 → zh/es/vi/th/id 순차 추가
  - 필리핀은 영어 공용어라 en으로 커버 가능
  - 번역 품질 주의 (기계번역 그대로 쓰면 역효과)
- **앱 내 언어 확장**: 백엔드 이미 en/ko/es/zh 지원, 프론트 lang 타입은 en/ko만 연결됨
  - zh/es 추가 시: Topbar 토글 드롭다운으로 전환 + 컴포넌트 라벨 번역 필요
  - vi/th는 백엔드 locale 확장부터 필요

## 완료된 스프린트 항목 (MVP)

- DB 스키마 v2.1, Alembic 마이그레이션 (40테이블) 완료
- Rule Engine + Q&A API 완료
- KPI Snapshot 잡 (ARQ) 완료
- 오프라인 동기화 프로토콜 완료
- OpenAPI 3.1 스펙 v1 완료
- Docker Compose 로컬 개발환경 완료
- Next.js 15 프론트엔드 기반 완료
- API Contract 검증 + 수정 완료 (unit 43/43 pass)

## 2026-06-10 (저녁) — 상태 코드 v2 + CRUD 완성
- [x] **모돈 상태 코드 v2** — GILT/OPEN/PREGNANT/LACTATING/ACCIDENT (SCREEN_MENU_SPEC 정렬, Alembic d2a8c5e7f1b3, 건유(DRY) 제거, 웹/모바일 이유 전이 불일치 수정, 테스트 106/106)
- [x] **모돈 수정/도폐사·판매 UI** — 수정 모달 + 도태/폐사/판매/전출 모달 (사유 9종)
- [x] **웅돈 CRUD** — 등록/수정/상태변경 완성
- [x] **/settings 허브 페이지** — 계정/농장/지원/기타 섹션
- [x] **Sidebar 개편** — 공식 로고 + lucide 아이콘 + 그룹핑(돈군관리/기록/분석) + 5개 언어 현지 용어
- [x] **로그인/온보딩 라이트모드** — 공식 로고, 2단 레이아웃, 5개 언어 (기본 ko)
- [x] **Addon 스토어 리디자인** — Data Dividend 히어로 + 카테고리 필터
- [x] **가입 500 해결 검증** — onboarding/complete, auth/register 둘 다 201 실측

## 2026-06-10 — Phase 1 이벤트 입력 검증 (Backend Validators) 완료
- [x] **[P1-1]** `app/validators/base.py` + `__init__.py` — ValidationError(422) 재사용 + 날짜 헬퍼
- [x] **[P1-2]** `validators/farrowing.py` — TB<=35, SB/MUM<=25, BA<=TB, 암수합, 체중<=3.0kg (12 tests)
- [x] **[P1-3]** `validators/weaning.py` — 이유두수 항등식 weaned=nursing-(deaths+out-in) (7 tests)
- [x] **[P1-4]** `validators/mating.py` — 상태 GILT/OPEN/ACCIDENT + 웅돈 순차 (9 tests)
- [x] **[P1-5]** `validators/cross_fostering.py` — 양자 <=25/transfer (3 tests)
- [x] **[P1-6]** `validators/date_rules.py` — 입식/제거 경계 + 교배/분만/이유 순서 (12 tests)
- [x] **[P1-7]** `event_service.py` 연결 — mating/farrowing/weaning/piglet 처리 전 validator 호출
- 검증: unit 134/134 pass (기존 91 + 신규 43). 샌드박스 Python 3.10 + UTC shim 환경.

## 2026-06-10 — Phase 2 모돈 상태 전이 + 알람 (Backend)
- [x] **[P2-1]** `validators/sow_state.py` — ALLOWED_TRANSITIONS 전이 강제 (17 tests)
- [x] **[P2-3]** `services/alert_service.py` — 6 과기한 유형 + 3 도태기준, farm_configs 임계값 (pure classify, 20 tests)
- [x] **[P2-4]** `routers/base/alerts.py` + `schemas/alert.py` — GET /alerts/overdue, /alerts/cull-candidates, main.py 등록
- 검증: unit 171/171 pass, FastAPI 앱 빌드 + 라우트 등록 확인. (P2-2 상태코드 v2는 기완료)

## 2026-06-10 — Phase 3 Rule Engine 확장 (Reproduction Rules)
- [x] **[P3-2]** Finding.grade 필드 + psy_grade 헬퍼(Excellence/Advanced/Stable/Developing), psy.below_target에 부착 (severity는 벤치마크 기반 유지)
- [x] **[P3-1]** `engine/rules/reproduction.py` — wsi.overdue(10/14), rts.rate_high(15/25), pwmr.high(15/20, method A/B), 벤치마크 오버라이드 가능
- [x] **[P3-3]** `tests/unit/test_reproduction_rules.py` — 경계값 17 cases
- 검증: unit 188/188 pass, 규칙 8종 등록 확인.

## 2026-06-10 — Phase 4 프론트엔드 (부분: P4-1/P4-4/P4-5)
- [x] **[P4-1]** `/alerts` 페이지 + alertsApi + 타입 + queryKeys + Sidebar 메뉴 (요약카드/테이블/도태권고, /record 링크)
- [x] **[P4-4]** 대시보드 관리대상 모돈 카드 + /alerts 링크 + 도태권고 건수
- [x] **[P4-5]** QuickInputDrawer 이모지 → lucide-react 아이콘
- 검증: npx tsc --noEmit 통과(EXIT 0). (P4-2 모돈수정모달 기완료, P4-3 상세페이지·P4-6 record 모바일은 후속)

## 2026-06-10 — Phase 7 보고서 API (Reports Backend)
- [x] **[P7-1/2/3]** `services/report_service.py` — 번식(기간 버킷팅: 월/분기/연), 비육(ADG/FCR/폐사율), 모돈 이력(산차별 사이클) 순수 빌더 + DB 래퍼
- [x] **[P7-4]** `schemas/report.py` + `routers/base/reports.py` — /reports/reproduction·grow-finish·sows/{id}/history, >2년 400, main.py 등록
- 검증: unit 199/199 pass, 3개 라우트 등록 확인. (스냅샷 스키마가 얇아 이벤트 테이블 직접 집계)

## 2026-06-10 — Phase 14 Addon #1 AI Insight (LLM Renderer)
- [x] **[P14-1]** `engine/llm_renderer.py` — 벤더 중립, lazy SDK, 템플릿 폴백(키없음/use_llm=False/쿼터초과)
- [x] **[P14-2]** `chat_service.py` — use_llm/usage_count 파라미터 + rendered_by 반환
- [~] **[P14-3]** 쿼터 폴백(within_quota) 구현 완료; 영속 llm_usage_logs 테이블/마이그레이션은 DB 필요로 deferred
- 검증: unit 206/206 pass (외부 API 호출 없음 — 폴백 경로만 테스트)

## 2026-06-10 — Phase 8 설정 페이지 (Settings)
- [x] **[P8-1]** 백엔드 `GET/PATCH /farms/{id}/config/repro` (resolve_repro_config + 범위검증, unit 8) + 프론트 `/settings/farm` 폼
- [x] **[P8-2]** `/settings/benchmarks` — 국가별 KPI 참고표 + 현재 농장 설정값
- [x] **[P8-3]** settings 허브에 번식설정/벤치마크 링크 추가
- 검증: backend unit 214/214, frontend tsc clean

## 2026-06-10 — Phase 11 배포 준비 + Phase 5 i18n 감사
- [x] **[P11-1]** `src/.env.example` + `api/.env.example`에 LLM/Sentry 옵션 키
- [x] **[P11-2]** `src/vercel.json` (nextjs, icn1)
- [x] **[P11-4]** `.github/workflows/ci.yml` (ruff+pytest+tsc+build, PR→development, 수동 배포)
- [x] **[P11-5]** `docs/DEVELOPMENT.md` 로컬 온보딩 가이드
- [P11-3] Dockerfile/compose/`/health` 기존 존재 확인
- [x] **[P5-4]** i18n 키 정합성 감사 — 5개 언어 × 98키 완전 일치(누락/초과 0) 스크립트 검증

## 2026-06-10 — Phase 12 CRUD (백엔드)
- [x] **[P12-1 백엔드]** events PATCH/DELETE (matings/farrowings/weanings) + 상태 롤백(rollback_status_on_delete, 5 tests) + period_locks 423 + 다운스트림 가드
- [x] **[P12-3 백엔드]** finishers PATCH (FinisherGroupUpdate)
- 잔여(프론트): P12-1/2 이벤트 수정·삭제 UI, P12-3 그룹 수정 모달, P12-4 페이지네이션, P12-5 CSV, P12-6 알림 개선
- 검증: backend unit 219/219 (event_rollback 5 신규), 라우트 등록 확인

## 2026-06-10 — Phase 9 보고서 화면 + Phase 12 프론트 API
- [x] **[P9-1]** `/reports/reproduction` — Phase 7 API 연동, 기간 프리셋(3/6/12개월), 월별 테이블(교배/분만/이유/FR/총산/생존산/이유두수/PWMR-A·B/RTS), CSV 내보내기
- [x] **[P9-2]** `/reports/grow-finish` — 그룹별 ADG/FCR/폐사율 테이블 + CSV
- [x] **[P12-5 일부]** 보고서 CSV 클라이언트 내보내기 (BOM 포함 한글 호환)
- [x] **[P12-1/3 프론트 API]** eventsApi update/remove, finishersApi update + 타입
- Sidebar 분석 그룹에 번식/비육 보고서 링크 추가. tsc clean.

## 2026-06-10 — Phase 9-3 / Phase 12-3 프론트
- [x] **[P9-3]** `/finishers` 그룹 수정 모달 추가 (EditGroupModal, finishersApi.update 연동) — 목록/입식/출하/수정 완비
- 검증: tsc clean

## 2026-06-10 — Phase 12/4 프론트 마무리 배치
- [x] **[P12-4]** finishers 페이지네이션 (boars+finishers 완료)
- [x] **[P12-6]** notifications 심각도 필터 탭 (전체/위험/주의/정보)
- [x] **[P4-6]** /record 모바일 상하 스택 레이아웃 (반응형)
- 검증: tsc clean (5개 커밋 연속)

## 2026-06-10 — Phase 12/5/10 연속 배치
- [x] **[P12-2]** 모돈 상세 이벤트 삭제+롤백 UI (eventsApi.remove, 확인 다이얼로그)
- [x] **[P5-2]** 5개 언어 sowStatus i18n 키 (정합성 105키 유지)
- [x] **[P10-2]** 검증 오류 E2E 통합 테스트 7케이스 (수집 OK, Docker DB 실행)
- [x] **[P10-3]** 알람 서비스 통합 테스트 4케이스 (today= 결정적, 수집 OK)
- 통합 테스트는 샌드박스에 Docker Postgres 없어 '수집/구문 검증'까지 — 사용자 머신 `uv run pytest tests/` 실행 필요
- 검증: unit 219/219, tsc clean

## 2026-06-10 — Phase 10 통합 테스트 (4파일 13케이스)
- [x] **[P10-1]** test_full_breeding_cycle — 2산차 상태전이 + 이유두수 가드
- [x] **[P10-2]** test_validation_errors — validator 7케이스
- [x] **[P10-3]** test_alert_service — 과기한/도태 4케이스 (today= 결정적)
- [x] **[P10-4]** test_reports — 번식 월별집계 + 비육 ADG/폐사율
- [x] **[P6-1]** 통합 테스트 기반 (conftest db/client fixture 기존 + 위 4파일 추가)
- 모두 pytest 수집 통과. 실행은 사용자 머신 `cd api && uv run pytest tests/`(Docker pigos_test 필요).

## 2026-06-10 — Phase 9-4 / Phase 5 i18n 완료
- [x] **[P9-4]** Sidebar Alerts 실시간 과기한 배지 (5분 refetch)
- [x] **[P5-1]** alerts i18n 키 5개 언어 (title + 6유형 + 도태)
- [x] **[P5-3]** validation 422 메시지 i18n 키 5개 언어
- 검증: 5개 언어 정합성 123키, tsc clean

## 2026-06-10 — 잔여 일괄 완료 (Phase 6/11/13/14)
- [x] **[P6-2]** vercel.json (P11-2 동일), **[P6-3]/[P11-3]** 프로덕션 Dockerfile(non-root+healthcheck) + dev compose --reload
- [x] **[P14-3]** llm_usage_logs 모델 + 마이그레이션 + usage 서비스 (런타임 쿼터 폴백 기존)
- [x] **[P13-1/2/3/4]** Vitest config+setup+test-utils + 컴포넌트(QuickInputDrawer/Sidebar) + 페이지(alerts) 스모크 테스트
  - ⚠ 샌드박스 npm install 차단(마운트 ENOTEMPTY) → 사용자 머신에서 `npm i -D vitest jsdom @vitejs/plugin-react @testing-library/{react,jest-dom,user-event}` 후 `npm test`
- **자율 플랜 54/54 항목 처리 완료.** backend unit 219/219, tsc clean, 통합테스트 수집 통과.

## 2026-06-16 — 야간 QA/검증 (cowork, 무중단 모드)
- **[야간QA 시작 / DB_OK=true]** — cowork 샌드박스에 Docker 없음 → 루트 권한 없이 `pgserver`(PyPI)로 임시 Postgres 기동, `pigos_test` 생성. psycopg2-binary 번들 libpq 누락은 pgserver의 libpq로 심볼릭링크 해결. Python 3.10뿐(3.14 인터프리터 github 차단)이라 `datetime.UTC` 1개 심으로 백필. 이 조건에서 **전체 테스트 실제 실행 가능**(이전 세션들은 '수집까지'였음).
- 베이스라인 게이트 전부 green: `ruff check` clean / `tsc --noEmit` rc0 / import-smoke(`import app.main`) OK / **pytest tests/ = 289 passed (unit 219 + integration 70)**.
- 주의: 이 실행환경은 py3.10+shim이라 3.11/3.12 런타임 전용 기능이 테스트 경로에 있으면 드러날 수 있음(현재까진 289 green이라 해당 없음). 사용자 머신의 정식 py3.12+docker 검증을 대체하지 않음(보완).

---

## 🌙 야간QA 결과 요약 (2026-06-16, cowork 무중단 모드)

**판정: 기존 구현 견고 — 실제 버그 0건. 회귀잠금 테스트 11종 추가 + 문서 정합 1건.**

### 최종 게이트 (전부 green)
- `ruff check` clean · `tsc --noEmit` rc0 · **pytest tests/ = 300 passed** (베이스라인 289 + 신규 11)
- 실행환경: cowork 샌드박스에 Docker/py3.12 없음 → 루트 없이 `pgserver`로 임시 Postgres + py3.10 + `datetime.UTC` 심 1개로 **전체 통합테스트 실제 실행**(이전 세션들은 '수집까지'였던 것을 실행까지 끌어올림).

### Q1~Q8 수행
- **Q1 인사이트 렌더만 원칙**: InsightBanner.tsx·record/page.tsx 검사 → 위반 0. severity/gap/priority/confidence/loss/relative 전부 백엔드 필드 렌더만. 프론트 판정 로직 없음. (프론트 `severity:"CRITICAL"` 2곳은 AI 호출실패 에러표시용, KPI 판정 아님 — 정상)
- **Q2 인사이트 엔진 엣지케이스**: insight_service.py 정독. 분모0(tb>0 가드)·음수폐사(severity OK→None)·null임계(skip)·글로벌폴백·가격없음·top25없음 전부 안전 가드 확인. `_attach_insights` try/except 격리 확인. → 누락 엣지 7종 테스트 추가(test_event_insight.py).
- **Q3 국가별 임계값**: threshold_service.list_effective/set_override/clear_override + insight_service._load_benchmark 우선순위(농장>국가>글로벌) 일치 확인. 기존 테스트는 글로벌+농장만 커버 → **국가(region) 티어** 검증 2종 추가(region>global·source 귀속·clear시 국가복귀). 시드(f3a7c2e9…) source 귀속 정확(US=PigCHAMP, KR=PigPlan/한돈팜스, region scope).
- **Q4 손실/상대 슬롯**: loss=손실두수×가격, 가격없음 null, 글로벌/저신뢰 demo=true 확인. relative gap 부호 below(기존)+ **above 방향 1종 추가**.
- **Q5 알림/디바이스/Task**: notification_service savepoint(begin_nested) 격리·멱등 확인, push_service graceful skip(미설정 예외0) 확인, device upsert/소프트삭제 확인. 기존 18종 green. → **savepoint 격리(KPI 실패가 과기한 알림 안 막음) 1종 추가**(monkeypatch).
- **Q6 i18n**: en/ko/zh/es/vi **959키 parity 0**, ICU 변수({value}{threshold}{unit}{n} 등) 불일치 0. 수정 불필요.
- **Q7 계약/스펙**: gen_openapi 재생성 → 커밋본과 **diff 0**(66 paths/103 schemas, 라우트 변경 없음 → yaml 미수정). mobile-integration-contract §3는 EventInsight 정확 반영. **누락이던 /thresholds 관리 엔드포인트(GET·PATCH·DELETE) §3에 문서화 추가.**
- **Q8 종합 회귀**: 위 최종 게이트 green.

### 신규 커밋 (6개, push는 사람이)
1. `78117e2` docs(qa): 야간QA 시작
2. `15395f4` test(insight): Q2 엣지 7종
3. `7f7e720` test(threshold): Q3 국가 티어 2종
4. `2e2c825` test(insight): Q4 상대판정 above
5. `a98ffc1` test(notification): Q5 savepoint 격리
6. `b8026b2` docs(contract): Q7 /thresholds 문서화

### 경미한 관찰(버그 아님, 참고용)
- `relative.better=True` 분기는 슬롯이 '경보 있을 때만' 붙으므로 실무상 도달 불가(경보 임계는 항상 top25보다 나쁜 쪽). 사실상 dead path지만 무해.
- `persist_insights`의 멱등키가 `related_entity_id == sow_id`라 sow_id=None이면 IS NULL 매칭 — 현재 모든 이벤트는 sow 보유라 영향 없음.

### ⚠ 사람이 확인할 것
- **DB 재검증 권장**: 본 실행은 py3.10+pgserver 우회환경. 정식 `cd api && uv run pytest tests/`(py3.12 + Docker pigos_test)로 300 passed 재확인 권장(현재까지 동작 차이 징후 없음).
- **[환경 발견] 라인엔딩 churn**: `.gitattributes` 부재로 리눅스 체크아웃 시 워킹트리 ~100개 파일이 CRLF↔LF 차이로 통째 'modified' 표시됨(내 작업 아님). 커밋은 LF·해당 파일만 골라 오염 없이 진행. `* text=auto eol=lf` 등 정규화 정책 검토 권장.
- **[BLOCKED] 없음.**

### 다음 추천 (순환 2회차)
- Q1~Q8 더 깊게: 적대적 입력(거대값/음수/유니코드 ear_tag)·동시성(같은 이벤트 동시 POST 멱등)·라우터 레벨 권한 회귀. 신규 기능은 계속 추가 금지, 테스트·문서 정합만.

---

## 🌙 야간QA 2회차 요약 (2026-06-16, 적대적 입력·동시성·권한)

**판정: 신규 버그 0. 회귀잠금 테스트 4종 추가. 사람 결정 필요 finding 1건(동기화 검증 경로).**

### 최종 게이트
- `ruff` clean · `tsc --noEmit` rc0 · **pytest tests/ = 304 passed** (1회차 300 + 신규 4)

### 수행/추가 테스트
- **C2-Q1 적대적 입력**: REST 생성경로는 견고 — `FarrowingCreate` born_alive/stillborn/mummified `ge=0`, `WeaningCreate` weaned_count `ge=0,le=30`, total_born=합계 후 validator가 >35 차단. sow `ear_tag` max_length=30·parity 0~20·status/entry_type 패턴 가드. → 추가 버그 없음.
- **C2-Q2 멱등**: `persist_insights` 2회 호출 시 미읽음 중복 알림 0 검증(test_event_insight.py::TestPersistIdempotency).
- **C2-Q3 라우터 권한**: `/thresholds` RBAC 회귀 신규(test_thresholds_perm.py) — 워커 override 403·읽기 200·비멤버 403. `require_role`은 user.system_role 기준, `FarmDep`는 멤버십(can_access_farm) 기준으로 동작 확인. 멤버 생성 시 system_role=farm role 동기화(members.py:64-65 주석으로 의도 명시) → 권한 일관.

### ⚠ 사람 결정 필요 (finding)
1. **[중요·동기화 검증 비대칭]** REST 이벤트 생성은 validator(분만 TB≤35/SB·MUM≤25/BA≤TB, 이유 ≤30, ge=0)를 거치지만, **오프라인 동기화 경로(`sync_service._process_farrowing/_process_weaning`)는 카운트 validator를 호출하지 않음**. 또 `schemas/sync.py`의 `SyncFarrowing.total_born/born_alive`, `SyncWeaning.weaned_count`는 `ge=0` 등 범위제약 없는 순수 int. → 비정상 클라이언트가 `/sync`로 음수·과대 카운트를 적재 가능(데이터 무결성 갭).
   - **권고**: sync 경로에서도 동일 validator 적용 + sync 스키마에 범위 제약 추가. 단, 이는 동기화 **계약 변경**(SyncRejected에 신규 사유 추가 + offline-sync-spec 갱신)이라 사람 승인 후 진행 권장. (야간 무단 변경 안 함 — 계약 안정성)
2. **[경미·멀티팜 역할]** 권한 판정 기준인 `user.system_role`은 사용자당 전역값. 한 사용자가 농장A=OWNER, 농장B=WORKER로 서로 다른 역할을 가지면 system_role이 마지막 설정으로 덮여 농장별 차등이 안 됨(MVP는 1유저-주로 1농장 가정이라 현재 영향 적음). 멀티팜 본격화 시 per-farm 역할 기반 require_role 재설계 검토.

### 신규 커밋 (3개, push는 사람이)
- `c445aa2` test(insight): C2-Q2 persist_insights 멱등
- `(직전)` test(thresholds): C2-Q3 RBAC 회귀
- `(이 커밋)` docs(qa): 2회차 요약

### 다음 추천
- finding #1(동기화 검증) 사람 승인 시 1순위 수정. 그 외 적대적 동시성(동일 sync batch 내 중복 id)·report 기간경계(>2년 400) 회귀 추가 여지.

---

## ✅ finding #1 해소 (2026-06-16, 사람 승인 후)

**동기화 검증 비대칭 수정 완료.** 오프라인 `/sync` 경로가 REST 생성경로와 동일한 카운트 검증을 거치도록 보강.
- `sync_service._process_farrowing`: 음수 금지 + `validate_farrowing`(TB≤35/SB·MUM≤25/BA≤TB) → 위반 시 `SyncRejected(reason="VALIDATION_FAILED")`.
- `sync_service._process_weaning`: `0 ≤ weaned_count ≤ 30` → 위반 시 동일.
- **설계 판단**: sync 스키마(`schemas/sync.py`)에 하드 `ge=0`를 넣으면 잘못된 1건이 배치 전체를 422로 떨굼 → 기존 '항목별 graceful reject' 계약 유지를 위해 **프로세서 내부 항목별 검증**으로 처리(새 임계 도입 아님, REST 규칙 미러).
- 계약 문서화: `docs/specs/2026-05-19_offline-sync-spec.md`에 2-8절 + 충돌/에러 표에 `VALIDATION_FAILED` 추가.
- 테스트: `test_sync_validation.py` xfail 제거 → 정상 7케이스(분만 거부3/정상1, 이유 거부2/정상1) 전환.
- 검증: **pytest tests/ = 311 passed**, ruff clean, tsc rc0.
- 잔여(경미): finding #2(멀티팜 전역 system_role)는 미해결 — 멀티팜 본격화 시 재설계 대상.

---

## ✅ finding #2 해소 (2026-06-16, 멀티팜 농장별 역할)

**전역 system_role 기반 권한 판정의 멀티팜 혼선 수정.**
- `permissions.effective_farm_role(user, farm_id, db)` 신규: 농장별 `user_farms.role_override`로 판정. SUPER_ADMIN/조직레벨 롤은 시스템 롤 그대로, 멤버십 없으면 None(거부), role_override NULL이면 시스템 롤 폴백(하위호환).
- `dependencies.require_farm_role(*roles)` 신규(path farm_id 기준). 농장 스코프 라우터 3종 이관: members(create/update), thresholds(patch/delete), notifications(generate). 기존 `require_role`(전역)은 잔존(플랫폼/시스템 스코프용).
- 효과: 한 사용자가 농장A=OWNER·농장B=WORKER일 때 A에선 override 200, B에선 403. 구버전은 전역 system_role(기본 FARM_OWNER)만 봐서 둘 다 통과하던 버그.
- 테스트: `test_thresholds_perm.py::test_per_farm_role_isolation` 추가. 기존 권한 테스트 13종 무회귀.
- 검증: **pytest tests/ = 312 passed**, ruff clean, tsc rc0.

### 야간QA 총괄 (2사이클 + finding #1·#2 해소)
- 누적 커밋: 야간 16개(시작 프롬프트 제외 15). push 미실시(사람).
- 최종: **312 passed**, ruff/tsc green. 발견·수정: 실제 버그성 갭 2건(동기화 검증 비대칭, 멀티팜 RBAC) 해소 + 회귀잠금 테스트 다수 + 문서 정합.
- 남은 권고: 정식 py3.12+Docker 재검증 1회, `.gitattributes` 라인엔딩 정규화 정책.

## 2026-06-17 — 정식환경 후속 (Claude Code, Docker PG + Python 3.14)
cowork 야간 우회환경(pgserver+py3.10+UTC shim) 결과를 정식환경에서 재검증·마무리.
- **A. 정식환경 회귀**: Docker Postgres + Python 3.14에서 전체 pytest **320 passed**(cowork 312 + 신규 8), ruff·tsc clean. py3.10↔3.14 차이 무관.
- **B. 라인엔딩**: `.gitattributes`(* text=auto eol=lf) 추가 — 저장소는 이미 LF였고 churn 차단용. 단독 커밋 `51c3502`.
- **C. sync 검증갭(finding #1 확장)**: SyncMating이 REST MatingCreate 규칙(mating_type AI|NATURAL, mating_number 1..5) 우회 → 항목별 VALIDATION_FAILED 추가. reproductive/piglet은 스키마 pattern으로 검증됨 확인. 테스트 3종. `1dbbdd5`.
- **D. 농장쓰기 RBAC 전수**: 가드 없던 파괴적/설정 엔드포인트(sows cull·delete, finishers delete, events delete×3, farms PATCH×2)에 require_farm_role(OWNER/MANAGER) 적용. 일상입력은 WORKER 유지. RBAC 테스트 5종. `c25f645`.
- **F. 프론트 vitest**: 정식 실행 — alerts 스모크의 next-intl mock 누락 수정 → **7 files / 16 tests 통과**. `88199b6`.
  ⚠ vite8 require(ESM) → Node 22.12+ 필요(22.11은 --experimental-require-module).
- **E. 동시성·경계 회귀**: [선택] 미실시 — 권고로 남김(중복 sync id, 동시 POST 멱등, report 기간경계).
- 누적 미푸시 커밋 다수. push 미실시(사람 확인 후).

## 2026-06-17 — 보고서 고도화 야간작업 (R1~R7, cowork)
> 목표: 피그플랜 "전체농가 품종별 주요생산성적"(146지표) 수준으로 보고서 고도화 + 국가별 KPI 차등 + UI 이모지 정리.
> 프롬프트: docs/cowork-reports-overnight.md. push 금지·DB직접변경 금지·수치 임의생성 금지 준수.

### [R1] 146지표 매핑 (완료, docs-only)
- 레퍼런스 `c:/dev/realtime/전체농가_품종별_주요생산성적_2025.xlsx`에서 openpyxl로 **distinct 지표명 146 전수 추출**(데이터행 159,349). 원본 `docs/specs/_pigplan_metrics_raw.txt`.
- `docs/specs/2026-06-17_pigplan-metrics-mapping.md`: 146지표 4분류 — **① 이미계산 22 / ② 데이터있음·미집계 98 / ③ 데이터부족 26 / 국가차등 Y 41**. 각 행에 PigOS metric/source·식 또는 갭·국가차등·근거.
- 스키마 갭 식별: 생시체중 컬럼 없음(생시체중 7지표 ③), 분만 4구분 없음(farrowing_ease 난이도만), 보정21일체중·재포유·부분이유·후보돈 사육일수 미입력.
- 수치 임의생성 없음(매핑·분류만). 검증: docs-only(코드 무변경 → 테스트 영향 없음).

### [R2] 국가별 KPI 차등 (완료, docs-only)
- `docs/specs/2026-06-17_country-kpi-differences.md`: KR/US/CN/SEA(VN)/LatAm(BR) × 9 KPI를 4축(벤치마크/임계/단위/정의)으로 정리.
- **검증 출처만 사용**: 기존 `f3a7c2e9` 시드(PigCHAMP/PorkCheckoff/Agriness/WEPIG/한돈팜스/PigPlan) 재활용 + KR 2025 신규 실측(xlsx n=456 median: PSY 24.73·분만율 83.19·실산 12.22·이유두수 10.85·WSI 6.30). 원자료 `_pigplan_kr_means.txt`.
- 출처 없는 칸은 전부 "출처 미확보" 빈칸(임의생성 0). MSY 전 시장·정의값(이유일령/포유기간/초교배일령)·모돈도폐사율(KR 정의불일치 의심)은 빈칸/보류.
- 단위: US=lb·그 외 kg(저장 kg canonical). 정정: xlsx '품종'축은 실제 보고서 섹션 → R3 breed분해는 PigOS sow.breed 기반으로 진행.

### [R3] 보고서 API 확장 (완료, backend)
- `build_reproduction_rows` 확장(하위호환 keyword-only): `group_by=period|breed`(sow.breed 버킷), 신규 지표 — total_born_sum/born_alive_sum/total_stillborn/total_mummified/stillborn_rate/mummified_rate/birth_loss_rate(=생시자돈사고율)/mating_1·2·3plus_count/ai·natural_count. 기존 6-positional 호출 무회귀.
- `get_reproduction_report`: Sow 조인으로 breed + stillborn/mummified + mating_number/type 동봉. `/reproduction?group_by=breed` 지원.
- 신규 `GET /reports/production-summary` (ProductionSummary envelope): rows + 농장 country 기준값(`threshold_service.list_effective`→`benchmark_values_from_effective`, 순수변환). 프론트는 비교만(판정 재구현 금지).
- schema: ReproductionRow 확장필드 + BenchmarkValue + ProductionSummary. 공식 `docs/specs/2026-06-17_reports-extended-formulas.md`.
- 검증: **unit pytest 226 passed**(219+7 신규: 사산/미라율·교배분해·breed그룹·benchmark매핑), ruff clean, `import app.main` OK. ⚠ integration(test_reports breed/summary)·DB 검증은 R6 + 사용자머신.

### [R4] 국가 기준값 시드 (완료, 마이그레이션 파일만)
- `api/alembic/versions/b1c2d3e4f5a6_seed_kr_pigplan2025_benchmarks.py`: KR region scope의 PSY/FARROWING_RATE/BORN_ALIVE/WEANED_COUNT/WSI **benchmark_avg를 PigPlan2025 median(n=456)으로 갱신**(target/threshold 기존 PigPlan 확정값 보존). confidence=high, source_ref=PigPlan2025-xlsx-median-n456.
- **검증값만**(R2 근거). 출처 미확보(MSY·CN/VN/BR 일부·정의값·모돈도폐사율)는 시드하지 않음. US/CN/BR/VN은 기존 f3a7c2e9 시드 유지(재시드 안 함).
- ⚠ 운영 DB 직접 변경 안 함 — 파일만. 적용은 사람 `cd api && uv run alembic upgrade head`.
- 검증: py_compile OK, `alembic heads` 단일 head(a8d2f4c6e1b9→b1c2d3e4f5a6) 체인 정상(브랜치 없음).

### [R5] 보고서 프론트 강화 (완료, frontend)
- `/reports/reproduction`: **기간/품종 토글(group_by)** + production-summary 연동 → 국가 **기준값(target) 대비 셀 색상**(녹색=달성/빨강=미달, alert_direction 반영, 비교만·판정 재구현 없음) + 신규 컬럼(사산율/미라율).
- `reportsApi`: reproduction(group_by) + **productionSummary()** 신규. queryKeys 갱신. api.types.ts: ReproductionRow 확장필드 + BenchmarkValue + ProductionSummary.
- CSV: 품종/기간 라벨 + 신규 지표 포함 파일명(`pigos_reproduction_{groupBy}_...`).
- i18n: reproReport +7키(groupByPeriod/groupByBreed/breed/cStillbornRate/cMummifiedRate/benchTarget/benchLegend) **5개 언어 동시**. 전수 parity **1022키 × 5 일치(0 diff)**.
- 검증: `tsc --noEmit` EXIT 0. ⚠ vitest는 환경 제약(PROGRESS N5) → 사용자머신 `npm run test` 재검증.

### [R6] 테스트 + 검증 (완료)
- `tests/integration/test_reports.py` +3: group_by=breed(LY/Duroc 버킷+ai/natural/회차 분해), 사산/미라율(stillborn_rate 6.2·birth_loss 12.5), production-summary 봉투(rows+benchmarks list, 비교만).
- **전체 게이트 GREEN (정식 로컬 DB, Python 3.14)**: `pytest tests/ -q` = **344 passed**(베이스라인 320 + R3/R6 신규), ruff clean, `import app.main` OK, `tsc --noEmit` EXIT 0, i18n 1022키×5 parity.
- ⚠ **vitest 미실행**: 로컬 Node v22.11.0 < 22.12 → `ERR_REQUIRE_ESM`(vite8 require ESM) **startup 에러**(코드 실패 아님). Node 22.12+에서 `cd src && npm run test` 재검증 필요(PROGRESS 2026-06-17 F항과 동일 제약).

### [R7] 이모지 → lucide 아이콘 전면 교체 (완료, frontend)
- 신규 `src/lib/icons.tsx`: SEVERITY_ICON(OK→CheckCircle2, INFO→Info, WARNING→AlertTriangle, CRITICAL→AlertOctagon) + STAGE_ICON(교배→Syringe, 임신→HeartPulse, 분만→Baby, 포유→Milk, 이유→Sprout) **단일 소스로 일원화**(대시보드/kpi 중복 SEVERITY_STYLE 통합).
- 교체 매핑: 🔍→Search, 🔔→Bell, 🚨→AlertOctagon, ⚠→AlertTriangle, ℹ→Info, ✓→Check/CheckCircle2, 🧠→Brain, 💉→Syringe, 🤰→HeartPulse, 🐖→Baby, 🍼→Milk, 🌱→Sprout, 🐷→PiggyBank, 💡→Lightbulb, ⚡→Zap, 🔮/✦→Sparkles, BottomNav 글리프(⊞⬡✦⚙)→LayoutDashboard/PiggyBank/Sparkles/Menu.
- 교체 파일(9): `(app)/page.tsx`, `(app)/kpi/page.tsx`, `(app)/record/page.tsx`, `(app)/sows/[id]/page.tsx`, `components/{Topbar,BottomNav,ui,AskAiDrawer}.tsx`, `app/update/page.tsx`. PipeItem/Step icon prop을 string→ReactNode로.
- 회귀 가드: `src/tests/no-emoji-guard.test.ts` — 핵심 9화면 picto charset 잔존 0 정적 스캔(vitest; e2e/playwright 미구성이라 소스스캔으로 대체).
- 검증: `grep` picto 잔존 **0**(전 .tsx), `tsc --noEmit` EXIT 0. ⚠ 가드 테스트 실행은 Node 22.12+ 필요(vitest 제약 동일).

### 🌙 보고서 고도화 야간작업 총괄 (R1~R7 전부 완료, push 미실시)
- 커밋 7개: R1 `50baaac` · R2 `4f0afc1` · R3 `e993d64` · R4 `e784aef` · R5 `a3893b4` · R6 `61f48c3` · R7 `e1eb783`. (`08bcfbb` worker fix는 본 작업 아님 — 기존 커밋.)
- **최종 게이트 GREEN**: 백엔드 `pytest tests/ = 344 passed`(정식 로컬 DB+py3.14), ruff clean, `import app.main` OK / 프론트 `tsc --noEmit` EXIT 0, i18n **1022키 × 5개 언어 parity 0 diff**, picto 이모지 잔존 0.
- 산출물: 146지표 매핑 + 국가 KPI 차등(검증출처만) + reports API(breed/확장지표/production-summary) + KR2025 시드 마이그(파일) + /reports 프론트(품종/벤치마크/신규컬럼/CSV/5개어) + 통합테스트 + 이모지→lucide 전면교체+가드.
- 수치 임의생성 0(출처 미확보는 빈칸). 운영DB 직접변경 0(시드는 마이그 파일만).
- ⚠ **사람 재검증/적용 필요**: ① `cd api && uv run alembic upgrade head`(b1c2d3e4f5a6 KR 벤치 시드 적용) ② Node 22.12+에서 `cd src && npm run test`(vitest+이모지가드) ③ `git push`(미실시) ④ ③데이터부족 26지표(생시체중·분만4구분·재포유 등)는 스키마 확장 후 차기 작업.
