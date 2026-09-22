import logging

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DbDep
from app.core.permissions import effective_system_role, get_farm_access
from app.core.rate_limit import require_auth_quota, require_signup_quota
from app.schemas.auth import (
    AccountDeleteRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    MeUpdate,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services import account_deletion_service, auth_service, eligibility

router = APIRouter(prefix="/auth", tags=["Auth"])
log = logging.getLogger(__name__)


@router.post("/register", response_model=LoginResponse, status_code=201,
             dependencies=[Depends(require_signup_quota)])
async def register(body: RegisterRequest, db: DbDep):
    """
    Create organization + user account. Returns tokens immediately.
    Next step: POST /onboarding/complete
    """
    # ★ 국가 진입 판정을 서버가 강제한다. 클라이언트가 /consent/record 를 호출하지
    #   않아도 CN·KR hard block 을 우회할 수 없어야 한다(LEGAL-P0-CONSENT-AUTHORITY).
    #   첫 DB write 이전에 막는다 — rollback 에 기대지 않는다.
    j = eligibility.assert_country_entry_allowed(selected_country=body.country)
    # G-3: 미승인 문서 상태에서는 계정을 만들지 않는다 — 첫 write 이전에 막는다.
    eligibility.assert_publication_approved(j)
    user, org = await auth_service.register(db, body)
    return await auth_service.issue_tokens(db, user)


@router.post("/login", response_model=LoginResponse,
             dependencies=[Depends(require_auth_quota)])
async def login(body: LoginRequest, db: DbDep):
    user = await auth_service.authenticate(db, body.username, body.password)
    return await auth_service.issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: DbDep):
    return await auth_service.refresh_tokens(db, body.refresh_token)


@router.post("/logout", status_code=204)
async def logout(body: RefreshRequest, db: DbDep):
    await auth_service.logout(db, body.refresh_token)


@router.post("/password-reset/request", status_code=204,
             dependencies=[Depends(require_auth_quota)])
async def password_reset_request(body: PasswordResetRequest, db: DbDep):
    """비밀번호 재설정 요청 — 계정 존재 여부와 무관하게 항상 204(열거 방지). 존재 시 토큰 발급·전달."""
    raw = await auth_service.request_password_reset(db, body.email)
    if raw:
        await auth_service._deliver_reset_token(body.email, raw)  # 응답엔 노출 안 함
    await db.commit()


@router.post("/password-reset/confirm", status_code=204,
             dependencies=[Depends(require_auth_quota)])
async def password_reset_confirm(body: PasswordResetConfirm, db: DbDep):
    """토큰 + 새 비번 → 검증 후 비번 갱신(+ refresh 전부 폐기). 무효/만료 토큰은 400."""
    await auth_service.confirm_password_reset(db, body.token, body.new_password)
    await db.commit()


@router.get("/me", response_model=MeResponse)
async def me(current_user: CurrentUser, db: DbDep):
    # 멀티팜: 접근 가능 농장 + 농장별 role (issue_tokens와 동일 소스).
    farm_ids, farm_roles = await get_farm_access(current_user, db)
    return MeResponse(
        id=str(current_user.id),
        name=current_user.name,
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        role=current_user.role,
        system_role=effective_system_role(current_user),
        org_id=str(current_user.org_id) if current_user.org_id else None,
        language=current_user.language,
        farm_ids=farm_ids,
        farm_roles=farm_roles,
    )


@router.patch("/me", response_model=MeResponse)
async def update_me(body: MeUpdate, current_user: CurrentUser, db: DbDep):
    """프로필 자기수정(이름/연락처). 지정된 필드만 반영(부분수정)."""
    if body.name is not None:
        current_user.name = body.name
    if body.phone is not None:
        current_user.phone = body.phone or None
    await db.commit()
    await db.refresh(current_user)
    farm_ids, farm_roles = await get_farm_access(current_user, db)
    return MeResponse(
        id=str(current_user.id),
        name=current_user.name,
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        role=current_user.role,
        system_role=effective_system_role(current_user),
        org_id=str(current_user.org_id) if current_user.org_id else None,
        language=current_user.language,
        farm_ids=farm_ids,
        farm_roles=farm_roles,
    )

@router.delete("/me", status_code=204)
async def delete_me(body: AccountDeleteRequest, current_user: CurrentUser, db: DbDep):
    """계정 삭제(탈퇴) — Apple Guideline 5.1.1(v).

    앱에서 계정을 만들 수 있으면 앱에서 삭제도 가능해야 한다. 되돌릴 수 없다.

    204  삭제 완료
    401  토큰 무효
    403  비밀번호 불일치 (재인증 실패)
    422  비밀번호 누락

    처리 방식과 근거(익명화 · 농장 비활성화)는 app/services/account_deletion_service.py.
    """
    result = await account_deletion_service.delete_account(db, current_user, body.password)
    log.info("account deleted user=%s farms_deactivated=%s memberships=%s purged=%s",
             result.user_id, len(result.deactivated_farms),
             result.released_memberships, result.purged)
    await db.commit()
