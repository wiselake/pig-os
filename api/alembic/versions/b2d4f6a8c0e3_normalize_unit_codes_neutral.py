"""normalize default_metric_values.unit_code to language-neutral tokens

일부 KR/이벤트-인사이트 시드가 unit_code를 한국어("두/복","두/복/년","일")로 넣어
EventInsight.unit → (a) 앱 InsightBanner, (b) 알림 body 로 그대로 새어
비한국어 사용자에게도 한국어 단위가 노출됐다(계약: "문구는 프론트 i18n" 위반).
같은 지표(PSY·WEANING_AGE)가 scope별로 서로 다른 단위(한국어 vs 중립)를 갖는
데이터 불일치도 동반. 여기서 unit_code를 중립 토큰으로 통일한다(프론트가 현지화).

데이터 정리 성격 → downgrade는 no-op(되돌리면 다시 한국어로 깨짐).

Revision ID: b2d4f6a8c0e3
Revises: a1c3e5b7d9f2
Create Date: 2026-07-01
"""
import sqlalchemy as sa

from alembic import op

revision = "b2d4f6a8c0e3"
down_revision = "a1c3e5b7d9f2"
branch_labels = None
depends_on = None

# 한국어 단위 → 중립 토큰. 중립 토큰은 default_metric_values에 이미 존재하는 값과 정렬:
#   "두/모돈/년" → "piglets/sow/year" (PSY/MSY 중립행과 동일)
#   "일"         → "days"             (NPD/WEANING_AGE 중립행과 동일)
#   "두/복"      → "piglets/litter"   (복당 두수 — 기존 중립행 없어 신설 표준)
_MAP = {
    "두/모돈/년": "piglets/sow/year",
    "두/복": "piglets/litter",
    "일": "days",
}


def upgrade() -> None:
    for ko, neutral in _MAP.items():
        op.execute(
            sa.text(
                "UPDATE default_metric_values SET unit_code = :n WHERE unit_code = :k"
            ).bindparams(n=neutral, k=ko)
        )


def downgrade() -> None:
    # 데이터 정규화 — 되돌리면 한국어 단위 노출 버그가 재발하므로 no-op.
    pass
