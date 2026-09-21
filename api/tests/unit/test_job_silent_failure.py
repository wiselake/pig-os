"""배경 잡이 **전건 실패를 성공이라고 말하지 못하게** — 회귀 고정.

## 재현하는 사고 (2026-08-28 런타임 감사)

```
로그    'daily KPI done: 0 farms, 71 errors'
ARQ     j_failed = 0        ← 성공으로 기록
결과    kpi_snapshots 가 2026-05-29 이래 0행인데 아무도 몰랐다
```

잡이 문자열을 반환하는 한 스케줄러는 성공으로 본다. `_result.job_result` 가 그 경로를
막지만, **같은 모양이 한 층 아래에 또 있었다** — 아래 §3 (push 전송).

★ 이 파일은 "부분 실패면 무조건 크래시" 를 요구하지 않는다. 한 농장 실패가 나머지를
  막으면 안 된다는 격리 원칙은 그대로다. 요구하는 것은 하나: **대상이 있었는데 하나도
  성공하지 못했으면 성공으로 끝내지 않는다.**
"""
import logging

import pytest

from app.jobs._result import JobTotalFailure, job_result
from app.services.push_service import PushResult

# ── 1. job_result 의 네 경우 ──────────────────────────────────────────────────

def test_all_fail_raises():
    """★ 사고 재현: 71개 대상, 0개 성공, 71 에러."""
    with pytest.raises(JobTotalFailure) as ei:
        job_result("daily_kpi_aggregation", expected=71, success=0, errors=71)
    msg = str(ei.value)
    assert "TOTAL FAILURE" in msg
    assert "0/71" in msg and "71 errors" in msg


def test_some_fail_is_partial_not_silent():
    out = job_result("job", expected=10, success=7, errors=3)
    assert "PARTIAL" in out and "7/10" in out and "3 errors" in out


def test_all_succeed_is_ok():
    out = job_result("job", expected=10, success=10)
    assert out.startswith("job: OK") and "10/10" in out


def test_nothing_to_do_is_success_not_failure():
    """대상이 0 이면 성공이다 — '할 일이 없었다' 와 '전부 실패했다' 는 다르다.

    weekly/monthly 가 errors 를 세지 않아 둘을 구분할 수 없던 것이 사고의 절반이었다.
    """
    out = job_result("job", expected=0, success=0)
    assert "OK" in out
    assert "TOTAL FAILURE" not in out


def test_one_success_among_many_failures_is_not_total_failure():
    """경계: 1건이라도 성공했으면 raise 하지 않는다. 격리 원칙을 깨지 않는다."""
    out = job_result("job", expected=71, success=1, errors=70)
    assert "PARTIAL" in out


def test_total_failure_is_logged_at_error_level(caplog):
    """스케줄러가 예외를 삼켜도 로그에는 남아야 한다."""
    with caplog.at_level(logging.ERROR), pytest.raises(JobTotalFailure):
        job_result("job", expected=5, success=0, errors=5)
    assert any("TOTAL FAILURE" in r.message % r.args if r.args else "TOTAL FAILURE" in r.message
               for r in caplog.records)


# ── 2. 예외 종류가 스케줄러에 실패로 보이는가 ────────────────────────────────

def test_job_total_failure_is_an_exception_not_a_return_value():
    """★ 문자열을 반환하면 ARQ 는 성공으로 본다. 그래서 반환이 아니라 raise 여야 한다."""
    assert issubclass(JobTotalFailure, Exception)


# ── 3. ★ 한 층 아래 — 푸시 전송에도 같은 모양이 있었다 ───────────────────────
#
# 이전 구현: PushResult(sent=sent, skipped=len(tokens) - sent)
#   → FCM 이 전건 거절해도 failed 가 없으니 "건너뛴 것" 으로 집계되고,
#     호출부는 res.sent 만 보므로 잡 결과가 "OK — 71/71 processed, 0 pushed" 가 된다.
#   → 푸시가 완전히 죽어도 잡은 계속 초록이다.

def test_push_result_separates_failure_from_skip():
    r = PushResult(sent=0, skipped=0, failed=3)
    assert r.failed == 3
    assert r.attempted == 3


def test_push_skip_is_not_failure():
    """미설정·토큰 없음은 실패가 아니다 — 이것까지 실패로 세면 경보가 무뎌진다."""
    r = PushResult(sent=0, skipped=5, reason="fcm_not_configured")
    assert r.failed == 0
    assert r.attempted == 0


def test_push_counts_do_not_overlap():
    """sent + failed + skipped 가 대상 수를 넘지 않는다 — 겹치면 집계가 거짓말을 한다."""
    tokens = 10
    r = PushResult(sent=4, failed=3, skipped=tokens - 4 - 3)
    assert r.sent + r.failed + r.skipped == tokens


@pytest.mark.parametrize("sent,failed,expect_alarm", [
    (0, 0, False),   # 보낼 것이 없었다
    (5, 0, False),   # 전부 성공
    (3, 2, True),    # 부분 실패 — 보여야 한다
    (0, 5, True),    # ★ 전건 실패 — 절대 숨으면 안 된다
])
def test_failure_is_visible_whenever_it_is_nonzero(sent, failed, expect_alarm):
    r = PushResult(sent=sent, skipped=0, failed=failed)
    assert (r.failed > 0) is expect_alarm
