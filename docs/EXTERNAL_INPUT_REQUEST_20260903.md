# EXTERNAL_INPUT_REQUEST — 밖에서 알아와야 할 것 (2026-09-03)

> **용도**: 대표·변호사·외부 계약·리서치로만 풀 수 있는 항목을 한 곳에.
> 개발로 닫을 수 있는 것은 이미 닫았거나 진행 중이며, 아래는 **코드로 풀리지 않는 것**만이다.
>
> **규율**: 각 항목에 실측 근거를 붙였다. 확정되지 않은 것은 `미확정`으로 표기했고
> 그 전제로 결정을 요청하지 않는다.

---

## 0. 한 장 요약

```
[A] 문서        공통 약관 · 6개국 부속조항 초안   있음 (약 200KB, ko+en)
                법무 승인 · 현지어 최종본          없음        ← 밖에서 필요

[B] 게시        신규 오염 차단                    ✅ 코드로 닫음
                라이브 48건 미해결 마커 제거       대기        ← 밖에서 필요

[C] 가입 강제   서버 국가 권한                    ✅ 코드로 닫음
                Web fail-closed · iOS 배선        진행 중

[D] 증빙        동의 원장                          있음
                locale · hash · channel            설계만
```

**핵심**: 약관 문구를 더 쓰는 단계가 아니다. 밖에서 받아와야 할 것은
**결정 · 변호사 회신 · 계약 · 번역 · 리서치** 다섯 종류다.

---

## 1. 대표 결정 — 외부 도움 없이 정할 수 있는 것

| # | 항목 | 왜 필요한가 | 근거 |
|---|---|---|---|
| D-1 | **CURRENT_PUBLICATION_SET** — 신규 가입자·공개 URL 에 서빙할 문서 집합 | 이게 없으면 라이브 48건 마커를 무엇으로 교체할지 정할 수 없다 | `KNOWN_PUBLICATION_EXPOSURE.md` |
| D-2 | 결제 통화 · PG사 · 세금(부가세 포함) 정책 | MASTER_TERMS `[OPEN]` | publish_candidate |
| D-3 | 고객 응대 영업일 수 | MASTER_TERMS `[OPEN]` | 〃 |
| D-4 | 약관 시행일 | MASTER_TERMS `[OPEN — 시행일, 확정 전]` | 〃 |
| D-5 | BR pt-BR 미게시 상태에서 BR 신규가입 유지 / 중단 | App Store BR 라이브와 충돌 | 스펙 F-2 |
| D-6 | 보존기간 6건 — 로그 · 고객지원 · consent_ledger · audit_log · AI 학습분 · 오프라인 미동기화분 | 방침에 기간을 쓰면 그 기간에 삭제하는 잡이 있어야 참이 된다 | `PRIVACY_NOTICE_FACT_FINDING` |
| D-7 | 탈퇴 유예 · 휴면 제도 도입 여부 | 현재 제도 자체가 없다(grep 0건) | 〃 |

★ **D-1 이 최우선이다.** 나머지 결정이 다 나와도 D-1 없이는 라이브 노출을 못 치운다.

---

## 2. 변호사 회신 — `LAWYER_BRIEF.md` (Q1~Q30) 그대로 발송

```
docs/legal/LAWYER_BRIEF.md   38KB · 8개 그룹
첨부  publish_candidate/** (8문서 ko·en) · research/*_legal.md (7개국)
      internal/LIA_PURPOSE2_DRAFT.md
```

### ★ 최우선 1건 — 이것 하나가 7문서를 연다

```
LEGAL-D13   controller / processor 역할 확정

대기 위치   US·EU·GB·BR·TH·VN 부속조항 전부 + 방침 제11조
            "[OPEN — 역할 확정 후 DPA·본 조에 반영]"

질의        B2B DPA 제2조의 역할 분리가 타당한가
            · 고객 입력 직원·계약농가 → 고객=controller, 회사=processor
            · 가입·계정·결제·보안·분석 → 회사=controller
            joint controller 소지는 없는가
```

### 국가별 잔여

```
BR    SCC 전문 첨부 · 국제이전 vs 국제수집 구분(F1) · 완전익명 Art.12 제외(F3)
US    LB525 전자동의=express written 충족 · 데이터브로커 등록 · CA ADMT · DOJ Rule
EU/GB Art.37 DPO 해당성 · LIA 승인 · 쿠키 CMP · 회원국 언어
TH    §37(5) 무한책임 대행계약 조건
VN    외부 DPO 지정 가능 여부·자격
공통  MASTER 경과조치 — 기존 피그플랜 회원과의 관계
```

### 2026-09-02~03 신규 발견 — LAWYER_BRIEF 에 없음

`docs/legal/COUNSEL_QUESTION_QUEUE_20260902.md` B-1~B-8. 요지만:

```
B-2  pigos.io 에 시행일 다른 개인정보 문서 3개 병존 (5/30 · 8/26 · 7/1)
     → 정보주체에게 유효한 것은 무엇인가. 구본 철회 공고가 필요한가
B-3  /legal/terms 라우트 부재 — App Store 약관 URL 을 무엇으로 등록하나
B-4  consent_ledger 0행인데 계정 85 · native 농장 33
     → 동의 기록 없이 생성된 계정의 처리 근거. 소급 동의가 필요한가
B-6  방침 문장 5건이 실제 구현과 다름 (탈퇴·농장데이터·휴면·AI·OCR)
B-7  보존기간을 집행할 파기 잡이 0건 — 기간 명시에 기술적 수단이 필수인가
★ B-9 (신규) 라이브 공개 방침에 [COUNSEL]·[OPEN]·[V] 마커 48건 노출 중
     → 노출 기간 동안의 고지 유효성. 사후 조치가 필요한가
```

★ **아직 자문에 넣지 말 것**: B-1·B-8 의 계정 성격(KR 13 · CN 2 · MX 8 이 실고객인지
내부 테스트인지)은 미확정이다. 전제가 틀리면 자문이 무의미해진다. 아래 §5 참조.

---

## 3. 외부 계약 — 돈이 드는 것

```
H1  EU 대리인 (GDPR Art.27)      rep-as-a-service · 연 1~3천 유로
H2  UK 대리인                     보통 같은 업체가 병행
H3  태국 대리인 (PDPA §37(5))     ★ 무한책임 조항 — 계약 조건 검토 필요
```

★ **EU·GB 는 현재 타겟이 아니다**(CLAUDE.md 5개 시장). **US·BR 만 열 계획이면 H1·H2 는 지금 불필요하다.**
TH 도 유료 게이트(D-09) 상태라 급하지 않다.

---

## 4. 번역 — 승인 확정본이 나온 뒤

```
pt (BR) · th (TH) · vi (VN)      각각 MASTER + PRIVACY + 부속조항
```

manifest 가 이 셋을 **법정 우선어**로 선언하고 있어 영어 대체가 안 된다.
서버가 이미 `lang_gate=true` 로 경고를 내고 있다.

★ **확정본 전에 번역하면 두 번 일한다.** 승인 후에 착수한다.

---

## 5. 내부 확인 — 밖은 아니지만 결정 전에 필요

```
V-1  KR 13 · CN 2 · MX 8 · PH 4 native 농장이 실고객인가 내부 테스트인가
     → admin 에 이미 category(real/test/pigplan) 파생 로직이 있다
        (api/app/routers/admin/admin.py:71,145)
        그 판정 기준이 신뢰할 만하면 실측으로 닫힌다
     → 닫히면 §2 의 B-1·B-8 을 자문에 넣을 수 있다

V-2  백업 순환 주기 · 원본 삭제 후 백업 잔존분 삭제 시점   서버·인프라 담당

V-3  운영 allow_kr_signup 실제 값                        KR 5건의 역사적 원인 판독용
```

---

## 6. 신규 리서치 필요 — 질병 · 백신 · 약품 국가별 기본 set

**스키마는 이미 국가 스코프를 갖고 있다.** 부족한 것은 데이터다.

```
disease_codes        regional_prevalence  JSONB  {"KR":"ENDEMIC","US":"FREE"}   ✓
vaccine_catalog      approved_regions     ARRAY  {"US","KR","SEA"} | {"ALL"}    ✓
medication_catalog   vfd_required_us · eu_restricted                            △
```

현재 시드 규모(`docs/master-data/`):

```
                      2026-03-19    2026-05-19
disease_codes             30            33
vaccine_catalog           22            23
medication_catalog        22            13
country_configs            0             0
```

### 문제 3가지

```
① medication 만 국가가 컬럼명에 박혀 있다
   vfd_required_us · eu_restricted → BR·TH·VN·CN 추가 시 컬럼을 계속 늘려야 한다
   "국가 확장 = 데이터 추가" 원칙과 어긋난다 (스키마 변경 필요)

② 국가 필터를 읽는 코드가 2곳뿐
   engine/rules/disease.py (경보 심각도) · kpi_service.py:304
   approved_regions · vfd_required_us · eu_restricted 를 읽는 코드 0건
   → 백신·약품 국가 필터가 스키마에만 있고 동작하지 않는다

③ 국가별 데이터가 없다
```

### ★ 밖에서 받아와야 하는 것

```
국가별 승인 백신 목록          US · BR · TH · VN  (제조사·제품명·승인 여부)
국가별 약품 규제               휴약기간 · 항생제 제한 · 처방 요건
                              (US VFD 상당의 BR/TH/VN 제도)
국가별 신고대상 질병           WOAH 기준 + 각국 법정 신고 질병
```

★ **이건 지어낼 수 없다.** 휴약기간을 틀리게 표시하면 **잔류물질 위반**으로 이어진다.
`docs/legal/research/*_legal.md` 처럼 국가별 수의·약사 규제 리서치가 선행되어야 한다.

---

## 7. 이미 코드로 닫은 것 — 밖에서 알아올 필요 없음

2026-09-02~03 작업. 전부 로컬 커밋, push·deploy 0건.

```
4a64da8  국가 진입 권한을 서버로 이동
         /auth/register · /onboarding/complete · /onboarding/farm 세 진입점
         → consent API 를 호출하지 않는 클라이언트도 CN·KR 차단 우회 불가
         → 첫 DB write 이전에 차단 (org·user·farm 생성 0 을 테스트로 증명)
         14 tests

cc247d6  라이브 게시 노출 격리 + 잘못된 정본 계약 제거
         → publish_candidate 를 런타임 정본으로 강제하던 테스트가 오염 경로였다
         → 48건을 정확히 등록. 증가도 감소도 실패. 만료 2026-09-10
         7 tests

90e1284  미지원국 목적② 기본 OFF (마스터 제10조③ 정합)
         14 tests

+ 문서 7건   법무 게시 갭 · 프로덕션 원장 감사 · 방침 미결 실측 ·
             국가별 온보딩 스펙 · 자문 질의 큐 · 프로젝트 브리프
```

```
pytest   1374 passed · 0 failed
```

---

## 8. 진행 중 / 다음

```
진행 중   Web consent fail-closed      판독 완료 · 착수 대기
다음      iOS consent (PR #3 재검증)
다음      consent evidence (locale · channel · hash) — migration 승인 필요
```

### ★ 별도 P0 로 보고한 것 (범위 밖이라 손대지 않음)

```
LEGAL-P0-ORPHAN-ACCOUNT-STATE

동의 없이 생성된 계정이 정상 서비스에 진입 가능하고,
재로그인해도 동의 화면으로 돌아오지 않는다.

  onboarding/page.tsx  setAuth·쿠키가 consent 시도 이전에 실행
                       router.replace("/") 가 catch 와 무관하게 실행
  middleware.ts:75     세션 있으면 / 로 보냄
  서버                 "법적 온보딩 완료" 상태 자체가 없음
                       (onboarding_complete 는 데이터 입력 진척도다)

→ 클라이언트를 fail-closed 로 고쳐도 이미 만들어진 계정은 남는다.
  백엔드 상태 추가 + 마이그레이션이 필요하다.
```

---

## 9. 가장 짧은 경로

```
US 만 먼저 열 경우
  회사 입력   0건
  번역        불요 (법정 우선어 = en)
  대리인      불요
  남은 것     LEGAL-D13 하나 + D-1(CURRENT_PUBLICATION_SET)

→ 변호사 답변 1건 + 대표 결정 1건이면 미국은 게시 가능 상태가 된다.
   온보딩 기본 국가이자 1차 출시 시장이므로 순서도 맞다.

BR 은 그다음
  LEGAL-D13 + SCC 전문 + 국제이전 판단 + pt 번역 + D-5
```

★ **미결 소진 ≠ 승인.** `DOCUMENT_APPROVED`(변호사 확인 + 대표 승인 + 공고일·시행일 기입)
기록 없이 게시하지 않는다.

---

## 10. 참조

```
docs/legal/LAWYER_BRIEF.md                              Q1~Q30 본체
docs/legal/COUNSEL_QUESTION_QUEUE_20260902.md           신규 발견 B-1~B-8
docs/legal/KNOWN_PUBLICATION_EXPOSURE.md                라이브 48건 격리 명세
docs/legal/LEGAL_PUBLICATION_GAP_REPORT_20260902.md     문서·구현·승인 gap
docs/legal/PRODUCTION_CONSENT_LEDGER_AUDIT_20260902.md  원장 0행 실측
docs/legal/PRIVACY_NOTICE_FACT_FINDING_20260902.md      방침 미결 20건 실측
docs/legal/PIGOS_COUNTRY_LEGAL_ONBOARDING_SPEC_v1.0.md  국가별 가입 설계
docs/PIGOS_PROJECT_BRIEF.md                             프로젝트 정본 + 산업 리서치 프롬프트
docs/master-data/*.sql                                  질병·백신·약품 시드
```
