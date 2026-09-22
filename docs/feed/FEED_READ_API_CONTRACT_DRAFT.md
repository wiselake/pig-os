# Feed Read API — Contract Draft (L9, 2026-09-23 · 문서만, 구현 0)

> 조건 충족: L1·L2·L3·L4·L5 PASS. 이 문서는 **계약 초안**이다. 라우터·스키마 코드는 만들지 않았다.
> 노출 결재(D-15/B-7 FCR·과금 경계)와 PLATFORM_PARITY 등재(모바일 3-클라이언트 계약) 뒤에 구현한다.
> 원칙: 원천 raw row 를 노출하지 않는다 · basis 를 숨기지 않는다 · 값 없음을 0 으로 만들지 않는다 · lineage 는 내부 id/요약까지만.

## 1. 엔드포인트 후보 (읽기 전용 · farm-scoped · 기존 `/api/v1/farms/{farm_id}` 관례)

| # | 경로 | 목적 | 우선 |
|---|---|---|---|
| E1 | `GET /api/v1/farms/{farm_id}/feed/summary?period=YYYY-MM&basis=DELIVERED\|AS_RECORDED` | 한 달의 CORE 6 + 상태 + provenance | **P0** |
| E2 | `GET /api/v1/farms/{farm_id}/feed/months?from=YYYY-MM&to=YYYY-MM&basis=` | 월 시계열(CORE 4 값만, change 없음) — 화면 표 | P0 |
| E3 | `GET /api/v1/farms/{farm_id}/feed/sources` | 이 농장에 어떤 basis/소스가 있는가 (AS_RECORDED 수기 n행 · DELIVERED 소스 n행 · 최근 sync) | P1 |
| — | FCR / cost per kg gain / group efficiency | **없음** — DELIVERED 소스로 계산 안 함(`basis_unsupported`). AS_RECORDED 코호트 지표는 D-15 결재 뒤 별도 | — |

## 2. 파라미터

```text
farm_id   경로 · 기존 FarmDep 권한(멤버십·역할) 그대로
period    YYYY-MM (달력월만 — P6-B 의 grain). 임의 구간은 V1 API 에서 받지 않는다
basis     필수. DELIVERED | AS_RECORDED. 기본값 없음 — 호출자가 무엇을 계산하는지 말해야 한다 (§15)
          두 basis 를 한 응답에 합산하는 옵션은 없다 (§16)
```

## 3. 응답 (E1)

```jsonc
{
  "farm_id": "…", "period": {"start": "2026-08-01", "end": "2026-08-31", "grain": "calendar_month"},
  "quantity_basis": "DELIVERED",                 // 결과 전체의 basis — 라벨이 아니라 의미
  "currency": "KRW",                              // 행 통화(단일) · 혼합이면 null + status currency_mixed
  "formula_version": "FEED_ENGINE.v1",
  "metrics": {
    "FEED_QTY":        {"value": 691900.0, "unit": "kg",          "provenance": "ACTUAL",  "status": {"status": "normal", "reason": "no_policy"}},
    "FEED_COST":       {"value": null,     "unit": "currency",    "provenance": "INSUFFICIENT", "reason": "cost_incomplete",
                        "evidence": {"partial_cost": 264917590.0, "coverage_rows": 0.8333, "coverage_kg": 0.79}},   // 부분원가는 값이 아니라 evidence
    "FEED_UNIT_PRICE": {"value": 600.1013, "unit": "currency/kg", "provenance": "DERIVED", "evidence": {"by_feed_type": {"비육돈": 598.2, "육성돈": 610.0}}},
    "FEED_MIX_SHARE":  {"value": 0.62,     "unit": "ratio",       "provenance": "DERIVED", "evidence": {"shares": {"비육돈": 0.62, "육성돈": 0.38}, "dominant_type": "비육돈"}},
    "FEED_QTY_CHANGE": {"value": 33140.0,  "unit": "kg",          "provenance": "DERIVED", "evidence": {"prev_kg": 658760.0, "rate": 0.0503, "comparison_grain": "calendar_month"}},
    "FEED_COST_CHANGE":{"value": null,     "unit": "currency",    "provenance": "INSUFFICIENT", "reason": "cost_incomplete"}
  },
  "findings": [ {"rule_id": "feed.cost_incomplete", "severity": "info", "detail": {...}} ],   // 판정 없음(임계 없음) — 사실만
  "no_data": false,                                // 행 0 이면 true 이고 metrics 는 전부 INSUFFICIENT no_data (0 이 아니다)
  "provenance": {
    "source_systems": ["pigplan"], "contract_versions": ["pigplan_feed_delivery.v1"],
    "rows": 77, "cost_rows": 64, "last_sync": {"status": "SUCCEEDED", "completed_at": "…", "watermark_to": "…"}
  },
  "lineage": {"source_row_count": 77, "source_row_ids_sha256": "…"}   // 개별 id 목록은 내부 감사 API 에서만. raw row 는 어디에도 없음
}
```

규칙:
- `metrics.*.value == null` ⇔ `provenance == "INSUFFICIENT"` ⇔ `reason` 존재 (엔진 계약 그대로). 클라이언트는 `null` 을 0 으로 그리지 않는다 (iOS M-3 교훈).
- `status` 는 기존 `KpiStatus{status, reason}` — 정책 없으면 `no_policy`. 좋고 나쁨 판정은 임계 결재 전까지 나오지 않는다.
- DELIVERED 응답에는 "입고량/구매 원가" 라벨이 붙는다. 소비·효율 문구 금지(§16 shadow).
- 부분월(진행 중)은 `period.partial: true` 로 표시하고 CHANGE 는 계산하지 않는다.

## 4. 오류/경계

| 상황 | 응답 |
|---|---|
| basis 누락/잘못 | 422 |
| 농장 권한 없음 | 기존 403/404 관례 |
| 해당 basis 소스 행 0 | 200 + `no_data: true` (404 아님 — "없음" 도 사실) |
| 소스 sync 실패 상태 | 200 + `provenance.last_sync.status = SOURCE_UNAVAILABLE` — 마지막 성공 적재 기준 값. 값이 사라지지 않는다 |
| 통화 혼합 | `currency: null`, 원가 계열 INSUFFICIENT `currency_mixed` |

## 5. 하지 않는 것

원천 raw row/식별자 노출 · Oracle 실시간 조회 · basis 합산 · FCR/효율 · 임계 판정 · 쓰기 엔드포인트 · 모바일 전용 변형(3-클라이언트 동일 계약, PLATFORM_PARITY 행으로 관리).

## 6. 구현 전 결재/선행

```text
D-15/B-7   FCR·원가 노출 경계          (이 초안은 FCR 을 포함하지 않으므로 CORE 노출만 결재 대상)
PARITY     PLATFORM_PARITY §9-x 행 신설 — Web DONE 조건 · Android/iOS PLANNED
i18n       8 로케일 라벨 (basis 라벨 "입고량"/"급여량" 분리)
INITIAL LOAD APPROVAL   DELIVERED 응답이 비지 않으려면 프로덕션 적재가 먼저
```
