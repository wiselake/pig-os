# PigPlan Oracle Feed Data Preflight (2026-09-22)

> 질문 하나: **PigPlan Oracle 에 Feed Engine CORE-MVI 를 충족하거나 매핑할 수 있는 기존 실데이터가 존재하는가?**
> 방법: 승인된 read-only 계정 · `SET TRANSACTION READ ONLY` · 메타데이터(all_tables/all_tab_columns/all_tab_comments/all_views) → 후보 컬럼 → A/B 후보만 집계(COUNT/MIN/MAX/분위수).
> 이 문서에는 **집계와 메타데이터만** 있다. 원시 행·농장 식별자·credential 은 없다. 새 개발 0 · Oracle 쓰기 0 · PigOS 프로덕션 쓰기 0.
> 선행: `F4_REAL_DATA_AUDIT_20260922.md`(프로덕션 feed_records 0) · `../FEED_INPUT_ADOPTION_AUDIT_20260922.md`(§9 UNKNOWN 을 이 문서가 닫는다).

---

## 0. 한 화면

```text
FINAL STATUS   INTEGRATION_FEASIBLE
BEST SOURCE    PKSU.TM_ETC_TRADE  WHERE ACCOUNT_CD='410002' AND GAIN_YN='M'   (농장 거래내역 중 사료 입고 행)
               12개월  21,617행 · 67농장 · 월 ~50농장 꾸준 · 최신 2026-09 (LIVE)
               행당 p50 4,400 kg · 단가 p50 582/kg · 사료명 마스터 100% 해석(625 사료명) · 단계코드 8종
CORE-MVI       date DIRECT · quantity DIRECT(kg) · unit_cost DIRECT(63 %)+DERIVABLE(total/kg, 항등 96 %) · feed_type DIRECT ×2
               currency MISSING(컬럼 없음 → 농장 국가 KOR 로만 추정 · 자동 확정 안 함) · farm 42 하베스트만 DIRECT · group AMBIGUOUS
PigOS 겹침      하베스트 42농장 중 9농장이 12개월 내 사료 행 보유(5,240행) · 9/9 2개월 이상 연속 · 6/9 단가 완비
막는 것        ① ACCOUNT_CD 410002 의 이름이 어느 코드표에도 없다(앱 하드코딩 추정) — 내용으로 사료임은 확실, 라벨은 미확인
               ② quantity 의미 = "입고"(DB 코멘트) ≠ PigOS UI 의 "급여" — 계약(UNRESOLVED-1) 결정 필요, 데이터 문제 아님
               ③ 통화 컬럼 없음 → 적재 시 명시 태깅 결정 필요 (PigOS 하베스트 농장 currency 는 합성 국가 기준 USD 다수)
NEXT STEP      EXISTING DATA INTEGRATION
```

---

## 1. ACCESS

| 항목 | 결과 |
|---|---|
| credential | 기존 승인 read-only 계정(하베스트와 동일, `harvest_import.py` 가 쓰는 계정). 새로 만들지 않았고 출력하지 않았다 |
| read-only | `SET TRANSACTION READ ONLY` + SELECT 만 + 종료 시 rollback. DDL/DML/프로시저 0 |
| schema | `PKSU` 457 테이블(백업 스키마 PKSUBAK·PIGSUBAK 은 제외). Oracle 19c |
| 검색어 | 이름: FEED·RATION·DIET·SARYO·VIN·TRADE·STOCK·PRICE·COST / 코멘트: 사료·급이·급여·입고·사용량·단가·FEED·RATION·DIET |

## 2. CANDIDATES

이름·코멘트로 잡힌 후보 31+34 중 CORE-MVI 관점으로 등급을 매긴 것. 나머지(IoT 급이기 수신 `TE_*`/`IOT_*`/`UIT_*` — 모돈 개체·군사·자돈 급이기 섭취량, 사료빈 잔량)는 **급이 시계열**이라 CORE(농장×기간 총량·원가)와 결이 다르고 원가가 없어 C 로 묶는다.

| 등급 | 소스 | 행 | 근거 |
|---|---|---|---|
| **B** | `TM_ETC_TRADE` (농장 거래내역) `ACCOUNT_CD='410002'` | 2.30M 전체 / 사료행 675,630 전체 / 12m 21,726 | 거래 원장. 사료 행에 `TOTAL_KG`(kg)·`FPER_PRICE`(단가)·`TOTAL_PRICE`·`FEED_CD`(→`TM_FEED` 사료명·단가)·`CK_USE_GUBUN_CD`(단계 8종)·`GRP_NO`·`COMP_CD`(거래처)·`GAIN_YN`(`M`=경영 입고기록 / `B`=비육 사료급이 기록 — **DB 코멘트**). 계정코드 필터 + 마스터 조인이 필요해 A 아닌 B |
| **B** | `TM_MNG_FEED_INFO` (경영자료 사료현황) | 72,762 / 12m 581행·73농장 | 농장×년×월 × 단계 8종 `QUANTITY1..8`(주거래 물량)+`QUPRICE1..8`(금액)+타사 물량/금액. 월 그레인이라 CALENDAR_PERIOD 에 바로 맞음. 단 12m 581행(농장당 ~8개월)·1995 부터 누적·단위 컬럼 없음(금액/물량 p50 533 → kg 로 추정되나 미확정) |
| C | `TM_FEED_RELEASE` (사료출고정보) | 16,133 / 12m 1,805행·12농장 | 출고(빈→돈방) 기록 `EAT_KG`·`SET_KG`·`GRP_NO`·`LOC_CD`. 원가 없음. 농장 12 |
| C | `TM_FEED` (사료코드정보) | 17,653 | 마스터: `FEED_NM`·`FPER_PRICE`·`CK_USE_GUBUN_CD`·`COMP_CD`. 단독으론 수량 없음 — B 의 조인 대상 |
| C | `TI_SMART_FARM_DATA` | — | 월별 경영 KPI 요약(단계별 사료량 4종·총사료비·PSY 등). 업체 스마트팜 코드 기준(`S_FARM_NO`) — farm_no 아님 |
| C | `TB_PIG_FEED` (사료급이정보) | 604 / 5농장 · 2026-05~07 | 개체 급이. 표본 극소 |
| C | `TE_FEEDING_HY` 1.66M · `IOT_AUTOMATIC_FEEDER` 1.78M · `IOT_FEED_BIN_MANAGER` 302k 외 IoT | — | 급이기 수신 시계열(kg 섭취·설정·잔량). 원가 0 · 장비 보유 농장 한정 |
| D | `FEED_SALES_COMPANY`·`FEED_SALES_GOAL`·`FEED_USAGE_FARM` | 3,379 / 84 / 433 | 사료회사 영업 관리(업체·담당·회원). 수량·원가 없음 |
| D | `TC_STD_GAIN*`·`TI_SMART_FEEDRATIO`·`TG_BUN_JADON.FEED_EFF/BR_FEED*` | — | 표준지표·육종가. 실적 아님 |

`ACCOUNT_CD` 12개월 분포 상위: `512001` 50,147행(총체중·도축일 → 출하 추정) · **`410002` 21,726행(사료코드 99.7 %·kg 99.7 %·단가 99.5 %·총액 100 %)** · `511002`/`513001`/`511001`(kg 있고 단가 없음, `GAIN_YN` B/M 혼재 → 이동/전입 추정) · `410003` 4,913행(단가 있고 kg 없음, `DRUG_SEQ` → 약품 추정). **추정은 표기만** — 이름을 확정하지 않는다(§8 RISK ①).

## 3. BEST SOURCE — `TM_ETC_TRADE` 사료 입고 행

```text
필터            ACCOUNT_CD='410002' AND GAIN_YN='M' AND USE_YN='Y'     (B 행 53건·NULL 56건은 제외 — 원가·kg 없음)
rows            전체 675,630 · 12m 21,617 · 90d ≈ 3,600
period          … ~ 2026-09  (불량 날짜: 미래 24행 · 1990 이전 27행 — 전체 0.008 %)
recent_90d      2026-07 1,649행/47농장 · 08 1,416/41 · 09(부분) 528/17
recent_12m      21,617행 · 67농장 · 월 41~52농장
farm coverage   67농장 (PigPlan 전체 use_yn=Y 686 중) · 2개월+ 연속 62 · 12개월 전부 33
pricing         농장 단위: 단가 완비 50 · 부분 9 · 없음 8
cadence         농장-월 603 · 월당 행 p50 16 (p90 84) — 배송 단위 입고 기록 (행당 kg p05 250 · p50 4,400 · p95 20,020)
quality (12m)   kg≤0 46행(0.2 %) · 총액≠단가×kg 550행(단가 있는 행의 4 %) · USE_YN≠Y 917행(4 %)
```

## 4. CORE-MVI MAPPING

| Feed Engine | PigPlan candidate | 판정 | 근거 |
|---|---|---|---|
| `record_date` | `WK_DT` (DATE) | **DIRECT** | 작업일자. 불량 51행은 필터 |
| `quantity_kg` | `TOTAL_KG` | **DIRECT** | 12m 99.8 % 존재. 단위 = kg 로 판단하는 근거: 단가×kg=총액 항등 96 %, 단가 p50 582 이 KRW/kg 규모, `UNIT` 컬럼은 사료 행에서 0 % 사용 |
| `quantity_basis` | `GAIN_YN='M'` = "경영 **입고**기록" | **DERIVABLE — 단 의미 = 입고(구매/배송)** | DB 코멘트 명시 + 거래처 80 % + 배송 크기 분포. **급여/소진이 아니다.** F0 는 `AS_RECORDED` 이므로 적재 자체는 가능하나, UNRESOLVED-1 을 `DELIVERED` 로 닫는 결정이 선행 — 데이터가 아니라 계약의 문제 |
| `unit_cost` (통화/kg) | `FPER_PRICE` · 없으면 `TOTAL_PRICE/TOTAL_KG` | **DIRECT 63 % + DERIVABLE 11 %** (합 74 %) | 항등 96 % 로 `FPER_PRICE` 가 kg 당임을 확인. 단가 없고 총액만 있는 행은 0 (총액 있으면 단가도 있음). 나머지 26 % 는 원가 없음 → 엔진 `partial_cost` 가 정상 동작 |
| `currency` | **없음** | **MISSING** | 행·농장 어디에도 통화 컬럼 값이 없다(`TA_FARM.MONEY_SIGN` 67농장 전부 NULL, `COUNTRY_CODE`='KOR' 67/67). "PigPlan 은 KRW" 를 여기서 자동 확정하지 않는다 — 적재 시 명시 태깅은 **결정** |
| `feed_type` | `CK_USE_GUBUN_CD` (단계 8종: 갓돈·젖돈·젖뗀돈·육성돈·비육돈·임신돈·포유돈·기타) 또는 `FEED_CD→TM_FEED.FEED_NM` (625 사료명) | **DIRECT ×2** | 단계 코드는 `TC_CODE_SYS pcode=100` 으로 100 % 해석. 사료명은 마스터 조인 99.7 %. 어느 것을 `feed_type` 으로 쓸지는 MIX_SHARE 의 어휘 결정 — PigOS UI placeholder(임신돈/포유돈/비육)와는 단계 코드가 같은 어휘 |
| `farm` | `FARM_NO` → PigOS `farms.farm_code='PP-{farm_no}'` | **DIRECT (42 하베스트 농장만)** | §6 |
| `group_id` | `GRP_NO` | **AMBIGUOUS** | §5 |

## 5. GROUP

`GRP_NO` 는 사료 행의 82 %에 있으나 `TJ_GAIN_GRP`(비육돈그룹) 와 조인되는 행은 **57/17,782 (0.3 %)** · 15그룹. 즉 거래 원장의 `GRP_NO` 는 비육 그룹이 아닌 다른 묶음(입고 묶음/일련 추정 — 확정 안 함). **GROUP mapping = NO.** CORE 적재를 막지 않는다 — `CORE usable · GROUP/FCR unavailable` 로 간다. (`TM_FEED_RELEASE` 출고 기록은 그룹·돈방 귀속이 있으나 12농장·원가 0 → 별도 후속)

## 6. PIGOS FARM MAPPING

```text
status         DIRECT_MAPPING_EXISTS (하베스트 42농장)  ·  NO_MAPPING (그 외 PigPlan 농장)
근거           harvest_import.py:368  farm_code = f"PP-{fno}" · data_origin='pigplan_migration' · 프로덕션 42농장 존재(F4)
겹침           42 중 사료 행 보유 16농장(전기간 27,805행) · 12개월 내 9농장 5,240행
               9농장 전부 2개월+ 연속 · 7농장 6개월+ · 단가 완비 6 · 부분 2 · 없음 1
★ 주의         하베스트 42농장은 PigOS 에서 **합성 국가·통화(대부분 USD)** 로 등록돼 있다(manifest.py 의 국가 배정).
               원장 금액은 KRW 규모다(단가 p50 582). 적재 시 행 단위 currency 를 명시하지 않으면 엔진이 farm.currency(USD) 로 fallback → 잘못된 통화 라벨.
               → currency 태깅은 결정 사항이고, 하지 않으면 COST 축 적재 금지.
```

## 7. `TM_MNG_FEED_INFO` (월 요약) 보조 판정

월 그레인·단계별 물량+금액이라 CORE 와 형태가 가장 가깝지만: 12m 581행/73농장(농장당 ~8개월, 빈 달 다수) · 단위 컬럼 없음(금액/물량 p50 533 → kg 추정, 미확정) · 1995~ 누적 중 최근 몇 년은 농장 70대로 축소. **원장(TM_ETC_TRADE)의 파생 요약으로 보이나 증명하지 않았다** — 두 소스의 월 합계 대조는 후속 검증 항목. 1차 소스는 원장.

## 8. RISKS

| 축 | 위험 | 처리 |
|---|---|---|
| semantic ① | `ACCOUNT_CD` 값(410002 등)이 `TC_CODE_SYS`·`TC_CODE_JOHAP` 어디에도 없다 — 앱 하드코딩 추정. "410002 = 사료" 는 **내용(사료코드·kg·단가 99 %)으로 확실**, 라벨은 미확인 | 적재 필터를 `ACCOUNT_CD` 하나에 걸지 말고 `FEED_CD IS NOT NULL AND TOTAL_KG>0` 를 함께 건다. 라벨은 PigPlan 담당자 1문장 확인 |
| semantic ② | 수량 = **입고**(구매/배송). PigOS `quantity_basis=AS_RECORDED`·UI "급여" 와 다르다. 재고 변동을 모르므로 월 입고 ≠ 월 소비 | UNRESOLVED-1 결정(`DELIVERED`) + 산식 버전 표기. 데이터로 해결되지 않는다 |
| freshness | 없음 — 2026-09 까지 산다. 단 9월 부분(17농장)은 월중 스냅샷 | — |
| mapping | 42 하베스트 외 58 사료 농장은 PigOS 에 없다. 하베스트 농장은 **이력(폐쇄) 계정**으로 등록됐는데 사료 원장은 살아 있다 — 같은 farm_no 가 PigPlan 에선 현행 고객 | 42 범위에서 시작. 확장은 하베스트 정책 결정 |
| quality | kg≤0 0.2 % · 항등 깨짐 4 % · USE_YN≠Y 4 % · 불량 날짜 0.008 % | 필터·플래그. 보정 없음 |
| currency | 컬럼 없음 · 농장 설정 NULL | 명시 태깅 결정 없이는 COST 축 적재 금지 (QTY 축은 무관) |
| 스키마 | PigOS `feed_records` 는 그대로 받는다(`record_date·quantity_kg·unit_cost·currency·feed_type·farm_id`). `group_id` 는 비움. 컬럼 추가 불필요 | SCHEMA CHANGE 아님 |

## 9. FINAL

```text
FINAL STATUS          INTEGRATION_FEASIBLE
                      (READY 가 아닌 이유: 계정코드 라벨 미확인 · quantity 의미 결정(UNRESOLVED-1) · currency 태깅 결정 — 셋 다 "결정" 이지 "미지" 가 아니다)
CORE usable           YES — 9 하베스트 농장 × 12개월 (QTY·MIX_SHARE·QTY_CHANGE 즉시, COST·UNIT_PRICE·COST_CHANGE 는 currency 결정 후 6~8농장)
GROUP/FCR             NO  — GRP_NO 는 비육 그룹이 아니다
PRODUCTION            write = NO  (Oracle 0 · PigOS 0)
개발                  0 (ETL·adapter·mapping table 없음)
```

## 10. 재현 (credential 제외)

```sql
-- 메타데이터
SELECT table_name, num_rows FROM all_tables WHERE owner='PKSU' AND table_name LIKE '%FEED%';
SELECT table_name, comments FROM all_tab_comments WHERE owner='PKSU' AND comments LIKE '%사료%';
-- 사료 행 집계 (12m)
SELECT count(*), count(DISTINCT farm_no), min(wk_dt), max(wk_dt)
FROM pksu.tm_etc_trade WHERE account_cd='410002' AND gain_yn='M' AND wk_dt >= add_months(sysdate,-12);
-- 단가×kg 항등
SELECT sum(CASE WHEN abs(total_price - fper_price*total_kg) < 1 THEN 1 ELSE 0 END), count(*)
FROM pksu.tm_etc_trade WHERE account_cd='410002' AND gain_yn='M' AND fper_price>0 AND total_kg>0 AND wk_dt >= add_months(sysdate,-12);
-- 단계 코드
SELECT code, cname FROM pksu.tc_code_sys WHERE pcode='100' AND language_cd='ko';
```

세션은 `SET TRANSACTION READ ONLY` 로 열고 rollback 으로 닫았다. 스크립트는 저장소에 넣지 않았다(단발성 preflight · 결정 후 정식 read-only 커넥터로 다시 쓴다).
