"""동의 기록 컨텍스트·법역 가시성 (CONSENT_SPEC §3·§4) — ledger 미커버분.

- UI_SETTINGS 컨텍스트: 필수 ack 요건은 가입(UI_SIGNUP)에만 적용 → 설정 변경은 ack 없이 허용
- VN ⑤ TRANSACTION_MATCHING = HIDDEN → granted 로 보내도 기록 안 됨(매매 규제)
- VN ① SERVICE_OPERATION = 고지형 → NOTICE_GIVEN
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.platform import Farm, User
from app.schemas.consent import ConsentChoice, RecordConsentRequest
from app.services import consent_service as cs

pytestmark = pytest.mark.anyio


async def test_ui_settings_context_skips_ack_requirement(db: AsyncSession, test_user: User, test_farm: Farm):
    # 설정 화면(UI_SETTINGS)에서는 terms/privacy ack 없이도 옵트인 갱신 허용
    req = RecordConsentRequest(
        farm_id=test_farm.id, selected_country="KR", farm_country="KR",
        terms_ack=False, privacy_ack=False, collection_context="UI_SETTINGS",
        choices=[ConsentChoice(purpose_code="AI_MODEL_TRAINING", granted=True)],
    )
    out = await cs.record_consents(db, user_id=test_user.id, req=req)  # 422 없어야 함
    ai = next(o for o in out if o.purpose_code == "AI_MODEL_TRAINING")
    assert ai.consent_status == "GRANTED"
    assert ai.collection_context == "UI_SETTINGS"


async def test_vn_transaction_matching_hidden_not_recorded(db: AsyncSession, test_user, test_farm):
    req = RecordConsentRequest(
        farm_id=test_farm.id, selected_country="VN", farm_country="VN",
        terms_ack=True, privacy_ack=True,
        choices=[ConsentChoice(purpose_code="TRANSACTION_MATCHING", granted=True)],
    )
    out = await cs.record_consents(db, user_id=test_user.id, req=req)
    codes = {o.purpose_code for o in out}
    # ⑤ 는 VN 미노출 → granted 여도 원장에 없음
    assert "TRANSACTION_MATCHING" not in codes
    # ① 서비스운영 고지형은 기록됨
    svc = next(o for o in out if o.purpose_code == "SERVICE_OPERATION")
    assert svc.consent_status == "NOTICE_GIVEN"
    assert svc.jurisdiction == "VN"


async def test_kr_signup_blocked_when_allow_off(db: AsyncSession, test_user, test_farm, monkeypatch):
    # 운영 기본(allow_kr_signup=False) → KR 실고객 가입 차단(451). autouse override를 이 테스트만 끔.
    # 게이트 판정이 jurisdiction.signup_overrides 로 모이면서 설정을 지연 조회한다 → 정본 settings 를 패치.
    from app.core.config import settings
    monkeypatch.setattr(settings, "allow_kr_signup", False)
    req = RecordConsentRequest(
        farm_id=test_farm.id, selected_country="KR", farm_country="KR",
        terms_ack=True, privacy_ack=True, choices=[],
    )
    with pytest.raises(Exception) as ei:
        await cs.record_consents(db, user_id=test_user.id, req=req)
    assert "451" in str(ei.value) or "KR_REFERENCE_ONLY" in str(ei.value)
