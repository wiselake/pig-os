-- =====================================================================================
-- Feed PHASE 0 — coverage audit  (READ-ONLY)
-- =====================================================================================
-- 목적: Feed Basic(PIGOS-F-0011: FCR · Feed Cost/pig · Feed Cost/kg gain) 이 지금 있는
--       데이터로 계산 가능한지, 항목별 충족률·분포를 **숫자로** 낸다. 결론은 내지 않는다.
--       판정 임계는 docs/feed/PHASE0_AUDIT_PLAN.md 가 갖는다.
--
-- 대상: 스테이징/로컬 (프로덕션 금지 — 결재 5 미승인. run_feed_audit.sh 가 호스트를 검사한다)
-- 실행: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/feed_coverage_audit.sql
-- 안전: SELECT 만. 임시 테이블·함수·DDL 없음. 개인정보 컬럼 SELECT 없음 (집계만).
--       READ ONLY 트랜잭션 안에서 돈다 — 쓰기 문장이 섞이면 실패한다.
--
-- 출력 한 행 = (section, metric, n, d, pct, note)
--   n / d      분자 / 분모 (행 수).  pct = n/d*100 (d=0 이면 NULL)
--   STRUCTURAL 행은 information_schema 실측이다 — "컬럼이 없다" 도 측정값으로 남긴다
--
-- 스키마 근거 (api/app/db/models, 2026-09-18 HEAD):
--   feed_records      quantity_kg NOT NULL · sow_id/group_id/building_id NULL 허용 · group_id FK 없음
--                     feed_type VARCHAR(50) 자유입력(web feed/page.tsx <input type=text>) · unit_cost/currency NULL 허용
--   finisher_groups   start_date NOT NULL · end_date NULL · avg_entry/exit_weight_kg NULL · head_count_out NULL
--   piglet_groups     weaning_date NOT NULL · transfer_date NULL · avg_entry/exit_weight_kg NULL
--   health_events     group_id(비육그룹) · event_type DEATH · head_count NULL — 체중 컬럼 없음
--   removals          모돈 전용(sow_id NOT NULL) · body_weight_kg · sale_price · removal_type CULL/DEAD/SOLD/TRANSFER
--   (재고 경계 테이블 없음 · 출하 live/carcass 구분 컬럼 없음 — 아래 STRUCTURAL 행이 실측한다)
-- =====================================================================================

BEGIN READ ONLY;
SET LOCAL statement_timeout = '120s';

WITH
-- ---------- 기준 집합 (soft-delete 제외) ----------
fr AS (
    SELECT * FROM feed_records WHERE deleted_at IS NULL
),
fr_12m AS (
    SELECT * FROM fr WHERE record_date >= (current_date - INTERVAL '12 months')::date
),
fg AS (
    SELECT * FROM finisher_groups WHERE deleted_at IS NULL
),
fg_closed AS (
    SELECT * FROM fg WHERE end_date IS NOT NULL
),
pg AS (
    SELECT * FROM piglet_groups WHERE deleted_at IS NULL
),
he_death AS (
    SELECT * FROM health_events
    WHERE deleted_at IS NULL AND event_type = 'DEATH' AND group_id IS NOT NULL
),
rm AS (
    SELECT * FROM removals WHERE deleted_at IS NULL
),
-- feed_type 표기 정규화: 소문자·양끝 공백 제거·연속 공백 1개
ft AS (
    SELECT feed_type AS raw,
           regexp_replace(lower(btrim(feed_type)), '\s+', ' ', 'g') AS norm
    FROM fr WHERE feed_type IS NOT NULL AND btrim(feed_type) <> ''
),
-- 그룹별 FCR 계산 가능 조건: CLOSED + 입/출 체중 + 출하두수 + group_id 귀속 사료 ≥1건
fg_fcr AS (
    SELECT g.id,
           (g.avg_entry_weight_kg IS NOT NULL)                          AS has_entry_w,
           (g.avg_exit_weight_kg  IS NOT NULL)                          AS has_exit_w,
           (g.head_count_out      IS NOT NULL)                          AS has_out,
           EXISTS (SELECT 1 FROM fr WHERE fr.group_id = g.id)            AS has_feed,
           EXISTS (SELECT 1 FROM fr WHERE fr.group_id = g.id AND fr.unit_cost IS NOT NULL) AS has_priced_feed
    FROM fg_closed g
),
-- information_schema 실측 (컬럼/테이블 존재 여부)
cols AS (
    SELECT table_name, column_name FROM information_schema.columns
    WHERE table_schema = current_schema()
),
tbls AS (
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'
),
rows_out AS (

-- ===================== A. feed_records =====================
SELECT 'A.feed_records' AS section, 'A0 rows (deleted_at IS NULL)' AS metric,
       count(*)::bigint AS n, NULL::bigint AS d, NULL::text AS note FROM fr
UNION ALL
SELECT 'A.feed_records', 'A0 rows, last 12 months', count(*), NULL, NULL FROM fr_12m
UNION ALL
SELECT 'A.feed_records', 'A0 farms with >=1 feed record', count(DISTINCT farm_id), (SELECT count(*) FROM farms WHERE active), 'd = farms(active = true)' FROM fr
UNION ALL
SELECT 'A.feed_records', 'A0 farms with >=1 feed record, last 12 months', count(DISTINCT farm_id), (SELECT count(*) FROM farms WHERE active), NULL FROM fr_12m

-- A1 quantity_kg 의 의미(급이/소진/입고) 판별 근거 컬럼 — 스키마에 있는가
UNION ALL
SELECT 'A.feed_records', 'A1 STRUCTURAL: columns that could qualify quantity_kg meaning', count(*), NULL,
       'looked for: record_kind|measure_type|quantity_type|unit|uom|delivery|consumed|disappearance|basis in feed_records'
FROM cols WHERE table_name = 'feed_records'
  AND column_name ~ '(record_kind|measure_type|quantity_type|^unit$|uom|delivery|consumed|disappear|basis)'
UNION ALL
SELECT 'A.feed_records', 'A1 rows with notes text (only free-text place a meaning could hide)', count(*) FILTER (WHERE notes IS NOT NULL AND btrim(notes) <> ''), count(*), NULL FROM fr

-- A2 귀속 (sow / group / building)
UNION ALL
SELECT 'A.feed_records', 'A2 sow_id IS NULL', count(*) FILTER (WHERE sow_id IS NULL), count(*), NULL FROM fr
UNION ALL
SELECT 'A.feed_records', 'A2 group_id IS NULL', count(*) FILTER (WHERE group_id IS NULL), count(*), NULL FROM fr
UNION ALL
SELECT 'A.feed_records', 'A2 sow_id AND group_id both NULL (unattributable)', count(*) FILTER (WHERE sow_id IS NULL AND group_id IS NULL), count(*), NULL FROM fr
UNION ALL
SELECT 'A.feed_records', 'A2 group_id set but no live finisher_group (orphan — no FK)',
       count(*) FILTER (WHERE group_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM fg WHERE fg.id = fr.group_id)),
       count(*) FILTER (WHERE group_id IS NOT NULL), 'd = rows with group_id' FROM fr
UNION ALL
SELECT 'A.feed_records', 'A2 building_id IS NULL', count(*) FILTER (WHERE building_id IS NULL), count(*), NULL FROM fr

-- A3 feed_type 값 종류 / 표기 흔들림
UNION ALL
SELECT 'A.feed_records', 'A3 feed_type NULL or blank', count(*) FILTER (WHERE feed_type IS NULL OR btrim(feed_type) = ''), count(*), NULL FROM fr
UNION ALL
SELECT 'A.feed_records', 'A3 feed_type distinct (raw)', count(DISTINCT raw), NULL, NULL FROM ft
UNION ALL
SELECT 'A.feed_records', 'A3 feed_type distinct (normalized lower/trim/space)', count(DISTINCT norm), NULL, NULL FROM ft
UNION ALL
SELECT 'A.feed_records', 'A3 feed_type spelling variants (raw distinct - normalized distinct)',
       count(DISTINCT raw) - count(DISTINCT norm), count(DISTINCT raw), 'n>0 = same value typed differently' FROM ft
UNION ALL
SELECT 'A.feed_records', 'A3 feed_type rows covered by top-5 normalized values',
       (SELECT coalesce(sum(c),0) FROM (SELECT count(*) c FROM ft GROUP BY norm ORDER BY c DESC LIMIT 5) t),
       count(*), NULL FROM ft

-- A4 kg 당 단가 확보율
UNION ALL
SELECT 'A.feed_records', 'A4 unit_cost IS NOT NULL', count(*) FILTER (WHERE unit_cost IS NOT NULL), count(*), NULL FROM fr
UNION ALL
SELECT 'A.feed_records', 'A4 unit_cost IS NOT NULL AND currency IS NOT NULL', count(*) FILTER (WHERE unit_cost IS NOT NULL AND currency IS NOT NULL), count(*), NULL FROM fr
UNION ALL
SELECT 'A.feed_records', 'A4 unit_cost set but currency missing', count(*) FILTER (WHERE unit_cost IS NOT NULL AND currency IS NULL), count(*) FILTER (WHERE unit_cost IS NOT NULL), 'd = rows with unit_cost' FROM fr
UNION ALL
SELECT 'A.feed_records', 'A4 unit_cost <= 0 (suspicious)', count(*) FILTER (WHERE unit_cost IS NOT NULL AND unit_cost <= 0), count(*) FILTER (WHERE unit_cost IS NOT NULL), NULL FROM fr
UNION ALL
SELECT 'A.feed_records', 'A4 distinct currencies', count(DISTINCT currency), NULL, NULL FROM fr WHERE currency IS NOT NULL
UNION ALL
SELECT 'A.feed_records', 'A4 quantity_kg-weighted: kg with unit_cost / total kg',
       coalesce(sum(quantity_kg) FILTER (WHERE unit_cost IS NOT NULL),0)::bigint, coalesce(sum(quantity_kg),0)::bigint, 'n,d in kg (truncated)' FROM fr

-- A5 quantity_kg 분포 (0/음수 = 입력 오류 후보)
UNION ALL
SELECT 'A.feed_records', 'A5 quantity_kg <= 0', count(*) FILTER (WHERE quantity_kg <= 0), count(*), NULL FROM fr
UNION ALL
SELECT 'A.feed_records', 'A5 quantity_kg p50 (kg, truncated)', percentile_cont(0.5) WITHIN GROUP (ORDER BY quantity_kg)::bigint, NULL, 'distribution, not a rate' FROM fr
UNION ALL
SELECT 'A.feed_records', 'A5 quantity_kg p90 (kg, truncated)', percentile_cont(0.9) WITHIN GROUP (ORDER BY quantity_kg)::bigint, NULL, NULL FROM fr
UNION ALL
SELECT 'A.feed_records', 'A5 quantity_kg max (kg, truncated)', max(quantity_kg)::bigint, NULL, NULL FROM fr
UNION ALL
SELECT 'A.feed_records', 'A5 duplicate key (farm, group, date, feed_type, qty) rows beyond first',
       (SELECT coalesce(sum(c - 1),0) FROM (SELECT count(*) c FROM fr GROUP BY farm_id, group_id, sow_id, record_date, feed_type, quantity_kg HAVING count(*) > 1) t),
       count(*), 'double-entry candidates' FROM fr

-- ===================== B. finisher_groups =====================
UNION ALL
SELECT 'B.finisher_groups', 'B0 groups (deleted_at IS NULL)', count(*), NULL, NULL FROM fg
UNION ALL
SELECT 'B.finisher_groups', 'B1 closed (end_date IS NOT NULL)', count(*), (SELECT count(*) FROM fg), NULL FROM fg_closed
UNION ALL
SELECT 'B.finisher_groups', 'B1 closed with end_date < start_date (invalid)', count(*) FILTER (WHERE end_date < start_date), count(*), NULL FROM fg_closed
UNION ALL
SELECT 'B.finisher_groups', 'B1 open groups older than 240 days (probably never closed)',
       count(*) FILTER (WHERE end_date IS NULL AND start_date < current_date - 240), count(*) FILTER (WHERE end_date IS NULL), 'd = open groups' FROM fg
UNION ALL
SELECT 'B.finisher_groups', 'B2 avg_entry_weight_kg IS NOT NULL (all groups)', count(*) FILTER (WHERE avg_entry_weight_kg IS NOT NULL), count(*), NULL FROM fg
UNION ALL
SELECT 'B.finisher_groups', 'B2 avg_exit_weight_kg IS NOT NULL (closed groups)', count(*) FILTER (WHERE avg_exit_weight_kg IS NOT NULL), count(*), NULL FROM fg_closed
UNION ALL
SELECT 'B.finisher_groups', 'B2 both weights present (closed groups)', count(*) FILTER (WHERE avg_entry_weight_kg IS NOT NULL AND avg_exit_weight_kg IS NOT NULL), count(*), NULL FROM fg_closed
UNION ALL
SELECT 'B.finisher_groups', 'B2 exit <= entry weight (invalid, closed w/ both)',
       count(*) FILTER (WHERE avg_exit_weight_kg <= avg_entry_weight_kg),
       count(*) FILTER (WHERE avg_entry_weight_kg IS NOT NULL AND avg_exit_weight_kg IS NOT NULL), NULL FROM fg_closed
UNION ALL
SELECT 'B.finisher_groups', 'B3 head_count_out IS NOT NULL (closed groups)', count(*) FILTER (WHERE head_count_out IS NOT NULL), count(*), NULL FROM fg_closed
UNION ALL
SELECT 'B.finisher_groups', 'B3 head_count_out > head_count_in (invalid)', count(*) FILTER (WHERE head_count_out > head_count_in), count(*) FILTER (WHERE head_count_out IS NOT NULL), NULL FROM fg_closed
UNION ALL
SELECT 'B.finisher_groups', 'B4 groups with >=1 attributed feed record (all)', count(*) FILTER (WHERE EXISTS (SELECT 1 FROM fr WHERE fr.group_id = fg.id)), count(*), NULL FROM fg
UNION ALL
SELECT 'B.finisher_groups', 'B4 closed groups with feed', count(*) FILTER (WHERE has_feed), count(*), NULL FROM fg_fcr
UNION ALL
SELECT 'B.finisher_groups', 'B4 FCR-computable: closed + both weights + head_count_out + feed', count(*) FILTER (WHERE has_entry_w AND has_exit_w AND has_out AND has_feed), count(*), 'd = closed groups' FROM fg_fcr
UNION ALL
SELECT 'B.finisher_groups', 'B4 Feed-Cost-computable: FCR-computable + >=1 priced feed row', count(*) FILTER (WHERE has_entry_w AND has_exit_w AND has_out AND has_priced_feed), count(*), 'd = closed groups' FROM fg_fcr
UNION ALL
SELECT 'B.finisher_groups', 'B4 farms with >=1 FCR-computable group',
       count(DISTINCT g.farm_id) FILTER (WHERE f.has_entry_w AND f.has_exit_w AND f.has_out AND f.has_feed),
       (SELECT count(*) FROM farms WHERE active), 'd = farms' FROM fg_fcr f JOIN fg_closed g ON g.id = f.id

-- ===================== B'. piglet_groups =====================
UNION ALL
SELECT 'B2.piglet_groups', 'P0 groups (deleted_at IS NULL)', count(*), NULL, NULL FROM pg
UNION ALL
SELECT 'B2.piglet_groups', 'P1 closed (transfer_date IS NOT NULL)', count(*) FILTER (WHERE transfer_date IS NOT NULL), count(*), NULL FROM pg
UNION ALL
SELECT 'B2.piglet_groups', 'P2 both weights present (closed)', count(*) FILTER (WHERE avg_entry_weight_kg IS NOT NULL AND avg_exit_weight_kg IS NOT NULL), count(*) FILTER (WHERE transfer_date IS NOT NULL), 'd = closed' FROM pg
UNION ALL
SELECT 'B2.piglet_groups', 'P3 groups referenced by feed_records.group_id', count(*) FILTER (WHERE EXISTS (SELECT 1 FROM fr WHERE fr.group_id = pg.id)), count(*), 'group_id has no FK — could point here' FROM pg

-- ===================== C. 폐사 체중 =====================
UNION ALL
SELECT 'C.mortality', 'C1 STRUCTURAL: weight column on health_events', count(*), NULL, 'looked for: weight|kg' FROM cols WHERE table_name = 'health_events' AND column_name ~ '(weight|kg)'
UNION ALL
SELECT 'C.mortality', 'C1 finisher DEATH events (health_events, group_id set)', count(*), NULL, NULL FROM he_death
UNION ALL
SELECT 'C.mortality', 'C1 finisher DEATH events with head_count', count(*) FILTER (WHERE head_count IS NOT NULL), count(*), NULL FROM he_death
UNION ALL
SELECT 'C.mortality', 'C2 sow removals DEAD with body_weight_kg', count(*) FILTER (WHERE body_weight_kg IS NOT NULL), count(*), 'd = removals DEAD' FROM rm WHERE removal_type = 'DEAD'
UNION ALL
SELECT 'C.mortality', 'C3 finisher_groups: head_count_in - head_count_out (implied losses, closed)', coalesce(sum(head_count_in - head_count_out),0), coalesce(sum(head_count_in),0), 'n,d in head; no per-head weight anywhere' FROM fg_closed WHERE head_count_out IS NOT NULL

-- ===================== D. 출하 체중 =====================
UNION ALL
SELECT 'D.shipment', 'D1 STRUCTURAL: live/carcass distinction column (finisher_groups|removals)', count(*), NULL, 'looked for: carcass|live_weight|dressing|hot_weight' FROM cols WHERE table_name IN ('finisher_groups','removals') AND column_name ~ '(carcass|live_weight|dressing|hot_weight)'
UNION ALL
SELECT 'D.shipment', 'D2 closed groups with avg_exit_weight_kg (basis unknown: live vs carcass)', count(*) FILTER (WHERE avg_exit_weight_kg IS NOT NULL), count(*), NULL FROM fg_closed
UNION ALL
SELECT 'D.shipment', 'D3 sow removals SOLD with body_weight_kg', count(*) FILTER (WHERE body_weight_kg IS NOT NULL), count(*), 'd = removals SOLD' FROM rm WHERE removal_type = 'SOLD'
UNION ALL
SELECT 'D.shipment', 'D3 sow removals SOLD with sale_price', count(*) FILTER (WHERE sale_price IS NOT NULL), count(*), NULL FROM rm WHERE removal_type = 'SOLD'
UNION ALL
SELECT 'D.shipment', 'D4 removal_type distinct values', count(DISTINCT removal_type), NULL, 'expected vocabulary: CULL/DEAD/SOLD/TRANSFER (kpi_service filters CULLED)' FROM rm

-- ===================== E. 재고 경계 =====================
UNION ALL
SELECT 'E.inventory', 'E1 STRUCTURAL: feed stock / inventory tables', count(*), NULL, 'looked for table names ~ (feed_stock|feed_inventor|inventory|stock_count|opening|closing)' FROM tbls WHERE table_name ~ '(feed_stock|feed_inventor|inventory|stock_count|opening|closing)'
UNION ALL
SELECT 'E.inventory', 'E1 STRUCTURAL: feed_records columns for opening/closing balance', count(*), NULL, 'looked for: opening|closing|balance|on_hand|stock' FROM cols WHERE table_name = 'feed_records' AND column_name ~ '(opening|closing|balance|on_hand|stock)'

-- ===================== F. 가격 참조 =====================
UNION ALL
SELECT 'F.price_ref', 'F1 market_price_reference rows', count(*), NULL, NULL FROM market_price_reference
UNION ALL
SELECT 'F.price_ref', 'F1 distinct price_type', count(DISTINCT price_type), NULL, 'LIVE_HOG / PORK_CUTOUT / LEAN_HOG_FUTURES expected' FROM market_price_reference
UNION ALL
SELECT 'F.price_ref', 'F1 rows with price_type = FEED (feed price reference exists?)', count(*) FILTER (WHERE price_type ILIKE '%FEED%'), count(*), NULL FROM market_price_reference
)
SELECT section, metric, n, d,
       CASE WHEN d IS NULL OR d = 0 THEN NULL ELSE round(100.0 * n / d, 1) END AS pct,
       note
FROM rows_out
ORDER BY section, metric;

-- ---------- 분포 상세 (판정 보조; 개인정보 없음) ----------
-- feed_type 상위 20 (정규화 키별 원문 변형 목록)
SELECT 'A3.feed_type_top20' AS section,
       regexp_replace(lower(btrim(feed_type)), '\s+', ' ', 'g') AS normalized,
       count(*) AS rows_,
       count(DISTINCT feed_type) AS raw_variants,
       string_agg(DISTINCT feed_type, ' | ' ORDER BY feed_type) AS raw_values
FROM feed_records
WHERE deleted_at IS NULL AND feed_type IS NOT NULL AND btrim(feed_type) <> ''
GROUP BY 2
ORDER BY rows_ DESC
LIMIT 20;

-- removal_type 실제 어휘 (kpi_service 는 'CULLED' 를, 모델 주석은 'CULL' 을 말한다 — 실측으로 확인)
SELECT 'D4.removal_type' AS section, removal_type, count(*) AS rows_
FROM removals WHERE deleted_at IS NULL
GROUP BY removal_type ORDER BY rows_ DESC;

-- 월별 사료 입력 활동 (최근 18개월) — 입력 습관이 있는지
SELECT 'A0.monthly' AS section, to_char(date_trunc('month', record_date), 'YYYY-MM') AS month,
       count(*) AS rows_, count(DISTINCT farm_id) AS farms,
       count(*) FILTER (WHERE group_id IS NOT NULL) AS with_group,
       count(*) FILTER (WHERE unit_cost IS NOT NULL) AS with_price
FROM feed_records
WHERE deleted_at IS NULL AND record_date >= (current_date - INTERVAL '18 months')::date
GROUP BY 2 ORDER BY 2;

COMMIT;
