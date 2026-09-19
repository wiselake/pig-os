"""
default_metric_values 검증 게이트 메타 — 회귀 가드(위조 0).

- 신규 행은 benchmark_status='unverified'(검증 전), definition_id=None.
- 검증된 수치를 주입하기 전엔 'verified' 상태가 코드/시드에서 자동 부여되지 않는다(위조 0).
"""
import pytest

from app.db.models.config import DefaultMetricValue


@pytest.mark.asyncio
async def test_new_row_defaults_unverified(db):
    row = DefaultMetricValue(
        scope_type="region", scope_code="ZZ", metric_code="PSY",
        warning_threshold=20, critical_threshold=18, alert_direction="below",
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    # 검증 전이므로 verified 아님(위조 0). 정의 미매핑.
    assert row.benchmark_status == "unverified"
    assert row.definition_id is None


@pytest.mark.asyncio
async def test_no_auto_verified_status(db):
    """코드/모델 기본값으로 'verified'가 부여되지 않는다(검증값은 명시 주입만)."""
    row = DefaultMetricValue(scope_type="system", scope_code="SYSTEM", metric_code="NPD")
    db.add(row)
    await db.flush()
    assert row.benchmark_status != "verified"


@pytest.mark.asyncio
async def test_verified_requires_explicit_set(db):
    """'verified'는 명시적으로만 설정 가능(출처 확보 후 주입 단계)."""
    row = DefaultMetricValue(
        scope_type="region", scope_code="KR", metric_code="PSY",
        benchmark_status="verified", definition_id="pigos.psy.v1", source_ref="한돈팜스 2025",
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    assert row.benchmark_status == "verified"
    assert row.definition_id == "pigos.psy.v1"
