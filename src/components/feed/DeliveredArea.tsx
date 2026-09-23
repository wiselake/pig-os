"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { feedApi, type FeedMetric } from "@/lib/api/endpoints/feed";

// 영역 A "사료 입고 · PigPlan 연계" (DELIVERED) — 사료 화면 기획서 v0.2 §2·§3·§4·§6 (docs/feed/FEED_SCREEN_SPEC_DRAFT.md).
//  - 그릴지는 서버 판정(GET /feed/sources)만 따른다: visibility 가 REFERENCE_VISIBLE/CUSTOMER_VISIBLE 이고 입고 행이 있을 때.
//    그 전에는 입고 요약을 **요청하지도 않는다**. 국가·관할로 다시 판정하지 않는다.
//  - 데이터 기준일(마지막 성공 동기화)을 항상 보인다 — scheduler 가 꺼져 있으면 숫자는 멈춰 있다.
//  - 원가가 일부만 있으면 부분합을 입고비로 쓰지 않는다 — "일부만 있음(행 n%)".
//  - 진행 중인 달은 비교하지 않는다(B-1). 벤치마크 없음(n 이 peer 하한 미달).

const VISIBLE = new Set(["REFERENCE_VISIBLE", "CUSTOMER_VISIBLE"]);

function shiftMonths(period: string, n: number): string {
  const [y, m] = period.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + n, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

function fmt(v: number | null | undefined, digits = 0): string {
  return v == null ? "—" : v.toLocaleString(undefined, { maximumFractionDigits: digits });
}

export default function DeliveredArea({ farmId, period }: { farmId: string; period: string }) {
  const t = useTranslations("feed");
  const { data: sources } = useQuery({
    queryKey: ["feed", farmId, "sources"],
    queryFn: () => feedApi.sources(farmId),
  });
  const shown = !!sources && VISIBLE.has(sources.delivered.visibility) && (sources.delivered.rows ?? 0) > 0;

  const { data: summary } = useQuery({
    queryKey: ["feed", farmId, "summary", period, "DELIVERED"],
    queryFn: () => feedApi.summary(farmId, period, "DELIVERED"),
    enabled: shown,
  });
  const from = shiftMonths(period, -11);
  const { data: months = [] } = useQuery({
    queryKey: ["feed", farmId, "months", from, period, "DELIVERED"],
    queryFn: () => feedApi.months(farmId, from, period, "DELIVERED"),
    enabled: shown,
  });

  if (!shown || !sources) return null;

  const d = sources.delivered;
  const asOf = d.last_sync?.completed_at ? d.last_sync.completed_at.slice(0, 10) : "—";
  const syncFailed = d.latest_run_status != null && d.latest_run_status !== "SUCCEEDED";
  const m = summary?.metrics ?? {};
  const partial = summary?.period?.partial === true;
  const cost = m["FEED_COST"] as FeedMetric | undefined;
  const coverage = cost?.evidence?.["coverage_rows"] as number | undefined;
  const costText = cost?.value != null
    ? fmt(cost.value, 0)
    : cost?.reason === "cost_incomplete" && coverage != null
      ? t("delivered.costPartial", { pct: Math.round(coverage * 100) })
      : t("delivered.noCost");
  const qtyChange = m["FEED_QTY_CHANGE"];
  const shares = (m["FEED_MIX_SHARE"]?.evidence?.["shares"] ?? {}) as Record<string, number>;
  const cur = summary?.currency ?? "";

  return (
    <section data-testid="feed-area-delivered" className="mt-4 rounded-2xl border border-border bg-surface p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold text-text">{t("delivered.title")}</h2>
          <p className="text-[11px] text-text3">{t("delivered.basis")}</p>
        </div>
        <div className="text-[11px] text-text3" data-testid="feed-delivered-asof">
          {t("delivered.asOf", { date: asOf })}
          {syncFailed && <span className="ml-2 text-warning">{t("delivered.syncFailed")}</span>}
        </div>
      </div>
      {partial && (
        <span data-testid="feed-delivered-mtd" className="inline-block mt-2 rounded-full bg-bg2 px-2 py-0.5 text-[11px] font-semibold text-warning">
          {t("mtdBadge")}
        </span>
      )}

      {summary?.no_data ? (
        <div className="mt-4 rounded-xl border border-dashed border-border p-5 text-center text-text3 text-sm">{t("delivered.noMonth")}</div>
      ) : (
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          <Box label={t("delivered.qty")} value={fmt(m["FEED_QTY"]?.value, 1)} unit="kg" />
          <Box label={t("delivered.cost")} value={costText} unit={cost?.value != null ? cur : ""} />
          <Box label={t("delivered.unitPrice")} value={fmt(m["FEED_UNIT_PRICE"]?.value, 2)} unit={m["FEED_UNIT_PRICE"]?.value != null ? `${cur}/kg` : ""} />
          {!partial && qtyChange?.value != null && (
            <Box label={t("mChange")} value={`${qtyChange.value > 0 ? "+" : ""}${fmt(qtyChange.value, 1)}`} unit="kg" />
          )}
        </div>
      )}
      {!summary?.no_data && Object.keys(shares).length > 0 && (
        <div className="mt-3 text-xs text-text3">
          <span className="font-semibold text-text2">{t("delivered.mix")}: </span>
          {Object.entries(shares).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${Math.round(v * 100)}%`).join(" · ")}
        </div>
      )}

      {months.length > 0 && (
        <table className="mt-4 w-full text-xs" data-testid="feed-delivered-months">
          <thead className="text-text3">
            <tr>
              <th className="text-left py-1">{t("month")}</th>
              <th className="text-right py-1">{t("delivered.qty")} (kg)</th>
              <th className="text-right py-1">{t("delivered.cost")}</th>
              <th className="text-right py-1">{t("delivered.unitPrice")}</th>
            </tr>
          </thead>
          <tbody>
            {months.map((mo) => (
              <tr key={mo.period} className="border-t border-border">
                <td className="py-1 font-mono">
                  {mo.period}
                  {mo.partial && <span className="ml-1 font-sans text-[10px] text-warning">{t("mtdRow")}</span>}
                </td>
                <td className="py-1 text-right font-mono">{fmt(mo.feed_qty_kg, 1)}</td>
                <td className="py-1 text-right font-mono">{fmt(mo.feed_cost, 0)}</td>
                <td className="py-1 text-right font-mono">{fmt(mo.unit_price, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function Box({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="rounded-xl border border-border bg-bg p-3">
      <div className="text-[11px] text-text3">{label}</div>
      <div className="font-mono text-lg font-extrabold text-text">
        {value} <span className="text-xs font-normal text-text3">{unit}</span>
      </div>
    </div>
  );
}
