# PIGOS_PROJECT_BRIEF — 프로젝트 정본 브리프 (v1.0, 2026-09-02)

> **용도 2가지**
> 1. 외부 도구(GPT·리서치 에이전트)에 붙여 **산업 정보를 수집**하는 컨텍스트 프롬프트 — §1~§4
> 2. 수집 결과를 **개발 방향 판단**으로 연결하는 기준 — §5~§7
>
> **규율**: 이 문서의 수치·상태는 실측이다. 추정으로 갱신하지 않는다.
> 상태가 바뀌면 근거(커밋·쿼리·파일:줄)와 함께 갱신한다.

---

# PART A — 수집용 컨텍스트 (외부 도구에 그대로 붙여도 되는 부분)

## 1. PigOS가 무엇인가

**한 줄**: 해외 양돈 농장용 Farm Management SaaS + 데이터 수익화 플랫폼.

```
회사        와이즈레이크(주) / WiseLake Inc. (대한민국)
도메인      pigos.io
기반        한국 시장 27년 운영 제품 "PigPlan" 의 노하우를 글로벌로 재설계
포지셔닝    벤더-중립 독립 데이터 플랫폼 + 오픈 연동 생태계
            (사료·기자재·유전자 회사에 종속되지 않는 것이 핵심 차별점)
```

**사업 모델**

```
무료 제공  →  데이터 수집  →  수익화  →  농가 환원
                                          ★ 현금 배분이 아니라 벤치마크 인사이트 환원
                                            (2026-07-21 방향 변경)
```

수익화 브랜드는 **PigSignal** — 개별 농장 데이터를 익명·집계 통계로 변환해 사료·동물약품·
유전자·금융·정부에 제공하는 구상. 원 데이터 판매가 아니라 집계 산출물이며, 국가별로
법적 근거가 갈린다(익명정보 예외 / 정당한 이익 / 옵트인).

**타겟 시장 5개 × 8개 언어**

```
US        1차 출시 시장. 온보딩 기본 국가
CN        진입 HOLD (현지 법무 필수)
SEA       VN + TH (유료·마케팅 게이트 상태)
LatAm     현재 BR(pt)만 커버. 스페인어권(MX·CO 등) 미비
KR        ★ 레퍼런스 전용. 공개 마케팅 타겟 아님, 실고객 가입 차단

언어      en · ko · zh · es · vi · th · pt · ru
비타겟    EU · GB (대리인 미계약)
```

**제품 범위**

```
모듈       27개 라우터 / 49 테이블
핵심 KPI   PSY · NPD · FCR · 분만율 · MSY · WSI · PWMR
           사산율 · 미라율 · 이유두수 · 모돈회전율
기능       모돈 개체관리 · 분만/이유/교배 이벤트 · 비육/자돈 · 월마감 잠금
           국가별 벤치마크 비교 · Rule Engine 경고 · Q&A(룰 기반 + LLM 렌더)
현장성     오프라인 우선 입력 · 저사양 안드로이드 · 백그라운드 동기화
```

**기술 스택** (경쟁사 기술 비교 시 참고)

```
Backend   FastAPI(Python) · PostgreSQL 16 + TimescaleDB · Redis · ARQ
Frontend  Next.js + TypeScript
Mobile    Android = Kotlin/Compose/Room/WorkManager (네이티브)
          iOS = Swift/SwiftUI
Infra     AWS 서울(ap-northeast-2) · Docker · Kubernetes
AI        Rule Engine 이 판정, LLM 은 자연어 변환만 (판단 금지 구조)
```

**Phase 2 구상** — 이 방향의 시장 신호를 특히 주시

```
Task 자동배정      Rule Engine 경고 → 할 일 자동 생성 → 담당자 배정 (노동력 절감)
PRRS 유전자 추적   품종별 질병 발생률 비교
Traceability      농장 이벤트 → 도축장 → 소비자 QR (B2B 프리미엄)
```

---

## 2. 이미 파악한 경쟁 지형 — **중복 수집 금지**

사내 문서에 이미 정리된 대상. **새 사실이 있을 때만 보고**하고 회사 소개 수준 재기술은 금지.

```
기록관리 SaaS      PigCHAMP(US) · MetaFarms(US) · AgroVision/Porcitec/PigVision(NL)
                   CloudFarms(CZ·CA) · PigFlow(CA)
센서·정밀축산      Nedap(NL) · Precision Livestock Diagnostics(CA)
하드웨어 번들      Big Dutchman(DE) · Fancom(NL) · Eco-Pork(JP)
                   ★ 동남아 동시 진입 중 — 번들로 SaaS 를 끼워 파는 구조
동물약품·진단      Zoetis
대형 생산자        Muyuan · Wens(CN) · Charoen Pokphand(TH) · BRF · JBS · Seara(BR)
```

출처: `docs/planning/2026-04-27_PigOS_CompetitorIntel.md` · `docs/legal/benchmark/`

---

## 3. 수집 대상

### A. 뉴스·이벤트

```
질병          ASF · PRRS · PED 발생·확산·백신 승인 → 시장 진입 타이밍과 직결
가격·수급      돈가 · 사료가(옥수수·대두박) · 도축두수 · 모돈 사육두수 통계
정책·보조금    스마트축산 보조금, 디지털 전환 지원사업, 축산 규제 강화
M&A·투자      농장관리 SW·정밀축산 스타트업 인수·펀딩 (금액·투자자·밸류)
대형 계약      통합업체(integrator) 의 전사 시스템 도입 발표
```

### B. 경쟁사 움직임

```
신규 진입      새 국가 출시, 현지 파트너십, 언어 추가
제품 변화      AI 기능 추가, 요금제 변경, 무료 티어 도입, API 개방
데이터 사업    벤치마크·인사이트 상품화, 데이터 판매·공유 프로그램
              ★ PigSignal 과 직접 경합 — 최우선 감시
번들 전략      기자재·사료 회사가 SW 를 무료로 끼워 파는 사례
철수·실패      서비스 종료·축소 (반면교사 + 고객 이전 기회)
```

### C. 트렌드·기술

```
노동력 절감    양돈 산업 최대 과제. AI 기반 자동화 사례
정밀축산(PLF)  카메라·음성(기침 감지)·체중 추정·행동 분석
데이터 소유권  농가 데이터 권리, ag-data 표준
벤더 종속      농가가 특정 벤더에 묶이는 문제 제기 — PigOS 포지셔닝 근거
시장 규모      정밀축산·농장관리 SW 시장 규모·성장률 (출처·연도 필수)
```

### D. 규제·법무

```
데이터보호     US 주법(CCPA·주 프라이버시법·Nebraska LB525 농업데이터)
              EU GDPR · BR LGPD + ANPD SCC · TH PDPA · VN PDPD · CN PIPL
국외이전      한국 서버로의 이전 근거 변화 (적정성·SCC·TIA)
축산 특수법    방역법상 데이터 보고 의무, 이력제, 도축 정보
AI 규제       EU AI Act 등이 축산 AI 에 미치는 영향
```

★ `docs/legal/research/{US,BR,TH,VN,CN,KR,GB_EU}_legal.md` (약 200KB)가 이 영역을 이미
상당 부분 커버한다. **그 문서들 작성(2026-08-13) 이후 바뀐 것**만 물을 것.

---

## 4. 수집 제외 · 출력 형식 · 규율

**제외**

```
✗ 소·닭·수산 전용 (양돈 시사점 명시된 경우만 예외)
✗ 회사 소개·연혁 수준 일반 정보
✗ 보도자료 재탕, 출처 없는 요약 블로그
✗ §2 목록의 재기술 (새 사실 없이)
✗ 한국 국내 마케팅 정보 (KR 은 레퍼런스 전용)
```

**항목별 출력** — 빈칸은 빈칸으로 둔다. 추정으로 채우지 않는다.

```
[제목]
출처        기관명 + URL
발행일      YYYY-MM-DD (미상이면 "미상")
국가/시장   US · BR · VN · TH · CN · MX · 글로벌 …
분류        뉴스 / 경쟁사 / 트렌드 / 규제
요약        3줄 이내. 수치는 원문 그대로
PigOS 함의  진입 타이밍 / 제품 로드맵 / PigSignal 수익화 /
            경쟁 위협 / 법무·컴플라이언스 / 파트너십 기회
확신도      확인됨(1차 출처) / 보도 기반 / 미확인
```

**종합 3섹션**: 즉시 대응 필요 / 로드맵 반영 후보 / 계속 관찰

**규율**

```
★ 위조 0            수치·날짜·회사명을 추정하지 않는다. 모르면 "미확인"
★ 출처와 해석 분리   원문이 말한 것과 당신의 함의를 섞지 않는다
★ 상태 승격 금지     "발표됨" ≠ "출시됨" ≠ "실제 도입됨"
★ 1차 출처 우선     기업 IR·정부 통계·학술지 > 업계지 > 블로그
                    업계지: National Hog Farmer · Pig Progress · Feedstuffs ·
                           WATTAgNet · Pig333 · Suínos & Cia(BR)
```

---

# PART B — 개발 방향 판단 기준 (내부용, 외부 도구에 붙이지 않음)

## 5. 현재 실측 상태 (2026-09-02)

**코드 규모**

```
backend      175 py files · 27 라우터 · 16 DB 모델 · 53 alembic revision
frontend     122 ts/tsx files
tests        1,340 collected
mobile       Android(Kotlin/Compose) · iOS(Swift/SUI) 독립 저장소 2개
```

**★ 운영 실측 — 이게 방향 판단의 핵심 입력이다**

```
users        85          2026-06-26 ~ 2026-08-29
farms        75          pigplan_migration 42 · native_signup 33

농장 국가 분포 (12개국)
  US 20(native 10)   KR 13(13)   CN 10(2)   MX  8(5)
  BR  6(1)           VN  5(1)    PH  4(1)   TH  3(0)
  ES  2(0)           DE  2(0)    DK  1(0)   NL  1(0)
```

★ **선언한 타겟과 실제 가입이 어긋나 있다.**

```
KR 13 native   레퍼런스 전용·가입 차단 법역인데 실제 native 가입이 가장 많다
CN  2 native   진입 HOLD 법역인데 native 가입이 있다
MX  8 (5)      타겟 목록에 없는데 US 다음으로 많다 — 스페인어권 신호
PH  4 (1)      시드·법역 목록에 아예 없는 국가
BR  1 native   1차 LatAm 시장인데 native 1건
```

이 불일치의 원인은 미확정이며 `WHY-ZERO-CONSENT` RUN(Z-4·Z-5)에서 확인 예정.
**내부 테스트 계정일 가능성이 있으므로 시장 신호로 단정하지 않는다.**

**동작하지 않는 것 — 알고 있어야 할 결함**

```
kpi_snapshots        0행. 2026-05-29 이래 단 한 건도 기록된 적 없음
                     일·주·월 집계 잡이 매일 실행되나 71농장 전건 실패
                     대시보드는 요청 시 계산 + Redis 30초 캐시로 동작 중
                     근거: docs/runs/RUNTIME_INTEGRITY_AUDIT_20260828.md
consent_ledger       0행. 코드·테이블·라우터는 배포됐으나 기록 0
                     근거: docs/legal/PRODUCTION_CONSENT_LEDGER_AUDIT_20260902.md
국가별 약관 본문      런타임은 394~782B placeholder. 실문서는 승인 대기로 미연결
                     근거: docs/legal/LEGAL_PUBLICATION_GAP_REPORT_20260902.md
```

## 6. 수집 결과 → 개발 방향 연결 규칙

수집한 정보를 어떤 결정으로 옮길지 미리 정해둔다. **정보가 로드맵을 자동으로 바꾸지 않는다.**

| 수집 신호 | 연결되는 결정 | 결정 주체 |
|---|---|---|
| 특정 국가 ASF·PRRS 확산 | 해당 시장 진입 타이밍 · 질병 모듈 우선순위 | 대표 |
| 경쟁사가 벤치마크/인사이트 상품 출시 | **PigSignal 차별화 재검토** — 최우선 | 대표 + 기획 |
| 하드웨어 번들이 SEA 확대 | VN·TH 게이트(D-08·D-09) 해제 시점 재검토 | 대표 |
| 노동력 절감 AI 사례 축적 | Phase 2 Task 자동배정 우선순위 상향 | 기획 |
| 스페인어권 규제·시장 정보 | MX 법무 리서치 착수 여부 (현재 UNREVIEWED) | 대표 + 법무 |
| ag-data 소유권 논쟁 격화 | 벤더-중립 포지셔닝 메시지 강화 · 약관 반영 | 기획 + 법무 |
| 국가별 데이터보호법 개정 | `docs/legal/research/*` 갱신 → 부속조항 개정 | 법무 |

**절대 규칙**

```
★ 수집 정보로 코드를 바꾸지 않는다.
  정보 → 대표/기획 결정 → Decision Register → 그 다음에 구현.
  APPROVED 아닌 정책을 코드·seed 에 반영 금지 (CLAUDE.md 스펙 문서 체계).

★ 시장 신호와 내부 데이터를 구분한다.
  §5 의 농장 국가 분포는 내부 테스트 계정이 섞여 있을 수 있다.
  Z-4 확정 전까지 "MX 수요 있음" 같은 결론을 내지 않는다.
```

## 7. 현재 막혀 있는 것 — 정보 수집으로 풀리지 않는 것

수집을 아무리 해도 아래는 안 풀린다. 혼동하지 말 것.

```
변호사 회신     LEGAL-D13(controller/processor 역할) — 6개국 부속조항 + 방침을 동시에 잠금
현지어 번역     pt(BR) · th(TH) · vi(VN) 0건. 법정 우선어라 영어 대체 불가
대리인 계약     EU · UK · TH (연 1~3천 유로 규모). 단 EU·GB 는 현재 비타겟
대표 결정       결제 통화·PG·세금 / 응대 영업일 / 약관 시행일
                CURRENT_PUBLICATION_SET (신규 가입자 서빙 문서 집합)
운영 확정       보존기간 9건 · 수집항목 실측 11건
                근거: docs/legal/PRIVACY_NOTICE_FACT_FINDING_20260902.md
```

---

## 8. 관련 문서

```
docs/PIGOS_SPEC_INDEX.md                          전 스펙 지도 (세션 시작 시 진입점)
docs/PLATFORM_PARITY.md                           웹·Android·iOS 기능 동등성 + P0 결함
docs/planning/2026-04-27_PigOS_CompetitorIntel.md 경쟁사 인텔
docs/planning/2026-04-15_PigOS_MarketingRoadmap.md
docs/qa/overnight-market-qa/2026-06-24/           시장별 QA (BR·CN·KR)
docs/legal/research/*_legal.md                    국가별 법무 리서치 7개국
docs/legal/PIGOS_COUNTRY_LEGAL_ONBOARDING_SPEC_v1.0.md
docs/LANDING_SYNC.md                              랜딩 노출 수치 정본
```
