"""Add nursing_head avg_birth_weight to farrowings, age_days to piglet_events (P0-BE-4/5/6)

Revision ID: dbeb4c5ed00f
Revises: b1c2d3e4f5a6
Create Date: 2026-06-19 09:39:30.762966

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'dbeb4c5ed00f'
down_revision: str | None = 'b1c2d3e4f5a6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # P0-BE-4/5/6 — 신규 컬럼만. (autogenerate가 잡은 무관한 드리프트는 제외)
    op.add_column('farrowings', sa.Column('nursing_head', sa.Integer(), nullable=True))
    op.add_column('farrowings', sa.Column('avg_birth_weight_kg', sa.Float(), nullable=True))
    op.add_column('piglet_events', sa.Column('age_days', sa.Integer(), nullable=True))
    # 기존 분만 데이터: nursing_head 초기값 = born_alive (포유개시두수 정합성)
    op.execute("UPDATE farrowings SET nursing_head = born_alive WHERE nursing_head IS NULL")


def downgrade() -> None:
    op.drop_column('piglet_events', 'age_days')
    op.drop_column('farrowings', 'avg_birth_weight_kg')
    op.drop_column('farrowings', 'nursing_head')
