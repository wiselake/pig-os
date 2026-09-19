"use client";

import { localToday } from "@/lib/date";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { Heart, Baby, Sprout, AlertTriangle, LogOut, PiggyBank } from "lucide-react";

import { reportsApi } from "@/lib/api/endpoints/reports";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";

function today(): string {
  return localToday();
}

export default function DailyReportPage() {
  const t = useTranslations("dailyReport");
  const farmId = useAuthStore((s) => s.activeFarmId);
  const [date, setDate] = useState(today());

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.reports.daily(farmId ?? "", date),
    queryFn: () => reportsApi.daily(farmId!, date),
    enabled: !!farmId,
  });

  const Stat = ({ label, value, sub }: { label: string; value: number | string; sub?: string }) => (
    <div className="rounded-xl border border-border bg-surface px-4 py-3">
      <div className="text-[11px] text-text3 font-semibold">{label}</div>
      <div className="text-2xl font-extrabold font-mono mt-0.5">{value}</div>
      {sub && <div className="text-[11px] text-text3 mt-0.5">{sub}</div>}
    </div>
  );

  const Card = ({ Icon, color, label, children }: { Icon: React.ElementType; color: string; label: string; children: React.ReactNode }) => (
    <div className="rounded-2xl border border-border bg-bg2/40 p-4">
      <div className={`flex items-center gap-2 mb-3 text-sm font-bold ${color}`}><Icon size={14} />{label}</div>
      {children}
    </div>
  );

  return (
    <div className="p-7 max-w-6xl">
      <div className="flex items-center justify-between mb-5 gap-4 flex-wrap">
        <div>
          <h1 className="text-[22px] font-extrabold tracking-tight">{t("title")}</h1>
          <p className="text-xs text-text3 mt-0.5">{t("subtitle")}</p>
        </div>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          data-testid="daily-date"
          className="input w-44"
        />
      </div>

      {isLoading || !data ? (
        <div className="text-center py-20 text-text3 text-sm">{t("loading")}</div>
      ) : (
        <div className="space-y-4">
          {/* 돈군 현황 */}
          <Card Icon={PiggyBank} color="text-navy" label={t("herd")}>
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
              <Stat label={t("activeSows")} value={data.herd.active_sows} />
              <Stat label={t("gilts")} value={data.herd.gilts} />
              <Stat label={t("open")} value={data.herd.open} />
              <Stat label={t("pregnant")} value={data.herd.pregnant} />
              <Stat label={t("lactating")} value={data.herd.lactating} />
              <Stat label={t("accident")} value={data.herd.accident} />
            </div>
          </Card>

          {/* 당일 이벤트 */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <Card Icon={Heart} color="text-primary" label={t("matings")}>
              <div className="text-3xl font-extrabold font-mono">{data.matings}</div>
            </Card>
            <Card Icon={Baby} color="text-success" label={t("farrowings")}>
              <div className="text-3xl font-extrabold font-mono">{data.farrowings.count}</div>
              <div className="text-[11px] text-text3 mt-1">{t("totalBorn")} {data.farrowings.total_born} · {t("bornAlive")} {data.farrowings.born_alive}</div>
            </Card>
            <Card Icon={Sprout} color="text-warning" label={t("weanings")}>
              <div className="text-3xl font-extrabold font-mono">{data.weanings.count}</div>
              <div className="text-[11px] text-text3 mt-1">{t("weaned")} {data.weanings.weaned}</div>
            </Card>
            <Card Icon={AlertTriangle} color="text-purple" label={t("accidents")}>
              <div className="text-3xl font-extrabold font-mono">{data.accidents}</div>
            </Card>
            <Card Icon={Baby} color="text-snout" label={t("pigletDeaths")}>
              <div className="text-3xl font-extrabold font-mono">{data.piglet_deaths.count}</div>
              <div className="text-[11px] text-text3 mt-1">{t("piglets")} {data.piglet_deaths.piglets}</div>
            </Card>
            <Card Icon={LogOut} color="text-danger" label={t("removals")}>
              <div className="text-3xl font-extrabold font-mono">{data.removals}</div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
