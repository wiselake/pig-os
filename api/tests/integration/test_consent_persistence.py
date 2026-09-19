"""LEGAL-P0-CONSENT-LEDGER-PERSISTENCE — 요청이 끝난 뒤에도 남는가.

## 왜 별도 파일인가

공용 `db` fixture 는 테스트 격리를 위해 **commit 을 flush 로 바꿔 끼운다**
(`conftest.py:114`).

    async def mock_commit():
        await session.flush()
    session.commit = mock_commit

그래서 커밋 누락이 flush 와 구분되지 않고, 원장 조회도 같은 트랜잭션 안에서
이뤄진다. 통합 테스트 1389건이 전부 통과하면서도 "정말 저장됐는가"는 그 스위트가
**원리적으로** 답할 수 없는 질문이다. `/consent/record` 가 200 을 주고 rollback
되는 상태가 그렇게 오래 살아남았다.

★ 검증 대상인 commit 을 테스트 코드가 무력화하면 안 된다.

그 fixture 자체는 격리 설계로서 합리적이므로 전역에서 제거하지 않는다. 대신
이 파일만 별도 경로를 쓴다.

    공용 경로        commit→flush 오버라이드, 트랜잭션 rollback (격리)
    이 파일          오버라이드 없음. 앱이 프로덕션과 같은 형태로 세션을 열고,
                     **요청이 끝난 뒤 완전히 새로운 세션**으로 확인한다

## 이 파일이 증명하는 것

    record   2xx → 요청 세션 종료 → fresh session → row 존재
    withdraw 2xx → fresh session → 철회 상태 존재
    실패     commit 실패 → 2xx 금지 → fresh session 에 부분 기록 없음

요청 세션과 확인 세션이 다르다는 점이 핵심이다. 같은 세션에서 읽으면 커밋하지
않아도 보인다 — 그것이 지금까지의 착시였다.
"""
from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from urllib.parse import urlparse, urlunparse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.dependencies import get_db
from app.db.models.consent import ConsentRecord
from app.main import app

pytestmark = pytest.mark.anyio

PW = "Test1234!"
CONSENT = "/api/v1/consent"


def _test_url() -> str:
    """공용 conftest 와 같은 규칙으로 테스트 DB URL 을 만든다."""
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        p = urlparse(settings.database_url)
        url = urlunparse(p._replace(path="/pigos_test"))
    if not urlparse(url).path.lstrip("/").lower().endswith("_test"):
        raise RuntimeError("persistence 테스트는 *_test DB 에서만 돈다")
    return url


_engine = create_async_engine(_test_url(), echo=False, future=True, poolclass=NullPool)


class _Harness:
    """실제 커밋이 일어나는 요청 클라이언트 + 별도 확인 세션."""

    def __init__(self) -> None:
        self.client: AsyncClient = None  # type: ignore[assignment]
        self.user_ids: list[uuid.UUID] = []
        # 요청 시점에 읽는다 — 같은 harness 로 정상 setup 후 실패로 전환할 수 있다.
        self.fail_commit = False

    async def signup(self, country: str = "US") -> tuple[str, str]:
        tag = uuid.uuid4().hex[:8]
        r = await self.client.post("/api/v1/onboarding/complete", json={
            "name": "P", "username": f"p{tag}", "email": f"p{tag}@example.com",
            "password": PW, "org_name": f"Org {tag}", "country": country,
            "language": "en", "farm_name": f"Farm {tag}", "farm_type": "FARROW_TO_FINISH",
        })
        assert r.status_code == 201, r.text
        self.user_ids.append(uuid.UUID(r.json()["user_id"]))
        return r.json()["access_token"], r.json()["farm_id"]

    async def fresh_session(self) -> AsyncSession:
        """★ 요청과 무관한, 완전히 새로운 세션.

        요청이 쓴 트랜잭션이 커밋됐을 때만 여기서 보인다."""
        return AsyncSession(_engine, expire_on_commit=False)

    async def ledger_rows(self, farm_id: str) -> int:
        async with await self.fresh_session() as s:
            return await s.scalar(
                select(func.count()).select_from(ConsentRecord)
                .where(ConsentRecord.farm_id == uuid.UUID(farm_id))
            )


def _body(farm_id: str, *, country="US", terms=True, privacy=True, choices=None) -> dict:
    return {
        "farm_id": farm_id, "selected_country": country, "farm_country": country,
        "lang": "en", "terms_ack": terms, "privacy_ack": privacy,
        "choices": choices or [], "collection_context": "UI_SIGNUP",
    }


async def _cleanup(user_ids: list[uuid.UUID]) -> None:
    """이 파일은 실제로 커밋하므로 자기가 만든 것을 지운다.

    (세션 시작 시 drop_all/create_all 이 돌긴 하지만, 같은 실행 안에서 다른
    테스트에 영향을 주지 않도록 원장 행만이라도 정리한다.)"""
    if not user_ids:
        return
    async with AsyncSession(_engine) as s:
        await s.execute(
            text("DELETE FROM consent_ledger WHERE user_id = ANY(:ids)"),
            {"ids": user_ids},
        )
        await s.commit()


@pytest_asyncio.fixture
async def hx() -> AsyncGenerator[_Harness, None]:
    """앱이 프로덕션과 **같은 형태**로 세션을 여는 클라이언트.

    `get_db` 원본과 동일하게 `async with AsyncSession(...)` 로 열고 커밋하지
    않는다 — 다른 점은 엔진이 테스트 DB 를 가리키는 것뿐이다. commit 은
    가로채지 않는다(`fail_commit` 을 켠 요청만 의도적으로 실패시킨다).

    ★ harness 를 하나만 쓴다. 예전에는 setup 용과 실패용 fixture 를 나눴는데,
      먼저 닫히는 쪽의 `dependency_overrides.clear()` 가 다른 쪽 override 까지
      지워 요청이 운영 DB 로 새어나갔다(401 로 드러났다)."""
    h = _Harness()

    async def real_get_db():
        async with AsyncSession(_engine, expire_on_commit=False, autoflush=False) as session:
            if h.fail_commit:
                async def boom():
                    raise RuntimeError("simulated commit failure")
                session.commit = boom       # type: ignore[method-assign]
            yield session

    app.dependency_overrides[get_db] = real_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        h.client = c
        try:
            yield h
        finally:
            app.dependency_overrides.clear()
            h.fail_commit = False
            await _cleanup(h.user_ids)


# ── 1. record — 요청이 끝난 뒤에도 남는가 ───────────────────────────────────

async def test_record_persists_after_the_request_ends(hx: _Harness):
    """★ 이 P0 의 핵심.

    같은 세션에서 읽으면 커밋 없이도 보인다. 그래서 **다른 세션**에서 읽는다."""
    token, farm_id = await hx.signup()
    assert await hx.ledger_rows(farm_id) == 0

    r = await hx.client.post(f"{CONSENT}/record", json=_body(farm_id),
                             headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert len(r.json()) > 0

    assert await hx.ledger_rows(farm_id) > 0, (
        "200 을 받았지만 새 세션에서는 원장이 비어 있다 — 요청 종료 시 rollback 됐다"
    )


async def test_withdraw_persists_after_the_request_ends(hx: _Harness):
    token, farm_id = await hx.signup()
    auth = {"Authorization": f"Bearer {token}"}
    r = await hx.client.post(f"{CONSENT}/record", json=_body(farm_id, choices=[
        {"purpose_code": "AI_MODEL_TRAINING", "granted": True},
    ]), headers=auth)
    assert r.status_code == 200, r.text

    w = await hx.client.post(f"{CONSENT}/withdraw", json={
        "purpose_code": "AI_MODEL_TRAINING", "action": "WITHDRAWN",
        "farm_id": farm_id, "reason": "persistence test",
    }, headers=auth)
    assert w.status_code == 200, w.text

    async with await hx.fresh_session() as s:
        latest = (await s.execute(
            select(ConsentRecord)
            .where(ConsentRecord.farm_id == uuid.UUID(farm_id),
                   ConsentRecord.purpose_code == "AI_MODEL_TRAINING")
            .order_by(ConsentRecord.created_at.desc()).limit(1)
        )).scalars().first()
    assert latest is not None, "철회 요청은 200 인데 새 세션에 아무 행도 없다"
    assert latest.consent_status == "WITHDRAWN", (
        f"새 세션에서 본 최신 상태가 {latest.consent_status} 다 — 철회가 저장되지 않았다"
    )


# ── 2. 거부 경로 — 부분 기록이 남지 않는가 ──────────────────────────────────

async def test_rejected_record_leaves_nothing_in_a_fresh_session(hx: _Harness):
    """422(필수 동의 미체크)는 어떤 행도 남기지 않는다."""
    token, farm_id = await hx.signup()
    r = await hx.client.post(f"{CONSENT}/record", json=_body(farm_id, terms=False),
                             headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422, r.text
    assert await hx.ledger_rows(farm_id) == 0


async def test_foreign_farm_record_leaves_nothing_in_a_fresh_session(hx: _Harness):
    """403(농장 권한)도 마찬가지 — FARM-AUTHORITY 를 실제 커밋 환경에서 재확인한다."""
    _t1, farm_a = await hx.signup()
    token_b, _farm_b = await hx.signup()
    r = await hx.client.post(f"{CONSENT}/record", json=_body(farm_a),
                             headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code == 403, r.text
    assert await hx.ledger_rows(farm_a) == 0


# ── 3. commit 실패 — 성공을 반환하면 안 된다 ────────────────────────────────

async def test_commit_failure_must_not_report_success(hx: _Harness):
    """★ 진짜 fail-closed 의 조건.

    커밋이 실패했는데 2xx 를 주면 클라이언트는 저장됐다고 믿는다. 웹의
    fail-closed(e064e60)가 정확히 그 200 을 로그인 확정 조건으로 쓴다.

    ※ signup 자체는 커밋돼야 하므로 먼저 정상으로 계정을 만든 뒤 커밋을
      실패로 전환한다."""
    token, farm_id = await hx.signup()

    hx.fail_commit = True
    r = await hx.client.post(
        f"{CONSENT}/record", json=_body(farm_id),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code >= 500, (
        f"커밋이 실패했는데 {r.status_code} 를 반환했다 — 클라이언트는 저장됐다고 믿는다"
    )

    async with AsyncSession(_engine) as s:
        rows = await s.scalar(
            select(func.count()).select_from(ConsentRecord)
            .where(ConsentRecord.farm_id == uuid.UUID(farm_id))
        )
    assert rows == 0, f"커밋 실패인데 {rows} 행이 남았다"
