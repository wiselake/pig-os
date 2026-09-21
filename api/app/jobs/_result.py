"""잡 결과 semantics — item-level 실패가 job-level 성공으로 둔갑하지 않게 한다.

★ 왜 필요한가 (2026-08-28 런타임 감사)

  daily_kpi_aggregation 이 71농장 **전건 실패**하면서도 ARQ 에는 성공(●)으로 끝났다.
  로그는 `'daily KPI done: 0 farms, 71 errors'` 였는데, 잡이 문자열을 반환하는 한
  스케줄러는 그것을 성공으로 본다. weekly/monthly 는 더해서 errors 를 **세지도 않아**
  `'weekly KPI done: 0 farms'` 가 "처리할 농장이 없었다" 와 구분되지 않았다.

  그 결과 `kpi_snapshots` 는 2026-05-29 이래 0행인데 아무도 몰랐다.
  근거: docs/runs/RUNTIME_INTEGRITY_AUDIT_20260828.md

규칙 둘.

  1. expected > 0 인데 success == 0  →  성공으로 끝내지 않는다 (raise)
  2. errors > 0                      →  결과 문자열에 PARTIAL 을 남긴다

재시도 안전성: 이 규칙을 적용한 잡(KPI upsert · task 생성 · 알림 생성)은 전부 멱등이라
ARQ 재시도가 중복을 만들지 않는다. 멱등이 아닌 잡에 이 헬퍼를 쓰지 말 것.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class JobTotalFailure(RuntimeError):
    """대상이 있었는데 하나도 처리하지 못했다. 스케줄러에 실패로 보고되어야 한다."""


def job_result(
    name: str,
    *,
    expected: int,
    success: int,
    errors: int = 0,
    detail: str = "",
) -> str:
    """잡 결과 문자열을 만들되, 전건 실패면 예외를 던진다.

    expected  처리 대상 수 (0 이면 할 일이 없었다는 뜻 — 성공)
    success   실제로 성공한 수
    errors    실패한 수
    detail    기간 등 부가 정보. 그대로 뒤에 붙인다.
    """
    suffix = f" {detail}" if detail else ""

    if expected > 0 and success == 0:
        msg = f"{name}: TOTAL FAILURE — 0/{expected} processed, {errors} errors{suffix}"
        log.error(msg)
        raise JobTotalFailure(msg)

    if errors:
        msg = f"{name}: PARTIAL — {success}/{expected} processed, {errors} errors{suffix}"
        log.warning(msg)
        return msg

    msg = f"{name}: OK — {success}/{expected} processed{suffix}"
    log.info(msg)
    return msg
