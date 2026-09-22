"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Building2, Tractor, Users, PiggyBank, UserPlus, CheckCircle2, AlertTriangle } from "lucide-react";
import { adminApi } from "@/lib/api/endpoints/admin";

// 운영자 어드민 — Phase 0 개요. 전사 카운트(조직/농장/사용자/모돈).
export default function AdminOverviewPage() {
  const t = useTranslations("admin");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["admin", "overview"],
    queryFn: () => adminApi.overview(),
  });

  const cards = [
    { key: "organizations", label: t("cardOrgs"), icon: Building2, value: data?.organizations },
    { key: "farms", label: t("cardFarms"), icon: Tractor, value: data?.farms },
    { key: "users", label: t("cardUsers"), icon: Users, value: data?.users },
    { key: "sows", label: t("cardSows"), icon: PiggyBank, value: data?.sows },
    { key: "signups7d", label: t("cardSignups7d"), icon: UserPlus, value: data?.signups_7d },
    { key: "activated", label: t("cardActivated"), icon: CheckCircle2, value: data?.activated_farms },
    { key: "stale", label: t("cardStale"), icon: AlertTriangle, value: data?.stale_farms },
  ];

  return (
    <div className="p-7 max-w-5xl">
      <header className="mb-6">
        <h1 className="text-[22px] font-extrabold tracking-tight">{t("overviewTitle")}</h1>
        <p className="text-xs text-text3 mt-0.5">{t("overviewSubtitle")}</p>
      </header>

      {isError ? (
        <div className="bg-red-soft border border-danger/30 rounded-xl p-4 text-sm text-danger">{t("loadError")}</div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
          {cards.map(({ key, label, icon: Icon, value }) => (
            <div key={key} className="bg-surface border border-border rounded-2xl p-5" style={{ boxShadow: "var(--shadow-card)" }}>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-bold uppercase tracking-wide text-text3">{label}</span>
                <Icon size={16} className="text-primary" />
              </div>
              {isLoading ? (
                <div className="h-9 w-16 bg-border rounded animate-pulse" />
              ) : (
                <div className="font-mono text-4xl font-extrabold text-text">{value ?? "—"}</div>
              )}
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-text3 mt-6">{t("phase0Note")}</p>
    </div>
  );
}
