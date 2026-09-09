"""
Integration test fixtures.
- 테스트 DB: pigos_test (Docker postgres 컨테이너 재활용)
- 각 테스트는 별도 트랜잭션 + rollback으로 격리
"""
import os
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from urllib.parse import urlparse, urlunparse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.dependencies import get_db
from app.db.base import Base
from app.db.models import *  # noqa: F401,F403 — registers all models
from app.db.models.platform import Farm, Organization, User
from app.db.models.sow import Sow
from app.main import app


# ── Test DB URL ───────────────────────────────────────────────────────────────
def _make_test_url(url: str) -> str:
    p = urlparse(url)
    return urlunparse(p._replace(path="/pigos_test"))


def _assert_test_database(url: str) -> None:
    database_name = urlparse(url).path.lstrip("/")
    if not database_name.lower().endswith("_test"):
        raise RuntimeError(f"Refusing to reset non-test database: {database_name}")


_ASYNC_TEST_URL = os.getenv("TEST_DATABASE_URL", _make_test_url(settings.database_url))
_SYNC_TEST_URL = _ASYNC_TEST_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")

# sync 엔진 — 테이블 생성 전용 (event loop 없이 session-scoped fixture에서 사용)
_sync_engine = create_engine(_SYNC_TEST_URL, echo=False)

# async 엔진 — 각 테스트 함수에서만 사용, NullPool로 독립 연결
_async_engine = create_async_engine(_ASYNC_TEST_URL, echo=False, future=True, poolclass=NullPool)


@pytest.fixture(autouse=True)
def _approved_publication_set(request, monkeypatch):
    """게시 문서를 승인본으로 두고 테스트한다 — G-3 게이트의 기본 우회.

    `assert_publication_approved` 가 미승인(DRAFT) 상태에서 가입을 451 로 막는다.
    실제 manifest 는 현재 8건 전부 DRAFT 이므로, 이 픽스처가 없으면 계정을 만드는
    통합 테스트가 전부 막힌다(2026-09-09 실측 40건).

    ★ 게이트를 약화시키는 것이 아니다. 게이트는 문서가 승인되면 사라지는 **일시
      상태**이고, 다른 기능의 테스트를 그 상태에 묶어두면 승인 시점에 40건이 다시
      흔들린다. 각 테스트는 자기가 검증하는 것만 전제로 삼는다.

    게이트 자체를 검증하는 파일은 `@pytest.mark.real_publication_set` 로 빠진다.
    (기존 `_allow_kr_signup` autouse 픽스처와 같은 방식이다.)
    """
    if request.node.get_closest_marker("real_publication_set"):
        return
    from app.services import terms_renderer
    from tests.publication_manifest import approved

    raw = terms_renderer._manifest()
    monkeypatch.setattr(terms_renderer, "_manifest", lambda: approved(raw))


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """세션 시작 시 한 번만 테이블 생성 (sync 엔진 사용)."""
    _assert_test_database(_SYNC_TEST_URL)
    with _sync_engine.begin() as conn:
        conn.exec_driver_sql("DROP VIEW IF EXISTS v_sow_npd, v_farm_psy CASCADE")
        conn.exec_driver_sql(
            "DROP FUNCTION IF EXISTS effective_metric_values(VARCHAR, VARCHAR, VARCHAR)"
        )
    Base.metadata.drop_all(_sync_engine)
    Base.metadata.create_all(_sync_engine)
    # KPI 뷰는 마이그레이션으로만 생기고 create_all엔 없음 → get_trend/NPD가 참조하는 v_sow_npd를
    # 테스트에서도 생성해 운영과 동일 스키마로 검증(과거엔 뷰 부재로 get_trend가 미검증이었음).
    with _sync_engine.begin() as conn:
        conn.exec_driver_sql("""
            CREATE OR REPLACE VIEW v_sow_npd AS
            SELECT s.id AS sow_id, s.farm_id, w.id AS weaning_id, w.weaning_date,
                   m_next.mating_date AS next_mating_date,
                   CASE
                       WHEN m_next.mating_date IS NOT NULL THEN LEAST(60, m_next.mating_date - w.weaning_date)
                       WHEN w.weaning_date <= CURRENT_DATE - 60 THEN 60
                       ELSE NULL
                   END AS wei_days
            FROM sows s
            JOIN weanings w ON w.sow_id = s.id AND w.deleted_at IS NULL
            LEFT JOIN LATERAL (
                SELECT m.mating_date FROM matings m
                WHERE m.sow_id = s.id AND m.mating_date > w.weaning_date
                  AND m.mating_date <= (w.weaning_date + INTERVAL '60 days') AND m.deleted_at IS NULL
                ORDER BY m.mating_date LIMIT 1
            ) m_next ON TRUE
        """)  # sow deleted_at 필터 없음(C2): 도태 모돈의 과거 이유 이력도 NPD 포함
        # 벤치마크 해석 함수(마이그레이션 전용) — get_dashboard/_all_benchmarks가 참조. 없으면
        # 대시보드/챗이 테스트에서 미검증이었음 → 운영과 동일 스키마로 생성.
        conn.exec_driver_sql("""
            CREATE OR REPLACE FUNCTION effective_metric_values(
                p_farm_code varchar, p_region_code varchar, p_market_code varchar)
            RETURNS TABLE(metric_code varchar, default_value numeric, benchmark_avg numeric,
                benchmark_top25 numeric, target_value numeric, warning_threshold numeric,
                critical_threshold numeric, alert_direction varchar, unit_code varchar, scope_type varchar)
            LANGUAGE sql STABLE AS $$
                SELECT DISTINCT ON (dmv.metric_code) dmv.metric_code, dmv.default_value,
                    dmv.benchmark_avg, dmv.benchmark_top25, dmv.target_value, dmv.warning_threshold,
                    dmv.critical_threshold, dmv.alert_direction, dmv.unit_code, dmv.scope_type
                FROM default_metric_values dmv
                WHERE (dmv.scope_type='farm' AND dmv.scope_code=p_farm_code)
                   OR (dmv.scope_type='region' AND dmv.scope_code=p_region_code)
                   OR (dmv.scope_type='market' AND dmv.scope_code=p_market_code)
                   OR (dmv.scope_type='system' AND dmv.scope_code='SYSTEM')
                ORDER BY dmv.metric_code, CASE dmv.scope_type WHEN 'farm' THEN 1 WHEN 'region' THEN 2
                    WHEN 'market' THEN 3 WHEN 'system' THEN 4 ELSE 5 END
            $$
        """)
    yield
    _sync_engine.dispose()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    각 테스트마다 독립 트랜잭션.
    서비스의 commit()을 flush()로 대체 후 rollback → DB 격리.
    """
    async with _async_engine.begin() as conn:
        session = AsyncSession(bind=conn, expire_on_commit=False)

        async def mock_commit():
            await session.flush()

        session.commit = mock_commit  # type: ignore[method-assign]

        yield session

        await session.close()
        await conn.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI 테스트 클라이언트 — DB는 테스트 세션으로 오버라이드."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Common entity fixtures ────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_org(db: AsyncSession) -> Organization:
    org = Organization(name="Test Corp", country="KR", timezone="Asia/Seoul")
    db.add(org)
    await db.flush()
    return org


@pytest_asyncio.fixture
async def test_farm(db: AsyncSession, test_org: Organization) -> Farm:
    farm = Farm(
        org_id=test_org.id,
        farm_code=f"TEST-{uuid.uuid4().hex[:6].upper()}",
        name="Test Farm",
        country="KR",
        timezone="Asia/Seoul",
    )
    db.add(farm)
    await db.flush()
    return farm


@pytest_asyncio.fixture
async def test_user(db: AsyncSession, test_org: Organization) -> User:
    from app.core.security import hash_password
    _u = uuid.uuid4().hex[:6]
    user = User(
        org_id=test_org.id,
        username=f"test_{_u}",
        email=f"test-{_u}@pigos.io",
        name="Test User",
        password_hash=hash_password("Test1234!"),
        role="FARM_OWNER",
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def test_sow(db: AsyncSession, test_farm: Farm) -> Sow:
    sow = Sow(
        farm_id=test_farm.id,
        ear_tag=f"SOW-{uuid.uuid4().hex[:6].upper()}",
        parity=0,
        status="GILT",
        # 과거 고정 날짜 — date_rules validator(이벤트일 ≥ 입식일)와 충돌 방지
        entry_date=datetime(2024, 1, 1, tzinfo=UTC),
        entry_type="GILT",
    )
    db.add(sow)
    await db.flush()
    return sow
