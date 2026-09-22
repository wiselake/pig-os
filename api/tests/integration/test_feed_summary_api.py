"""GET /farms/{id}/feed/summary · /months — 계약(docs/feed/FEED_READ_API_CONTRACT_DRAFT.md) 통합테스트.

basis 필수 · null≠0 · no_data 는 200 · 부분원가는 evidence · basis 별 소스 분리 · FCR 없음 · 판정 없음(no_policy).
"""
from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.models.health import FeedRecord
from app.db.models.platform import Farm, User, UserFarm


@pytest_asyncio.fixture
async def auth_headers(db: AsyncSession, test_user: User, test_farm: Farm) -> dict[str, str]:
    """FARM 레벨 롤은 user_farms 멤버십으로 접근 (dependencies.get_farm_context)."""
    db.add(UserFarm(user_id=test_user.id, farm_id=test_farm.id))
    await db.flush()
    return {"Authorization": f"Bearer {create_access_token(test_user.id, test_user.org_id, [test_user.system_role])}"}


async def _seed(db: AsyncSession, farm: Farm, user: User) -> None:
    rows = [
        FeedRecord(farm_id=farm.id, record_date=date(2026, 7, 10), quantity_kg=900, feed_type="Grower", unit_cost=1.0, currency="USD", created_by=user.id),
        FeedRecord(farm_id=farm.id, record_date=date(2026, 8, 5), quantity_kg=1000, feed_type="Grower", unit_cost=1.0, currency="USD", created_by=user.id),
        FeedRecord(farm_id=farm.id, record_date=date(2026, 8, 20), quantity_kg=500, feed_type="Finisher", unit_cost=None, currency=None, created_by=user.id),
    ]
    db.add_all(rows)
    await db.flush()


@pytest.mark.asyncio
async def test_summary_requires_basis_and_valid_period(client: AsyncClient, test_farm: Farm, auth_headers):
    r = await client.get(f"/api/v1/farms/{test_farm.id}/feed/summary", params={"period": "2026-08"}, headers=auth_headers)
    assert r.status_code == 422
    r = await client.get(f"/api/v1/farms/{test_farm.id}/feed/summary", params={"period": "2026-8", "basis": "AS_RECORDED"}, headers=auth_headers)
    assert r.status_code == 422
    r = await client.get(f"/api/v1/farms/{test_farm.id}/feed/summary", params={"period": "2026-08", "basis": "CONSUMED"}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_summary_unauthenticated_is_401(client: AsyncClient, test_farm: Farm):
    r = await client.get(f"/api/v1/farms/{test_farm.id}/feed/summary", params={"period": "2026-08", "basis": "AS_RECORDED"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_summary_as_recorded_partial_cost_is_evidence_not_zero(client: AsyncClient, db: AsyncSession, test_farm: Farm, test_user: User, auth_headers):
    await _seed(db, test_farm, test_user)
    r = await client.get(f"/api/v1/farms/{test_farm.id}/feed/summary", params={"period": "2026-08", "basis": "AS_RECORDED"}, headers=auth_headers)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["quantity_basis"] == "AS_RECORDED" and j["no_data"] is False and j["period"]["grain"] == "calendar_month"
    mt = j["metrics"]
    assert mt["FEED_QTY"]["value"] == 1500.0 and mt["FEED_QTY"]["provenance"] == "ACTUAL"
    assert mt["FEED_COST"]["value"] is None and mt["FEED_COST"]["reason"] == "cost_incomplete"
    assert mt["FEED_COST"]["evidence"]["partial_cost"] == 1000.0            # 부분원가는 evidence
    assert mt["FEED_UNIT_PRICE"]["value"] == 1.0 and mt["FEED_MIX_SHARE"]["evidence"]["dominant_type"] == "grower"
    assert mt["FEED_QTY_CHANGE"]["value"] == 600.0 and mt["FEED_QTY_CHANGE"]["evidence"]["comparison_grain"] == "calendar_month"
    assert mt["FEED_COST_CHANGE"]["value"] is None and mt["FEED_COST_CHANGE"]["reason"] == "cost_incomplete"
    assert "FCR" not in mt and "FEED_COST_PER_KG_GAIN" not in mt              # 효율 지표 없음
    assert mt["FEED_QTY"]["status"]["reason"] in ("no_policy", None)          # 판정 없음
    assert any(f["rule_id"] == "feed.cost_incomplete" for f in j["findings"])
    assert j["currency"] == "USD" and j["provenance"]["rows"] == 2


@pytest.mark.asyncio
async def test_summary_no_data_is_200_with_null_metrics(client: AsyncClient, test_farm: Farm, auth_headers):
    r = await client.get(f"/api/v1/farms/{test_farm.id}/feed/summary", params={"period": "2026-08", "basis": "AS_RECORDED"}, headers=auth_headers)
    assert r.status_code == 200
    j = r.json()
    assert j["no_data"] is True and all(v["value"] is None and v["reason"] == "no_data" for k, v in j["metrics"].items()
                                        if k in ("FEED_QTY", "FEED_COST", "FEED_UNIT_PRICE", "FEED_MIX_SHARE"))


@pytest.mark.asyncio
async def test_delivered_basis_reads_source_rows_only(client: AsyncClient, db: AsyncSession, test_farm: Farm, test_user: User, auth_headers):
    await _seed(db, test_farm, test_user)                                    # 수기 행이 있어도
    r = await client.get(f"/api/v1/farms/{test_farm.id}/feed/summary", params={"period": "2026-08", "basis": "DELIVERED"}, headers=auth_headers)
    assert r.status_code == 200
    j = r.json()
    assert j["quantity_basis"] == "DELIVERED" and j["no_data"] is True       # DELIVERED 소스는 비어 있다 — 수기와 합치지 않는다
    assert j["metrics"]["FEED_QTY"]["value"] is None


@pytest.mark.asyncio
async def test_months_series(client: AsyncClient, db: AsyncSession, test_farm: Farm, test_user: User, auth_headers):
    await _seed(db, test_farm, test_user)
    r = await client.get(f"/api/v1/farms/{test_farm.id}/feed/months", params={"from": "2026-06", "to": "2026-08", "basis": "AS_RECORDED"}, headers=auth_headers)
    assert r.status_code == 200
    j = r.json()
    assert [x["period"] for x in j] == ["2026-06", "2026-07", "2026-08"]
    assert j[0]["rows"] == 0 and j[0]["feed_qty_kg"] is None
    assert j[1]["feed_qty_kg"] == 900.0 and j[1]["feed_cost"] == 900.0
    assert j[2]["feed_qty_kg"] == 1500.0 and j[2]["feed_cost"] is None and j[2]["partial_cost"] == 1000.0
    r = await client.get(f"/api/v1/farms/{test_farm.id}/feed/months", params={"from": "2026-09", "to": "2026-08", "basis": "AS_RECORDED"}, headers=auth_headers)
    assert r.status_code == 422
