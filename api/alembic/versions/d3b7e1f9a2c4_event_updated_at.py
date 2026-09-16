"""이벤트 테이블에 updated_at 추가 (#7: 오프라인 sync pull이 서버측 수정분 감지)

이벤트 모델(matings/farrowings/weanings/pregnancy_checks/reproductive_events/
piglet_events/health_events)에 updated_at이 없어 _pull_server_changes가 created_at만
보고 → 서버에서 수정·소프트삭제된 행이 모바일로 pull되지 않았음. updated_at(onupdate)을
추가해 수정·삭제(soft-delete도 UPDATE라 updated_at 갱신)가 since 윈도우에 잡히게 한다.

Revision ID: d3b7e1f9a2c4
Revises: c9f1a3b5d7e2
"""
import sqlalchemy as sa

from alembic import op

revision = "d3b7e1f9a2c4"
down_revision = "c9f1a3b5d7e2"
branch_labels = None
depends_on = None

_TABLES = [
    "matings", "farrowings", "weanings", "pregnancy_checks",
    "reproductive_events", "piglet_events", "health_events",
]


def upgrade() -> None:
    for t in _TABLES:
        op.add_column(t, sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ))


def downgrade() -> None:
    for t in _TABLES:
        op.drop_column(t, "updated_at")
