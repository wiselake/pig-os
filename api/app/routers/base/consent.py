"""동의 인프라 라우터 (TERMS_DISPLAY §7, CONSENT_SPEC §3~§5).

- GET  /consent/signup-plan   가입/설정 화면 스펙(법역·문서·목적 UI) — 인증 사용자
- POST /consent/record        동의/고지 선택 기록
- GET  /consent/current       현재 유효 상태(목적별 최신)
- POST /consent/withdraw      철회/이의/제외요청
"""
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DbDep
from app.schemas.consent import (
    ConsentDiffOut,
    ConsentStatusOut,
    RecordConsentRequest,
    SignupPlan,
    WithdrawRequest,
)
from app.services import consent_service

router = APIRouter(prefix="/consent", tags=["Consent"])


@router.get("/signup-plan", response_model=SignupPlan)
async def get_signup_plan(
    # 공개: 가입 전(pre-auth) 온보딩에서 법역별 약관·목적 UI를 그리기 위한 정책 프리뷰.
    # 사용자 데이터 없음(정책·문서 조합만) → 인증 불요. 기록(record)은 인증 필요.
    selected_country: str = Query(..., min_length=2, max_length=2),
    farm_country: str | None = Query(None, min_length=2, max_length=2),
    farm_state: str | None = Query(None, max_length=3),
    lang: str | None = Query(None, max_length=5),
    include_body: bool = Query(True),
) -> SignupPlan:
    return consent_service.build_signup_plan(
        selected_country=selected_country,
        farm_country=farm_country,
        farm_state=farm_state,
        lang=lang,
        include_body=include_body,
    )


@router.post("/record", response_model=list[ConsentStatusOut])
async def record_consent(
    req: RecordConsentRequest, current_user: CurrentUser, db: DbDep,
) -> list[ConsentStatusOut]:
    return await consent_service.record_consents(db, user_id=current_user.id, req=req)


@router.get("/current", response_model=list[ConsentStatusOut])
async def get_current_consents(
    current_user: CurrentUser, db: DbDep,
    farm_id: UUID | None = Query(None),
) -> list[ConsentStatusOut]:
    return await consent_service.current_consents(db, user_id=current_user.id, farm_id=farm_id)


@router.get("/diff", response_model=ConsentDiffOut)
async def get_consent_diff(
    current_user: CurrentUser, db: DbDep,
    farm_id: UUID | None = Query(None),
) -> ConsentDiffOut:
    """목적별 (필요 버전, 기록 버전). ★ 국가 파라미터 없음 — 서버가 farm/org 에서 도출한다."""
    return await consent_service.consent_diff(db, user_id=current_user.id, farm_id=farm_id)


@router.post("/withdraw", response_model=ConsentStatusOut)
async def withdraw_consent(
    req: WithdrawRequest, current_user: CurrentUser, db: DbDep,
) -> ConsentStatusOut:
    return await consent_service.withdraw(db, user_id=current_user.id, req=req)
