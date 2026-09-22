"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, AlertTriangle, AlertOctagon, ArrowRight } from "lucide-react";

import { reportsApi } from "@/lib/api/endpoints/reports";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import type { DataQualityIssue } from "@/types/api.types";

export default function DataQualityPage() {
  const t = useTranslations("dataQuality");
  const farmId = useAuthStore((s) => s.activeFarmId);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.reports.dataQuality(farmId ?? ""),
    queryFn: () => reportsApi.dataQuality(farmId!),
    enabled: !!farmId,
  });

  const issues = data ?? [];
  const critical = issues.filter((i) => i.severity === "CRITICAL");
  const warning = issues.filter((i) => i.severity === "WARNING");

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <header className="mb-5">
        <h1 className="text-xl font-extrabold text-text flex items-center gap-2">
          <ShieldCheck size={20} className="text-primary" /> {t("title")}
        </h1>
        <p className="text-sm text-text3 mt-1">{t("subtitle")}</p>
      </header>

      {/* Summary */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        <div className="rounded-2xl border border-danger/40 bg-red-soft px-4 py-3">
          <div className="flex items-center gap-2 text-danger text-xs font-bold">
            <AlertOctagon size={14} /> {t("critical")}
          </div>
          <div className="text-3xl font-extrabold font-mono text-danger mt-1">{critical.length}</div>
        </div>
        <div className="rounded-2xl border border-warning/40 bg-amber-soft px-4 py-3">
          <div className="flex items-center gap-2 text-warning text-xs font-bold">
            <AlertTriangle size={14} /> {t("warning")}
          </div>
          <div className="text-3xl font-extrabold font-mono text-warning mt-1">{warning.length}</div>
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-text3 py-10 text-center">{t("loading")}</p>
      ) : issues.length === 0 ? (
        <div className="rounded-2xl border border-success/30 bg-green-soft px-6 py-12 text-center">
          <ShieldCheck size={40} className="text-success mx-auto mb-3" />
          <p className="text-sm font-semibold text-success">{t("allClear")}</p>
        </div>
      ) : (
        <div className="rounded-2xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface text-text3 text-[11px] uppercase">
              <tr>
                <th className="text-left px-4 py-2.5 font-semibold">{t("colType")}</th>
                <th className="text-left px-4 py-2.5 font-semibold">{t("colSow")}</th>
                <th className="text-left px-4 py-2.5 font-semibold">{t("colDetail")}</th>
                <th className="text-left px-4 py-2.5 font-semibold">{t("colDate")}</th>
                <th className="px-4 py-2.5"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {issues.map((i, idx) => (
                <IssueRow key={idx} issue={i} farmId={farmId ?? ""} t={t} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function IssueRow({
  issue, farmId, t,
}: { issue: DataQualityIssue; farmId: string; t: (k: string) => string }) {
  const isCrit = issue.severity === "CRITICAL";
  return (
    <tr className="hover:bg-bg2/40">
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center gap-1.5 text-xs font-semibold ${
            isCrit ? "text-danger" : "text-warning"
          }`}
        >
          {isCrit ? <AlertOctagon size={12} /> : <AlertTriangle size={12} />}
          {t(issue.issue_type)}
        </span>
      </td>
      <td className="px-4 py-3 font-mono font-bold text-text1">{issue.ear_tag ?? "—"}</td>
      <td className="px-4 py-3 text-text2 text-xs">{issue.detail}</td>
      <td className="px-4 py-3 text-text3 font-mono text-xs">{issue.event_date ?? "—"}</td>
      <td className="px-4 py-3 text-right">
        {issue.sow_id && (
          <Link
            href={`/sows/${issue.sow_id}`}
            className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
          >
            {t("fix")} <ArrowRight size={12} />
          </Link>
        )}
      </td>
    </tr>
  );
}
