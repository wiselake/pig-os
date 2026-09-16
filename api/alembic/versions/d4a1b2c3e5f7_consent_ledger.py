"""consent_ledger (동의·데이터이용 원장) + head 병합

CONSENT_AND_DATA_USE_SPEC §5.1 스키마. 기존 2개 head(1e6172486c75, e1d2c3b4a5f6)를
병합하면서 테이블을 생성한다.

⚠️ 프로드 DB는 alembic 히스토리가 발산(divergent) 상태 — 이 마이그레이션은 로컬/CI 전용.
프로드 반영은 사람이 스키마 수동 확인 후 별도 결정.

Revision ID: d4a1b2c3e5f7
Revises: 1e6172486c75, e1d2c3b4a5f6
Create Date: 2026-07-22
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4a1b2c3e5f7"
# DAG 정정: 1e6172486c75 는 e1d2c3b4a5f6 가 이미 조상으로 물고 있어 이중 클레임이었다.
down_revision: str | Sequence[str] | None = "e1d2c3b4a5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PURPOSE_CODES = (
    "SERVICE_OPERATION", "ANON_AGG_STATS", "AI_MODEL_TRAINING",
    "NAMED_RESEARCH", "TRANSACTION_MATCHING", "EXTERNAL_AI_PROCESSING",
)
LAWFUL_BASES = (
    "CONTRACT", "CONSENT", "LEGITIMATE_INTEREST",
    "ANONYMIZED_EXEMPT", "DEIDENTIFIED_EXEMPT", "PROCESSOR_TRANSFER",
)
CONSENT_STATUSES = (
    "GRANTED", "NOTICE_GIVEN", "WITHDRAWN", "OBJECTED",
    "EXCLUSION_REQUESTED", "EXPIRED",
)
COLLECTION_CONTEXTS = ("UI_SIGNUP", "UI_SETTINGS", "UI_JIT", "API", "MIGRATION")


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} IN (" + ", ".join(f"'{v}'" for v in values) + ")"


def upgrade() -> None:
    op.create_table(
        "consent_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("purpose_code", sa.String(length=32), nullable=False),
        sa.Column("jurisdiction", sa.String(length=8), nullable=False),
        sa.Column("lawful_basis", sa.String(length=24), nullable=False),
        sa.Column("consent_status", sa.String(length=24), nullable=False),
        sa.Column("notice_version", sa.String(length=255), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("downstream_recipient", postgresql.ARRAY(sa.String(length=120)), nullable=True),
        sa.Column("collection_context", sa.String(length=16), nullable=False, server_default="UI_SIGNUP"),
        sa.Column("evidence_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.CheckConstraint(_in("purpose_code", PURPOSE_CODES), name="ck_consent_purpose"),
        sa.CheckConstraint(_in("lawful_basis", LAWFUL_BASES), name="ck_consent_basis"),
        sa.CheckConstraint(_in("consent_status", CONSENT_STATUSES), name="ck_consent_status"),
        sa.CheckConstraint(_in("collection_context", COLLECTION_CONTEXTS), name="ck_consent_context"),
        sa.CheckConstraint(
            "lawful_basis <> 'CONSENT' OR evidence_ref IS NOT NULL",
            name="ck_consent_requires_evidence",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_consent_current", "consent_ledger",
                    ["user_id", "farm_id", "purpose_code", "created_at"])
    op.create_index("idx_consent_farm", "consent_ledger", ["farm_id", "purpose_code"])


def downgrade() -> None:
    op.drop_index("idx_consent_farm", table_name="consent_ledger")
    op.drop_index("idx_consent_current", table_name="consent_ledger")
    op.drop_table("consent_ledger")
