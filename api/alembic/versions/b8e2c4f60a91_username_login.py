"""username 기반 로그인 — users.username 추가(unique·not null) + email not null

PigOS 로그인을 email→username으로 전환(현장형). email은 복구·알림용 필수 유지.
출시 전(유저 ~0) 기준 단순 마이그레이션. 기존 행은 email 로컬파트로 username 백필.

Revision ID: b8e2c4f60a91
Revises: d4f6a8c1e2b3
"""
import sqlalchemy as sa

from alembic import op

revision = "b8e2c4f60a91"
down_revision = "d4f6a8c1e2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) username 컬럼 추가(우선 nullable)
    op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))
    # 2) 백필: email 로컬파트 → username. 충돌 시 id 앞 8자 접미(출시 전 저볼륨)
    op.execute("""
        UPDATE users SET username = split_part(email, '@', 1)
        WHERE username IS NULL AND email IS NOT NULL
    """)
    op.execute("""
        UPDATE users u SET username = u.username || '_' || left(u.id::text, 8)
        WHERE u.id IN (
            SELECT id FROM (
                SELECT id, row_number() OVER (PARTITION BY username ORDER BY created_at) rn
                FROM users WHERE username IS NOT NULL
            ) t WHERE t.rn > 1
        )
    """)
    op.execute("UPDATE users SET username = 'user_' || left(id::text, 8) WHERE username IS NULL OR username = ''")
    # 3) 제약: NOT NULL + unique
    op.alter_column("users", "username", nullable=False)
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    # 4) email NOT NULL (복구·연락 필수). 출시 전 모든 행 email 보유 가정.
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)


def downgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "username")
