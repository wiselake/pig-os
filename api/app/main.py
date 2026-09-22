"""
PigOS API — FastAPI entry point.

Architecture:
  Base routers  → always mounted
  Addon routers → discovered from AddonRegistry at startup

To add a new Addon:
  1. Create app/addons/<name>/ package with AddonRegistry.register() call
  2. Import it in app/routers/addons/__init__.py
  3. Restart → router appears automatically at /addons/<url_prefix>/
"""
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.addons import AddonRegistry
from app.core import cache, client_version
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db import keepalive
from app.routers.base import (
    alerts,
    analytics,
    auth,
    boars,
    chat,
    config,
    consent,
    devices,
    events,
    farms,
    feed,
    finishers,
    kpi,
    members,
    notifications,
    onboarding,
    ops,
    orgs,
    piglets,
    pilot_signups,
    reports,
    scorecard,
    sows,
    sync,
    tasks,
    thresholds,
)
from app.services import public_notice

# ── Import Addon packages here to trigger AddonRegistry.register() ──────────
# from app.addons import fcr      # uncomment when Addon #1 is ready
# from app.addons import health   # Addon #2
# from app.addons import market   # Addon #4
# from app.addons import breeding # Addon #5
# from app.addons import biosec   # Addon #6
# ────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    addons = AddonRegistry.all()
    print(f"[PigOS] {len(addons)} Addon(s) registered: {[a.code for a in addons]}")
    # 풀러가 유휴 커넥션을 끊어 재수립에 수 초가 걸리는 스파이크를 막는다(2026-08-25).
    keepalive.start()
    try:
        yield
    finally:
        await keepalive.stop()


app = FastAPI(
    title="PigOS API",
    version="0.1.0",
    description="Global Swine Farm Management — Base API + AI Addon platform",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 캐시 무효화 ───────────────────────────────────────────────────────────────
# 대시보드는 짧은 TTL 캐시를 쓴다(app/core/cache.py). 이벤트를 입력했는데 옛 숫자가
# 남아 보이면 사용자가 "입력이 안 됐다"고 판단하므로 쓰기 직후 즉시 무효화한다.
#
# ★ 라우터마다 무효화를 넣지 않고 미들웨어 한 곳에서 처리한다 — 쓰기 엔드포인트가
#   수십 개라 개별 처리하면 반드시 누락이 생기고, 누락은 "가끔 안 바뀐다"로 나타나
#   재현·추적이 어렵다.
_FARM_PATH = re.compile(r"/farms/([0-9a-fA-F-]{36})")


@app.middleware("http")
async def _invalidate_farm_cache(request: Request, call_next):
    response = await call_next(request)
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and response.status_code < 400:
        m = _FARM_PATH.search(request.url.path)
        if m:
            await cache.invalidate_farm(m.group(1))
    return response


# ── 클라이언트 버전 관측 ──────────────────────────────────────────────────────
# ★ 관측만 한다. 차단·분기·거부를 하지 않는다.
#   지금 세 surface 중 헤더를 보내는 곳이 하나도 없다(2026-08-28 실측).
#   여기서 fail-closed 를 켜면 정상 클라이언트가 전부 막힌다.
#   활성화 순서: Web→Android→iOS 송출 → 서버 관측 확인 → 그 다음에야 강제.
#   상세: app/core/client_version.py · HANDOFF §12-1


@app.middleware("http")
async def _observe_client_version(request: Request, call_next):
    request.state.client_version = client_version.parse(request.headers)
    return await call_next(request)


# ── Exception handlers ────────────────────────────────────────────────────────
register_exception_handlers(app)

V1 = "/api/v1"

# ── Public routers (no auth) ─────────────────────────────────────────────────
app.include_router(pilot_signups.router, prefix=V1)
app.include_router(scorecard.router, prefix=V1)

# ── 서비스-투-서비스 연동 (자체 서비스토큰 가드) ──────────────────────────────
from app.routers.integrations import qbridge as qbridge_integration  # noqa: E402

app.include_router(qbridge_integration.router, prefix=V1)

# ── Base routers ─────────────────────────────────────────────────────────────
# ★ 운영 상태는 V1 prefix 밖이다 — /health 와 나란히 둔다.
#   모니터링이 API 버전에 묶이면 버전을 올릴 때 감시가 끊긴다.
app.include_router(ops.router)

app.include_router(auth.router,        prefix=V1)
app.include_router(orgs.router,        prefix=V1)
app.include_router(onboarding.router,  prefix=V1)
app.include_router(config.router,      prefix=V1)
app.include_router(consent.router,     prefix=V1)
app.include_router(farms.router,       prefix=V1)
app.include_router(sows.router,        prefix=V1)
app.include_router(events.router,      prefix=V1)
app.include_router(kpi.router,         prefix=V1)
app.include_router(chat.router,        prefix=V1)
app.include_router(sync.router,        prefix=V1)
app.include_router(finishers.router,   prefix=V1)
app.include_router(feed.router,        prefix=V1)
app.include_router(piglets.router,     prefix=V1)
app.include_router(boars.router,       prefix=V1)
app.include_router(alerts.router,      prefix=V1)
app.include_router(tasks.router,       prefix=V1)
app.include_router(thresholds.router,  prefix=V1)
app.include_router(notifications.router, prefix=V1)
app.include_router(notifications.farm_router, prefix=V1)
app.include_router(devices.router,     prefix=V1)
app.include_router(reports.router,     prefix=V1)
app.include_router(analytics.router,   prefix=V1)
app.include_router(members.router,     prefix=V1)

# ── Admin console (SUPER_ADMIN 전용, 전사 스코프) ─────────────────────────────
from app.routers.admin import audit_router as admin_audit_router  # noqa: E402
from app.routers.admin import benchmarks_router as admin_benchmarks_router  # noqa: E402
from app.routers.admin import content_router as admin_content_router  # noqa: E402
from app.routers.admin import core_router as admin_core_router  # noqa: E402
from app.routers.admin import master_data_router as admin_master_data_router  # noqa: E402
from app.routers.admin import orgs_router as admin_orgs_router  # noqa: E402
from app.routers.admin import rules_router as admin_rules_router  # noqa: E402
from app.routers.admin import users_router as admin_users_router  # noqa: E402
from app.routers.base import announcements as base_announcements  # noqa: E402
from app.routers.base import support as base_support  # noqa: E402

app.include_router(admin_core_router,   prefix=V1)
app.include_router(admin_users_router,  prefix=V1)
app.include_router(admin_content_router, prefix=V1)
app.include_router(admin_rules_router,  prefix=V1)
app.include_router(admin_audit_router,  prefix=V1)
app.include_router(admin_orgs_router,   prefix=V1)
app.include_router(admin_benchmarks_router, prefix=V1)
app.include_router(admin_master_data_router, prefix=V1)
app.include_router(base_announcements.router, prefix=V1)
app.include_router(base_support.router, prefix=V1)

# ── Addon routers (auto-discovered from AddonRegistry) ───────────────────────
for addon in AddonRegistry.all():
    app.include_router(
        addon.router,
        prefix=f"{V1}/addons/{addon.url_prefix}",
        tags=addon.tags or [f"Addon: {addon.name}"],
    )


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "version": app.version}


# ── 공개 개인정보 처리방침 ────────────────────────────────────────────────────
# App Store Connect 의 방침 URL(필수 입력값)이 여기를 가리킨다.
#
# ★ 2026-08-26: 손으로 쓴 정적 HTML(app/static/privacy.html, 2026-06-29 자)을 서빙하다
#   정본과 어긋났다 — 대표 개인 메일 노출·쓰지 않는 FCM 기재·상호 오기·보호책임자 누락.
#   심사자가 앱 문구와 대조 가능한 부분이라 위험했다.
#   지금은 **정본 마크다운을 렌더링**한다. 손으로 쓴 HTML 을 다시 두지 않는다.
@app.get("/legal/privacy", response_class=HTMLResponse, include_in_schema=False)
async def privacy_notice(request: Request, lang: str | None = None):
    chosen = public_notice.normalize_lang(lang or request.headers.get("accept-language"))
    return HTMLResponse(public_notice.render(chosen))
