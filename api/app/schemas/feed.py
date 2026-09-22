"""사료 급여(Feed) 입력 스키마 — 수기 급이량 기록.

Core 누락 고리(handoff/FINDING_feed_input_gap.md) 해소: FCR 계산의 입력원.
대상은 선택(농장 전체/사bldg/그룹/모돈). quantity_kg는 필수(>0).
"""
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class FeedRecordCreate(BaseModel):
    record_date: date
    quantity_kg: float = Field(..., gt=0, le=100000, description="급여량(kg). 0 초과")
    feed_type: str | None = Field(None, max_length=50, description="사료 종류(예: 임신돈/포유돈/비육)")
    sow_id: UUID | None = None
    group_id: UUID | None = None        # finisher_group 등
    building_id: UUID | None = None
    # DB unit_cost = Numeric(10,4) → 최대 999,999.9999. 상한 없으면 큰 값에 DB overflow(500) (M4).
    unit_cost: float | None = Field(None, ge=0, le=999999, description="kg당 단가(선택)")
    currency: str | None = Field(None, max_length=3)
    notes: str | None = None

    @field_validator("record_date")
    @classmethod
    def _no_far_future_date(cls, v: date) -> date:
        """미래일자 사료는 기간 리포트를 왜곡한다 → 거부 (M5).

        ★ 여기서는 **서버 날짜 +1일**까지만 본다 — 스키마는 농장을 모른다.
          UTC 서버 기준으로 자르면 서버보다 앞선 타임존 농장(서울 UTC+9)이 자기 오늘
          날짜를 넣지 못한다(2026-08-25 독립검증에서 이 경로가 남아 있었다).
          전 세계 최대 오프셋이 UTC+14 라 +1일이 정확한 상한이다.

          정밀 판정은 농장 현지 기준으로 feed_service.create_feed_record 가 한다.
        """
        if v > datetime.now(UTC).date() + timedelta(days=1):
            raise ValueError("record_date cannot be in the future")
        return v


class FeedRecordResponse(BaseModel):
    id: UUID
    farm_id: UUID
    record_date: date
    quantity_kg: float
    feed_type: str | None
    sow_id: UUID | None
    group_id: UUID | None
    building_id: UUID | None
    unit_cost: float | None
    currency: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedBasicOut(BaseModel):
    """Feed Basic 응답 계약 — PIGOS-F-0011. ★ 아직 어느 라우터도 이것을 내보내지 않는다.

    계약을 지금 정하는 이유: 값이 없는 칸이 "0" 인지 "못 냈다" 인지를 응답이 스스로 말해야
    한다. iOS 가 판정 없음을 초록으로 그리던 것(M-3)과 같은 fail-OPEN 이 원가 칸에서 재현되지
    않게, 유보 이유(`withheld`)를 계약에 **지금** 넣는다 — 노출 전이라 비용이 0 이고, 노출 뒤에
    넣으면 게시된 계약을 바꾸는 일이라 웹·Android·iOS 셋이 따라와야 한다.
    """
    formula_version: str
    fcr: float | None
    feed_cost_per_pig: float | None
    feed_cost_per_kg_gain: float | None
    currency: str | None
    withheld: dict[str, str]          # 지표 → 이유 (feed_metrics.NO_GAIN · COST_INCOMPLETE · CURRENCY_MIXED …)

