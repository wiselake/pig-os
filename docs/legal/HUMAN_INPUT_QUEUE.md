# HUMAN_INPUT_QUEUE — 사람이 채울 법무 빈칸 (loop 대상 아님)

> 2026-07-23. **이 항목들은 자동 생성 금지(위조0).** 실값·계약·변호사 판단이 필요. 채우면 표기.
> 전체 미결 상세는 `OPEN_QUESTIONS.md`(A~G) 참조 — 이 문서는 **바로 처리할 액션**만 추림.
> 채우는 절차: 값 확보 → 해당 `[OPEN]` 교체 → `SESSION_HANDOFF_ADDENDA_v1.4.md`의 RUN F'(변호사 회신)·RUN R(대리인) 실행.

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
> D-01~D-04는 조건부 BUSINESS_APPROVED(2026-07-21) — 변호사 반대 시 자동 REOPEN.

## 3. 변호사 회신 필요 ([COUNSEL] — LAWYER_BRIEF 30건 요지)
- US: LB525 전자동의=express written 충족 여부(Q7)·데이터브로커 등록·CAN-SPAM 주소·CA ADMT/위험평가(Q8)·DOJ Rule(Q10)
- EU/GB: 대리인 확정·DPO 해당성(Art.37)·LIA 승인·쿠키 CMP UI·회원국 언어
- BR: SCC 전문 편입·역할 매핑(F1 exporter 주체)·F3 완전익명 Art.12/33 제외 여부
- 공통: D-01~D-04 조건부 승인의 법무 확인
> 전문: `LAWYER_BRIEF.md`. 회신 오면 RUN F'로 반영.

## 4. 사업조건 placeholder (임의 확정 금지 — 8건)
- 크레딧·환불·SLA·최소액·취소·세금 등 (`OPEN_QUESTIONS.md` §B). 확정 전 약관에서 제외 또는 `[OPEN]`.

## 5. 게시 전 문서/검증 (loop 아님)
- SCC 전문(BR/TH) · LIA 최종(변호사 승인) · F5 KR 게시본 상충 실사 · V1 동의 UI·로그 실사.

---
### 채운 뒤 실행 프롬프트 (SESSION_HANDOFF_ADDENDA_v1.4.md)
- **RUN L** (LIA 초안) — 변호사 회신 불요, 지금 가능
- **RUN F'** (변호사 회신 반영) — 회신 첨부 후
- **RUN R** (대리인 정보 반영) — H1~H3 계약 후
