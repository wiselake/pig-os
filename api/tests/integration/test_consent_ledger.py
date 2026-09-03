"""동의 원장 기록/철회 통합 (CONSENT_SPEC §5 원장 불변식).

- 가입 기록: 고지형(①②⑥)=NOTICE_GIVEN, 옵트인(③④⑤)=granted 만 GRANTED
- 현재상태: 목적별 최신 1행
- 철회/이의/제외: append-only, 최신이 현재
- 필수 동의 미체크 → 422
- CONSENT 근거인데 evidence 없음 → DB CheckConstraint 위반 방지(서비스가 evidence 합성)
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.consent import ConsentRecord
from app.db.models.platform import Farm, User, UserFarm
from app.schemas.consent import ConsentChoice, RecordConsentRequest, WithdrawRequest
from app.services import consent_service as cs

pytestmark = pytest.mark.anyio


# ★ LEGAL-P0-CONSENT-FARM-AUTHORITY 이후 필요.
#
#   consent 기록은 이제 farm_id 에 대한 접근 권한을 canonical 규칙
#   (`can_access_farm`)으로 확인한다. 그런데 공용 픽스처의 test_user 와 test_farm
#   은 org 만 같을 뿐 user_farms 행이 없어, 실제 서비스에서는 존재할 수 없는
#   조합이었다 — 실 가입 경로는 auth_service.py:178 에서 UserFarm 을 만든다.
#
#   즉 이 픽스처는 프로덕션 현실을 반영하지 못하고 있었다. 검증을 우회하려고
#   멤버십을 주는 것이 아니라, 픽스처를 실제 상태에 맞추는 것이다.
@pytest_asyncio.fixture(autouse=True)
async def _farm_membership(db: AsyncSession, test_user: User, test_farm: Farm):
    db.add(UserFarm(user_id=test_user.id, farm_id=test_farm.id, role_override="FARM_OWNER"))
    await db.flush()


async def _record(db, user, farm, *, country="KR", choices=None, terms=True, privacy=True):
    req = RecordConsentRequest(
        farm_id=farm.id, selected_country=country, farm_country=country,
        terms_ack=terms, privacy_ack=privacy,
        choices=choices or [],
    )
    return await cs.record_consents(db, user_id=user.id, req=req)


async def test_signup_records_notice_and_optin(db: AsyncSession, test_user: User, test_farm: Farm):
    out = await _record(db, test_user, test_farm, country="KR", choices=[
        ConsentChoice(purpose_code="AI_MODEL_TRAINING", granted=True),
        ConsentChoice(purpose_code="NAMED_RESEARCH", granted=False),
    ])
    by = {o.purpose_code: o for o in out}
    # 고지형: ① 서비스운영, ② 익명, ⑥ 외부처리 → NOTICE_GIVEN
    assert by["SERVICE_OPERATION"].consent_status == "NOTICE_GIVEN"
    assert by["ANON_AGG_STATS"].consent_status == "NOTICE_GIVEN"
    assert by["EXTERNAL_AI_PROCESSING"].consent_status == "NOTICE_GIVEN"
    # 옵트인: 켠 것만 GRANTED, 끈 건 미기록
    assert by["AI_MODEL_TRAINING"].consent_status == "GRANTED"
    assert "NAMED_RESEARCH" not in by


async def test_optin_granted_has_consent_basis_and_evidence(db: AsyncSession, test_user, test_farm):
    await _record(db, test_user, test_farm, country="KR", choices=[
        ConsentChoice(purpose_code="AI_MODEL_TRAINING", granted=True),
    ])
    row = (await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.user_id == test_user.id,
            ConsentRecord.purpose_code == "AI_MODEL_TRAINING",
        )
    )).scalars().one()
    assert row.lawful_basis == "CONSENT"
    assert row.evidence_ref  # 증적 필수(§5.2) — 서비스가 합성


async def test_required_ack_missing_is_422(db: AsyncSession, test_user, test_farm):
    with pytest.raises(Exception) as ei:
        await _record(db, test_user, test_farm, terms=False)
    assert "422" in str(ei.value) or "TERMS" in str(ei.value)


async def test_cn_signup_blocked_451(db: AsyncSession, test_user, test_farm):
    with pytest.raises(Exception) as ei:
        await _record(db, test_user, test_farm, country="CN")
    assert "451" in str(ei.value) or "BLOCKED" in str(ei.value)


async def test_current_returns_latest_per_purpose(db: AsyncSession, test_user, test_farm):
    await _record(db, test_user, test_farm, country="KR", choices=[
        ConsentChoice(purpose_code="AI_MODEL_TRAINING", granted=True),
    ])
    cur = await cs.current_consents(db, user_id=test_user.id, farm_id=test_farm.id)
    codes = {c.purpose_code for c in cur}
    assert "AI_MODEL_TRAINING" in codes and "SERVICE_OPERATION" in codes


async def test_withdraw_optin_appends_and_becomes_current(db: AsyncSession, test_user, test_farm):
    await _record(db, test_user, test_farm, country="KR", choices=[
        ConsentChoice(purpose_code="AI_MODEL_TRAINING", granted=True),
    ])
    await cs.withdraw(db, user_id=test_user.id,
                      req=WithdrawRequest(purpose_code="AI_MODEL_TRAINING", farm_id=test_farm.id, action="WITHDRAWN"))
    cur = await cs.current_consents(db, user_id=test_user.id, farm_id=test_farm.id)
    ai = next(c for c in cur if c.purpose_code == "AI_MODEL_TRAINING")
    assert ai.consent_status == "WITHDRAWN"
    # append-only: 원장에 2행 이상 남음
    n = (await db.execute(
        select(func.count()).select_from(ConsentRecord).where(
            ConsentRecord.user_id == test_user.id,
            ConsentRecord.purpose_code == "AI_MODEL_TRAINING",
        )
    )).scalar()
    assert n >= 2


async def test_exclusion_request_on_anon(db: AsyncSession, test_user, test_farm):
    await _record(db, test_user, test_farm, country="KR")
    out = await cs.withdraw(db, user_id=test_user.id,
                            req=WithdrawRequest(purpose_code="ANON_AGG_STATS", farm_id=test_farm.id,
                                                action="EXCLUSION_REQUESTED"))
    assert out.consent_status == "EXCLUSION_REQUESTED"


async def test_us_ne_written_optin_recorded_with_evidence(db: AsyncSession, test_user, test_farm):
    req = RecordConsentRequest(
        farm_id=test_farm.id, selected_country="US", farm_country="US", farm_state="NE",
        terms_ack=True, privacy_ack=True,
        choices=[ConsentChoice(purpose_code="ANON_AGG_STATS", granted=True, evidence_ref="e-signature:abc")],
    )
    out = await cs.record_consents(db, user_id=test_user.id, req=req)
    anon = next(o for o in out if o.purpose_code == "ANON_AGG_STATS")
    # NE 는 ②가 서면 옵트인 → granted 시 GRANTED(고지형 아님)
    assert anon.consent_status == "GRANTED"
    assert anon.jurisdiction == "US-NE"


# ── farm_id 귀속 권한 (LEGAL-P0-CONSENT-FARM-AUTHORITY) ────────────────────

async def test_same_org_user_without_membership_cannot_record(
    db: AsyncSession, test_farm: Farm, test_org,
):
    """★ org 소속을 농장 접근으로 오용하지 않는다.

    같은 조직이라도 농장레벨 롤(FARM_OWNER 등)은 user_farms 멤버십이 있어야
    한다 — canonical `can_access_farm` 의 semantics 다. 여기서 통과해 버리면
    법무 경로만 기존 권한 모델보다 느슨해진다."""
    from app.core.exceptions import ForbiddenError
    from app.core.security import hash_password

    outsider = User(
        org_id=test_org.id, username="outsider_x", email="outsider_x@pigos.io",
        name="Outsider", password_hash=hash_password("Test1234!"), role="FARM_OWNER",
    )
    db.add(outsider)
    await db.flush()

    with pytest.raises(ForbiddenError):
        await _record(db, outsider, test_farm, country="US")

    assert await db.scalar(
        select(func.count()).select_from(ConsentRecord)
        .where(ConsentRecord.user_id == outsider.id)
    ) == 0


async def test_withdraw_cannot_launder_inaccessible_farm_via_null(
    db: AsyncSession, test_user: User, test_org,
):
    """★ C2 회귀. farm_id 를 빼는 것만으로 권한 검증을 건너뛸 수 없다.

    withdraw 는 farm_id 가 없으면 직전 행의 farm_id 를 상속한다. 상속분을
    검사하지 않으면 접근 불가 농장에 귀속된 행을 **새로** 하나 더 만들 수 있다.
    실제 경로: 결함기에 만들어진 행, 또는 농장 비활성화로 접근을 잃은 경우
    (account_deletion_service 가 owner 삭제 시 farm.active=False 로 만든다).
    """
    from app.core.exceptions import ForbiddenError

    stranger_farm = Farm(
        org_id=test_org.id, farm_code=f"OTHER-{uuid.uuid4().hex[:6].upper()}",
        name="Stranger Farm", country="KR", timezone="Asia/Seoul",
    )
    db.add(stranger_farm)
    await db.flush()

    # 결함기에 만들어졌을 법한 행 — test_user 는 이 농장에 멤버십이 없다.
    db.add(ConsentRecord(
        user_id=test_user.id, farm_id=stranger_farm.id, purpose_code="AI_MODEL_TRAINING",
        jurisdiction="KR", lawful_basis="CONSENT", consent_status="GRANTED",
        notice_version="legacy@0.1", evidence_ref="legacy",
    ))
    await db.flush()
    before = await db.scalar(
        select(func.count()).select_from(ConsentRecord)
        .where(ConsentRecord.farm_id == stranger_farm.id)
    )

    with pytest.raises(ForbiddenError):
        await cs.withdraw(db, user_id=test_user.id,
                          req=WithdrawRequest(purpose_code="AI_MODEL_TRAINING",
                                              action="WITHDRAWN"))

    assert await db.scalar(
        select(func.count()).select_from(ConsentRecord)
        .where(ConsentRecord.farm_id == stranger_farm.id)
    ) == before, "거부됐는데 상속 행이 추가됐다"
