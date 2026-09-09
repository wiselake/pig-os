"use client";

import { localToday } from "@/lib/date";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { ReportsTabs } from "@/components/ReportsTabs";
import { ReportExportBar } from "@/components/ReportExportBar";

import { downloadCsv } from "@/lib/utils/csv";
import { useQuery } from "@tanstack/react-query";
import { reportsApi } from "@/lib/api/endpoints/reports";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import type { BenchmarkValue, ReproductionRow } from "@/types/api.types";
import { AlertTriangle } from "lucide-react";

function monthsAgoISO(n: number): string {
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() - n);
  return d.toISOString().slice(0, 10);
}
const TODAY = localToday();

const PRESETS = [
  { labelKey: "p3m", months: 3 },
  { labelKey: "p6m", months: 6 },
  { labelKey: "p1y", months: 12 },
];

// bench: 해당 컬럼과 비교할 country 기준값 metric_code (없으면 비교 안 함)
const COLS: { key: keyof ReproductionRow; labelKey: string; pct?: boolean; bench?: string }[] = [
  { key: "total_matings", labelKey: "cMatings" },
  { key: "total_farrowings", labelKey: "cFarrowings" },
  { key: "total_weanings", labelKey: "cWeanings" },
  { key: "fr", labelKey: "cFr", pct: true, bench: "FARROWING_RATE" },
  { key: "avg_tb", labelKey: "cAvgTb" },
  { key: "avg_ba", labelKey: "cAvgBa", bench: "BORN_ALIVE" },
  { key: "avg_weaned", labelKey: "cAvgWeaned", bench: "WEANED_COUNT" },
  { key: "avg_lactation_days", labelKey: "cLactDays" },
  { key: "pwmr_a", labelKey: "cPwmrA", pct: true },
  { key: "pwmr_b", labelKey: "cPwmrB", pct: true },
  { key: "rts_rate", labelKey: "cRts", pct: true, bench: "RTS_RATE" },
  { key: "stillborn_rate", labelKey: "cStillbornRate", pct: true },
  { key: "mummified_rate", labelKey: "cMummifiedRate", pct: true },
];

function fmt(v: number | null | undefined, pct?: boolean): string {
  if (v == null) return "-";
  return pct ? `${v}%` : String(v);
}

// 기준값 대비 색상 — 비교만(판정 재구현 금지). below형=클수록 좋음, above형=작을수록 좋음.
function compareClass(v: number | null | undefined, b?: BenchmarkValue): string {
  if (v == null || !b || b.target == null) return "";
  const better = b.alert_direction === "above" ? v <= b.target : v >= b.target;
  return better ? "text-success" : "text-danger";
}

export default function ReproductionReportPage() {
  const t = useTranslations("reproReport");
  const farmId = useAuthStore((s) => s.activeFarmId);
  const [months, setMonths] = useState(6);
  const [groupBy, setGroupBy] = useState<"period" | "breed">("period");
  const start = monthsAgoISO(months);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.reports.productionSummary(farmId ?? "", start, TODAY, "monthly", groupBy),
    queryFn: () => reportsApi.productionSummary(farmId!, start, TODAY, "monthly", groupBy),
    enabled: !!farmId,
  });

  if (!farmId) return <div className="p-7 text-text3">{t("selectFarm")}</div>;

  const rows = data?.rows ?? [];
  const benchByCode = new Map<string, BenchmarkValue>(
    (data?.benchmarks ?? []).map((b) => [b.metric_code, b]),
  );
  const firstColLabel = groupBy === "breed" ? t("breed") : t("period");

  const exportCsv = () => {
    downloadCsv(
      `pigos_reproduction_${groupBy}_${start}_${TODAY}.csv`,
      [firstColLabel, ...COLS.map((c) => t(c.labelKey))],
      rows.map((r) => [r.period, ...COLS.map((c) => (r[c.key] as number | null) ?? null)]),
    );
  };

  return (
    <div className="p-7 max-w-[1600px] print-area">
      <div className="no-print"><ReportsTabs /></div>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-[22px] font-extrabold tracking-tight">{t("title")}</h1>
          <p className="text-xs text-text3 mt-0.5">{t("subtitle")}</p>
        </div>
        <ReportExportBar onCsv={exportCsv} csvDisabled={rows.length === 0} />
      </div>

      <div className="no-print flex flex-wrap items-center gap-2 mb-3">
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
            {t(p.labelKey)}
          </button>
        ))}
        <span className="mx-1 h-4 w-px bg-border" />
        {(["period", "breed"] as const).map((g) => (
          <button
            key={g}
            onClick={() => setGroupBy(g)}
            className={`text-xs font-semibold rounded-full px-3.5 py-1.5 border transition ${
              groupBy === g
                ? "bg-primary text-white border-primary"
                : "border-border text-text3 hover:border-primary"
            }`}
          >
            {g === "period" ? t("groupByPeriod") : t("groupByBreed")}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="h-40 bg-border rounded-2xl animate-pulse" />
      ) : rows.length === 0 ? (
        <div className="border border-border rounded-2xl py-16 text-center text-text3">
          {t("noData")}
        </div>
      ) : (
        <div className="border border-border rounded-2xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-bg2 text-text3 text-[11px] uppercase tracking-wide">
                <th className="text-left font-semibold px-3 py-2.5 sticky left-0 bg-bg2">{firstColLabel}</th>
                {COLS.map((c) => {
                  const b = c.bench ? benchByCode.get(c.bench) : undefined;
                  return (
                    <th key={c.key} className="text-right font-semibold px-3 py-2.5">
                      <div>{t(c.labelKey)}</div>
                      {b?.target != null && (
                        <div className="text-[9px] font-normal normal-case text-text3">
                          {t("benchTarget")} {b.target}
                        </div>
                      )}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.period} className="border-t border-border">
                  <td className="px-3 py-2.5 font-mono font-semibold sticky left-0 bg-surface">{r.period}</td>
                  {COLS.map((c) => {
                    const v = r[c.key] as number | null | undefined;
                    const b = c.bench ? benchByCode.get(c.bench) : undefined;
                    return (
                      <td
                        key={c.key}
                        className={`px-3 py-2.5 text-right font-mono tabular-nums ${compareClass(v, b)}`}
                      >
                        {fmt(v, c.pct)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-[11px] text-text3 mt-3 flex items-start gap-1.5">
        <AlertTriangle size={13} className="shrink-0 mt-px text-warning" strokeWidth={2} aria-hidden />
        <span>{t("pwmrNote")}</span>
      </p>
      {benchByCode.size > 0 && (
        <p className="text-[11px] text-text3 mt-1">
          {t("benchLegend")}
          {data?.country_scope ? ` (${data.country_scope})` : ""}
        </p>
      )}
    </div>
  );
}
