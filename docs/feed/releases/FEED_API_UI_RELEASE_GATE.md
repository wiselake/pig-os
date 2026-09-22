# Feed API/UI Release Gate (열림 — 2026-09-23 등재)

> Initial Load 승인과 **분리된** 게이트. 적재가 끝나고 데이터가 정상이라는 이유만으로 여기를 자동 통과시키지 않는다.
> 대상: `4882427`(읽기 API) · `89c1e70`(웹 화면). 두 커밋은 `feat/feed-engine-v1-core` 에만 있고 적재 승인 가지
> `release/feed-initial-load` 에는 **없다**.

## 1. 이 게이트가 승인해야 하는 것

```text
GET /farms/{id}/feed/summary · /months 공개
/feed 화면의 월 결과 노출
Oracle DELIVERED 데이터의 고객 노출 여부와 라벨
D-15 / B-7 (FCR·원가 노출 경계, 과금)
PLATFORM_PARITY §9-11 모바일 행 (Android·iOS PLANNED)
```

## 2. Blocker (2026-09-23 감사에서 발견 — 코드 수정 전)

### B-1 `PARTIAL_MONTH_COMPARISON` — 부분월이 전월 대비에 들어간다

```text
사실   /feed/summary 는 요청 월이 진행 중이어도 전월 대비(FEED_QTY_CHANGE·FEED_COST_CHANGE)를 계산한다.
       period.partial = true 로 표시만 하고 값은 그대로 내려간다. 웹 기본 선택이 이번 달이라 사용자가 처음 보는 화면이 그 경우다.
왜 문제  "9월 5일까지 vs 8월 한 달" 이 감소로 보인다. 엔진은 두 기간이 모두 달력월이라 grain 을 통과시킨다(P6-B) —
       데이터가 덜 찼다는 사실은 엔진이 알 수 없다.
선례   shadow 감사·L4 검증은 부분월을 비교에서 제외했다(완료월만 CHANGE/VARIANCE).
선택지  (a) 부분월이면 CHANGE 계열을 INSUFFICIENT 로 유보 (b) 값은 주되 라벨에 "진행 중" 을 강제 (c) 부분월 비교 전용 계약을 별도로 정의
판정   **제품 결정** — 근거 없이 코드로 고르지 않는다. 결정 전 공개 금지.
```

### B-2 `PAGE_SUBTITLE_SAYS_FCR_INPUT` — DELIVERED 를 얹기 전에 문구를 고쳐야 한다

```text
사실   /feed 페이지 부제(8 로케일)는 "급여한 사료량 기록 — FCR 계산 입력원" / "Record feed given — input for FCR".
       지금은 맞다(그 화면은 수기 AS_RECORDED 만 읽고, 그 행이 실제 kpi_service FCR 의 입력이다).
왜 문제  같은 화면에 Oracle DELIVERED(입고)를 붙이는 순간 그 문구가 입고량까지 덮는다 — §12 금지(급여·섭취·소비·FCR input).
조치   DELIVERED 노출 시 basis 별 문구 분리 필수. 현재 코드는 위반 아님(감사 결과), 노출 조건으로 등재.
```

## 3. 감사 결과 — 현재 위반 없음 (조건부)

| 항목 | 결과 |
|---|---|
| API 가 DELIVERED 를 급여/섭취/소비로 부르는가 | 아니오 — docstring·파라미터 설명 모두 "입고 원장" |
| 웹이 DELIVERED 를 표시하는가 | 아니오 — `basis="AS_RECORDED"` 고정 호출, 문구도 "여기에 기록한 급여량 기준" |
| 두 basis 합산 | 없음 (호출마다 basis 하나) |
| FCR·효율 노출 | 없음 (코호트 미적재 → 응답 키 자체가 없음) |
| 원천 raw row 노출 | 없음 (lineage 는 내부 id 요약) |
| null 을 0 으로 | 없음 (값 없음은 reason·부분원가는 evidence — 테스트로 고정) |

## 4. 통과 조건

```text
B-1 결정 + 반영 · B-2 문구 계약 · D-15/B-7 결재 · PLATFORM_PARITY §9-11 모바일 행 계획 · 8 로케일 basis 라벨 확정
그리고 DELIVERED 를 고객에게 보일 경우: 적재 완료 + 대사 0 + "입고" 라벨 강제
```
