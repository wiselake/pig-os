"""운영 상태 — `/health` 가 답하지 못하는 것을 답한다.

## 왜 별도 엔드포인트인가

```
/health            프로세스가 살아 있는가          — Docker healthcheck 가 쓴다. 건드리지 않는다
/health/ready      의존성이 붙어 있는가            — DB · Redis
/health/ops        운영상 건강한가                 — ★ 배경 잡이 실제로 일하고 있는가
```

★ **"프로세스가 살아 있다" 와 "운영상 건강하다" 는 다르다.** 이 프로젝트는 그 차이로
넉 달을 잃었다 — `kpi_snapshots` 가 2026-05-29 이래 0행인데 `/health` 는 내내 `ok` 였고
ARQ 도 성공으로 기록했다(`RUNTIME_INTEGRITY_AUDIT_20260828`). 프로세스는 건강했다.
서비스는 아니었다.

## 무엇을 하지 않는가

외부 SaaS 를 붙이지 않는다(Sentry·OTel·Prometheus 전부 미도입). 새 의존성·계약 없이
**이미 DB 에 있는 사실**만 읽어 보여준다. 관측 플랫폼을 짓는 것이 목적이 아니라,
"장애인데 성공이라고 말하는 상태" 를 없애는 것이 목적이다.

## 판정 규칙

```
ok        의존성 정상 + 잡 신선도 정상
degraded  일부 실패 — 서비스는 응답하지만 뭔가 밀려 있다
down      DB 불가 — 아무것도 못 한다
```

★ HTTP status 는 항상 200 이다. 모니터가 본문을 읽게 한다 — 상태코드로 degraded 를
표현하면 로드밸런서가 인스턴스를 빼버려 오히려 장애가 커진다.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import text

from app.core.dependencies import DbDep

log = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["System"])

# 잡 신선도 기준. 일간 잡이므로 하루를 넘겨 밀리면 문제다.
# ★ 값을 여기 하나에만 둔다 — 여러 곳에 흩어지면 조용히 갈라진다.
_SNAPSHOT_STALE_AFTER = timedelta(hours=36)


async def _check_db(db) -> dict:
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:  # noqa: BLE001 — 진단용이므로 예외 종류를 가리지 않는다
        log.error("health/ops: db 확인 실패 — %s", e)
        return {"status": "down", "error": type(e).__name__}


async def _check_redis() -> dict:
    from app.core import cache

    client = cache._get()
    if client is None:
        # 캐시는 없어도 서비스가 돈다(요청 시 계산). 그래서 down 이 아니라 degraded.
        return {"status": "degraded", "detail": "redis unavailable — 캐시 없이 동작 중"}
    try:
        await client.ping()
        return {"status": "ok"}
    except Exception as e:  # noqa: BLE001
        return {"status": "degraded", "error": type(e).__name__}


async def _check_snapshots(db) -> dict:
    """★ 이 프로젝트가 실제로 겪은 침묵 장애를 보이게 한다.

    잡이 "성공" 으로 끝나도 스냅샷이 안 쌓이면 여기서 드러난다 — 잡의 자기보고가 아니라
    **결과물**을 본다. 자기보고를 믿었기 때문에 넉 달이 걸렸다.
    """
    try:
        row = (await db.execute(text(
            "SELECT count(*) AS n, max(created_at) AS latest FROM kpi_snapshots"
        ))).one()
    except Exception as e:  # noqa: BLE001
        return {"status": "unknown", "error": type(e).__name__}

    total = int(row.n or 0)
    latest = row.latest
    if total == 0:
        return {
            "status": "degraded",
            "rows": 0,
            "detail": (
                "kpi_snapshots 가 비어 있다 — 집계 잡이 한 번도 성공적으로 영속하지 못했다. "
                "대시보드는 요청 시 계산으로 동작하므로 사용자에게는 보이지 않는다"
            ),
        }

    age = datetime.now(UTC) - (latest if latest.tzinfo else latest.replace(tzinfo=UTC))
    stale = age > _SNAPSHOT_STALE_AFTER
    return {
        "status": "degraded" if stale else "ok",
        "rows": total,
        "latest_age_hours": round(age.total_seconds() / 3600, 1),
        **({"detail": f"최신 스냅샷이 {_SNAPSHOT_STALE_AFTER} 보다 오래됐다"} if stale else {}),
    }


def _roll_up(checks: dict) -> str:
    statuses = {c.get("status") for c in checks.values()}
    if "down" in statuses:
        return "down"
    if "degraded" in statuses or "unknown" in statuses:
        return "degraded"
    return "ok"


@router.get("/ready", include_in_schema=False)
async def readiness(db: DbDep) -> dict:
    """의존성만 본다 — 배포 직후 트래픽을 받아도 되는가."""
    checks = {"database": await _check_db(db), "redis": await _check_redis()}
    return {"status": _roll_up(checks), "checks": checks}


@router.get("/ops", include_in_schema=False)
async def operational_health(db: DbDep) -> dict:
    """운영 상태 — 사람이 아침에 한 번 보면 되는 화면.

    ★ status 가 ok 여도 배포 가능하다는 뜻은 아니고, degraded 라고 장애도 아니다.
      이것은 **판정이 아니라 사실**이다. 판정 규칙을 여기 넣으면 그 규칙이 또 다른
      단일 출처가 된다.
    """
    from app.core.config import settings

    checks = {
        "database": await _check_db(db),
        "redis": await _check_redis(),
        "kpi_snapshots": await _check_snapshots(db),
    }
    return {
        "status": _roll_up(checks),
        "checked_at": datetime.now(UTC).isoformat(),
        "environment": settings.environment,
        "checks": checks,
    }
