import asyncio
import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.countries import get_country
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationError
from app.core.permissions import effective_system_role, get_farm_access
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.db.models.config import FarmConfig
from app.db.models.platform import (
    Farm,
    Organization,
    PasswordResetToken,
    RefreshToken,
    User,
    UserFarm,
)
from app.schemas.auth import (
    LoginResponse,
    OnboardingCompleteRequest,
    OnboardingCompleteResponse,
    RegisterRequest,
    TokenResponse,
)
from app.services.farm_service import _generate_farm_code


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# F3: 사용자 부재 시에도 동일한 bcrypt 비용을 치러 계정 열거(타이밍 오라클)를 차단.
_DUMMY_PW_HASH = hash_password("pigos-timing-equalizer")


def normalize_username(username: str) -> str:
    """username 정규화 — 앞뒤 공백 제거 + 소문자.
    'Admin'/'admin'/' admin ' 가 같은 계정으로 취급되도록(대소문자 footgun 차단, H3).
    생성·로그인·중복검사 모든 경로에서 동일 적용해야 일관성 유지."""
    return username.strip().lower()


async def register(db: AsyncSession, req: RegisterRequest) -> tuple[User, Organization]:
    username = normalize_username(req.username)
    if await db.scalar(select(User).where(User.username == username)):
        raise ConflictError("Username already taken")
    if await db.scalar(select(User).where(User.email == req.email)):
        raise ConflictError("Email already registered")

    org = Organization(
        name=req.org_name,
        country=req.country,
        timezone=req.timezone,
    )
    db.add(org)
    await db.flush()

    user = User(
        org_id=org.id,
        username=username,
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        role="FARM_OWNER",
        language=req.language,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, org


async def authenticate(db: AsyncSession, username: str, password: str) -> User:
    user = await db.scalar(
        select(User).where(User.username == normalize_username(username), User.active.is_(True))
    )
    # bcrypt는 CPU 블로킹 → asyncio.to_thread로 이벤트루프 밖에서 실행.
    # (동기 호출 시 동시 로그인이 이벤트루프에서 직렬화돼 부하 시 응답 11~24s로 폭증)
    if not user:
        # 미존재 계정도 1회 bcrypt 검증을 수행해 존재 계정과 응답시간을 맞춤(결과 무시).
        await asyncio.to_thread(verify_password, password, _DUMMY_PW_HASH)
        raise UnauthorizedError("Invalid credentials")
    if not await asyncio.to_thread(verify_password, password, user.password_hash):
        raise UnauthorizedError("Invalid credentials")

    user.last_login_at = datetime.now(UTC)
    await db.commit()
    return user


async def issue_tokens(db: AsyncSession, user: User) -> LoginResponse:
    # 멀티팜: 접근 가능 농장(총판은 하위 전체) + 농장별 role. 멤버십만 보던 기존 로직을
    # get_farm_access로 교체(조직레벨 사용자도 하위 농장 전환 가능).
    farm_ids, farm_roles = await get_farm_access(user, db)

    access = create_access_token(user.id, user.org_id, [user.role])
    refresh = create_refresh_token(user.id)

    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(refresh),
        expires_at=expires_at,
    ))
    await db.commit()

    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=str(user.id),
        name=user.name,
        username=user.username,
        email=user.email or "",
        role=user.role,
        system_role=effective_system_role(user),
        farm_ids=farm_ids,
        farm_roles=farm_roles,
    )


async def complete_onboarding(
    db: AsyncSession, req: OnboardingCompleteRequest
) -> OnboardingCompleteResponse:
    username = normalize_username(req.username)
    if await db.scalar(select(User).where(User.username == username)):
        raise ConflictError("Username already taken")
    if await db.scalar(select(User).where(User.email == req.email)):
        raise ConflictError("Email already registered")

    # 국가 → 통화/단위/타임존 파생(단일 소스 country_config). 클라가 명시 전송 시 그 값 우선.
    cc = get_country(req.country)
    eff_timezone = req.timezone if req.timezone and req.timezone != "UTC" else cc["timezone"]
    eff_currency = req.currency or cc["currency"]
    eff_unit = req.unit_system or cc["unit_system"]

    org = Organization(name=req.org_name, country=req.country, timezone=eff_timezone)
    db.add(org)
    await db.flush()

    user = User(
        org_id=org.id,
        username=username,
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        role="FARM_OWNER",
        language=req.language,  # M3: 온보딩 로케일 보존(하드코딩 "en" 제거)
    )
    db.add(user)
    await db.flush()

    farm = Farm(
        org_id=org.id,
        farm_code=_generate_farm_code(req.country, org.id),
        name=req.farm_name,
        country=req.country,
        timezone=eff_timezone,
        currency=eff_currency,
        unit_system=eff_unit,
    )
    db.add(farm)
    await db.flush()

    db.add(UserFarm(user_id=user.id, farm_id=farm.id, role_override="FARM_OWNER"))

    db.add(FarmConfig(farm_id=farm.id, config_key="FARM_TYPE", config_value=req.farm_type))
    if req.sow_count is not None:
        db.add(FarmConfig(farm_id=farm.id, config_key="SOW_CAPACITY", config_value=str(req.sow_count)))

    await db.flush()  # ensure UserFarm is visible to issue_tokens' farm_ids query
    tokens = await issue_tokens(db, user)

    return OnboardingCompleteResponse(
        org_id=str(org.id),
        farm_id=str(farm.id),
        user_id=str(user.id),
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    try:
        user_id_str = decode_refresh_token(refresh_token)
        user_id = UUID(user_id_str)
    except Exception:
        raise UnauthorizedError("Invalid refresh token")

    token_hash = _hash_token(refresh_token)
    # revoked 필터 없이 먼저 조회 — '이미 회전된(revoked) 토큰의 재사용'과 '미지의 토큰'을 구분.
    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if not stored or stored.expires_at <= datetime.now(UTC):
        raise UnauthorizedError("Refresh token revoked or expired")
    if stored.revoked:
        # F2: 회전 완료된 토큰의 재사용 = 탈취 의심(OWASP) → 해당 사용자 활성 토큰 전부 회수.
        # 탈취자·피해자 중 누가 재사용하든 패밀리 전체를 끊어 재로그인을 강제한다.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == stored.user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        await db.commit()
        raise UnauthorizedError("Refresh token reuse detected; please log in again")

    # Rotate: revoke old, issue new
    stored.revoked = True
    await db.flush()

    user = await db.get(User, user_id)
    if not user or not user.active:
        raise UnauthorizedError("User not found")

    return await issue_tokens(db, user)


async def logout(db: AsyncSession, refresh_token: str) -> None:
    token_hash = _hash_token(refresh_token)
    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if stored:
        stored.revoked = True
        await db.commit()


# ── 비밀번호 재설정 (PASSWORD_RESET_DRAFT.md 구현, 2026-06-26) ─────────────────
logger = logging.getLogger("pigos.auth.reset")
RESET_TTL = timedelta(minutes=30)


def _hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def _deliver_reset_token(email: str, raw: str) -> None:
    """재설정 토큰 전달. SMTP 설정 시 이메일 발송, 미설정 시 로그 폴백(운영자 중개).
    운영에서 SMTP 미설정이면 raw 토큰을 평문 로그에 남기지 않는다(자격증명/토큰 노출 금지)."""
    from app.services.email_service import send_email

    link = f"{settings.app_base_url.rstrip('/')}/forgot-password?token={raw}"
    sent = await send_email(
        to=email,
        subject="PigOS — Password reset / 비밀번호 재설정",
        text_body=(
            "A password reset was requested for your PigOS account.\n"
            f"Reset link (valid 30 min, one-time): {link}\n\n"
            "If you didn't request this, ignore this email.\n"
            "본 요청을 하지 않았다면 이 메일을 무시하세요."
        ),
        html_body=(
            f'<p>A password reset was requested for your PigOS account.</p>'
            f'<p><a href="{link}">Reset your password</a> (valid 30 min, one-time)</p>'
            f'<p style="color:#64748b;font-size:12px">If you didn\'t request this, ignore this email.<br>'
            f'본 요청을 하지 않았다면 이 메일을 무시하세요.</p>'
        ),
    )
    if sent:
        logger.info("[PASSWORD-RESET] reset email sent to %s", email)
    elif settings.is_production:
        logger.warning("[PASSWORD-RESET] 토큰 발급(%s) — SMTP 미설정, 전달 채널 필요(운영자 조치)", email)
    else:
        logger.warning("[PASSWORD-RESET][dev] %s 토큰=%s (TTL 30분, 1회용)", email, raw)


async def request_password_reset(db: AsyncSession, email: str) -> str | None:
    """유저 존재·active면 1회용 토큰 생성·반환(라우터가 전달). 없으면 None. 라우터는 항상 204(열거 방지).
    반환된 raw 토큰은 라우터의 _deliver_reset_token으로만 전달 — 응답엔 절대 노출 안 함."""
    user = await db.scalar(select(User).where(User.email == email, User.active.is_(True)))
    if not user:
        return None
    raw = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_reset_token(raw),
        expires_at=datetime.now(UTC) + RESET_TTL,
    ))
    await db.flush()
    return raw


async def confirm_password_reset(db: AsyncSession, token: str, new_password: str) -> None:
    """토큰 검증(해시·미만료·미사용) → 비번 갱신 + 토큰 소진 + 해당 유저 refresh 전부 폐기."""
    prt = await db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_reset_token(token))
    )
    now = datetime.now(UTC)
    if not prt or prt.used_at is not None or prt.expires_at < now:
        raise ValidationError("토큰이 유효하지 않거나 만료되었습니다.")
    user = await db.get(User, prt.user_id)
    if not user:
        raise ValidationError("토큰이 유효하지 않습니다.")
    user.password_hash = hash_password(new_password)
    prt.used_at = now
    # 같은 유저의 다른 미사용 reset 토큰 무효 + refresh 토큰 전부 삭제(강제 재로그인)
    await db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
    await db.flush()
