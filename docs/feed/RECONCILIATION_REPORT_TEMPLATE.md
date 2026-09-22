# Feed Source Reconciliation Report — Template

> 한 번의 적재/동기화 실행마다 한 부. 숫자는 스크립트 JSON(`docs/feed/runs/*.json`)에서 옮긴다 — 손으로 쓰지 않는다.
> 실제 농장 식별자 금지 (마스킹 id = sha256("PP-{no}")[:12]).

```text
RUN
  date · operator/session · branch/HEAD · target DB (local/ephemeral/prod) · source mode (ORACLE_READONLY/SNAPSHOT)
  sync_run_id · status · source_scope_hash · watermark_to

SOURCE SCOPE
  system/dataset/filter · farms in scope (n) · window · contract version · snapshot content_hash

EXTRACTION
  source rows · farms · date_min/max · USE_YN Y/non-Y · dateless

PERSISTENCE (generation-1 or current)
  expected total vs observed total
  by_farm mismatches · by_month mismatches · by_farm_month mismatches
  source_status (ACTIVE/INACTIVE/RETRACTED) · quantity_status · cost_status
  invariants: payload_hash_null · currency_null · currency_not_krw · basis_not_delivered · current_per_identity_max · identities · max_revision

SYNC LEDGER
  inserted · unchanged · superseded · retracted · empty_source · retraction_skipped_farms · error_class (if any)

PROJECTION (persisted → FeedInput → engine)
  projected rows · lineage checked/failures
  vs Oracle SQL: compared · quantity · cost · unit_price · mix
  vs shadow:     compared · quantity · cost · unit_price · change · variance
  change reasons · variance eligible / identity pass

MISMATCH CLASSIFICATION
  SPEC_AMBIGUITY · SOURCE_ANOMALY · SOURCE_SCOPE_ERROR · PERSISTENCE_BUG · PROJECTION_BUG · SYNC_BUG · ENGINE_BUG · TEST_BUG · EXPECTED_DIFFERENCE · UNEXPLAINED
  (UNEXPLAINED > 0 → PASS 금지)

PERFORMANCE
  elapsed · rows/s · peak mem · db size delta · batch size

VERDICT
  PASS / FAIL · next step
```
