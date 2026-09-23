# Feed Pilot Input Protocol — CORE 실데이터 확보 프로토콜 (v0, 2026-09-22)

> 목적: Feed Engine V1 **CORE 6 지표**가 실제 농장 입력으로 값을 내는지, 그리고 그 값이 입력값과 대조되는지 확인한다.
> 새 기능·새 지표·임계·벤치마크·과금 없음. 이 문서는 **절차**이고 실행은 결재 뒤다 — 이 세션은 어떤 농장에도 연락·입력하지 않았다.
> 근거: `FEED_INPUT_ADOPTION_AUDIT_20260922.md` §10 MVI · `FEED_ENGINE_V1_CANONICAL_SPEC.md` §4-5 · `reports/F4_REAL_DATA_AUDIT_20260922.md`.

---

## 0. 전제 (하나라도 아니면 시작하지 않는다)

```text
P0 INPUT UX FIX 배포됨    /feed 폼에 unit_cost·currency 입력 (감사 §12) — 없으면 COST 축 검증 불가 → QTY 축만 도는 축소 파일럿으로 명시
결재                     파일럿 대상 농장 접촉·안내 (대표) · KR 농장 포함 여부 (KR = 레퍼런스 전용, 실고객 아님 — CLAUDE.md)
프로덕션 쓰기             파일럿 농장의 **자기 데이터 입력**만. 운영자가 대신 입력하지 않는다. 시드·백필 없음
계약 고정                 quantity_basis = AS_RECORDED 유지. 파일럿의 "기록 규칙"(§2) 은 사용 안내이지 계약 변경이 아니다
```

## 1. 대상 선정 (연락 전, 읽기 전용 집계로)

```text
모집단     farms.data_classification = 'live_customer' AND active
1차 필터   최근 90일 내 이벤트(mating/farrowing/weaning 또는 /sync) 가 있는 농장   ← 09-22 기준 8 농장
2차 필터   입력 권한(OWNER/MANAGER/WORKER) 사용자가 30일 내 로그인                 ← 09-22 기준 5 사용자
목표 수    5 ~ 10 농장 (현재 모집단으로는 최대 8 — 부족분은 "90일 이벤트" 조건을 완화하지 않고 그대로 보고)
GROUP 축   위 중 open finisher_group 이 있는 농장만 별도 선정                       ← 09-22 기준 0 → GROUP 축은 이번 파일럿 범위 밖으로 명시
제외       KR(레퍼런스) · internal_reference(하베스트) · 통화 ≠ farm.currency 로 사료를 사는 농장(통화 혼합 → INSUFFICIENT 만 생김)
```

농장 식별은 운영자 화면에서만. 이 문서·보고서에는 농장 수와 sha256 마스킹 id 만 적는다.

## 2. 기록 규칙 (농장에 주는 안내 — 계약이 아니라 사용 규칙)

```text
언제      월 1회 (월말 또는 다음 달 초). 일별 입력도 허용 — 엔진은 월 합산이라 결과 동일
무엇을    그 달에 **돼지에게 준 사료 총량** (kg). 입고량·재고가 아니다   ← AS_RECORDED 안에서 "급여" 로 통일해 기록
                                                                          (의미 확정 UNRESOLVED-1 은 이 관찰로 닫을 근거를 모은다)
사료 종류  사용한 사료별로 행을 나눈다 (예: 비육 전기 / 비육 후기). 한 종류만 쓰면 1행. 이름은 농장이 쓰는 이름 그대로 — 표준어휘 강요 없음
단가      kg 당, 농장 통화. 톤당·포대당이면 농장이 kg 당으로 나눠 넣는다 (환산 책임 = 사용자, 감사 §7)
          ★ 단가를 모르는 행은 비워 둔다. 추정값을 넣지 않는다 → 그 달 FEED_COST 는 partial 로 표시되는 것이 **정상**
기간      최소 **연속 2개월** (예: 10월·11월) — CHANGE·VARIANCE 검증용. 3개월이면 prior_insufficient 경계도 본다
그룹      finisher_group 을 운영하는 농장만 group 선택 (P1 UI 뒤). 이번 v0 은 그룹 없음
```

농장이 안내 없이 스스로 입력하는지 보려면 **첫 달은 규칙 카드 1장만 주고 질문을 받는다** — 질문 목록이 곧 SEMANTIC_AMBIGUITY 의 실측이다.

## 3. 관찰 항목 (입력 기간 중, 읽기 전용)

| 축 | 관찰 | 방법 |
|---|---|---|
| 도달 | 페이지 도달 → 저장 전환 | nginx `GET /feed` 대비 `POST feed-records 201` (`scripts/feed_input_nginx_audit.sh`) |
| 오류 | 4xx/5xx 유형 | 同 (422 = 검증, 423 = 월마감, 404 = 대상) |
| 의미 질문 | 농장이 물어본 것 | 운영자 기록 (자유 텍스트, 문서에는 유형만) |
| 입력 형태 | 월 1행 vs 일별 다행 · 사료 종류 수 · 단가 기입률 | `api/scripts/feed_engine_real_data_audit.py` (F4 하네스, 덤프 대상) |
| 통화 | farm.currency 와 다르게 넣었는지 | 同 (currency_mixed 발화) |

## 4. 성공 기준 (사전 고정 — 숫자 임계는 제품 결정이라 두지 않는다)

```text
S1  농장이 입력 경로를 **운영자 도움 없이** 완료한다                       (POST 201 이 그 농장 사용자로 기록)
S2  기록 규칙 카드만으로 입력한다 — 의미 질문이 있으면 유형별로 기록(0 을 요구하지 않는다)
S3  CORE 6 이 값을 낸다: FEED_QTY · FEED_MIX_SHARE (1개월) · FEED_UNIT_PRICE · FEED_COST (단가 전부 있을 때 ACTUAL)
S4  partial/missing 이 정확히 표시된다 — 단가 없는 행이 있으면 FEED_COST = INSUFFICIENT(partial_cost) 이고 0 으로 보이지 않는다
S5  2개월째에 FEED_QTY_CHANGE · FEED_COST_CHANGE 가 값을 내고, VARIANCE 가 PRICE+VOLUME+MIX = TOTAL 을 만족한다
S6  입력값 ↔ 계산값 수기 대조 일치 — 농장이 넣은 행을 손으로 합산한 값과 엔진 값이 반올림 규칙 안에서 같다 (독립 SQL 대조, F4 방식)
```

S3·S5 는 **표시가 아니라 계산**으로 확인한다 — UI 노출은 이 파일럿의 범위가 아니다(D-15/B-7 결재). 확인 경로 = F4 하네스(덤프 대상, 프로덕션 쓰기 0).

## 5. 판정과 종료

```text
PILOT_INPUT_COMPLETED      농장 수 / 대상 수 · 2개월 연속 확보 농장 수
CORE_REAL_VALUES           S3 충족 농장-월 수
COST_COMPLETE_RATE         단가 전부 있는 농장-월 / 전체 농장-월     (PHASE0 G-E 대입은 사람이)
SEMANTIC_QUESTIONS         유형별 건수 → UNRESOLVED-1 결재 자료
UNEXPECTED                 엔진 불일치(있으면 ENGINE_BUG 절차 F4 §15) · 데이터 이상(DATA_QUALITY)
```

종료 후 결정은 두 갈래뿐이고 여기서 정하지 않는다: (a) 입력 경로 확장(그룹·모바일·CSV) (b) 자동 연계 우선(PigPlan 사료 테이블이 AVAILABLE 일 때).

## 6. 하지 않는 것

- 운영자 대리 입력 · 테스트 행 · 백필 · 시드
- 임계·벤치마크·FCR 노출·과금 판단
- quantity 의미 계약 변경 (관찰만)
- 그룹 축 (open finisher_group 0 인 동안)
- 새 화면 (P0 필드 추가 외)
