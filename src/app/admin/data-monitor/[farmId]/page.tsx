"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft, PiggyBank, Activity, Calendar, Check,
  Heart, Baby, Milk, Syringe, LogOut, Wheat, type LucideIcon,
} from "lucide-react";
import { adminApi } from "@/lib/api/endpoints/admin";

// admin 콘솔은 ko 전용(내부 운영팀). 이벤트 유형 라벨은 한국어 고정 — 일반 사용자 노출 없음.
const EVENT_LABEL: Record<string, [LucideIcon, string]> = {
  mating: [Heart, "교배"], farrowing: [Baby, "분만"], weaning: [Milk, "이유"],
  health: [Syringe, "건강"], removal: [LogOut, "도폐사"], piglet: [PiggyBank, "자돈"],
  feed: [Wheat, "사료"],
};

/** 유형 배지 — 미등록 유형은 원문 코드를 그대로 보여준다(빈칸으로 삼키지 않는다). */
function EventLabel({ type }: { type: string }) {
  const hit = EVENT_LABEL[type];
  if (!hit) return <>{type}</>;
  const [Icon, label] = hit;
  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon size={13} className="text-text3 shrink-0" strokeWidth={1.75} aria-hidden />
      {label}
    </span>
  );
}

export default function FarmDataDetailPage() {
  const t = useTranslations("adminFarmDetail");
  const router = useRouter();
  const { farmId } = useParams<{ farmId: string }>();

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "data-monitor", farmId],
    queryFn: () => adminApi.dataMonitorDetail(farmId),
    enabled: !!farmId,
  });

  return (
    <div className="p-7 max-w-5xl">
      <button onClick={() => router.push("/admin/data-monitor")}
        className="inline-flex items-center gap-1.5 text-xs text-text3 hover:text-text mb-4">
        <ArrowLeft size={14} /> {t("back")}
      </button>

      {isLoading || !data ? (
        <div className="text-text3 text-sm">{t("loading")}</div>
      ) : (
        <>
          {/* 헤더 */}
          <header className="mb-6">
            <h1 className="text-[22px] font-extrabold tracking-tight">{data.farm_name}</h1>
            <p className="text-xs text-text3 mt-0.5">
              {t("country")} {data.country} · {t("org")} {data.org_name ?? "—"} · {data.timezone} · {data.currency}
            </p>
          </header>

          {/* KPI 카드 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {[
              { label: t("sows"), value: data.total_sows, icon: PiggyBank },
              { label: t("psy"), value: data.psy != null ? data.psy.toFixed(1) : "—", icon: Activity },
              { label: t("weaned"), value: data.total_weaned_ytd.toLocaleString(), icon: Activity },
              { label: t("avgSows"), value: data.avg_sows_ytd != null ? data.avg_sows_ytd.toFixed(0) : "—", icon: PiggyBank },
            ].map((k) => (
              <div key={k.label} className="bg-surface border border-border rounded-2xl p-4">
                <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-text3 mb-1.5">
                  <k.icon size={13} className="text-primary" />{k.label}
                </div>
                <div className="font-mono text-2xl font-extrabold text-text">{k.value}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* 모돈 상태분포 */}
            <div className="bg-surface border border-border rounded-2xl p-5">
              <h2 className="text-sm font-bold mb-3">{t("status")}</h2>
              {data.sows_by_status.length === 0 ? (
                <p className="text-xs text-text3">{t("none")}</p>
              ) : data.sows_by_status.map((s) => (
                <div key={s.status} className="flex items-center justify-between py-1 text-sm">
                  <span className="text-text2 font-mono text-xs">{s.status}</span>
                  <span className="font-mono font-bold">{s.count}</span>
                </div>
              ))}
            </div>

            {/* 이벤트 유형별 분해 */}
            <div className="bg-surface border border-border rounded-2xl p-5 md:col-span-2">
              <h2 className="text-sm font-bold mb-3">{t("events")}</h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[11px] uppercase tracking-wide text-text3">
                    <th className="text-left font-bold py-1">{t("type")}</th>
                    <th className="text-right font-bold py-1">{t("total")}</th>
                    <th className="text-right font-bold py-1">{t("d30")}</th>
                    <th className="text-right font-bold py-1">{t("last")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.event_breakdown.length === 0 ? (
                    <tr><td colSpan={4} className="py-4 text-center text-text3 text-xs">{t("none")}</td></tr>
                  ) : data.event_breakdown.map((e) => (
                    <tr key={e.type} className="border-t border-border">
                      <td className="py-1.5"><EventLabel type={e.type} /></td>
                      <td className="py-1.5 text-right font-mono">{e.total.toLocaleString()}</td>
                      <td className="py-1.5 text-right font-mono">{e.count_30d}</td>
                      <td className="py-1.5 text-right font-mono text-xs text-text3">{e.last_at ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 데이터 품질(정합성) */}
          <div className={`border rounded-2xl p-5 mt-5 ${data.integrity.total > 0 ? "bg-red-soft border-danger/40" : "bg-surface border-border"}`}>
            <h2 className="text-sm font-bold mb-3">{t("quality")}</h2>
            {data.integrity.total === 0 ? (
              <p className="inline-flex items-center gap-1 text-xs text-success font-semibold"><Check size={13} strokeWidth={3} aria-hidden />{t("clean")}</p>
            ) : (
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: t("litter"), v: data.integrity.litter_mismatch },
                  { label: t("reversal"), v: data.integrity.date_reversal },
                  { label: t("orphan"), v: data.integrity.status_orphan },
                ].map((x) => (
                  <div key={x.label} className="text-center">
                    <div className={`font-mono text-2xl font-extrabold ${x.v > 0 ? "text-danger" : "text-text3"}`}>{x.v}</div>
                    <div className="text-[11px] text-text3 mt-0.5">{x.label}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 최근 활동 타임라인 */}
          <div className="bg-surface border border-border rounded-2xl p-5 mt-5">
            <h2 className="text-sm font-bold mb-3 flex items-center gap-1.5"><Calendar size={14} className="text-primary" />{t("recent")}</h2>
            {data.recent_events.length === 0 ? (
              <p className="text-xs text-text3">{t("none")}</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {data.recent_events.map((r, i) => (
                  <span key={i} className="inline-flex items-center gap-1.5 bg-bg2 border border-border rounded-full px-2.5 py-1 text-xs">
                    <span><EventLabel type={r.type} /></span>
                    <span className="font-mono text-text3">{r.date}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
