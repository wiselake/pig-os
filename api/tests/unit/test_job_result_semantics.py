"""ARQ 잡이 item-level 실패를 job-level 성공으로 둔갑시키지 않는지 잠근다.

배경: 2026-08-28 런타임 감사에서 daily_kpi_aggregation 이 71농장 **전건 실패**하면서
      ARQ 에 성공(●)으로 끝나는 것이 확인됐다. weekly/monthly 는 errors 를 세지도
      않아 '0 farms' 가 "할 일이 없었다" 와 구분되지 않았다.
      근거: docs/runs/RUNTIME_INTEGRITY_AUDIT_20260828.md §A1

이 테스트는 산식이 아니라 **보고 규약**을 잠근다.
"""
from __future__ import annotations

import inspect

import pytest

from app.jobs import kpi as kpi_job
from app.jobs import notifications as notif_job
from app.jobs import tasks as tasks_job
from app.jobs._result import JobTotalFailure, job_result


# ── job_result 규약 ───────────────────────────────────────────────────────────

def test_total_failure_raises_not_returns():
    """대상이 있었는데 하나도 처리 못 했으면 성공 문자열을 돌려주지 않는다."""
    with pytest.raises(JobTotalFailure) as ei:
        job_result("j", expected=71, success=0, errors=71)
    assert "TOTAL FAILURE" in str(ei.value)
    assert "0/71" in str(ei.value)


def test_partial_is_labelled_partial():
    out = job_result("j", expected=10, success=7, errors=3)
    assert out.startswith("j: PARTIAL")
    assert "7/10" in out and "3 errors" in out


def test_clean_run_is_ok():
    out = job_result("j", expected=5, success=5)
    assert out.startswith("j: OK")


def test_nothing_to_do_is_not_a_failure():
    """expected=0 은 '할 일이 없었다' 이지 실패가 아니다."""
    out = job_result("j", expected=0, success=0)
    assert out.startswith("j: OK")


def test_partial_never_hides_error_count():
    """errors>0 인데 PARTIAL 표기가 빠지면 안 된다."""
    out = job_result("j", expected=3, success=1, errors=2)
    assert "PARTIAL" in out


# ── 잡들이 실제로 이 규약을 쓰는지 (구조 가드) ────────────────────────────────

@pytest.mark.parametrize(
    "fn",
    [
        kpi_job.daily_kpi_aggregation,
        kpi_job.weekly_kpi_aggregation,
        kpi_job.monthly_kpi_aggregation,
        kpi_job.recalculate_farm_kpi,
        tasks_job.generate_tasks_job,
        notif_job.generate_notifications_job,
    ],
)
def test_job_uses_job_result(fn):
    """잡이 결과 문자열을 직접 만들지 않고 job_result 를 거치는지."""
    src = inspect.getsource(fn)
    assert "job_result(" in src, f"{fn.__name__} 이 job_result 를 쓰지 않는다"


@pytest.mark.parametrize(
    "fn",
    [
        kpi_job.weekly_kpi_aggregation,
        kpi_job.monthly_kpi_aggregation,
        kpi_job.recalculate_farm_kpi,
    ],
)
def test_previously_uncounted_jobs_now_count_errors(fn):
    """weekly/monthly/recalc 는 예전에 errors 를 세지 않았다. 회귀 차단."""
    src = inspect.getsource(fn)
    assert "errors += 1" in src, f"{fn.__name__} 이 실패를 세지 않는다"
    assert "errors=errors" in src, f"{fn.__name__} 이 실패를 보고하지 않는다"


def test_kpi_alert_block_is_not_silent():
    """create_from_alerts 의 KPI 블록이 다시 조용한 pass 로 돌아가지 않도록."""
    from app.services import notification_service

    src = inspect.getsource(notification_service.create_from_alerts)
    assert "log.exception" in src, "KPI alert 실패가 다시 무기록으로 삼켜진다"
