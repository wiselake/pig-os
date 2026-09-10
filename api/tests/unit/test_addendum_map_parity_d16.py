"""D-16 — KR·CN 부속조항 부재는 누락이 아니라 설계다.

같은 의도를 말하는 맵이 두 곳에 있다.

    app.services.jurisdiction._ADDENDUM        표시용 부속조항 id
    app.services.terms_renderer._GROUP_ADDENDUM 문서 세트 조립

한쪽에만 키가 있으면 나중에 어긋난다. 두 맵이 **모든 그룹에 대해 같은 답**을
내는지 고정한다.

승인: D-16 (2026-09-10, 대표 구두). KR 법정 고지사항 충족 여부는 COUNSEL_PENDING —
이 테스트는 문서 구조만 고정하며 법률 결론을 주장하지 않는다.
"""
from __future__ import annotations

import pytest

from app.services.jurisdiction import _ADDENDUM
from app.services.terms_renderer import _GROUP_ADDENDUM

ALL_GROUPS = ["US", "EU", "GB", "BR", "TH", "VN", "KR", "CN", "OTHER"]


@pytest.mark.parametrize("group", ALL_GROUPS)
def test_two_maps_agree(group):
    assert _GROUP_ADDENDUM.get(group) == _ADDENDUM.get(group)


@pytest.mark.parametrize("group", ["KR", "CN", "OTHER"])
def test_no_addendum_is_explicit_not_missing(group):
    """키 자체가 없으면 '빠뜨린 것'과 구분되지 않는다. None 으로 명시한다."""
    assert group in _GROUP_ADDENDUM
    assert _GROUP_ADDENDUM[group] is None
    assert group in _ADDENDUM
    assert _ADDENDUM[group] is None


def test_unknown_group_falls_back_to_no_addendum():
    """명시 전 fallback semantics 와 결과가 동일함 — 기존 동작 보존."""
    assert _GROUP_ADDENDUM.get("ZZ") is None
    assert _ADDENDUM.get("ZZ") is None


@pytest.mark.parametrize("group", ["US", "EU", "GB", "BR", "TH", "VN"])
def test_other_jurisdictions_unchanged(group):
    assert _GROUP_ADDENDUM[group] == f"ADDENDUM_{group}"
