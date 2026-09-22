-- =====================================================================================
-- Feed PHASE 0 — SYNTHETIC fixture for exercising feed_coverage_audit.sql
-- =====================================================================================
-- ★ 이 데이터는 전부 지어낸 것이다. 실농장 결론에 쓰지 않는다. 하네스가 완주하는지·각 지표가
--   0/NULL 이 아닌 값을 낼 수 있는지만 본다. run_feed_audit.sh --synthetic 이 **scratch DB**
--   (TEMPLATE pigos 로 복제한 별도 DB) 에만 적재한다. 프로덕션·스테이징 원본 DB 에 넣지 않는다.
-- 식별 마커: organizations.name = '__FEED_AUDIT_FIXTURE__' · farm_code 'FXA-*'
-- 개인정보 없음(users 행 없음). 값은 지표를 자극하도록 일부러 결측·표기흔들림·오류를 섞었다.
-- =====================================================================================
BEGIN;

INSERT INTO organizations (id, name, org_type, country, timezone)
VALUES ('00000000-0000-4000-8000-00000000f001', '__FEED_AUDIT_FIXTURE__', 'FARM', 'US', 'America/Chicago');

INSERT INTO farms (id, org_id, farm_code, name, country, timezone, unit_system, language, currency, date_format,
                   notification_channel, farm_scale, internet_reliability, active, data_origin, data_classification)
VALUES
 ('00000000-0000-4000-8000-00000000fa01', '00000000-0000-4000-8000-00000000f001', 'FXA-1', 'fixture farm 1', 'US', 'America/Chicago', 'imperial', 'en', 'USD', 'MM/DD/YYYY', 'push', 'MEDIUM', 'GOOD', true, 'synthetic', 'test_fixture'),
 ('00000000-0000-4000-8000-00000000fa02', '00000000-0000-4000-8000-00000000f001', 'FXA-2', 'fixture farm 2', 'VN', 'Asia/Ho_Chi_Minh', 'metric', 'vi', 'VND', 'DD/MM/YYYY', 'push', 'SMALL', 'POOR', true, 'synthetic', 'test_fixture'),
 ('00000000-0000-4000-8000-00000000fa03', '00000000-0000-4000-8000-00000000f001', 'FXA-3', 'fixture farm 3 (no feed)', 'BR', 'America/Sao_Paulo', 'metric', 'pt', 'BRL', 'DD/MM/YYYY', 'push', 'LARGE', 'GOOD', true, 'synthetic', 'test_fixture');

-- finisher groups: G1 fully closed & complete · G2 closed, no exit weight · G3 closed, no head_count_out
--                  G4 open (recent) · G5 open, stale (>240d) · G6 closed with invalid weights · G7 soft-deleted
INSERT INTO finisher_groups (id, farm_id, group_code, start_date, end_date, head_count_in, head_count_out, avg_entry_weight_kg, avg_exit_weight_kg, deleted_at)
VALUES
 ('00000000-0000-4000-8000-0000000000a1', '00000000-0000-4000-8000-00000000fa01', 'G1', current_date - 200, current_date - 80, 500, 488, 30.0, 118.5, NULL),
 ('00000000-0000-4000-8000-0000000000a2', '00000000-0000-4000-8000-00000000fa01', 'G2', current_date - 190, current_date - 70, 480, 470, 29.0, NULL,  NULL),
 ('00000000-0000-4000-8000-0000000000a3', '00000000-0000-4000-8000-00000000fa01', 'G3', current_date - 180, current_date - 60, 510, NULL, 31.0, 120.0, NULL),
 ('00000000-0000-4000-8000-0000000000a4', '00000000-0000-4000-8000-00000000fa02', 'G4', current_date - 40,  NULL,             300, NULL, 28.0, NULL,  NULL),
 ('00000000-0000-4000-8000-0000000000a5', '00000000-0000-4000-8000-00000000fa02', 'G5', current_date - 400, NULL,             250, NULL, NULL, NULL,  NULL),
 ('00000000-0000-4000-8000-0000000000a6', '00000000-0000-4000-8000-00000000fa02', 'G6', current_date - 150, current_date - 30, 200, 210, 60.0, 55.0,  NULL),
 ('00000000-0000-4000-8000-0000000000a7', '00000000-0000-4000-8000-00000000fa01', 'G7', current_date - 300, current_date - 200, 100, 99, 30.0, 115.0, now());

-- feed records: attribution mix · feed_type spelling variants · partial pricing · one orphan group · one zero qty · one duplicate
INSERT INTO feed_records (id, farm_id, sow_id, group_id, record_date, feed_type, quantity_kg, unit_cost, currency, notes)
VALUES
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa01', NULL, '00000000-0000-4000-8000-0000000000a1', current_date - 150, 'Grower',   12000, 0.31, 'USD', NULL),
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa01', NULL, '00000000-0000-4000-8000-0000000000a1', current_date - 120, 'grower ',  15000, 0.30, 'USD', NULL),
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa01', NULL, '00000000-0000-4000-8000-0000000000a1', current_date - 95,  'FINISHER', 18000, NULL, NULL,  'delivered'),
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa01', NULL, '00000000-0000-4000-8000-0000000000a2', current_date - 140, 'Grower',   11000, 0.31, NULL,  NULL),
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa01', NULL, '00000000-0000-4000-8000-0000000000a3', current_date - 130, 'finisher', 16000, 0.29, 'USD', NULL),
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa01', NULL, NULL,                                    current_date - 100, NULL,       9000,  NULL, NULL,  'bulk bin, unassigned'),
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa01', NULL, '00000000-0000-4000-8000-0000000000ff', current_date - 90,  'Grower',   5000,  0.31, 'USD', NULL),  -- orphan group_id
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa02', NULL, '00000000-0000-4000-8000-0000000000a4', current_date - 20,  'Tăng trọng', 4000, 9800, 'VND', NULL),
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa02', NULL, '00000000-0000-4000-8000-0000000000a4', current_date - 10,  'tăng trọng', 4200, 9900, 'VND', NULL),
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa02', NULL, '00000000-0000-4000-8000-0000000000a6', current_date - 100, 'Finisher', 0,     0.28, 'USD', NULL),  -- zero qty
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa02', NULL, '00000000-0000-4000-8000-0000000000a6', current_date - 60,  'Finisher', 7000,  -1,   'USD', NULL),  -- negative price
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa02', NULL, '00000000-0000-4000-8000-0000000000a6', current_date - 60,  'Finisher', 7000,  -1,   'USD', NULL),  -- exact duplicate
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa01', NULL, '00000000-0000-4000-8000-0000000000a7', current_date - 250, 'Grower',   3000,  0.30, 'USD', NULL),
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa01', NULL, '00000000-0000-4000-8000-0000000000a1', current_date - 500, 'Starter',  1000,  0.40, 'USD', NULL);  -- >12 months old

-- piglet groups: one closed with weights, one open
INSERT INTO piglet_groups (id, farm_id, group_code, weaning_date, transfer_date, head_count_in, head_count_dead, head_count_out, avg_entry_weight_kg, avg_exit_weight_kg)
VALUES
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa01', 'P1', current_date - 120, current_date - 70, 600, 12, 588, 6.5, 28.0),
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa02', 'P2', current_date - 30,  NULL,              400, 3,  NULL, 6.8, NULL);

-- finisher deaths: with and without head_count (no weight column exists)
INSERT INTO health_events (id, farm_id, sow_id, group_id, event_date, event_type, head_count)
VALUES
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa01', NULL, '00000000-0000-4000-8000-0000000000a1', current_date - 110, 'DEATH', 7),
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa01', NULL, '00000000-0000-4000-8000-0000000000a1', current_date - 100, 'DEATH', NULL),
 (gen_random_uuid(), '00000000-0000-4000-8000-00000000fa02', NULL, '00000000-0000-4000-8000-0000000000a4', current_date - 5,   'DEATH', 2);

COMMIT;
