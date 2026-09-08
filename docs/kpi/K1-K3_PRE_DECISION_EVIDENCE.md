# K-1~K-3 PRE-DECISION EVIDENCE — 현재 런타임과 선택지별 영향

> **RUN**: `KPI-K13-PREDECISION-EVIDENCE` · 2026-09-08 · machine `bjh`
> **위치**: `T6 §5-1` 실행 흐름의 `PRE-DECISION EVIDENCE` 단계
> **산출**: 이 문서 · 코드 수정 0건 · DB 쓰기 0건

---

## 0. 이 문서가 하는 일과 하지 않는 일

`T6 §0` 3축 구분에 따른다.

```
이 문서가 채우는 것    ① RUNTIME — 프로덕션 코드가 실제로 무엇을 계산하는가
                       + 선택지별로 값이 어느 방향으로 움직이는가

이 문서가 하지 않는 것  ② DOCUMENTED 수정
                       ③ CANONICAL 확정
                       CONFIRMED 판정
                       코드 수정
```

★ **이것은 D-19 가 아니다.** D-19 는 ①과 ②의 간극을 증거로 확정하는 절차이고,
이 문서는 그 앞에서 **결재자가 K-1~K-3 을 고르는 데 필요한 입력**만 만든다.
여기서 "현재 코드가 이렇게 한다"를 읽고 "그러니 그게 정본이다"로 넘어가면
3축 구분이 무너진다. **기존 코드는 후보이지 기준이 아니다.**

---

## 1. K-1 — 사산율 분자 (미라 포함 vs 제외)

### ① 런타임 — 한 제품 안에 두 값이 이미 함께 있다

| # | 경로 | 산식 | 노출면 |
|---|---|---|---|
| ①-a | `services/kpi_service.py:523` `STILLBORN_RATE` | `SUM(stillborn) / SUM(total_born)` — **미라 제외** | 대시보드 · 룰 엔진 |
| ①-b | `services/kpi_service.py:524` `MUMMIFIED_RATE` | `SUM(mummified) / SUM(total_born)` | 〃 |
| ①-c | `services/report_service.py:195` `stillborn_rate` | 사산 / 총산 — **미라 제외** | 리포트 |
| ①-d | `services/report_service.py:197` → `:218` `birth_loss_rate` | `(사산+미라) / 총산` | 리포트 |

즉 **"사산+미라" 합성 지표는 이미 런타임에 있다.** 다만 그 이름이
`stillbirth_rate` 가 아니라 `birth_loss_rate` 다.

이것은 K-1 의 성격을 바꾼다. 선택지는 "미라를 셀 것인가"가 아니라
**"`stillbirth_rate` 라는 이름이 둘 중 어느 것을 가리키는가"** 다.
두 값 모두 이미 계산되고 있다.

### ★ 이름이 어긋나는 지점 — 벤치마크 비교

```
services/benchmark_service.py:227
    "STILLBORN_RATE": "stillbirth_rate"      ← 룰 KPI → 거버넌스 kpi_code 매핑

db/benchmark_seed.py:47
    kpi_code="stillbirth_rate"  numerator_def="사산+미라"
    notes="PigOS 비표준 분자(미라 포함)"
```

**미라를 뺀 값(①-a)을 미라를 포함한 정의의 벤치마크에 갖다 댄다.**
`direction=lower_better` 이므로 편향 방향은 결정돼 있다 — 우리 값이 실제보다
**낮게(좋게)** 보인다. 크기는 그 농장의 미라율만큼이다.

★ **다만 지금 살아 있다고 단정할 수 없다.** 이 비교는 `use_governance_benchmarks`
플래그가 켜져야 실행된다.

```
core/config.py:77         use_governance_benchmarks: bool = False   ← 코드 기본값
kpi_service.py:896        if settings.use_governance_benchmarks:
chat_service.py:84        if settings.use_governance_benchmarks:
```

**프로덕션 env 의 실제 값은 이번에 확인하지 못했다(§5 차단).** 코드 기본값이
False 라는 것까지가 확인된 사실이다. 플래그가 프로덕션에서 켜져 있다면 이 항목은
잠재 결함이 아니라 현재 오노출이므로, **§5 해제 시 첫 번째로 확인할 것.**

### ★ 레지스트리 자체의 중복

```
benchmark_seed.py:47   stillbirth_rate  = 사산 + 미라
benchmark_seed.py:50   mummy_rate       = 미라
```

두 행을 함께 쓰면 **미라가 두 번 세어진다.** 어떤 선택을 하든 이 중복은 정리
대상이다 — K-1 이 "제외"로 결정되면 `:47` 의 `numerator_def` 가, "포함"으로
결정되면 계산 경로 ①-a·①-c 가 바뀐다. **어느 쪽이든 한쪽은 반드시 움직인다.**

### 선택지와 영향

| 안 | 내용 | 코드 영향 | 문서 영향 | 값 변화 방향 |
|---|---|---|---|---|
| **A** 미라 제외 (NPB 관행) | `stillbirth_rate` = 사산만. 미라는 `mummy_rate`, 합계는 `birth_loss_rate` | 계산 경로 불변 (①-a 유지) | `benchmark_seed.py:47` + **정의·벤치마크 마이그레이션** | 표시값 불변 |
| **B** 미라 포함 | `stillbirth_rate` = 사산+미라 | ①-a·①-c 변경 | 없음 | **상승** — 정확히 미라율만큼 |

### ★ 2026-09-08 정정 — 안 A 를 "코드 0줄"로 적었던 것은 틀렸다

초판은 A 의 비용을 "`numerator_def` 1줄"로 적었다. **적재된 벤치마크 행을 보지 않고
쓴 판단이었다.**

```
alembic/versions/e1a3c5d7f9b2_work_us_pigchamp_load.py:70-77
    kpi_code="stillbirth_rate"
    transform_formula = "(stillborn+mummified)/total_born*100"
    benchmark_status  = "normalized_verified"
    notes             = "PigCHAMP 사산·미라 분리 → (사산+미라)/총산 재계산.
                         PigOS stillbirth_rate 정의일치."
```

이 행은 **우리 정의가 "사산+미라"라는 전제 위에서 정규화된 값**이다. 정의를 "사산만"으로
바꾸면 이 값은 더 이상 그 정의의 값이 아니다. 방치하면 위조 0 위반이 벤치마크 쪽에서
그대로 발생한다.

★ **다만 재도출에 새 외부 조사는 필요 없다.** 원자료가 분리 보존돼 있다.

```
:49-52  source_observations.raw_fields_json
        {"total_born": …, "stillborn": …, "mummified": …}
```

`Benchmark` 모델 주석의 `★⑩ 분리항목 보존` 설계가 정확히 이 상황을 위해 있었고,
의도대로 작동한다. 재도출하면 `transform_formula` 가 필요 없어져
`normalized_verified` → **`verified`(exact)** 로 오히려 올라간다. 보존된 미라 수치로
`mummy_rate` 벤치마크를 새로 세울 수도 있다(현재 US 행 없음).

**결론: A 의 비용은 "1줄"이 아니라 "마이그레이션 1건"이다.** 그래도 B 보다 싸고,
결과물의 등급은 더 높다. 정정 후에도 방향은 바뀌지 않는다.

---

## 2. K-2 — 분만율 정본 (교배 코호트 vs 동기간 나눗셈)

### ① 런타임 — 경로 4개, 그중 3개가 같은 방식

| # | 경로 | 산식 | 노출면 |
|---|---|---|---|
| ①-a | `kpi_service.py:370-387` `_cohort_farrowing_rate` | ref 기준 **110~150일 전 초교배(`mating_number=1`)** 중 분만 성공 비율. 교배 후 115일 내 폐사 모돈은 분모 제외 | 대시보드(`:520`) |
| ①-b | `kpi_service.py:786-797` trend SQL | 월별 `farrowings / matings` | `/kpi/trend` |
| ①-c | `report_service.py:182` | 기간 `farrowings / matings` | 리포트 |
| ①-d | `jobs/kpi.py:185-187` | 기간 `farrowings / matings` | 스냅샷 잡 (**현재 전건 실패 — CLAUDE.md**) |

### ★ 두 방식은 창(window)만 다른 게 아니다 — 모집단이 다르다

이것이 이 항목에서 가장 중요한 사실이다.

```
코호트(①-a)      mating_number = 1 만       → 재발정 재교배가 분모·분자에서 전부 빠진다
                 교배 후 115일 내 폐사 제외  → 관찰 불능 개체를 실패로 세지 않는다

동기간(①-b/c/d)  모든 교배                  → 재교배 포함
                 폐사 보정 없음              → 관찰 미완료·중도 이탈을 실패로 처리
```

따라서 ①-a 는 **초교배 수태 성공률**에 가깝고, ①-b/c/d 는 **총 교배 대비
분만 산출률**이다. 이름이 같을 뿐 **묻는 질문이 다르다.**

방향은 두 힘이 반대로 작용한다 — 재교배가 성공하는 만큼 동기간식이 올라가고,
관찰 미완료를 실패로 세는 만큼 내려간다. **순효과의 부호조차 산식만으로는
단정할 수 없다.** 실측이 필요한 이유가 여기 있다(§5).

### 선택지와 영향

| 안 | 내용 | 코드 영향 |
|---|---|---|
| **A** 코호트 정본 | ①-b/c/d 를 코호트로 통일 | 3개 경로 수정. trend 는 월별 코호트 창 재설계 필요 |
| **B** 동기간 정본 | ①-a 를 폐기 | 1개 경로 수정. 단 관찰 미완료 왜곡을 정본으로 채택하는 것 |
| **C** 둘 다 유지 + 이름 분리 | 예: `farrowing_rate` / `first_service_farrowing_rate` | 이름·라벨 작업. K-4 와 함께 처리 |

★ C 는 회피가 아니다. 두 지표가 실제로 다른 질문에 답한다면 **하나로 합치는 것이
오히려 정보 손실**이다. 다만 그 경우에도 어느 쪽이 대표값인지는 여전히 정해야 한다.

---

## 3. K-3 — NPD·PSY 모집단 (후보돈 제외 유지 여부)

### ① 런타임 — 라이브 경로는 후보돈을 일관되게 제외한다

```
PSY   kpi_service.py:86               inv: s.parity >= 1
NPD   kpi_service.py:137              inv
      kpi_service.py:143              sow_days
      kpi_service.py:160              preg
      kpi_service.py:170              preg_open
      kpi_service.py:186              lact
      kpi_service.py:196              lact_open
      kpi_service.py:204              fc (회전율 분자)
```

★ NPD 는 **분자·분모·재고가 모두 같은 모집단**으로 잠겨 있다. 일관성 자체는 좋다.

### ★ 발견 1 — `gilt_entry_included` 플래그는 존재하지 않는다

```
전체 저장소 검색 결과 1건
  db/benchmark_seed.py:46   notes="gilt_entry_included 플래그(D-1)"   ← 주석 문자열
```

`DRIFT-3` 은 "스펙은 제외 단정, 레지스트리는 플래그로 다룬다"고 적었다. 실제로는
**플래그를 읽는 코드가 0건**이다. 런타임에 스위치가 없으므로 이 대립은
"두 구현 중 택일"이 아니라 **"문서의 표현을 코드에 맞출 것인가, 코드에 스위치를
새로 만들 것인가"** 다.

### ★ 발견 2 — 스냅샷 잡의 PSY 분모에는 후보돈이 들어 있다

```
jobs/kpi.py:131-136   active = COUNT(sows WHERE status NOT IN ('CULLED','DEAD'))
                                                        ↑ parity 필터 없음 = 후보돈 포함
jobs/kpi.py:182       psy = total_weaned / active * (365/days)
```

라이브 경로는 `parity >= 1`, 스냅샷 잡은 전체 활성두수다. **같은 제품 안에서
PSY 분모가 두 가지다.**

지금은 드러나지 않는다 — 스냅샷 파이프라인이 71농장 전건 실패 중이기 때문이다
(`CLAUDE.md` KPI 현황 경고). 그러나 **파이프라인을 고치는 순간 PSY 가 조용히
내려간다.** 분모가 커지기 때문이다.

★ 이것이 K-3 을 스냅샷 복구보다 **먼저** 결정해야 하는 이유다. 순서를 뒤집으면
"스냅샷을 고쳤더니 PSY 가 떨어졌다"는 사고가 난다.

### ★ 발견 3 — `parity` 는 시점 속성인데 기간 필터로 쓰인다

`sows.parity` 는 분만 시 갱신되는 **현재 산차**다. 그런데 `sow_days`·`inv` 는
12개월 창 전체에 이 값을 적용한다. 창 안에서 초산한 모돈은 **후보돈이던 기간까지
소급해서** 경산돈 모집단에 들어간다.

이 비대칭은 K-3 을 "제외"로 결정하더라도 남는다 — **"언제부터 경산인가"**는
별개 질문이기 때문이다. 결정문에 이 문장이 함께 들어가야 한다.

### 이미 기록된 대조 (2026-07) — ★ 2차 증거

`kpi_service.py:81-82` 주석이 PigPlan 대조 결과를 남겨두었다.

```
후보돈 포함  431
경산만       323          → PigPlan 상시모돈 311 과 정합
```

★ **이 숫자는 이번 RUN 의 측정이 아니라 코드 주석의 기록이다.** 농장 1곳·시점 1회
기준이며, 재현 절차가 문서에 남아 있지 않다. 방향(포함 시 분모 ↑ → PSY ↓)의
근거로는 쓸 수 있으나, **결재 수치로 인용하기 전에 재측정해야 한다.**

### 선택지와 영향

| 안 | 내용 | 값 변화 |
|---|---|---|
| **A** 제외 유지 (현 라이브) | `parity >= 1` | 라이브 불변. `jobs/kpi.py` 를 맞춰야 함 |
| **B** 후보돈 포함 | 전체 활성두수 | PSY **하락**(분모 ↑). NPD **상승**(후보돈의 미교배 기간이 전부 비생산일) |
| **C** 플래그로 국가별 선택 | `gilt_entry_included` 신설 | ★ `ADR-KPI-00` I-1 위반 검토 필요 — 아래 |

★ **C 는 아키텍처 검토가 선행돼야 한다.** `ADR-KPI-00` I-1 은 "국가 표시 정책만
바꾸면 계산값은 바뀌지 않는다"이고, `test_one_engine_many_policies.py` 가 이를
강제한다. 모집단은 표현이 아니라 **계산의 정의**이므로, 국가별 스위치로 두면 같은
농장이 국가에 따라 다른 PSY 를 낸다. C 를 택하려면 그것을 정책층이 아니라
**metric variant(별도 kpi_code)** 로 두는 설계가 필요하다 —
`ADR-KPI-00` §5 Non-Goals 의 "정의가 다른 지표를 같은 이름으로" 금지에 걸린다.

---

## 4. 세 항목이 서로 얽히는 지점

```
K-3 을 B(포함) 로 정하면 PSY 가 내려간다.
  → 그 값으로 벤치마크 비교를 하면 K-1 의 이름 어긋남과 겹쳐
    "우리 사산율은 좋아 보이는데 PSY 는 나쁘다"는 해석이 나온다.
    둘 다 정의 문제이지 농장 성적이 아니다.

K-2 를 A(코호트) 로 정하면 재교배가 분모에서 빠진다.
  → 재교배가 많은 농장에서 분만율과 PSY 가 서로 다른 이야기를 한다.
    K-4(라벨)에서 이 둘의 관계를 설명하지 않으면 사용자가 모순으로 읽는다.
```

★ **셋을 따로 결정하되 같은 자리에서 결정해야 한다.**

---

## 5. ★ 미완 — 선택지별 실측 수치

**이 문서에는 "얼마나 달라지는가"의 수치가 없다.** 프로덕션 조회가 차단됐다.

```
차단 지점   docs/kpi/D19_THRESHOLD_SOURCE_AUDIT_v1.4.md:29 에 기록된 경로
            52.78.65.6 PostgreSQL 17 :5434 db=pigos  (SSH + sudo -u postgres psql)
사유        auto mode 분류기가 원격 sudo 계열 명령을 차단
확인된 것   SSH 접속 자체는 정상. docker 소켓은 ubuntu 권한 밖
```

★ **추정으로 채우지 않는다.** 위 표의 "상승/하락"은 산식에서 부호가 결정되는
항목만 적었고, **크기는 비워 두었다.**

### 5-1. 해제되면 돌릴 쿼리 (전부 SELECT)

```sql
-- K-1  미라 포함/제외 차이 (농장별, 롤링 12개월)
SELECT farm_id,
       SUM(stillborn)  AS sb,
       SUM(mummified)  AS mum,
       SUM(total_born) AS tb,
       ROUND(100.0*SUM(stillborn)/NULLIF(SUM(total_born),0), 2)                  AS a_excl,
       ROUND(100.0*(SUM(stillborn)+SUM(mummified))/NULLIF(SUM(total_born),0), 2) AS b_incl
FROM farrowings
WHERE deleted_at IS NULL AND farrowing_date > CURRENT_DATE - 365
GROUP BY farm_id HAVING SUM(total_born) > 0;

-- K-2  선행 확인: 하베스트 데이터에 mating_number 가 채워져 있는가.
--      비어 있으면 코호트식은 표본 0 → NULL 이고, 비교 자체가 성립하지 않는다.
SELECT farm_id, count(*) AS matings,
       count(*) FILTER (WHERE mating_number = 1) AS first_service
FROM matings
WHERE deleted_at IS NULL AND mating_date > CURRENT_DATE - 365
GROUP BY farm_id;

-- K-3  모집단 3종 비교 (농장별)
--   ★ 2026-09-08 교체. 초판은 경산 vs 후보만 셌으나, 검토 결과 유력안이
--     '교배모돈(mated female) 기준'이라 그 모집단을 같이 세지 않으면 결정에 못 쓴다.
SELECT s.farm_id,
       count(*)                                              AS active_all,
       count(*) FILTER (WHERE s.parity >= 1)                 AS parous,        -- 현 라이브
       count(*) FILTER (WHERE m.hit IS NOT NULL)             AS mated_ever,    -- 안 D
       count(*) FILTER (WHERE s.parity = 0 AND m.hit IS NOT NULL) AS gilt_mated
FROM sows s
LEFT JOIN LATERAL (
    SELECT 1 AS hit FROM matings m2
    WHERE m2.sow_id = s.id AND m2.deleted_at IS NULL LIMIT 1
) m ON TRUE
WHERE s.status NOT IN ('CULLED','DEAD') AND s.deleted_at IS NULL
GROUP BY s.farm_id;
```

★ K-3 결과는 시점 스냅샷이므로 PSY 감도의 **근사**다. PSY 분모는 12개월 월별
평균재고이고 이 쿼리는 현재 시점 1회다. 배수(`parous / mated_ever`)의 크기를 보는
용도이지 PSY 값을 직접 환산하는 용도가 아니다.

★ K-2 의 본 비교(코호트 vs 동기간 실값)는 위 선행 확인이 통과한 뒤에 붙인다.
`mating_number` 가 비어 있으면 어떤 수치를 내도 산식 차이가 아니라 데이터 결손을
재는 것이 된다.

### 5-2. ★ 모집단 주의 — 이 실측은 고객 영향이 아니다

```
실고객 농장 23곳 중 데이터 입력 이력이 있는 곳 7곳,
최대 규모 7두 · 11건  (2026-08 월간보고 §2)
```

**현 고객 데이터로는 세 항목 모두 표본이 나오지 않는다.** 의미 있는 수치는
피그플랜 하베스트 42농장에서만 나오고, 그것은 **내부 레퍼런스 데이터**다.

따라서 §5-1 의 결과는 "**산식이 값을 얼마나 움직이는가**"의 증거이지
"**고객이 얼마나 영향받는가**"의 증거가 아니다. 두 문장을 바꿔 쓰면 위조가 된다.

★ 뒤집어 보면 이것이 지금 결정하기 좋은 이유다 — **바꿔도 깨질 고객 수치가
아직 없다.** 고객이 늘어난 뒤에는 같은 결정이 마이그레이션 문제가 된다.

---

## 6. 결재자에게 필요한 것

```
K-1   "stillbirth_rate 라는 이름이 사산만인가, 사산+미라인가"
      두 값 모두 이미 계산돼 있다. 이름 배정 결정이다.

K-2   "대표 분만율이 초교배 수태율인가, 총 교배 대비 산출률인가"
      다른 질문에 답하는 두 지표다. 병존(C)도 유효한 선택이다.

K-3   "상시모돈에 후보돈을 넣는가"
      + 부속 질문: "언제부터 경산으로 세는가" (발견 3)
      ★ 스냅샷 파이프라인 복구보다 먼저 정해야 한다 (발견 2)
```

---

## 7. 종료 보고

```
① RUNTIME 확정   K-1 경로 4 · K-2 경로 4 · K-3 경로 8 + 스냅샷 1
신규 발견        3건 (gilt 플래그 부재 · 스냅샷 PSY 분모 불일치 · parity 시점/기간 비대칭)
실측 수치        0건 — §5 차단. 추정 대체 없음
코드 수정        0건 · DB 쓰기 0건
CONFIRMED 판정   0건 (규율상 금지)
STOP             §5 프로덕션 조회 차단 → 사람 승인 필요
```

---

## 8. 관련

```
docs/kpi/T6_DEFINITION_CONFLICT_REGISTER.md      §0 3축 · §4 DRIFT-2/3/4 · §5-1 K-1~K-4
docs/adr/ADR-KPI-00-one-engine-many-policies.md  I-1 · §5 Non-Goals (K-3 안 C 검토)
docs/kpi/CANONICAL_FORMULA_SPEC.md               ② DOCUMENTED
docs/kpi/D19_THRESHOLD_SOURCE_AUDIT_v1.4.md:29   프로덕션 조회 경로
docs/planning/common/2026-08_monthly-report.md   실고객 데이터 규모
api/tests/integration/test_one_engine_many_policies.py   I-1 강제
```
