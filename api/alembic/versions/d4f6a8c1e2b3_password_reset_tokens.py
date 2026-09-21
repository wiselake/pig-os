"""password_reset_tokens — 비밀번호 재설정 1회용 토큰 테이블

Revision ID: d4f6a8c1e2b3
Revises: 8b817ad8587a
Create Date: 2026-06-26

(codex governance 머지 8b817ad8587a 뒤로 재지정 — 2026-06-26 rebase 시 단일 head 유지.)
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4f6a8c1e2b3"
down_revision: str | None = "8b817ad8587a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_prt_user", "password_reset_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_prt_user", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
