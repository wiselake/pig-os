# HUMAN_INPUT_QUEUE — 사람이 채울 법무 빈칸 (loop 대상 아님)

> 2026-07-23. **이 항목들은 자동 생성 금지(위조0).** 실값·계약·변호사 판단이 필요. 채우면 표기.
> 전체 미결 상세는 `OPEN_QUESTIONS.md`(A~G) 참조 — 이 문서는 **바로 처리할 액션**만 추림.
> 채우는 절차: 값 확보 → 해당 `[OPEN]` 교체 → `SESSION_HANDOFF_ADDENDA_v1.4.md`의 RUN F'(변호사 회신)·RUN R(대리인) 실행.

---

## 0. ★ 마감 있는 것 — 셋 (2026-09-10 정리)

이 문서는 오래 열려 있는 항목이 많다. **마감이 붙은 것만 먼저 본다.**

```
1  H13 결재                    ★ 오늘 가능. 나머지가 전부 이것 뒤에 있다
2  G-3 배포 → (A) 14건          ★ G-3 는 결정된 코드(320baea). 이틀째 미배포 — B-6 참조
                               (A) 는 §8. 문서 완성과 가입 재개의 유일한 출구
                               (모바일 451 은 9/11 해소 — B-1 축소)
3  2026-09-17 격리 만료         ★ H13·회신 둘 다 안 오면
                               "게시 문서 없이 서비스를 계속 열어둘 것인가" 판단
                               세 번째 연장은 답이 아니다
```

### 소유자별 지도

```
Grant 결재      H13 · H14 · H15 · H11 · H12 · H10(기능 매트릭스)
                + P0 5건 배포 승인 (§0-2)
변호사 회신     §3-1 — US 우선 7건으로 좁힌 요청
Brian 실행      §6 — 결정 불필요, 실행만
```

### 0-2. 배포 승인 (Grant)

```
대상   DEPLOY_GATE_20260910.md §5-2 의 sha 5건
       90e1284 · 4a64da8 · e064e60 · f4d9c3f · 557a347
       + 런타임 10건 (마이그레이션 0)
선행   G-1a(대표 — H13·문안 정정) · G-1b(변호사 회신) · G-2(H14, US 경로면 불필요) · 모바일 451
       ★ 2026-09-10 분할. 정정 배포는 G-1a 만으로 가능 — DEPLOY_GATE §6-0
```

---

## 1. 대행 대리인 계약 후 채움 (외부 계약 필수 — PigPlan에 없음, 복사 불가)
| # | 항목 | 위치 | 채울 값 | 게이트 |
|---|---|---|---|---|
| H1 | **EU 대리인(Art.27) 명칭·주소** | `drafts/COUNTRY_ADDENDA/ADDENDUM_EU.md` 제1조1 `[OPEN]` | rep-as-a-service(연 1~3천유로) 계약 후 | EU 출시 게이트 |
| H2 | **UK 대리인 명칭·주소** | `ADDENDUM_GB.md` 제1조1 `[OPEN]` | 위 동일(UK rep) | UK 출시 게이트 |
| H3 | **태국 대리인(§37(5) 무한책임)** | `ADDENDUM_TH.md` + D-09 | 현지 대리인 계약 + Thai SCC | TH 유료·마케팅 게이트 |
> ※ BR·US·KR·CN은 별도 현지 대리인 불요(문서에 근거 기재됨). 컨트롤러=**와이즈레이크(주)**, DPO 문의처=**wiselake@wiselake.ai**(기입 완료).
>
> ✅ **2026-08-25 대표 확인으로 닫힌 항목**
> - `wiselake@wiselake.ai` **실제 수신·운영 확인됨**(v1.3 기입 후 미결이던 운영 확인 종결)
> - 개인정보 보호책임자 = **진교문 / 대표이사 / wiselake@wiselake.ai / +82-31-421-3418**
> - 개인정보 보호 담당부서 = **경영지원팀 / wiselake@wiselake.ai / +82-31-421-3418**
> - **연락처는 조직 메일 하나로 통일**(2026-08-26 확정). PIPA §30 은 '연락처'를 요구할 뿐
>   개인 이메일을 요구하지 않는다 — 담당자 변경 시 방침 개정 불요, 공개 문서에 개인
>   이메일 비노출, 부속조항 6벌·권리행사 창구와 동일 주소.

## 2. 대표(사업) 결정 — DECISION_REGISTER OPEN
| # | 결정 | 상태 |
|---|---|---|
| H4 | D-05 글로벌 최소 코호트 k값(기본10/세분20 후보) | OPEN — 변호사+통계 검증 후 |
| H5 | D-06 KR 코호트 5→글로벌 상향 통일 여부 | OPEN |
| H6 | D-07 중국 진입 구조 | **HOLD**(현지 법무 필수) |
| H7 | D-08 베트남 / D-09 태국 출시 게이트 조건 | OPEN |
| H8 | D-12 데이터 수익 배분(농장 share) 약관 포함 여부 | OPEN(사업 결정) |
| H9 | D-13 controller/processor 역할 확정(처리유형별) | OPEN — 변호사 |
| H10 | D-15 유료/무료 경계 확정 | OPEN(사업) |
| H11 | **원장 없는 기존 계정 처리** — 프로덕션에 동의 원장 0행인 계정이 이미 있다. 전면 차단 / 다음 로그인에서 동의 수집 / 유예 중 무엇인가 | OPEN(사업+법무) — `LEGAL_P0_MANDATORY_CONSENT_LOGIN_GATE.md` |
| H12 | **차단 국가 기존 계정의 로그인 허용 여부** — KR 5건·CN 계정은 `signup_blocked` 이지만 로그인은 막히지 않는다. 막으면 레퍼런스 사용이 끊긴다 | OPEN(대표) — 같은 문서 |
| H13 | **CURRENT_PUBLICATION_SET** — 로그인 동의 게이트가 '무엇에 대한 동의'를 요구할지의 선행 결정. 승인 문서가 없으면 게이트를 켜는 순간 아무도 로그인할 수 없다 | OPEN(대표+법무) — `KNOWN_PUBLICATION_EXPOSURE.md` 해소 조건과 동일 |
| H14 | **게시 언어 세트** — 공개 개인정보 처리방침이 **ko·en 뿐**이다(`public_notice.py`). 법정 요건은 BR `pt-BR`(부속조항 제8조가 포어를 정본으로 지정)·TH `th`·VN `vi` 이고, 정작 게시 언어에 있는 KR 은 PigOS 비대상(A-rule)이다. **언어 세트가 법역 정책과 반대로 붙어 있다** | OPEN(대표+법무) — **H13 `CURRENT_PUBLICATION_SET` 의 입력**. 별건으로 처리하지 말 것 |
| H15 | **프론트 `ru` 로케일 노출 유지 여부** — UI 는 러시아어 8번째 로케일을 제공하는데 백엔드 룰 엔진·AI 답변은 ru 미지원(의도)이다. 사용자는 UI 가 러시아어면 **서비스가 지원된다고 읽는다** — 마스터 제10조③ 미지원국 취급과 어긋난다. V16 국가 분포에 RU 유입은 없었다 | OPEN(대표) — 유입 재확인 후 프론트에서도 내리는 쪽이 정합적 |
| H16 | **버전 전이 분류표** — `notice_version` 의 어느 전이가 중대변경(재동의)이고 어느 것이 고지만으로 족한가. `0.1-draft → 1.0` 은 전원 재동의가 자명하나, 그 뒤 `1.0 → 1.1` 부터는 목적별로 갈린다(마스터 :42 3단 구조). 재동의 화면·서버 비교 계약이 이 표 없이는 판정 필드를 가질 수 없다 | OPEN(대표+법무) — `LEGAL_P0_MANDATORY_CONSENT_LOGIN_GATE.md` 구현 메모. H11 과 한 쌍 |
| H17 | **pigos.io 공개 방침·약관 두 벌** — `pigos.io/privacy`(5/30 자 한국어 구본)·`/terms`(피그플랜 문안)가 정적 서빙 중이고 푸터 5곳이 거기로 간다. 격리 정본은 `api.pigos.io/legal/privacy`. (a) /privacy·/terms → /legal/* 리다이렉트(격리본이 공개 사이트에도 노출됨) (b) 구본 내려 안내문만 (c) 승인까지 유지 | OPEN(대표+법무) — `KNOWN_PUBLICATION_EXPOSURE` "격리 밖 노출". ★ 지금 노출 중 |
> D-01~D-04는 조건부 BUSINESS_APPROVED(2026-07-21) — 변호사 반대 시 자동 REOPEN.

## 3. 변호사 회신 필요 ([COUNSEL] — LAWYER_BRIEF 30건 요지)
- US: LB525 전자동의=express written 충족 여부(Q8)·데이터브로커 등록(Q4)·CAN-SPAM 주소(Q19)·CA ADMT/위험평가(Q23)·DOJ Rule(전용 Q 없음 — §1 리스크표) — ★ 2026-09-10 Q번호 정정
- EU/GB: 대리인 확정·DPO 해당성(Art.37)·LIA 승인·쿠키 CMP UI·회원국 언어
- BR: SCC 전문 편입·역할 매핑(F1 exporter 주체)·F3 완전익명 Art.12/33 제외 여부
- 공통: D-01~D-04 조건부 승인의 법무 확인
> 전문: `LAWYER_BRIEF.md`. 회신 오면 RUN F'로 반영.

### 3-1. ★ US 우선 회신 요청 — 좁힌 7건 (2026-09-10)

**30건 전건을 기다리면 몇 주다.** US 를 먼저 여는 경로에 필요한 것만 남긴다.

```
1  미해결 표기가 남은 방침을 공개 게시 중인 상태의 위험
   즉시 내릴 것인가, 정정 게시로 충분한가
   ★ 지금 이 순간 api.pigos.io/legal/privacy 에 노출 중 (V 11 · OPEN 10 · COUNSEL 1)

2  US 만 무료 가입을 여는 데 필요한 최소 문서 세트
   MASTER_TERMS + GLOBAL_PRIVACY_NOTICE + ADDENDUM_US 로 되는가

3  D-01~D-04 이견 여부
   국가별 익명통계 분기 · ③④⑤ 옵트인 · 20년 보유 삭제 · 소급회수 한정

4  controller / processor 역할 확정 (D-13)          ← H9 와 동일 건

5  BR SCC 전문 편입 없이 파일럿 가능 범위

6  동의 기록 0건인 기존 가입자
   사후 수락으로 되는가, 계약 성립 자체를 다시 봐야 하는가   ← H11 의 법률 측면

7  ★ US 승인이 OTHER(부속조항 없는 전 국가)까지 여는 구조
   그대로 열어도 되는가
   근거: DEPLOY_GATE_20260910.md §6-3 — MASTER+PRIVACY 승인만으로
   MX·CL·CO·JP 등이 함께 열린다. 게이트가 틀린 게 아니라 설계대로다
```

★ 4·6 은 기존 H9·H11 과 같은 건이다. **새 항목이 아니라 회신 우선순위를 붙인 것.**

★ **발송본은 `COUNSEL_REQUEST_US_FIRST_20260910.md` 다** (2026-09-10 검토 반영: 7번을 변호사 질의 B-8(a) / 대표 결재 H13 로 분리 · 6번에 B-4 (c) 복원 · 1번에 App Store URL·/legal/terms 부재 명시 · Q번호 매핑 정정 · 회신 기한 9-17 · LAWYER_BRIEF §5 형식 축약). 위 7줄은 요지이고 정본은 그 문서다.
★ 국가별 미결 종결 시트: `closure/README.md` (COMMON · US · OTHER · BR · EU · GB · TH · VN · KR · CN).

## 4. 사업조건 placeholder (임의 확정 금지 — 8건)
- 크레딧·환불·SLA·최소액·취소·세금 등 (`OPEN_QUESTIONS.md` §B). 확정 전 약관에서 제외 또는 `[OPEN]`.

## 5. 게시 전 문서/검증 (loop 아님)
- SCC 전문(BR/TH) · LIA 최종(변호사 승인) · F5 KR 게시본 상충 실사 · V1 동의 UI·로그 실사.

---

## 6. Brian 실행 — 결정 불필요 (2026-09-10)

결재가 아니라 **실행만 남은 것들**이다. 이 문서의 다른 절과 성격이 다르므로 분리한다.

| # | 항목 | 왜 막혀 있나 | 푸는 것 |
|---|---|---|---|
| B-1 | ~~모바일 2개 저장소 451 처리 확인~~ → **iOS 608b418 빌드 1회** — ★ 2026-09-16 `safety/ios-20260916` push 됨. iOS CI 는 `push: main` 트리거라 safety 브랜치로는 안 돈다. Mac 빌드 또는 main merge 시 | Android `b88c571` DONE. iOS 는 커밋됐으나 컴파일 0회 — Xcode 없음, push 금지라 CI 도 안 돈다 | push 승인 1회 (CI macos-15 가 빌드·테스트) 또는 Mac 빌드. ★ **배포를 막지는 않는다** — §9-7-2 |
| B-6 | **초안 동의 원장 집계 — 두 번, 결정일로 나눠서** | 프로덕션 읽기 — EC2 세션. `terms_renderer.py:40` 이 `…@0.1-draft` 라벨을 남기므로 모집단이 원장에 찍혀 있다 (`eligibility.py:119`). `accepted_at` 은 `consent_service.py:317` | ★ **EC2 한 세션 다섯 번째 줄**. SQL 은 아래. **G-3 배포 직전 1회(의사결정용) + 배포 직후 1회(확정 모집단 — 게이트가 동결선)**. 배포 전 숫자는 배포 시점엔 옛 값이다 |

```sql
-- B-6. 9/09 이전 = 유산, 9/09 이후 = 결정 (나) 이후 집행 지연분. 경위가 다르다
SELECT notice_version,
       count(*) FILTER (WHERE accepted_at <  '2026-09-09') AS before_decision,
       count(*) FILTER (WHERE accepted_at >= '2026-09-09') AS after_decision,
       count(*) AS total
FROM consent_ledger
WHERE notice_version LIKE '%-draft%'
GROUP BY notice_version ORDER BY total DESC;
```

★ **순서 정정 (2026-09-11)**: G-3 배포가 (A) 14건보다 **앞선다**. G-3 는 9/09 (나) 로
결정된 승인 코드(`320baea`)인데 이틀째 미배포이고, 그동안 프로덕션은 결정이 하지 말라고
한 일(초안 동의 수집)을 하고 있다. 문서를 채우는 동안에도 모집단은 는다. G-3 가 켜지면
CL 포함 전 국가가 DRAFT 동안 닫히므로 H13 의 "열린 문" 급박성도 흡수된다 — H13 한
문장은 xfail 10건·결재문 정합성 문제로 돌아간다. 배포 자체는 §0-2 승인 + §5-3 롤백
번들이 필요하다. 개발 세션은 배포하지 않는다.

| B-7 | **FCR 을 실제로 본 농장 수** — D-15 기울기 측정 | 프로덕션 읽기 — EC2 세션 **여섯 번째 줄**. 계측(F-0005)이 0 이라 "본" 것은 못 세고, "FCR 이 None 이 아니었던 농장"(CLOSED 그룹 + 귀속 사료 보유)을 센다. 집계만, PII 0 | `SELECT count(DISTINCT g.farm_id) FROM finisher_groups g JOIN feed_records fr ON fr.group_id=g.id WHERE g.deleted_at IS NULL AND fr.deleted_at IS NULL AND g.end_date IS NOT NULL AND g.head_count_out IS NOT NULL AND g.avg_exit_weight_kg IS NOT NULL AND g.avg_entry_weight_kg IS NOT NULL;` 이 수가 0 이면 (a)/(b) 는 다시 대칭이다. ★ **그리고 0 이면 D-15 보다 큰 게 나온다** — CLOSED 그룹 + 귀속 사료를 가진 농장이 지금까지 없었다는 뜻이라, 사료 트랙은 "있는 데이터로 지표를 만드는" 분석 프로젝트가 아니라 **입력 경로 프로젝트**(feed_type↔단계 매핑 · measurement_basis · entry/exit weight 수집)가 된다. F-0011 PHASE 1 계약 설계에 더 투자하기 전에 이 숫자를 본다 — 같은 세션이니 **⑥을 ⑦보다 먼저**, 또는 한 번에 |
| B-8 | **백업 복구 리허설** — 복구해본 적 없는 백업은 백업이 아니다 | `~/pigos-backups/` 와 S3 `pigos-db-backup` 이 있으나 복원 실행 기록 0 | EC2 세션 **여덟 번째 줄**: 최신 덤프를 빈 DB 에 `pg_restore` → `alembic current` == head 확인. V-11 조건 6 과 같은 폴더. 프로덕션 DB 에 쓰지 않는다 — 별도 DB 이름 |
| B-9 | **RESOLVED (2026-09-16)** — canonical = `eligibility` 파사드. Lou 구현은 **테스트만** 흡수(`tests/unit/test_signup_gate_absorbed.py` 16건), 프로덕션 코드 복사 0. `8a80ea4` 는 origin 에 **보존**(revert·force-reset 하지 않음) — 금지기간 main push 사실도 감사 기록으로 남긴다. 남은 것은 main↔safety 3파일 conflict 해소 후 PR base 를 main 으로 복원 → CI 재실행 → 그 GREEN 에서만 merge 판단. ★ 그 뒤 즉시 **main branch protection** (direct push 금지 · PR required · CI required · force push 금지) — 안 걸면 같은 일이 반복된다 | 원래 항목 ↓ |
| ~~B-9~~ | ~~**origin/main 이 갈라져 있다 — 가입 게이트 구현 둘 중 하나를 골라야 main merge 가 된다** | `8a80ea4` (author Lou <ahnyj1229@gmail.com>, committed 2026-09-10 11:20 KST, **pushed by foes88 2026-09-10 11:23 KST** — push 금지 기간 중) 가 origin/main 에만 있다. 내용: `jurisdiction.signup_overrides · resolve_for_signup · assert_signup_allowed` + `auth_service.register/complete_onboarding` 진입 게이트 + `test_signup_gate` 16건. safety 브랜치는 같은 목적을 `eligibility.assert_country_entry_allowed`(LEGAL-P0-CONSENT-AUTHORITY 파사드) + G-3 + H13 허용목록으로 이미 구현. 세 파일 충돌(consent_service · jurisdiction · test_consent_record_context) | ★ 권한 게이트라 개발이 임의로 해소하지 않는다(STOP 규칙). 권고: safety 쪽(eligibility 파사드)을 정본으로, Lou 의 16 케이스는 eligibility 로 옮겨 보존. 누가 9/10 에 main 에 push 했는지는 기록만 — CI 는 그때도 안 돌았다(트리거 부재)~~ | ~~권고~~ → 위 행으로 해소 |
| B-5 | **iOS Debug 빌드 호스트 결정** — `Debug.xcconfig` 가 34130df 이후 `api.pigos.io` 를 가리킨다. 주석·문서 7곳은 여전히 localhost 라고 적혀 있다 | 34130df 의 의도 미기록 — 되돌리면 그 용도가 깨질 수 있다 | (가) 34130df 되돌림 **← 두 세션 권고**: env 를 잊으면 (가)는 연결 실패로 보이고 (나)는 프로덕션에 계정이 조용히 생긴다 / (나) 문서 7곳 현실화. **확인할 한 줄**: 왜 Release 가 아니라 Debug 를 바꿨나. **공통·B-5 전에 가능**: `MAC_VERIFY_CHECKLIST:36` 에 `PIGOS_API_BASE_URL` env 필수 명기. 확정 후 Debug 기대값 단위 테스트로 고정. `PLATFORM_PARITY` §9-7-3 |
| B-2 | `pigos_ro` 읽기 전용 롤 생성 | 프로덕션 권한 변경 — 개발 범위 밖 | `KPI_K_LOOP` P-1. SQL 은 그 문서에 완성돼 있다 |
| B-3 | K-2d 확정 통보 (115일 폐사 제외 삭제) | 값이 내려가는 정의 변경 | `KPI_K_LOOP` P-2 |
| B-4 | 9/17 전 판단 | — | 격리 3차 연장 대신 "게시 문서 없이 열어둘 것인가" |

★ **B-2·B-3 은 KPI 트랙이고 법무와 별개다.** `KPI_K_LOOP` 는 `READY_BUT_BLOCKED` —
착수한 적 없다. B-1 은 2026-09-11 Android 쪽이 닫혔고 iOS 는 빌드 1회만 남아 배포 선행조건에서 빠졌다. B-5 는 배포가 아니라 **수동 검증 절차**의 선행조건이다.

---

## 8. ★ 약관 완성 입력 — 변호사 없이 갈 때 비는 칸 (2026-09-11 실측)

`publish_candidate` 8건(ko) + en 8건의 미기입 마커 전수. **글이 아니라 사실값이 비어 있다.**
각 파일 3행의 범례 표기는 제외했다.

### 8-0. 규칙 — 값은 본문보다 먼저 DECISION_REGISTER 로 간다

```
값 수령 → docs/legal/DECISION_REGISTER.md 에 일자·결정자·값 기록
       → publish_candidate 본문은 그 행을 참조해 채운다 (같은 커밋)
       → "승인 전 본문 편집 금지"는 이 절차로 대체된다 — 규칙을 푸는 게 아니라 안전장치를 바꿔 다는 것
```

없으면 6개월 뒤 14개 보유기간 중 어느 것이 결정이고 어느 것이 초안 잔여물인지 구분할 수 없다.

### 8-A. 운영·사업 확정 — 대표만 정할 수 있음, 변호사 불요 (14)

| # | 위치 | 비는 값 |
|---|---|---|
| A-1 | 방침 제9조 :141 | 계정정보 — 법정보존 외 보유 기준 |
| A-2 | 방침 :145 | 탈퇴 유예·휴면 처리 여부 |
| A-3 | 방침 :146 | 농장 원천데이터 — 조직 고객 종료 시 반환/파기 기한 |
| A-4 | 방침 :147 | 오프라인 미동기화분 보존 한도 |
| A-5 | 방침 :148 | AI 입력·출력 보관 기간 |
| A-6 | 방침 :149 | OCR 업로드 원본 보관 여부·기간 |
| A-7 | 방침 :150 | 보안·이용 로그 보존 (접속 로그 3개월은 법정, 그 외) |
| A-8 | 방침 :151 | 고객지원 기록 보존 |
| A-9 | 방침 :152 | 백업 순환 주기·완전삭제 시점 |
| A-10 | 방침 :153 | 동의 이력 보존 기간 (근거는 COUNSEL 병기) |
| A-11 | 마스터 :81 | 결제 통화 · PG사 · 세금 부담 주체 |
| A-12 | 마스터 :134 | 통계 제외 요청 처리 영업일 수 |
| A-13 | 마스터 :269 | 시행일 |
| A-14 | VN :8 | DPO 외부 지정 가능 여부 |

### 8-B. 컨트롤러/프로세서 역할 — ★ 사업 판단이 아니다 (5곳 · = D-13)

`ADDENDUM_US:56 · EU:57 · GB:58 · TH:51 · VN:49` — 같은 한 문장. 그리고 방침 `:111`.

```
CLOSURE_COMMON N-1 · CLOSURE_BR BR-4 · CLOSURE_EU EU-2 · CLOSURE_GB GB-2 · COUNSEL_REQUEST 4번
DECISION_REGISTER D-13  "확정은 변호사"
```

역할은 고르는 것이 아니라 법이 판정한다. 그 라벨 하나가 GDPR 제28조 · PIPA 제26조⑧ ·
미국 주법 프로세서 통지 층을 전부 끌고 온다. 변호사 없이 가더라도 **"회사 입장(미확인)"**
으로만 적을 수 있고, 잘못 적고 게시하면 정정이 곧 중대변경 → 재동의 2회차다.
**(A) 와 같은 칸에 두지 않는다.** 오전에 (A) 옆 "사업 판단" 으로 적은 것은 틀렸다.

### 8-C. 첨부·법률 판단 (4)

```
BR :16       SCC 포어 전문 첨부
BR :15,23    SCC 지정필드 · 완전익명화 산출물의 LGPD 적용 여부
방침 :111    B2B 역할 문단 (= 8-B)
마스터 :269  피그플랜 기존 회원 경과조치 · 재동의 경계 (KR_legal §8)
```

피그플랜 약관·조사 근거로 초안은 쓸 수 있으나 `[OPEN]` 잔존을 명시한다. 위조 0.

### 8-D. 문서 자체가 없음

```
KR·CN 부속조항        D-16 (a) 로 "두지 않는다" APPROVED_VERBAL — KR 법정 고지 충족은 COUNSEL_PENDING
DPA 부표 A·B·C        PLACEHOLDER 9곳
/legal/terms 라우트   없음 — 약관은 가입 화면에서만 보인다 (S-4)
```

### 8-E. 왜 (A) 가 병목인가

프로덕션은 지금 **초안으로 동의를 받고 있다** (`any_draft=True`, G-3 미배포). G-3 는
2026-09-09 **(나) 로 결정**됐다 (DEPLOY_GATE :406) — 배포하면 승인 시점까지 신규 가입이
멈춘다. 배포 안 하면 재동의 모집단(B-6)이 매일 는다. **(A) 14건 → 결재 → APPROVED**
가 이 양자택일에서 빠져나오는 유일한 출구다.

그리고 CL(OTHER) 이 프로덕션에서 **열려 있다** — MASTER+PRIVACY 만, 부속 없음, 초안.
H13 (4) 한 문장은 xfail 10건이 아니라 열린 문을 기다린다.

---

## 7. ★ 미확인 수치 — 결재 전에 정리 필요

**KR 계정 수가 문서마다 다르다.** 같은 대상을 세 번 다르게 세고 있다.

```
H12 (이 문서)          KR 5건 · CN 계정
2026-09-10 대화        KR 13 · CN 2 native  ·  가입자 34농장 동의 0건 · 차단법역 15농장
2026-09-08 프로덕션 실측  전체 75농장 = 피그플랜 42 + 내부 10 + 멤버없음 2 + 실고객 23
                       그중 KR 4 · CN 2
```

모집단이 다른 집계로 보이나 **확인되지 않았다.** 프로덕션 조회가 막혀 있어
개발이 재측정하지 못한다(`KPI_K_LOOP` P-1 과 같은 제약).

★ 이 숫자가 정하는 것.

```
H12   차단 법역 기존 계정 처리 범위
H11   배포 후 "기존 N농장 재동의" 범위
      ★ 실고객인지 내부 계정인지에 따라 결정 자체가 달라진다
```

---
### 채운 뒤 실행 프롬프트 (SESSION_HANDOFF_ADDENDA_v1.4.md)
- **RUN L** (LIA 초안) — 변호사 회신 불요, 지금 가능
- **RUN F'** (변호사 회신 반영) — 회신 첨부 후
- **RUN R** (대리인 정보 반영) — H1~H3 계약 후
