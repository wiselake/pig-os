"""클라이언트 platform / app version 관측 — **송출·수신만. 강제하지 않는다.**

★ 순서를 지키는 것이 이 모듈의 전부다.

  1. Web / Android / iOS 가 헤더를 보낸다
  2. 서버가 받아서 관측한다            ← 이 모듈
  3. 세 surface 에서 실제로 들어오는지 확인한다
  4. 그 다음에야 missing-version = LEGACY fail-closed 를 켠다

  ★★ 3번 없이 4번을 켜면 **정상 클라이언트가 전부 차단된다.**
     지금 세 surface 중 헤더를 보내는 곳이 하나도 없기 때문이다(2026-08-28 실측).
     그래서 이 모듈은 값을 읽어 request.state 에 담고 로그만 남긴다.
     차단·분기·거부를 하지 않는다.

  근거: docs/product/PIGOS_PRODUCT_IMPLEMENTATION_HANDOFF.md §12-1
        docs/PLATFORM_PARITY.md §9-1 B-5
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

log = logging.getLogger(__name__)

HEADER_PLATFORM = "X-PigOS-Platform"
HEADER_APP_VERSION = "X-PigOS-App-Version"

KNOWN_PLATFORMS = frozenset({"web", "android", "ios"})

# 느슨하게 받는다. 지금 목적은 검증이 아니라 관측이다.
# 엄격한 semver 강제는 실제로 무엇이 들어오는지 본 다음에 정한다.
_VERSION_RE = re.compile(r"^[0-9A-Za-z.\-+]{1,32}$")


@dataclass(frozen=True)
class ClientVersion:
    """요청이 스스로 밝힌 클라이언트 신원. 신뢰 경계 밖 값이다.

    ★ 인증·권한 판정에 쓰지 않는다. 클라이언트가 마음대로 보낼 수 있는 값이다.
      용도는 rollout 관측과 legacy 분포 파악뿐이다.
    """

    platform: str | None
    app_version: str | None

    @property
    def reported(self) -> bool:
        """헤더를 보내기는 했는가. (값의 유효성과 별개)"""
        return self.platform is not None or self.app_version is not None

    @property
    def complete(self) -> bool:
        """platform·version 둘 다 정상적으로 왔는가."""
        return self.platform is not None and self.app_version is not None


def parse(headers) -> ClientVersion:
    """헤더에서 클라이언트 신원을 읽는다. 예외를 던지지 않는다.

    headers 는 대소문자 무관 매핑(Starlette Headers 등)을 가정한다.
    """
    raw_platform = (headers.get(HEADER_PLATFORM) or "").strip().lower()
    raw_version = (headers.get(HEADER_APP_VERSION) or "").strip()

    platform = raw_platform if raw_platform in KNOWN_PLATFORMS else None
    version = raw_version if _VERSION_RE.match(raw_version) else None

    # 값은 왔는데 형식이 어긋난 경우는 조용히 버리지 않는다 — 계약 불일치의 신호다.
    if raw_platform and platform is None:
        log.info("client_version: unknown platform=%r", raw_platform[:32])
    if raw_version and version is None:
        log.info("client_version: malformed app_version=%r", raw_version[:32])

    return ClientVersion(platform=platform, app_version=version)
