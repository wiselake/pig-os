"""잡이 raise 하면 **ARQ 관측 계층까지** 실패로 전파되는지 확인한다.

★ 왜 이 테스트가 따로 필요한가 (2026-08-31)

  원래 사고는 "함수가 틀린 값을 냈다" 가 아니라 **"관측 계층이 거짓말했다"** 였다.
  daily_kpi_aggregation 이 71농장 전건 실패하면서도 ARQ 에는 성공(●)으로 끝났고,
  `j_failed=0` 이었다. 그래서 3개월간 아무도 몰랐다.

  `2e372b1` 은 함수가 성공 문자열 대신 `JobTotalFailure` 를 raise 하도록 고쳤다.
  순수함수 수준은 프로덕션에서 확인했다. **그러나 남은 질문은 하나 더 있다:**

      함수 raise  →  task exception  →  ARQ job status
                                        여기까지 실제로 전파되는가?

  이것이 확인돼야 사고가 닫힌다.

★ 왜 프로덕션 자연 실행으로는 확인할 수 없는가

  수정 후 daily_kpi_aggregation 은 **성공한다**(크래시 원인이 제거됐으므로).
  즉 자연 실행은 `OK — 71/71` 을 낼 뿐 실패 경로를 밟지 않는다.
  그리고 확인을 위해 프로덕션에 의도적 실패를 만드는 것은 금지돼 있다.

  → 그래서 로컬에서 닫는다. 프로덕션 무접촉.

  근거: docs/PLATFORM_PARITY.md §9-4 · docs/runs/RUNTIME_INTEGRITY_AUDIT_20260828.md §A1
"""
from __future__ import annotations

import uuid

import pytest
from arq.connections import RedisSettings, create_pool
from arq.worker import Worker

from app.core.config import settings
from app.jobs._result import JobTotalFailure, job_result

pytestmark = pytest.mark.asyncio


# ── 대상 잡 3종 (실제 잡 로직이 아니라 **결과 semantics** 를 그대로 재현) ──────────

async def _job_total_failure(ctx: dict) -> str:
    """전건 실패 — 실제 잡이 71농장 전부 실패했을 때와 같은 호출."""
    return job_result("probe_total", expected=71, success=0, errors=71)


async def _job_partial(ctx: dict) -> str:
    return job_result("probe_partial", expected=10, success=7, errors=3)


async def _job_ok(ctx: dict) -> str:
    return job_result("probe_ok", expected=5, success=5)


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


async def _run_one(fn, *, max_tries: int = 1):
    """잡 하나를 enqueue 하고 burst 워커로 소진시킨 뒤 (complete, failed, retried) 반환."""
    queue = f"arq:test:{uuid.uuid4().hex[:12]}"
    pool = await create_pool(_redis_settings(), default_queue_name=queue)
    try:
        await pool.enqueue_job(fn.__name__)
        worker = Worker(
            functions=[fn],
            redis_settings=_redis_settings(),
            queue_name=queue,
            burst=True,
            max_tries=max_tries,
            poll_delay=0.05,
            handle_signals=False,
        )
        try:
            await worker.main()
            return worker.jobs_complete, worker.jobs_failed, worker.jobs_retried
        finally:
            # arq 0.28 의 Worker.close() 는 handle_sig(signal.SIGUSR1) 을 호출하는데
            # SIGUSR1 은 POSIX 전용이라 Windows 개발 머신에서 AttributeError 가 난다.
            # 잡 실행 자체와 무관한 teardown 이므로 여기서만 흡수한다.
            # (CI 는 ubuntu 라 정상 close 된다)
            try:
                await worker.close()
            except AttributeError as e:            # pragma: no cover - platform specific
                if "SIGUSR1" not in str(e):
                    raise
    finally:
        await pool.aclose()


# ── ★ 핵심: 전건 실패가 ARQ 에 실패로 잡히는가 ────────────────────────────────

async def test_total_failure_propagates_to_arq_job_status():
    """이것이 원래 사고의 재발 방지선이다.

    예전 코드였다면 성공 문자열을 반환해 jobs_complete=1 / jobs_failed=0 이 됐다.
    지금은 raise 하므로 ARQ 가 실패로 집계해야 한다.
    """
    complete, failed, _retried = await _run_one(_job_total_failure)

    assert failed == 1, (
        f"전건 실패인데 ARQ 가 실패로 집계하지 않았다 (failed={failed}). "
        "관측 계층이 다시 거짓말하고 있다 — 이것이 원래 사고다."
    )
    assert complete == 0, (
        f"전건 실패인데 jobs_complete={complete}. 성공으로 끝나면 안 된다."
    )


async def test_total_failure_preserves_reason():
    """traceback/메시지에 실제 실패 원인이 남는가."""
    with pytest.raises(JobTotalFailure) as ei:
        job_result("probe_total", expected=71, success=0, errors=71)
    msg = str(ei.value)
    assert "TOTAL FAILURE" in msg
    assert "0/71" in msg and "71 errors" in msg


# ── 대조군: 성공/부분실패는 ARQ 에서 실패가 아니다 ───────────────────────────

async def test_ok_job_is_complete_not_failed():
    complete, failed, _ = await _run_one(_job_ok)
    assert complete == 1 and failed == 0


async def test_partial_is_complete_but_labelled():
    """부분 실패는 ARQ 잡 자체를 실패시키지 않는다(재시도 폭주 방지).
    대신 결과 문자열에 PARTIAL 과 실제 errors 가 남아야 한다."""
    complete, failed, _ = await _run_one(_job_partial)
    assert complete == 1 and failed == 0

    out = job_result("probe_partial", expected=10, success=7, errors=3)
    assert "PARTIAL" in out and "3 errors" in out


# ── 재시도 정책 — ★ 실측으로 정정된 이해 ────────────────────────────────────

async def test_plain_exception_fails_immediately_without_retry():
    """일반 예외는 **재시도되지 않고 즉시 실패**로 끝난다.

    ★ 정정 기록 (2026-08-31)
      처음에 "운영 max_tries 가 arq 기본값 5 이므로 전건 실패 시 5회 재시도된다"
      고 판단했다. **틀렸다.**

      arq worker.py:612-634 실측:
        Retry 예외                    → jobs_retried
        CancelledError / RetryJob     → jobs_retried
        그 외 일반 예외(우리 경우)     → logger.exception + finish=True + jobs_failed

      즉 `max_tries` 는 **Retry 로 유발된 재시도만** 제한한다.
      JobTotalFailure 같은 일반 예외는 한 번에 실패로 종료된다.

      결과적으로 더 낫다 — 매일 실패하는 cron 이 재시도 폭주를 일으키지 않는다.
    """
    complete, failed, retried = await _run_one(_job_total_failure, max_tries=3)
    assert failed == 1, f"실패로 집계돼야 한다 (failed={failed})"
    assert complete == 0, "성공으로 끝나면 안 된다"
    assert retried == 0, (
        f"일반 예외는 재시도 대상이 아니다 (retried={retried}). "
        "이 값이 올라갔다면 arq 의 예외 분기가 바뀐 것이므로 재확인이 필요하다."
    )
