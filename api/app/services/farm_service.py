from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_accessible_farm_ids
from app.db.models.config import ComplianceProfile, FarmConfig, RegionDefault
from app.db.models.platform import Farm, Organization, User, UserFarm
from app.db.models.sow import Building, Sow
from app.schemas.farm import (
    CURRENCY_SYMBOLS,
    FarmConfigSet,
    FarmCreate,
    FarmLocalConfig,
    FarmReproConfigUpdate,
    FarmUpdate,
    OnboardingStatus,
)


def _generate_farm_code(country: str, org_id: UUID) -> str:
    # org+country만으로 결정하면 같은 org의 2번째 동일국가 농장이 farm_code UNIQUE 충돌→500 (QA 온보딩 B1).
    # org 그룹핑(가독성) + 농장별 엔트로피로 유니크 보장.
    return f"FARM-{country.upper()}-{str(org_id)[:6].upper()}-{uuid4().hex[:6].upper()}"


async def org_country(db: AsyncSession, org_id: UUID | None) -> str | None:
    """조직(계정)의 authoritative 국가. 추가 농장 생성 시 cross-jurisdiction 판정에 쓴다.

    User 모델에는 country 가 없고 Organization 에만 있다."""
    if org_id is None:
        return None
    return await db.scalar(select(Organization.country).where(Organization.id == org_id))


async def create_farm(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    req: FarmCreate,
) -> Farm:
    farm = Farm(
        org_id=org_id,
        farm_code=_generate_farm_code(req.country, org_id),
        **req.model_dump(),
    )
    db.add(farm)
    await db.flush()

    db.add(UserFarm(user_id=user_id, farm_id=farm.id, role_override="FARM_OWNER"))
    await db.commit()
    await db.refresh(farm)
    return farm


async def list_farms(db: AsyncSession, user: User) -> list[Farm]:
    farm_ids = await get_accessible_farm_ids(user, db)
    if not farm_ids:
        return []

    rows = await db.scalars(
        select(Farm)
        .where(Farm.id.in_(farm_ids), Farm.active.is_(True))
        .order_by(Farm.created_at)
    )
    return list(rows)


async def update_farm(db: AsyncSession, farm: Farm, req: FarmUpdate) -> Farm:
    for k, v in req.model_dump(exclude_none=True).items():
        setattr(farm, k, v)
    await db.commit()
    await db.refresh(farm)
    return farm


async def set_farm_configs(db: AsyncSession, farm_id: UUID, req: FarmConfigSet) -> list[FarmConfig]:
    """Upsert farm configs from onboarding payload."""
    key_map = {
        "gestation_days": "GESTATION_DAYS",
        "lactation_days": "LACTATION_DAYS",
        "wei_target_days": "WEI_TARGET_DAYS",
        "pregnancy_check_day": "PREGNANCY_CHECK_DAY",
        "npd_alert_threshold": "NPD_ALERT_THRESHOLD",
        "sow_cull_parity_threshold": "SOW_CULL_PARITY_THRESHOLD",
    }
    results = []
    for field, key in key_map.items():
        value = getattr(req, field)
        if value is None:
            continue
        existing = await db.scalar(
            select(FarmConfig).where(
                FarmConfig.farm_id == farm_id,
                FarmConfig.config_key == key,
            )
        )
        if existing:
            existing.config_value = str(value)
            results.append(existing)
        else:
            cfg = FarmConfig(farm_id=farm_id, config_key=key, config_value=str(value))
            db.add(cfg)
            results.append(cfg)
    await db.commit()
    return results


async def get_local_config(db: AsyncSession, farm: Farm) -> FarmLocalConfig:
    """
    Resolve weight_unit, currency, compliance profile for this farm.
    Priority: farm.country → region_defaults → market_defaults → hardcoded fallback.
    """
    region = await db.scalar(
        select(RegionDefault).where(RegionDefault.region_code == (farm.country or "").upper())
    )

    # 농장의 명시적 unit_system(온보딩 선택)이 weight_unit의 SSOT — 없으면 region default → kg.
    # (모바일 계약: unit_system=IMPERIAL → lb. 표준 온보딩은 region과 일치하므로 하위호환.)
    if farm.unit_system == "IMPERIAL":
        weight_unit = "lb"
    elif farm.unit_system == "METRIC":
        weight_unit = "kg"
    else:
        weight_unit = (region.weight_unit if region and region.weight_unit else None) or "kg"
    currency_code = (region.currency_code if region and region.currency_code else None) or farm.currency or "USD"

    # Compliance profile
    compliance: ComplianceProfile | None = None
    profile_code = region.compliance_profile_code if region else None
    if profile_code:
        compliance = await db.scalar(
            select(ComplianceProfile).where(ComplianceProfile.profile_code == profile_code)
        )

    # Slaughter weight from default_metric_values
    slaughter_kg: float | None = None
    try:
        row = await db.execute(
            text(
                "SELECT default_value FROM default_metric_values"
                " WHERE metric_code = 'SLAUGHTER_WEIGHT'"
                "   AND scope_type = 'region' AND scope_code = :region"
                " LIMIT 1"
            ),
            {"region": (farm.country or "").upper()},
        )
        rec = row.fetchone()
        if rec:
            slaughter_kg = float(rec.default_value)
    except Exception:
        pass

    return FarmLocalConfig(
        weight_unit=weight_unit,
        currency_code=currency_code,
        currency_symbol=CURRENCY_SYMBOLS.get(currency_code, currency_code),
        min_wean_period=compliance.min_wean_period if compliance else None,
        requires_traceability=compliance.requires_traceability if compliance else False,
        requires_antibiotic_tracking=compliance.requires_antibiotic_tracking if compliance else False,
        slaughter_weight_target_kg=slaughter_kg,
        market_code=region.market_code if region else None,
    )


async def get_onboarding_status(db: AsyncSession, farm_id: UUID) -> OnboardingStatus:
    config_count = await db.scalar(
        select(func.count()).select_from(FarmConfig).where(FarmConfig.farm_id == farm_id)
    )
    sow_count = await db.scalar(
        select(func.count()).select_from(Sow).where(Sow.farm_id == farm_id, Sow.deleted_at.is_(None))
    )
    building_count = await db.scalar(
        select(func.count()).select_from(Building).where(Building.farm_id == farm_id)
    )

    has_farm_config = (config_count or 0) > 0
    has_sows = (sow_count or 0) > 0
    has_buildings = (building_count or 0) > 0

    checks = [has_farm_config, has_sows, has_buildings]
    pct = int(sum(checks) / len(checks) * 100)

    return OnboardingStatus(
        farm_id=farm_id,
        has_farm_config=has_farm_config,
        has_sows=has_sows,
        has_buildings=has_buildings,
        onboarding_complete=all(checks),
        completion_pct=pct,
    )


# ── Reproductive parameter config (Farm settings page) ────────────────────────

REPRO_CONFIG_KEYS: dict[str, tuple[str, int]] = {
    "gestation_days": ("GESTATION_DAYS", 114),
    "lactation_days": ("LACTATION_DAYS", 21),
    "wei_target_days": ("WEI_TARGET_DAYS", 7),
    "gilt_first_mating_age": ("GILT_FIRST_MATING_AGE", 240),
    "slaughter_age": ("SLAUGHTER_AGE", 180),
}


def resolve_repro_config(cfg: dict[str, str]) -> dict[str, int]:
    """Apply defaults to a raw {config_key: value} dict → typed repro params."""
    out: dict[str, int] = {}
    for field, (key, default) in REPRO_CONFIG_KEYS.items():
        try:
            out[field] = int(cfg[key])
        except (KeyError, ValueError, TypeError):
            out[field] = default
    return out


async def get_repro_config(db: AsyncSession, farm_id: UUID) -> dict[str, int]:
    rows = await db.scalars(select(FarmConfig).where(FarmConfig.farm_id == farm_id))
    cfg = {r.config_key: r.config_value for r in rows}
    return resolve_repro_config(cfg)


async def set_repro_config(
    db: AsyncSession, farm_id: UUID, body: FarmReproConfigUpdate
) -> dict[str, int]:
    for field, (key, _default) in REPRO_CONFIG_KEYS.items():
        value = getattr(body, field, None)
        if value is None:
            continue
        existing = await db.scalar(
            select(FarmConfig).where(
                FarmConfig.farm_id == farm_id, FarmConfig.config_key == key
            )
        )
        if existing:
            existing.config_value = str(value)
        else:
            db.add(FarmConfig(farm_id=farm_id, config_key=key, config_value=str(value)))
    await db.commit()
    return await get_repro_config(db, farm_id)
