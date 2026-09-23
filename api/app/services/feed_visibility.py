"""Feed Delivery Intelligence 노출 상태 — 서버에서만 판정한다 (결정 D-15a · Q-0, 2026-09-23).

    HIDDEN              입고 영역 없음 · DELIVERED 조회는 404          ← 기본값
    REFERENCE_VISIBLE   KR PigPlan 레퍼런스·내부 계정 — 시연·검증용, 상용 공개 아님
    CUSTOMER_VISIBLE    상용 고객 공개 — 코드 경로만 있다. 결재 전에는 어떤 농장에도 설정하지 않는다

판정 근거는 **명시적 플래그 하나**: farm_configs(config_key = FEED_DELIVERY_VISIBILITY). 사용자 API 로는 쓸 수 없다
(온보딩·번식 설정은 허용 키만 받는다). 농장 국가·관할로 유추하지 않는다 — 기준 확정은 결정 대기(DQ-1).
행이 없거나 값이 셋 중 하나가 아니면 HIDDEN (fail closed).
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.config import FarmConfig

HIDDEN = "HIDDEN"
REFERENCE_VISIBLE = "REFERENCE_VISIBLE"
CUSTOMER_VISIBLE = "CUSTOMER_VISIBLE"
STATES = (HIDDEN, REFERENCE_VISIBLE, CUSTOMER_VISIBLE)
VISIBILITY_KEY = "FEED_DELIVERY_VISIBILITY"


async def delivered_visibility(db: AsyncSession, farm_id: UUID) -> str:
    v = await db.scalar(select(FarmConfig.config_value).where(
        FarmConfig.farm_id == farm_id, FarmConfig.config_key == VISIBILITY_KEY))
    return v if v in (REFERENCE_VISIBLE, CUSTOMER_VISIBLE) else HIDDEN


def is_visible(state: str) -> bool:
    return state in (REFERENCE_VISIBLE, CUSTOMER_VISIBLE)
