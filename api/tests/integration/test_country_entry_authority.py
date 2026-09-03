"""LEGAL-P0-CONSENT-AUTHORITY — 국가 진입 판정은 서버가 한다.

## 왜 생겼나 (2026-09-03 실측)

국가 차단이 `POST /consent/record` **안에서만** 걸려 있었다. register·onboarding
경로는 jurisdiction 을 아예 호출하지 않았다.

    → 동의 API 를 호출하지 않는 것만으로 국가 차단까지 우회된다.
    → iOS main 이 실제 반례다. consent 호출 0건인데 가입이 된다.

클라이언트가 법적 권한 경계를 쥐고 있으면 구버전·미배선·악성 클라이언트가 전부
통과한다. 그래서 세 진입점 모두에 서버 판정을 넣었다.

    /auth/register        Web 미사용 · iOS 사용
    /onboarding/complete  Web · Android 사용 (org+user+farm 동시)
    /onboarding/farm      추가 농장

## ★ 이 파일이 검증하지 **않는** 것

가입 자격(eligibility)과 동의 완료(consent completion)는 다르다. 여기서는
국가 hard block 만 본다. ledger row 존재·부속조항 동의·목적별 선택동의는
별도 계층이 맡는다 — register 는 토큰 발급 전이라 인증이 필요한
`/consent/record` 를 요구할 수 없다(순환).
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.core.config import settings
from app.db.models.platform import Farm, Organization, User
from app.services import eligibility

pytestmark = pytest.mark.anyio


def _reg(country: str, **over) -> dict:
    u = uuid.uuid4().hex[:10]
    body = {
        "username": f"u{u}", "email": f"{u}@example.com", "name": "T",
        "password": "Passw0rd!23", "org_name": f"Org {u}",
        "country": country, "language": "en",
    }
    body.update(over)
    return body


def _complete(country: str, **over) -> dict:
    body = _reg(country)
    body.update({"farm_name": f"Farm {body['username']}", "farm_type": "FARROW_TO_FINISH"})
    body.update(over)
    return body


async def _counts(db) -> tuple[int, int, int]:
    return (
        await db.scalar(select(func.count()).select_from(Organization)),
        await db.scalar(select(func.count()).select_from(User)),
        await db.scalar(select(func.count()).select_from(Farm)),
    )


# ── 1·2. hard block 국가 — 첫 DB write 이전에 막힌다 ────────────────────────

async def test_cn_register_is_blocked_and_creates_nothing(client: AsyncClient, db):
    before = await _counts(db)
    r = await client.post("/api/v1/auth/register", json=_reg("CN"))
    assert r.status_code == 451, r.text
    assert "HOLD_D07" in r.text
    assert await _counts(db) == before, "451 인데 org·user 가 생성됐다"


async def test_cn_onboarding_complete_is_blocked_and_creates_nothing(client: AsyncClient, db):
    before = await _counts(db)
    r = await client.post("/api/v1/onboarding/complete", json=_complete("CN"))
    assert r.status_code == 451, r.text
    assert "HOLD_D07" in r.text
    assert await _counts(db) == before, "451 인데 org·user·farm 이 생성됐다"


# ── 3. 허용 국가 — 기존 성공 계약 유지 ─────────────────────────────────────

async def test_allowed_country_onboarding_still_succeeds(client: AsyncClient):
    r = await client.post("/api/v1/onboarding/complete", json=_complete("US"))
    assert r.status_code == 201, r.text
    assert "access_token" in r.json()


async def test_allowed_country_register_still_succeeds(client: AsyncClient):
    r = await client.post("/api/v1/auth/register", json=_reg("US"))
    assert r.status_code == 201, r.text


# ── 4·5. KR override semantics 보존 ────────────────────────────────────────

async def test_kr_is_blocked_when_override_off(client: AsyncClient, db, monkeypatch):
    """conftest 가 테스트 환경에서 allow_kr_signup=True 로 열어둔다.
    운영 기본값(False)에서는 막혀야 한다 — 그 semantics 를 여기서 되돌려 검증한다."""
    monkeypatch.setattr(settings, "allow_kr_signup", False)
    before = await _counts(db)
    r = await client.post("/api/v1/onboarding/complete", json=_complete("KR"))
    assert r.status_code == 451, r.text
    assert "KR_REFERENCE_ONLY" in r.text
    assert await _counts(db) == before


async def test_kr_is_allowed_when_override_on(client: AsyncClient, monkeypatch):
    """대표 확인용 환경(allow_kr_signup=True)에서는 기존대로 통과한다."""
    monkeypatch.setattr(settings, "allow_kr_signup", True)
    r = await client.post("/api/v1/onboarding/complete", json=_complete("KR"))
    assert r.status_code == 201, r.text


def test_override_source_is_shared_not_duplicated():
    """★ override 구성이 두 곳에 있으면 '동의 화면은 막는데 가입은 뚫리는' 상태가 다시 생긴다.

    consent_service 가 자체 dict 를 만들지 않고 파사드를 쓰는지 소스로 확인한다."""
    from pathlib import Path
    src = Path(eligibility.__file__).with_name("consent_service.py").read_text(encoding="utf-8")
    assert '"KR_signup": settings.allow_kr_signup' not in src, (
        "consent_service 가 override 를 자체 구성한다 — eligibility.feature_overrides 를 쓸 것"
    )
    assert "eligibility.resolve_entry" in src


# ── 6·7. 계정 국가 ≠ 농장 국가 ─────────────────────────────────────────────

async def test_us_account_cn_farm_is_blocked(client: AsyncClient, db):
    """CN 은 hard block 이므로 계정이 US 여도 농장 추가가 막힌다."""
    reg = await client.post("/api/v1/onboarding/complete", json=_complete("US"))
    token = reg.json()["access_token"]
    before = await _counts(db)
    r = await client.post(
        "/api/v1/onboarding/farm",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "CN farm", "country": "CN"},
    )
    assert r.status_code == 451, r.text
    assert await _counts(db) == before, "451 인데 farm 이 생성됐다"


async def test_us_account_br_farm_is_allowed_without_consent_completion(client: AsyncClient):
    """★ deadlock 회피.

    BR 은 hard block 이 아니다(release_hold 일 뿐). 이 P0 에서는 BR 부속조항 동의를
    요구하지 않는다 — 요구하면 그 동의를 받을 UI 흐름이 없어 다국가 농장 기능이
    먼저 죽는다. 동의 강제는 UI 준비 후 별도 변수로 넣는다."""
    reg = await client.post("/api/v1/onboarding/complete", json=_complete("US"))
    token = reg.json()["access_token"]
    r = await client.post(
        "/api/v1/onboarding/farm",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "BR farm", "country": "BR"},
    )
    assert r.status_code == 201, r.text


def test_cross_jurisdiction_resolution_is_preserved():
    """계정 국가와 농장 국가를 둘 다 넘겨야 더 엄격한 쪽 채택 + counsel 이 유지된다.

    farm.country 만 넘기면 이 의미가 사라진다."""
    j = eligibility.resolve_entry(selected_country="US", farm_country="BR")
    assert j.counsel_review is True
    assert j.group == "BR", "더 엄격한 쪽(BR)이 채택되어야 한다"

    same = eligibility.resolve_entry(selected_country="US", farm_country="US")
    assert same.counsel_review is False


# ── 8. consent API 를 전혀 부르지 않아도 우회 불가 ──────────────────────────

async def test_blocked_country_cannot_be_bypassed_by_skipping_consent_api(
    client: AsyncClient, db,
):
    """★ 이 P0 의 핵심.

    iOS main 처럼 /consent/* 를 한 번도 호출하지 않는 클라이언트를 흉내 낸다.
    이전에는 이것만으로 국가 차단이 통과됐다."""
    before = await _counts(db)
    for path, body in (
        ("/api/v1/auth/register", _reg("CN")),
        ("/api/v1/onboarding/complete", _complete("CN")),
    ):
        r = await client.post(path, json=body)
        assert r.status_code == 451, f"{path} 가 consent 호출 없이 통과했다: {r.status_code}"
    assert await _counts(db) == before


# ── 9. 진입 경로가 달라도 동일 판정 ────────────────────────────────────────

async def test_all_entry_paths_agree_on_the_same_country(client: AsyncClient):
    """Web(/onboarding/complete) · iOS(/auth/register) 가 같은 국가에 같은 결과를 낸다."""
    a = await client.post("/api/v1/auth/register", json=_reg("CN"))
    b = await client.post("/api/v1/onboarding/complete", json=_complete("CN"))
    assert a.status_code == b.status_code == 451
    assert "HOLD_D07" in a.text and "HOLD_D07" in b.text


# ── 10. 미지원 국가 정책 보존 ───────────────────────────────────────────────

async def test_unsupported_country_policy_is_unchanged(client: AsyncClient):
    """★ 이 RUN 은 미지원국 정책을 바꾸지 않는다.

    MX 는 부속조항이 없지만 hard block 대상이 아니다. 가입 차단 여부는
    레지스트리 스펙 R-3 의 별도 결정이다."""
    j = eligibility.resolve_entry(selected_country="MX", farm_country="MX")
    assert j.group == "OTHER"
    assert j.gate.signup_blocked is False

    r = await client.post("/api/v1/onboarding/complete", json=_complete("MX"))
    assert r.status_code == 201, r.text


def test_facade_does_not_hardcode_countries():
    """국가별 if 하드코딩을 새로 만들지 않았는지 — 기존 jurisdiction service 재사용."""
    from pathlib import Path
    src = Path(eligibility.__file__).read_text(encoding="utf-8")
    code = "\n".join(
        ln for ln in src.split("\n")
        if not ln.lstrip().startswith("#") and not ln.lstrip().startswith('"')
    )
    for token in ('== "CN"', "== 'CN'", '== "KR"', "== 'KR'", '== "BR"', "== 'BR'"):
        assert token not in code, f"eligibility 에 국가 하드코딩이 생겼다: {token}"
