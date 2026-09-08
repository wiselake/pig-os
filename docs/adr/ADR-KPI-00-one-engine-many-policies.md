# ADR-KPI-00 — One Engine, Many Policies

status: ACCEPTED (retroactive — 구현이 선행했고 이 문서가 뒤늦게 고정한다)
date: 2026-09-07
supersedes: (없음) · referenced_by: ADR-KPI-08 (`depends_on: ADR-KPI-00 P7`)

> **왜 뒤늦게 쓰는가.** `ADR-KPI-08`(2026-08-13)이 이 문서를 `depends_on` 으로
> 참조하는데 **저장소에 실물이 없었다.** 개념은 `COUNTRY_KPI_EVIDENCE_ARCHITECTURE_v1.1`
> 과 마이그레이션 주석에 흩어져 있었고, ADR 로 고정된 적이 없다. 참조되는 문서가
> 존재하지 않는 상태는 그 자체로 결함이다.
>
> 이 구조를 제품 차별점으로 말하려면 **먼저 문서로 서 있어야 한다.**

---

## 0. Decision (한 문장)

> **계산 엔진은 하나다. 국가는 그 엔진을 바꾸지 않고, 무엇을 쓸지·뭐라 부를지·언제
> 경고할지만 데이터로 정한다. 국가를 추가하는 데 로직 코드 변경은 0이어야 한다.**

---

## 1. Context — 왜 이 구조가 필요한가

같은 이름의 지표가 나라마다 다른 것을 뜻한다. 이것이 이 도메인의 본질적 난점이다.

```
NPD          연간 비생산일수 / 개체 누적 비생산일 / 이유~교배 간격
             — 셋 다 "NPD" 로 불린다

PSY          분모의 모돈 재고 정의(후보돈 포함 여부)·연율화 방식·기간이 다르면
             같은 농장에서 다른 값이 나온다

분만율        같은 달 교배수 대비 분만수인가, 교배 코호트의 결과인가
             — 후자에서 관찰 미완료 코호트를 실패로 처리하면 값이 왜곡된다

사산          사산만인가 미라 포함인가. 분모도 총산인가 실산인가

이유두수      부분이유·양자(cross-foster)·포유 대리모를 어떻게 세는가
```

순진한 대응은 두 가지이고 둘 다 틀렸다.

```
(A) 국가별로 계산 코드를 분기한다
    → 국가 수만큼 산식이 복제된다. 어느 것이 정본인지 사라진다.

(B) 하나의 정의로 통일하고 나머지는 버린다
    → 현지 관행과 어긋나 고객이 "우리 숫자가 아니다" 라고 한다.
       (2026-08-28 D-8 실측: NPD 30.4 의 차이는 결함이 아니라 관례차였다)
```

**세 번째 길**을 택했다. 계산은 하나로 고정하고, **국가는 정책 데이터로만 말한다.**

---

## 2. Decision — 네 층을 분리한다

각 층은 답하는 질문이 다르다. 층을 섞으면 "표시를 바꿨더니 값이 바뀌는" 사고가 난다.

| 층 | 답하는 질문 | 위치 |
|---|---|---|
| **Canonical 계산** | 무엇을 어떻게 계산했는가 | `app/services/kpi_service.py` · `app/engine/rules/` |
| **거버넌스 정책(CKP)** | 이 국가에서 **써도 되는가 · 어느 군인가** | `country_kpi_policy` |
| **표현(CKPRES)** | **뭐라 부르고 몇 번째인가** | `country_kpi_presentation` |
| **판정 임계** | **언제 경고인가** | threshold 계층 (`severity_for`) |

### 2.1 계산은 국가로 분기하지 않는다

`kpi_service` 가 `farm.country` 를 쓰는 곳은 **정책·기본값 조회의 scope 키**일 뿐이며,
산식 자체가 국가로 갈라지지 않는다. 국가는 계산의 *입력*이 아니라 *조회 좌표*다.

```
farm.country → operational_defaults 조회 · governance enrich · 정책 scope
             ↛ 분자/분모/기간/모집단의 정의
```

### 2.2 두 테이블은 서로 다른 질문이다

`display_order` 를 CKP 에서 CKPRES 로 이관한 것(`a7d9c3e5f1b8`)이 이 분리의 실체다.
모델 주석이 경계를 한 줄로 요약한다.

```
CKP    = 써도 되는가 / 어느 군인가
CKPRES = 뭐라 부르고 몇 번째인가
```

**거버넌스 벡터 6축**(NULL = 상위 상속):

```
compute_enabled       계산할 것인가
display_role          어느 표시군인가
priority_class        중요도 등급 (NORTH_STAR 는 국가당 1개 — uq_ckp_north_star)
rule_enabled          룰 평가 대상인가
benchmark_exposure    외부 비교를 노출하는가
prediction_feature    예측 입력으로 쓰는가
```

★ **headline 은 CKP 에 남는다.** 순서(CKPRES)와 달리 "무엇이 이 나라의 북극성인가"는
표현이 아니라 거버넌스 결정이기 때문이다.

### 2.3 상속 — scope 4단, 높은 쪽이 이긴다

```
GLOBAL(0) → COUNTRY(1) → FARM_TYPE(2) → TENANT(3)
```

GLOBAL 은 6축 전부 NOT NULL 이 강제된다(`chk_global_complete`). 즉 **어떤 조회도
빈 정책으로 끝나지 않는다.** 미결정 국가는 GLOBAL 을 최소 안전값으로 상속한다.

★ `display_order` 의 상속만 규칙이 다르다. **NULL 유무가 아니라 `display_order_override`
플래그로 판단한다** — NULL 이 "미지정"이 아니라 "맨 뒤"라는 정당한 값이기 때문이다.
NULL 을 미지정으로 읽으면 "맨 뒤로 보내라"는 국가 결정이 상위 값으로 덮인다.

### 2.4 벤치마크와 판정 임계는 다른 것이다

**국가 평균보다 낮다는 사실이 곧 경고는 아니다.** 벤치마크는 설명용 비교이고,
심각도는 별도로 승인된 운영 정책이다. `severity_for()` 는 임계를 인자로 받으며
벤치마크를 스스로 읽지 않는다.

이 분리가 없으면 외부 평균 데이터가 바뀔 때 고객 화면의 경고가 조용히 뒤집힌다.

---

## 3. 이 구조가 지키는 불변식

```
I-1  국가 표시 정책만 바꾸면 계산값은 바뀌지 않는다
I-2  국가 추가에 필요한 것은 INSERT 뿐이다 (로직 코드 변경 0)
I-3  지정하지 않은 축은 상위 scope 를 상속한다
I-4  다른 국가의 행이 새어 들어오지 않는다 (폴백 금지)
I-5  미승인 행은 무시된다 (fail-closed)
I-6  발효 전·만료 행은 무시된다
```

**증거 — 불변식별로 다른 파일이 맡는다.**

| 불변식 | 증거 |
|---|---|
| I-1 | `test_one_engine_many_policies.py` — 국가·표현·표시군을 바꿔가며 **같은 수치**인지 |
| I-2 | `test_us_template_lock.py` L1·L2 |
| I-3 | 〃 L3 |
| I-4 | 〃 L4 (2건) |
| I-5 | 〃 L5 |
| I-6 | 〃 L6 |

★ **I-1 은 2026-09-07 까지 테스트가 없었다.** L1~L6 은 I-2~I-6 만 덮는데, 이 ADR 을
  쓰면서 그것을 I-1 의 근거로 인용할 뻔했다. 가장 가까운 기존 테스트
  (`test_global_visible_minimum.py:70`)도 `compute_enabled` 가 True 로 남는지만 보지
  계산 결과가 같은지는 보지 않는다. **하중을 지는 명제에 증거가 없던 것**이므로
  이 ADR 과 함께 테스트를 신설했다.

`test_us_template_lock.py` 는 일부러 `us_pilot_seed.py` 같은 모듈을 만들지 않고
테스트 안에서 행을 리터럴로 넣는다. 새 시드 모듈을 작성했다면 "코드를 썼더니
됐다"가 되어 증명이 약해지기 때문이다. LOCK 이 묻는 것은 **"아무것도 안 써도
되느냐"** 다.

`test_one_engine_many_policies.py` 는 같은 이유로 **대조군**을 함께 둔다. I-1 계열
테스트가 "정책이 아무 데도 영향을 못 준다"로 통과하면 아무것도 증명하지 못하므로,
정책이 **표시에는 반드시** 영향을 준다는 것을 별도로 확인한다.

---

## 4. ★ 이 ADR 이 주장하지 **않는** 것

구조가 옳다는 것과 그 구조를 통과하는 내용이 검증됐다는 것은 다르다.
**이 문서를 근거로 다음을 말하면 위조다.**

```
✗ "PigOS 의 KPI 정의는 검증됐다"
    CANONICAL_FORMULA_SPEC.md:5 — "§3 의 CONFIRMED 7 과 §6 의 verdict: CLEAN 은 무효다"
    :138 — PSY | PSY_ROLLING12M | UNKNOWN | REVOKED → UNVERIFIED
    2026-08-27 Codex 독립검증으로 CONFIRMED 전건이 강등됐다.

✗ "국가별 임계가 승인돼 있다"
    D-19 실사: 승인된 threshold 0건. 프로덕션 severity 는 default_metric_values 가 낸다.
    임계 거버넌스(D-21)는 설계 단계다.

✗ "정의 충돌 목록을 제품이 갖고 있다"
    충돌 레지스터는 아직 없다. 위 §1 의 목록은 감사 과정에서 발견된 사례이지
    체계적으로 수집된 레지스터가 아니다.
```

즉 **엔진은 서 있고, 그 위에 실을 내용이 아직 승인되지 않았다.**
고객에게 정의를 노출하는 것은 그 뒤의 일이다 — 순서는:

```
CANONICAL_FORMULA_SPEC UNVERIFIED → CONFIRMED
  → D-21 임계 승인 체계 가동
    → 정의·근거 고객 노출
```

---

## 5. Non-Goals (명시적 금지)

```
국가별 계산 코드 분기            I-2 가 깨진다
표시 정책이 계산값을 바꾸는 것    I-1 이 깨진다
벤치마크로 severity 를 정하는 것  §2.4 분리가 깨진다
정의가 다른 지표를 같은 이름으로  별도 metric/variant 로 명시한다
미승인 정책의 런타임 반영         I-5 fail-closed
```

---

## 6. Open — 이 ADR 이 닫지 못한 것

| # | 항목 | 소관 |
|---|---|---|
| O-1 | 정의 충돌 레지스터(어느 나라가 어느 정의를 쓰는가)가 없다 | 국가별 수요 리서치 산출물 |
| O-2 | `production_stage`·`herd_size_band` 축이 실제로 쓰이는지 미확인 | 별도 실측 |
| O-3 | 산식 버전과 정책 버전이 분석 결과에 함께 기록되지 않는다 | evidence 계약 |
| O-4 | 치료·휴약·항생제 기록의 국가별 요구가 컬럼으로 증식 중 | `COUNTRY-HEALTH-MASTER` — `master.py:70` `vfd_required_us`·`eu_restricted` 를 읽는 코드 0건 |

---

## 7. 관련

```
docs/adr/ADR-KPI-08-backend-owned-kpi-status.md        이 문서를 depends_on 으로 참조
docs/specs/COUNTRY_KPI_EVIDENCE_ARCHITECTURE_v1.1.md   개념이 흩어져 있던 곳
docs/kpi/CANONICAL_FORMULA_SPEC.md                     산식 검증 상태(전건 강등)
docs/kpi/D19_THRESHOLD_SOURCE_AUDIT_v1.4.md            승인 임계 0건
api/app/db/models/kpi_policy.py                        CKP — 거버넌스 6축
api/app/db/models/kpi_presentation.py                  CKPRES — 표현
api/app/services/kpi_policy_resolver.py                scope 상속
api/app/engine/benchmark_thresholds.py                 severity_for (임계 주입)
api/tests/integration/test_us_template_lock.py         I-2~I-6 수용 게이트 (L1~L6)
api/tests/integration/test_one_engine_many_policies.py  I-1 — 계산값 불변 + 대조군
```
