"""조직 계층 접근 캐스케이드 검증 — 업체(VENDOR)→총판(DISTRIBUTOR)→대리점(DEALER)→농장.

상위 조직 로그인 시 하위 트리 농장에 접근 가능해야 하고, 다른 트리는 격리(403)되어야 한다.
실제 사용자 시나리오: "업체로 로그인하면 총판·대리점·농장을 다 볼 수 있는가?"
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models.platform import Farm, Organization, User

pytestmark = pytest.mark.anyio


async def _org(db, name, org_type, level, parent=None) -> Organization:
    o = Organization(
        name=name, org_type=org_type, org_level=level,
        parent_org_id=parent.id if parent else None, country="KR", timezone="Asia/Seoul",
    )
    db.add(o)
    await db.flush()
    return o


async def _farm(db, org) -> Farm:
    f = Farm(
        org_id=org.id, farm_code=f"F-{uuid.uuid4().hex[:6].upper()}",
        name=f"{org.name} Farm", country="KR", timezone="Asia/Seoul", active=True,
    )
    db.add(f)
    await db.flush()
    return f


async def _admin(db, org, system_role) -> User:
    u = User(
        org_id=org.id, email=f"{system_role.lower()}-{uuid.uuid4().hex[:6]}@pigos.io",
        name=f"{system_role}", password_hash=hash_password("Test1234!"),
        role="FARM_OWNER", system_role=system_role,
    )
    db.add(u)
    await db.flush()
    return u


def _auth(u: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(u.id), str(u.org_id), [u.system_role])}"}


async def _build_tree(db: AsyncSession):
    # 트리 A: 업체A → 총판A → 대리점A → 농장A
    vendorA = await _org(db, "VendorA", "VENDOR", 0)
    distA = await _org(db, "DistA", "DISTRIBUTOR", 1, vendorA)
    dealerA = await _org(db, "DealerA", "DEALER", 2, distA)
    farmA = await _farm(db, dealerA)
    # 트리 B: 업체B → 대리점B → 농장B (격리 대상)
    vendorB = await _org(db, "VendorB", "VENDOR", 0)
    dealerB = await _org(db, "DealerB", "DEALER", 2, vendorB)
    farmB = await _farm(db, dealerB)
    await db.flush()
    return {
        "vendorA": vendorA, "distA": distA, "dealerA": dealerA, "farmA": farmA,
        "vendorB": vendorB, "dealerB": dealerB, "farmB": farmB,
    }


async def test_vendor_sees_whole_subtree_farm(client: AsyncClient, db: AsyncSession):
    """업체A 로그인 → 총판A·대리점A 하위 농장A 접근 가능(2단계 캐스케이드)."""
    t = await _build_tree(db)
    vendor_admin = await _admin(db, t["vendorA"], "VENDOR_ADMIN")
    await db.flush()
    r = await client.get(f"/api/v1/farms/{t['farmA'].id}", headers=_auth(vendor_admin))
    assert r.status_code == 200, r.text


async def test_distributor_sees_dealer_farm(client: AsyncClient, db: AsyncSession):
    """총판A → 대리점A 농장 접근."""
    t = await _build_tree(db)
    dist_admin = await _admin(db, t["distA"], "DISTRIBUTOR_ADMIN")
    await db.flush()
    r = await client.get(f"/api/v1/farms/{t['farmA'].id}", headers=_auth(dist_admin))
    assert r.status_code == 200, r.text


async def test_dealer_sees_own_farm(client: AsyncClient, db: AsyncSession):
    t = await _build_tree(db)
    dealer_admin = await _admin(db, t["dealerA"], "DEALER_ADMIN")
    await db.flush()
    r = await client.get(f"/api/v1/farms/{t['farmA'].id}", headers=_auth(dealer_admin))
    assert r.status_code == 200, r.text


async def test_dealer_cannot_see_other_tree_farm(client: AsyncClient, db: AsyncSession):
    """격리: 대리점A는 다른 업체(B) 트리의 농장B에 접근 불가(403)."""
    t = await _build_tree(db)
    dealer_admin = await _admin(db, t["dealerA"], "DEALER_ADMIN")
    await db.flush()
    r = await client.get(f"/api/v1/farms/{t['farmB'].id}", headers=_auth(dealer_admin))
    assert r.status_code in (403, 404), r.text


async def test_vendor_cannot_see_other_vendor_farm(client: AsyncClient, db: AsyncSession):
    """격리: 업체A는 업체B 트리 농장에 접근 불가."""
    t = await _build_tree(db)
    vendor_admin = await _admin(db, t["vendorA"], "VENDOR_ADMIN")
    await db.flush()
    r = await client.get(f"/api/v1/farms/{t['farmB'].id}", headers=_auth(vendor_admin))
    assert r.status_code in (403, 404), r.text


async def test_org_farms_endpoint_lists_subtree(client: AsyncClient, db: AsyncSession):
    """업체A의 /orgs/{id}/farms → 하위 트리 농장A 포함."""
    t = await _build_tree(db)
    vendor_admin = await _admin(db, t["vendorA"], "VENDOR_ADMIN")
    await db.flush()
    r = await client.get(f"/api/v1/orgs/{t['vendorA'].id}/farms", headers=_auth(vendor_admin))
    assert r.status_code == 200, r.text
    assert str(t["farmA"].id) in {str(x.get("farm_id", x.get("id"))) for x in r.json()}
