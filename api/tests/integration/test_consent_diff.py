"""GET /consent/diff — 목적별 (필요 버전, 기록 버전). 판정 없음.

LEGAL-P0-MANDATORY-CONSENT-LOGIN-GATE 구현 메모의 세 계약을 고정한다.
    1  국가는 서버가 정한다 — 쿼리로 국가를 보내도 무시된다
    2  불리언 없음 — 응답 어디에도 needs_reconsent 류 판정 필드가 없다
    3  "동의한 적 없음"과 "철회함"이 구분된다 (:150)
"""
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models.consent import ConsentRecord
from app.db.models.platform import Farm, Organization, User, UserFarm

pytestmark = pytest.mark.anyio


async def _user_with_farm(db: AsyncSession, country: str) -> tuple[User, Farm, dict]:
    tag = uuid.uuid4().hex[:6]
    org = Organization(name=f"Org {tag}", country=country, timezone="UTC")
    db.add(org)
    await db.flush()
    user = User(org_id=org.id, username=f"u{tag}", email=f"u{tag}@example.com", name="U",
                password_hash=hash_password("Test1234!"), role="FARM_OWNER")
    farm = Farm(org_id=org.id, farm_code=f"F-{tag}", name="F", country=country, timezone="UTC")
    db.add_all([user, farm])
    await db.flush()
    db.add(UserFarm(user_id=user.id, farm_id=farm.id))
    await db.flush()
    headers = {"Authorization": f"Bearer {create_access_token(user.id, org.id, [user.role])}"}
    return user, farm, headers


async def test_country_comes_from_the_farm_not_the_client(client: AsyncClient, db: AsyncSession):
    """BR 농장 사용자가 ?country=CL(부속조항 없는 OTHER)을 붙여도 BR 로 도출된다."""
    _, farm, h = await _user_with_farm(db, "BR")
    r = await client.get("/api/v1/consent/diff",
                         params={"farm_id": str(farm.id), "country": "CL", "selected_country": "CL"},
                         headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["farm_country"] == "BR" and body["selected_country"] == "BR"
    assert body["group"] == "BR"
    assert "ADDENDUM_BR" in body["required_version"]


async def test_country_falls_back_to_the_org_without_farm_scope(client: AsyncClient, db: AsyncSession):
    _, _, h = await _user_with_farm(db, "US")
    r = await client.get("/api/v1/consent/diff", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["selected_country"] == "US" and r.json()["farm_country"] is None
    assert r.json()["farm_id"] is None


async def test_no_verdict_field_anywhere(client: AsyncClient, db: AsyncSession):
    """계정 단위 불리언을 만들지 않는다. 목적별 두 버전만 나란히 놓는다."""
    _, farm, h = await _user_with_farm(db, "US")
    body = (await client.get("/api/v1/consent/diff", params={"farm_id": str(farm.id)},
                             headers=h)).json()
    forbidden = {"needs_reconsent", "reconsent_required", "is_current", "ok", "verdict"}
    assert not (forbidden & set(body))
    for it in body["items"]:
        assert not (forbidden & set(it))
        assert set(it) == {"purpose_code", "lawful_basis", "ui_kind", "required_version",
                           "recorded_version", "recorded_status", "recorded_at"}
    assert body["items"], "가시 목적이 하나도 없다면 계획 자체가 비어 있다"


async def test_never_consented_shows_none_not_withdrawn(client: AsyncClient, db: AsyncSession):
    _, farm, h = await _user_with_farm(db, "US")
    body = (await client.get("/api/v1/consent/diff", params={"farm_id": str(farm.id)},
                             headers=h)).json()
    assert all(it["recorded_version"] is None and it["recorded_status"] is None
               for it in body["items"])


async def _first_visible(client: AsyncClient, farm: Farm, h: dict) -> dict:
    body = (await client.get("/api/v1/consent/diff", params={"farm_id": str(farm.id)},
                             headers=h)).json()
    assert body["items"]
    return body


async def test_recorded_draft_version_is_shown_beside_required(client: AsyncClient, db: AsyncSession):
    """초안에 동의한 원장 행이 있으면 recorded_version 에 그 문자열이 그대로 나온다.
    목적·근거는 실제 계획에서 가져온다 — 원장 CHECK 제약(purpose·basis·evidence)이 지키는 값이다."""
    user, farm, h = await _user_with_farm(db, "US")
    plan = await _first_visible(client, farm, h)
    target = next(it for it in plan["items"] if it["lawful_basis"] != "CONSENT")
    now = datetime.now(UTC)
    draft = "MASTER_TERMS@0.1-draft+GLOBAL_PRIVACY_NOTICE@0.1-draft+ADDENDUM_US@0.1-draft"
    db.add(ConsentRecord(
        user_id=user.id, farm_id=farm.id, purpose_code=target["purpose_code"],
        jurisdiction="US", lawful_basis=target["lawful_basis"], consent_status="NOTICE_GIVEN",
        notice_version=draft, accepted_at=now, effective_from=now.date(),
        collection_context="UI_SIGNUP",
    ))
    await db.flush()
    body = await _first_visible(client, farm, h)
    it = next(x for x in body["items"] if x["purpose_code"] == target["purpose_code"])
    assert it["recorded_version"] == draft
    assert it["recorded_status"] == "NOTICE_GIVEN"
    assert it["required_version"] == body["required_version"]
    # 다른 목적은 여전히 "동의한 적 없음"
    others = [x for x in body["items"] if x["purpose_code"] != target["purpose_code"]]
    assert all(x["recorded_version"] is None for x in others)


async def test_withdrawn_is_distinguished_from_never(client: AsyncClient, db: AsyncSession):
    user, farm, h = await _user_with_farm(db, "US")
    plan = await _first_visible(client, farm, h)
    target = next(it for it in plan["items"] if it["lawful_basis"] == "CONSENT")
    now = datetime.now(UTC)
    db.add(ConsentRecord(
        user_id=user.id, farm_id=farm.id, purpose_code=target["purpose_code"],
        jurisdiction="US", lawful_basis="CONSENT", consent_status="WITHDRAWN",
        notice_version="x", accepted_at=now, withdrawn_at=now, effective_from=now.date(),
        collection_context="UI_SETTINGS", evidence_ref="test-evidence",
    ))
    await db.flush()
    body = await _first_visible(client, farm, h)
    it = next(x for x in body["items"] if x["purpose_code"] == target["purpose_code"])
    assert it["recorded_status"] == "WITHDRAWN"
    assert it["recorded_version"] == "x"


async def test_other_users_farm_is_forbidden(client: AsyncClient, db: AsyncSession):
    _, farm_a, _ = await _user_with_farm(db, "US")
    _, _, h_b = await _user_with_farm(db, "US")
    r = await client.get("/api/v1/consent/diff", params={"farm_id": str(farm_a.id)}, headers=h_b)
    assert r.status_code == 403, r.text


async def test_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/consent/diff")
    assert r.status_code == 401


async def test_jurisdiction_is_the_signup_paths_resolve_not_a_fallback(client: AsyncClient, db: AsyncSession):
    """US 조직 아래 BR 농장 — 가입 경로(resolve)는 더 엄격한 BR 을 고르고 counsel_review 를 켠다.
    diff 가 'FARM 우선' 이나 'ORG 우선' 폴백을 따로 두면 같은 계정에 법역 답이 둘이 된다.
    같은 함수를 태우는지 build_signup_plan 과 동치로 고정한다."""
    from app.services.consent_service import build_signup_plan

    tag = uuid.uuid4().hex[:6]
    org = Organization(name=f"Org {tag}", country="US", timezone="UTC")
    db.add(org)
    await db.flush()
    user = User(org_id=org.id, username=f"u{tag}", email=f"u{tag}@example.com", name="U",
                password_hash=hash_password("Test1234!"), role="FARM_OWNER")
    farm = Farm(org_id=org.id, farm_code=f"F-{tag}", name="F", country="BR", timezone="UTC")
    db.add_all([user, farm])
    await db.flush()
    db.add(UserFarm(user_id=user.id, farm_id=farm.id))
    await db.flush()
    h = {"Authorization": f"Bearer {create_access_token(user.id, org.id, [user.role])}"}

    body = (await client.get("/api/v1/consent/diff", params={"farm_id": str(farm.id)},
                             headers=h)).json()
    expected = build_signup_plan(selected_country="US", farm_country="BR", farm_state=None,
                                 lang=None, include_body=False)
    assert body["jurisdiction"] == expected.jurisdiction.code == "BR"
    assert body["counsel_review"] is expected.jurisdiction.counsel_review is True
    assert body["required_version"] == expected.notice_version
    assert body["selected_country"] == "US" and body["farm_country"] == "BR"

