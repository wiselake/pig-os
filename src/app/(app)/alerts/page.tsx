"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { Sparkles, ChevronRight, Info, ShieldAlert, CheckCircle2 } from "lucide-react";
import { alertsApi } from "@/lib/api/endpoints/alerts";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import { AlertsTabs } from "@/components/AlertsTabs";
import { ALERT_META, ALL_OVERDUE_TYPES, SEVERITY_BAND, SEVERITY_PILL, type Severity } from "@/lib/alerts/meta";
import type { OverdueSow, OverdueType } from "@/types/api.types";

const CULL_REASON_KEYS: Record<string, string> = {
  repeat_rts: "reasonRepeatRts",
  aged_low_performer: "reasonAgedLowPerformer",
  overdue_gilt: "reasonOverdueGilt",
};

const SEV_ORDER: Severity[] = ["critical", "warning", "info"];

export default function AlertsPage() {
  const t = useTranslations("alerts");
  const tMeta = useTranslations("alertsMeta");
  const tStatus = useTranslations("sowStatus");
  const farmId = useAuthStore((s) => s.activeFarmId);
  const [tab, setTab] = useState<"all" | Severity>("all");

  const { data: overdue, isLoading, isError } = useQuery({
    queryKey: queryKeys.alerts.overdue(farmId ?? ""),
    queryFn: () => alertsApi.overdue(farmId!),
    enabled: !!farmId,
  });

  const { data: cullCandidates } = useQuery({
    queryKey: queryKeys.alerts.cullCandidates(farmId ?? ""),
    queryFn: () => alertsApi.cullCandidates(farmId!),
    enabled: !!farmId,
  });

  if (!farmId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-text3">{t("selectFarm")}</p>
      </div>
    );
  }

  const counts = overdue?.counts ?? {};
  const items = overdue?.items ?? [];
  const culls = cullCandidates ?? [];

  // 타입별 신호 그룹 (count>0). 심각도순 → 건수순 정렬.
  const signals = ALL_OVERDUE_TYPES
    .map((type) => ({ type, count: counts[type] ?? 0, meta: ALERT_META[type] }))
    .filter((s) => s.count > 0)
    .filter((s) => tab === "all" || s.meta.severity === tab)
    .sort((a, b) => SEV_ORDER.indexOf(a.meta.severity) - SEV_ORDER.indexOf(b.meta.severity) || b.count - a.count);

  const tabCounts: Record<Severity, number> = { critical: 0, warning: 0, info: 0 };
  for (const type of ALL_OVERDUE_TYPES) tabCounts[ALERT_META[type].severity] += counts[type] ?? 0;
  const totalOpen = overdue?.total ?? 0;

  return (
    <div className="p-7 max-w-[1600px] space-y-4">
      <AlertsTabs />

      {/* Header */}
      <div className="flex items-center gap-2.5">
        <div className="w-9 h-9 rounded-xl bg-green-soft flex items-center justify-center">
          <Sparkles size={18} className="text-primary" />
        </div>
        <div>
          <h1 className="text-[22px] font-extrabold tracking-tight">{t("title")}</h1>
          <p className="text-xs text-text3 mt-0.5">{t("subtitle")}</p>
        </div>
      </div>

      {/* Severity tabs + open total */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex gap-1.5">
          <SevTab active={tab === "all"} onClick={() => setTab("all")} label={t("tabAll")} n={totalOpen} />
          <SevTab active={tab === "critical"} onClick={() => setTab("critical")} label={t("sevCritical")} n={tabCounts.critical} tone="critical" />
          <SevTab active={tab === "warning"} onClick={() => setTab("warning")} label={t("sevWarning")} n={tabCounts.warning} tone="warning" />
          <SevTab active={tab === "info"} onClick={() => setTab("info")} label={t("sevInfo")} n={tabCounts.info} tone="info" />
        </div>
        <div className="ml-auto flex items-center gap-2 px-3.5 py-2 rounded-xl bg-green-soft border border-success/20">
          <span className="text-[11px] font-bold uppercase tracking-wide text-success">{t("openSignals")}</span>
          <span className="font-mono text-lg font-extrabold text-success">{totalOpen}</span>
        </div>
      </div>

      {/* Explainable-AI notice */}
      <div className="flex items-center gap-2 text-xs text-text3">
        <Info size={14} className="text-primary shrink-0" />
        {t("evidenceNotice")}
      </div>

      {/* Signal cards */}
      {isLoading ? (
        <div className="space-y-2.5">{[1, 2, 3].map((i) => <div key={i} className="h-20 bg-border rounded-2xl animate-pulse" />)}</div>
      ) : isError ? (
        <div className="border border-danger/30 bg-danger/5 rounded-2xl py-14 text-center">
          <p className="font-bold text-danger">{t("loadError")}</p>
          <p className="text-xs text-text3 mt-1">{t("loadErrorDesc")}</p>
        </div>
      ) : signals.length === 0 ? (
        <div className="border border-border rounded-2xl py-14 text-center">
          <CheckCircle2 size={28} className="mx-auto mb-3 text-success" strokeWidth={1.75} aria-hidden />
          <p className="font-bold text-text">{t("emptyOverdueTitle")}</p>
          <p className="text-xs text-text3 mt-1">{t("emptyOverdueDesc")}</p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {signals.map((s) => (
            <SignalCard
              key={s.type}
              type={s.type}
              count={s.count}
              rows={items.filter((r) => r.type === s.type)}
              t={t}
              tMeta={tMeta}
              tStatus={tStatus}
            />
          ))}
        </div>
      )}

      {/* Cull recommendations */}
      {culls.length > 0 && (
        <section className="pt-2">
          <div className="flex items-center gap-2 text-[11px] font-bold text-faint uppercase tracking-widest mb-2">
            <ShieldAlert size={14} className="text-danger" />
            {t("cullRecommendations")} ({culls.length})
          </div>
          <div className="space-y-2">
            {culls.map((c) => (
              <div key={c.sow_id} className="border border-border rounded-2xl px-4 py-3 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono font-semibold text-sm">{c.ear_tag}</span>
                    <span className="text-[11px] text-text3">
                      {tStatus(c.status)} · {t("parity")} {c.parity}
                      {c.last_weaned != null && ` · ${t("lastWeaned", { n: c.last_weaned })}`}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {c.reasons.map((r) => (
                      <span key={r} className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-red-soft text-danger border border-danger/30">
                        {CULL_REASON_KEYS[r] ? t(CULL_REASON_KEYS[r]) : r}
                      </span>
                    ))}
                  </div>
                </div>
                <Link href={`/sows/${c.sow_id}`} className="inline-flex items-center gap-1 text-text3 text-xs font-semibold hover:text-text shrink-0">
                  {t("detail")} <ChevronRight className="w-3 h-3" />
                </Link>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function SevTab({ active, onClick, label, n, tone }: { active: boolean; onClick: () => void; label: string; n: number; tone?: Severity }) {
  const activeCls = tone === "critical" ? "bg-danger text-white border-danger"
    : tone === "warning" ? "bg-warning text-white border-warning"
    : tone === "info" ? "bg-success text-white border-success"
    : "bg-console text-white border-console";
  return (
    <button
      onClick={onClick}
      className={`px-3.5 py-1.5 rounded-full border text-[13px] font-semibold transition ${active ? activeCls : "bg-surface text-text2 border-border hover:bg-bg2"}`}
    >
      {label}{n > 0 ? ` ${n}` : ""}
    </button>
  );
}

function SignalCard({
  type, count, rows, t, tMeta, tStatus,
}: {
  type: OverdueType; count: number; rows: OverdueSow[];
  t: (k: string, v?: Record<string, string | number | Date>) => string;
  tMeta: (k: string, v?: Record<string, string | number | Date>) => string;
  tStatus: (k: string) => string;
}) {
  const meta = ALERT_META[type];
  const maxOverdue = rows.reduce((m, r) => Math.max(m, r.overdue_days), 0);
  const preview = rows.slice(0, 4);
  return (
    <Link
      href={`/alerts/${type}`}
      className="flex items-stretch gap-3.5 p-4 bg-surface border border-border rounded-2xl hover:shadow-[var(--shadow-card)] transition group"
    >
      <span className={`w-1 rounded-full shrink-0 ${SEVERITY_BAND[meta.severity]}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <span className="text-[15px] font-bold text-text">{t(meta.labelKey)}</span>
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${SEVERITY_PILL[meta.severity]}`}>
            {t(`sev${meta.severity.charAt(0).toUpperCase()}${meta.severity.slice(1)}`)}
          </span>
        </div>
        <div className="text-xs text-text3 leading-relaxed">{tMeta(meta.ruleKey, { n: meta.threshold })}</div>
        <div className="flex flex-wrap gap-1.5 mt-2">
          {preview.map((r) => (
            <span key={r.sow_id} className="font-mono text-[11px] font-semibold px-2 py-0.5 rounded bg-bg2 text-text2">
              {r.ear_tag} · {tStatus(r.status)}
            </span>
          ))}
          {count > preview.length && <span className="text-[11px] text-text3 self-center">+{count - preview.length}</span>}
        </div>
      </div>
      <div className="text-right shrink-0 flex flex-col items-end justify-between">
        <div>
          <div className="font-mono text-2xl font-extrabold text-text leading-none">{count}</div>
          <div className="text-[10px] text-text3 mt-0.5">{t("headUnit")}</div>
        </div>
        <div className="flex items-center gap-1 text-[11px] text-warning font-mono font-semibold">
          {t("maxOverdue", { days: maxOverdue })}
          <ChevronRight size={15} className="text-text3 group-hover:text-text transition" />
        </div>
      </div>
    </Link>
  );
}
