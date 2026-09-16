"""add benchmark verification metadata to default_metric_values (definition_id, benchmark_status)

검증 게이트 메타만 추가 — 수치(threshold/avg/target 등)는 일절 건드리지 않는다(위조 0).
- definition_id: 어떤 정의로 계산된 값인지(외부값 재정규화 판단 기준). 기본 NULL — 정의 매핑은 별도 단계.
- benchmark_status: 'missing'|'unverified'|'provisional'|'verified'. 룰 전환(보류) 시 발화 게이트.
  기존 행: 값 있으면 'unverified'(검증 대기), 값 전무면 'missing'. 검증된 값은 이후 'verified'로 주입.
정의: docs/KPI_DEFINITIONS.md. 결정: docs/verification/2026-06-24_country_kpi_audit.md.

Revision ID: c1e3f5a7b9d2
Revises: b3d5f7091a2c
"""
import sqlalchemy as sa

from alembic import op

revision = "c1e3f5a7b9d2"
down_revision = "b3d5f7091a2c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("default_metric_values", sa.Column("definition_id", sa.String(length=60), nullable=True))
    op.add_column(
        "default_metric_values",
        sa.Column("benchmark_status", sa.String(length=16), nullable=False, server_default="unverified"),
    )
    # 값이 전혀 없는 행(임계·평균·목표 모두 NULL)은 'missing' — 룰 전환 시 침묵 대상.
    # 값 있는 행은 server_default 'unverified' 유지(검증 전이라 verified 아님 — 위조 없음).
    op.execute(
        """
        UPDATE default_metric_values
        SET benchmark_status = 'missing'
        WHERE warning_threshold IS NULL
          AND critical_threshold IS NULL
          AND benchmark_avg IS NULL
          AND target_value IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("default_metric_values", "benchmark_status")
    op.drop_column("default_metric_values", "definition_id")
