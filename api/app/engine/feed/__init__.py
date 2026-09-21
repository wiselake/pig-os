"""Feed Engine V1 — deterministic feed metrics (F0 계약: docs/feed/FEED_ENGINE_V1_CANONICAL_SPEC.md).

계층:  raw rows → normalize (F1) → FeedInput → metrics / variance (F2) → FeedMetricResult → status
원칙:  모르는 입력 의미를 추정하지 않는다 · 없는 데이터를 만들지 않는다 · 계산과 판정을 분리한다 ·
       같은 입력은 같은 결과. 이 패키지는 DB·시계·난수를 모른다 (tests/unit/test_feed_engine_purity.py 가 강제).
"""
from app.engine.feed.types import (
    ACTUAL,
    DERIVED,
    FORMULA_VERSION,
    INSUFFICIENT,
    QUANTITY_BASIS,
    FeedInput,
    FeedMetricResult,
    FeedRow,
    Period,
)

__all__ = [
    "ACTUAL", "DERIVED", "INSUFFICIENT", "FORMULA_VERSION", "QUANTITY_BASIS",
    "FeedInput", "FeedMetricResult", "FeedRow", "Period",
]
