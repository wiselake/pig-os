"""가입·인증 rate limit — 남용 방지가 실제로 동작하는가, 그리고 **인가를 대신하지 않는가**.

근거·기본값: `docs/runs/RATE_LIMIT_POLICY.md`

★ 이 파일이 지키는 경계 두 개
    1  한도를 넘으면 429 + Retry-After
    2  ★ rate limit 은 eligibility 를 대신하지 않는다 — 한도 안이어도 차단 법역은 451
       (B-9: 가입 허용 판단의 단일 진입점은 eligibility 하나다)
"""
import uuid

import pytest
from httpx import AsyncClient

from app.core import rate_limit as rl

pytestmark = [pytest.mark.anyio, pytest.mark.real_rate_limit]

PW = "Test1234!"


class _FakeRedis:
    """인메모리 대역 — 테스트가 실제 Redis 상태에 의존하지 않게.

    ★ 파이프라인만 흉내 낸다. 진짜 Redis 의 의미를 재현하려는 것이 아니라
      limiter 의 카운팅·만료 호출이 맞는지만 본다.
    """

    def __init__(self):
        self.store: dict[str, int] = {}
        self.expires: dict[str, int] = {}
        self.fail = False

    def pipeline(self):
        outer = self

        class _P:
            def __init__(self):
                self.ops = []

            def incr(self, key):
                self.ops.append(("incr", key))

            def expire(self, key, ttl):
                self.ops.append(("expire", key, ttl))

            async def execute(self):
                if outer.fail:
                    raise ConnectionError("redis down (simulated)")
                out = []
                for op in self.ops:
                    if op[0] == "incr":
                        outer.store[op[1]] = outer.store.get(op[1], 0) + 1
                        out.append(outer.store[op[1]])
                    else:
                        outer.expires[op[1]] = op[2]
                        out.append(True)
                return out

        return _P()


@pytest.fixture
def fake_redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr("app.core.cache._get", lambda: fake)
    return fake


@pytest.fixture
def signup_limit(monkeypatch):
    """한도를 테스트에서 정한다 — 운영 기본값(5/시간)에 테스트를 묶지 않는다.

    ★ 실제 설정 경로를 패치한다. `rl.signup_limit` 을 갈아끼우면 `require_signup_quota`
      가 import 시점에 붙잡은 참조는 그대로라 아무 일도 일어나지 않는다 — 그렇게 쓰면
      테스트는 초록인데 운영에서는 값이 안 바뀌는 상태를 못 잡는다.
    """
    from app.core.config import settings

    def _set(times: int, window: int = 3600):
        monkeypatch.setattr(settings, "rate_limit_signup_per_hour", times)
        if window != 3600:
            monkeypatch.setattr(rl, "signup_limit", lambda: rl.Limit(times, window))
    return _set


def _reg_body(country: str = "US") -> dict:
    tag = uuid.uuid4().hex[:8]
    return {
        "name": "RL", "username": f"rl{tag}", "email": f"rl{tag}@example.com",
        "password": PW, "org_name": f"Org {tag}", "country": country, "language": "en",
    }


# ── 1. 한도 초과 → 429 ────────────────────────────────────────────────────────

async def test_register_burst_is_throttled(client: AsyncClient, fake_redis, signup_limit):
    signup_limit(2)
    codes = [(await client.post("/api/v1/auth/register", json=_reg_body())).status_code
             for _ in range(4)]
    assert codes[:2] == [201, 201], codes
    assert codes[2:] == [429, 429], codes


async def test_429_carries_retry_after_and_a_reason(client: AsyncClient, fake_redis, signup_limit):
    signup_limit(1)
    await client.post("/api/v1/auth/register", json=_reg_body())
    r = await client.post("/api/v1/auth/register", json=_reg_body())
    assert r.status_code == 429
    assert "RATE_LIMITED:signup" in r.text
    retry = r.headers.get("retry-after")
    assert retry and retry.isdigit() and int(retry) > 0, r.headers


async def test_onboarding_complete_shares_the_signup_bucket(
    client: AsyncClient, fake_redis, signup_limit,
):
    """두 경로가 같은 버킷을 쓴다 — 한쪽이 막히면 다른 쪽으로 이어가지 못한다.

    ★ 진입점이 둘인데 버킷이 둘이면 한도가 2배가 된다. H11 이 가르쳐준 모양과 같다:
      가입 경로가 하나라고 가정하지 않는다.
    """
    signup_limit(1)
    body = _reg_body()
    assert (await client.post("/api/v1/auth/register", json=body)).status_code == 201
    ob = _reg_body()
    ob.update({"farm_name": "F", "farm_type": "FARROW_TO_FINISH"})
    r = await client.post("/api/v1/onboarding/complete", json=ob)
    assert r.status_code == 429, r.text


# ── 2. 창·식별자 분리 ─────────────────────────────────────────────────────────

async def test_window_expiry_restores_quota(client: AsyncClient, fake_redis, signup_limit):
    """창이 지나면 다시 열린다. 영구 차단이 아니다."""
    signup_limit(1)
    assert (await client.post("/api/v1/auth/register", json=_reg_body())).status_code == 201
    assert (await client.post("/api/v1/auth/register", json=_reg_body())).status_code == 429
    # 창 경계가 넘어간 것과 같게 — 키가 창 시작 시각을 포함하므로 저장소를 비우면 동일하다
    fake_redis.store.clear()
    assert (await client.post("/api/v1/auth/register", json=_reg_body())).status_code == 201


async def test_different_sources_are_counted_separately(
    client: AsyncClient, fake_redis, signup_limit,
):
    signup_limit(1)
    h1 = {"X-Real-IP": "203.0.113.10"}
    h2 = {"X-Real-IP": "203.0.113.11"}
    assert (await client.post("/api/v1/auth/register", json=_reg_body(), headers=h1)).status_code == 201
    assert (await client.post("/api/v1/auth/register", json=_reg_body(), headers=h1)).status_code == 429
    # 다른 출처는 자기 몫이 남아 있다
    assert (await client.post("/api/v1/auth/register", json=_reg_body(), headers=h2)).status_code == 201


async def test_x_forwarded_for_cannot_reset_the_counter(
    client: AsyncClient, fake_redis, signup_limit,
):
    """★ 우회 시도. 우리 nginx 는 X-Forwarded-For 를 만들지 않으므로 신뢰하지 않는다.

    이 헤더를 식별자로 쓰면 공격자가 매 요청 다른 값을 넣어 한도를 무한히 늘린다.
    """
    signup_limit(1)
    base = {"X-Real-IP": "203.0.113.20"}
    assert (await client.post("/api/v1/auth/register", json=_reg_body(), headers=base)).status_code == 201
    for spoof in ("198.51.100.1", "198.51.100.2", "198.51.100.3"):
        r = await client.post(
            "/api/v1/auth/register", json=_reg_body(),
            headers={**base, "X-Forwarded-For": spoof},
        )
        assert r.status_code == 429, f"X-Forwarded-For={spoof} 로 한도가 초기화됐다"


# ── 3. Redis 장애 의미론 ──────────────────────────────────────────────────────

async def test_redis_failure_fails_open_for_the_limiter(
    client: AsyncClient, fake_redis, signup_limit,
):
    """제한기는 통과시킨다 — 캐시 장애로 정상 가입이 전면 중단되면 안 된다."""
    signup_limit(1)
    fake_redis.fail = True
    for _ in range(3):
        r = await client.post("/api/v1/auth/register", json=_reg_body())
        assert r.status_code == 201, r.text


async def test_redis_absent_fails_open(client: AsyncClient, monkeypatch, signup_limit):
    monkeypatch.setattr("app.core.cache._get", lambda: None)
    signup_limit(1)
    for _ in range(3):
        assert (await client.post("/api/v1/auth/register", json=_reg_body())).status_code == 201


# ── 4. ★ 인가 경계 — 가장 중요한 절 ───────────────────────────────────────────

async def test_rate_limit_does_not_replace_eligibility(
    client: AsyncClient, fake_redis, signup_limit, monkeypatch,
):
    """한도 안이어도 차단 법역은 451 이다.

    두 계층의 순서·역할이 섞이면 "제한에 안 걸렸으니 통과" 가 되어 국가 차단이 무너진다.
    """
    from app.core.config import settings
    monkeypatch.setattr(settings, "allow_kr_signup", False)
    signup_limit(100)          # 넉넉히 — rate limit 은 이 테스트에서 발동하지 않는다
    r = await client.post("/api/v1/auth/register", json=_reg_body("KR"))
    assert r.status_code == 451, r.text
    assert "KR_REFERENCE_ONLY" in r.text


async def test_eligibility_still_blocks_when_redis_is_down(
    client: AsyncClient, fake_redis, monkeypatch,
):
    """★ 두 계층의 실패 방향이 반대다.

    Redis 가 죽어 제한기가 fail-open 해도 eligibility 는 그대로 막는다.
    이것이 깨지면 캐시 장애가 곧 국가 게이트 우회가 된다.
    """
    from app.core.config import settings
    monkeypatch.setattr(settings, "allow_kr_signup", False)
    fake_redis.fail = True
    r = await client.post("/api/v1/auth/register", json=_reg_body("KR"))
    assert r.status_code == 451, r.text


async def test_limiter_is_disabled_at_zero(client: AsyncClient, fake_redis, signup_limit):
    """0 이하 = 비활성. 개발·테스트 기본값이며 Redis 를 건드리지도 않는다."""
    signup_limit(0)
    for _ in range(3):
        assert (await client.post("/api/v1/auth/register", json=_reg_body())).status_code == 201
    assert not fake_redis.store, "비활성인데 카운터를 기록했다"
