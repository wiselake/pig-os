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

★ 마지막 절은 farm_id 귀속 권한(LEGAL-P0-CONSENT-FARM-AUTHORITY)이다.
  2026-09-03 까지 여기에는 `characterization_known_defect_...` 라는 이름의
  **결함 재현** 테스트가 있었다. 결함이 닫히면서 예고대로 정상 계약으로
  교체됐다 — 이제 전부 "이렇게 동작해야 한다"이다.
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


# ── 5. farm_id 귀속 권한 (LEGAL-P0-CONSENT-FARM-AUTHORITY) ─────────────────
#
# 동의 원장은 "누가 · 어느 농장에 대해 · 무엇에 동의했는가" 의 법적 증거물이다.
# 귀속 농장이 틀린 행이 섞이면 그 원장으로는 아무것도 증명하지 못한다.
#
# 판정은 **새 법무 전용 규칙을 만들지 않고** farm-scoped API 의 canonical access
# semantics(`app/core/permissions.can_access_farm`)를 그대로 재사용한다.
# 실패 semantics 도 `get_farm_context` 와 동일하게 403 이다 — 그 dependency 는
# 없는 농장·비활성 농장·접근 불가 농장을 모두 ForbiddenError(403)로 처리하며
# 404 로 존재를 숨기지 않는다.

async def test_record_rejects_foreign_farm_id(client: AsyncClient, db: AsyncSession):
    """★ 이 P0 의 핵심. 남의 farm_id 로는 원장에 한 줄도 남기지 못한다."""
    _t1, farm_a = await _signup(client)
    token_b, _farm_b = await _signup(client)

    r = await client.post(f"{CONSENT}/record", json=_body(farm_a),
                          headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code == 403, r.text
    assert await _ledger_count(db, farm_a) == 0, "거부됐는데 원장에 행이 남았다"


async def test_record_accepts_own_farm_id(client: AsyncClient, db: AsyncSession):
    """★ 회귀 방지. 방금 만든 자기 농장은 반드시 통과해야 한다.

    여기서 403 이 나면 LEGAL-P0-WEB-CONSENT-FAIL-CLOSED 때문에 **정상 가입이
    전부 막힌다**(record 성공이 로그인 확정 조건이다). 권한을 조인 이 테스트가
    그 폭발을 잡는다."""
    token, farm_id = await _signup(client)
    r = await client.post(f"{CONSENT}/record", json=_body(farm_id),
                          headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert await _ledger_count(db, farm_id) > 0


async def test_record_allows_null_farm_id_and_writes_null(
    client: AsyncClient, db: AsyncSession,
):
    """farm_id 없음 = 계정 스코프. 검증 대상이 아니며, 실제로 NULL 로 저장된다.

    ★ 200 만 확인하면 부족하다 — 그러면 서버가 farm_id 를 어딘가에서 채워 넣어도
      통과한다. 기록된 행의 farm_id 가 정말 NULL 인지 본다.

    ※ 현재는 **모든** 가시 목적이 NULL 로 기록된다. 모델 주석
      (`db/models/consent.py`)은 farm 단위 목적(②③④⑤)에 farm_id 가 필수라고
      적고 있어 서로 어긋난다. 이 P0 는 그 불일치를 해소하지 않는다 —
      아래 assert 는 "옳다"가 아니라 **현재 이렇다**를 고정한 것이고,
      LEGAL-P0-CONSENT-EVIDENCE 에서 다뤄야 한다.
    """
    token, _farm_id = await _signup(client)
    body = _body("")
    body["farm_id"] = None
    r = await client.post(f"{CONSENT}/record", json=body,
                          headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text

    written = (await db.execute(
        select(ConsentRecord.farm_id).where(ConsentRecord.notice_version.isnot(None))
        .order_by(ConsentRecord.created_at.desc()).limit(len(r.json()))
    )).scalars().all()
    assert written and all(f is None for f in written), f"farm_id 가 NULL 이 아니다: {written}"


async def test_withdraw_rejects_foreign_farm_id(client: AsyncClient):
    """record 만 막으면 withdraw 로 같은 일을 할 수 있다 — 두 경로 다 막는다."""
    token_a, farm_a = await _signup(client)
    auth_a = {"Authorization": f"Bearer {token_a}"}
    await client.post(f"{CONSENT}/record", json=_body(farm_a, choices=[
        {"purpose_code": "AI_MODEL_TRAINING", "granted": True},
    ]), headers=auth_a)

    token_b, _farm_b = await _signup(client)
    r = await client.post(f"{CONSENT}/withdraw", json={
        "purpose_code": "AI_MODEL_TRAINING", "action": "WITHDRAWN", "farm_id": farm_a,
    }, headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code == 403, r.text


async def test_withdraw_without_farm_id_inherits_the_prior_rows_farm(
    client: AsyncClient, db: AsyncSession,
):
    """farm_id 를 생략한 철회는 **직전 행의 farm_id 를 상속**한다.

    ★ 이 테스트의 이전 이름은 `..._keeps_account_scope` 였고 200 만 확인했다.
      그런데 직전 행이 farm-scoped 였으므로 새 행도 그 농장에 귀속된다 —
      이름이 주장하는 것과 정반대였다. 무엇이 기록되는지까지 확인한다.

    상속 자체는 정상이다(자기 농장이다). 무검증 상속이 문제였고 그건 아래
    `test_withdraw_cannot_launder_inaccessible_farm_via_null` 이 막는다."""
    token, farm_id = await _signup(client)
    auth = {"Authorization": f"Bearer {token}"}
    await client.post(f"{CONSENT}/record", json=_body(farm_id, choices=[
        {"purpose_code": "AI_MODEL_TRAINING", "granted": True},
    ]), headers=auth)

    r = await client.post(f"{CONSENT}/withdraw", json={
        "purpose_code": "AI_MODEL_TRAINING", "action": "WITHDRAWN",
    }, headers=auth)
    assert r.status_code == 200, r.text

    latest = (await db.execute(
        select(ConsentRecord)
        .where(ConsentRecord.purpose_code == "AI_MODEL_TRAINING",
               ConsentRecord.consent_status == "WITHDRAWN")
        .order_by(ConsentRecord.created_at.desc()).limit(1)
    )).scalars().first()
    assert latest is not None
    assert str(latest.farm_id) == farm_id, "상속된 farm_id 가 직전 행과 다르다"
