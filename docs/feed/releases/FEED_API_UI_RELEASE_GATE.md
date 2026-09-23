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

## 5. 리뷰 권고 (2026-09-23) — 결재 대기, 아직 반영 안 함

### B-1 → 권고: **부분월은 비교하지 않는다**
```text
정책안  완료월끼리만 비교. 당월은 "진행 중" 배지 + 델타·화살표·벤치마크 전부 제거
근거    사료는 배송이 덩어리로 들어온다 — 9/1~9/23 부분월은 농장마다 의미가 제각각
★ 사실 정정  "지금 코드가 이미 그렇게 동작한다" 는 **읽기 API 에는 맞지 않는다.**
       부분월을 비교에서 빼는 것은 검증 스크립트(shadow·L4·프로덕션 projection 대사)의 동작이다.
       제품 코드 `/feed/summary` 는 당월에도 FEED_QTY_CHANGE·FEED_COST_CHANGE 를 계산해 내려보내고
       `period.partial=true` 를 표시만 한다(이 문서 §2 B-1). 웹도 기본 선택이 당월이라 전월 대비를 그린다.
       → 정책 고정은 "잠그기" 가 아니라 **API 변경 + 테스트** 가 필요하다: 부분월이면 CHANGE 계열을 INSUFFICIENT(사유 partial_period)로
         내리고, 웹은 배지만 그린다
```

### B-2 → 권고: **이번 릴리스에서 FCR 을 뺀다** (라벨 교정이 아니라)
```text
정책안  1차 = 사료 입고량(배송 기준) + 사료비만 · 화면에 "배송 기준" 명시
근거    배송량 ≠ 소비량. 빈 재고 보정 없으면 차이가 두 자리 %까지 — 그 숫자를 "FCR" 이라 부르면 틀린 수치를 박는 것
        FCR 은 measurement basis(CONSUMED)와 체중 데이터가 계약으로 정의된 뒤
현재    API/웹 응답에 FCR 키 없음(감사 결과). 페이지 부제 "FCR 입력원" 은 DELIVERED 화면에서 제거 대상
```

### D-15 → 권고: **쪼개서 결재**
```text
D-15a  비용·수량 공개 — Oracle 원본과 대사 끝난 사실(프로덕션 대사 0 mismatch)
D-15b  FCR — 파생값, 보류
```

### 추가 게이트 항목 (리뷰)
```text
EMPTY STATE   42 매핑 농장 중 9 농장만 데이터 — 33 농장은 빈 화면 → empty state 문구 필수(8 로케일)
BENCHMARK OFF n=9 는 peer 비교 하한 미달 → 이번 릴리스 벤치마크 off
DATA AS-OF    scheduler OFF 상태에서 화면이 멈춘 스냅샷을 최신으로 오해시킨다 → "데이터 기준일"(마지막 sync_run completed_at /
              source watermark) 표시가 UI 게이트 필수 항목
```

### 순서 (리뷰 합의안)
```text
PR #8 merge → deploy.sh preflight(드리프트 게이트) 설치 → downgrade·복원 테스트 → B-1/B-2/D-15a/D-15b 결재 → API/UI
```
