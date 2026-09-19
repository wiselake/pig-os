"""
Notification 서비스 — 인앱 알림 목록/읽음 처리 (P12-6 + 모바일).

수신자(user_id) 스코프. read_at IS NULL = 미읽음.
IN_APP 채널만 노출 (PUSH/EMAIL/SMS 전송로그는 목록에서 제외).
"""
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.ops import Notification

log = logging.getLogger(__name__)

# 목록에 노출하는 채널 (전송 추적 로그 제외)
_INAPP_TYPES = ("IN_APP",)
_SEVERITY_RANK = {"INFO": 0, "WARNING": 1, "CRITICAL": 2}  # 승격 판정용(높을수록 심각)


async def _unread_count(db: AsyncSession, user_id: UUID, farm_id: UUID | None) -> int:
    q = select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id,
        Notification.type.in_(_INAPP_TYPES),
        Notification.read_at.is_(None),
    )
    if farm_id:
        q = q.where(Notification.farm_id == farm_id)
    return int(await db.scalar(q) or 0)


async def list_notifications(
    db: AsyncSession, user_id: UUID, farm_id: UUID | None = None,
    unread_only: bool = False, limit: int = 50, offset: int = 0,
) -> tuple[list[Notification], int, int]:
    """(items, unread_count, total) 반환. 최신순."""
    base = [
        Notification.user_id == user_id,
        Notification.type.in_(_INAPP_TYPES),
    ]
    if farm_id:
        base.append(Notification.farm_id == farm_id)
    if unread_only:
        base.append(Notification.read_at.is_(None))

    total = int(await db.scalar(
        select(func.count()).select_from(Notification).where(*base)
    ) or 0)

    rows = list(await db.scalars(
        select(Notification).where(*base)
        .order_by(Notification.created_at.desc())
        .limit(limit).offset(offset)
    ))
    unread = await _unread_count(db, user_id, farm_id)
    return rows, unread, total


async def mark_read(db: AsyncSession, user_id: UUID, notification_id: UUID) -> int:
    notif = await db.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id,
        )
    )
    if not notif:
        raise NotFoundError(f"Notification {notification_id} not found")
    if notif.read_at is None:
        notif.read_at = datetime.now(UTC)
        await db.commit()
        return 1
    return 0


async def mark_all_read(db: AsyncSession, user_id: UUID, farm_id: UUID | None = None) -> int:
    conds = [
        Notification.user_id == user_id,
        Notification.type.in_(_INAPP_TYPES),
        Notification.read_at.is_(None),
    ]
    if farm_id:
        conds.append(Notification.farm_id == farm_id)
    result = await db.execute(
        update(Notification).where(*conds).values(read_at=datetime.now(UTC))
    )
    await db.commit()
    return result.rowcount or 0


# ── Producer: alert → 영구 IN_APP Notification (P12-6) ──────────────────
# OWNER/MANAGER 농장 멤버에게 alert를 영구 알림으로 적재. 멱등(미읽음 중복 방지).
_OWNER_MANAGER_ROLES = ("FARM_OWNER", "FARM_MANAGER")

# overdue 유형 → 표시용 제목 (프론트는 alert_type 기준 현지화 가능, 본 문자열은 폴백)
OVERDUE_TITLES = {
    "gilt_no_estrus": "Gilt heat check overdue",
    "gilt_overdue_mating": "Gilt mating overdue",
    "pregnant_overdue_farrowing": "Farrowing overdue",
    "lactating_overdue_weaning": "Weaning overdue",
    "open_overdue_mating": "Mating overdue",
    "accident_overdue_mating": "Re-mating overdue (RTS)",
}


async def _farm_recipients(db: AsyncSession, farm_id: UUID) -> list[UUID]:
    """농장 멤버 중 유효 역할이 OWNER/MANAGER인 활성 유저 id 목록.

    유효 역할 = user_farms.role_override 우선, 없으면 users.system_role.
    """
    from app.db.models.platform import User, UserFarm

    q = (
        select(User.id)
        .join(UserFarm, UserFarm.user_id == User.id)
        .where(
            UserFarm.farm_id == farm_id,
            User.active.is_(True),
            func.coalesce(UserFarm.role_override, User.system_role).in_(_OWNER_MANAGER_ROLES),
        )
    )
    return list(await db.scalars(q))


async def farm_recipients(db: AsyncSession, farm_id: UUID) -> list[UUID]:
    """푸시/알림 수신 대상(OWNER/MANAGER) 유저 id — 잡/푸시 연동용 공개 래퍼."""
    return await _farm_recipients(db, farm_id)


async def create_from_alerts(db: AsyncSession, farm_id: UUID, today=None) -> int:
    """alert_service 과기한/도태 + KPI 알림을 OWNER/MANAGER에게 IN_APP 영구화.

    멱등: 같은 (user_id, alert_type, related_entity_id)의 미읽음 알림이 있으면 재생성하지 않음.
    반환: 신규 생성 건수.
    """
    from app.db.models.platform import Farm
    from app.services import alert_service, kpi_service

    recipients = await _farm_recipients(db, farm_id)
    if not recipients:
        return 0

    items: list[dict] = []

    # 1) 과기한 모돈 (6유형)
    for o in await alert_service.get_overdue_sows(db, farm_id, today=today):
        otype = o["type"]
        items.append({
            "alert_type": f"OVERDUE_{otype.upper()}",
            "severity": "WARNING",
            "title": OVERDUE_TITLES.get(otype, "Sow attention required"),
            "body": f"Sow {o['ear_tag']} is {o['overdue_days']} day(s) overdue ({otype}).",
            "related_entity_type": "sow",
            "related_entity_id": o["sow_id"],
        })

    # 2) 도태 권고
    for c in await alert_service.get_cull_candidates(db, farm_id, today=today):
        reasons = ", ".join(c.get("reasons", []))
        items.append({
            "alert_type": "CULL_CANDIDATE",
            "severity": "WARNING",
            "title": "Culling candidate",
            "body": f"Sow {c['ear_tag']} (parity {c.get('parity')}): {reasons}",
            "related_entity_type": "sow",
            "related_entity_id": c["sow_id"],
        })

    # 3) KPI 알림 (Rule Engine WARNING/CRITICAL) — 한 농장 KPI 오류가 전체를 막지 않도록 격리.
    # savepoint(begin_nested)로 감싸 KPI 집계 실패 시 외부 트랜잭션이 오염되지 않게 한다.
    farm = await db.get(Farm, farm_id)
    if farm is not None:
        try:
            async with db.begin_nested():
                dash = await kpi_service.get_dashboard(db, farm)
                for a in dash.alerts:
                    items.append({
                        "alert_type": f"KPI_{a.kpi}",
                        "severity": a.severity,
                        "title": f"{a.kpi} alert",
                        "body": a.message,
                        "related_entity_type": "kpi",
                        "related_entity_id": None,
                    })
        except Exception:  # noqa: BLE001 — KPI 집계 실패 시 과기한/도태 알림은 계속 생성
            # ★ 2026-08-28: 여기는 원래 `pass` 뿐이었다. KPI 알림이 통째로 유실돼도
            #   로그도 카운터도 없어 **실패 여부 자체를 알 수 없었다.** 잡이 보고하는
            #   `0 errors` 는 이 블록을 포함하지 않는다.
            #   근거: docs/runs/RUNTIME_INTEGRITY_AUDIT_20260828.md §A1-4
            #   격리는 유지한다(과기한·도태 알림은 계속 나가야 한다). 침묵만 없앤다.
            log.exception("create_from_alerts: KPI alert block failed farm=%s", farm_id)

    if not items:
        return 0

    # 멱등: 수신자들의 기존 미읽음 IN_APP 알림 키 집합 선적재
    existing_rows = await db.execute(
        select(
            Notification.id,
            Notification.user_id,
            Notification.alert_type,
            Notification.related_entity_id,
            Notification.severity,
        ).where(
            Notification.user_id.in_(recipients),
            Notification.farm_id == farm_id,  # farm 스코프 — 다농장 소유자의 KPI 알림(관련 엔티티 없음) 충돌 방지
            Notification.type.in_(_INAPP_TYPES),
            Notification.read_at.is_(None),
        )
    )
    # M1: 멱등 키에 severity 포함 — WARNING 미읽음 상태에서 CRITICAL로 승격되면
    # 별개 키가 되어 에스컬레이션 알림이 생성됨(같은 심각도 반복만 억제).
    existing: set = set()
    unread_by_base: dict[tuple, list[tuple]] = {}  # (uid, alert_type, entity) → [(id, severity)]
    for nid, uid_, atype, ent, sev in existing_rows.all():
        existing.add((uid_, atype, ent, sev))
        unread_by_base.setdefault((uid_, atype, ent), []).append((nid, sev))

    now = datetime.now(UTC)
    created = 0
    superseded_ids: list[UUID] = []
    for uid in recipients:
        for it in items:
            sev = it["severity"]
            base = (uid, it["alert_type"], it["related_entity_id"])
            key = (*base, sev)
            if key in existing:
                continue
            db.add(Notification(
                farm_id=farm_id,
                user_id=uid,
                type="IN_APP",
                title=it["title"],
                body=it["body"],
                alert_type=it["alert_type"],
                severity=sev,
                related_entity_type=it["related_entity_type"],
                related_entity_id=it["related_entity_id"],
                sent_at=now,
            ))
            existing.add(key)
            created += 1
            # 승격 시 같은 대상의 '더 낮은 심각도' 미읽음은 읽음 처리(중복 unread 방지, P3).
            new_rank = _SEVERITY_RANK.get(sev, 1)
            for nid, osev in unread_by_base.get(base, []):
                if _SEVERITY_RANK.get(osev, 1) < new_rank:
                    superseded_ids.append(nid)

    if superseded_ids:
        await db.execute(
            update(Notification)
            .where(Notification.id.in_(superseded_ids), Notification.read_at.is_(None))
            .values(read_at=now)
        )
    if created:
        await db.commit()
    return created
