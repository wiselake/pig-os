"""
Onboarding flow (quick start):
  POST /onboarding/complete  → one-step: creates org + user + farm, returns tokens

Extended flow (advanced):
  Step 1: POST /auth/register       → creates org + user
  Step 2: POST /onboarding/farm     → creates farm, links user
  Step 3: POST /onboarding/farm/{id}/config → set farm params
  Step 4: POST /farms/{id}/sows     → add first sows
  GET  /onboarding/farm/{id}/status → completion check
"""
from uuid import UUID

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbDep, FarmDep, require_farm_role, require_role
from app.schemas.auth import OnboardingCompleteRequest, OnboardingCompleteResponse
from app.schemas.farm import FarmConfigSet, FarmCreate, FarmResponse, OnboardingStatus
from app.services import auth_service, eligibility, farm_service

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.post("/complete", response_model=OnboardingCompleteResponse, status_code=201)
async def onboarding_complete(body: OnboardingCompleteRequest, db: DbDep):
    """
    One-step onboarding: create org + user + farm in a single call.
    Returns tokens immediately — no follow-up steps required.
    """
    # 계정 국가와 농장 국가를 함께 넣는다 — 이 엔드포인트는 org+user+farm 을 한 번에
    # 만들므로 둘 다 판정 대상이다(현재 계약상 같은 값이지만 resolver 의미를 유지한다).
    # ★ 첫 DB write 이전에 막는다 — rollback 에 기대지 않는다.
    eligibility.assert_country_entry_allowed(
        selected_country=body.country, farm_country=body.country,
    )
    return await auth_service.complete_onboarding(db, body)


@router.post("/farm", response_model=FarmResponse, status_code=201,
             dependencies=[require_role(
                 "FARM_OWNER", "VENDOR_ADMIN", "DISTRIBUTOR_ADMIN", "DEALER_ADMIN", "SUPER_ADMIN")])
async def create_farm(body: FarmCreate, db: DbDep, current_user: CurrentUser):
    """
    Create a farm and link it to the current user (caller becomes FARM_OWNER).
    org-스코프 작업 — 농장소유주/조직관리자만(QA 보안 H3: VIEWER/WORKER 등 무권한 생성 차단).
    farm_code is auto-generated: FARM-{COUNTRY}-{ORG_PREFIX}-{RAND}.
    """
    # ★ 추가 농장은 계정 국가와 농장 국가가 다를 수 있다(US 계정 + BR 농장).
    #   farm.country 만 넣으면 cross-jurisdiction 판정(더 엄격한 쪽 + counsel)이 사라진다.
    account_country = await farm_service.org_country(db, current_user.org_id)
    eligibility.assert_country_entry_allowed(
        selected_country=account_country or body.country, farm_country=body.country,
    )
    farm = await farm_service.create_farm(db, current_user.org_id, current_user.id, body)
    return FarmResponse.model_validate(farm)


@router.post("/farm/{farm_id}/config", response_model=dict,
             dependencies=[require_farm_role("FARM_OWNER", "FARM_MANAGER", "SUPER_ADMIN")])
async def set_farm_config(
    farm_id: UUID,
    body: FarmConfigSet,
    db: DbDep,
    farm: FarmDep,  # validates access
):
    """
    Upsert reproductive parameters. All fields optional — only provided keys are saved.
    Default values (gestation=114, lactation=21) apply until overridden.
    """
    await farm_service.set_farm_configs(db, farm_id, body)
    return {"saved": True}


@router.get("/farm/{farm_id}/status", response_model=OnboardingStatus)
async def onboarding_status(farm_id: UUID, db: DbDep, farm: FarmDep):
    """Returns completion % and which onboarding steps are done."""
    return await farm_service.get_onboarding_status(db, farm_id)
