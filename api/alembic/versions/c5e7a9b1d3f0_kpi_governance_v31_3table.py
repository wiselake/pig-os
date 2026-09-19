"""KPI Governance v3.1 — 3-테이블(kpi_definitions/source_observations/benchmarks) + KR 27 안전 이전

작업 A (handoff/KPI_GOVERNANCE_v3.1.md / PROMPT_A_schema_migration.md).
순서 엄수(§3): ①테이블 최소생성 ②kpi_definitions 시드 ③KR 27 이전(강등) ④제약 강화.
- 기존 default_metric_values(KR 27 원본)는 삭제하지 않음(이전 + 강등만).
- KR은 전부 provisional/missing 강등. verified 확정은 작업 B.

Revision ID: c5e7a9b1d3f0
Revises: b3d5f7091a2c
"""
import json

import sqlalchemy as sa

from alembic import op
from app.db.benchmark_seed import (
    KPI_DEFINITIONS,
    definition_id_for,
    kpi_definition_index,
    validate_benchmark,
)

revision = "c5e7a9b1d3f0"
down_revision = "b3d5f7091a2c"
branch_labels = None
depends_on = None

# KR metric_code → PigOS kpi_code (§2에 대응되는 11종). 나머지 16종은 orphan(정의 없음).
KR_MAP = {
    "PSY": "psy",
    "MSY": "msy",
    "FARROWING_RATE": "farrowing_rate",
    "WEANED_COUNT": "weaned_per_litter",
    "NPD": "npd",
    "SOW_MORTALITY": "sow_mortality",
    "WSI": "wsi",
    "FCR": "fcr",
    "PRE_WEANING_MORTALITY": "prewean_mortality",
    "CULLING_RATE": "culling_rate",
    "STILLBORN_RATE": "stillbirth_rate",  # 특수: 분자(미라 포함) 불일치·재정규화 불가 → missing 강등
}


def upgrade() -> None:
    conn = op.get_bind()

    # ── ① 테이블 최소 생성 (제약 최소: 컬럼/PK/enum CHECK만. 복합FK·★⑦⑧⑫는 데이터 이전 후) ──
    op.create_table(
        "kpi_definitions",
        sa.Column("kpi_code", sa.Text(), nullable=False),
        sa.Column("definition_id", sa.Text(), nullable=False),
        sa.Column("name_ko", sa.Text()),
        sa.Column("numerator_def", sa.Text(), nullable=False),
        sa.Column("denominator_def", sa.Text(), nullable=False),
        sa.Column("denominator_type", sa.Text(), nullable=False),
        sa.Column("period_basis", sa.Text(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column("value_scale", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.PrimaryKeyConstraint("kpi_code", "definition_id"),
        sa.CheckConstraint("direction IN ('higher_better','lower_better','range_target')", name="ck_kpidef_direction"),
        sa.CheckConstraint(
            "denominator_type IN ('avg_inventory_sow','mated_female','farrowed_female','litter','piglet','total_born','weight')",
            name="ck_kpidef_denomtype"),
        sa.CheckConstraint("period_basis IN ('rolling_365','annual','quarterly','period')", name="ck_kpidef_period"),
        sa.CheckConstraint("value_scale IN ('percent_0_100','ratio_0_1','n/a')", name="ck_kpidef_valuescale"),
    )

    op.create_table(
        "source_observations",
        sa.Column("obs_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("obs_group_id", sa.Text()),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("source_name", sa.Text()),
        sa.Column("source_year", sa.Integer()),
        sa.Column("source_url", sa.Text()),
        sa.Column("period_start", sa.Date()),
        sa.Column("period_end", sa.Date()),
        sa.Column("publication_date", sa.Date()),
        sa.Column("country_code", sa.Text()),
        sa.Column("source_kpi_code", sa.Text()),
        sa.Column("source_kpi_label", sa.Text()),
        sa.Column("source_value", sa.Numeric()),
        sa.Column("source_numerator", sa.Text()),
        sa.Column("source_denominator", sa.Text()),
        sa.Column("source_denominator_raw", sa.Text()),
        sa.Column("population_scope", sa.Text()),
        sa.Column("period_basis", sa.Text()),
        sa.Column("source_value_scale", sa.Text()),
        sa.Column("is_provisional", sa.Boolean(), server_default="false"),
        sa.Column("confidence_level", sa.Text()),
        sa.Column("raw_fields_json", sa.dialects.postgresql.JSONB()),
        sa.Column("notes", sa.Text()),
        sa.PrimaryKeyConstraint("obs_id"),
    )
    op.create_index("idx_srcobs_group", "source_observations", ["obs_group_id"])
    op.create_index("idx_srcobs_country_kpi", "source_observations", ["country_code", "source_kpi_code"])

    op.create_table(
        "benchmarks",
        sa.Column("bench_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("country_code", sa.Text(), nullable=False),
        sa.Column("production_system", sa.Text(), server_default="all"),
        sa.Column("farm_size_band", sa.Text(), server_default="all"),
        sa.Column("kpi_code", sa.Text(), nullable=False),
        sa.Column("definition_id", sa.Text(), nullable=False),
        sa.Column("transformed_value", sa.Numeric()),
        sa.Column("transform_formula", sa.Text()),
        sa.Column("value_scale", sa.Text()),
        sa.Column("source_obs_id", sa.Integer()),
        sa.Column("obs_group_id", sa.Text()),
        sa.Column("warning_min", sa.Numeric()),
        sa.Column("warning_max", sa.Numeric()),
        sa.Column("critical_min", sa.Numeric()),
        sa.Column("critical_max", sa.Numeric()),
        sa.Column("target", sa.Numeric()),
        sa.Column("mapping_status", sa.Text()),
        sa.Column("comparison_status", sa.Text()),
        sa.Column("benchmark_status", sa.Text(), server_default="missing"),
        sa.Column("is_provisional", sa.Boolean(), server_default="false"),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("effective_from", sa.Date()),
        sa.Column("effective_to", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("bench_id"),
        # enum CHECK만 (KR 이전이 유효 enum을 넣으므로 안전). 복합FK·★⑦⑧⑫는 이전 후 ALTER.
        sa.CheckConstraint("mapping_status IN ('exact','normalized','incompatible','unknown')", name="ck_bench_mapping"),
        sa.CheckConstraint(
            "comparison_status IN ('exact','compatible','normalized','incompatible','unknown')", name="ck_bench_comparison"),
        sa.CheckConstraint(
            "benchmark_status IN ('verified','normalized_verified','provisional','missing','global_fallback')",
            name="ck_bench_status"),
        sa.CheckConstraint(
            "value_scale IS NULL OR value_scale IN ('percent_0_100','ratio_0_1','n/a')", name="ck_bench_valuescale"),
        sa.ForeignKeyConstraint(["source_obs_id"], ["source_observations.obs_id"]),
    )
    op.create_index("idx_bench_lookup", "benchmarks", ["country_code", "kpi_code", "definition_id"])

    # ── ② kpi_definitions 시드 (§2 16종) ──
    for d in KPI_DEFINITIONS:
        conn.execute(
            sa.text(
                "INSERT INTO kpi_definitions "
                "(kpi_code, definition_id, name_ko, numerator_def, denominator_def, denominator_type, "
                " period_basis, direction, unit, value_scale, notes) VALUES "
                "(:kc, :did, :nk, :num, :den, :dt, :pb, :dir, :unit, :vs, :notes)"
            ),
            dict(kc=d["kpi_code"], did=definition_id_for(d["kpi_code"]), nk=d.get("name_ko"),
                 num=d["numerator_def"], den=d["denominator_def"], dt=d["denominator_type"],
                 pb=d["period_basis"], dir=d["direction"], unit=d["unit"], vs=d["value_scale"],
                 notes=d.get("notes")),
        )

    # ── ③ KR 27 이전 (source_observations + benchmarks, 강등 허용) ──
    kdefs = kpi_definition_index()
    kr_rows = conn.execute(sa.text(
        "SELECT metric_code, warning_threshold, critical_threshold, target_value, "
        "       alert_direction, unit_code, confidence, source_ref "
        "FROM default_metric_values WHERE scope_code='KR' AND scope_type='region' ORDER BY metric_code"
    )).fetchall()

    for r in kr_rows:
        metric, warn, crit, tgt, adir, unit, conf, src = (
            r.metric_code, r.warning_threshold, r.critical_threshold, r.target_value,
            r.alert_direction, r.unit_code, r.confidence, r.source_ref)
        raw = {"warning_threshold": _num(warn), "critical_threshold": _num(crit),
               "target_value": _num(tgt), "alert_direction": adir, "unit_code": unit,
               "confidence": conf, "source_ref": src}

        # source_observations: 원문 보존 (전 27종)
        obs_id = conn.execute(
            sa.text(
                "INSERT INTO source_observations "
                "(obs_group_id, source_id, source_name, country_code, source_kpi_code, source_value, "
                " population_scope, source_value_scale, confidence_level, is_provisional, raw_fields_json, notes) "
                "VALUES (:gid, :sid, :sname, 'KR', :skc, :sval, :pop, :svs, :conf, true, :raw, :notes) "
                "RETURNING obs_id"
            ),
            dict(gid="PIGPLAN_KR_2025", sid="PIGPLAN_KR", sname=(src or "PigPlan KR"),
                 skc=metric, sval=_num(tgt), pop="unknown",
                 svs=("percent_0_100" if unit == "%" else None),
                 conf=_conf_to_level(conf), raw=json.dumps(raw, ensure_ascii=False),
                 notes="KR PigPlan 임계 원문 이전(작업A). 기간·모집단 미확정 → publication/period NULL, B에서 한돈팜스 PDF 확인."),
        ).scalar()

        pigos = KR_MAP.get(metric)
        if pigos is None:
            # orphan: §2에 정의 없음 → benchmarks 생성 불가(복합FK). source_observations로만 보존.
            conn.execute(sa.text("UPDATE source_observations SET notes = notes || :n WHERE obs_id=:o"),
                         dict(n=" / §2 kpi_definitions 대응 KPI 없음(가격·잔존가·RTS·고산차 등) → 작업B/후속 KPI정의 결정.",
                              o=obs_id))
            continue

        kdef = kdefs[pigos]
        direction = kdef["direction"]
        bench = dict(country_code="KR", production_system="all", farm_size_band="all",
                     kpi_code=pigos, definition_id=kdef["definition_id"],
                     source_obs_id=obs_id, obs_group_id="PIGPLAN_KR_2025",
                     transform_formula=None, transformed_value=None,
                     warning_min=None, warning_max=None, critical_min=None, critical_max=None,
                     target=_num(tgt), is_provisional=True)

        if pigos == "stillbirth_rate":
            # 강등 missing: PigOS 사산율=(사산+미라)/총산, KR은 사산기준 추정·원자료 분리 없음 → 재정규화 불가
            bench.update(benchmark_status="missing", mapping_status="incompatible",
                         comparison_status="incompatible", value_scale=None, is_provisional=False,
                         target=None,
                         notes="강등=missing. KR STILLBORN_RATE 분자(미라 포함 여부) 불명·원자료 분리 없어 PigOS "
                               "stillbirth_rate(사산+미라)로 재정규화 불가. B에서 한돈팜스 원문 사산/미라 분리 확인 필요.")
        else:
            # provisional 강등: direction별 칸 배치(★⑪)
            if direction == "higher_better":
                bench.update(warning_min=_num(warn), critical_min=_num(crit))
            elif direction == "lower_better":
                bench.update(warning_max=_num(warn), critical_max=_num(crit))
            else:  # range_target (culling_rate): KR은 상단 임계만 보유
                bench.update(warning_max=_num(warn), critical_max=_num(crit))
            bench.update(
                benchmark_status="provisional", mapping_status="exact", comparison_status="compatible",
                value_scale=kdef["value_scale"],
                notes=("강등=provisional. KR PigPlan 임계 안전 이전. 모집단(전국/조합)·기간·정의 미확정 → "
                       "B에서 한돈팜스 원문으로 verified 판정."
                       + (" range_target인데 KR은 상단 임계만 있어 하단(노령화) 기준 없음."
                          if direction == "range_target" else "")))

        # seed validator로 사전검증(위반 시 migration 중단 → 매핑 수정 신호)
        validate_benchmark(bench, kdefs)
        conn.execute(
            sa.text(
                "INSERT INTO benchmarks "
                "(country_code, production_system, farm_size_band, kpi_code, definition_id, "
                " transformed_value, transform_formula, value_scale, source_obs_id, obs_group_id, "
                " warning_min, warning_max, critical_min, critical_max, target, "
                " mapping_status, comparison_status, benchmark_status, is_provisional, notes) VALUES "
                "(:country_code, :production_system, :farm_size_band, :kpi_code, :definition_id, "
                " :transformed_value, :transform_formula, :value_scale, :source_obs_id, :obs_group_id, "
                " :warning_min, :warning_max, :critical_min, :critical_max, :target, "
                " :mapping_status, :comparison_status, :benchmark_status, :is_provisional, :notes)"
            ),
            bench,
        )

    # ── ④ 제약 강화 (데이터 이전 후에만 — ★④⑦⑧⑫ + active verified 중복방지) ──
    op.create_foreign_key(
        "fk_bench_kpidef", "benchmarks", "kpi_definitions",
        ["kpi_code", "definition_id"], ["kpi_code", "definition_id"],
    )
    op.create_check_constraint(
        "ck_bench_verified_notprovisional", "benchmarks",
        "benchmark_status NOT IN ('verified','normalized_verified') "
        "OR (is_provisional = false AND transformed_value IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_bench_normverified_6cond", "benchmarks",
        "benchmark_status <> 'normalized_verified' OR ("
        "transform_formula IS NOT NULL AND mapping_status = 'normalized' "
        "AND comparison_status = 'normalized' AND transformed_value IS NOT NULL "
        "AND value_scale IS NOT NULL AND (source_obs_id IS NOT NULL OR obs_group_id IS NOT NULL))",
    )
    op.create_check_constraint(
        "ck_bench_verified_comparison", "benchmarks",
        "benchmark_status <> 'verified' OR comparison_status IN ('exact','compatible')",
    )
    op.create_check_constraint(
        "ck_bench_verified_noformula", "benchmarks",
        "benchmark_status <> 'verified' OR transform_formula IS NULL",
    )
    op.create_check_constraint(
        "ck_bench_missing_novalue", "benchmarks",
        "benchmark_status <> 'missing' OR transformed_value IS NULL",
    )
    op.create_check_constraint(
        "ck_bench_incompatible_silent", "benchmarks",
        "comparison_status NOT IN ('incompatible','unknown') OR ("
        "transformed_value IS NULL AND warning_min IS NULL AND warning_max IS NULL "
        "AND critical_min IS NULL AND critical_max IS NULL)",
    )
    op.create_index(
        "uq_bench_active_verified", "benchmarks",
        ["country_code", "production_system", "farm_size_band", "kpi_code", "definition_id"],
        unique=True,
        postgresql_where=sa.text("benchmark_status IN ('verified','normalized_verified') AND is_active"),
    )


def downgrade() -> None:
    op.drop_table("benchmarks")
    op.drop_table("source_observations")
    op.drop_table("kpi_definitions")


def _num(v):
    return float(v) if v is not None else None


def _conf_to_level(conf: str | None) -> str | None:
    return {"high": "A", "medium": "B", "low": "C"}.get((conf or "").lower())
