"""add user.approval_status (운영자 콘솔 회원 가입승인)

기존 사용자 전원 APPROVED 기본값 → 잠김 0. 로그인 강제는 별도 단계.

Revision ID: a9b3c1d7e2f4
Revises: dbeb4c5ed00f
Create Date: 2026-06-22
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a9b3c1d7e2f4"
down_revision: str | None = "dbeb4c5ed00f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "approval_status",
            sa.String(length=20),
            nullable=False,
            server_default="APPROVED",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "approval_status")
