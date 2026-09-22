# PigOS KPI Decision Register

```
목적    산식·임계·거버넌스 결정의 승인 SSOT.
        D-21 persistence 가 붙기 전까지 **이 문서가 승인 기록의 정본**이고,
        DB policy row 는 여기의 decision_id 를 참조한다.
        (D21_THRESHOLD_GOVERNANCE_DESIGN §10 — 관리 UI 는 나중에 붙인다)

규율    ★ PROPOSED 를 APPROVED 로 올릴 수 있는 것은 **사람**뿐이다.
        ★ approved_by 는 표시명("Brian")이 아니라 **불변 actor/user ID** 다.
        ★ 결재(APPROVED) ≠ 구현정합(CONFIRMED). 둘을 같은 칸에 쓰지 않는다.
        ★ 산식 결정 ≠ 임계 결정. 별도 decision 으로 분리한다.
```

## 0. 상태 전이

```
DRAFT → PROPOSED → APPROVED
                 → REJECTED
        APPROVED → SUPERSEDED   (supersedes_id 로 승계)
```

각 결정의 최소 metadata:

```yaml
decision_id:
proposed_by:        # actor/user ID
approved_by:        # actor/user ID — 표시명 금지
approved_at:
approval_status:    DRAFT | PROPOSED | APPROVED | REJECTED | SUPERSEDED
approval_reason:
effective_from:
supersedes_id:
```

---

## D-2026-001 — 사산율 canonical 산식

```yaml
decision_id:     D-2026-001
title:           STILLBORN canonical formula
approval_status: PROPOSED          # ★ APPROVED 아님
proposed_by:     jhbae@wiselake.co.kr   # 대화상 제안. actor ID 체계 확정 시 치환
proposed_at:     2026-08-31
approved_by:     null
approved_at:     null
effective_from:  null
supersedes_id:   null
```

### 제안 내용

```
canonical = (stillborn + mummified) / total_born
```

즉 **경로 ②**(`insight_service.py:211`)를 canonical 로 삼고,
경로 ①(`kpi_service.py:523`, `stillborn / total_born`)을 정렬 대상으로 본다.

### 왜 PROPOSED 인가 — APPROVED 로 쓰지 않은 이유

승인 주체·경로가 아직 없다(D-2026-002). **기록할 actor ID 가 존재하지 않는 상태에서
APPROVED 를 쓰면 그것이 곧 위조다.** D-19 가 `APPROVED_POLICY = 0` 을 실측한 근본 이유가
"승인을 기록할 곳이 없다" 였고, 같은 함정에 문서로 빠지지 않는다.

### ★ 승인해도 그날 CONFIRMED 가 되지 않는다

```
D-2026-001 APPROVED
      ↓
code alignment — live 산식 경로 정렬
      ↓
regression (U-8 계열 회귀 테스트)
      ↓
D-13 재실사
      ↓
formula_status = CONFIRMED
      ↓
그 다음에야 threshold 를 이 산식에 귀속시킬 수 있다
```

근거: `docs/kpi/CANONICAL_FORMULA_SPEC_REAUDIT.md` §5-1 (사산 계열 = `AMBIGUOUS · LIVE_DIVERGENCE`) ·
`docs/specs/D21_THRESHOLD_GOVERNANCE_DESIGN.md` §6-1.

### 정렬 대상 (승인 후 착수)

| 경로 | 위치 | 현재 | 조치 |
|---|---|---|---|
| ① | `kpi_service.py:523` | `stillborn / total_born` | canonical 로 정렬 |
| ② | `insight_service.py:211` | `(stillborn + mummified) / total_born` | canonical |
| — | `MUMMIFIED_RATE` `kpi_service.py:524` | 별도 지표 | **이중 계상 검토 필요** |

★ ②를 canonical 로 삼으면 `MUMMIFIED_RATE` 를 별도 지표로 계속 둘 때 미라가
두 지표에 동시에 들어간다. 표시 정책에서 처리할지 지표를 재정의할지는
**이 결정의 범위 밖**이며 별도 항목으로 남긴다.

### ★ 임계값은 이 결정에 포함되지 않는다

```
D-2026-001  = 산식 결정      (이 항목)
D-2026-003  = 임계 결정      (별도. 아래)
```

산식 B 를 확정했다고 현재 임계(8.00/12.00 등)를 자동 승인하지 않는다.
미라를 포함하면 값이 구조적으로 올라가므로 **같은 임계가 두 산식에 동시에 맞을 수 없다.**

---

## D-2026-002 — Threshold 승인 주체·경로

```yaml
decision_id:     D-2026-002
title:           Threshold approval authority and path
approval_status: PROPOSED
proposed_by:     jhbae@wiselake.co.kr
proposed_at:     2026-08-31
approved_by:     null
approved_at:     null
```

### 제안 내용

```
사람의 승인
   ↓
Decision Register (이 문서)  ← 승인 SSOT
   ↓
decision_id
   ↓
D-21 persistence: policy row 가 decision_id 를 참조
   ↓
resolver 는 APPROVED policy 만 사용
```

* 거대한 Admin UI 를 먼저 만들지 않는다. 관리 UI 는 나중에 붙인다.
* 코드 작성자와 승인자를 2인으로 **강제하지는 않는다.**
  다만 **누가 승인했는지 audit 가능한 것은 필수**다.
* `approved_by` 는 반드시 불변 actor/user ID. 표시명 문자열 금지.

### 미결 — 승인 전 확정 필요

```
[ ] actor ID 체계 — users.id 를 쓸 것인가, 별도 principal 을 둘 것인가
[ ] Decision Register ↔ DB 동기화 시점 (수동 스크립트 / 마이그레이션 / 서비스)
```

---

## D-2026-003 — 사산 임계값 (placeholder)

```yaml
decision_id:     D-2026-003
title:           STILLBORN threshold values
approval_status: DRAFT              # 아직 제안조차 하지 않는다
blocked_by:      [D-2026-001, D-2026-002]
```

산식(D-2026-001)이 확정되고 그 산식이 `CONFIRMED` 가 된 뒤에야 임계를 논의한다.
현행 값(BR 8.20 / KR·US·SYSTEM 8.00, critical 12.00)은 D-19 실측상 전부
`UNATTRIBUTED` 이며 **자동 승격하지 않는다.**

### ★ 001 이 APPROVED 돼도 003 이 따라 올라가지 않는다

```
D-2026-001 APPROVED
      ↓
   003 은 그대로 DRAFT 다.
   임계는 **별도 evidence + 별도 approval** 이 필요하다.
```

산식을 승인했다는 사실은 임계의 근거가 아니다. 오히려 반대다 —
미라를 포함하면 값이 구조적으로 올라가므로 **기존 임계는 새 산식에 맞지 않을 가능성이 높다.**
승계가 아니라 재산정 대상이다.

---

## 부록 A — 결정 간 순서

```
001 APPROVED
      ↓
  code alignment  →  regression  →  D-13 재실사  →  formula CONFIRMED

002 APPROVED
      ↓
  approval persistence 구현 가능

001 + 002 + formula CONFIRMED
      ↓
  D-21 persistence GO

003 threshold
      ↓
  별도 evidence / 별도 approval      ← 001 을 따라 올라가지 않는다
```

---

## 부록 B — 이 문서와 기존 문서의 관계

| 문서 | 역할 |
|---|---|
| `CANONICAL_FORMULA_SPEC*.md` | 산식이 **코드에서 무엇인가** (사실) |
| `D19_THRESHOLD_SOURCE_AUDIT_v1.4.md` | 임계가 **어디서 오는가** (사실) |
| `D21_THRESHOLD_GOVERNANCE_DESIGN.md` | 승인·버전 **구조 설계** |
| **`DECISION_REGISTER.md`** (이 문서) | **누가 무엇을 승인했는가** (결정) |

사실과 결정을 같은 문서에 섞지 않는다.
