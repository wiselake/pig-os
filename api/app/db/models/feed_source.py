"""Feed source persistence — 외부 사료 관측의 **불변 revision** + 동기화 원장 (P-1 topology C, 2026-09-22).

docs/feed/FEED_PERSISTENCE_ARCHITECTURE.md 가 정본. 요지:
  · 한 행 = 외부 원장의 한 row 의 한 **revision** (payload_hash 가 다르면 새 revision, 같으면 재삽입 없음 → 멱등)
  · 절대 UPDATE 로 값을 고치지 않는다. 정정 = 새 revision 추가 + 이전 revision superseded (P-5 B)
  · 소스에서 사라짐 = RETRACTED revision (tombstone). 물리 삭제 없음
  · quantity_basis 는 행의 속성이다 (AS_RECORDED | DELIVERED | CONSUMED) — 테이블 이름이 아니라 (P-3)
  · currency 는 NOT NULL — 소스 계약이 행마다 명시한다. PigOS farm.currency fallback 금지
  · 품질은 boolean 하나로 뭉개지 않는다: source_status(소스 사실) · quantity_status · cost_status · quality_reasons (§11)
  · Feed Engine 은 이 ORM 을 직접 읽지 않는다 — repositories/feed_source_repo.py 의 projection 이 RawFeedRow 로 바꾼다 (P-4)
  · 기존 feed_records(수기, AS_RECORDED) 는 건드리지 않는다. 다른 basis 의 관측은 중복이 아니라 다른 사실이다 (§14-15)
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

QUANTITY_BASES = ("AS_RECORDED", "DELIVERED", "CONSUMED")
SOURCE_STATUSES = ("ACTIVE", "INACTIVE", "RETRACTED")
QUANTITY_STATUSES = ("ACCEPTED", "EXCLUDED")
COST_STATUSES = ("ACCEPTED", "INSUFFICIENT", "EXCLUDED")
SYNC_STATUSES = ("RUNNING", "SUCCEEDED", "SOURCE_UNAVAILABLE", "SYNC_FAILED")


class FeedSourceSyncRun(Base):
    """동기화 원장 — 한 실행 = 한 행. 실패도 행이다(SOURCE_UNAVAILABLE ≠ 빈 데이터, §24)."""
    __tablename__ = "feed_source_sync_runs"
    __table_args__ = (
        CheckConstraint(f"status IN {SYNC_STATUSES}", name="ck_fssr_status"),
        Index("idx_fssr_source_started", "source_system", "source_dataset", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_system: Mapped[str] = mapped_column(String(20), nullable=False)
    source_dataset: Mapped[str] = mapped_column(String(40), nullable=False)
    source_contract_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 창: [window_start, window_end] 의 event_date 를 전량 대조(재철회 감지용) · watermark 는 소스 갱신시각 기준 증분
    window_start: Mapped[date | None] = mapped_column(Date)
    window_end: Mapped[date | None] = mapped_column(Date)
    watermark_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    watermark_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lookback_days: Mapped[int | None] = mapped_column(Integer)
    farms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)     # 새 revision (신규 + 정정)
    rows_unchanged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)    # 같은 payload_hash → 아무것도 안 함
    rows_superseded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)   # 정정으로 이전 revision 닫힘
    rows_retracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)    # 소스에서 사라져 tombstone
    error: Mapped[str | None] = mapped_column(Text)


class FeedSourceRow(Base):
    """외부 사료 관측 한 revision. INSERT 만 한다 (is_current/superseded_at 만 flip)."""
    __tablename__ = "feed_source_rows"
    __table_args__ = (
        # 멱등: 같은 identity + 같은 payload 는 한 번만
        UniqueConstraint("source_system", "source_dataset", "source_row_key", "payload_hash", name="uq_fsr_identity_payload"),
        UniqueConstraint("source_system", "source_dataset", "source_row_key", "revision", name="uq_fsr_identity_revision"),
        # 현재 revision 은 identity 당 하나
        Index("uq_fsr_identity_current", "source_system", "source_dataset", "source_row_key",
              unique=True, postgresql_where="is_current"),
        # projection 경로: 농장 × basis × 날짜, 현재·활성만
        Index("idx_fsr_farm_basis_date", "farm_id", "quantity_basis", "event_date",
              postgresql_where="is_current AND source_status = 'ACTIVE'"),
        CheckConstraint(f"quantity_basis IN {QUANTITY_BASES}", name="ck_fsr_basis"),
        CheckConstraint(f"source_status IN {SOURCE_STATUSES}", name="ck_fsr_source_status"),
        CheckConstraint(f"quantity_status IN {QUANTITY_STATUSES}", name="ck_fsr_quantity_status"),
        CheckConstraint(f"cost_status IN {COST_STATUSES}", name="ck_fsr_cost_status"),
        CheckConstraint("revision >= 1", name="ck_fsr_revision"),
    )

    # id 는 identity+payload 의 결정론 uuid5 (harvest_import 와 같은 규율) — 재실행이 같은 id 를 만들어 ON CONFLICT 가 성립한다
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    source_system: Mapped[str] = mapped_column(String(20), nullable=False)       # pigplan
    source_dataset: Mapped[str] = mapped_column(String(40), nullable=False)      # TM_ETC_TRADE
    source_row_key: Mapped[str] = mapped_column(String(64), nullable=False)      # "{FARM_NO}:{SEQ}" — 소스 PK, row number 아님
    source_contract_version: Mapped[str] = mapped_column(String(40), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_run_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("feed_source_sync_runs.id"))

    farm_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("farms.id"), nullable=False)  # 내부 키만

    event_date: Mapped[date | None] = mapped_column(Date)                        # 파싱/범위 실패면 NULL, 원문은 event_date_raw
    event_date_raw: Mapped[str | None] = mapped_column(String(32))
    quantity_kg: Mapped[float | None] = mapped_column(Numeric(12, 3))
    quantity_unit: Mapped[str] = mapped_column(String(8), nullable=False, default="kg")
    quantity_basis: Mapped[str] = mapped_column(String(12), nullable=False)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(14, 4))               # currency/kg (소스 직접값 또는 total/kg 파생 — reasons 에 표기)
    total_cost: Mapped[float | None] = mapped_column(Numeric(16, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    feed_stage_raw: Mapped[str | None] = mapped_column(String(50))
    feed_product_raw: Mapped[str | None] = mapped_column(String(200))

    source_status: Mapped[str] = mapped_column(String(10), nullable=False)       # ACTIVE | INACTIVE | RETRACTED
    quantity_status: Mapped[str] = mapped_column(String(12), nullable=False)     # ACCEPTED | EXCLUDED
    cost_status: Mapped[str] = mapped_column(String(12), nullable=False)         # ACCEPTED | INSUFFICIENT | EXCLUDED
    quality_reasons: Mapped[list[str] | None] = mapped_column(JSONB)

    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)   # 우리가 본 시각
    source_inserted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))     # LOG_INS_DT
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))      # LOG_UPT_DT (watermark 기준)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)                    # sha256(정규화 payload)
    payload: Mapped[dict | None] = mapped_column(JSONB)                                      # 원문 값(식별정보 없음) — lineage 용
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
