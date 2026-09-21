"""
operational_defaults 1:1 값보존 검증 (A-하이브리드 인수조건 ①②③).

① 발화 동일성: 레지스트리 min/max로 severity_for 한 결과 == 기존 sev_above/sev_below(원본 w/c) 결과.
② origin/원본값 메타 보존. ③ scope=global.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.operational_default import OperationalDefault
from app.db.operational_defaults_seed import OPERATIONAL_DEFAULTS, to_bounds
from app.engine.benchmark_thresholds import CRITICAL, OK, WARNING, severity_for
from app.engine.rules._common import sev_above, sev_below

pytestmark = pytest.mark.anyio

_SEV = {None: OK, "WARNING": WARNING, "CRITICAL": CRITICAL}


def _old(direction: str, v: float, w: float, c: float) -> str:
    """기존 코드 발화 로직 재현."""
    sev = sev_below(v, w, c) if direction == "higher_better" else sev_above(v, w, c)
    return _SEV[sev.name if sev else None]


@pytest.mark.parametrize("d", OPERATIONAL_DEFAULTS, ids=[d["rule_id"] for d in OPERATIONAL_DEFAULTS])
def test_firing_equivalence_1to1(d):
    """① 각 룰: 레지스트리 임계 발화 == 기존 인라인 임계 발화 (모든 구간)."""
    w, c, direction = d["warning"], d["critical"], d["direction"]
    b = to_bounds(d)
    # 임계 주변 + 양 극단 표본
    span = abs(w - c) or 1.0
    samples = [min(w, c) - span, c, (w + c) / 2, w, max(w, c) + span,
               min(w, c) - 0.01, max(w, c) + 0.01]
    for v in samples:
        got = severity_for(direction, v,
                           warning_min=b["warning_min"], warning_max=b["warning_max"],
                           critical_min=b["critical_min"], critical_max=b["critical_max"])
        exp = _old(direction, v, w, c)
        assert got == exp, f"{d['rule_id']} v={v}: registry={got} != code={exp}"


def test_inventory_count_29():
    assert len(OPERATIONAL_DEFAULTS) == 29


def test_no_duplicate_rule_ids():
    ids = [d["rule_id"] for d in OPERATIONAL_DEFAULTS]
    assert len(ids) == len(set(ids))


async def test_seed_rows_in_db(db: AsyncSession):
    """②③ DB 적재분: 29행·origin=code_default·scope=global·원본값 보존."""
    # 마이그레이션이 아닌 create_all 환경이므로 시드 직접 주입 후 검증
    for d in OPERATIONAL_DEFAULTS:
        b = to_bounds(d)
        db.add(OperationalDefault(
            scope="global", country_code=None, rule_id=d["rule_id"], kpi_code=d["kpi_code"],
            direction=d["direction"], value_scale=d["value_scale"],
            origin="code_default", source_rule=d["rule_id"], source_loc=d["src"],
            original_warning=d["warning"], original_critical=d["critical"], **b))
    await db.flush()
    rows = (await db.scalars(select(OperationalDefault))).all()
    assert len(rows) == 29
    assert all(r.origin == "code_default" and r.scope == "global" and r.country_code is None for r in rows)
    # 원본값 == 시드값
    by_rule = {r.rule_id: r for r in rows}
    for d in OPERATIONAL_DEFAULTS:
        r = by_rule[d["rule_id"]]
        assert float(r.original_warning) == d["warning"] and float(r.original_critical) == d["critical"]
