"""
알림 발송 잡 — alert→IN_APP 영구화 + FCM 푸시 요약 전송 (G1).

푸시는 push_service가 미설정/미설치 시 graceful skip하므로 잡은 항상 안전.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.db.models.platform import Farm
from app.db.session import AsyncSessionLocal
from app.jobs._result import job_result
from app.services import device_service, notification_service, push_service

log = logging.getLogger(__name__)


async def send_push_notification(
    ctx: dict,
    user_id: str,
    title: str,
    body: str,
    alert_type: str = "SYSTEM",
    farm_id: str | None = None,
) -> str:
    """FCM/APNs 푸시 발송. Phase 2 구현 예정."""
    log.info("PUSH [stub] user=%s title=%s", user_id, title)
    # TODO Phase 2: FCM HTTP v1 API 연동
    return f"stub:push:{user_id}"


async def send_rule_alert(
    ctx: dict,
    farm_id: str,
    rule_id: str,
    severity: str,
    message: str,
) -> str:
    """
    Rule Engine CRITICAL/WARNING 알림 발송.
    대상: farm의 OWNER + MANAGER 역할 사용자.
    """
    log.info("RULE_ALERT [stub] farm=%s rule=%s severity=%s", farm_id, rule_id, severity)
    # TODO Phase 2:
    #   1. DB에서 farm_id + role IN (OWNER, MANAGER) 사용자 조회
    #   2. send_push_notification 잡 enqueue
    #   3. severity==CRITICAL → 이메일도 발송
    return f"stub:rule_alert:{farm_id}:{rule_id}"


async def generate_notifications_job(ctx: dict) -> str:
    """전 활성 농장 순회 — alert(과기한/도태/KPI) → IN_APP 영구 알림 멱등 생성 (P12-6).

    스케줄: 매일 06:00 UTC (worker.py cron_jobs).
    """
    async with AsyncSessionLocal() as db:
        farm_ids = list(await db.scalars(
            select(Farm.id).where(Farm.active.is_(True))
        ))

    processed = 0
    errors = 0
    total_created = 0
    total_pushed = 0
    for farm_id in farm_ids:
        try:
            async with AsyncSessionLocal() as db:
                created = await notification_service.create_from_alerts(db, farm_id)
                total_created += created
                # 신규 알림 있을 때만 수신자 단말에 요약 푸시 (미설정 시 graceful skip)
                if created > 0:
                    recipients = await notification_service.farm_recipients(db, farm_id)
                    tokens = await device_service.active_tokens_for_users(db, recipients)
                    res = await push_service.send_push(
                        tokens,
                        title="PigOS",
                        body=f"새 알림 {created}건이 있습니다.",
                        data={"farm_id": str(farm_id), "type": "alert_digest"},
                    )
                    total_pushed += res.sent
            processed += 1
        except Exception as e:  # noqa: BLE001 — 한 농장 실패 격리
            log.error("generate_notifications farm=%s error=%s", farm_id, e)
            errors += 1

    return job_result(
        "generate_notifications_job",
        expected=len(farm_ids), success=processed, errors=errors,
        detail=f"{total_created} created, {total_pushed} pushed",
    )
