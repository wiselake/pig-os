"""merge npd(f7a1) + tasks(c3e5) heads

Revision ID: 1e6172486c75
Revises: c3e5f7a9b1d4, f7a1c3e5b9d0
Create Date: 2026-07-07 12:25:48.831961

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '1e6172486c75'
down_revision: str | None = ('c3e5f7a9b1d4', 'f7a1c3e5b9d0')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
