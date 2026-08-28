"""KPI 스냅샷 supported-field contract.

배경: `_calculate_farm_kpi` 가 "farrowing_rate" 를 반환하는데 `KpiSnapshot` 에 그
      컬럼이 없어 **2026-05-29(26c2e68) 이래 71농장 전건 실패**했다. 두 파일이 같은
      커밋에서 태어나면서 어긋났고, 잡은 그 실패를 성공으로 보고했다.
      근거: docs/runs/RUNTIME_INTEGRITY_AUDIT_20260828.md §A4

이 테스트가 잠그는 것 셋.
  1. 페이로드에 미지의 키가 있어도 **전건 실패로 번지지 않는다** (per-field fail-safe)
  2. 산식이 확정되지 않은 지표는 **컬럼이 생겨도 영속되지 않는다**
  3. 보류 사유가 코드에 남아 있다 (이유 없는 보류 금지)
"""
from __future__ import annotations

from sqlalchemy import inspect as sa_inspect

from app.db.models.ops import KpiSnapshot
from app.jobs.kpi import _SNAPSHOT_COLUMNS, _WITHHELD_FIELDS, _snapshot_payload


def test_unknown_key_is_dropped_not_raised():
    """모델에 없는 키가 와도 예외가 아니라 drop 이다 — 이것이 원래 사고의 재발 방지책."""
    persisted, dropped = _snapshot_payload(
        {"active_sow_count": 10, "totally_unknown_kpi": 1.23}
    )
    assert persisted == {"active_sow_count": 10}
    assert "totally_unknown_kpi" in dropped


def test_farrowing_rate_is_withheld_with_reason():
    """canonical formula 가 AMBIGUOUS 인 동안은 컬럼 유무와 무관하게 저장 금지."""
    assert "farrowing_rate" in _WITHHELD_FIELDS
    assert _WITHHELD_FIELDS["farrowing_rate"].strip(), "보류 사유가 비어 있다"

    persisted, dropped = _snapshot_payload({"farrowing_rate": 82.0})
    assert persisted == {}
    assert "farrowing_rate" in dropped


def test_psy_is_withheld_until_aligned_with_canonical():
    """이 잡의 PSY 는 canonical 과 분모가 다르다(D-13 §1-4). 정렬 전 영속 금지."""
    assert "psy" in _WITHHELD_FIELDS
    persisted, _ = _snapshot_payload({"psy": 24.0})
    assert persisted == {}


def test_every_withheld_field_has_a_reason():
    for field, reason in _WITHHELD_FIELDS.items():
        assert isinstance(reason, str) and len(reason) > 20, (
            f"{field} 의 보류 사유가 부실하다 — 이유 없이 보류하지 않는다"
        )


def test_counts_still_persist():
    """한 지표의 모호성 때문에 스냅샷 전체가 죽지 않는다 — 사고의 핵심 교훈."""
    persisted, _ = _snapshot_payload({
        "psy": 24.0,
        "farrowing_rate": 82.0,
        "active_sow_count": 120,
        "gestating_count": 80,
        "lactating_count": 30,
    })
    assert persisted == {
        "active_sow_count": 120,
        "gestating_count": 80,
        "lactating_count": 30,
    }


def test_snapshot_columns_match_model():
    """_SNAPSHOT_COLUMNS 는 모델에서 런타임으로 읽어야 한다(하드코딩 금지)."""
    model_cols = {c.key for c in sa_inspect(KpiSnapshot).mapper.column_attrs}
    assert set(_SNAPSHOT_COLUMNS) == model_cols


def test_farrowing_rate_still_absent_from_model():
    """모델에 컬럼이 추가되면 이 테스트가 깨진다 — 그때 P0-2 확정 여부를 재검토하라는 신호."""
    model_cols = {c.key for c in sa_inspect(KpiSnapshot).mapper.column_attrs}
    assert "farrowing_rate" not in model_cols, (
        "KpiSnapshot 에 farrowing_rate 가 추가됐다. "
        "canonical formula 가 확정됐는지 확인하고 _WITHHELD_FIELDS 를 갱신하라."
    )
