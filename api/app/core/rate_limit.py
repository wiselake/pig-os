"""가입 남용 방지 — 분산 rate limit.

## 왜 필요한가

`/auth/register` · `/onboarding/complete` 에 어떤 속도 제한도 없다(2026-09-11 전수 확인).
가입이 다시 열리는 순간 무제한이다. **스팸 가입은 곧 개인정보 대량 수집**이라 이것은
성능 문제가 아니라 법무 트랙과 같은 축의 문제다.

## 이것이 하지 않는 것 — ★ 인가가 아니다

rate limit 은 **같은 출처가 얼마나 자주 시도하는가**만 본다. 누가 가입할 수 있는가는
`eligibility.assert_country_entry_allowed` 하나가 정한다(B-9). 여기에 국가·법역 판단을
넣지 않는다 — 넣는 순간 가입 허용 판단이 두 군데가 된다.

## 식별자 — 프록시를 어디까지 믿는가

프로덕션은 nginx 뒤에 있고 `nginx.conf` 가 `X-Real-IP: $remote_addr` 를 **덮어쓴다**
(클라이언트가 보낸 값을 통과시키지 않는다). `X-Forwarded-For` 는 설정하지 않는다.

```
신뢰    X-Real-IP   — 우리 nginx 가 매 요청 덮어쓴다
불신    X-Forwarded-For — 아무나 붙일 수 있고 우리 프록시가 만들지 않는다
```

그래서 `X-Forwarded-For` 는 **읽지 않는다**. 헤더가 없으면 소켓 peer 주소를 쓴다.
프록시 구성이 바뀌면 이 모듈의 `client_key` 하나만 고치면 된다.

## 저장소 — Redis, 실패 시 열어둔다

이미 `core/cache.py` 가 Redis 를 쓴다. 같은 인스턴스를 쓰되 키 공간을 분리한다.
API 는 여러 워커로 뜨므로 **프로세스 메모리 카운터는 의미가 없다** — 워커 수만큼
한도가 곱해진다.

★ Redis 가 죽으면 **요청을 통과시킨다**(fail-open). 논쟁의 여지가 있는 선택이라 이유를
적는다: 이 제한은 남용 완화이지 인가가 아니고, 인가는 eligibility 가 별도로 건다.
캐시 장애로 정상 농가의 가입이 전면 중단되는 쪽이 더 나쁘다. 반대로 **eligibility 는
절대 fail-open 하지 않는다** — 그쪽은 실패하면 막는다.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request

from app.core import cache
from app.core.config import settings

log = logging.getLogger(__name__)

_PREFIX = "pigos:rl"


@dataclass(frozen=True)
class Limit:
    """고정 창(fixed window) 한도. `times` 회 / `window_seconds` 초."""
    times: int
    window_seconds: int

    @property
    def name(self) -> str:
        return f"{self.times}/{self.window_seconds}s"


def client_key(request: Request) -> str:
    """요청 출처 식별자. ★ X-Forwarded-For 는 쓰지 않는다 (모듈 docstring 참조)."""
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        # 값 형식만 본다. nginx 가 덮어쓰므로 내용 자체는 신뢰하되, 길이 폭주는 막는다.
        return real_ip.strip()[:45]
    client = request.client
    return client.host if client else "unknown"


async def hit(bucket: str, identity: str, limit: Limit) -> tuple[bool, int]:
    """카운터를 1 올리고 (허용 여부, 남은 초) 를 돌려준다.

    Redis 없음/장애 → `(True, 0)`. 제한을 걸지 못했다는 사실만 로그로 남긴다.
    """
    client = cache._get()
    if client is None:
        return True, 0

    now = int(time.time())
    window_start = now - (now % limit.window_seconds)
    key = f"{_PREFIX}:{bucket}:{identity}:{window_start}"
    try:
        pipe = client.pipeline()
        pipe.incr(key)
        # 창 길이 + 1초. 만료를 매번 걸어도 값은 같아서 창이 밀리지 않는다.
        pipe.expire(key, limit.window_seconds + 1)
        count, _ = await pipe.execute()
    except Exception:
        log.warning("rate_limit: redis 실패 — 이 요청은 제한 없이 통과", exc_info=True)
        return True, 0

    if int(count) > limit.times:
        retry_after = (window_start + limit.window_seconds) - now
        return False, max(retry_after, 1)
    return True, 0


async def enforce(request: Request, bucket: str, limit: Limit) -> None:
    """초과면 429. 기존 에러 계약과 같은 모양(detail 문자열 + 사유 토큰)을 쓴다."""
    allowed, retry_after = await hit(bucket, client_key(request), limit)
    if allowed:
        return
    raise HTTPException(
        status_code=429,
        detail=f"RATE_LIMITED:{bucket}",
        headers={"Retry-After": str(retry_after)},
    )


def limiter(bucket: str, limit_getter):
    """FastAPI 의존성 팩토리.

    ★ 한도를 인자로 받지 않고 **호출 시점에 조회**한다 — 설정을 런타임에 바꾸거나
      테스트에서 monkeypatch 할 때 import 시점에 굳은 값이 남지 않게 한다.
    """
    async def _dep(request: Request) -> None:
        limit = limit_getter()
        if limit.times <= 0:      # 0 이하 = 비활성 (개발·테스트)
            return
        await enforce(request, bucket, limit)
    return _dep


# ── 버킷 정의 ─────────────────────────────────────────────────────────────────
#
# ★ 값을 코드에 흩뿌리지 않는다. 전부 settings 에서 오고 env 로 덮을 수 있다.
#   기본값 근거는 docs/runs/RATE_LIMIT_POLICY.md — 정상 농가가 막히지 않는 선.

def signup_limit() -> Limit:
    return Limit(settings.rate_limit_signup_per_hour, 3600)


def auth_limit() -> Limit:
    return Limit(settings.rate_limit_auth_per_minute, 60)


require_signup_quota = limiter("signup", signup_limit)
require_auth_quota = limiter("auth", auth_limit)
