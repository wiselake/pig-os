"use client";

import { use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Info, Sparkles, ListChecks, ArrowRight } from "lucide-react";
import { alertsApi } from "@/lib/api/endpoints/alerts";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import { MiniBars } from "@/components/ui/charts";
import { ALERT_META, SEVERITY_PILL, type Severity } from "@/lib/alerts/meta";
import type { OverdueType } from "@/types/api.types";

export default function AlertDetailPage({ params }: { params: Promise<{ type: string }> }) {
  const { type } = use(params);
  const router = useRouter();
  const t = useTranslations("alerts");
  const tMeta = useTranslations("alertsMeta");
  const tStatus = useTranslations("sowStatus");
  const farmId = useAuthStore((s) => s.activeFarmId);
  const meta = ALERT_META[type as OverdueType];

  const { data: overdue, isLoading } = useQuery({
    queryKey: queryKeys.alerts.overdue(farmId ?? ""),
    queryFn: () => alertsApi.overdue(farmId!),
    enabled: !!farmId,
  });

  if (!meta) {
    return (
      <div className="p-7">
        <Link href="/alerts" className="text-sm text-primary">← {t("backToList")}</Link>
        <p className="text-text3 mt-4">{t("unknownSignal")}</p>
      </div>
    );
  }

  const rows = (overdue?.items ?? []).filter((r) => r.type === type).sort((a, b) => b.overdue_days - a.overdue_days);
  const count = rows.length;
  const maxOverdue = rows.reduce((m, r) => Math.max(m, r.overdue_days), 0);
  const sevKey = `sev${meta.severity.charAt(0).toUpperCase()}${meta.severity.slice(1)}`;
  // 경과일 분포(상위 12두) → 임계 초과 가시화
  const bars = rows.slice(0, 12).map((r) => r.overdue_days).reverse();

  return (
    <div className="p-7 max-w-[1600px] space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <button onClick={() => router.back()} className="w-9 h-9 rounded-lg border border-border bg-surface flex items-center justify-center hover:bg-bg2 transition">
          <ChevronLeft size={16} className="text-text2" />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-extrabold tracking-tight">{t(meta.labelKey)}</h1>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${SEVERITY_PILL[meta.severity]}`}>{t(sevKey)}</span>
          </div>
          <p className="text-xs text-text3 mt-0.5">{t("detailSubtitle")}</p>
        </div>
      </div>

      {isLoading ? (
        <div className="h-64 bg-border rounded-2xl animate-pulse" />
      ) : (
        <div className="grid lg:grid-cols-[1.55fr_1fr] gap-4 items-start">
          {/* LEFT — evidence */}
          <div className="space-y-4">
            {/* Why this fired */}
            <div className="bg-surface border border-border rounded-2xl p-5" style={{ boxShadow: "var(--shadow-card)" }}>
              <div className="flex items-center gap-2 text-sm font-bold text-text mb-4">
                <Info size={16} className="text-primary" /> {t("whyTitle")}
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                <Evidence label={t("detectionRule")} value={tMeta(meta.ruleKey, { n: meta.threshold })} />
                <Evidence label={t("currentValue")} value={t("detectedCount", { n: count, thr: meta.threshold })} tone={meta.severity} />
              </div>
              {bars.length >= 2 && (
                <div className="mt-5">
                  <div className="text-xs font-semibold text-text3 mb-2">{t("overdueDistribution")}</div>
                  <div className="flex items-end gap-3">
                    <span className={meta.severity === "critical" ? "text-danger" : "text-warning"}>
                      <MiniBars data={bars} w={300} h={56} />
                    </span>
                    <div className="pb-1">
                      <span className={`font-mono text-2xl font-extrabold ${meta.severity === "critical" ? "text-danger" : "text-warning"}`}>{maxOverdue}</span>
                      <span className="text-xs text-text3"> / {t("thresholdShort")} {meta.threshold}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Impact (honest: count + overdue range, no fabricated $) */}
            <div className="grid sm:grid-cols-2 gap-4">
              <div className={`rounded-2xl border p-4 ${meta.severity === "critical" ? "bg-red-soft border-danger/30" : "bg-amber-soft border-warning/30"}`}>
                <div className={`text-[11px] font-bold uppercase tracking-wide ${meta.severity === "critical" ? "text-danger" : "text-warning"}`}>{t("scale")}</div>
                <div className={`font-mono text-3xl font-extrabold mt-1 ${meta.severity === "critical" ? "text-danger" : "text-warning"}`}>{count}<span className="text-sm ml-1">{t("headUnit")}</span></div>
                <div className="text-[11px] text-text3 mt-1">{t("maxOverdue", { days: maxOverdue })}</div>
              </div>
              <div className="rounded-2xl border border-border bg-surface p-4">
                <div className="text-[11px] font-bold uppercase tracking-wide text-text3">{t("impact")}</div>
                <div className="text-[13px] text-text2 leading-relaxed mt-2">{tMeta(`${meta.ruleKey}_impact`)}</div>
              </div>
            </div>

            {/* Related animals */}
            <div className="bg-surface border border-border rounded-2xl p-5" style={{ boxShadow: "var(--shadow-card)" }}>
              <div className="text-sm font-bold text-text mb-3">{t("relatedAnimals", { n: count })}</div>
              <div className="border border-border rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-bg2 text-text3 text-[10px] uppercase tracking-wide">
                      <th className="text-left font-bold px-3 py-2">{t("colEarTag")}</th>
                      <th className="text-left font-bold px-3 py-2">{t("colStatus")}</th>
                      <th className="text-right font-bold px-3 py-2">{t("parity")}</th>
                      <th className="text-right font-bold px-3 py-2">{t("colOverdueDays")}</th>
                      <th className="text-right font-bold px-3 py-2">{t("colAction")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.sow_id} className="border-t border-border hover:bg-bg2/50">
                        <td className="px-3 py-2">
                          <Link href={`/sows/${r.sow_id}`} className="font-mono font-semibold text-text hover:text-primary">{r.ear_tag}</Link>
                        </td>
                        <td className="px-3 py-2 text-text3">{tStatus(r.status)}</td>
                        <td className="px-3 py-2 text-right font-mono text-text3">{r.parity}</td>
                        <td className="px-3 py-2 text-right font-mono font-semibold text-warning">{t("overdueDays", { days: r.overdue_days })}</td>
                        <td className="px-3 py-2 text-right">
                          <Link href={`/record?tab=${meta.action}&sowId=${r.sow_id}`} className="inline-flex items-center gap-1 text-primary text-xs font-semibold hover:underline">
                            {t(meta.action === "weaning" ? "actionWeaning" : meta.action === "farrowing" ? "actionFarrowing" : "actionMating")} <ArrowRight size={12} />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* RIGHT — actions + Ask Claude */}
          <div className="space-y-4">
            <div className="bg-surface border border-border rounded-2xl p-5" style={{ boxShadow: "var(--shadow-card)" }}>
              <div className="flex items-center gap-2 text-sm font-bold text-text mb-3">
                <ListChecks size={16} className="text-primary" /> {t("recommendedActions")}
              </div>
              <div className="space-y-2.5">
                {meta.actionKeys.map((k, i) => (
                  <div key={k} className="flex gap-3 items-start">
                    <span className="w-5 h-5 rounded-md border-[1.5px] border-border shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <div className="text-[13px] text-text2 leading-snug">{tMeta(k)}</div>
                      {i === 0 && <span className={`inline-block mt-1 text-[10px] font-bold px-1.5 py-0.5 rounded border ${SEVERITY_PILL[meta.severity]}`}>{t("priorityFirst")}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Ask Claude (Addon #1) */}
            <div className="rounded-2xl bg-console p-4 flex items-center gap-3 text-white">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0"><Sparkles size={16} className="text-white" /></div>
              <div className="flex-1 text-[12px] text-white/80 leading-snug">{t("askClaudeBody")}</div>
              <Link href="/chat" className="text-xs font-bold px-3 py-1.5 rounded-lg bg-primary text-white hover:opacity-90 inline-flex items-center gap-1 shrink-0">
                {t("askClaude")} <ChevronRight size={14} />
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Evidence({ label, value, tone }: { label: string; value: string; tone?: Severity }) {
  const valCls = tone === "critical" ? "text-danger" : tone === "warning" ? "text-warning" : "text-text";
  return (
    <div className="bg-bg2 border border-border rounded-xl px-3.5 py-3">
      <div className="text-[11px] font-bold uppercase tracking-wide text-text3">{label}</div>
      <div className={`text-[13px] font-semibold mt-1 leading-snug ${valCls}`}>{value}</div>
    </div>
  );
}
