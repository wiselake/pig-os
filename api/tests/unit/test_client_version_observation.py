"""클라이언트 버전 관측 — 관측만 하고 강제하지 않는다는 것을 잠근다.

배경: 세 surface 중 헤더를 보내는 곳이 하나도 없었다(2026-08-28 실측).
      이 상태에서 missing-version fail-closed 를 켜면 정상 클라이언트가 전부 막힌다.
      docs/product/PIGOS_PRODUCT_IMPLEMENTATION_HANDOFF.md §12-1
"""
from __future__ import annotations

import inspect

from starlette.datastructures import Headers

from app.core import client_version as cv


def _h(**kw) -> Headers:
    return Headers({k.replace("_", "-"): v for k, v in kw.items()})


# ── 정상 케이스 ───────────────────────────────────────────────────────────────

def test_parses_known_platform_and_version():
    out = cv.parse(_h(**{"X-PigOS-Platform": "android", "X-PigOS-App-Version": "1.4.2"}))
    assert out.platform == "android"
    assert out.app_version == "1.4.2"
    assert out.complete and out.reported


def test_platform_is_case_insensitive():
    out = cv.parse(Headers({"x-pigos-platform": "IOS", "x-pigos-app-version": "2.0"}))
    assert out.platform == "ios"


# ── 없거나 이상해도 예외를 던지지 않는다 ──────────────────────────────────────

def test_missing_headers_are_not_an_error():
    out = cv.parse(Headers({}))
    assert out.platform is None and out.app_version is None
    assert not out.reported and not out.complete


def test_unknown_platform_is_dropped_not_raised():
    out = cv.parse(Headers({"x-pigos-platform": "windows-phone"}))
    assert out.platform is None


def test_malformed_version_is_dropped_not_raised():
    out = cv.parse(Headers({"x-pigos-app-version": "1.0; DROP TABLE farms"}))
    assert out.app_version is None


def test_partial_report_is_reported_but_not_complete():
    out = cv.parse(Headers({"x-pigos-platform": "web"}))
    assert out.reported and not out.complete


# ── ★ 강제하지 않는다 (구조 가드) ─────────────────────────────────────────────

def test_module_does_not_reject_requests():
    """parse 가 예외를 던지거나 응답을 만들지 않는지 — 관측 전용임을 잠근다."""
    src = inspect.getsource(cv)
    for forbidden in ("raise ", "HTTPException", "status_code", "JSONResponse"):
        assert forbidden not in src, (
            f"client_version 모듈에 '{forbidden}' 이 생겼다. "
            "이 모듈은 관측 전용이며 차단은 별도 활성화 단계다(HANDOFF §12-1)."
        )


def test_middleware_does_not_branch_on_version():
    """main.py 의 미들웨어가 버전으로 분기하지 않는지."""
    import app.main as m

    src = inspect.getsource(m._observe_client_version)
    assert "return await call_next(request)" in src
    for forbidden in ("if ", "raise ", "status_code"):
        assert forbidden not in src, (
            "버전 관측 미들웨어가 분기·차단을 시작했다. "
            "세 surface 송출·관측 확인 전에는 강제하지 않는다."
        )
