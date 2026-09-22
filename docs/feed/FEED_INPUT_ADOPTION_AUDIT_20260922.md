# Feed Input Adoption Audit — 왜 `feed_records` 가 0건인가 (2026-09-22)

> 선행: F4 실데이터 감사(`reports/F4_REAL_DATA_AUDIT_20260922.md`) — 프로덕션 feed_records 0행.
> 이 문서는 **그 0의 원인**을 코드 경로·프로덕션 로그·DB 집계(읽기 전용)로 분류하고, CORE 지표가 실제 값을 낼 수 있는
> **최소 입력 계약(MVI)** 을 정한다. 새 기능 개발 0 · 프로덕션 쓰기 0 · 실고객 접촉 0.
>
> 근거 규율: 코드는 `main fc96efc`(= 프로덕션 api 6675b3f · web 이미지 08-26 빌드와 feed 경로 동일 — §1-0 에서 확인).
> 프로덕션 evidence 는 nginx access log 14일(09-08~09-22)과 SELECT 집계뿐. 원자료·식별정보는 옮기지 않았다.
> 재현 스크립트: `scripts/feed_input_nginx_audit.sh` · `api/scripts/feed_input_adoption_readonly.py`.

---

## 0. 한 화면

```text
프로덕션에 있는 것       /feed 페이지(웹·데스크톱 사이드바) → POST /api/v1/farms/{id}/feed-records → feed_records
프로덕션에서 일어난 것   14일간  /feed 페이지 열림 3회 · feed-records GET 1회 · POST 0회 · 2xx POST 0회
                        3개월간  feed_records 0행 · audit_log feed 액션 0
같은 14일의 다른 입력    웹에서 번식 이벤트 POST 성공 0회 · 모바일 /sync 10회 · 로그인 30일 5명(live 42명 중)
live_customer 농장       38 활성 / 최근 30일 이벤트 있는 농장 4 / 모돈 보유 14 / finisher_group 보유 1(폐쇄·체중 없음)

원인(복수)  NO_OPERATIONAL_PROCESS + NO_USER_PROMPT  ← 지배적. 사료만이 아니라 웹 수기 입력 전반이 0 이다
            MODEL_MISMATCH                           ← UI 가 unit_cost·currency·group_id 를 받지 않는다 → 원가·FCR 은 입력해도 불가능
            DISCOVERABILITY (모바일 HIDDEN)           ← 모바일 뷰포트·네이티브 앱·sync 에 사료 입력 경로 없음
            SEMANTIC_AMBIGUITY                       ← "급여량" 한 단어. 일/월/입고 구분 설명 없음
            NO_DATA_SOURCE                           ← 자동 연계 0 (PigPlan 하베스트는 모돈 8테이블뿐)
배제된 원인  ACCESS(권한) — 입력 권한 사용자 40명/37농장. BROKEN_FLOW — 시도 0회라 고장 증거도 없다(테스트 12건 green)
```

---

## 1. 현재 입력 경로 — 호출 그래프 판정 (§3)

### 1-0. 프로덕션이 실제로 이 코드인가

| 확인 | 결과 |
|---|---|
| 배포 web 컨테이너 `pigos-web` 생성 2026-08-26 15:39 KST · `.next/server/app/(app)/feed/page.js` 존재 · `chunks/app/(app)/feed/page-*.js` 존재 | 라우트 **배포됨** |
| 호스트 `~/pigos/src/app/(app)/feed/page.tsx` 2026-07-21 (= `0a18206`) · 로컬 main 과 동일 | 소스 **동일** |
| 배포 api `6675b3f` — `routers/base/feed.py`·`schemas/feed.py`·`feed_service.create_feed_record` 는 main 과 동일 (safety 의 추가분은 `load_feed_cohort`·`FeedBasicOut` 뿐, 입력 경로 무관) | 입력 경로 **동일** |
| 기능 등장: 백엔드 `cabeb96` 2026-06-26 · 프론트 `9ed03e1` 2026-06-26 | 프로덕션 노출 **≈ 3개월** |

### 1-1. 단계별 판정

| 단계 | 위치 | 판정 | 근거 |
|---|---|---|---|
| navigation (데스크톱) | `Sidebar.tsx:59-64` "Herd" 그룹 5번째 `/feed` | **REACHABLE** | 14일 로그 `GET /feed` 200 ×3, 페이지 chunk 로드 ×1 |
| navigation (모바일 웹) | `Sidebar.tsx:156` `hidden md:flex` · `BottomNav.tsx:17-21` 홈/모돈/AI/알림/더보기 · `settings/page.tsx:54-83` 더보기 메뉴 · `QuickInputDrawer.tsx:46-58` | **HIDDEN** | md 미만 뷰포트에서 `/feed` 로 가는 링크가 **0개**. URL 직접 입력만 가능 |
| navigation (네이티브) | Android: `feed-records` 참조 = CostSummary 읽기 전용 4파일 · iOS: 0 · sync 프로토콜 `sync_service.py` 엔티티 = mating/farrowing/weaning/reproductive/preg_check/health/piglet (feed 없음) | **NOT_EXISTS** | 모바일 앱에서 사료 입력 불가. Android QA 9차 "sync 부재 정상" |
| page | `(app)/feed/page.tsx` | **EXISTS · CONDITIONAL** | `activeFarmId` 없으면 `noFarm` 안내. 그 외 항상 렌더 |
| form | 同 `:71-101` | **CONDITIONAL** (role) | `canEntry(role)` = OWNER/MANAGER/WORKER 만 폼 표시. VIEWER/VET 는 목록만. vitest 3건(`tests/pages/feed.test.tsx`) |
| validation (클라) | 同 `:58-62` | **FUNCTIONAL** | `quantity_kg` 숫자·>0 만. 다른 검증 없음 |
| frontend API client | `lib/api/endpoints/feed.ts:18-25` | **EXISTS · 계약 축소** | `CreateFeedRecordRequest` 에 **`unit_cost`·`currency` 필드 자체가 없다**. `group_id`·`building_id`·`notes` 는 타입에 있으나 페이지가 보내지 않는다 |
| backend route | `routers/base/feed.py` GET/POST/DELETE · `main.py:159` 등록 | **REACHABLE** | 09-21 `GET feed-records` 200 ×1. POST 는 `require_farm_role(OWNER/MANAGER/WORKER/…ADMIN)` |
| schema | `schemas/feed.py:12-41` | **EXISTS** | `record_date`(≤서버+1일) · `quantity_kg` 0<x≤100000 · `feed_type` ≤50 자유 · `sow_id/group_id/building_id` 택1 · `unit_cost` 0≤x≤999999 · `currency` ≤3 · `notes` |
| service | `feed_service.create_feed_record:51-78` | **FUNCTIONAL** (테스트) | 농장 현지 미래일 거부 · 대상 농장 소속 검증 · 월마감 423 · commit. 통합테스트 12건 green. **프로덕션 런타임 실행 0회** → `NOT_RUNTIME_VERIFIED` |
| model | `health.py:48-68` `feed_records` | **EXISTS** | `group_id` FK 없음(F0 SCHEMA_GAP) · soft-delete |
| commit | 同 `:75-77` | **EXISTS** | audit_log 기록 **없음**(feed_service 는 `_audit` 를 부르지 않는다 — F4 "audit feed 액션 0" 의 이유이기도 하다) |
| result | 프로덕션 | **0행** | `feed_records` total 0 · live 0 (09-22 SELECT) |

**CURRENT_INPUT_FLOW_USABLE = YES(데스크톱 웹, 수량만) / NO(원가·귀속·모바일).** 흐름 자체는 끊기지 않았다. 다만 그 흐름이 실어 나르는 것이 CORE 6 중 `FEED_QTY`·`FEED_MIX_SHARE`·`FEED_QTY_CHANGE` 의 입력뿐이다.

---

## 2. 도달 가능성 (§4)

| 조건 | 결과 | 근거 |
|---|---|---|
| 메뉴 노출 | 데스크톱만 | §1-1 |
| role/permission | 차단 아님 | live_customer 활성 농장 37/38 에 입력 권한(OWNER/MANAGER/WORKER) 사용자 ≥1 · 사용자 40명 |
| farm selection | 조건 | `activeFarmId` 필수 — 로그인 후 기본 설정됨(auth.store) |
| country restriction | 없음 | 코드 경로에 국가 분기 0 |
| feature flag / entitlement | 없음 | `capture_feed` = 기존·무료(E11). 라우터·페이지에 게이트 0. **단 애드온 스토어에 "Feed Inventory — coming_soon"(`addons/page.tsx:33`) 이 별도로 보인다** → 사용자에게 "사료 기능은 아직" 이라는 반대 신호 |
| route guard | `(app)/layout.tsx` 공통 인증만 | 동의 게이트·개정 배너는 안내형(게이트 아님) |
| responsive/mobile | **HIDDEN** | §1-1 |
| 결론 | live_customer 사용자는 **데스크톱 브라우저**에서 정상 로그인하면 사이드바 "Herd → Feed" 로 도달할 수 있다 | 로그 상 3회 도달했고 1회 목록 조회했다. 저장은 0 |

---

## 3. 현재 입력 계약 (§5)

| 필드 | 스키마(서버) | UI(웹) | required | default | 검증 | 사용자가 무엇을 넣어야 하는지 설명 |
|---|---|---|---|---|---|---|
| `record_date` | date | date input | Y | 오늘(로컬) | ≤농장 오늘 · 월마감 | 라벨 "날짜"뿐. 급여일? 입고일? 월 대표일? — **없음** |
| `feed_type` | str≤50 자유 | text | N | "" → null | 없음 | placeholder "임신돈 / 포유돈 / 비육" → **동물 단계** 분류를 유도. 제품명·배합 아님 |
| `quantity_kg` | 0<x≤100000 | number step 0.1 | Y | — | >0 | "급여량 (kg)" — 일별? 해당일 총량? 돈군별? **없음** |
| `unit_cost` | 0≤x≤999999 (kg당) | **UI 없음** | N | null | — | — |
| `currency` | ≤3 | **UI 없음** | N | null (→ 엔진은 farm.currency 로 fallback) | — | — |
| `group_id` | UUID, 농장 소속 검증 | **UI 없음** | N | null | 서버 404 | — |
| `sow_id` / `building_id` | 同 | **UI 없음** | N | null | 택1 | — |
| `notes` | text | **UI 없음** | N | null | — | — |

입력 부담(현재): 행 1건 = 클릭 3~4회 + 숫자 1개 + 자유 텍스트 1개. 가볍다. **가벼운 대신 CORE 원가·GROUP 지표의 입력이 통째로 빠져 있다** — 제품 확장 결정(E2)이 정한 최소 입력 `feed_quantity · feed_unit_cost · pig/group weight · period` 중 UI 는 첫 항목만 받는다.

---

## 4. 실제 농장 업무 대비 의미 (§6)

8개 로케일 문구가 모두 같은 뜻이다: en "Record feed given — input for FCR" · ko "급여한 사료량 기록" · zh "记录投喂的饲料量" · es "alimento suministrado" · vi "thức ăn đã cho" · th "อาหารที่ให้" · pt "ração fornecida" · ru "выданных кормов".

```text
판정  C. 사료 급여 (feeding) — 한 건이 "어느 날 준 양"
      단 대상(돈군/돈사/모돈) 선택이 UI 에 없어 실제로는 "농장 전체가 그날 준 양" 으로 읽힌다
      → C 이면서 F(월 총량) 와도 구분되지 않는다. 사용자가 월 1회 월 총량을 넣어도 시스템은 막지 않고, 구분도 못 한다
캐노니컬  quantity_basis = AS_RECORDED (F0 UNRESOLVED-1) — 이 감사는 그것을 바꾸지 않는다
어긋남  UI 가 "given(급여)" 라고 말하는데 엔진은 "기록된 대로" 라고 말한다. 둘 다 틀리지 않으나
        사용자에게 **"매일 넣어라 / 월 1회 넣어라 / 입고 시 넣어라" 중 무엇인지 아무도 말하지 않는다**
분류    SEMANTIC_AMBIGUITY (adoption blocker 후보) — 단 시도 0회라 "이것 때문에 안 넣었다" 는 증명 불가 → severity 는 MEDIUM 으로만
```

## 5. group_id 현실성 (§7)

| 질문 | 답 |
|---|---|
| 입력 시 group 선택 가능? | **아니오** — UI 없음 (서버는 받음) |
| active/open 만? closed 도? | 해당 없음(선택지 없음). 서버 검증은 farm 소속만 — open/closed 구분 없음 |
| group 없는 입력 가능? | 예 — 현재 UI 는 **항상** group 없이 보낸다 |
| farm 에 실제 group? (프로덕션 09-22, 읽기 전용) | live_customer: **1개**(폐쇄·entry/exit 체중 NULL·1농장) · open **0** · internal_reference: **0** |

→ 오늘 어떤 농장도 `group_id` 를 붙일 대상이 없다. GROUP-MVI 는 사료 입력이 아니라 **finisher_group 채택**이 선행이다(3개월간 1개).

## 6. feed_type UX (§8)

`free text`. 마스터·select·국가별 어휘 없음(F0 SCHEMA_GAP 그대로). placeholder 가 동물 단계(임신돈/포유돈/비육)를 예시로 들어 사용자는 **단계**를 넣을 것이고, `FEED_MIX_SHARE` 는 그 단계 어휘의 구성비가 된다 — 제품 어휘가 아니어도 CORE 는 계산된다(`UNSPECIFIED` 키 허용). 이해 가능성: **가능**(예시가 있다) · 일관성: **보장 없음**(오타·대소문자 → normalize 가 흡수, 동의어는 흡수 못 함). 온톨로지 신설 금지 — 판정만 남긴다.

## 7. unit_cost 현실성 (§9)

| 항목 | 현재 |
|---|---|
| 입력 방식 | **없음** (UI) |
| 서버 계약 | `kg당 단가` (`schemas/feed.py:24`) · DB Numeric(10,4) |
| 사용자가 보통 가진 값 | 구매 단가(톤당·포대당·총액) — 이것은 기존 조사(E2)의 표현이며 이 감사는 새 시장조사를 하지 않았다 |
| conversion 책임 | 계약상 **사용자**(kg 당으로 환산해 넣어야 함). 자동 환산 없음 |
| mismatch 판정 | **MISMATCH_LIKELY** — 근거는 계약 단위(kg)와 흔한 거래 단위(톤/포대)의 차이라는 구조적 사실뿐. 실사용 증거 0 |

## 8. Zero-row 원인 분류 (§10)

| 원인 | evidence | severity | affected | fix needed? |
|---|---|---|---|---|
| **NO_OPERATIONAL_PROCESS** | 14일 로그: 웹에서 `POST /api/v1/farms/{id}/(matings|farrowings|weanings)` 성공 **0회**(PATCH 422 ×2 뿐) · 모바일 `/sync` 10회 · `onboarding/complete` 409 ×26(재시도) · 로그인 30일 5명. **사료만 0 이 아니다 — 웹 수기 입력 전반이 0** | HIGH | live 38 농장 전부 | 코드 아님 — 운영·파일럿 프로세스 |
| **NO_USER_PROMPT** | FCR·ADG = `GLOBAL_HIDDEN`(E10) → 사료를 넣으면 무엇이 생기는지 대시보드에 없음 · grow-finish 리포트 FCR 칸 "-" 에 안내 없음 · cost 리포트 `noData` 문구만 · 애드온 "Feed Inventory coming_soon" 이 반대 신호 | HIGH | 전부 | 작은 UI 안내(후순위) + D-15/B-7 노출 결재 |
| **MODEL_MISMATCH** | UI 3필드 vs 스키마 9필드. `unit_cost`·`currency` 는 TS 타입에도 없음 → **원가 coverage 는 구조적으로 0 %** (`reportCost.coverageNote` 는 "단가 있는 행만" 이라 쓰는데 단가를 넣을 곳이 없다) · `group_id` 없음 → FCR 귀속 0 | HIGH (CORE 원가·GROUP) | 전부 | **YES — P0** (§11) |
| **DISCOVERABILITY** | 모바일 웹 HIDDEN · 네이티브 앱 NOT_EXISTS · sync 없음 · 데스크톱은 "Herd" 그룹 5번째 | MEDIUM | 모바일 중심 사용자(양돈 현장 — 근거: CLAUDE.md Mobile 결정 "현장 작업자·Android 우선") | P1 |
| **SEMANTIC_AMBIGUITY** | §4 — 일/월/입고 무설명 · AS_RECORDED | MEDIUM | 입력자 전부 | P1 (문구) — 의미 확정은 UNRESOLVED-1 결재 |
| **NO_DATA_SOURCE** | §9 — 자동 연계 0 | MEDIUM | 전부 | 이번 단계 아님 |
| INPUT_BURDEN | 시도 0회 → 부담이 원인이라는 증거 없음. 현재 폼은 오히려 가볍다 | UNKNOWN | — | — |
| ACCESS | 권한자 40명/37농장 · 게이트 0 | **배제** | — | — |
| BROKEN_FLOW | 4xx/5xx 0(시도 0) · 테스트 12+3 green | **NOT_OBSERVED** | — | — |
| UNKNOWN | 사용자가 페이지를 3회 열고 저장하지 않은 이유 — 로그로는 알 수 없다 | — | — | 파일럿에서 관찰 |

★ 가장 중요한 해석: `feed_records = 0` 은 **사료 기능의 실패가 아니라 "프로덕션에서 아무도 수기 입력을 하고 있지 않다" 의 한 단면**이다. live_customer 이벤트도 대부분 모바일 sync 소수 농장(30일 4농장)에서 온다. 사료만 고쳐서 0 이 바뀔 것이라고 기대할 근거가 없다 — 그래서 다음 STEP 은 **입력 경로를 사람이 실제로 밟게 하는 파일럿**이고, 그 전에 밟아도 소용없는 구멍(원가 필드 부재)만 막는다.

## 9. 자동 수집 가능성 (§11)

| 소스 | 판정 | 근거 |
|---|---|---|
| feed purchase / delivery | NOT_AVAILABLE | 테이블·엔드포인트·연계 0 |
| feed usage | NOT_AVAILABLE | `feed_records` 수기뿐 |
| feed inventory | NOT_AVAILABLE | 애드온 `coming_soon` · F0 E12 STRUCTURAL 0 |
| feed cost | NOT_AVAILABLE | `unit_cost` 컬럼만 |
| feed company integration | NOT_AVAILABLE | `api_keys` 모델 docstring 에 "feed companies" 언급, **라우터 0** |
| group feeding | NOT_AVAILABLE | group 1개 |
| PigPlan Oracle 하베스트 | **PARTIAL → 2026-09-22 preflight: `INTEGRATION_FEASIBLE`** (`reports/PIGPLAN_ORACLE_FEED_PREFLIGHT_20260922.md`) | `harvest_import.py` 는 `TB_MODON_WK·TB_GYOBAE·TB_BUNMAN·TB_EU`(+저장소 내 알려진 8 테이블) 만 읽는다. Oracle 에 사료 테이블이 있는지는 저장소 어디에도 없다. **확인 비용 = 읽기 전용 1쿼리**(`SELECT table_name FROM all_tables WHERE owner='PKSU'` — ORACLE_PW 필요, 이 세션은 실행하지 않았다) |
| QBridge (같은 호스트 `qbridge-*` 컨테이너) | UNKNOWN | PigOS 저장소 밖. 사료 데이터 보유 여부 미확인 |

→ 42 internal_reference 농장(하베스트)에 사료 데이터를 붙일 수 있다면 **파일럿 없이도 CORE 를 실데이터로 돌릴 수 있다.** 이 한 가지 UNKNOWN 이 다음 STEP 의 순서를 바꿀 수 있어 §13 에 별도 표기.

## 10. 최소 입력 계약 — MVI (§12)

F0 계약(`FEED_ENGINE_V1_CANONICAL_SPEC.md` §4·§5)을 그대로 입력 요구로 뒤집은 것이다. 새 지표·새 컬럼 없음.

```text
CORE-MVI  (FEED_QTY · FEED_MIX_SHARE · FEED_QTY_CHANGE 는 ①②만으로, FEED_COST · FEED_UNIT_PRICE · FEED_COST_CHANGE 는 ③까지)
  ① record_date   — 해당 기간(월) 안의 날짜. CALENDAR_PERIOD 합산이므로 일자 정밀도는 계산에 영향 없음
  ② quantity_kg   — kg, AS_RECORDED (의미 확정은 UNRESOLVED-1; 파일럿은 "그 달에 준 총량" 으로 **기록 규칙**만 정한다 — 계약 변경 아님)
  ③ unit_cost     — 통화/kg. 그 기간 **모든 행**에 있어야 FEED_COST = ACTUAL (partial ≠ complete)
     currency     — 생략 시 farm.currency (엔진 fallback). 한 기간 안에 통화 2종이면 currency_mixed → INSUFFICIENT
  ④ feed_type     — 선택. 없으면 UNSPECIFIED 1종 → MIX_SHARE = 1.0
  CHANGE/VARIANCE — 위를 **길이가 같은 연속 2기간**(예: 8월·9월) 에 대해

GROUP-MVI (FCR · FEED_COST_PER_PIG · FEED_COST_PER_KG_GAIN · FEED_QTY_PER_HEAD · ADG)
  CORE-MVI
  + group_id      — 행마다 finisher_group 귀속 (현재 UI 없음)
  + finisher_group CLOSED: start/end_date · head_count_in/out · avg_entry_weight_kg · avg_exit_weight_kg (현재 프로덕션 0 충족)
```

CORE_MVI_DEFINED = **YES**. FCR 때문에 CORE 입력을 무겁게 하지 않는다 — GROUP-MVI 는 그룹을 운영하는 농장에만 별도로.

## 11. 입력 방식 비교 (§13)

| 후보 | 스키마 호환 | CORE 계산 | 입력 부담 | 돈군 귀속 | 검증 가능성 | 개발량 | 기존 UX 일관성 | 판정 |
|---|---|---|---|---|---|---|---|---|
| A. 현재 건별 수기 **+ 빠진 필드(unit_cost·currency, group 선택)** | 그대로 | ③까지 가능 | 낮음(필드 2개 추가) | 가능(그룹 있을 때) | 행 단위 대조 쉬움 | **작음** — 폼 필드·TS 타입·i18n 8 로케일·vitest | 같은 페이지 | **P0 전제** |
| B. 월 단위 간편 입력 | 그대로(월 대표일 1행 = A 의 사용 규칙) | 가능 | 가장 낮음 | 불가(월 총량은 그룹 귀속 안 됨) | 월 합계 대조 | 작음~중간 (별도 화면이면 중간) | 새 패턴 | 파일럿 **기록 규칙**으로 채택, 화면은 A 재사용 |
| C. CSV/Excel import | 컬럼 매핑 필요 | 가능 | 준비 있으면 낮음 | 파일에 있으면 가능 | 파일 ↔ DB 대조 쉬움 | 중간 (파서·검증·오류 UX) | 없음 | 파일럿에서 "농장이 이미 표를 가지고 있다" 가 관찰되면 |
| D. 기존 데이터 자동 연계 | 소스에 따름 | 가능 | 0 | 소스에 따름 | 소스 대조 | 큼 (소스 미확인) | — | §9 UNKNOWN 해소 후 |
| E. 복수 | — | — | — | — | — | — | — | A(코드) + B(규칙) 로 시작. C·D 는 파일럿 관찰 뒤 |

## 12. 코드 blocker (§16)

```text
P0 INPUT BLOCKER  (파일럿에서 CORE 원가를 검증하려면 필수)
  - /feed 폼에 unit_cost(kg당) · currency(기본 farm.currency, 표시만) 입력 추가
    src/app/(app)/feed/page.tsx · src/lib/api/endpoints/feed.ts CreateFeedRecordRequest · src/messages/{8}.json · tests/pages/feed.test.tsx
    서버·스키마·DB 변경 0. 목록 표에 단가·통화 열 표시
  - 폼 안내 문장 1개: "이 달에 준 사료 총량을 kg 로, 단가는 kg 당" (파일럿 기록 규칙 — 계약 변경 아님)
P1 ADOPTION IMPROVEMENT
  - group 선택(open finisher_group 드롭다운, 선택) — 그룹 있는 농장에서만 의미
  - 모바일 뷰포트 진입점(더보기 메뉴 1줄) — 네이티브 앱은 별도 저장소·별도 결재
  - grow-finish FCR "-" 와 cost 리포트 noData 에 "사료 입력하면 계산됨" 안내 — FCR 노출은 D-15/B-7 결재 뒤
  - feed_service.create 에 audit_log 기록 (현재 0 — CUD 감사 원칙 위반, 별도 항목)
LATER
  - feed_type select/마스터 · CSV import · 자동 연계 · quantity 의미 컬럼(UNRESOLVED-1) · group_id FK
```

P0 는 이 세션에서 구현하지 않았다 — 입력 필드 추가는 "명백한 broken flow" 가 아니라 입력 계약 확장이라 결재 뒤 한다.

## 13. 판정

```text
CURRENT_INPUT_FLOW_USABLE       YES (데스크톱 웹 · 수량만)   /  NO (원가 · 귀속 · 모바일)
CORE_MVI_DEFINED                YES
PILOT_PROTOCOL_READY            YES  (FEED_PILOT_INPUT_PROTOCOL.md)

NEEDS_CODE_BEFORE_PILOT         YES  — P0 unit_cost·currency 필드 없이는 파일럿이 COST 축을 검증할 수 없다 (QTY 축만이면 NO)
NEEDS_SCHEMA_BEFORE_PILOT       NO
NEEDS_REAL_USER_INPUT           YES  — 자동 소스 AVAILABLE 0 (PigPlan 사료 테이블 = UNKNOWN, 1쿼리로 확정 가능)
```

**다음 STEP 하나: `INPUT UX FIX` (P0 범위만)** — 그 다음이 `PILOT DATA ENTRY`.

> ☞ 2026-09-22 (같은 날 저녁) Oracle preflight 결과 `INTEGRATION_FEASIBLE` — 다음 STEP 은 **`EXISTING DATA INTEGRATION`** 으로 바뀌었다. INPUT UX FIX 는 보조 경로.
단, §9 의 PigPlan 사료 테이블 확인(읽기 1쿼리)이 AVAILABLE 로 나오면 순서는 `EXISTING DATA INTEGRATION` 이 앞선다 — 42 하베스트 농장이 곧 실데이터이기 때문이다. 그 확인은 ORACLE_PW 보유자가 한다.

---

## 부록 A. 프로덕션 집계 원본 (읽기 전용 · 식별정보 없음)

```text
farms                     internal_reference/pigplan_migration 42 (active 42) · live_customer/native_signup 40 (active 38)
live_customer 활동        repro 이벤트 보유 10 · 최근 90일 8 · 최근 30일 4 · 30일 내 이벤트 생성 5 · 모돈 보유 14 (88두)
사용자(live 농장 소속)     42 · 30일 로그인 5 · 90일 로그인 17 · 입력 권한 40 (37 농장)
finisher_groups           live 1 (closed 1 · open 0 · 체중 0) · internal 0
feed_records              0 / 0   ·  audit_log feed 액션 0
90일 생성 이벤트           internal(하베스트) mating 659,583 · farrowing 531,754 · weaning 527,016 (42 농장)
                          live mating 136 (11 농장) · farrowing 87 (4) · weaning 78 (3) · finisher_group 1 (1)
통화(활성 농장)            USD 70 · MXN 5 · VND 2 · KRW 2 · PHP 1
국가(live)                US 15 · KR 12 · MX 5 · CN 2 · VN 2 · BR 1 · PH 1

nginx 14일 (09-08 ~ 09-22, 101,433 라인)
  feed-records          GET 200 ×1 · OPTIONS ×1 · POST 0        /feed 페이지 GET 200 ×3 · chunk ×1
  쓰기 메서드 상위        auth/login 200 ×36 · auth/signin 500 ×30 · onboarding/complete 409 ×26 · devices 401 ×11 · farms/{id}/sync 200 ×10
  farm-scoped POST 성공  sync ×10 (09-10 ×5 · 09-21 ×5) · chat/query ×4 — 번식 이벤트 POST 성공 0
  읽기 상위              kpi/dashboard 36 · sows 32 · reports/comprehensive-daily 16 · config 16 · boars 15
```

## 부록 B. 이 감사가 하지 않은 것

- 실고객 접촉·설문 0 · 테스트 데이터 입력 0 · 코드 변경 0(스크립트 2개 추가만) · 스키마·계약 변경 0
- quantity 의미 확정(UNRESOLVED-1) · FCR 노출/과금(D-15·B-7) · 온톨로지 · 자동 환산 — 전부 결재 사항으로 남김
