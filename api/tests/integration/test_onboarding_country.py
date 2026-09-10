"""
온보딩 국가별 파생값(통화/단위/타임존) + 공개 국가 설정 엔드포인트.
단일 소스 app.core.countries.COUNTRY_CONFIG 기준. Runs on pigos_test (Docker).
"""
import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.platform import Farm


def _payload(country: str, **over) -> dict:
    uniq = uuid.uuid4().hex[:8]
    body = {
        "org_name": f"Org {uniq}",
        "farm_name": f"Farm {uniq}",
        "country": country,
        "name": "Grower One",
        "username": f"grower_{uniq}",
        "email": f"{uniq}@example.com",
        "password": "supersecret8",
    }
    body.update(over)
    return body


class TestConfigCountries:
    async def test_public_countries_endpoint(self, client: AsyncClient):
        r = await client.get("/api/v1/config/countries")
        assert r.status_code == 200
        rows = r.json()
        codes = {c["code"] for c in rows}
        assert {"KR", "US", "CL", "RU"} <= codes  # 칠레·러시아 포함
        us = next(c for c in rows if c["code"] == "US")
        assert us["currency"] == "USD" and us["unit_system"] == "IMPERIAL"
        cl = next(c for c in rows if c["code"] == "CL")
        assert cl["currency"] == "CLP" and cl["timezone"] == "America/Santiago"


class TestOnboardingCountryDerivation:
    async def _farm(self, db: AsyncSession, farm_id: str) -> Farm:
        return await db.scalar(select(Farm).where(Farm.id == uuid.UUID(farm_id)))

    async def test_us_farm_gets_usd_imperial_chicago(self, client: AsyncClient, db: AsyncSession):
        r = await client.post("/api/v1/onboarding/complete", json=_payload("US"))
        assert r.status_code == 201, r.text
        farm = await self._farm(db, r.json()["farm_id"])
        assert farm.currency == "USD"
        assert farm.unit_system == "IMPERIAL"
        assert farm.timezone == "America/Chicago"

    async def test_chile_farm_gets_clp_metric_santiago(self, client: AsyncClient, db: AsyncSession, launch_enabled):
        launch_enabled("CL")   # H13: 통화 파생 검증이지 launch 정책 검증이 아니다
        r = await client.post("/api/v1/onboarding/complete", json=_payload("CL"))
        assert r.status_code == 201, r.text
        farm = await self._farm(db, r.json()["farm_id"])
        assert farm.currency == "CLP"
        assert farm.unit_system == "METRIC"
        assert farm.timezone == "America/Santiago"

    async def test_russia_farm_gets_rub_moscow(self, client: AsyncClient, db: AsyncSession, launch_enabled):
        launch_enabled("RU")   # H13: 통화 파생 검증이지 launch 정책 검증이 아니다
        r = await client.post("/api/v1/onboarding/complete", json=_payload("RU"))
        assert r.status_code == 201, r.text
        farm = await self._farm(db, r.json()["farm_id"])
        assert farm.currency == "RUB"
        assert farm.timezone == "Europe/Moscow"

    async def test_client_override_wins(self, client: AsyncClient, db: AsyncSession):
        # 클라가 명시 전송하면 그 값 우선(예: 미국 농장이 metric 선택)
        r = await client.post(
            "/api/v1/onboarding/complete",
            json=_payload("US", currency="EUR", unit_system="METRIC"),
        )
        assert r.status_code == 201, r.text
        farm = await self._farm(db, r.json()["farm_id"])
        assert farm.currency == "EUR"
        assert farm.unit_system == "METRIC"

    async def test_config_weight_unit_follows_unit_system(self, client: AsyncClient, db: AsyncSession):
        # 모바일 계약 [1](d): unit_system 이 config.weight_unit 의 SSOT.
        # US(IMPERIAL) → lb, 명시 METRIC override → kg.
        us = await client.post("/api/v1/onboarding/complete", json=_payload("US"))
        assert us.status_code == 201, us.text
        h = {"Authorization": f"Bearer {us.json()['access_token']}"}
        cfg = await client.get(f"/api/v1/farms/{us.json()['farm_id']}/config", headers=h)
        assert cfg.status_code == 200, cfg.text
        assert cfg.json()["weight_unit"] == "lb"

        metric = await client.post(
            "/api/v1/onboarding/complete",
            json=_payload("US", unit_system="METRIC"),
        )
        h2 = {"Authorization": f"Bearer {metric.json()['access_token']}"}
        cfg2 = await client.get(f"/api/v1/farms/{metric.json()['farm_id']}/config", headers=h2)
        assert cfg2.status_code == 200, cfg2.text
        assert cfg2.json()["weight_unit"] == "kg"
