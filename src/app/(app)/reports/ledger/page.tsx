"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { Heart, Baby, Sprout, AlertTriangle, PiggyBank, LogOut } from "lucide-react";

import { eventsApi } from "@/lib/api/endpoints/events";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import type { LedgerKind } from "@/types/api.types";

const KINDS: { value: LedgerKind | "all"; key: string; Icon: React.ElementType; color: string }[] = [
  { value: "all",          key: "all",          Icon: PiggyBank,     color: "text-text2" },
  { value: "mating",       key: "kindMating",   Icon: Heart,         color: "text-primary" },
  { value: "farrowing",    key: "kindFarrowing", Icon: Baby,         color: "text-success" },
  { value: "weaning",      key: "kindWeaning",  Icon: Sprout,        color: "text-warning" },
  { value: "reproductive", key: "kindRepro",    Icon: AlertTriangle, color: "text-purple" },
  { value: "piglet",       key: "kindPiglet",   Icon: Baby,          color: "text-snout" },
  { value: "removal",      key: "kindRemoval",  Icon: LogOut,        color: "text-danger" },
];

export default function LedgerPage() {
  const t = useTranslations("ledger");
  const farmId = useAuthStore((s) => s.activeFarmId);
  const [kind, setKind] = useState<LedgerKind | "all">("all");

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.events.ledger(farmId ?? "", kind),
    queryFn: () => eventsApi.ledger(farmId!, { kind: kind === "all" ? undefined : kind, limit: 500 }),
    enabled: !!farmId,
  });

  const kindLabel = (k: string) => t(KINDS.find((x) => x.value === k)?.key ?? "all");

  return (
    <div className="p-7 max-w-6xl">
      <div className="mb-5">
        <h1 className="text-[22px] font-extrabold tracking-tight">{t("title")}</h1>
        <p className="text-xs text-text3 mt-0.5">{t("subtitle")}</p>
      </div>

      {/* Kind filter chips */}
      <div className="flex flex-wrap gap-2 mb-4">
        {KINDS.map(({ value, key, Icon }) => (
          <button
            key={value}
            data-testid={`ledger-kind-${value}`}
            onClick={() => setKind(value)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
              kind === value ? "bg-primary/10 border-primary text-primary" : "border-border text-text3 hover:bg-bg2"
            }`}
          >
            <Icon size={12} />
            {t(key)}
          </button>
        ))}
      </div>

      <div className="border border-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-bg2 text-text3 text-xs">
            <tr>
              <th className="text-left px-4 py-2.5 font-semibold">{t("colDate")}</th>
              <th className="text-left px-4 py-2.5 font-semibold">{t("colKind")}</th>
              <th className="text-left px-4 py-2.5 font-semibold">{t("colSow")}</th>
              <th className="text-left px-4 py-2.5 font-semibold">{t("colSummary")}</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={4} className="px-4 py-10 text-center text-text3">{t("loading")}</td></tr>
            ) : !data || data.length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-10 text-center text-text3">{t("empty")}</td></tr>
            ) : (
              data.map((e) => (
                <tr key={e.id} data-testid="ledger-row" className="border-t border-border hover:bg-bg2/50">
                  <td className="px-4 py-2.5 font-mono text-text2">{e.event_date}</td>
                  <td className="px-4 py-2.5">{kindLabel(e.kind)}</td>
                  <td className="px-4 py-2.5 font-mono font-semibold">{e.ear_tag ?? "-"}</td>
                  <td className="px-4 py-2.5 text-text2">{e.summary}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
