"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";

import { analyticsApi } from "@/lib/api/endpoints/analytics";
import { queryKeys } from "@/lib/api/queryKeys";
import { downloadCsv } from "@/lib/utils/csv";
import { useAuthStore } from "@/store/auth.store";
import type { PrrsGeneticsRow } from "@/types/api.types";

type Col = { key: keyof PrrsGeneticsRow; labelKey: string; num?: boolean; pct?: boolean };

const COLS: Col[] = [
  { key: "breed", labelKey: "cBreed" },
  { key: "genetics_id", labelKey: "cGenetics" },
  { key: "breed_company", labelKey: "cCompany" },
  { key: "total_sows", labelKey: "cTotal", num: true },
  { key: "affected_sows", labelKey: "cAffected", num: true },
  { key: "prrs_events", labelKey: "cEvents", num: true },
  { key: "incidence_rate", labelKey: "cRate", pct: true },
];

export default function PrrsReportPage() {
  const t = useTranslations("prrsReport");
  const farmId = useAuthStore((s) => s.activeFarmId);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.analytics.prrsByGenetics(farmId ?? ""),
    queryFn: () => analyticsApi.prrsByGenetics(farmId!),
    enabled: !!farmId,
  });

  if (!farmId) return <div className="p-7 text-text3">{t("selectFarm")}</div>;

  const rows = data?.rows ?? [];

  const exportCsv = () => {
    downloadCsv(
      `pigos_prrs_by_genetics_${farmId}.csv`,
      COLS.map((c) => t(c.labelKey)),
      rows.map((r) => COLS.map((c) => r[c.key])),
    );
  };

  return (
    <div className="p-7 max-w-[1600px]">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-[22px] font-extrabold tracking-tight">{t("title")}</h1>
          <p className="text-xs text-text3 mt-0.5">{t("subtitle")}</p>
        </div>
        <button
          onClick={exportCsv}
          disabled={rows.length === 0}
          className="inline-flex items-center gap-1.5 text-sm font-semibold border border-border rounded-xl px-3.5 py-2 hover:border-primary disabled:opacity-50"
        >
          <Download size={16} />
          CSV
        </button>
      </div>

      {/* Summary */}
      {data && (
        <div className="grid grid-cols-3 gap-3 mb-5">
          {[
            { k: "sumSows", v: data.total_sows },
            { k: "sumAffected", v: data.total_affected },
            { k: "sumEvents", v: data.total_events },
          ].map((c) => (
            <div key={c.k} className="border border-border rounded-2xl px-4 py-3 bg-surface">
              <div className="text-[11px] text-text3 uppercase tracking-wide">{t(c.k)}</div>
              <div className="text-xl font-extrabold font-mono tabular-nums mt-0.5">{c.v}</div>
            </div>
          ))}
        </div>
      )}

      {isLoading ? (
        <div className="h-40 bg-border rounded-2xl animate-pulse" />
      ) : rows.length === 0 ? (
        <div className="border border-border rounded-2xl py-16 text-center text-text3">{t("noData")}</div>
      ) : (
        <div className="border border-border rounded-2xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-bg2 text-text3 text-[11px] uppercase tracking-wide">
                {COLS.map((c) => (
                  <th key={c.key} className={`font-semibold px-3 py-2.5 ${c.num || c.pct ? "text-right" : "text-left"}`}>
                    {t(c.labelKey)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={`${r.breed}-${r.genetics_id}-${i}`} className="border-t border-border">
                  {COLS.map((c) => {
                    const v = r[c.key];
                    const display = v == null || v === "" ? "-" : c.pct ? `${v}%` : String(v);
                    return (
                      <td
                        key={c.key}
                        className={`px-3 py-2.5 ${c.num || c.pct ? "text-right font-mono tabular-nums" : "text-left"}`}
                      >
                        {display}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-[11px] text-text3 mt-3">{t("note")}</p>
    </div>
  );
}
