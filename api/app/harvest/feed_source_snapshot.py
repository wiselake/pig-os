"""Source snapshot — Oracle 을 한 번만 읽어 repo 밖 임시 경로에 고정하고, 이후 단계는 snapshot 을 소스로 쓴다 (L0-B).

파일 내용은 실제 원장 행(식별자 포함)이므로 **repo 안에 두지 않는다**. 메타(개수·해시·분포)만 보고서에 옮긴다.
SnapshotSource 는 PigPlanFeedDeliverySource 와 같은 fetch_rows() 계약을 갖는다 — sync 코드는 둘을 구분하지 않는다.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.harvest import pigplan_feed_delivery as pf

SNAPSHOT_FORMAT = "feed_source_snapshot.v1"


def scope_hash(farm_nos: list[int], start: date, end: date) -> str:
    body = {"system": pf.SOURCE_SYSTEM, "dataset": pf.SOURCE_DATASET, "filter": pf.SOURCE_CONTRACT["source_filter"],
            "contract": pf.SOURCE_CONTRACT_VERSION, "farms": sorted(int(f) for f in farm_nos),
            "window": [start.isoformat(), end.isoformat()]}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def _ser(v: Any) -> Any:
    if isinstance(v, Decimal):
        return {"__dec__": str(v)}
    if isinstance(v, datetime):
        return {"__dt__": v.isoformat()}
    if isinstance(v, date):
        return {"__d__": v.isoformat()}
    return v


def _de(v: Any) -> Any:
    if isinstance(v, dict):
        if "__dec__" in v:
            return Decimal(v["__dec__"])
        if "__dt__" in v:
            return datetime.fromisoformat(v["__dt__"])
        if "__d__" in v:
            return date.fromisoformat(v["__d__"])
    return v


def row_to_json(r: pf.PigPlanFeedDeliveryRow) -> dict[str, Any]:
    return {k: _ser(v) for k, v in asdict(r).items()}


def row_from_json(d: dict[str, Any]) -> pf.PigPlanFeedDeliveryRow:
    return pf.PigPlanFeedDeliveryRow(**{k: _de(v) for k, v in d.items()})


def content_hash(rows: list[pf.PigPlanFeedDeliveryRow]) -> str:
    """정렬 후 해시 — 입력 순서와 무관 (L2 shuffle 검증의 기준)."""
    h = hashlib.sha256()
    for r in sorted(rows, key=lambda x: (x.source_farm_no, x.seq if x.seq is not None else -1)):
        h.update(json.dumps(row_to_json(r), sort_keys=True, ensure_ascii=False).encode())
    return h.hexdigest()


def summarize(rows: list[pf.PigPlanFeedDeliveryRow], farm_nos: list[int], start: date, end: date, *,
              extracted_at: datetime, oracle_elapsed_s: float | None = None) -> dict[str, Any]:
    """보고 가능한 메타만 (식별자 없음)."""
    dates = [r.wk_dt for r in rows if r.wk_dt is not None]
    use = {}
    for r in rows:
        k = "Y" if (r.use_yn or "") == "Y" else "non-Y"
        use[k] = use.get(k, 0) + 1
    upd = sum(1 for r in rows if r.source_inserted_at and r.source_updated_at and (r.source_updated_at - r.source_inserted_at).total_seconds() > 60)
    return {
        "format": SNAPSHOT_FORMAT, "extracted_at": extracted_at.isoformat(),
        "source_scope_hash": scope_hash(farm_nos, start, end), "content_hash": content_hash(rows),
        "row_count": len(rows), "farm_count": len({r.source_farm_no for r in rows}),
        "date_min": min(dates).isoformat() if dates else None, "date_max": max(dates).isoformat() if dates else None,
        "dateless_rows": sum(1 for r in rows if r.wk_dt is None),
        "use_yn_distribution": use, "rows_changed_after_insert": upd,
        "window": [start.isoformat(), end.isoformat()], "oracle_elapsed_s": oracle_elapsed_s,
        "filter": pf.SOURCE_CONTRACT["source_filter"], "contract": pf.SOURCE_CONTRACT_VERSION,
    }


def save(path: Path, rows: list[pf.PigPlanFeedDeliveryRow], meta: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"meta": meta, "rows": [row_to_json(r) for r in rows]}, ensure_ascii=False), encoding="utf-8")


def load(path: Path) -> tuple[list[pf.PigPlanFeedDeliveryRow], dict[str, Any]]:
    d = json.loads(path.read_text(encoding="utf-8"))
    if d.get("meta", {}).get("format") != SNAPSHOT_FORMAT:
        raise ValueError("not a feed source snapshot")
    return [row_from_json(x) for x in d["rows"]], d["meta"]


class SnapshotSource:
    """fetch_rows() 계약을 snapshot 파일로 구현. 창·농장 필터는 호출 인자대로 다시 적용한다."""

    def __init__(self, rows: list[pf.PigPlanFeedDeliveryRow], meta: dict[str, Any]):
        self.rows, self.meta = rows, meta

    @classmethod
    def from_file(cls, path: Path) -> SnapshotSource:
        return cls(*load(path))

    def fetch_rows(self, farm_nos: list[int], start: date, end: date) -> list[pf.PigPlanFeedDeliveryRow]:
        fs = set(int(f) for f in farm_nos)
        return [r for r in self.rows if r.source_farm_no in fs and (r.wk_dt is None or start <= r.wk_dt <= end)]

    def farms_with_rows(self, farm_nos: list[int], start: date, end: date) -> list[int]:
        return sorted({r.source_farm_no for r in self.fetch_rows(farm_nos, start, end)
                       if (r.use_yn or "") == "Y" and r.total_kg is not None and r.total_kg > 0})
