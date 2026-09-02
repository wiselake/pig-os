# COUNSEL_QUESTION_QUEUE — 2026-09-02

> **용도**: 변호사 자문에 가져갈 항목을 한 곳에. 기존 `LAWYER_BRIEF.md`(Q1~Q30, 2026-08-13)와
> **중복되지 않는 신규 발견분**을 분리했다.
>
> **규율**: 각 항목은 실측 근거(파일:줄 · 쿼리 · 커밋)를 붙인다. 추정을 질문으로 만들지 않는다.
> 미확정 사실은 "확인 예정"으로 표기하고 그 전제로 자문을 구하지 않는다.

---

## 0. 먼저 — 약관은 "개발"된 상태가 아니다

혼동을 없애기 위해 축을 분리한다.

```
작성      YES / SUBSTANTIAL   publish_candidate v1.0-rc  8문서 × ko/en = 16벌 ≈ 200KB
승인      NO                  전 문서 DRAFT_LAWYER_PENDING
번역      NO                  pt(BR) · th(TH) · vi(VN)  0건
앱 연결   NO                  런타임은 394~782B placeholder
```

**문서는 잘 만들어져 있고, 앱에 붙어 있지 않다.** 이 상태는 사고가 아니라 의도된 잠금이다
(`IMPLEMENTATION_COVERAGE.md` — "확정본 파일 교체로 반영", "any_draft=true 가 게시 차단 신호").

---

## A. 이미 준비된 질의 — 그대로 발송

```
docs/legal/LAWYER_BRIEF.md   38KB · Q1~Q30 · 8개 그룹
  ① 익명화·판매모델   ② 동의·법적근거   ③ 국외이전   ④ 보유·삭제·철회
  ⑤ 마케팅·아웃리치   ⑥ 국가별 등록·대리인   ⑦ 중국·베트남 진입   ⑧ 기존 게시본 정비
```

첨부: `publish_candidate/` 8문서(ko·en) · `research/*_legal.md` 7개국 · `LIA_PURPOSE2_DRAFT.md`

### A-1. ★ 최우선 — 이것 하나가 7문서를 연다

```
LEGAL-D13   controller / processor 역할 확정

  대기 위치   publish_candidate 6개국 부속조항 전부
              "[OPEN — 역할 확정 후 DPA·본 조에 반영]"
              + GLOBAL_PRIVACY_NOTICE 제⑪조

  질의        B2B DPA 초안(제2조)의 역할 분리가 타당한가
              · 고객이 입력한 직원·계약농가 정보 → 고객=controller, 회사=processor
              · 가입·계정·결제·보안·이용분석 → 회사=controller
              사실관계상 이 구분이 유지되는가, 공동처리자(joint controller) 소지는 없는가
```

이 1건이 미결인 동안 US·EU·GB·BR·TH·VN 부속조항 전부 승인 불가다.

---

## B. 2026-09-02 신규 발견 — LAWYER_BRIEF 에 없는 항목

`LAWYER_BRIEF`(2026-08-13) 이후 실측으로 드러난 것들이다.

### B-1. 차단 법역에 실제 가입이 존재한다

```
실측    farms.country = KR 13건 (native_signup 13)
                        CN 10건 (native_signup 2)
근거    운영 DB READ ONLY 집계 2026-09-02
설계    jurisdiction._GATES  KR=signup_blocked(KR_REFERENCE_ONLY) · CN=signup_blocked(HOLD_D07)

★ 확인 예정   이 계정들이 내부 테스트 계정인지 실고객인지 미확정
              (WHY-ZERO-CONSENT RUN Z-4·Z-5 에서 이메일 도메인 count·차단 로직 도입일로 판별)

질의    (a) 내부 테스트 계정이라면 법적 노출이 있는가
        (b) 실고객이라면 — KR 은 회사 본국이고 CN 은 진입 HOLD 인데
            이미 존재하는 계정의 처리 방침은 무엇이어야 하는가
        ※ (b) 는 Z-4 확정 후에만 자문 요청. 전제가 틀리면 자문이 무의미하다
```

### B-2. 시행일이 다른 개인정보 문서 2개가 동시에 라이브다

```
pigos.io/privacy          시행일 2026년 05월 30일   (랜딩 자체 페이지)
pigos.io/legal/privacy    302 → api.pigos.io/legal/privacy
                          "확정 개인정보 처리방침 v1.0(시행 2026-08-26)"
pigos-landing docs/legal/*.ko.md   시행일자 2026년 7월 1일   (제3의 날짜)

★ 등급   위 sha 는 repo 판독(REPO_CANDIDATE)이며 HTTP 실측 아님 — Z-6 에서 확정

질의    동일 도메인에 시행일이 다른 처리방침이 병존할 때
        (a) 정보주체에게 유효한 것은 무엇인가
        (b) 정리 방법 — 구본 철회 공고가 필요한가, 링크 정리로 충분한가
        (c) 5/30 본에서 8/26 본으로의 변경이 중대변경인가 (제15조 자기 규칙 적용)
```

### B-3. 이용약관 URL 이 존재하지 않는다

```
/legal/privacy   구현됨 (api/app/main.py:211)
/legal/terms     NOT_IN_REPO — 라우트·상수 모두 부재

질의    App Store 제출 시 약관 URL 을 무엇으로 등록해야 하는가
        랜딩 /terms(5/30 본)를 가리켜도 되는가, 아니면 정본 렌더 경로가 필요한가
```

### B-4. 동의 기록이 0건이다

```
consent_ledger   0행  (테이블·라우터·마이그레이션 전부 배포됨)
계정              85    2026-06-26 ~ 2026-08-29
농장              75    native_signup 33

질의    (a) 약관 동의 기록 없이 생성된 기존 계정의 처리 근거는 무엇인가
            SERVICE_OPERATION 의 lawful basis 가 계약 이행이고 그 계약이 곧 약관인데
            동의 기록이 없다
        (b) 소급 동의 취득이 필요한가. 필요하다면 승인본 게시 후
            일괄 고지·동의로 처리 가능한가
        (c) 그 사이 처리된 데이터의 지위는 어떻게 되는가
```

★ **좋은 소식 하나**: placeholder 약관에 동의한 사용자가 0명이므로
**잘못된 약관에 동의받은 사고는 없다.** 재동의 대상 자체가 존재하지 않는다.
(`PRODUCTION_CONSENT_LEDGER_AUDIT_20260902.md`)

### B-5. 동의 버전 식별자가 본문을 구분하지 못한다

```
notice_version   "MASTER_TERMS@0.1-draft+GLOBAL_PRIVACY_NOTICE@0.1-draft+…"
                 terms_renderer.py:98
version 값       manifest 4커밋 전 구간 "0.1-draft" 고정
실제 본문        privacy_notice.en.md 는 3종
                 80b68ed9 → d8a1030d → 7db446b6

→ 같은 문자열이 서로 다른 본문 3개를 가리킨다

질의    향후 동의 증빙에 문서 본문 해시(sha256)를 기록하는 것이 필요한가
        아니면 버전 번호 체계만으로 충분한가
        (설계는 이미 body_sha256 기록 방향으로 잡혀 있으나 법적 요구 수준을 확인하고 싶다)
```

### B-6. 방침 문장이 실제 구현과 다르다 — 5건

```
탈퇴        방침 "지체 없이 파기"
            실제 행 DELETE 가 아니라 식별정보만 파기하고 행은 남긴다
                 (period_locks FK — users 를 지우면 확정 월마감이 풀리고
                  consent_ledger 도 사라져 동의·철회를 증명할 수 없다)
            질의  PIPA 제21조 "파기" 를 식별성 제거로 충족한다는 해석이 유지되는가
                  방침 문구를 어떻게 써야 실제와 일치하면서 법적으로 안전한가

농장데이터   방침 "계약 종료·탈퇴 시 파기 또는 반환"
            실제 파기하지 않고 farms.active=false. 반환 절차 없음
            질의  가축 생산기록을 "탈퇴자의 개인정보가 아니다" 로 보는 것이 타당한가

휴면        방침에 언급  ·  실제 제도 없음 (grep 0건)
AI 입출력    방침 "필요 기간 보관 후 삭제"  ·  실제 저장 모델 없음(서버 미보관)
OCR         방침에 보존기간 기재  ·  실제 기능·모델 자체가 없음

질의    수집·보관하지 않는 항목을 방침에 기재하는 것도 부정확 고지인가
        (광고 식별자·PG 결제·권한변경 이력도 모델에 0건)
```

### B-7. 보존기간을 집행할 수단이 없다

```
api/app/jobs/   keepalive · kpi · notifications · tasks · worker
purge / cleanup / retention 함수   0건

→ 어떤 데이터도 기간 경과로 자동 삭제되지 않는다

질의    방침에 보존기간을 명시하면 그 기간이 지난 데이터를 삭제하는
        기술적 수단이 반드시 있어야 하는가
        "목적 달성 시 지체 없이 파기" 원칙과 무기한 보관의 충돌을 어떻게 정리하는가
        특히 consent_ledger · audit_log 는 증빙 목적이라 장기 보관이 필요한데
        그 근거 문구를 어떻게 써야 하는가
```

### B-8. 타겟 아닌 국가에 농장이 존재한다

```
MX  8농장 (native 5)   법역 미검토(UNREVIEWED) · 부속조항 없음 · 스페인어 문서 없음
PH  4농장 (native 1)   법역 목록·시드에 아예 없는 국가
ES·DE·DK·NL           각 1~2농장 (전부 pigplan_migration, native 0)

★ 확인 예정   내부 테스트 여부 미확정 (B-1 과 동일 — Z-4)

질의    법역 검토가 안 된 국가의 이용자에게
        (a) 글로벌 마스터+방침만으로 서비스해도 되는가
        (b) 아니면 가입을 차단해야 하는가
        (c) 이미 있는 계정은 어떻게 하는가
```

---

## C. 변호사가 아니라 **회사가 정할 것**

자문 요청에 섞지 말 것. 답을 정해서 문서에 넣어야 하는 값이다.

```
C-1  결제 통화 · PG사 · 세금(부가세 포함) 정책          MASTER_TERMS
C-2  고객 응대 영업일 수                                MASTER_TERMS
C-3  약관 시행일                                        MASTER_TERMS
C-4  CURRENT_PUBLICATION_SET — 신규 가입자에게 서빙할 문서 집합
C-5  보존기간 6건   오프라인 미동기화분 · 보안/이용 로그 · 고객지원 기록
                    consent_ledger · audit_log · AI 학습 이용분
C-6  인프라 확인 2건  백업 순환 주기 · 원본 삭제 후 백업 잔존분 삭제 시점
C-7  BASELINE_APPROVED 판정 기준 — 어떤 검토를 거치면 baseline 국가인가 (COUNSEL 협의)
```

`C-5`·`C-6` 은 `PRIVACY_NOTICE_FACT_FINDING_20260902.md` 에 실측 초안이 있다.

---

## D. **계약**이 필요한 것 — 돈이 드는 항목

```
H1  EU 대리인 (GDPR Art.27)      rep-as-a-service, 연 1~3천 유로 규모
H2  UK 대리인                     보통 같은 업체가 병행
H3  태국 대리인 (PDPA §37(5))     ★ 무한책임 조항 — 대행계약 조건 검토 필요
```

★ **EU·GB 는 현재 타겟이 아니다**(CLAUDE.md 5개 시장). **US·BR 만 열 계획이면 H1·H2 는 지금 불필요하다.**
TH 도 유료 게이트(D-09) 상태라 급하지 않다.

---

## E. 가장 짧은 경로

```
US 만 먼저 열 경우
  회사 입력   0건
  번역        불요 (법정 우선어 = en)
  대리인      불요
  남은 것     LEGAL-D13  1건

→ 변호사 답변 1건이면 미국은 게시 가능 상태가 된다.
   온보딩 기본 국가이자 1차 출시 시장이므로 순서도 맞다.

BR 는 그다음
  LEGAL-D13 + SCC 전문 + 국제이전/국제수집 구분 + Art.12 완전익명 + pt 번역
```

★ **미결 소진 ≠ 승인.** `DOCUMENT_APPROVED`(변호사 확인 + 대표 승인 + 공고일·시행일 기입)
기록 없이 게시하지 않는다.

---

## F. 자문 요청 시 함께 보낼 것

```
docs/legal/LAWYER_BRIEF.md                              Q1~Q30 본체
docs/legal/publish_candidate/**                         대상 문서 8종 (ko·en)
docs/legal/research/*_legal.md                          국가별 리서치 7개국
docs/legal/internal/LIA_PURPOSE2_DRAFT.md               목적② 정당한 이익 평가
docs/legal/LEGAL_PUBLICATION_GAP_REPORT_20260902.md     문서·구현·승인 gap
docs/legal/PRODUCTION_CONSENT_LEDGER_AUDIT_20260902.md  원장 0행 (재동의 불요 근거)
docs/legal/PRIVACY_NOTICE_FACT_FINDING_20260902.md      방침 미결 20건 실측
본 문서                                                  신규 발견 B-1~B-8
```

---

## G. 아직 확정되지 않아 자문에 넣으면 안 되는 것

```
B-1 · B-8 의 (b) 항  KR·CN·MX·PH 계정이 실고객인지 내부 테스트인지 미확정
                     WHY-ZERO-CONSENT RUN Z-4(이메일 도메인 count) ·
                     Z-5(차단 로직 도입일) 로 확정 예정
                     → 전제가 틀리면 자문 자체가 무의미해진다

LIVE_PUBLIC sha      B-2 의 해시는 repo 판독(REPO_CANDIDATE)이며 HTTP 실측 아님
                     Z-6 HTTP 관측으로 확정 후 자문
```

이 둘은 확정 뒤에 2차로 보내는 편이 낫다.
