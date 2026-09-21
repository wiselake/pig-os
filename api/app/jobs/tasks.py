"""
Task 자동배정 잡 — alert → 오늘 할 일 (Phase 2).

스케줄: 매일 05:30 UTC (worker.py cron_jobs).
전 활성 농장 순회 → task_service.generate_tasks 멱등 호출.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.db.models.platform import Farm
from app.db.session import AsyncSessionLocal
from app.jobs._result import job_result
from app.services import task_service

log = logging.getLogger(__name__)


async def generate_tasks_job(ctx: dict) -> str:
    """전 활성 농장에 대해 alert 기반 Task 자동 생성/갱신."""
    async with AsyncSessionLocal() as db:
        farm_ids = list(await db.scalars(
            select(Farm.id).where(Farm.active.is_(True))
        ))

    processed = 0
    errors = 0
    total_created = 0
    for farm_id in farm_ids:
        try:
            async with AsyncSessionLocal() as db:
                created, _closed, _open_total = await task_service.generate_tasks(db, farm_id)
                total_created += created
            processed += 1
        except Exception as e:  # noqa: BLE001 — 한 농장 실패가 전체를 막지 않도록 격리
            log.error("generate_tasks farm=%s error=%s", farm_id, e)
            errors += 1

    return job_result(
        "generate_tasks_job",
        expected=len(farm_ids), success=processed, errors=errors,
        detail=f"{total_created} created",
    )
