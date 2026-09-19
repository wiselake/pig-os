"""country_kpi_policy 테이블 + GLOBAL seed (v0.4 P1 정책벡터)

COUNTRY_KPI_RULE_SPEC v0.3.1 §4.2 + v0.4 패치. GLOBAL seed는 '현재 라이브 동작을 codify'
(신규 제품결정 아님·위조0): 코드 구현된 SSOT KPI의 compute/display/rule을 그대로 APPROVED.
priority_class는 NULL(미결 — 제품결정 대기). 국가별 override 행은 G-C 게이트 통과분만 후속.

⚠️ 프로드 alembic divergent — 로컬/CI 전용.

Revision ID: c7d9e1f3a5b8
Revises: d4a1b2c3e5f7
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c7d9e1f3a5b8"
down_revision: str | Sequence[str] | None = "d4a1b2c3e5f7"
branch_labels = None
depends_on = None

SCOPE = ("GLOBAL", "COUNTRY", "FARM_TYPE", "TENANT")
DISPLAY = ("PRIMARY", "SECONDARY", "HIDDEN")
BENCH = ("FULL", "CONTEXT_ONLY", "NONE")
APIEXP = ("PUBLIC", "TENANT_ONLY", "INTERNAL_ONLY", "NONE")
DEC = ("PROPOSED", "REVIEWED", "APPROVED", "REJECTED")
PRIO = ("NORTH_STAR", "DRIVER", "GUARDRAIL", "FINANCIAL", "QUALITY", "CONTEXT")
STAGE = ("BREEDING", "NURSERY", "GROW_FINISH", "FARROW_TO_FINISH")
EVID = ("VERIFIED", "OFFICIAL_GUIDANCE", "DRAFT_GUIDANCE", "REVIEWED_DIRECTION", "UNVERIFIED_DRAFT", "INSUFFICIENT")


def _in(c, v):
    return f"{c} IN (" + ", ".join(f"'{x}'" for x in v) + ")"


def upgrade() -> None:
    op.create_table(
        "country_kpi_policy",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_level", sa.String(16), nullable=False),
        sa.Column("country_code", sa.String(2)),
        sa.Column("farm_type", sa.String(24)),
        sa.Column("production_system", sa.String(24)),
        sa.Column("production_stage", sa.String(16)),
        sa.Column("herd_size_band", sa.String(24)),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("kpi_code", sa.String(64), nullable=False),
        sa.Column("compute_enabled", sa.Boolean()),
        sa.Column("display_role", sa.String(16)),
        sa.Column("priority_class", sa.String(16)),
        sa.Column("rule_enabled", sa.Boolean()),
        sa.Column("benchmark_exposure", sa.String(16)),
        sa.Column("prediction_feature", sa.Boolean()),
        sa.Column("api_export_policy", sa.String(24)),
        sa.Column("evidence_status", sa.String(24)),
        sa.Column("decision_status", sa.String(16), nullable=False, server_default="PROPOSED"),
        sa.Column("decided_by", sa.String(64)),
        sa.Column("effective_from", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("effective_to", sa.Date()),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(scope_level = 'GLOBAL'    AND country_code IS NULL AND farm_type IS NULL AND tenant_id IS NULL) OR "
            "(scope_level = 'COUNTRY'   AND country_code IS NOT NULL AND farm_type IS NULL AND tenant_id IS NULL) OR "
            "(scope_level = 'FARM_TYPE' AND country_code IS NOT NULL AND farm_type IS NOT NULL AND tenant_id IS NULL) OR "
            "(scope_level = 'TENANT'    AND tenant_id IS NOT NULL)", name="ck_ckp_scope_keys"),
        sa.CheckConstraint(
            "scope_level != 'GLOBAL' OR (compute_enabled IS NOT NULL AND display_role IS NOT NULL AND "
            "rule_enabled IS NOT NULL AND benchmark_exposure IS NOT NULL AND prediction_feature IS NOT NULL AND "
            "api_export_policy IS NOT NULL)", name="ck_ckp_global_complete"),
        sa.CheckConstraint("decision_status != 'APPROVED' OR decided_by IS NOT NULL", name="ck_ckp_approved_decided"),
        sa.CheckConstraint(
            "decision_status != 'APPROVED' OR evidence_status IS NULL OR "
            "evidence_status NOT IN ('UNVERIFIED_DRAFT','INSUFFICIENT') OR note IS NOT NULL",
            name="ck_ckp_approved_needs_evidence"),
        sa.CheckConstraint(_in("scope_level", SCOPE), name="ck_ckp_scope"),
        sa.CheckConstraint("display_role IS NULL OR " + _in("display_role", DISPLAY), name="ck_ckp_display"),
        sa.CheckConstraint("priority_class IS NULL OR " + _in("priority_class", PRIO), name="ck_ckp_priority"),
        sa.CheckConstraint("production_stage IS NULL OR " + _in("production_stage", STAGE), name="ck_ckp_stage"),
        sa.CheckConstraint("evidence_status IS NULL OR " + _in("evidence_status", EVID), name="ck_ckp_evidence"),
        sa.CheckConstraint("benchmark_exposure IS NULL OR " + _in("benchmark_exposure", BENCH), name="ck_ckp_bench"),
        sa.CheckConstraint("api_export_policy IS NULL OR " + _in("api_export_policy", APIEXP), name="ck_ckp_api"),
        sa.CheckConstraint(_in("decision_status", DEC), name="ck_ckp_decision"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ckp_resolve", "country_kpi_policy",
                    ["kpi_code", "scope_level", "country_code", "farm_type", "production_stage"])
    # NORTH_STAR 유일성: (country,farm_type,stage)당 APPROVED NORTH_STAR ≤1 (부분 유니크)
    op.execute(
        "CREATE UNIQUE INDEX uq_ckp_north_star ON country_kpi_policy "
        "(COALESCE(country_code,''), COALESCE(farm_type,''), COALESCE(production_stage,'')) "
        "WHERE priority_class='NORTH_STAR' AND decision_status='APPROVED'"
    )

    # --- GLOBAL seed: 현재 라이브 동작 codify (APPROVED). priority_class=NULL(미결). ---
    # (kpi_code, display_role, rule_enabled, benchmark_exposure, evidence_status)
    V, R = "VERIFIED", "REVIEWED_DIRECTION"
    rows = [
        ("PSY", "PRIMARY", True, "CONTEXT_ONLY", V),
        ("NPD", "PRIMARY", True, "CONTEXT_ONLY", V),
        ("FARROWING_RATE", "PRIMARY", True, "CONTEXT_ONLY", V),
        ("SOW_TURNOVER", "SECONDARY", False, "CONTEXT_ONLY", V),
        ("MSY", "SECONDARY", False, "CONTEXT_ONLY", R),
        ("FCR", "SECONDARY", False, "CONTEXT_ONLY", R),
        ("ADG", "SECONDARY", False, "CONTEXT_ONLY", R),
        ("WSI", "SECONDARY", True, "CONTEXT_ONLY", R),
        ("RTS_RATE", "SECONDARY", True, "CONTEXT_ONLY", R),
        ("PWMR", "SECONDARY", True, "CONTEXT_ONLY", R),
        ("BORN_ALIVE", "SECONDARY", False, "CONTEXT_ONLY", R),
        ("WEANED_COUNT", "SECONDARY", False, "CONTEXT_ONLY", R),
        ("SOW_MORTALITY", "SECONDARY", True, "CONTEXT_ONLY", V),
        # 사산율: 외부비교 무효(정의 상이) → benchmark NONE
        ("STILLBORN_RATE", "SECONDARY", False, "NONE", V),
    ]
    import uuid
    t = sa.table(
        "country_kpi_policy",
        sa.column("id"), sa.column("scope_level"), sa.column("kpi_code"),
        sa.column("compute_enabled"), sa.column("display_role"), sa.column("rule_enabled"),
        sa.column("benchmark_exposure"), sa.column("prediction_feature"), sa.column("api_export_policy"),
        sa.column("evidence_status"), sa.column("decision_status"), sa.column("decided_by"), sa.column("note"),
    )
    op.bulk_insert(t, [
        dict(id=uuid.uuid4(), scope_level="GLOBAL", kpi_code=k, compute_enabled=True,
             display_role=dr, rule_enabled=re, benchmark_exposure=be, prediction_feature=False,
             api_export_policy="TENANT_ONLY", evidence_status=ev, decision_status="APPROVED",
             decided_by="v0.4-P1-baseline",
             note="현재 구현된 SSOT 동작 codify. priority_class는 제품결정 대기(NULL).")
        for (k, dr, re, be, ev) in rows
    ])


def downgrade() -> None:
    op.drop_index("uq_ckp_north_star", table_name="country_kpi_policy")
    op.drop_index("idx_ckp_resolve", table_name="country_kpi_policy")
    op.drop_table("country_kpi_policy")
