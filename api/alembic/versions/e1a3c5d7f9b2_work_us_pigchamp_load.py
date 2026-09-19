"""작업 US — PigCHAMP USA 2025 적재 (D-4: PWMFY 별도, PSY missing)

기준: handoff/KPI_GOVERNANCE_v3.1.md §4.3 / §10.6.
- 분만율 verified 83.81% (compatible)
- 사산율 normalized_verified 9.93% = (stillborn+mummified)/total_born (raw 86157.32/5526.13/3031.06)
- PSY missing (PWMFY 분모=교배모돈 → incompatible). PWMFY 원문은 source_observations 보존.
- prewean_mortality 14.17%·복당총산 15.96은 source_observations만(§10.6 미커밋/orphan) — benchmarks 미적재.
population_scope='national_avg'. 1차자료: PigCHAMP USA 2025 Spring(2024 데이터).

Revision ID: e1a3c5d7f9b2
Revises: d7f9b2c4e6a1
"""
import json
from datetime import date

import sqlalchemy as sa

from alembic import op
from app.db.benchmark_seed import kpi_definition_index, validate_benchmark

revision = "e1a3c5d7f9b2"
down_revision = "d7f9b2c4e6a1"
branch_labels = None
depends_on = None

_SRC = "PigCHAMP USA Benchmark 2025 Spring (2024 데이터)"
_GID = "PIGCHAMP_USA_2025_SPRING"
_PS, _PE, _PUB = date(2024, 1, 1), date(2024, 12, 31), date(2025, 4, 1)


def upgrade() -> None:
    conn = op.get_bind()
    kdefs = kpi_definition_index()

    def _obs(skc, label, val, *, num=None, den=None, raw=None, vscale=None, notes=None):
        return conn.execute(sa.text(
            "INSERT INTO source_observations "
            "(obs_group_id, source_id, source_name, source_year, period_start, period_end, publication_date, "
            " country_code, source_kpi_code, source_kpi_label, source_value, source_numerator, source_denominator, "
            " population_scope, source_value_scale, is_provisional, confidence_level, raw_fields_json, notes) "
            "VALUES (:g,'PIGCHAMP_USA_2025',:sn,2024,:ps,:pe,:pub,'US',:skc,:lbl,:val,:num,:den,"
            " 'national_avg',:vs,false,'A',:raw,:notes) RETURNING obs_id"),
            dict(g=_GID, sn=_SRC, ps=_PS, pe=_PE, pub=_PUB, skc=skc, lbl=label, val=val,
                 num=num, den=den, vs=vscale, raw=(json.dumps(raw, ensure_ascii=False) if raw else None),
                 notes=notes)).scalar()

    # ── source_observations (원문 보존, 5건) ──
    far_obs = _obs("FARROWING_RATE", "Farrowing rate", 83.81, vscale="percent_0_100")
    sb_obs = _obs("STILLBIRTH_RAW", "Total born/stillborn/mummified", 9.93,
                  num="stillborn+mummified", den="total born",
                  raw={"total_born": 86157.32, "stillborn": 5526.13, "mummified": 3031.06},
                  vscale="percent_0_100", notes="PigOS 재계산 (5526.13+3031.06)/86157.32=9.93%")
    _obs("PWMFY", "Pigs weaned/mated female/yr", 27.1, den="mated_female",
         notes="PigOS PSY와 분모 불일치(교배모돈 vs 상시모돈) → 직접 비교 금지. 참고 출처값만 보존, "
               "PigOS KPI 미승격(D-4 보류). PSY benchmark는 missing 유지.")
    _obs("PRE_WEANING_MORTALITY", "Pre-weaning mortality", 14.17, vscale="percent_0_100",
         notes="모집단/분모(born alive vs 포유개시) 주의 → benchmarks 미적재(후속 판정).")
    _obs("TOTAL_BORN", "Average total pigs/litter", 15.96,
         notes="복당총산 — kpi_definitions에 KPI 없음(orphan). benchmarks 미적재.")

    # ── benchmarks (3건: farrowing verified / stillbirth normalized_verified / psy missing) ──
    far = dict(country_code="US", production_system="all", farm_size_band="all", population_scope="national_avg",
               kpi_code="farrowing_rate", definition_id=kdefs["farrowing_rate"]["definition_id"],
               transformed_value=83.81, transform_formula=None, value_scale="percent_0_100",
               source_obs_id=far_obs, obs_group_id=_GID,
               warning_min=None, warning_max=None, critical_min=None, critical_max=None, target=None,
               mapping_status="exact", comparison_status="compatible",
               benchmark_status="verified", is_provisional=False,
               notes="PigCHAMP USA 2025 분만율. 분만복수/교배복수 정의 호환.")
    sb = dict(country_code="US", production_system="all", farm_size_band="all", population_scope="national_avg",
              kpi_code="stillbirth_rate", definition_id=kdefs["stillbirth_rate"]["definition_id"],
              transformed_value=9.93, transform_formula="(stillborn+mummified)/total_born*100",
              value_scale="percent_0_100", source_obs_id=sb_obs, obs_group_id=_GID,
              warning_min=None, warning_max=None, critical_min=None, critical_max=None, target=None,
              mapping_status="normalized", comparison_status="normalized",
              benchmark_status="normalized_verified", is_provisional=False,
              notes="PigCHAMP 사산·미라 분리 → (사산+미라)/총산 재계산. PigOS stillbirth_rate 정의일치.")
    psy = dict(country_code="US", production_system="all", farm_size_band="all", population_scope="national_avg",
               kpi_code="psy", definition_id=kdefs["psy"]["definition_id"],
               transformed_value=None, transform_formula=None, value_scale=None,
               source_obs_id=None, obs_group_id=_GID,
               warning_min=None, warning_max=None, critical_min=None, critical_max=None, target=None,
               mapping_status="incompatible", comparison_status="incompatible",
               benchmark_status="missing", is_provisional=False,
               notes="US PWMFY(분모=교배모돈) ≠ PigOS PSY(상시모돈). 비호환 → missing. 발화 금지(D-4).")

    for b in (far, sb, psy):
        validate_benchmark(b, kdefs)
        conn.execute(sa.text(
            "INSERT INTO benchmarks (country_code, production_system, farm_size_band, population_scope, "
            " kpi_code, definition_id, transformed_value, transform_formula, value_scale, source_obs_id, "
            " obs_group_id, warning_min, warning_max, critical_min, critical_max, target, mapping_status, "
            " comparison_status, benchmark_status, is_provisional, notes) VALUES "
            "(:country_code,:production_system,:farm_size_band,:population_scope,:kpi_code,:definition_id,"
            " :transformed_value,:transform_formula,:value_scale,:source_obs_id,:obs_group_id,"
            " :warning_min,:warning_max,:critical_min,:critical_max,:target,:mapping_status,"
            " :comparison_status,:benchmark_status,:is_provisional,:notes)"), b)


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM benchmarks WHERE country_code='US' AND obs_group_id=:g"), {"g": _GID})
    conn.execute(sa.text("DELETE FROM source_observations WHERE obs_group_id=:g"), {"g": _GID})
