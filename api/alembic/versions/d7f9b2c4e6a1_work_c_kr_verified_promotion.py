"""작업 C — KR 벤치마크 verified 승격 (1차자료: 한돈팜스 2025 전산성적)

기준: handoff/KPI_GOVERNANCE_v3.1.md §10(v3.2) / PROMPT_C_kr_verified_promotion.md
- D-6 해결: 전국 일반사용자(2,655호) 2025 연간확정. 상시모돈 분모 → comparison_status=compatible.
- national_general verified 7종 (psy/msy/farrowing_rate/prewean_survival/postwean_survival/weaned_per_litter/sow_turnover)
- professional normalized_verified 1종 (stillbirth_rate 9.3% = 복당사산/복당총산, 잔차=사산+미라)
- 전국 stillbirth_rate는 missing 유지(모집단 혼입 금지). total_born/market_age 드롭. npd missing 유지.
- population_scope 컬럼 신설 + active-verified unique에 포함.
- 내부 입수본: 메타+검증수치만 저장, PDF 원본/이미지 저장 안 함.

Revision ID: d7f9b2c4e6a1
Revises: c5e7a9b1d3f0
"""
import json
from datetime import date

import sqlalchemy as sa

from alembic import op
from app.db.benchmark_seed import kpi_definition_index, validate_benchmark

revision = "d7f9b2c4e6a1"
down_revision = "c5e7a9b1d3f0"
branch_labels = None
depends_on = None

_SOURCE = "한돈팜스 전국 한돈농가 2025년 전산성적 (한돈연구소, 2026-05)"
_PSTART, _PEND, _PUB = date(2025, 1, 1), date(2025, 12, 31), date(2026, 5, 1)

# national_general verified 7종: (kpi_code, value, value_scale)
NATIONAL = [
    ("psy", 22.4, "n/a"),
    ("msy", 18.9, "n/a"),
    ("farrowing_rate", 85.7, "percent_0_100"),
    ("prewean_survival", 89.1, "percent_0_100"),
    ("postwean_survival", 84.3, "percent_0_100"),
    ("weaned_per_litter", 10.45, "n/a"),
    ("sow_turnover", 2.14, "n/a"),
]


def upgrade() -> None:
    conn = op.get_bind()
    kdefs = kpi_definition_index()

    # ① population_scope 컬럼 + active-verified unique 재정의(population 포함)
    op.add_column("benchmarks", sa.Column("population_scope", sa.Text()))
    op.drop_index("uq_bench_active_verified", table_name="benchmarks")
    op.create_index(
        "uq_bench_active_verified", "benchmarks",
        ["country_code", "production_system", "farm_size_band", "population_scope", "kpi_code", "definition_id"],
        unique=True,
        postgresql_where=sa.text("benchmark_status IN ('verified','normalized_verified') AND is_active"),
    )

    existing = {r.kpi_code for r in conn.execute(sa.text(
        "SELECT kpi_code FROM benchmarks WHERE country_code='KR'"))}

    # ② national_general verified 7종
    for kpi, value, vscale in NATIONAL:
        kdef = kdefs[kpi]
        if vscale != kdef["value_scale"]:  # ★⑫-4 사전 가드 (override 금지)
            raise RuntimeError(f"[{kpi}] value_scale {vscale} ≠ kpi_def {kdef['value_scale']} — 중단")
        obs_id = conn.execute(sa.text(
            "INSERT INTO source_observations "
            "(obs_group_id, source_id, source_name, source_year, period_start, period_end, publication_date, "
            " country_code, source_kpi_code, source_value, population_scope, period_basis, source_value_scale, "
            " is_provisional, confidence_level, notes) "
            "VALUES ('KR_2025_national_general','HANDON_FARMS_2025',:sn,2025,:ps,:pe,:pub,'KR',:skc,:sv,"
            " 'national_general',:pb,:svs,false,'A',:notes) RETURNING obs_id"),
            dict(sn=_SOURCE, ps=_PSTART, pe=_PEND, pub=_PUB, skc=kpi, sv=value,
                 pb=kdef["period_basis"], svs=vscale,
                 notes="전국 일반사용자 2,655호, 2025 연간확정, 상시모돈 분모(p.12)")).scalar()

        bench = dict(country_code="KR", production_system="all", farm_size_band="all",
                     population_scope="national_general", kpi_code=kpi, definition_id=kdef["definition_id"],
                     transformed_value=value, transform_formula=None, value_scale=vscale,
                     source_obs_id=obs_id, obs_group_id="KR_2025_national_general",
                     warning_min=None, warning_max=None, critical_min=None, critical_max=None, target=None,
                     mapping_status="exact", comparison_status="compatible",
                     benchmark_status="verified", is_provisional=False,
                     notes="작업C verified 승격. 한돈팜스 2025 전국 일반사용자 연간확정. "
                           "상시모돈 분모→EU/GB InterPIG 호환. 알림 임계는 별도(1차자료엔 평균만).")
        validate_benchmark(bench, kdefs)

        if kpi in existing:  # B provisional → verified UPDATE
            conn.execute(sa.text(
                "UPDATE benchmarks SET transformed_value=:tv, value_scale=:vs, source_obs_id=:oid, "
                " obs_group_id='KR_2025_national_general', population_scope='national_general', "
                " warning_min=NULL, warning_max=NULL, critical_min=NULL, critical_max=NULL, target=NULL, "
                " transform_formula=NULL, mapping_status='exact', comparison_status='compatible', "
                " benchmark_status='verified', is_provisional=false, notes=:notes "
                "WHERE country_code='KR' AND kpi_code=:kpi"),
                dict(tv=value, vs=vscale, oid=obs_id, notes=bench["notes"], kpi=kpi))
        else:  # 신규 INSERT (sow_turnover/prewean_survival/postwean_survival)
            _insert_benchmark(conn, bench)

    # ③ 전문사용자(229호) 사산율 normalized_verified — 별도 obs_group, 전국 슬롯 금지
    sb = kdefs["stillbirth_rate"]
    raw = {"복당총산": 13.62, "복당생존_bornalive": 12.35, "복당사산_잔차_사산미라": 1.27, "복당이유": 11.03}
    sb_obs = conn.execute(sa.text(
        "INSERT INTO source_observations "
        "(obs_group_id, source_id, source_name, source_year, period_start, period_end, publication_date, "
        " country_code, source_kpi_code, source_value, source_numerator, source_denominator, population_scope, "
        " period_basis, source_value_scale, is_provisional, confidence_level, raw_fields_json, notes) "
        "VALUES ('KR_2025_professional','HANDON_FARMS_2025',:sn,2025,:ps,:pe,:pub,'KR','복당사산율',9.3,"
        " '복당사산(잔차=사산+미라)','복당총산','professional',:pb,'percent_0_100',false,'A',:raw,:notes) "
        "RETURNING obs_id"),
        dict(sn=_SOURCE, ps=_PSTART, pe=_PEND, pub=_PUB, pb=sb["period_basis"],
             raw=json.dumps(raw, ensure_ascii=False),
             notes="전문사용자 229호(p.64). 총산=실산+사산+미라 항등식 → 잔차(총산−생존)=사산+미라. "
                   "전제: 복당생존=born alive(실산), 복당이유 별도컬럼이므로 생존=이유전 실산.")).scalar()

    sb_bench = dict(country_code="KR", production_system="all", farm_size_band="all",
                    population_scope="professional", kpi_code="stillbirth_rate", definition_id=sb["definition_id"],
                    transformed_value=9.3, transform_formula="복당사산/복당총산*100", value_scale="percent_0_100",
                    source_obs_id=sb_obs, obs_group_id="KR_2025_professional",
                    warning_min=None, warning_max=None, critical_min=None, critical_max=None, target=None,
                    mapping_status="normalized", comparison_status="normalized",
                    benchmark_status="normalized_verified", is_provisional=False,
                    notes="전문사용자 229호 한정. 1.27/13.62=9.3%=(사산+미라)/총산=PigOS stillbirth_rate 정의일치. "
                          "전국(national_general) 슬롯은 missing 유지(모집단 혼입 금지).")
    validate_benchmark(sb_bench, kdefs)
    _insert_benchmark(conn, sb_bench)


def _insert_benchmark(conn, b: dict) -> None:
    conn.execute(sa.text(
        "INSERT INTO benchmarks "
        "(country_code, production_system, farm_size_band, population_scope, kpi_code, definition_id, "
        " transformed_value, transform_formula, value_scale, source_obs_id, obs_group_id, "
        " warning_min, warning_max, critical_min, critical_max, target, "
        " mapping_status, comparison_status, benchmark_status, is_provisional, notes) VALUES "
        "(:country_code,:production_system,:farm_size_band,:population_scope,:kpi_code,:definition_id,"
        " :transformed_value,:transform_formula,:value_scale,:source_obs_id,:obs_group_id,"
        " :warning_min,:warning_max,:critical_min,:critical_max,:target,"
        " :mapping_status,:comparison_status,:benchmark_status,:is_provisional,:notes)"), b)


def downgrade() -> None:
    conn = op.get_bind()
    # 사산율 professional 행 제거
    conn.execute(sa.text(
        "DELETE FROM benchmarks WHERE country_code='KR' AND population_scope='professional' "
        "AND kpi_code='stillbirth_rate'"))
    # 신규 INSERT된 3종 제거
    conn.execute(sa.text(
        "DELETE FROM benchmarks WHERE country_code='KR' AND kpi_code IN "
        "('sow_turnover','prewean_survival','postwean_survival')"))
    # 승격된 4종 provisional 복원(값/임계는 작업A 재실행 영역이라 상태만 되돌림)
    conn.execute(sa.text(
        "UPDATE benchmarks SET benchmark_status='provisional', is_provisional=true, "
        " transformed_value=NULL, comparison_status='compatible', population_scope=NULL, source_obs_id=NULL "
        "WHERE country_code='KR' AND kpi_code IN ('psy','msy','farrowing_rate','weaned_per_litter')"))
    conn.execute(sa.text("DELETE FROM source_observations WHERE obs_group_id IN "
                         "('KR_2025_national_general','KR_2025_professional')"))
    op.drop_index("uq_bench_active_verified", table_name="benchmarks")
    op.create_index(
        "uq_bench_active_verified", "benchmarks",
        ["country_code", "production_system", "farm_size_band", "kpi_code", "definition_id"],
        unique=True,
        postgresql_where=sa.text("benchmark_status IN ('verified','normalized_verified') AND is_active"))
    op.drop_column("benchmarks", "population_scope")
