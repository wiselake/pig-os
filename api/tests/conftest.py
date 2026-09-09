"""
공통 fixtures — unit/integration 양쪽에서 사용.
Integration DB fixture는 tests/integration/conftest.py에 분리.

PREFLIGHT(§0-1)도 여기서 건다 — 아래 pytest_collection_modifyitems 참조.
"""
import os
from urllib.parse import urlparse, urlunparse

import pytest

from app.core.config import settings

# ── PREFLIGHT: DB 환경 검사 ───────────────────────────────────────────────────
# 환경이 틀린 것과 코드가 틀린 것은 다른 사건이다.
#
# 2026-09-08 실측: Docker Desktop 이 죽은 상태로 전량 실행 → 663 ERROR.
# 컨테이너를 살리고 재측정하니 1414 passed 였다. 코드 회귀가 0인데도 RUN 의
# STOP-on-FAIL 게이트는 터진다. 그 오탐을 막는 것이 이 훅의 목적이다.
#
# ★ skip 하지 않는다. 조용히 0건 통과하는 구멍이 되기 때문이다
#   (이모지 가드가 9개 파일만 보면서 통과하던 것과 같은 실패 방식).
#   대신 종료 코드 78 로 즉시 끝낸다 — pytest 자신의 코드(0~5)와 겹치지 않는다.

EXIT_ENVIRONMENT_INVALID = 78
NL = chr(10)   # heredoc 이 백슬래시를 먹는 환경 — 이스케이프 대신 코드포인트로 적는다


def _sync_test_url() -> str:
    """integration/conftest.py 와 같은 대상. 그쪽이 실제로 붙을 URL 을 그대로 검사한다."""
    async_url = os.getenv(
        "TEST_DATABASE_URL",
        urlunparse(urlparse(settings.database_url)._replace(path="/pigos_test")),
    )
    return async_url.replace("postgresql+asyncpg", "postgresql+psycopg2")


def pytest_collection_modifyitems(config, items):
    """integration 테스트가 수집됐을 때만 DB 를 검사한다.

    unit 만 돌릴 때는 DB 가 없어도 정상이므로 막지 않는다 — 필요 없는 의존성을
    강제하면 그 자체가 새로운 오탐이 된다.
    """
    needs_db = any("integration" in item.nodeid.replace("\\", "/").split("/") for item in items)
    if not needs_db:
        return

    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    url = _sync_test_url()
    try:
        engine = create_engine(url, poolclass=NullPool, connect_args={"connect_timeout": 3})
        with engine.connect():
            pass
    except Exception as exc:  # noqa: BLE001 — 원인을 그대로 보여주는 것이 목적이다
        host = urlparse(url).netloc.rsplit("@", 1)[-1]  # 자격증명 노출 금지
        pytest.exit(
            "ENVIRONMENT_INVALID: test database unreachable at "
            f"{host}/{urlparse(url).path.lstrip('/')}" + NL
            + f"  actual: {type(exc).__name__}: {str(exc).splitlines()[0][:120]}" + NL
            + "  expected: pigos-postgres container Running" + NL
            + "  fix: docker start pigos-postgres pigos-redis",
            returncode=EXIT_ENVIRONMENT_INVALID,
        )


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _allow_kr_signup(monkeypatch):
    """테스트/개발 환경 = 대표 확인용으로 KR 가입 허용(운영 기본 차단).
    KR을 기본 법역으로 쓰는 consent 테스트가 signup_blocked(451)로 깨지지 않도록.
    KR 차단 자체 검증은 jurisdiction.resolve 순수 레벨에서 별도로 한다."""
    monkeypatch.setattr(settings, "allow_kr_signup", True)
