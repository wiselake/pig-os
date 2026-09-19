"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { Wallet, TrendingUp, TrendingDown, PiggyBank } from "lucide-react";
import { localToday } from "@/lib/date";
import { downloadCsv } from "@/lib/utils/csv";
import { ReportsTabs } from "@/components/ReportsTabs";
import { ReportExportBar } from "@/components/ReportExportBar";
import { reportsApi } from "@/lib/api/endpoints/reports";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import type { CostSummary } from "@/types/api.types";

// i18n: messages 네임스페이스 + useTranslations 사용(규칙4 준수).
function monthsAgoISO(n: number): string {
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() - n);
  return d.toISOString().slice(0, 10);
}
const TODAY = localToday();

const PRESETS = [
  { key: "p6m" as const, months: 6 },
  { key: "p1y" as const, months: 12 },
  { key: "p2y" as const, months: 24 },
];

function money(v: number | null, ccy: string): string {
  if (v == null) return "-";
  return `${ccy} ${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export default function CostReportPage() {
  const t = useTranslations("reportCost");
  const farmId = useAuthStore((s) => s.activeFarmId);
  const [months, setMonths] = useState(12);
  const start = monthsAgoISO(months);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.reports.costSummary(farmId ?? "", start, TODAY, "monthly"),
    queryFn: () => reportsApi.costSummary(farmId!, start, TODAY, "monthly"),
    enabled: !!farmId,
  });

  if (!farmId) return <div className="p-7 text-text3">{t("selectFarm")}</div>;

  const summary: CostSummary | undefined = data;
  const byCcy = summary?.by_currency ?? [];
  const rows = summary?.rows ?? [];
  const hasData = rows.length > 0;

  const exportCsv = () => {
    downloadCsv(
      `pigos_cost_${start}_${TODAY}.csv`,
      [t("period"), t("currency"), t("feedCost"), t("feedQty"), t("saleHead"), t("revenue"), t("net")],
      rows.map((r) => [
        r.period, r.currency, r.feed_cost, r.feed_qty_kg, r.sale_head, r.sale_revenue, r.net,
      ]),
    );
  };

  return (
    <div className="p-7 max-w-[1600px] print-area">
      <div className="no-print"><ReportsTabs /></div>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-[22px] font-extrabold tracking-tight">{t("title")}</h1>
          <p className="text-xs text-text3 mt-0.5">{t("sub")}</p>
        </div>
        <ReportExportBar onCsv={exportCsv} csvDisabled={!hasData} />
      </div>

      <div className="flex gap-2 mb-5">
        {PRESETS.map((p) => (
          <button
            key={p.months}
            onClick={() => setMonths(p.months)}
            className={`text-xs font-semibold rounded-full px-3.5 py-1.5 border transition ${
              months === p.months
                ? "bg-primary text-white border-primary"
                : "border-border text-text3 hover:border-primary"
            }`}
          >
            {t(p.key)}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="h-40 bg-border rounded-2xl animate-pulse" />
      ) : !hasData ? (
        <div className="border border-border rounded-2xl py-16 text-center text-text3">{t("noData")}</div>
      ) : (
        <>
          {/* 통화별 요약 카드 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 mb-6">
            {byCcy.map((cy) => {
              const netPos = cy.net != null && cy.net >= 0;
              return (
                <div key={cy.currency} className="bg-surface border border-border rounded-2xl p-5" style={{ boxShadow: "var(--shadow-card)" }}>
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-mono text-sm font-bold text-text3">{cy.currency}</span>
                    <PiggyBank size={16} className="text-primary" />
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <div className="flex items-center gap-1 text-[11px] text-text3 mb-0.5"><Wallet size={12} />{t("feedCost")}</div>
                      <div className="font-mono text-lg font-extrabold text-danger">{money(cy.feed_cost, cy.currency)}</div>
                    </div>
                    <div>
                      <div className="flex items-center gap-1 text-[11px] text-text3 mb-0.5"><TrendingUp size={12} />{t("revenue")}</div>
                      <div className="font-mono text-lg font-extrabold text-success">{money(cy.sale_revenue, cy.currency)}</div>
                    </div>
                    <div>
                      <div className="flex items-center gap-1 text-[11px] text-text3 mb-0.5">
                        {netPos ? <TrendingUp size={12} /> : <TrendingDown size={12} />}{t("net")}
                      </div>
                      <div className={`font-mono text-lg font-extrabold ${netPos ? "text-success" : "text-danger"}`}>
                        {money(cy.net, cy.currency)}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* 원가 입력률 안내 */}
          {summary?.feed_cost_coverage != null && summary.feed_cost_coverage < 100 && (
            <div className="bg-amber-soft border border-warning/40 rounded-xl p-3.5 mb-6 text-xs text-warning">
              <span className="font-bold">{t("coverage")}: {summary.feed_cost_coverage}%</span>
              <span className="ml-1">({summary.feed_records_with_cost}/{summary.feed_records_total}) — {t("coverageNote")}</span>
            </div>
          )}

          {/* 기간×통화 상세 테이블 */}
          <div className="border border-border rounded-2xl overflow-x-auto">
            <table className="w-full text-sm min-w-[640px]">
              <thead>
                <tr className="bg-bg2 text-text3 text-[11px] uppercase tracking-wide">
                  <th className="text-left font-semibold px-3 py-2.5">{t("period")}</th>
                  <th className="text-left font-semibold px-3 py-2.5">{t("currency")}</th>
                  <th className="text-right font-semibold px-3 py-2.5">{t("feedQty")}</th>
                  <th className="text-right font-semibold px-3 py-2.5">{t("feedCost")}</th>
                  <th className="text-right font-semibold px-3 py-2.5">{t("saleHead")}</th>
                  <th className="text-right font-semibold px-3 py-2.5">{t("revenue")}</th>
                  <th className="text-right font-semibold px-3 py-2.5">{t("net")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const netPos = r.net != null && r.net >= 0;
                  return (
                    <tr key={`${r.period}-${r.currency}`} className="border-t border-border">
                      <td className="px-3 py-2.5 font-mono text-xs text-text2">{r.period}</td>
                      <td className="px-3 py-2.5 font-mono text-xs">{r.currency}</td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums">{r.feed_qty_kg.toLocaleString()}</td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-danger">{r.feed_cost != null ? r.feed_cost.toLocaleString() : "-"}</td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums">{r.sale_head}</td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-success">{r.sale_revenue != null ? r.sale_revenue.toLocaleString() : "-"}</td>
                      <td className={`px-3 py-2.5 text-right font-mono tabular-nums font-semibold ${netPos ? "text-success" : "text-danger"}`}>
                        {r.net != null ? r.net.toLocaleString() : "-"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
