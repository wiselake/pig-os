"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { Activity, AlertTriangle, CircleDashed, PauseCircle, CheckCircle2 } from "lucide-react";
import { adminApi } from "@/lib/api/endpoints/admin";
import type { DataMonitorRow } from "@/types/api.types";

const STATUS_META: Record<DataMonitorRow["status"], { cls: string; icon: typeof Activity }> = {
  active: { cls: "bg-green-soft text-success border-success/30", icon: CheckCircle2 },
  idle: { cls: "bg-amber-soft text-warning border-warning/40", icon: PauseCircle },
  stale: { cls: "bg-red-soft text-danger border-danger/40", icon: AlertTriangle },
  onboarding: { cls: "bg-primary-soft text-primary border-primary/30", icon: CircleDashed },
};
// 농가 분류(data_origin/classification 파생) 배지
const CAT_META: Record<DataMonitorRow["category"], string> = {
  real: "bg-green-soft text-success border-success/30",
  test: "bg-amber-soft text-warning border-warning/40",
  pigplan: "bg-primary-soft text-primary border-primary/30",
};
const PAGE_SIZE = 25;

export default function DataMonitorPage() {
  const t = useTranslations("adminDataMonitor");
  const router = useRouter();
  const [cat, setCat] = useState<"all" | DataMonitorRow["category"]>("all");
  const [page, setPage] = useState(1);
  const { data = [], isLoading, isError } = useQuery({
    queryKey: ["admin", "data-monitor"],
    queryFn: () => adminApi.dataMonitor(),
    refetchInterval: 5 * 60 * 1000,
  });

  const counts = (["onboarding", "active", "idle", "stale"] as const).map((s) => ({
    s, n: data.filter((r) => r.status === s).length,
  }));
  // 분류 필터 + 페이지네이션(농장 목록 성장 대비 — 클라 슬라이스)
  const filtered = cat === "all" ? data : data.filter((r) => r.category === cat);
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paged = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  const catCount = (c: DataMonitorRow["category"]) => data.filter((r) => r.category === c).length;

  return (
    <div className="p-7 max-w-6xl">
      <header className="mb-5 flex items-center gap-2.5">
        <Activity size={20} className="text-primary" />
        <div>
          <h1 className="text-[22px] font-extrabold tracking-tight">{t("title")}</h1>
          <p className="text-xs text-text3 mt-0.5">{t("sub")}</p>
        </div>
      </header>

      {/* 상태별 요약 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        {counts.map(({ s, n }) => {
          const m = STATUS_META[s];
          return (
            <div key={s} className="bg-surface border border-border rounded-2xl p-4">
              <div className="flex items-center gap-1.5 mb-1.5">
                <m.icon size={14} className={m.cls.split(" ")[1]} />
                <span className="text-[11px] font-bold uppercase tracking-wide text-text3">{t(s)}</span>
              </div>
              <div className="text-2xl font-extrabold font-mono">{isLoading ? "—" : n}</div>
            </div>
          );
        })}
      </div>

      {/* 분류 필터 (실사용자/테스트/피그플랜이관) */}
      <div className="flex gap-1.5 mb-3 flex-wrap">
        {(["all", "real", "test", "pigplan"] as const).map((c) => {
          const n = c === "all" ? data.length : catCount(c);
          const active = cat === c;
          return (
            <button
              key={c}
              onClick={() => { setCat(c); setPage(1); }}
              className={`text-xs font-semibold rounded-full px-3 py-1.5 border transition inline-flex items-center gap-1.5 ${
                active ? "bg-console text-white border-console" : "bg-surface border-border text-text2 hover:bg-bg2"
              }`}
            >
              {t(c === "all" ? "catAll" : c === "real" ? "catReal" : c === "test" ? "catTest" : "catPigplan")}
              <span className={`font-mono text-[11px] ${active ? "text-white/80" : "text-text3"}`}>{n}</span>
            </button>
          );
        })}
      </div>

      {isError ? (
        <div className="bg-red-soft border border-danger/30 rounded-xl p-4 text-sm text-danger">Failed to load.</div>
      ) : (
        <div className="bg-surface border border-border rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[740px]">
              <thead>
                <tr className="bg-bg2 text-text3 text-[11px] uppercase tracking-wide">
                  <th className="text-left px-4 py-2.5 font-bold">{t("farm")}</th>
                  <th className="text-left px-4 py-2.5 font-bold">{t("category")}</th>
                  <th className="text-left px-4 py-2.5 font-bold">{t("country")}</th>
                  <th className="text-right px-4 py-2.5 font-bold">{t("sows")}</th>
                  <th className="text-left px-4 py-2.5 font-bold">{t("last")}</th>
                  <th className="text-right px-4 py-2.5 font-bold">{t("e7")}</th>
                  <th className="text-right px-4 py-2.5 font-bold">{t("e30")}</th>
                  <th className="text-right px-4 py-2.5 font-bold">{t("issues") ?? "Issues"}</th>
                  <th className="text-left px-4 py-2.5 font-bold">{t("status")}</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr><td colSpan={9} className="px-4 py-10 text-center text-text3">…</td></tr>
                ) : paged.length === 0 ? (
                  <tr><td colSpan={9} className="px-4 py-10 text-center text-text3">{t("empty")}</td></tr>
                ) : paged.map((r) => {
                  const m = STATUS_META[r.status];
                  const cm = CAT_META[r.category];
                  return (
                    <tr
                      key={r.farm_id}
                      onClick={() => router.push(`/admin/data-monitor/${r.farm_id}`)}
                      className="border-t border-border hover:bg-primary-soft/40 cursor-pointer"
                    >
                      <td className="px-4 py-2.5 font-semibold text-text underline decoration-dotted decoration-text3 underline-offset-2">{r.farm_name}</td>
                      <td className="px-4 py-2.5">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold border ${cm}`}>
                          {t(r.category === "real" ? "catReal" : r.category === "test" ? "catTest" : "catPigplan")}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-text2 font-mono text-xs">{r.country}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{r.sows}</td>
                      <td className="px-4 py-2.5 text-text3 font-mono text-xs">
                        {r.last_event_at ? r.last_event_at.slice(0, 10) : t("never")}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono">{r.events_7d}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{r.events_30d}</td>
                      <td className="px-4 py-2.5 text-right">
                        {r.issues > 0 ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold border bg-red-soft text-danger border-danger/40">
                            <AlertTriangle size={12} />{r.issues}
                          </span>
                        ) : (
                          <span className="text-text3 font-mono text-xs">0</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold border ${m.cls}`}>
                          <m.icon size={12} />{t(r.status)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {!isLoading && totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-border text-xs">
              <span className="text-text3 font-mono">
                {(safePage - 1) * PAGE_SIZE + 1}–{Math.min(safePage * PAGE_SIZE, filtered.length)} / {filtered.length}
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={safePage <= 1}
                  className="px-3 py-1.5 rounded-lg border border-border bg-surface font-semibold disabled:opacity-40 hover:bg-bg2 transition"
                >
                  {t("prev") ?? "Prev"}
                </button>
                <span className="font-mono text-text3 px-1">{safePage} / {totalPages}</span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={safePage >= totalPages}
                  className="px-3 py-1.5 rounded-lg border border-border bg-surface font-semibold disabled:opacity-40 hover:bg-bg2 transition"
                >
                  {t("next") ?? "Next"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
