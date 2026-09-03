"""동의 API — **HTTP 계층** 계약.

기존 동의 테스트 3파일(`test_consent_ledger` · `test_consent_record_context` ·
`test_consent_withdraw_edge`)은 전부 `consent_service` 를 직접 부른다. 서비스가
옳다는 것과 **클라이언트가 실제로 쓰는 경로가 옳다**는 것은 다른 얘기다.
이 프로젝트는 이미 그 층에서 두 번 데였다.

    2026-08-25   계정 삭제 — 서비스는 멀쩡한데 라우터가 없어 405
    2026-09-03   국가 차단 — 서비스에만 있어서 register 로 우회

그래서 라우터 배선·인증 요구·상태코드를 요청으로 확인한다.

## 특히 잠그는 것

    /consent/record 는 인증을 요구한다
        웹 fail-closed(LEGAL-P0-WEB-CONSENT-FAIL-CLOSED)는 가입 직후 받은
        토큰을 이 호출에만 명시 주입한다. 엔드포인트가 인증을 요구하지
        않는다면 그 설계 전체가 무의미해진다 — 전제를 못으로 박는다.

    /consent/signup-plan 은 공개다
        가입 전(pre-auth) 화면이 법역별 약관을 그려야 하므로 의도된 공개다.
        나중에 누가 인증을 붙이면 온보딩 2단계가 통째로 깨진다.

    철회해도 세션은 살아 있다
        `LEGAL_P0_MANDATORY_CONSENT_LOGIN_GATE.md` 에 UNVERIFIED 로 남겨둔
        항목이다. 추정으로 닫지 않고 실제 요청으로 확인해 여기 고정한다.

★ 이 파일은 동작을 바꾸지 않는다. 현재 계약을 그대로 기록할 뿐이다.
  아래 `test_record_does_not_verify_farm_membership` 는 **바람직한 동작이
  아니라 현재 동작**을 고정한 것이다 — 주석 참조.
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.consent import ConsentRecord

pytestmark = pytest.mark.anyio

PW = "Test1234!"
AUTH = "/api/v1/auth"
CONSENT = "/api/v1/consent"


async def _signup(client: AsyncClient, country: str = "US") -> tuple[str, str]:
    """온보딩으로 가입하고 (access_token, farm_id) 반환.

    register 가 아니라 onboarding/complete 를 쓰는 이유: 동의 기록에는 farm_id 가
    필요하고, 웹이 실제로 지나는 경로가 이쪽이다.
    """
    tag = uuid.uuid4().hex[:8]
    r = await client.post("/api/v1/onboarding/complete", json={
        "name": "HTTP", "username": f"h{tag}", "email": f"h{tag}@example.com",
        "password": PW, "org_name": f"Org {tag}", "country": country, "language": "en",
        "farm_name": f"Farm {tag}", "farm_type": "FARROW_TO_FINISH",
    })
    assert r.status_code == 201, r.text
    return r.json()["access_token"], r.json()["farm_id"]


def _body(farm_id: str, *, country="US", terms=True, privacy=True, choices=None) -> dict:
    return {
        "farm_id": farm_id, "selected_country": country, "farm_country": country,
        "lang": "en", "terms_ack": terms, "privacy_ack": privacy,
        "choices": choices or [], "collection_context": "UI_SIGNUP",
    }


async def _ledger_count(db: AsyncSession, farm_id: str) -> int:
    return await db.scalar(
        select(func.count()).select_from(ConsentRecord)
        .where(ConsentRecord.farm_id == uuid.UUID(farm_id))
    )


# ── 1. 인증 경계 ────────────────────────────────────────────────────────────

async def test_record_requires_authentication(client: AsyncClient):
    """★ 웹 fail-closed 설계의 전제.

    가입 직후 auth store 는 아직 비어 있고, 토큰을 이 호출에만 명시 주입한다.
    엔드포인트가 인증을 요구하지 않으면 그 주입도, 실패 처리도 의미가 없다."""
    r = await client.post(f"{CONSENT}/record", json=_body(str(uuid.uuid4())))
    assert r.status_code == 401, r.text


async def test_current_and_withdraw_require_authentication(client: AsyncClient):
    r = await client.get(f"{CONSENT}/current")
    assert r.status_code == 401, r.text
    r = await client.post(f"{CONSENT}/withdraw", json={
        "purpose_code": "AI_MODEL_TRAINING", "action": "WITHDRAWN",
    })
    assert r.status_code == 401, r.text


async def test_signup_plan_is_public_on_purpose(client: AsyncClient):
    """가입 전 화면이 법역별 약관을 그려야 하므로 의도된 공개다.

    여기에 인증을 붙이면 온보딩 확인 스텝이 통째로 죽는다(plan 실패 →
    fail-closed 로 제출 불가). 그 의도를 못으로 박는다."""
    r = await client.get(f"{CONSENT}/signup-plan", params={
        "selected_country": "US", "farm_country": "US", "include_body": False,
    })
    assert r.status_code == 200, r.text
    assert r.json()["jurisdiction"]["country"] == "US"


# ── 2. 기록이 실제로 원장에 남는다 ──────────────────────────────────────────

async def test_record_over_http_writes_the_ledger(client: AsyncClient, db: AsyncSession):
    """★ 프로덕션 원장이 0행이었다. 경로가 실제로 쓰는지 요청으로 확인한다."""
    token, farm_id = await _signup(client)
    assert await _ledger_count(db, farm_id) == 0

    r = await client.post(f"{CONSENT}/record", json=_body(farm_id),
                          headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert len(r.json()) > 0, "200 인데 아무 목적도 반환되지 않았다"
    assert await _ledger_count(db, farm_id) > 0, "200 인데 원장이 비어 있다"


async def test_current_reflects_what_was_recorded(client: AsyncClient):
    token, farm_id = await _signup(client)
    auth = {"Authorization": f"Bearer {token}"}
    await client.post(f"{CONSENT}/record", json=_body(farm_id), headers=auth)

    r = await client.get(f"{CONSENT}/current", params={"farm_id": farm_id}, headers=auth)
    assert r.status_code == 200, r.text
    codes = {row["purpose_code"] for row in r.json()}
    assert "SERVICE_OPERATION" in codes


# ── 3. 실패 계약 — 웹이 이 코드들을 그대로 표시한다 ─────────────────────────

async def test_missing_mandatory_ack_is_422_over_http(client: AsyncClient, db: AsyncSession):
    token, farm_id = await _signup(client)
    r = await client.post(f"{CONSENT}/record", json=_body(farm_id, terms=False),
                          headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422, r.text
    assert await _ledger_count(db, farm_id) == 0, "422 인데 원장에 뭔가 남았다"


async def test_blocked_country_is_451_with_reason_over_http(client: AsyncClient):
    """웹은 detail 문자열을 그대로 사용자에게 보여준다 — 포맷이 계약이다."""
    token, farm_id = await _signup(client)
    r = await client.post(f"{CONSENT}/record", json=_body(farm_id, country="CN"),
                          headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 451, r.text
    assert "SIGNUP_BLOCKED:HOLD_D07" in r.text


# ── 4. 철회 후 세션 — UNVERIFIED 를 닫는다 ──────────────────────────────────

async def test_withdrawal_does_not_end_the_session(client: AsyncClient):
    """★ `LEGAL_P0_MANDATORY_CONSENT_LOGIN_GATE.md` 의 UNVERIFIED 항목.

    실측 결과: **철회해도 토큰은 그대로 유효하다.** 로그인 게이트가 없기 때문이다.

    이것을 버그로 단정하지 않는다 — 선택 목적 하나를 철회했다고 서비스가
    끊기면 그게 더 이상하다. 다만 "철회했는데 계속 쓸 수 있다"는 사실 자체는
    로그인 게이트 설계 시 반드시 구분해서 다뤄야 하는 상태다
    (동의한 적 없음 ≠ 동의했다가 철회함)."""
    token, farm_id = await _signup(client)
    auth = {"Authorization": f"Bearer {token}"}
    await client.post(f"{CONSENT}/record", json=_body(farm_id, choices=[
        {"purpose_code": "AI_MODEL_TRAINING", "granted": True},
    ]), headers=auth)

    w = await client.post(f"{CONSENT}/withdraw", json={
        "purpose_code": "AI_MODEL_TRAINING", "action": "WITHDRAWN",
        "farm_id": farm_id, "reason": "test",
    }, headers=auth)
    assert w.status_code == 200, w.text

    me = await client.get(f"{AUTH}/me", headers=auth)
    assert me.status_code == 200, "철회가 세션을 끊는다면 이 테스트를 갱신하고 이유를 적을 것"


# ── 5. 현재 동작 고정 (개선 대상 — 여기서 고치지 않는다) ────────────────────

async def test_record_does_not_verify_farm_membership(client: AsyncClient, db: AsyncSession):
    """★ 이것은 **바람직한 동작이 아니라 현재 동작**이다.

    `consent_service.record_consents` 는 `farm_id=req.farm_id` 를 그대로 쓴다
    (`api/app/services/consent_service.py:163`). 호출자가 그 농장 소속인지 확인하지
    않는다. 따라서 남의 farm_id 로 자기 동의 행을 남길 수 있다.

    읽기는 user_id 로 걸리므로 남의 동의를 훔쳐보거나 바꾸지는 못한다. 그래도
    원장은 법적 증거물이고, 관계없는 농장에 귀속된 행이 섞이면 증거로서의 값이
    떨어진다.

    여기서 고치지 않는 이유: 권한 경계 변경이다. 어떤 관계를 요구할지
    (farm membership / org 소속 / 둘 다), 기존 행을 어떻게 볼지가 먼저 정해져야
    한다. 지금은 사실만 고정해 두고, 고칠 때 이 테스트가 반드시 함께 바뀌게 한다.

    FOUND_OUT_OF_SCOPE: api/app/services/consent_service.py:163
    """
    _t1, farm_a = await _signup(client)
    token_b, _farm_b = await _signup(client)

    r = await client.post(f"{CONSENT}/record", json=_body(farm_a),
                          headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code == 200, (
        "농장 소속 검증이 추가됐다면 좋은 변화다. 이 테스트를 403 기대로 바꾸고 "
        "LEGAL_P0_MANDATORY_CONSENT_LOGIN_GATE.md 의 관련 기록도 갱신할 것."
    )
    assert await _ledger_count(db, farm_a) > 0
