"""add rule_configs (운영자 콘솔 Phase 3 — AI 규칙 운영설정)

Revision ID: c3d5e7f9a1b3
Revises: b2c4e6a8d0f1
Create Date: 2026-06-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "c3d5e7f9a1b3"
down_revision: str | None = "b2c4e6a8d0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rule_configs",
        sa.Column("rule_id", sa.String(length=50), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("warning", sa.Float(), nullable=True),
        sa.Column("critical", sa.Float(), nullable=True),
        sa.Column("updated_by", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("rule_configs")
