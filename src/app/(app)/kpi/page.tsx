"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Sparkles, FileDown, Printer, BarChart3, Star } from "lucide-react";
import { kpiApi } from "@/lib/api/endpoints/kpi";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import { Spark, LineChart } from "@/components/ui/charts";
import { legacyTier, TIER_STYLE, type KpiTier } from "@/lib/kpi/status";
import { resolveTier } from "@/lib/kpi/statusObservation";
import { resolveKpiCards, reportPresentationGaps } from "@/lib/kpi/presentation";
import type { KpiDashboard, KpiTrend } from "@/types/api.types";
import { useEffect } from "react";

export default function KpiPage() {
  const t = useTranslations("kpi");
  const tc = useTranslations("kpiCards");  // 카드 라벨/설명/단위 — 대시보드와 공용
  const farmId = useAuthStore((s) => s.activeFarmId);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.kpi.dashboard(farmId ?? ""),
    queryFn: () => kpiApi.dashboard(farmId!),
    enabled: !!farmId,
    refetchInterval: 5 * 60 * 1000,
  });

  const { data: trend } = useQuery({
    queryKey: queryKeys.kpi.trend(farmId ?? "", "ALL", 12),
    queryFn: () => kpiApi.trend(farmId!, "PSY", 12),
    enabled: !!farmId,
  });

  // 국가별 표현 정책 — 실패해도 화면은 기본 카드 순서로 뜬다(A3 폴백).
  const { data: presentation } = useQuery({
    queryKey: queryKeys.kpi.presentation(farmId ?? ""),
    queryFn: () => kpiApi.presentation(farmId!),
    enabled: !!farmId,
    retry: 1,
  });
  const resolved = resolveKpiCards(presentation);
  useEffect(() => { reportPresentationGaps(resolved); }, [resolved.source, resolved.unknownCodes.join(",")]);

  if (!farmId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-text3">{t("selectFarm")}</p>
      </div>
    );
  }

  return (
    <div className="p-7 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-green-soft flex items-center justify-center">
            <BarChart3 size={16} className="text-primary" />
          </div>
          <div>
            <h1 className="text-[22px] font-extrabold tracking-tight">{t("pageTitle")}</h1>
            {data && (
              <p className="text-xs text-text3 mt-0.5">
                {t("asOfActive", { date: data.as_of.slice(0, 10), n: data.active_sows })}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => refetch()} className="text-xs text-text3 border border-border rounded-lg px-3 py-2 hover:bg-bg2 transition">
            {t("refresh")}
          </button>
          <button onClick={() => window.print()} className="inline-flex items-center gap-1.5 text-xs text-text2 border border-border rounded-lg px-3 py-2 hover:bg-bg2 transition">
            <FileDown size={14} /> {t("export")}
          </button>
          <button onClick={() => window.print()} className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-primary rounded-lg px-3 py-2 hover:opacity-90 transition">
            <Printer size={14} /> {t("print")}
          </button>
        </div>
      </div>

      {isLoading && <div className="text-center text-text3 py-20">{t("calculating")}</div>}
      {isError && <div className="bg-red-soft border border-danger/30 rounded-xl p-4 text-sm text-danger">{t("loadError")}</div>}

      {data && (
        <>
          {/* KPI cards with sparklines */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
            {/* 카드 목록·순서·명칭은 서버(Presentation Policy)가 확정. 프론트 재정렬 금지. */}
            {resolved.cards.map(({ meta, localLabel, isHeadline }) => (
              <KpiCard
                key={meta.kpi_code}
                label={localLabel ?? meta.literalLabel ?? tc(meta.labelKey)}
                desc={meta.descKey ? tc(meta.descKey) : ""}
                unit={meta.unitKey ? tc(meta.unitKey) : undefined}
                value={fmt(meta.value(data), meta.digits)}
                bench={meta.benchKey ? data.benchmarks?.[meta.benchKey]?.target ?? null : null}
                tier={resolveTier(data.kpi_status, meta.kpi_code, legacyTier(meta.kpi_code, meta.value(data)))}
                invert={meta.invert}
                headline={isHeadline}
                spark={meta.series && trend ? meta.series(trend) : undefined}
                t={t}
              />
            ))}
            <div className="bg-surface border border-border rounded-xl p-4 flex flex-col justify-between">
              <span className="text-[11px] font-bold tracking-wide uppercase text-text3">{t("herdActiveTotal")}</span>
              <div className="font-mono text-3xl font-extrabold text-text">{data.active_sows}<span className="text-sm text-text3 font-semibold ml-1">{t("headUnit")}</span></div>
              <div className="flex gap-2 text-[10px] text-text3 font-mono mt-1">
                <span>{t("herdPregnant")} {data.gestating}</span>
                <span>{t("herdLactating")} {data.lactating}</span>
              </div>
            </div>
          </div>

          {/* Trend + Loss */}
          <div className="grid lg:grid-cols-[1.5fr_1fr] gap-3.5">
            <div className="bg-surface border border-border rounded-2xl p-4" style={{ boxShadow: "var(--shadow-card)" }}>
              <div className="flex items-center justify-between mb-2.5">
                <span className="text-sm font-bold text-text">{t("trendTitle")}</span>
                <div className="flex gap-3 text-[11px] text-text3">
                  <Legend className="text-success" label="PSY" />
                  <Legend className="text-text3" label={t("benchmark")} dash />
                </div>
              </div>
              {trend && trend.length >= 2 ? (
                <LineChart
                  h={210}
                  xLabels={trend.map((r) => r.period.slice(2))}
                  bench={data.benchmarks?.PSY?.target ?? undefined}
                  series={[{ data: trend.map((r) => r.psy ?? 0), colorClass: "text-success" }]}
                />
              ) : (
                <div className="py-16 text-center text-text3 text-sm">{t("emptyTrend")}</div>
              )}
            </div>
            <LossCard loss={data.estimated_loss} alerts={data.alerts} t={t} />
          </div>

          {/* Compare + AI summary */}
          <div className="grid lg:grid-cols-[1.5fr_1fr] gap-3.5">
            <CompareCard trend={trend} t={t} />
            <AiSummaryCard data={data} trend={trend} t={t} />
          </div>
        </>
      )}
    </div>
  );
}

function fmt(v: number | null | undefined, d: number) {
  return v != null && Number.isFinite(v) ? v.toFixed(d) : "—";
}

function KpiCard({
  label, desc, value, unit, bench, tier, invert = false, headline = false, spark, t,
}: {
  label: string; desc: string; value: string; unit?: string;
  // bench=null: 국가 벤치마크 미제공 → 비교 자체를 표시하지 않는다(임의 기본값 대체 금지)
  bench: number | null; tier: KpiTier; invert?: boolean; headline?: boolean;
  spark?: (number | null)[]; t: (k: string, v?: Record<string, string | number | Date>) => string;
}) {
  const style = TIER_STYLE[tier];
  const num = parseFloat(value);
  const delta = bench != null && Number.isFinite(num) ? num - bench : null;
  // invert(낮을수록 좋음, 예: NPD): delta ≤ 0 이 좋음
  const deltaGood = delta == null ? false : invert ? delta <= 0 : delta >= 0;
  const sparkData = (spark ?? []).filter((v): v is number => v != null && Number.isFinite(v));
  return (
    <div className="bg-surface border border-border rounded-xl p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold tracking-wide uppercase text-text3">
          {headline && <Star size={12} className="mr-1 inline-block align-[1px] text-primary" fill="currentColor" strokeWidth={0} aria-hidden />}{label}
        </span>
        <span className={`w-2 h-2 rounded-full ${style.dot}`} />
      </div>
      <div className="text-[10px] text-text3 -mt-1">{desc}</div>
      <div className="flex items-baseline gap-1">
        <span className={`font-mono text-3xl font-extrabold leading-none ${style.text}`}>{value}</span>
        {unit && value !== "—" && <span className="text-xs text-text3 font-semibold">{unit}</span>}
      </div>
      {bench != null && (
        <div className="flex items-center gap-1.5 text-[11px] text-text3">
          {delta != null && (
            <span className={`font-mono font-bold ${deltaGood ? "text-success" : style.text}`}>
              {delta > 0 ? "+" : ""}{delta.toFixed(1)}
            </span>
          )}
          <span>{t("vsBench", { v: bench })}</span>
        </div>
      )}
      {sparkData.length >= 2 && (
        <div className={style.text}>
          <Spark data={sparkData} w={210} h={30} />
        </div>
      )}
    </div>
  );
}

function Legend({ label, className, dash }: { label: string; className: string; dash?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`}>
      <span className="w-3.5 border-t-2" style={{ borderStyle: dash ? "dashed" : "solid", borderColor: "currentColor" }} />
      <span className="text-text3">{label}</span>
    </span>
  );
}

function LossCard({
  loss, alerts, t,
}: {
  loss: KpiDashboard["estimated_loss"]; alerts: KpiDashboard["alerts"];
  t: (k: string, v?: Record<string, string | number | Date>) => string;
}) {
  // 손실 추정치가 있으면 표시. 없으면 관리신호(룰엔진)를 심각도별로 집계해 표시 — 가짜 금액 없음.
  const crit = alerts.filter((a) => a.severity === "CRITICAL").length;
  const warn = alerts.filter((a) => a.severity === "WARNING").length;
  return (
    <div className="bg-surface border border-border rounded-2xl p-4" style={{ boxShadow: "var(--shadow-card)" }}>
      <div className="text-sm font-bold text-text">{loss ? t("lossTitle") : t("signalSummaryTitle")}</div>
      {loss ? (
        <>
          <div className="text-xs text-text3 mb-2">{t("lossSub")}</div>
          <div className="font-mono text-3xl font-extrabold text-danger">
            {new Intl.NumberFormat().format(Math.round(loss.amount))} {loss.currency}
          </div>
          <div className="text-[11px] text-text3 mt-1.5 leading-relaxed">
            {t("lostPigs", { n: loss.lost_pigs })} · {loss.basis}
            {loss.demo && <span className="ml-1 px-1.5 py-0.5 rounded bg-insufficient-soft text-insufficient border border-insufficient-border text-[9px] font-bold">DEMO</span>}
          </div>
        </>
      ) : (
        <>
          <div className="text-xs text-text3 mb-3">{t("signalSummarySub")}</div>
          <div className="grid grid-cols-2 gap-2.5">
            <div className="rounded-xl border border-danger/30 bg-red-soft px-3 py-2.5">
              <div className="font-mono text-2xl font-extrabold text-danger">{crit}</div>
              <div className="text-[10px] text-danger font-semibold">{t("sevCritical")}</div>
            </div>
            <div className="rounded-xl border border-warning/40 bg-amber-soft px-3 py-2.5">
              <div className="font-mono text-2xl font-extrabold text-warning">{warn}</div>
              <div className="text-[10px] text-warning font-semibold">{t("sevWarning")}</div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function CompareCard({ trend, t }: { trend?: KpiTrend[]; t: (k: string, v?: Record<string, string | number | Date>) => string }) {
  const rows = trend && trend.length >= 2 ? trend.slice(-2) : null;
  const prev = rows?.[0];
  const curr = rows?.[1];
  const mk = (key: string, label: string, p: number | null | undefined, c: number | null | undefined, d = 1, invert = false) => {
    const delta = p != null && c != null ? c - p : null;
    const goodDir = delta == null ? "text-text3" : (invert ? delta <= 0 : delta >= 0) ? "text-success" : "text-danger";
    return (
      <tr key={key} className="border-t border-border">
        <td className="px-4 py-2.5 text-sm font-semibold text-text2">{label}</td>
        <td className="px-4 py-2.5 text-sm text-right font-mono text-text3">{p != null ? p.toFixed(d) : "—"}</td>
        <td className="px-4 py-2.5 text-sm text-right font-mono font-bold text-text">{c != null ? c.toFixed(d) : "—"}</td>
        <td className="px-4 py-2.5 text-right">
          <span className={`font-mono text-xs font-bold ${goodDir}`}>{delta != null ? (delta > 0 ? "+" : "") + delta.toFixed(d) : "—"}</span>
        </td>
      </tr>
    );
  };
  return (
    <div className="bg-surface border border-border rounded-2xl overflow-hidden" style={{ boxShadow: "var(--shadow-card)" }}>
      <div className="px-4 py-3 text-sm font-bold text-text border-b border-border">{t("compareTitle")}</div>
      {rows ? (
        <table className="w-full">
          <thead>
            <tr className="bg-bg2 text-text3 text-[10px] uppercase tracking-wide">
              <th className="text-left font-bold px-4 py-2">{t("colMetric")}</th>
              <th className="text-right font-bold px-4 py-2">{prev?.period.slice(2)}</th>
              <th className="text-right font-bold px-4 py-2">{curr?.period.slice(2)}</th>
              <th className="text-right font-bold px-4 py-2">Δ</th>
            </tr>
          </thead>
          <tbody>
            {mk("psy", "PSY", prev?.psy, curr?.psy)}
            {mk("npd", "NPD", prev?.npd, curr?.npd, 1, true)}
            {mk("fr", t("frLabel"), prev?.farrowing_rate ?? null, curr?.farrowing_rate ?? null)}
          </tbody>
        </table>
      ) : (
        <div className="py-12 text-center text-text3 text-sm">{t("emptyTrend")}</div>
      )}
    </div>
  );
}

function AiSummaryCard({
  data, trend, t,
}: {
  data: KpiDashboard; trend?: KpiTrend[]; t: (k: string, v?: Record<string, string | number | Date>) => string;
}) {
  // 데이터 기반 정형 요약(LLM 아님 — 판단 위조 없음). Addon #1 활성 시 LLM Renderer로 교체.
  const last2 = trend && trend.length >= 2 ? trend.slice(-2) : null;
  const psyDelta = last2 && last2[0].psy != null && last2[1].psy != null ? last2[1].psy - last2[0].psy : null;
  const crit = data.alerts.filter((a) => a.severity === "CRITICAL").length;
  const summary = t("aiSummaryBody", {
    psy: fmt(data.psy, 1),
    psyDelta: psyDelta != null ? (psyDelta > 0 ? "+" : "") + psyDelta.toFixed(1) : "—",
    fr: data.farrowing_rate != null ? data.farrowing_rate.toFixed(0) : "—",
    signals: data.alerts.length,
    crit,
  });
  return (
    <div className="rounded-2xl bg-console p-4 flex flex-col gap-3 text-white">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center"><Sparkles size={14} className="text-white" /></div>
        <span className="text-sm font-bold">{t("aiSummary")}</span>
        <span className="ml-auto text-[9px] font-bold px-1.5 py-0.5 rounded bg-white/10 text-white/70">{t("aiTemplateBadge")}</span>
      </div>
      <p className="text-[13px] leading-relaxed text-white/85 italic">{summary}</p>
    </div>
  );
}
