"""D-15a / Q-0 (2026-09-23): Feed Delivery Intelligence is REFERENCE_VISIBLE only; global commercial customers stay HIDDEN.
The state is decided by the server from one explicit flag (farm_configs FEED_DELIVERY_VISIBILITY); no flag → HIDDEN.
A client cannot see deliveries by asking for basis=DELIVERED directly, and cannot set the flag through any user API."""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.models.config import FarmConfig
from app.db.models.feed_source import FeedSourceSyncRun
from app.db.models.platform import Farm, User, UserFarm
from app.repositories.feed_source_repo import Observation, ingest_observations
from app.routers.base import feed_summary as fs
from app.services import feed_visibility as fv

NOW = datetime(2026, 9, 23, 3, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _frozen_now(monkeypatch):
    monkeypatch.setattr(fs, "_now", lambda: NOW)


@pytest_asyncio.fixture
async def auth_headers(db: AsyncSession, test_user: User, test_farm: Farm) -> dict[str, str]:
    db.add(UserFarm(user_id=test_user.id, farm_id=test_farm.id))
    await db.flush()
    return {"Authorization": f"Bearer {create_access_token(test_user.id, test_user.org_id, [test_user.system_role])}"}


async def _flag(db: AsyncSession, farm: Farm, value: str) -> None:
    db.add(FarmConfig(farm_id=farm.id, config_key=fv.VISIBILITY_KEY, config_value=value))
    await db.flush()


async def _deliveries(db: AsyncSession, farm: Farm) -> None:
    run = FeedSourceSyncRun(source_system="pigplan", source_dataset="tm_etc_trade", source_contract_version="pigplan_feed_delivery.v1",
                            status="SUCCEEDED", started_at=datetime(2026, 9, 23, 0, 10, tzinfo=UTC),
                            completed_at=datetime(2026, 9, 23, 0, 20, tzinfo=UTC), watermark_to=datetime(2026, 9, 23, 0, 8, tzinfo=UTC),
                            farms=1, rows_fetched=2, rows_inserted=2, rows_unchanged=0, rows_superseded=0, rows_retracted=0)
    db.add(run)
    await db.flush()
    obs = [Observation(source_system="pigplan", source_dataset="tm_etc_trade", source_row_key=f"T:{i}",
                       source_contract_version="pigplan_feed_delivery.v1", farm_id=farm.id, event_date=d, event_date_raw=d.isoformat(),
                       quantity_kg=Decimal(kg), quantity_basis="DELIVERED", unit_cost=Decimal("600"), total_cost=None, currency="KRW",
                       feed_stage_raw="grower", feed_product_raw="p", source_status="ACTIVE", quantity_status="ACCEPTED",
                       cost_status="ACCEPTED")
           for i, (d, kg) in enumerate([(date(2026, 7, 10), "1000"), (date(2026, 8, 10), "1200")])]
    await ingest_observations(db, obs, observed_at=NOW, sync_run_id=run.id)
    await db.flush()


async def _summary(client, farm, headers, basis="DELIVERED", **extra):
    return await client.get(f"/api/v1/farms/{farm.id}/feed/summary", params={"period": "2026-08", "basis": basis, **extra}, headers=headers)


async def _sources(client, farm, headers):
    r = await client.get(f"/api/v1/farms/{farm.id}/feed/sources", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.asyncio
async def test_no_flag_is_hidden_and_delivered_is_404(client: AsyncClient, db: AsyncSession, test_farm: Farm, auth_headers):
    await _deliveries(db, test_farm)                       # data exists — still hidden
    j = await _sources(client, test_farm, auth_headers)
    assert j["delivered"] == {"visibility": "HIDDEN", "rows": None, "last_sync": None, "latest_run_status": None}
    assert (await _summary(client, test_farm, auth_headers)).status_code == 404
    r = await client.get(f"/api/v1/farms/{test_farm.id}/feed/months", params={"from": "2026-07", "to": "2026-08", "basis": "DELIVERED"}, headers=auth_headers)
    assert r.status_code == 404
    assert (await _summary(client, test_farm, auth_headers, basis="AS_RECORDED")).status_code == 200   # manual area unaffected


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["yes", "reference_visible", "", "HIDDEN", "PUBLIC"])
async def test_unknown_flag_value_is_hidden(client, db, test_farm, auth_headers, value):
    await _flag(db, test_farm, value)
    assert (await _sources(client, test_farm, auth_headers))["delivered"]["visibility"] == "HIDDEN"
    assert (await _summary(client, test_farm, auth_headers)).status_code == 404


@pytest.mark.asyncio
async def test_reference_visible_farm_sees_deliveries_and_data_as_of(client, db, test_farm, auth_headers):
    await _flag(db, test_farm, "REFERENCE_VISIBLE")
    await _deliveries(db, test_farm)
    j = await _sources(client, test_farm, auth_headers)
    assert j["delivered"]["visibility"] == "REFERENCE_VISIBLE" and j["delivered"]["rows"] == 2
    assert j["delivered"]["last_sync"]["completed_at"].startswith("2026-09-23T00:20") and j["delivered"]["latest_run_status"] == "SUCCEEDED"
    r = await _summary(client, test_farm, auth_headers)
    assert r.status_code == 200
    mt = r.json()["metrics"]
    assert mt["FEED_QTY"]["value"] == 1200.0 and r.json()["quantity_basis"] == "DELIVERED"
    assert not ({"FCR", "FEED_COST_PER_KG_GAIN", "FEED_QTY_PER_HEAD", "FEED_COST_PER_PIG", "ADG"} & set(mt))


@pytest.mark.asyncio
async def test_reference_visible_without_rows_reports_zero_rows(client, db, test_farm, auth_headers):
    """The 33 mapped farms without deliveries: visible flag, 0 rows → the web shows no deliveries area (empty state)."""
    await _flag(db, test_farm, "REFERENCE_VISIBLE")
    j = await _sources(client, test_farm, auth_headers)
    assert j["delivered"]["visibility"] == "REFERENCE_VISIBLE" and j["delivered"]["rows"] == 0


@pytest.mark.asyncio
async def test_customer_visible_path_exists(client, db, test_farm, auth_headers):
    await _flag(db, test_farm, "CUSTOMER_VISIBLE")
    assert (await _sources(client, test_farm, auth_headers))["delivered"]["visibility"] == "CUSTOMER_VISIBLE"
    assert (await _summary(client, test_farm, auth_headers)).status_code == 200


@pytest.mark.asyncio
async def test_client_cannot_self_declare_visibility(client, db, test_farm, auth_headers):
    await _deliveries(db, test_farm)
    hdr = {**auth_headers, "X-Feed-Visibility": "REFERENCE_VISIBLE"}
    for r in (await _summary(client, test_farm, hdr, visibility="REFERENCE_VISIBLE"),
              await _summary(client, test_farm, hdr, visibility="CUSTOMER_VISIBLE")):
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_no_user_api_can_set_the_flag(client, db, test_farm, test_user, auth_headers):
    """The onboarding config endpoint only takes whitelisted fields — an extra field never becomes a farm_configs row."""
    r = await client.post(f"/api/v1/onboarding/farm/{test_farm.id}/config",
                          json={"gestation_days": 115, "feed_delivery_visibility": "REFERENCE_VISIBLE",
                                "FEED_DELIVERY_VISIBILITY": "REFERENCE_VISIBLE"}, headers=auth_headers)
    assert r.status_code in (200, 403), r.text
    rows = (await db.scalars(select(FarmConfig).where(FarmConfig.farm_id == test_farm.id, FarmConfig.config_key == fv.VISIBILITY_KEY))).all()
    assert rows == []
    assert (await _sources(client, test_farm, auth_headers))["delivered"]["visibility"] == "HIDDEN"


@pytest.mark.asyncio
async def test_visibility_is_per_farm(client, db, test_farm, test_org, test_user, auth_headers):
    other = Farm(id=uuid4(), org_id=test_org.id, farm_code="PP-X", name="x", country="KR", timezone="Asia/Seoul")
    db.add(other)
    await db.flush()
    await _flag(db, other, "REFERENCE_VISIBLE")                # another farm is visible …
    assert (await _sources(client, test_farm, auth_headers))["delivered"]["visibility"] == "HIDDEN"   # … this one is not
