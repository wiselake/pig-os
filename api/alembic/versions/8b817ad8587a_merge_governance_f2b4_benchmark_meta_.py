"""merge governance(f2b4) + benchmark_meta(c1e3) heads

Revision ID: 8b817ad8587a
Revises: f2b4d6e8a0c1, c1e3f5a7b9d2
Create Date: 2026-06-26 11:53:25.127703

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '8b817ad8587a'
down_revision: str | None = ('f2b4d6e8a0c1', 'c1e3f5a7b9d2')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
