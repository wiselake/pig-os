"""PigPlan Oracle 사료 **입고** 원장 → Feed Engine canonical input (shadow integration, 2026-09-22).

경계:  PigPlanFeedDeliverySource(Oracle, READ ONLY) → PigPlanFeedDeliveryRow → classify → RawFeedRow → FeedInput(DELIVERED)
원칙:  엔진 코드에 Oracle SQL 을 넣지 않는다 · PigOS DB 에 쓰지 않는다 · 보정하지 않는다(행을 ACCEPTED/EXCLUDED/INSUFFICIENT 로 나눌 뿐)
근거:  docs/feed/reports/PIGPLAN_ORACLE_FEED_PREFLIGHT_20260922.md · D-FEED-01/02/03

D-FEED-01  quantity_basis = DELIVERED — 입고/구매/배송량. CONSUMED·FED·USED 라 부르지 않는다. PigOS 수기 입력(AS_RECORDED)과 섞지 않는다.
D-FEED-02  source_currency = KRW — 근거: TC_CODE_SYS 943001 'KRW' ↔ 942001 'Korea(ko)' · TA_FARM.COUNTRY_CODE='KOR' (3,224/3,224).
           PigOS farm.currency 로 절대 fallback 하지 않는다. 농장 COUNTRY_CODE 가 KOR 이 아니면 그 농장의 원가는 BLOCKED_CURRENCY_EVIDENCE.
D-FEED-03  ACCOUNT_CD='410002' — filter evidence strong · official label unverified.
           증거: FEED_CD/TOTAL_KG/FPER_PRICE 99 % 채움 + 소스 스키마 트리거 TRG_TM_FEED_01:16 주석 "계정코드 : 사료비".
           코드표(TC_CODE_SYS/JOHAP)에는 없다 → "공식 사료 계정" 이라고 쓰지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from app.engine.feed.normalize import RawFeedRow, normalize
from app.engine.feed.types import QUANTITY_BASIS_DELIVERED, FeedInput, Period

SOURCE_CONTRACT: dict[str, Any] = {
    "source_system": "pigplan",
    "source_table": "TM_ETC_TRADE",
    "source_filter": {"ACCOUNT_CD": "410002", "GAIN_YN": "M"},
    "source_filter_status": "EVIDENCE_SUPPORTED_LABEL_UNVERIFIED",
    "label_evidence": "stored code TRG_TM_FEED_01 line 16: AND ACCOUNT_CD = '410002' -- 계정코드 : 사료비 (not in any code table)",
    "quantity_basis": QUANTITY_BASIS_DELIVERED,
    "quantity_column": "TOTAL_KG",
    "quantity_unit": "kg",
    "unit_cost_column": "FPER_PRICE",
    "unit_cost_unit": "currency/kg",
    "total_cost_column": "TOTAL_PRICE",
    "source_currency": "KRW",
    "currency_evidence_status": "CONFIRMED_BY_SOURCE_CONFIG",
    "currency_evidence": "TC_CODE_SYS 943001 'KRW' <-> 942001 'Korea'; TA_FARM.COUNTRY_CODE='KOR' for all farms",
    "currency_rule": "KRW only when TA_FARM.COUNTRY_CODE='KOR'; otherwise cost BLOCKED_CURRENCY_EVIDENCE (quantity still audited)",
    "pigos_farm_currency_fallback": "FORBIDDEN",
    "farm_mapping": "farms.farm_code = 'PP-{FARM_NO}' (harvest_import.py) — direct-mapped farms only, no fuzzy matching",
    "feed_stage_axis": "CK_USE_GUBUN_CD -> TC_CODE_SYS(pcode=100, ko) name — engine feed_type",
    "feed_product_axis": "FEED_CD -> TM_FEED.FEED_NM — preserved on the source row, never merged into feed_type",
    "group_attribution": "NONE (GRP_NO joins TJ_GAIN_GRP 0.3 %) — FCR family not computed",
}

SOURCE_CURRENCY = "KRW"
SOURCE_COUNTRY = "KOR"
FILTER_ACCOUNT_CD = "410002"
FILTER_GAIN_YN = "M"
MIN_VALID_DATE = date(1990, 1, 1)

RowStatus = Literal["ACCEPTED", "EXCLUDED", "INSUFFICIENT"]

# reason 어휘 (§7)
NON_POSITIVE_QUANTITY = "NON_POSITIVE_QUANTITY"
INACTIVE_SOURCE_ROW = "INACTIVE_SOURCE_ROW"
INVALID_DATE = "INVALID_DATE"
COST_INCOMPLETE = "COST_INCOMPLETE"
COST_IDENTITY_MISMATCH = "COST_IDENTITY_MISMATCH"
COST_DERIVED_FROM_TOTAL = "COST_DERIVED_FROM_TOTAL"
BLOCKED_CURRENCY_EVIDENCE = "BLOCKED_CURRENCY_EVIDENCE"
IDENTITY_TOLERANCE = Decimal("1")          # |total_price − fper_price×total_kg| < 1 (통화 최소단위 미만)


@dataclass(frozen=True)
class PigPlanFeedDeliveryRow:
    """소스 행 계약(§6). 값만, 원자료 provenance 를 잃지 않는다. 식별값은 artifact 에 내보내지 않는다(마스킹은 보고 계층)."""
    source_farm_no: int
    seq: int | None
    wk_dt: date | None                   # 파싱 실패/범위 밖은 None + wk_dt_raw
    wk_dt_raw: str | None
    total_kg: Decimal | None
    fper_price: Decimal | None           # currency/kg
    total_price: Decimal | None
    feed_stage_cd: str | None            # CK_USE_GUBUN_CD
    feed_stage_name: str | None          # 단계명(ko) — 엔진 feed_type
    feed_cd: int | None
    feed_name: str | None                # 제품명 — 보존만
    use_yn: str | None
    account_cd: str | None
    gain_yn: str | None
    country_code: str | None             # TA_FARM.COUNTRY_CODE
    has_supplier: bool = False           # COMP_CD IS NOT NULL


@dataclass(frozen=True)
class RowClassification:
    quantity: RowStatus
    cost: RowStatus
    unit_cost: Decimal | None            # 엔진에 넘길 값 (None = 원가 없음)
    reasons: tuple[str, ...] = ()


def classify(row: PigPlanFeedDeliveryRow, *, today: date) -> RowClassification:
    """수량 가용성과 원가 가용성을 **분리**해 판정한다. 보정 없음."""
    reasons: list[str] = []
    if row.account_cd != FILTER_ACCOUNT_CD or row.gain_yn != FILTER_GAIN_YN:
        return RowClassification("EXCLUDED", "EXCLUDED", None, ("OUT_OF_FILTER",))
    if (row.use_yn or "") != "Y":
        return RowClassification("EXCLUDED", "EXCLUDED", None, (INACTIVE_SOURCE_ROW,))
    if row.wk_dt is None or row.wk_dt < MIN_VALID_DATE or row.wk_dt > today:
        return RowClassification("EXCLUDED", "EXCLUDED", None, (INVALID_DATE,))
    if row.total_kg is None or row.total_kg <= 0:
        return RowClassification("EXCLUDED", "EXCLUDED", None, (NON_POSITIVE_QUANTITY,))

    # ── 수량 ACCEPTED. 이제 원가만 본다 ──
    if row.country_code != SOURCE_COUNTRY:
        return RowClassification("ACCEPTED", "EXCLUDED", None, (BLOCKED_CURRENCY_EVIDENCE,))
    price = row.fper_price if (row.fper_price is not None and row.fper_price > 0) else None
    total = row.total_price if (row.total_price is not None and row.total_price > 0) else None
    if price is not None and total is not None:
        if abs(total - price * row.total_kg) >= IDENTITY_TOLERANCE:
            # 단가와 총액이 서로 맞지 않는다 — 어느 쪽이 맞는지 정하지 않는다 → 원가 없음
            return RowClassification("ACCEPTED", "INSUFFICIENT", None, (COST_IDENTITY_MISMATCH,))
        return RowClassification("ACCEPTED", "ACCEPTED", price, ())
    if price is not None:
        return RowClassification("ACCEPTED", "ACCEPTED", price, ())
    if total is not None:
        # 총액만 있고 단가가 없다 — total/kg 는 kg 당 단가와 같은 의미(총액 = 단가×kg 항등이 96 % 에서 성립)
        reasons.append(COST_DERIVED_FROM_TOTAL)
        return RowClassification("ACCEPTED", "ACCEPTED", total / row.total_kg, tuple(reasons))
    return RowClassification("ACCEPTED", "INSUFFICIENT", None, (COST_INCOMPLETE,))


def to_raw_feed_row(row: PigPlanFeedDeliveryRow, cls: RowClassification) -> RawFeedRow:
    """ACCEPTED(수량) 행만 부른다. 통화는 소스 계약 KRW 를 행마다 명시 — 엔진의 farm_currency fallback 이 절대 닿지 않게."""
    if cls.quantity != "ACCEPTED":
        raise ValueError("only quantity-ACCEPTED rows become engine rows")
    return RawFeedRow(
        record_date=row.wk_dt,                      # type: ignore[arg-type]  (ACCEPTED ⇒ not None)
        quantity_kg=row.total_kg,                   # type: ignore[arg-type]
        unit_cost=cls.unit_cost,
        currency=SOURCE_CURRENCY,
        feed_type=row.feed_stage_name,              # 단계 축. 제품명(feed_name)은 여기 섞지 않는다
        sow_id=None, group_id=None, building_id=None,
    )


@dataclass
class ShadowBatch:
    """한 농장의 한 기간 — 분류 결과와 엔진 입력을 같이 들고 있어 감사 보고가 provenance 를 잃지 않는다."""
    source_farm_no: int
    period: Period
    rows: list[PigPlanFeedDeliveryRow] = field(default_factory=list)
    classes: list[RowClassification] = field(default_factory=list)

    def counts(self) -> dict[str, Any]:
        reasons: dict[str, int] = {}
        for c in self.classes:
            for r in c.reasons:
                reasons[r] = reasons.get(r, 0) + 1
        return {
            "source_rows": len(self.rows),
            "quantity_accepted": sum(1 for c in self.classes if c.quantity == "ACCEPTED"),
            "excluded": sum(1 for c in self.classes if c.quantity == "EXCLUDED"),
            "cost_accepted": sum(1 for c in self.classes if c.cost == "ACCEPTED"),
            "cost_insufficient": sum(1 for c in self.classes if c.cost == "INSUFFICIENT"),
            "cost_excluded": sum(1 for c in self.classes if c.quantity == "ACCEPTED" and c.cost == "EXCLUDED"),
            "reasons": dict(sorted(reasons.items())),
            "feed_products": len({r.feed_name for r, c in zip(self.rows, self.classes, strict=True)
                                  if c.quantity == "ACCEPTED" and r.feed_name}),
            "feed_stages": len({r.feed_stage_name for r, c in zip(self.rows, self.classes, strict=True)
                                if c.quantity == "ACCEPTED" and r.feed_stage_name}),
        }

    def feed_input(self) -> FeedInput:
        raws = [to_raw_feed_row(r, c) for r, c in zip(self.rows, self.classes, strict=True) if c.quantity == "ACCEPTED"]
        return normalize(raws, period=self.period, farm_currency=SOURCE_CURRENCY, cohort=None,
                         quantity_basis=QUANTITY_BASIS_DELIVERED)


def build_batch(source_farm_no: int, period: Period, rows: list[PigPlanFeedDeliveryRow], *, today: date) -> ShadowBatch:
    in_window = [r for r in rows if r.wk_dt is not None and period.contains(r.wk_dt)]
    # 날짜가 없는 행(INVALID_DATE)은 어느 기간에도 못 들어간다 — 분류 집계에는 남긴다
    dateless = [r for r in rows if r.wk_dt is None]
    b = ShadowBatch(source_farm_no=source_farm_no, period=period, rows=in_window + dateless)
    b.classes = [classify(r, today=today) for r in b.rows]
    return b


# ── Oracle 소스 (READ ONLY) ────────────────────────────────────────────────
_SELECT_ROWS = """
SELECT t.farm_no, t.seq, t.wk_dt, t.total_kg, t.fper_price, t.total_price,
       t.ck_use_gubun_cd,
       (SELECT s.cname FROM tc_code_sys s WHERE s.pcode='100' AND s.code=t.ck_use_gubun_cd AND s.language_cd='ko' AND rownum=1) stage_nm,
       t.feed_cd,
       (SELECT m.feed_nm FROM tm_feed m WHERE m.farm_no=t.farm_no AND m.feed_cd=t.feed_cd AND rownum=1) feed_nm,
       t.use_yn, t.account_cd, t.gain_yn, f.country_code,
       CASE WHEN t.comp_cd IS NULL THEN 0 ELSE 1 END has_supplier
FROM tm_etc_trade t LEFT JOIN ta_farm f ON f.farm_no = t.farm_no
WHERE t.account_cd = :acct AND t.gain_yn = :gain
  AND t.farm_no IN ({farms})
  AND (t.wk_dt IS NULL OR (t.wk_dt >= :d0 AND t.wk_dt < :d1 + 1))
"""

# 독립 대조 — 엔진을 거치지 않는 SQL. 분류 규칙(§7)을 SQL 로 다시 적은 것이라 두 구현이 서로를 검증한다.
_INDEPENDENT_MONTH = """
SELECT t.farm_no, to_char(t.wk_dt,'YYYY-MM') ym,
       sum(t.total_kg) kg,
       sum(CASE WHEN t.fper_price > 0 AND (t.total_price IS NULL OR t.total_price <= 0 OR abs(t.total_price - t.fper_price*t.total_kg) < 1)
                THEN t.total_kg * t.fper_price
                WHEN (t.fper_price IS NULL OR t.fper_price <= 0) AND t.total_price > 0 THEN t.total_price END) cost,
       sum(CASE WHEN t.fper_price > 0 AND (t.total_price IS NULL OR t.total_price <= 0 OR abs(t.total_price - t.fper_price*t.total_kg) < 1)
                THEN t.total_kg
                WHEN (t.fper_price IS NULL OR t.fper_price <= 0) AND t.total_price > 0 THEN t.total_kg END) priced_kg,
       count(*) rows_accepted,
       sum(CASE WHEN t.fper_price > 0 AND (t.total_price IS NULL OR t.total_price <= 0 OR abs(t.total_price - t.fper_price*t.total_kg) < 1) THEN 1
                WHEN (t.fper_price IS NULL OR t.fper_price <= 0) AND t.total_price > 0 THEN 1 ELSE 0 END) rows_costed
FROM tm_etc_trade t JOIN ta_farm f ON f.farm_no = t.farm_no
WHERE t.account_cd = :acct AND t.gain_yn = :gain AND t.use_yn = 'Y' AND f.country_code = :ctry
  AND t.farm_no IN ({farms}) AND t.total_kg > 0
  AND t.wk_dt >= :d0 AND t.wk_dt < :d1 + 1 AND t.wk_dt >= to_date('1990-01-01','YYYY-MM-DD') AND t.wk_dt <= :today
GROUP BY t.farm_no, to_char(t.wk_dt,'YYYY-MM')
"""

_INDEPENDENT_STAGE = """
SELECT t.farm_no, to_char(t.wk_dt,'YYYY-MM') ym,
       (SELECT s.cname FROM tc_code_sys s WHERE s.pcode='100' AND s.code=t.ck_use_gubun_cd AND s.language_cd='ko' AND rownum=1) stage_nm,
       sum(t.total_kg) kg
FROM tm_etc_trade t JOIN ta_farm f ON f.farm_no = t.farm_no
WHERE t.account_cd = :acct AND t.gain_yn = :gain AND t.use_yn = 'Y' AND f.country_code = :ctry
  AND t.farm_no IN ({farms}) AND t.total_kg > 0
  AND t.wk_dt >= :d0 AND t.wk_dt < :d1 + 1 AND t.wk_dt >= to_date('1990-01-01','YYYY-MM-DD') AND t.wk_dt <= :today
GROUP BY t.farm_no, to_char(t.wk_dt,'YYYY-MM'), t.ck_use_gubun_cd
"""


def _dec(v: Any) -> Decimal | None:
    return None if v is None else Decimal(str(v))


class PigPlanFeedDeliverySource:
    """Oracle 읽기 전용 소스. credential 은 호출자가 env 에서 넘긴다 — 이 모듈은 파일·메모리에서 비밀을 읽지 않는다."""

    def __init__(self, dsn: str, user: str, password: str) -> None:
        import oracledb  # 지연 import — 엔진·테스트는 드라이버 없이 돈다

        self._conn = oracledb.connect(user=user, password=password, dsn=dsn)
        self._conn.autocommit = False
        cur = self._conn.cursor()
        cur.execute("SET TRANSACTION READ ONLY")
        cur.execute("ALTER SESSION SET NLS_DATE_FORMAT='YYYY-MM-DD'")

    def close(self) -> None:
        self._conn.rollback()
        self._conn.close()

    @staticmethod
    def _farms_clause(farm_nos: list[int]) -> str:
        return ",".join(str(int(f)) for f in farm_nos)      # 정수만 — 바인딩 대신 int 강제

    def fetch_rows(self, farm_nos: list[int], start: date, end: date) -> list[PigPlanFeedDeliveryRow]:
        cur = self._conn.cursor()
        cur.execute(_SELECT_ROWS.format(farms=self._farms_clause(farm_nos)),
                    acct=FILTER_ACCOUNT_CD, gain=FILTER_GAIN_YN, d0=start, d1=end)
        out: list[PigPlanFeedDeliveryRow] = []
        for (farm_no, seq, wk_dt, kg, price, total, stage_cd, stage_nm, feed_cd, feed_nm,
             use_yn, acct, gain, ctry, has_supplier) in cur.fetchall():
            d = wk_dt.date() if hasattr(wk_dt, "date") else wk_dt
            out.append(PigPlanFeedDeliveryRow(
                source_farm_no=int(farm_no), seq=int(seq) if seq is not None else None,
                wk_dt=d, wk_dt_raw=str(wk_dt) if wk_dt is not None else None,
                total_kg=_dec(kg), fper_price=_dec(price), total_price=_dec(total),
                feed_stage_cd=stage_cd, feed_stage_name=stage_nm,
                feed_cd=int(feed_cd) if feed_cd is not None else None, feed_name=feed_nm,
                use_yn=use_yn, account_cd=acct, gain_yn=gain, country_code=ctry,
                has_supplier=bool(has_supplier),
            ))
        return out

    def independent_month_aggregates(self, farm_nos: list[int], start: date, end: date, *, today: date) -> dict[tuple[int, str], dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute(_INDEPENDENT_MONTH.format(farms=self._farms_clause(farm_nos)),
                    acct=FILTER_ACCOUNT_CD, gain=FILTER_GAIN_YN, ctry=SOURCE_COUNTRY, d0=start, d1=end, today=today)
        agg: dict[tuple[int, str], dict[str, Any]] = {}
        for farm_no, ym, kg, cost, priced_kg, rows_acc, rows_costed in cur.fetchall():
            agg[(int(farm_no), ym)] = {"kg": _dec(kg), "cost": _dec(cost), "priced_kg": _dec(priced_kg),
                                       "rows_accepted": int(rows_acc), "rows_costed": int(rows_costed), "stages": {}}
        cur.execute(_INDEPENDENT_STAGE.format(farms=self._farms_clause(farm_nos)),
                    acct=FILTER_ACCOUNT_CD, gain=FILTER_GAIN_YN, ctry=SOURCE_COUNTRY, d0=start, d1=end, today=today)
        for farm_no, ym, stage_nm, kg in cur.fetchall():
            key = (int(farm_no), ym)
            if key in agg:
                agg[key]["stages"][stage_nm or "UNSPECIFIED"] = _dec(kg)
        return agg

    def farms_with_rows(self, farm_nos: list[int], start: date, end: date) -> list[int]:
        cur = self._conn.cursor()
        cur.execute(f"""SELECT DISTINCT farm_no FROM tm_etc_trade
                        WHERE account_cd = :acct AND gain_yn = :gain AND use_yn = 'Y' AND total_kg > 0
                          AND farm_no IN ({self._farms_clause(farm_nos)}) AND wk_dt >= :d0 AND wk_dt < :d1 + 1""",
                    acct=FILTER_ACCOUNT_CD, gain=FILTER_GAIN_YN, d0=start, d1=end)
        return sorted(int(r[0]) for r in cur.fetchall())
