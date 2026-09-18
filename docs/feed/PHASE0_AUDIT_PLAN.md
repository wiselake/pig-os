# Feed PHASE 0 — Coverage Audit Plan (판정 임계 선정의)

> 대상 기능: PIGOS-F-0011 Feed Basic — FCR · Feed Cost/pig · Feed Cost/kg gain (HANDOFF §6, FEATURE_REGISTRY)
> 이 문서는 **실행 전에** 임계를 숫자로 못 박는다. 실행 후에 임계를 옮기지 않는다 (옮기면 그 사유를 §6 에 남긴다).
> 실데이터 결론은 이 문서에 없다. 결론은 실측 리포트(`docs/feed/reports/`)가 나온 뒤 별도 문서로 낸다.

## 0. 상태

```
하네스        scripts/feed_coverage_audit.sql   READ-ONLY (BEGIN READ ONLY) · 61 지표 + 분포 3표
래퍼          scripts/run_feed_audit.sh          프로덕션 호스트 패턴이면 exit 3 (우회 플래그 없음)
합성 fixture   scripts/feed_audit_fixture_synthetic.sql   scratch DB(TEMPLATE 복제) 에만 적재, 끝나면 DROP
샘플 리포트    docs/feed/reports/feed_audit_synthetic_*.txt   ★ SYNTHETIC — 실농장 결론 금지
스테이징      별도 스테이징 환경 없음(2026-09-18 실측: docs/ 에 staging 정의 0건). "스테이징/로컬 스키마" =
              로컬 docker postgres 16, alembic head f3c6a8d0b2e4 (프로덕션과 같은 마이그레이션 체인)
실데이터 실행  NOT_RUN — 프로덕션 읽기는 결재 5(pigos_ro) 미승인. 승인 후 read-replica 또는 덤프 복원본에 실행
```

## 1. 왜 감사부터 하나

FCR 은 이미 무료로 노출돼 있다(kpi_service:535, D-15). Feed Cost/pig · /kg gain 은 산식·정의행·테스트가 없다.
새 산식을 얹기 전에 **입력이 산식을 지탱하는지** 를 먼저 잰다. HANDOFF §6-1 "데이터 없을 때 추정값으로 채우지 않는다" —
채울 수 없다면 기능이 아니라 입력 UX 가 먼저다. 그 갈림길을 숫자로 정한다.

## 2. 항목 ↔ 지표 ↔ 스키마 근거

| 브리프 항목 | 지표 (audit SQL id) | 스키마 실측 (2026-09-18 HEAD) |
|---|---|---|
| `quantity_kg` 의 의미 판별 근거 컬럼 | A1 STRUCTURAL | `feed_records` 에 급이/소진/입고 구분 컬럼 **없음**. 자유 텍스트 `notes` 만 |
| `sow_id` null 비율 | A2 | `sow_id`·`group_id`·`building_id` 모두 NULL 허용. `group_id` 는 **FK 없음** → orphan 가능 |
| `feed_type` 값 종류 / 표기 흔들림 | A3 (+ top20 표) | VARCHAR(50) 자유 입력 (web `feed/page.tsx` `<input type="text">`). 모바일 입력 없음 |
| group entry/exit weight 입력률 | B2 | `finisher_groups.avg_entry/exit_weight_kg` NULL 허용 |
| 그룹 시작·종료일 완결률 | B1 | `start_date` NOT NULL · `end_date` NULL 허용 |
| feed price(kg당) 확보율 | A4 | `unit_cost` NUMERIC(10,4) · `currency` CHAR(3) 모두 NULL 허용. 단위(kg당) 는 컬럼명 관례일 뿐 |
| 폐사체중 | C1·C2·C3 STRUCTURAL | 비육 폐사 = `health_events(DEATH, group_id)` — **체중 컬럼 없음**, `head_count` NULL 허용. 모돈만 `removals.body_weight_kg` |
| 출하체중 (live/carcass 구분) | D1·D2 STRUCTURAL | `avg_exit_weight_kg` 하나뿐 — **live/carcass 구분 컬럼 없음** |
| 기간 시작/종료 재고 경계 | E1 STRUCTURAL | 재고 테이블·잔량 컬럼 **없음** → "소진량 = 입고량" 가정이 유일한 경로 |

★ STRUCTURAL 행은 `information_schema` 를 실제로 조회한다 — "없다" 도 실행 결과로 남는다.

## 3. 판정 임계 (실행 전 고정)

판정 단위는 **농장** 이 아니라 **FCR-computable 그룹** 이다 (`B4`). 기능은 그룹 단위로 계산하고, 농장은 그룹이 하나라도 있으면 카드가 뜬다.

### 3-1. GO / PARTIAL / NO-GO — Feed Basic v1 (FCR + Feed Cost)

| 게이트 | 지표 | GO | PARTIAL | NO-GO |
|---|---|---|---|---|
| G-A 데이터 존재 | A0 farms with ≥1 feed record, last 12 months (pct of active farms) | ≥ 30 % | 10–30 % | < 10 % |
| G-B 귀속 | A2 sow_id AND group_id both NULL (pct) | ≤ 20 % | 20–50 % | > 50 % |
| G-C orphan | A2 group_id set but no live finisher_group (pct) | ≤ 5 % | 5–20 % | > 20 % |
| G-D 그룹 완결 | B4 FCR-computable / closed groups (pct) | ≥ 50 % | 20–50 % | < 20 % |
| G-E 단가 | B4 Feed-Cost-computable / closed groups (pct) | ≥ 40 % | 15–40 % | < 15 % |
| G-F 단가 위생 | A4 unit_cost set but currency missing (pct) | ≤ 5 % | 5–25 % | > 25 % |
| G-G 무결성 | B2 exit ≤ entry (pct) + B3 out > in (pct) 합 | ≤ 2 % | 2–10 % | > 10 % |

종합:
```
GO       G-A~G-G 전부 GO
PARTIAL  NO-GO 0개 · PARTIAL 1개 이상 → v1 은 "FCR-computable 그룹만" 카드 노출, 나머지는 입력 유도(coverage 표시)
NO-GO    NO-GO 1개 이상 → 산식 착수 금지. 입력 UX(그룹 귀속 강제·feed_type 선택지·단가 필수화) 가 먼저
```

### 3-2. 독립 STOP 조건 (수치와 무관)

| 조건 | 판정 |
|---|---|
| A1 STRUCTURAL = 0 (quantity 의미 컬럼 없음) | **FCR 산식은 "quantity_kg = 그룹 귀속 소진량" 가정을 산식 버전 문서에 명시**해야 착수 가능. 가정 없이 착수 금지 |
| E1 STRUCTURAL = 0 (재고 경계 없음) | 기간 FCR(월별) 은 **불가**. 그룹 전생애 FCR 만 v1 범위 (kpi_service 현행과 동일) |
| C1 STRUCTURAL = 0 (폐사 체중 없음) | Feed Cost/kg gain 의 gain 은 **출하두수 × (출하체중 − 입식체중)** 만. 폐사 증체 반영 불가 — 산식 문서에 한계로 기재 |
| D1 STRUCTURAL = 0 (live/carcass 구분 없음) | exit weight 의 기준을 **입력 화면 라벨로 고정**(live) 하고, 국가별 관행 차이는 COUNTRY_KPI_RULE_SPEC 에 위임 |
| A3 spelling variants > 0 | feed_type 은 v1 산식 입력에서 **제외** (phase 구분 없이 합산). 선택지화는 별도 입력 UX 티켓 |

### 3-3. 표본 최소 크기

| 지표 | d 최소 | 미달 시 |
|---|---|---|
| B4 (closed groups) | ≥ 30 | 판정 보류 — "표본 부족" 으로 기록. 임계를 완화하지 않는다 |
| A0 rows, last 12 months | ≥ 200 | 同上 |

## 4. 실행 절차

```
1  대상 결정      로컬 docker(스키마 검증) / 승인된 read-replica·덤프 복원본(실데이터). 프로덕션 직접 접속 금지
2  하네스 검증    scripts/run_feed_audit.sh --synthetic     → 61행 + 3표, 에러 0, scratch DB DROP 확인
3  실데이터 실행  DATABASE_URL=<replica> scripts/run_feed_audit.sh --out docs/feed/reports/feed_audit_real_<date>.txt
4  판정           §3 표에 값을 대입. 임계 변경 없음. 결과는 docs/feed/PHASE0_AUDIT_RESULT_<date>.md 로 별도 작성
5  기록           PROGRESS.md · FEATURE_REGISTRY F-0011 에 판정·SHA 반영
```

리포트에 개인정보 없음: 집계값·information_schema 만. farm_id 도 출력하지 않는다.

## 5. 하네스 검증 기록

| 일시(UTC) | 모드 | 대상 | 결과 | 근거 |
|---|---|---|---|---|
| 2026-09-18 07:50 | synthetic | 로컬 docker postgres 16.15 · alembic `f3c6a8d0b2e4` · scratch `pigos_feedaudit_1789717817` (완료 후 DROP 확인) | 에러 0 · 61행 + 3표 · fixture 의 의도된 결측/흔들림/오류가 각 지표에 잡힘 | `docs/feed/reports/feed_audit_synthetic_20260918T075017Z.txt` · audit SQL @ `698bda3` |
| 2026-09-18 07:4x | target (빈 로컬 DB) | 로컬 `pigos` (farms 0) | 에러 0 · 전 지표 0/NULL — 실데이터 없음 | 콘솔 |
| 2026-09-18 | guard | `DATABASE_URL=...rds.amazonaws.com...` | exit 3 REFUSED | 콘솔 |

## 6. 임계 변경 이력

(없음 — 실행 전 고정 2026-09-18)
