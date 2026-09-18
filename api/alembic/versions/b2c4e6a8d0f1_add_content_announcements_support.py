"""add announcements + support_tickets/replies (운영자 콘솔 Phase 2)

Revision ID: b2c4e6a8d0f1
Revises: a9b3c1d7e2f4
Create Date: 2026-06-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "b2c4e6a8d0f1"
down_revision: str | None = "a9b3c1d7e2f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False, server_default="GENERAL"),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("publish_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publish_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lang", sa.String(length=5), nullable=True),
        sa.Column("created_by", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_announcements_published", "announcements", ["published", "pinned"])

    op.create_table(
        "support_tickets",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("farm_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_support_tickets_status", "support_tickets", ["status", "created_at"])
    op.create_index("idx_support_tickets_user", "support_tickets", ["user_id"])

    op.create_table(
        "support_replies",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_id", PG_UUID(as_uuid=True), sa.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("is_staff", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_support_replies_ticket", "support_replies", ["ticket_id"])


def downgrade() -> None:
    op.drop_table("support_replies")
    op.drop_table("support_tickets")
    op.drop_table("announcements")
