# K-1~K-4 결정문 — KPI canonical 정본

> **성격**: `T6 §0` 3축 중 **③ CANONICAL DECISION** 의 기록
> **결재**: Brian · 2026-09-08
> **입력**: `docs/kpi/K1-K3_PRE_DECISION_EVIDENCE.md` (① RUNTIME) + `T6 §5-1`
> **산출**: 이 문서 · 코드 수정 0건 · 마이그레이션 0건 · DB 쓰기 0건

---

## 0. 현재 상태

| # | 항목 | 상태 | 비고 |
|---|---|---|---|
| **K-1** | 사산율 분자 | **APPROVED** 2026-09-08 | 안 A — 사산만 |
| **K-1b** | 정의 버전 처리 | **APPROVED** 2026-09-08 | V2 신설 · V1 RETIRED |
| **K-2** | 분만율 정본 | **APPROVED** 2026-09-08 | 안 C — 병존 |
| **K-2b** | 필드 전략 | **APPROVED** 2026-09-08 | 기존 필드명 유지 · 신규 필드 추가 |
| **K-2c** | 분모 단위 | **PENDING** | 권고 female-cycle. ★ 현행 코호트가 이미 그것 |
| ★ **K-2 재확인** | 병존이 맞는가 | **REOPENED** | 전제였던 `mating_number` 해석이 틀렸다 |
| **K-3** | NPD·PSY 모집단 | **PENDING** | 유력안 = 안 D(교배모돈). §5-1 쿼리 결과 대기 |
| **K-4** | 명칭 | **조건부 APPROVED** | 내부 정의 ID 확정. 표시명은 K-3 확정 후 |

★ **APPROVED 는 ③ 확정이지 배포가 아니다.** 아래 구현 항목은 전부 미착수이며,
`kpi_definitions`·`benchmarks` 를 건드리는 마이그레이션은 별도 승인이 필요하다
(세션 하드룰: 스키마·마이그레이션은 멈추고 리포트).

---

## 1. K-1 — 사산율 분자

### 결정

```
stillbirth_rate  = 사산 / 총산                    ← 미라 제외
mummy_rate       = 미라 / 총산                    ← 별도 지표 유지
birth_loss_rate  = (사산 + 미라) / 총산           ← 합성 지표로 유지
```

### 근거

계산 경로가 이미 이렇게 하고 있고(`kpi_service.py:523-524`,
`report_service.py:195-197`), 외부 A급 관행과 정확히 일치한다 — NPB 는
`Percent Stillborn` 과 `Mummified` 를 분리하고 `Birth Loss` 를 합성으로 둔다.

★ **이것은 "코드가 그러니까 맞다"가 아니다.** 외부 관행이 독립적으로 같은 분리를
지지하기 때문에 코드 쪽으로 수렴시키는 것이다. 근거가 반대였다면 코드가 움직였을
것이다(`T6 §0` — 수렴 방향은 ③이 정한다).

### 고칠 것

```
1  db/benchmark_seed.py:47
   numerator_def  "사산+미라" → "사산"
   notes          "PigOS 비표준 분자(미라 포함)" 제거
                  ★ 제거해야 한다. 이 문장이 남으면 정정된 정의와 모순된다.

2  definition_id — K-1b 로 결정됨(아래). V2 신설 · V1 RETIRED.
   ★ 그러므로 1 은 "V1 의 numerator_def 를 고치는 것"이 아니라
     "V2 행을 새로 넣는 것"이다.

3  US PigCHAMP 벤치마크 재도출  (alembic e1a3c5d7f9b2:70-77)
   현재  transform_formula "(stillborn+mummified)/total_born*100"
         benchmark_status  normalized_verified
   개정  transform 불필요 → mapping/comparison = exact → verified 로 승격
   ★ 새 외부 조사 불필요 — raw_fields_json 에 사산·미라가 분리 보존돼 있다.

4  (선택) mummy_rate US 벤치마크 신설
   보존된 미라 수치로 세울 수 있다. 현재 US 행 없음.

5  benchmark_service.py:227 매핑은 **그대로 둔다.**
   STILLBORN_RATE → stillbirth_rate 는 1의 정정 후 정합이 된다.
   매핑이 틀린 게 아니라 정의가 틀렸던 것이다.
```

★ **`benchmark_service.py:227` 을 고치지 않는 이유**를 명시해 둔다. 증거 문서가
이 줄을 문제 지점으로 지목했기 때문에, 손대지 않는 판단을 남기지 않으면 다음
작업자가 "누락"으로 읽는다.

### K-1b — 정의 버전 처리 (APPROVED)

```
PIGOS_STILLBIRTH_RATE_V1   RETIRED       분자 "사산+미라" — 의미 보존
PIGOS_STILLBIRTH_RATE_V2   신설·정본     분자 "사산"
```

**V1 을 제자리에서 고치지 않는다.** `benchmarks` 가 `(kpi_code, definition_id)`
복합 FK 로 정의를 가리키므로, V1 의 분자를 바꾸면 그 id 를 가리키는 **과거 벤치마크와
리포트가 무엇을 뜻했는지가 사라진다.** 버전은 그러라고 있다.

```
US PigCHAMP 벤치마크
  raw_fields_json 에서 사산만으로 재도출 → V2 에 바인딩
  transform 불필요 → mapping/comparison = exact → benchmark_status = verified
  ★ 같은 마이그레이션에서 mummy_rate 벤치마크도 함께 세운다(보존된 미라 수치)
```

★ `definition_id_for()` 가 `PIGOS_<UPPER>_V1` 을 **하드코딩 생성**한다
(`benchmark_seed.py:73-74`). V2 를 도입하려면 이 함수가 버전을 고정 반환하지 못한다 —
정의별 버전 테이블/맵이 필요하다. **K-1b 구현의 실제 진입점은 이 함수다.**

### 배포 게이트 (★ 조건부)

```
use_governance_benchmarks = True 로 켜기 전에 위 1~3 이 완료돼야 한다.
```

플래그가 켜진 상태에서 정의만 옛것이면, 미라를 뺀 값이 미라를 포함한 벤치마크와
비교된다. `lower_better` 라 **항상 유리한 쪽으로** 왜곡된다 — 위조 0 위반이다.

★ 코드 기본값은 `False`(`core/config.py:77`)이나 **프로덕션 env 값은 미확인**이다.
`§5-1` 조회가 열리면 이것을 가장 먼저 확인한다. 이미 켜져 있다면 위 순서가
"배포 전 준비"가 아니라 "현재 오노출 수정"이 된다.

---

## 2. K-2 — 분만율 정본

### ★★ REOPENED — K-2 의 전제가 틀렸다 (2026-09-08)

K-2 를 "두 산식은 서로 다른 KPI 다"로 결정한 근거는 **`mating_number = 1` 이
개체 생애 초교배를 뜻한다**는 내 판독이었다. 그 판독이 틀렸다.

```
event_service.py:236-247   mating_number 는 breeding_cycle_id 범위 안에서 매겨진다
event_service.py:249-258   새 사이클 → 1
→ 사이클마다 정확히 1건이 mating_number = 1
→ mating_number = 1 은 female-cycle 단위다 (초교배가 아니다)
```

사고(RTS·EMPTY·INFERTILE·ABORTION) 시 사이클이 `FAILED` 로 닫히고 재교배는 새
사이클을 연다(`event_service.py:603,616,622,705`). **실패한 사이클은 분모에 남고
분자에 안 잡힌다** — 실패로 정확히 계산된다. 빠지는 것은 같은 사이클 안의
중복 교배뿐이다.

### 그래서 실제 대비는 이렇다

```
                  집계 창           분모 단위
①-a  코호트       코호트 창         female-cycle
①-b/c/d  동기간   동월·동기간       service
```

**두 축이 동시에 다르고, ①-a 가 양쪽 다 관행에 가깝다.** 동기간식은 관찰 미완료를
실패로 처리하고(창), 재교배로 분모를 부풀린다(단위).

★ **그러므로 "다른 질문에 답하는 두 KPI" 라는 병존 근거가 약하다.**
①-a 는 ①-b/c/d 의 **더 나은 구현**일 수 있다. 그렇다면 K-2 는 병존(C)이 아니라
**코호트 정본 통일(A)** 이 맞고, 신규 필드 `farrowing_rate_first_service` 는
**만들 대상이 없어진다** — 진짜 "초교배 분만율"은 현재 어느 경로도 계산하지 않는다.

```
Brian 재확인 필요
  (가) 코호트 정본 통일 — 지표 1개. 신규 필드 없음
  (나) 병존 유지 — 단, 두 번째 지표를 새로 정의해야 한다
       (예: 초산돈 초교배 분만율 · 생애 초교배 분만율)
       ★ 현행 코드에는 없다. 신규 산식이다
```

★ 코드 주석도 같은 오류다 — `kpi_service.py:371` "초교배(mating_number=1)".
SPEC_DRIFT 로 등록 대상.

### K-2c — 분모 단위 (PENDING · 권고 female-cycle)

```
service 단위        같은 주기 재교배 2회 → 분모 2
female-cycle 단위   같은 주기 재교배 2회 → 분모 1, 분만 1
```

pig333("sows mated in period")과 PigCHAMP("% of mated females")가 갈리는 지점이며
`T6-09` 에 다시 걸린다. **권고는 female-cycle** — 재교배가 분모를 부풀려 분만율을
낮추는 왜곡이 없고 PigCHAMP 정의와 정합한다.

★ **현행 코호트 경로가 이미 female-cycle 이다.** 즉 K-2c 권고를 채택하면
`_cohort_farrowing_rate` 는 **그대로 두는 것이 맞다.** 아래 "고칠 것"에서
"`mating_number = 1` 조건을 뺀다"고 적었던 것은 **service 단위로 되돌리는
행위**이므로 K-2c 와 정면으로 충돌한다 — 철회한다.

### 결정 (K-2 + K-2b) — ★ 위 재확인 결과에 따라 달라짐

**두 산식은 서로 다른 KPI다. 병존시킨다. 단 API 필드명은 바꾸지 않는다.**

```
farrowing_rate                 기존 필드명 유지
                               개념 = 총교배 분만율 (전 교배 대비 분만)
                               ★ 산식은 동월 나눗셈 → 코호트 창으로 교체 = 값이 바뀐다

farrowing_rate_first_service   신규 필드
                               개념 = 초교배 분만율 (mating_number = 1)
                               현 kpi_service.py:370-387 이 이 지표

외부 비교 정본 = farrowing_rate (총교배)
    pig333 · PigCHAMP "mated females … reach farrowing" = 전 교배 기준
```

### ★ K-2b 가 바꾸는 것 — 이름이 아니라 의미를 고정한다

초판 결정문은 `kpi_code` 를 `FARROWING_RATE_ALL_SERVICES` /
`_FIRST_SERVICE_COHORT` 로 **양쪽 다 개명**하는 안이었다. K-2b 는 그것을 뒤집는다.

```
개명한다     구버전 모바일이 읽던 필드가 사라진다 — API 계약 파괴
의미 고정    필드명은 그대로, "이 이름은 총교배를 뜻한다"를 확정하고
             왜곡 요인(동월 나눗셈)만 제거한다
```

**구버전 모바일은 기존 필드로 계속 읽는다.** 값은 달라지지만 계약은 유지된다.
이쪽이 `CLAUDE.md` §5(모바일 배포 주기가 길다 · API 계약 변경이 기능보다 위험)와
정합한다.

★ **대신 값이 조용히 바뀐다.** 같은 이름 · 같은 필드에서 숫자만 달라지므로
**What Changed 고지가 필수**다. 이것은 버그 수정이 아니라 정의 변경이다.

### 고칠 것

```
계산
  kpi_service.py:370-387   ★ 철회 — 초판은 "mating_number = 1 조건을 빼서
                           전 교배 코호트를 만든다"고 적었다. 그것은 분모를
                           service 단위로 되돌리는 것이라 K-2c 권고와 충돌한다.
                           현행 코호트 SQL 은 그대로 둔다.
  kpi_service.py:786-797   trend SQL — 동월 나눗셈 → 코호트 창
  report_service.py:182    기간 나눗셈 → 코호트
  jobs/kpi.py:185-187      ★ 같은 코호트로. 지금 안 맞추면 복구 시 세 번째 값이 생긴다

정의·벤치마크 (마이그레이션 — 별도 승인)
  db/benchmark_seed.py:28  farrowing_rate 정의에 "전 교배" 명시 + 신규 지표 1행
  alembic e1a3c5d7f9b2:62-69
                           US 분만율 벤치마크(verified)는 farrowing_rate(총교배)에
                           그대로 귀속 — ★ 이 행은 손대지 않아도 된다
                           (PigCHAMP 도 전 교배 기준이므로 정의 정합이 유지된다)

노출
  schemas/kpi.py · report.py · scorecard.py    신규 필드 추가(기존 유지)
  src/types/api.types.ts                        〃
  src/messages/*.json                           ★ 8 로케일 — 신규 라벨 1개 추가
                                                기존 "farrowingRate" 는 유지
  docs/PLATFORM_PARITY.md                       신규 필드 1행
```

★ 기존 필드를 유지하므로 **8 로케일은 개명이 아니라 추가**다. 초판이 예상한
개명 작업(정책·표현 시드 · 룰 · SQL 리터럴 · 스코어카드의 metric_code 일괄 변경)은
**대부분 불필요해진다.**

---

## 3. K-3 — NPD·PSY 모집단 (PENDING)

### ★ 유력안은 A/B/C 밖에 있다 — 안 D 등록

증거 문서는 선택지를 `A 제외 유지 / B 후보돈 포함 / C 국가별 플래그` 로 적었다.
**셋 다 `parity` 를 모집단 기준으로 쓰는 것을 전제**했고, 그래서 발견 3(소급 귀속)이
어느 안에서도 해소되지 않았다.

```
안 D   모집단 기준을 parity 가 아니라 초교배일(first service date) 로 바꾼다
       = NPB · PIC "mated female inventory"
```

**발견 3 이 소멸한다.** `parity` 는 시점 속성이라 12개월 창에 소급 적용되지만,
초교배일은 **사건 시각**이라 창 안에서 정확히 나뉜다. "언제부터 모집단인가"에
답이 생긴다.

### ★ 부수 효과 — US PWMFY 벤치마크가 살아난다

```
alembic e1a3c5d7f9b2:52-55 · :78-85
  US PWMFY(분모=교배모돈) ≠ PigOS PSY(상시모돈) → incompatible → benchmark_status=missing
  "직접 비교 금지. PigOS KPI 미승격(D-4 보류)"
```

이 행이 `missing` 인 **이유가 바로 이 모집단 차이**다. 안 D 를 택하면 분모가
`mated female` 이 되어 비교가 성립한다 — 미국 시장에서 쓸 수 있는 벤치마크가
`missing` 에서 실사용 가능으로 바뀐다.

★ **동시에 K-4 문제를 만든다.** 분모가 mated female 이 되면 그 지표는 사실상
PWMFY 다. 그걸 계속 `PSY` 라고 부르면 이름이 또 어긋난다(T6-22 재발).
**안 D 를 채택하면 K-4 에서 이 명칭을 반드시 함께 정해야 한다.**

### 대가

```
PigPlan 035001(경산돈) 정합 상실
  kpi_service.py:81-82 주석의 대조가 근거였다
  KR 은 PigOS 공개 타겟이 아니므로(CLAUDE.md) 비용이 작다 — Brian 판단
```

### ★ 안 D 채택 조건 — 모집단이 NPB 정의와 같은가 (1줄 명시)

US PWMFY 벤치마크의 `missing` 을 푸는 것은 **모집단이 NPB
`Average Mated Sow Inventory` 와 정확히 같을 때만** 정당하다. 대조한다.

```
NPB       편입 = 초교배 시점 (후보돈은 교배 순간 편입)
          이탈 = 제적 시점
          집계 = 기간 평균

안 D      편입 = 첫 mating 행 (deleted_at IS NULL)           → 일치
          이탈 = sows.exit_date                              → 일치 (아래)
          집계 = 12개월 월별 평균 (라이브 PSY 분모와 동일)   → 일치
```

**이탈 판정이 일치하는 근거**: 종료 4종(`CULLED`·`DEAD`·`SOLD`·`TRANSFER_OUT`)이
모두 `exit_date` 를 설정한다(`event_service.py:591,602,609`). 라이브 PSY·NPD 는
`exit_date` 로만 판정한다(`kpi_service.py:88,138,146,172,198`).

★ **그러므로 `status NOT IN ('CULLED','DEAD')` 를 쓰면 안 된다.** 부정 목록이라
`SOLD`·`TRANSFER` 가 재고에 남아 NPB 정의와 어긋난다. 증거 문서 **발견 4** 참조 —
`§5-1` K-3 쿼리를 `exit_date IS NULL` 로 교체했다.

```
남는 유일한 차이   시점 스냅샷 vs 기간 평균
                   → §5-1 결과는 배수(감도) 용도. PSY 값 환산 불가
                   mated_ever 에 날짜 필터가 없는 것도 같은 이유의 근사다
```

**결론**: 위 3행이 확인되면 `missing` 해제가 정당하다. 확인 전에는 풀지 않는다.

### 대기 중인 것

`§5-1` 쿼리 3건(전부 SELECT, Brian 직접 실행). K-3 쿼리는 **경산돈 vs 교배모돈 vs
전체활성** 3종 모집단을 세도록 교체했다.

★ 결과의 성격은 **산식 감도**다. 모집단이 하베스트 42농장이므로 "고객 영향"이
아니다. 실고객 7농장은 최대 7두라 표본이 안 나온다.

### 확정 후 따라오는 것

```
스냅샷 잡 vs 라이브 를 한쪽으로 통일 — ★ exit_date 기준으로
  현재 스냅샷 잡 분모 오염은 후보돈만이 아니다(증거문서 발견 4)
    jobs/kpi.py:135  status NOT IN ('CULLED','DEAD')
    → 후보돈 + 판 모돈(SOLD) + 전출 모돈(TRANSFER) 이 전부 잔류
★ 반드시 K-3 확정 이후. 순서를 뒤집으면 "스냅샷을 고쳤더니 PSY 가 떨어졌다"가 된다
```

---

## 4. K-4 — 명칭 (조건부 APPROVED)

### 결정 — 내부 정의 ID

```
WEANED_PER_MATED_FEMALE_YEAR      = PWMFY 개념
    안 D 채택 시 PSY 를 대체하는 내부 정의 ID
```

산식이 맞아도 이름이 틀리면 사용자가 읽는 의미는 계속 어긋난다(T6-22).
분모가 mated female 인 지표를 `PSY` 로 부르는 것이 정확히 그 경우다.

### 국가 표시명 — 정책층 (K-3 확정 후)

```
US    "PWMFY" 직결 — NPB 용어와 그대로 맞는다

BR    ★ 주의. Agriness `DFA` 는 역산 개념이라
      "PSY/DFA" 로 표시하면 T6-22 가 재발한다
      → "desmamados/fêmea coberta/ano" 계열로 표시하거나 배지로 구분

전 국가  ★ 정의 배지 필수 — 배지 없이 이름만 쓰면
         같은 라벨이 시장마다 다른 것을 뜻한다
```

★ 표시명은 `ADR-KPI-00` 의 **CKPRES(표현)** 계층이다. 내부 정의 ID 는
**계산·거버넌스** 계층이다. 둘을 같은 결정으로 묶지 않는다 — I-1 이 그 경계다.

### 아직 안 정한 것

```
K-2  farrowing_rate / farrowing_rate_first_service 중
     국가별로 무엇을 "분만율"로 표시할 것인가
K-1  stillbirth / mummy / birth loss 3종의 표시 라벨
```

---

## 5. 실행 순서

```
1  Brian — §5-1 SELECT 3건 + 프로덕션 use_governance_benchmarks   ← 현재 대기
     ★ env 가 True 면 K-1 은 P0 격상 (현재 오노출)
2  결과 → K-3 영향표 작성 → K-3 확정
3  K-4 확정
4  구현 착수 (마이그레이션 승인 별도)
     K-1/K-1b  V2 신설 + V1 RETIRED + 벤치마크 재도출(+mummy_rate)
     K-2/K-2b  코호트 산식 통일 + 신규 필드 추가 + What Changed 고지
               ★ 기존 필드명 유지 — 개명 아님
5  D-19 검증 3건 — PSY(reference implementation) → NPD → 분만율
```

★ **4 를 1~3 보다 먼저 시작하지 않는다.** K-3 이 PSY 분모를 바꾸면 D-19 의 PSY
검증을 다시 해야 한다.

---

## 6. 관련

```
docs/kpi/K1-K3_PRE_DECISION_EVIDENCE.md          ① RUNTIME · §5-1 쿼리
docs/kpi/T6_DEFINITION_CONFLICT_REGISTER.md      §0 3축 · §5-1 K-1~K-4
docs/adr/ADR-KPI-00-one-engine-many-policies.md  I-1 · §5 Non-Goals
api/app/db/benchmark_seed.py:47                  K-1 정의 정정 대상
api/alembic/versions/e1a3c5d7f9b2_work_us_pigchamp_load.py
                                                 K-1 재도출 · K-2 귀속 · K-3 PWMFY
docs/PLATFORM_PARITY.md                          K-2 API 계약 변경 등재 대상
```
