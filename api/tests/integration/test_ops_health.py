"""운영 상태 엔드포인트 — "프로세스 생존" 과 "운영상 건강" 을 섞지 않는다.

이 프로젝트가 실제로 겪은 것: `kpi_snapshots` 0행이 넉 달간 이어지는 동안 `/health` 는
계속 `ok` 였다(`RUNTIME_INTEGRITY_AUDIT_20260828`). 프로세스는 건강했고 서비스는 아니었다.
그 구분을 테스트로 고정한다.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_liveness_still_answers_the_old_contract(client: AsyncClient):
    """★ `/health` 는 바꾸지 않았다 — Docker healthcheck·e2e 헬퍼가 이 모양을 쓴다.

    관측을 붙이면서 기존 헬스체크 계약을 바꾸면 배포가 깨진다.
    """
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


async def test_readiness_reports_each_dependency(client: AsyncClient):
    r = await client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert set(body["checks"]) == {"database", "redis"}
    assert body["checks"]["database"]["status"] == "ok"
    assert body["status"] in {"ok", "degraded"}


async def test_ops_surfaces_job_output_not_job_self_report(client: AsyncClient):
    """★ 잡이 뭐라고 말했는지가 아니라 **결과물**을 본다.

    잡의 자기보고를 믿었기 때문에 0행 상태를 넉 달간 못 봤다.
    """
    r = await client.get("/health/ops")
    assert r.status_code == 200
    body = r.json()
    snap = body["checks"]["kpi_snapshots"]
    assert "rows" in snap or "error" in snap
    # 테스트 DB 는 비어 있으므로 0행 → degraded 로 보여야 한다. 이것이 핵심 동작이다.
    if snap.get("rows") == 0:
        assert snap["status"] == "degraded"
        assert body["status"] == "degraded"


async def test_degraded_still_returns_200(client: AsyncClient):
    """★ degraded 를 상태코드로 표현하지 않는다.

    비 200 을 내면 로드밸런서가 인스턴스를 빼고, 밀린 잡 하나 때문에 서비스가 죽는다.
    모니터가 본문을 읽게 한다.
    """
    r = await client.get("/health/ops")
    assert r.status_code == 200, "degraded 를 HTTP 오류로 표현하면 안 된다"


async def test_ops_never_leaks_credentials_or_internals(client: AsyncClient):
    """진단 응답에 비밀이 섞이면 공개 모니터링에 못 쓴다."""
    text = (await client.get("/health/ops")).text.lower()
    for forbidden in ("password", "secret", "postgresql://", "redis://", "token", "@"):
        assert forbidden not in text, f"운영 응답에 {forbidden!r} 이 보인다"


async def test_ops_is_not_versioned(client: AsyncClient):
    """API 버전을 올려도 감시가 끊기지 않게 — /api/v1 아래에 두지 않는다."""
    assert (await client.get("/api/v1/health/ops")).status_code == 404
    assert (await client.get("/health/ops")).status_code == 200
