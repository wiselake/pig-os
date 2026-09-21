#!/usr/bin/env python
"""
피그플랜 CSV → PigOS 이관 임포터 (서비스레이어 replay).

설계(docs/tests/db/pigplan_import_mapping.md):
- CSV 로드(농장·use_yn='Y' 필터) → 모돈별 이벤트 타임라인(WK_DT 오름차순)
- record_mating → farrowing → weaning → reproductive_event → piglet_event 순차 재생
  (검증기·사이클 조립·상태전이를 그대로 통과 = 정합성 검증의 핵심)
- 실패 이벤트는 격리(로그+카운트) 후 계속 → 부분 사이클/중복서비스 자연 배제
- 적재 후 calculate_psy 로 PigOS PSY ↔ 원본(dusu 합) 대조

사용:
  cd api && uv run python -m scripts.import_pigplan --farm 4448 --limit 50
  옵션: --farm ALL | <FARM_NO>  --limit N(모돈수)  --csv-dir PATH  --reset  --reconcile-only
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import text

from app.core.security import hash_password
from app.db.models.platform import Farm, Organization, User, UserFarm
from app.db.models.sow import Boar, Sow
from app.db.session import AsyncSessionLocal
from app.schemas.events import (
    FarrowingCreate,
    MatingCreate,
    PigletEventCreate,
    ReproductiveEventCreate,
    WeaningCreate,
)
from app.services import event_service, kpi_service

DEFAULT_CSV = Path(__file__).resolve().parents[2] / "tests" / "db" / "extract"

# 고정 UUID(멱등 재실행 — 파일럿 전용 네임스페이스)
NS = "a11c0000"
def _farm_uuid(fn: int) -> UUID: return UUID(f"{NS}-0000-0000-0000-{fn:012d}")
ORG_UUID = UUID(f"{NS}-0000-0000-0000-0000000000ff")
USER_UUID = UUID(f"{NS}-0000-0000-0000-0000000000fe")

# ── 코드 매핑 (mapping.md §3 확정) ────────────────────────────────────────────
STATUS_MAP = {
    "010001": "GILT", "010002": "PREGNANT", "010003": "LACTATING",
    "010004": "LACTATING", "010005": "OPEN", "010006": "ACCIDENT",
    "010007": "ACCIDENT", "010008": "CULLED",
}
SAGO_MAP = {
    "050001": "RETURN_TO_ESTRUS", "050002": "ABORTION", "050003": "CULLED",
    "050004": "DEAD", "050005": "TRANSFER_OUT", "050006": "SOLD",
    "050007": "EMPTY", "050008": "RETURN_TO_ESTRUS", "050009": "INFERTILE",
}
FOSTER_MAP = {"160001": "DEATH", "160003": "FOSTER_IN", "160004": "FOSTER_OUT"}


def pdate(s: str | None) -> date | None:
    if not s:
        return None
    s = s.strip()
    if not s or s in ("0", "00000000"):
        return None
    try:
        if "-" in s:
            d = date.fromisoformat(s[:10])
        elif len(s) == 8:
            d = date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        else:
            return None
    except ValueError:
        return None
    # 피그플랜 '열림' 센티넬(9999-12-31 등) → None. 미래/이상치도 배제.
    if d.year >= 2100 or d.year < 1990:
        return None
    return d


def pdt(d: date | None) -> datetime | None:
    """DateTime(timezone=True) 컬럼용 — date → datetime 승격."""
    return datetime(d.year, d.month, d.day) if d else None


def fnum(s: str | None) -> float:
    try:
        return float(s) if s not in (None, "", "NULL") else 0.0
    except ValueError:
        return 0.0


def load_csv(csv_dir: Path, name: str, farms: set[int] | None) -> list[dict]:
    rows = []
    with open(csv_dir / f"{name}.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("use_yn", "Y") not in ("Y", "", None):
                continue
            if farms is not None and int(r["farm_no"]) not in farms:
                continue
            rows.append(r)
    return rows


async def _reset_farm(db, farm_id: UUID):
    """멱등 재실행: 해당 farm의 이벤트/모돈/사이클 등 삭제(파일럿 전용)."""
    # sows/boars를 참조하는 모든 자식 테이블 먼저 → breeding_cycles → boars/sows (순서 중요).
    for tbl in ("piglet_transfers", "piglet_events", "pregnancy_checks", "reproductive_events",
                "removals", "tasks", "feed_records", "health_events", "weanings", "farrowings",
                "matings", "breeding_cycles", "piglet_groups", "kpi_snapshots", "notifications",
                "audit_log", "farm_configs", "boars", "sows"):
        try:
            await db.execute(text(f"DELETE FROM {tbl} WHERE farm_id = :f"), {"f": str(farm_id)})
            await db.commit()
        except Exception:  # noqa: BLE001 — 없는 테이블/컬럼은 스킵
            await db.rollback()


async def ensure_infra(db, farm_no: int, farm_nm: str):
    """org + import user + farm(멱등)."""
    org = await db.get(Organization, ORG_UUID)
    if not org:
        db.add(Organization(id=ORG_UUID, name="피그플랜 이관(파일럿)", country="KR", timezone="Asia/Seoul"))
        await db.flush()
    user = await db.get(User, USER_UUID)
    if not user:
        db.add(User(id=USER_UUID, org_id=ORG_UUID, username="pigplan_import",
                    email="import@pigos.local", name="PigPlan Import",
                    password_hash=hash_password("import-only-" + uuid4().hex), role="FARM_OWNER",
                    language="ko"))
        await db.flush()
    fid = _farm_uuid(farm_no)
    farm = await db.get(Farm, fid)
    if not farm:
        farm = Farm(id=fid, org_id=ORG_UUID, farm_code=f"PP-{farm_no}", name=farm_nm or f"Farm {farm_no}",
                    country="KR", timezone="Asia/Seoul", currency="KRW", unit_system="METRIC")
        db.add(farm)
        await db.flush()
        db.add(UserFarm(user_id=USER_UUID, farm_id=fid, role_override="FARM_OWNER"))
        await db.flush()
    return farm


def build_timeline(pig_key, by_pig) -> list[tuple]:
    """모돈 1두의 이벤트 목록 → (date, priority, kind, payload) 정렬."""
    ev = []
    for g in by_pig["gyobae"].get(pig_key, []):
        d = pdate(g["wk_dt"])
        if d:
            mt = "AI" if (g.get("method_1") or "A").upper().startswith("A") else "NATURAL"
            ev.append((d, 0, "mating", {"mating_type": mt, "boar": g.get("ungdon_pig_no_1")}))
    for b in by_pig["bunman"].get(pig_key, []):
        d = pdate(b["wk_dt"])
        if d:
            ba = int(fnum(b["silsan"]))
            ev.append((d, 2, "farrowing", {
                "born_alive": ba, "stillborn": int(fnum(b["sasan"])),
                "mummified": int(fnum(b["mila"])),
                "avg_bw": (round(fnum(b["saengsi_kg"]) / ba, 3) if ba and fnum(b["saengsi_kg"]) > 0 else None),
            }))
    for w in by_pig["eu"].get(pig_key, []):
        d = pdate(w["wk_dt"])
        if d:
            dusu = int(fnum(w["dusu"]))
            ev.append((d, 4, "weaning", {
                "weaned": dusu,
                "avg_ww": (round(fnum(w["total_kg"]) / dusu, 3) if dusu and fnum(w["total_kg"]) > 0 else None),
            }))
    for s in by_pig["sago"].get(pig_key, []):
        d = pdate(s["wk_dt"])
        et = SAGO_MAP.get((s.get("sago_gubun_cd") or "").strip())
        if d and et:
            ev.append((d, 1, "repro", {"event_type": et}))
    # 양자/포유폐사(TB_MODON_JADON_TRANS)는 KPI(PSY/NPD)에 무관 + 슬라이스서 target 부재 →
    # 개별 재생 대신, 이유 시 (born_alive - weaned)를 합성 DEATH로 주입(pre-wean 폐사 재구성).
    ev.sort(key=lambda x: (x[0], x[1]))
    return ev


async def replay_sow(db, farm_id, sow_id, timeline, boar_map, sow_map, stats):
    open_ba = 0  # 현재 열린 분만의 born_alive (이유 시 합성폐사 계산용)
    for d, _pri, kind, p in timeline:
        try:
            if kind == "mating":
                boar_id = boar_map.get(p["boar"]) if p.get("boar") else None
                await event_service.record_mating(db, farm_id, USER_UUID, MatingCreate(
                    sow_id=sow_id, mating_date=d, mating_type=p["mating_type"], boar_id=boar_id))
            elif kind == "farrowing":
                await event_service.record_farrowing(db, farm_id, USER_UUID, FarrowingCreate(
                    sow_id=sow_id, farrowing_date=d, born_alive=p["born_alive"],
                    stillborn=p["stillborn"], mummified=p["mummified"],
                    avg_birth_weight_kg=(p["avg_bw"] if p["avg_bw"] and p["avg_bw"] <= 3.0 else None)))
                open_ba = p["born_alive"]
            elif kind == "weaning":
                weaned = min(30, max(0, p["weaned"]))
                # pre-wean 폐사 재구성: born_alive > weaned → 차이만큼 합성 DEATH(이유 두수 항등식 충족)
                deficit = open_ba - weaned
                if deficit > 0:
                    try:
                        await event_service.record_piglet_event(db, farm_id, USER_UUID, PigletEventCreate(
                            sow_id=sow_id, event_date=d, event_type="DEATH",
                            piglet_count=deficit, reason="OTHER", notes="pigplan-import: pre-wean mort recon"))
                        stats["deathrecon_ok"] += 1
                    except Exception:  # noqa: BLE001
                        stats["deathrecon_err"] += 1
                await event_service.record_weaning(db, farm_id, USER_UUID, WeaningCreate(
                    sow_id=sow_id, weaning_date=d, weaned_count=weaned,
                    avg_weaning_weight_kg=(p["avg_ww"] if p["avg_ww"] and 2 <= p["avg_ww"] <= 12 else None)),
                    import_mode=True)
                open_ba = 0
            elif kind == "repro":
                await event_service.record_reproductive_event(db, farm_id, USER_UUID,
                    ReproductiveEventCreate(sow_id=sow_id, event_date=d, event_type=p["event_type"],
                                            notes="pigplan-import"))
            stats[kind + "_ok"] += 1
        except Exception as e:  # noqa: BLE001 — 격리
            stats[kind + "_err"] += 1
            if stats["_errsample"] < 10:
                stats["_errmsgs"].append(f"{kind}@{d}: {type(e).__name__}: {str(e)[:95]}")
                stats["_errsample"] += 1


async def import_farm(db, farm_no: int, csv_dir: Path, limit: int | None, reset: bool):
    farms = {farm_no}
    farm_rows = load_csv(csv_dir, "TA_FARM", farms)
    farm_nm = farm_rows[0]["farm_nm"] if farm_rows else f"Farm {farm_no}"
    farm = await ensure_infra(db, farm_no, farm_nm)
    if reset:
        await _reset_farm(db, farm.id)
        await ensure_infra(db, farm_no, farm_nm)

    print(f"\n=== 농장 {farm_no} ({farm_nm}) ===", flush=True)

    # 이벤트 인덱싱 (pig_no 기준)
    by_pig = {}
    for key, name in [("gyobae", "TB_GYOBAE"), ("bunman", "TB_BUNMAN"), ("eu", "TB_EU"),
                      ("sago", "TB_SAGO")]:
        idx = defaultdict(list)
        for r in load_csv(csv_dir, name, farms):
            idx[r["pig_no"]].append(r)
        by_pig[key] = idx

    # 웅돈 생성 (pig_no → boar UUID)
    boar_map: dict[str, UUID] = {}
    for u in load_csv(csv_dir, "TB_UNGDON", farms):
        bid = uuid4()
        # ear_tag = pig_no (농장 내 유니크; farm_pig_no는 태그 재사용으로 중복 가능)
        db.add(Boar(id=bid, farm_id=farm.id, ear_tag=u["pig_no"][:30],
                    breed=(u.get("pumjong_cd") or None)[:50] if u.get("pumjong_cd") else None,
                    status="ACTIVE", entry_type="PURCHASE",
                    entry_date=pdt(pdate(u.get("in_dt")) or date(2000, 1, 1))))
        boar_map[u["pig_no"]] = bid
    await db.flush()

    # 모돈 로드
    modon = load_csv(csv_dir, "TB_MODON", farms)
    if limit:
        modon = modon[:limit]
    sow_map: dict[str, UUID] = {}
    for m in modon:
        sid = uuid4()
        entry = pdate(m.get("in_dt")) or date(2000, 1, 1)
        out = pdate(m.get("out_dt"))
        sow_map[m["pig_no"]] = sid
        # ear_tag = pig_no (농장 내 유니크; farm_pig_no는 태그 재사용으로 중복 가능)
        db.add(Sow(id=sid, farm_id=farm.id, ear_tag=m["pig_no"][:30],
                   rfid_tag=(m.get("farm_pig_no") or None),  # 실제 농장 태그 보존
                   breed=(m.get("pumjong_cd") or None)[:50] if m.get("pumjong_cd") else None,
                   status="GILT", parity=int(fnum(m.get("in_sancha"))),
                   entry_date=pdt(entry), entry_type="GILT", exit_date=pdt(out),
                   deleted_at=None))
    await db.flush()
    await db.commit()

    # 모돈별 replay (모돈 단위 커밋 — 대량 트랜잭션 방지)
    stats = defaultdict(int)
    stats["_errmsgs"] = []
    n = 0
    for m in modon:
        pig = m["pig_no"]
        timeline = build_timeline(pig, by_pig)
        if not timeline:
            continue
        await replay_sow(db, farm.id, sow_map[pig], timeline, boar_map, sow_map, stats)
        await db.commit()
        n += 1
        if n % 100 == 0:
            print(f"  ...{n} sows replayed", flush=True)

    # replay 완료 후: 퇴출모돈(exit_date 있음) soft-delete → PSY 재고 분모 정확화.
    # (replay 중엔 _get_active_sow가 deleted_at IS NULL 요구 → 반드시 replay 뒤에 실행)
    await db.execute(text(
        "UPDATE sows SET deleted_at = exit_date "
        "WHERE farm_id = :f AND exit_date IS NOT NULL AND deleted_at IS NULL"),
        {"f": str(farm.id)})
    await db.commit()

    print(f"  모돈 {n}두 replay 완료.", flush=True)
    for k in ("mating", "farrowing", "weaning", "repro", "deathrecon"):
        print(f"    {k:10s} ok={stats[k+'_ok']:6d}  err={stats[k+'_err']:5d}", flush=True)
    if stats["_errmsgs"]:
        print("    오류 샘플:", flush=True)
        for msg in stats["_errmsgs"]:
            print(f"      - {msg}", flush=True)
    return farm, set(sow_map.keys())


async def reconcile(db, farm, csv_dir, farm_no, pigs: set[str] | None = None):
    """PigOS PSY ↔ 원본(dusu 합) 대조. pigs 주면 그 모돈만(슬라이스 검증)."""
    scope = " (전체)" if pigs is None else f" (모돈 {len(pigs)}두 슬라이스)"
    print(f"\n  ── 정합성 (농장 {farm_no}){scope} ──", flush=True)
    # 원본 연도별 이유두수 합
    raw = defaultdict(int)
    for w in load_csv(csv_dir, "TB_EU", {farm_no}):
        if pigs is not None and w["pig_no"] not in pigs:
            continue
        d = pdate(w["wk_dt"])
        if d:
            raw[d.year] += int(fnum(w["dusu"]))
    years = sorted(y for y in raw if y >= 2020)
    print(f"    {'YEAR':6s} {'PigOS_wean':>10s} {'raw_dusu':>10s} {'match':>8s} {'PigOS_PSY':>10s} {'avgSows':>8s}", flush=True)
    for y in years:
        psy = await kpi_service.calculate_psy(db, farm.id, y)
        pg = psy.total_weaned if psy else 0
        match = "OK" if pg == raw[y] else f"d{pg-raw[y]:+d}"
        print(f"    {y:<6d} {pg:>10d} {raw[y]:>10d} {match:>8s} "
              f"{(psy.psy if psy and psy.psy else 0):>10.2f} {(psy.avg_sow_count if psy else 0):>8.1f}", flush=True)


async def main():
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 → UTF-8(한글·기호 안전)
    except Exception:  # noqa: BLE001
        pass
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    ap = argparse.ArgumentParser()
    ap.add_argument("--farm", default="4448", help="FARM_NO 또는 ALL")
    ap.add_argument("--limit", type=int, default=None, help="모돈수 제한(슬라이스 검증용)")
    ap.add_argument("--csv-dir", default=str(DEFAULT_CSV))
    ap.add_argument("--reset", action="store_true", help="해당 농장 기존 데이터 삭제 후 재적재")
    ap.add_argument("--reconcile-only", action="store_true")
    args = ap.parse_args()

    csv_dir = Path(args.csv_dir)
    pilot = [2807, 4448, 848, 978]
    targets = pilot if args.farm.upper() == "ALL" else [int(args.farm)]

    async with AsyncSessionLocal() as db:
        for fn in targets:
            if args.reconcile_only:
                farm = await db.get(Farm, _farm_uuid(fn))
                if farm:
                    await reconcile(db, farm, csv_dir, fn)
                continue
            farm, pigs = await import_farm(db, fn, csv_dir, args.limit, args.reset)
            await reconcile(db, farm, csv_dir, fn, pigs if args.limit else None)


if __name__ == "__main__":
    asyncio.run(main())
