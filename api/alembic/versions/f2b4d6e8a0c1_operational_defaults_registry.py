"""operational_defaults 레지스트리 — 룰 코드 인라인 임계 1:1 이전 (A-하이브리드 2.1)

handoff/operational_default_inventory.md / A-하이브리드 §3.2.
글로벌 임상 임계(코드 default)를 명시 레지스트리로 이전. 값 보존(§10.2), origin/원본값 메타(②), scope=global(③).
base.py 특수형(PSY 밴드/NPD overdue/farrowing)은 코드 유지(㉮) — 제외.

Revision ID: f2b4d6e8a0c1
Revises: e1a3c5d7f9b2
"""
import sqlalchemy as sa

from alembic import op
from app.db.operational_defaults_seed import OPERATIONAL_DEFAULTS, to_bounds

revision = "f2b4d6e8a0c1"
down_revision = "e1a3c5d7f9b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_defaults",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scope", sa.Text(), server_default="global", nullable=False),
        sa.Column("country_code", sa.Text()),
        sa.Column("rule_id", sa.Text(), nullable=False),
        sa.Column("kpi_code", sa.Text(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("value_scale", sa.Text(), nullable=False),
        sa.Column("warning_min", sa.Numeric()),
        sa.Column("warning_max", sa.Numeric()),
        sa.Column("critical_min", sa.Numeric()),
        sa.Column("critical_max", sa.Numeric()),
        sa.Column("origin", sa.Text(), server_default="code_default", nullable=False),
        sa.Column("source_rule", sa.Text()),
        sa.Column("source_loc", sa.Text()),
        sa.Column("original_warning", sa.Numeric()),
        sa.Column("original_critical", sa.Numeric()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "country_code", "rule_id", name="uq_opdef_scope_rule"),
        sa.CheckConstraint("direction IN ('higher_better','lower_better','range_target')", name="ck_opdef_direction"),
        sa.CheckConstraint("value_scale IN ('percent_0_100','ratio_0_1','n/a')", name="ck_opdef_valuescale"),
        sa.CheckConstraint("origin IN ('code_default','operator','imported')", name="ck_opdef_origin"),
    )
    op.create_index("idx_opdef_lookup", "operational_defaults", ["country_code", "rule_id"])

    conn = op.get_bind()
    for d in OPERATIONAL_DEFAULTS:
        b = to_bounds(d)
        conn.execute(
            sa.text(
                "INSERT INTO operational_defaults "
                "(scope, country_code, rule_id, kpi_code, direction, value_scale, "
                " warning_min, warning_max, critical_min, critical_max, "
                " origin, source_rule, source_loc, original_warning, original_critical, notes) "
                "VALUES ('global', NULL, :rid, :kpi, :dir, :vs, "
                " :wmin, :wmax, :cmin, :cmax, 'code_default', :rid, :src, :ow, :oc, "
                " '룰 코드 인라인 임계 1:1 이전(값 보존). A-하이브리드.')"
            ),
            dict(rid=d["rule_id"], kpi=d["kpi_code"], dir=d["direction"], vs=d["value_scale"],
                 wmin=b["warning_min"], wmax=b["warning_max"], cmin=b["critical_min"], cmax=b["critical_max"],
                 src=d["src"], ow=d["warning"], oc=d["critical"]),
        )


def downgrade() -> None:
    op.drop_table("operational_defaults")
