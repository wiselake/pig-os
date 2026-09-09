"""G-3 — 미승인(DRAFT) 문서 상태에서는 동의를 받지 않는다.

## 왜 이 파일이 있나

`any_draft` 는 2026-09-09 이전에도 계산되고 있었다. 소비처가 **프론트 배너 하나**
였을 뿐이다(`ConsentForm.tsx:71`). 즉 초안 상태에서 사용자가 체크하고 가입할 수
있었고, `consent_ledger.notice_version` 에는 초안 버전이 그대로 적혔다.

배포 대기 중인 두 수정이 그 경로를 **강화한다.**

    557a347   동의 원장을 commit → 지금까지 0행이던 기록이 실제로 남는다
    e064e60   동의 기록 실패 시 가입 차단 → 기록 없는 가입이 사라진다

둘 다 옳은 수정인데, 게시 정본이 잘못된 상태에서는 **증거 능력만 올린다.**
없는 기록은 공백이지만, 있는 기록은 회사가 승인하지 않은 문서에 동의를 받았다는
적극적 기록이다. 그래서 게이트가 배포보다 먼저다
(`docs/legal/DEPLOY_GATE_20260910.md` §7 — 대표 결정 (나)).

## 이 파일이 잠그는 것

    negative   현재 manifest(8건 전부 DRAFT)에서 가입·동의가 실제로 실패하는가
    positive   승인본에서는 통과하는가          ← 게이트가 항상 막기만 하면 무의미하다
    authority  프론트가 아니라 **백엔드**가 막는가
    ★ 철회는 승인 여부와 무관하게 계속 가능한가

★ positive 대조군이 없으면 이 테스트는 "가입이 안 된다"만 증명한다. 그건 게이트가
  옳다는 증거가 아니라 서비스가 죽었다는 증거일 수도 있다.
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.consent import ConsentRecord
from tests.publication_manifest import approved as _approved_manifest

# ★ 이 파일만 실제 manifest(현재 전부 DRAFT)를 쓴다.
#   integration/conftest.py 의 autouse 픽스처가 기본으로 승인본을 깔아두기 때문에,
#   그것을 끄지 않으면 negative 테스트가 통과할 수 없다.
pytestmark = [pytest.mark.anyio, pytest.mark.real_publication_set]

PW = "Test1234!"


@pytest.fixture
def approved_docs(monkeypatch):
    """manifest 를 승인본으로 갈아끼운다. `_manifest` 는 lru_cache 라 함수째 교체한다."""
    from app.services import terms_renderer

    raw = terms_renderer._manifest()
    monkeypatch.setattr(terms_renderer, "_manifest", lambda: _approved_manifest(raw))
    yield


async def _signup(client: AsyncClient, country: str = "US") -> tuple[str, str]:
    tag = uuid.uuid4().hex[:8]
    r = await client.post("/api/v1/onboarding/complete", json={
        "name": "Gate", "username": f"g{tag}", "email": f"g{tag}@example.com",
        "password": PW, "org_name": f"Org {tag}", "country": country, "language": "en",
        "farm_name": f"Farm {tag}", "farm_type": "FARROW_TO_FINISH",
    })
    assert r.status_code == 201, r.text
    return r.json()["access_token"], r.json()["farm_id"]


# ── negative — 현재 상태(전 문서 DRAFT) ─────────────────────────────────────

async def test_manifest_is_still_draft() -> None:
    """전제 고정. 문서가 승인되면 이 테스트가 먼저 깨져서 알려준다."""
    from app.services import terms_renderer

    docs = terms_renderer._manifest().get("documents", {})
    statuses = {d.get("status") for d in docs.values() if isinstance(d, dict)}
    assert statuses and all(s.startswith("DRAFT") for s in statuses), (
        f"manifest 가 더 이상 전부 DRAFT 가 아니다: {statuses} — G-1 이 충족됐다면 "
        "이 테스트와 아래 negative 들을 승인 상태 기준으로 다시 쓴다"
    )


async def test_onboarding_is_blocked_while_documents_are_draft(client: AsyncClient) -> None:
    """★ 계정이 만들어지기 전에 막힌다.

    consent 단계에서만 막으면 계정은 이미 생기고 동의만 실패한다 — 가입이 멈추는
    게 아니라 고아 계정이 쌓인다(H11).
    """
    tag = uuid.uuid4().hex[:8]
    r = await client.post("/api/v1/onboarding/complete", json={
        "name": "Blocked", "username": f"b{tag}", "email": f"b{tag}@example.com",
        "password": PW, "org_name": f"Org {tag}", "country": "US", "language": "en",
        "farm_name": f"Farm {tag}", "farm_type": "FARROW_TO_FINISH",
    })
    assert r.status_code == 451, r.text
    assert "PUBLICATION_NOT_APPROVED" in r.text


async def test_register_is_blocked_while_documents_are_draft(client: AsyncClient) -> None:
    """가입 진입점은 둘이다. 하나만 막으면 다른 쪽으로 그대로 들어온다."""
    tag = uuid.uuid4().hex[:8]
    r = await client.post("/api/v1/auth/register", json={
        "name": "Blocked", "username": f"r{tag}", "email": f"r{tag}@example.com",
        "password": PW, "org_name": f"Org {tag}", "country": "US", "language": "en",
    })
    assert r.status_code == 451, r.text
    assert "PUBLICATION_NOT_APPROVED" in r.text


async def test_no_account_is_created_when_blocked(client: AsyncClient, db: AsyncSession) -> None:
    """451 을 던진 뒤 rollback 에 기대지 않는다 — 애초에 쓰지 않는다."""
    from app.db.models.platform import User

    tag = uuid.uuid4().hex[:8]
    await client.post("/api/v1/onboarding/complete", json={
        "name": "Blocked", "username": f"n{tag}", "email": f"n{tag}@example.com",
        "password": PW, "org_name": f"Org {tag}", "country": "US", "language": "en",
        "farm_name": f"Farm {tag}", "farm_type": "FARROW_TO_FINISH",
    })
    n = await db.scalar(select(func.count()).select_from(User).where(User.username == f"n{tag}"))
    assert n == 0, "차단됐는데 계정이 남았다 — 고아 계정 경로가 열려 있다"


# ── positive — 승인본에서는 통과한다 ────────────────────────────────────────

async def test_onboarding_succeeds_when_documents_are_approved(
    client: AsyncClient, approved_docs,
) -> None:
    """★ 대조군. 게이트가 status 하나로 열려야 한다."""
    token, farm_id = await _signup(client)
    assert token and farm_id


async def test_consent_record_succeeds_when_documents_are_approved(
    client: AsyncClient, db: AsyncSession, approved_docs,
) -> None:
    """승인본에서는 원장에 실제로 기록된다."""
    token, farm_id = await _signup(client)
    r = await client.post(
        "/api/v1/consent/record",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "selected_country": "US", "farm_country": "US", "farm_id": farm_id,
            "lang": "en", "terms_ack": True, "privacy_ack": True,
            "choices": [], "collection_context": "UI_SIGNUP",
        },
    )
    assert r.status_code == 200, r.text
    n = await db.scalar(
        select(func.count()).select_from(ConsentRecord).where(ConsentRecord.farm_id == farm_id)
    )
    assert n and n > 0, "승인본인데 원장에 아무것도 남지 않았다"


# ── 백엔드가 authoritative 인가 ─────────────────────────────────────────────

async def test_consent_record_is_blocked_by_the_service_not_the_form(
    client: AsyncClient, db: AsyncSession, monkeypatch,
) -> None:
    """★ 프론트 배너를 무시하고 직접 호출해도 막힌다.

    승인본으로 가입해 토큰을 얻은 뒤 **승인 상태를 되돌리고** 동의만 다시 시도한다.
    브라우저를 거치지 않는 클라이언트(구버전 모바일·스크립트)가 정확히 이 경로로
    들어온다. 게이트가 폼에 있으면 여기서 통과해버린다.

    ※ approved_docs 픽스처를 쓰지 않고 monkeypatch 를 직접 다룬다 —
      이 테스트는 patch 를 **중간에 되돌려야** 하기 때문이다.
    """
    from app.services import terms_renderer

    raw = terms_renderer._manifest()          # ★ 패치 전에 실제 manifest 를 잡아둔다
    monkeypatch.setattr(terms_renderer, "_manifest", lambda: _approved_manifest(raw))
    token, farm_id = await _signup(client)

    monkeypatch.undo()                        # 실제 manifest(전 문서 DRAFT)로 복귀
    assert terms_renderer._manifest() == raw, "복원 실패 — 이 테스트는 무의미해진다"

    r = await client.post(
        "/api/v1/consent/record",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "selected_country": "US", "farm_country": "US", "farm_id": farm_id,
            "lang": "en", "terms_ack": True, "privacy_ack": True,
            "choices": [], "collection_context": "UI_SIGNUP",
        },
    )
    assert r.status_code == 451, r.text
    assert "PUBLICATION_NOT_APPROVED" in r.text
    n = await db.scalar(
        select(func.count()).select_from(ConsentRecord).where(ConsentRecord.farm_id == farm_id)
    )
    assert n == 0, "차단됐는데 원장에 초안 동의가 남았다"


async def test_withdraw_still_works_while_documents_are_draft(
    client: AsyncClient, monkeypatch,
) -> None:
    """★ 철회는 승인 여부와 무관하게 언제나 가능해야 한다.

    게이트를 record 에만 걸고 withdraw 에는 걸지 않은 이유를 여기서 못으로 박는다.
    초안이라는 이유로 철회까지 막으면 게이트가 사용자 권리를 침해한다.
    """
    from app.services import terms_renderer

    raw = terms_renderer._manifest()
    monkeypatch.setattr(terms_renderer, "_manifest", lambda: _approved_manifest(raw))
    token, farm_id = await _signup(client)
    await client.post(
        "/api/v1/consent/record",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "selected_country": "US", "farm_country": "US", "farm_id": farm_id,
            "lang": "en", "terms_ack": True, "privacy_ack": True,
            "choices": [], "collection_context": "UI_SIGNUP",
        },
    )

    monkeypatch.undo()   # DRAFT 상태로 복귀 — 이래도 철회는 되어야 한다

    r = await client.post(
        "/api/v1/consent/withdraw",
        headers={"Authorization": f"Bearer {token}"},
        json={"purpose_code": "EXTERNAL_AI_PROCESSING", "action": "WITHDRAWN"},
    )
    assert r.status_code != 451, f"초안이라는 이유로 철회가 막혔다: {r.text}"
