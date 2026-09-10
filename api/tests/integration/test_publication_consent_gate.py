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
from tests.publication_manifest import approved_only

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


# ── 부분 승인 — 법역별로 갈리는가 ───────────────────────────────────────────

US_FIRST = {"MASTER_TERMS", "GLOBAL_PRIVACY_NOTICE", "ADDENDUM_US"}


@pytest.fixture
def us_first_approved(monkeypatch):
    """US 를 먼저 여는 시나리오 — 마스터·방침·US 부속조항만 승인."""
    from app.services import terms_renderer

    raw = terms_renderer._manifest()
    monkeypatch.setattr(terms_renderer, "_manifest", lambda: approved_only(raw, US_FIRST))
    yield


async def _try_signup(client: AsyncClient, country: str) -> int:
    tag = uuid.uuid4().hex[:8]
    r = await client.post("/api/v1/onboarding/complete", json={
        "name": "Part", "username": f"p{tag}", "email": f"p{tag}@example.com",
        "password": PW, "org_name": f"Org {tag}", "country": country, "language": "en",
        "farm_name": f"Farm {tag}", "farm_type": "FARROW_TO_FINISH",
    })
    return r.status_code


async def test_us_opens_while_addendum_jurisdictions_stay_closed(
    client: AsyncClient, us_first_approved,
) -> None:
    """★ 부분 승인이 실제로 가능하다 — G-1 은 전부-아니면-전무가 아니다.

    `build_document_set` 이 그 법역의 addendum 하나만 담으므로, US 부속조항만
    승인해도 US 는 열리고 BR·VN·TH·EU·GB 는 닫힌 채 남는다."""
    assert await _try_signup(client, "US") == 201
    for country in ("BR", "VN", "TH", "DE", "GB"):
        assert await _try_signup(client, country) == 451, f"{country} 가 열렸다"


@pytest.mark.xfail(strict=True, reason="H13 (4) 가 purpose2 AC5b 를 뒤집는다 — 해석 A/B 무관하게 깨진다. 결재문 (4) 행 재작성 후 supersede 기록 + 테스트 갱신 (APPROVAL_RECORD §5-1 [1])")
async def test_us_first_also_opens_every_country_without_an_addendum(
    client: AsyncClient, us_first_approved,
) -> None:
    """★★ "US 만 연다"는 실제로 "US + 부속조항 없는 모든 국가"다.

    `_GROUP_ADDENDUM` 에 없는 국가는 group=OTHER 이고, 문서 세트가
    MASTER + PRIVACY 뿐이다. 그 둘이 승인되는 순간 **함께 열린다.**

    설계상 맞는 동작이다 — OTHER 에는 적용할 국가별 부속조항이 애초에 없으므로
    그 둘이 곧 완전한 문서 세트다. 다만 결재 시 "US 3종 승인"의 실제 범위가
    US 하나가 아니라는 뜻이므로, 이 테스트가 그 사실을 눈에 보이게 붙잡는다.
    """
    for country in ("MX", "CL", "CO", "JP"):
        assert await _try_signup(client, country) == 201, (
            f"{country}(OTHER) 가 닫혔다 — 이 테스트의 전제가 바뀌었다면 "
            "DEPLOY_GATE §6-3 도 함께 갱신할 것"
        )


# ── H13 launch allowlist — HTTP 레벨 default-deny 가 살아 있는가 ─────────────

async def test_launch_gate_blocks_non_allowlisted_country_at_http(
    client: AsyncClient, approved_docs,
) -> None:
    """★ `launch_enabled` 헬퍼를 부르지 않으면 allowlist 밖 국가는 반드시 막힌다.

    이 테스트가 존재하는 이유는 헬퍼가 autouse 로 바뀌거나 픽스처마다 오버라이드가
    들어가서 스위트 전체가 default-deny 를 우회하게 되는 것을 막기 위해서다.
    문서 세트는 승인본(approved_docs)이라 G-3 는 통과한다 — 막는 것은 launch 게이트
    하나여야 한다.
    """
    tag = uuid.uuid4().hex[:8]
    r = await client.post("/api/v1/onboarding/complete", json={
        "name": "Launch", "username": f"l{tag}", "email": f"l{tag}@example.com",
        "password": PW, "org_name": f"Org {tag}", "country": "CL", "language": "en",
        "farm_name": f"Farm {tag}", "farm_type": "FARROW_TO_FINISH",
    })
    assert r.status_code == 451, r.text
    assert "LAUNCH_NOT_ENABLED" in r.text
