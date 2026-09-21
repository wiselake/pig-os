"""tasks: (farm,sow,task_type,status) unique → OPEN-only partial unique

버그: uq_task_open_per_sow_type가 status를 유니크 키에 포함해, 같은 (farm,sow,task_type)의
DONE 작업을 2개 이상 못 가짐. 결과로 '작업 완료 → 다음 주기 재발생 → 재생성 → 재완료'가
UNIQUE 위반(409 CONFLICT)으로 막힘(실사용 흐름에서 발생).
→ OPEN 상태에서만 (farm,sow,task_type) 중복 방지하는 partial unique로 교정.
완료/취소(DONE/DISMISSED) 이력은 무제한 허용.

Revision ID: c3e5f7a9b1d4
Revises: b2d4f6a8c0e3
Create Date: 2026-07-02
"""
from sqlalchemy import text as sa_text

from alembic import op

revision = "c3e5f7a9b1d4"
down_revision = "b2d4f6a8c0e3"
branch_labels = None
depends_on = None

_NAME = "uq_task_open_per_sow_type"


def upgrade() -> None:
    # 기존 4컬럼(status 포함) 유니크 제거 후 OPEN 한정 partial unique 재생성.
    # SQLAlchemy UniqueConstraint는 PG에서 유니크 인덱스로 구현되지만,
    # 제약/인덱스 중 무엇으로 잡혀도 지우도록 방어적으로 시도.
    op.execute(f"ALTER TABLE tasks DROP CONSTRAINT IF EXISTS {_NAME}")
    op.execute(f"DROP INDEX IF EXISTS {_NAME}")
    op.create_index(
        _NAME, "tasks", ["farm_id", "sow_id", "task_type"],
        unique=True, postgresql_where=sa_text("status = 'OPEN'"),
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {_NAME}")
    op.create_index(
        _NAME, "tasks", ["farm_id", "sow_id", "task_type", "status"], unique=True,
    )
