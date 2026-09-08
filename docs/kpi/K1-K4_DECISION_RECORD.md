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
| **K-2** | 분만율 정본 | **APPROVED** 2026-09-08 | 안 C — 병존 + 이름 분리 |
| **K-3** | NPD·PSY 모집단 | **PENDING** | 유력안 = 안 D(교배모돈). §5-1 쿼리 결과 대기 |
| **K-4** | 라벨 정책 | **PENDING** | K-1~K-3 확정 후 |

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

2  ★ definition_id 승격 검토
   benchmarks 는 (kpi_code, definition_id) 복합 FK 로 정의에 묶여 있다
   (models/benchmark.py:108-113 ★④). definition_id 는
   PIGOS_<UPPER>_V1 로 고정 생성된다(benchmark_seed.py:73-74).
   V1 의 분자를 제자리에서 바꾸면 **버전이 의미를 잃는다.**
   → PIGOS_STILLBIRTH_RATE_V2 신설이 맞는지 결정 필요.

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

### 결정

**두 산식은 서로 다른 KPI다. 병존시키고 이름을 분리한다.**

```
FARROWING_RATE_FIRST_SERVICE_COHORT
    초교배 분만율. mating_number = 1, 115일 내 폐사 모돈 분모 제외
    현 kpi_service.py:370-387 = 이 지표

FARROWING_RATE_ALL_SERVICES
    총교배 분만율. 전 교배 대비 분만
    현 trend SQL · report_service · jobs/kpi.py = 이 지표

외부 비교 정본 = FARROWING_RATE_ALL_SERVICES
    pig333 · PigCHAMP "mated females … reach farrowing" = 전 교배 기준
```

국가 표시 정책이 어느 쪽을 "분만율"로 보여줄지는 **K-4 이후**에 정한다.

### 근거

두 산식은 창이 다른 게 아니라 **모집단이 다르다** — 하나는 재발정 재교배를 전부
빼고, 다른 하나는 전부 넣는다. 서로 다른 질문에 답하므로 하나로 합치면 정보가
사라진다. 지금의 결함은 **둘이 같은 `farrowing_rate` 이름을 쓰는 것**이다.

### 고칠 것 — ★ 이름 하나가 아니다

```
정의·벤치마크 (마이그레이션 — 별도 승인 필요)
  db/benchmark_seed.py:28              kpi_code="farrowing_rate" → 2행으로 분리
  alembic e1a3c5d7f9b2:62-69           US 분만율 벤치마크(verified) 는
                                       ALL_SERVICES 로 귀속. 복합 FK 갱신 필요

metric_code 사용처 (백엔드)
  db/global_policy_defaults.py:28      GLOBAL_VISIBLE
  db/global_presentation_seed.py:25    display_order
  db/br_pilot_seed.py:23               "Taxa de Parto" 현지 라벨
  engine/rules/base.py:156,160,175     farrowing.low_rate 룰
  services/kpi_status_assembler.py:32  DASHBOARD_POLICY_KPIS
  services/report_service.py:291,298   metric_code IN (...) SQL 리터럴
  services/scorecard_service.py:9
  services/benchmark_service.py:226    거버넌스 매핑
  schemas/kpi.py:45,117 · schemas/report.py:230,238 · schemas/scorecard.py:14

프론트 / i18n
  src/types/api.types.ts               응답 필드
  src/messages/*.json                  ★ 8개 로케일 전부 (CLAUDE.md §4)
                                       en/ko/zh/es/vi/th/pt/ru — "farrowingRate" 라벨
```

★ **API 계약 변경이다.** `CLAUDE.md` §5 — 모바일은 독립 저장소 2개이고 배포 주기가
길어 구버전이 오래 남는다. 필드명 변경은 기능 변경보다 위험하다.
→ `docs/PLATFORM_PARITY.md` 한 줄 추가 대상이며, **기존 `farrowing_rate` 필드를
당분간 유지하는 이행 경로**를 설계에 포함해야 한다.

★ 스냅샷 잡(`jobs/kpi.py:185-187`)은 현재 전건 실패 중이므로 이 분리에서 제외하지
말 것. 지금 안 맞춰두면 파이프라인 복구 시 세 번째 값이 생긴다.

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

### 대기 중인 것

`§5-1` 쿼리 3건(전부 SELECT, Brian 직접 실행). K-3 쿼리는 **경산돈 vs 교배모돈 vs
전체활성** 3종 모집단을 세도록 교체했다.

★ 결과의 성격은 **산식 감도**다. 모집단이 하베스트 42농장이므로 "고객 영향"이
아니다. 실고객 7농장은 최대 7두라 표본이 안 나온다.

### 확정 후 따라오는 것

```
스냅샷 잡(후보돈 포함) vs 라이브(parity>=1) 를 한쪽으로 통일
★ 반드시 K-3 확정 이후. 순서를 뒤집으면 "스냅샷을 고쳤더니 PSY 가 떨어졌다"가 된다
```

---

## 4. K-4 — 라벨 정책 (PENDING)

K-1~K-3 이 만든 명칭 부채를 여기서 정리한다.

```
K-2  FARROWING_RATE_FIRST_SERVICE_COHORT / _ALL_SERVICES 중
     국가별로 무엇을 "분만율"로 표시할 것인가
K-3  안 D 채택 시 — 분모가 mated female 인 지표를 계속 PSY 로 부를 것인가
K-1  stillbirth / mummy / birth loss 3종의 표시 라벨
```

---

## 5. 실행 순서

```
1  Brian — §5-1 SELECT 3건 실행                                    ← 현재 대기
2  결과 → K-3 영향표 작성 → K-3 확정
3  K-4 확정
4  구현 착수 (마이그레이션 승인 별도)
     K-1 정의 정정 + 벤치마크 재도출
     K-2 kpi_code 분리 + 8로케일 + PLATFORM_PARITY
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
