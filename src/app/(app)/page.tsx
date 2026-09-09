"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Card, PipeItem } from "@/components/ui";
import Link from "next/link";
import { Brain, ArrowRight, CheckCircle2, ListTodo, Star } from "lucide-react";
import { SEVERITY_ICON, STAGE_ICON } from "@/lib/icons";
import { kpiApi } from "@/lib/api/endpoints/kpi";
import { alertsApi } from "@/lib/api/endpoints/alerts";
import { tasksApi } from "@/lib/api/endpoints/tasks";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import { useEffect } from "react";
import { track } from "@/lib/analytics";
import { psyTier, npdTier, farrowingRateTier, legacyTier, TIER_STYLE, type KpiTier } from "@/lib/kpi/status";
import { reportStatusMismatches, resolveTier } from "@/lib/kpi/statusObservation";
import { resolveKpiCards, reportPresentationGaps } from "@/lib/kpi/presentation";
import type { Alert, Task, KpiBenchmark } from "@/types/api.types";

const SEV_ORDER: Record<string, number> = { CRITICAL: 3, WARNING: 2, INFO: 1, OK: 0 };

function dedupeAlerts(alerts: Alert[]): Alert[] {
  const byKpi = new Map<string, Alert>();
  for (const a of alerts) {
    const key = a.kpi ?? a.rule_id ?? a.message;
    const cur = byKpi.get(key);
    if (!cur || (SEV_ORDER[a.severity] ?? 0) > (SEV_ORDER[cur.severity] ?? 0)) byKpi.set(key, a);
  }
  return [...byKpi.values()].sort((x, y) => (SEV_ORDER[y.severity] ?? 0) - (SEV_ORDER[x.severity] ?? 0));
}

function alertTitle(a: Alert): string {
  const kpi = a.kpi ?? "";
  const msg = a.message ?? "";
  if (!kpi) return msg;
  if (!msg) return kpi;
  return msg.toUpperCase().includes(kpi.toUpperCase()) ? msg : `${kpi} — ${msg}`;
}

// 신규 농장 온보딩 가이드 — 번식 데이터가 없어 KPI가 비어 있을 때 "다음 단계"를 안내.
function StepDot({ done, n }: { done: boolean; n: number }) {
  return done ? (
    <CheckCircle2 size={20} className="text-success flex-shrink-0" />
  ) : (
    <span className="w-5 h-5 rounded-full border-2 border-primary/40 text-primary text-[11px] font-bold flex items-center justify-center flex-shrink-0">{n}</span>
  );
}

function GettingStarted({ hasSow }: { hasSow: boolean }) {
  const t = useTranslations("dashboard.gettingStarted");
  return (
    <div className="rounded-2xl border border-primary/25 bg-primary-soft/30 p-6 mb-5">
      <div className="flex items-center gap-2 mb-1">
        <ListTodo size={16} className="text-primary" />
        <h2 className="text-base font-bold">{t("title")}</h2>
      </div>
      <p className="text-sm text-text2 mb-4">{t("sub")}</p>
      <ol className="space-y-3">
        <li className="flex items-center gap-3">
          <StepDot done={hasSow} n={1} />
          <div className="flex-1 text-sm font-semibold">{t("s1")}</div>
          {!hasSow && <Link href="/sows" className="text-primary hover:underline"><ArrowRight size={16} /></Link>}
        </li>
        <li className="flex items-start gap-3">
          <StepDot done={false} n={2} />
          <div className="flex-1">
            <div className="text-sm font-semibold">{t("s2")}</div>
            <div className="text-xs text-text3 mt-0.5">{t("s2hint")}</div>
          </div>
        </li>
      </ol>
      <Link href="/record" className="inline-flex items-center gap-1.5 mt-4 px-4 py-2 rounded-xl bg-navy text-white text-sm font-semibold hover:opacity-90 transition">
        {t("cta")} <ArrowRight size={14} />
      </Link>
    </div>
  );
}

export default function Dashboard() {
  const t = useTranslations("dashboard");
  const tc = useTranslations("kpiCards");  // 카드 라벨/설명/단위 — KPI 페이지와 공용
  const farmId = useAuthStore((s) => s.activeFarmId);
  const user = useAuthStore((s) => s.user);

  useEffect(() => { track("dashboard_viewed"); }, []);

  const { data, isLoading, isError } = useQuery({
    queryKey: queryKeys.kpi.dashboard(farmId ?? ""),
    queryFn: () => kpiApi.dashboard(farmId!),
    enabled: !!farmId,
    refetchInterval: 5 * 60 * 1000,
  });
  const { data: trendData } = useQuery({
    queryKey: ["kpi", "trend", farmId, 6],
    queryFn: () => kpiApi.trend(farmId!, "PSY", 6),
    enabled: !!farmId,
  });
  // 국가별 표현 정책 — 실패해도 기본 카드 순서로 렌더된다(A3 폴백). 국가 추정 없음.
  const { data: presentation } = useQuery({
    queryKey: queryKeys.kpi.presentation(farmId ?? ""),
    queryFn: () => kpiApi.presentation(farmId!),
    enabled: !!farmId,
    retry: 1,
  });
  const kpiCards = resolveKpiCards(presentation);
  useEffect(() => { reportPresentationGaps(kpiCards); },
    [kpiCards.source, kpiCards.unknownCodes.join(",")]);

  const { data: overdueData } = useQuery({
    queryKey: queryKeys.alerts.overdue(farmId ?? ""),
    queryFn: () => alertsApi.overdue(farmId!),
    enabled: !!farmId,
  });

  // ADR-KPI-08 Phase 2 — dual observation. 백엔드 판정 ↔ 현행 프론트 tier 불일치를 관측만 한다.
  // 화면 판정은 그대로(전환은 Phase 3). 불일치는 놓친 경보의 단서가 된다.
  useEffect(() => {
    if (!data) return;
    reportStatusMismatches(data.kpi_status, {
      PSY: psyTier(data.psy),
      NPD: npdTier(data.npd),
      FARROWING_RATE: farrowingRateTier(data.farrowing_rate),
    });
  }, [data]);
  const { data: tasks } = useQuery({
    queryKey: queryKeys.tasks.list(farmId ?? "", "OPEN"),
    queryFn: () => tasksApi.list(farmId!, "OPEN"),
    enabled: !!farmId,
  });

  const farmName = user?.name ?? "My Farm";

  return (
    <div className="p-7 max-w-[1600px]">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-[22px] font-extrabold tracking-tight flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse shadow-[0_0_8px_var(--color-primary)]" />
          {t("title")}
        </h1>
        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-primary-soft text-primary border border-primary/20 rounded-full text-xs font-semibold">
          <Brain size={14} /> {t("aiActive")}
        </span>
      </div>

      {isLoading && <DashboardSkeleton />}
      {!farmId && <div className="text-center py-20 text-text3 text-sm">{t("selectFarm")}</div>}
      {isError && farmId && !isLoading && (
        <div className="rounded-2xl border border-danger/30 bg-danger/5 py-16 text-center">
          <p className="font-bold text-danger">{t("loadError")}</p>
          <p className="text-xs text-text3 mt-1">{t("loadErrorDesc")}</p>
        </div>
      )}

      {data && (() => {
        // ADR-KPI-08 Phase 3 — 백엔드(국가별 Rule Engine) 판정을 렌더에 사용.
        // legacy tier는 백엔드가 status를 주지 않을 때만의 폴백(Phase 4에서 제거).
        const psyT = resolveTier(data.kpi_status, "PSY", psyTier(data.psy));
        const npdT = resolveTier(data.kpi_status, "NPD", npdTier(data.npd));
        const frT = resolveTier(data.kpi_status, "FARROWING_RATE", farrowingRateTier(data.farrowing_rate));
        const alerts = dedupeAlerts(data.alerts ?? []);
        const topAlert = alerts[0];
        const insufficient: string[] = [];
        if (psyT === "insufficient") insufficient.push("PSY");
        if (npdT === "insufficient") insufficient.push(t("statNpd"));
        if (frT === "insufficient") insufficient.push(t("statFarrowingRate"));
        const validCount = 3 - insufficient.length;
        const quality = Math.round((validCount / 3) * 100);
        const overdueTotal = overdueData?.total ?? 0;

        let verdict: string;
        if (!data.active_sows && !alerts.length) verdict = t("aiDiagNoData");
        else {
          const risk = topAlert ? topAlert.kpi : (insufficient.length ? t("riskDataQuality") : null);
          if (!risk) verdict = t("aiDiagHealthy");
          else {
            verdict = t("aiDiagRisk", { risk });
            if (insufficient.length) verdict += t("aiDiagInsufficient", { metrics: insufficient.join(", ") });
          }
        }

        return (
          <>
            {validCount === 0 && <GettingStarted hasSow={!!data.active_sows} />}
            {/* ── HERO: AI 운영 진단 ── */}
            <div className="rounded-2xl border border-primary/20 bg-gradient-to-br from-primary-soft/50 to-surface p-6 mb-5">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <Brain className="text-primary" size={20} />
                  </div>
                  <div>
                    <div className="text-[11px] font-bold text-primary uppercase tracking-wider">{t("aiDiagTitle")}</div>
                    <div className="text-xs text-text3">{farmName} · {data.active_sows}{t("unitHead")}</div>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-[10px] text-text3 font-semibold">{t("dataQualityLabel")}</div>
                  <div className={`text-xl font-extrabold font-mono ${quality >= 66 ? "text-success" : quality >= 33 ? "text-warning" : "text-danger"}`}>{quality}%</div>
                </div>
              </div>
              <p className="text-[15px] text-text1 leading-relaxed font-medium mb-3">{verdict}</p>
              {data.estimated_loss && data.estimated_loss.amount > 0 && (
                <div className="inline-flex items-center gap-2 mb-4 px-3 py-1.5 rounded-lg bg-danger/8 border border-danger/20">
                  <span className="text-[11px] font-semibold text-text3">{t("estLoss")}</span>
                  <span className="text-sm font-extrabold font-mono text-danger">
                    {data.estimated_loss.currency}{data.estimated_loss.amount.toLocaleString()}
                  </span>
                  <span className="text-[11px] text-text3">· {t("lostPigs", { n: data.estimated_loss.lost_pigs })}</span>
                  {data.estimated_loss.demo && (
                    <span className="text-[9px] font-bold bg-bg2 text-text3 rounded px-1 py-0.5">{t("demoBadge")}</span>
                  )}
                </div>
              )}
              <div className="flex gap-2 flex-wrap">
                <Link href="/record" className="inline-flex items-center gap-1.5 bg-primary text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-primary/90 transition">
                  {t("actionRecord")} <ArrowRight size={14} />
                </Link>
                {overdueTotal > 0 && (
                  <Link href="/alerts" className="inline-flex items-center gap-1.5 border border-border bg-surface text-text2 px-4 py-2 rounded-lg text-sm font-semibold hover:border-primary transition">
                    {t("actionAlerts", { n: overdueTotal })}
                  </Link>
                )}
              </div>
            </div>

            {/* ── 오늘 할 행동 ── */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2.5">
                <h2 className="text-sm font-bold flex items-center gap-2">
                  <ListTodo size={14} /> {t("todayActions")}
                  {!!tasks?.length && <span className="text-[10px] font-bold bg-primary/10 text-primary rounded-full px-1.5 py-0.5">{tasks.length}</span>}
                </h2>
                <Link href="/tasks" className="text-xs text-primary font-semibold">{t("viewAllTasks")} →</Link>
              </div>
              {!tasks?.length ? (
                <div className="bg-bg2/40 border border-border rounded-xl p-5 flex items-start gap-3">
                  <CheckCircle2 className="text-success flex-shrink-0 mt-0.5" size={16} />
                  <p className="text-xs text-text2 leading-relaxed">{t("noTasks")}</p>
                </div>
              ) : (
                <div className="space-y-1.5">
                  {tasks.slice(0, 5).map((task) => (
                    <TaskRow key={task.id} task={task} />
                  ))}
                </div>
              )}
            </div>

            {/* ── 보조: 핵심 지표 ── */}
            <div className="text-[11px] font-bold text-text3 uppercase tracking-widest mb-2">{t("kpiSummary")}</div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
              {/* 카드 목록·순서·명칭은 서버(Presentation Policy) 확정 — 프론트 재정렬·재필터 금지 */}
              {kpiCards.cards.map(({ meta, localLabel, isHeadline }) => {
                const raw = meta.value(data);
                if (raw == null && meta.kpi_code === "SOW_TURNOVER") return null;  // 값 없으면 카드 자체 미표시(기존 동작 유지)
                const tier = resolveTier(data.kpi_status, meta.kpi_code, legacyTier(meta.kpi_code, raw));
                const unit = meta.unitKey ? tc(meta.unitKey) : "";
                return (
                  <KpiCard
                    key={meta.kpi_code}
                    t={t}
                    label={localLabel ?? meta.literalLabel ?? tc(meta.labelKey)}
                    headline={isHeadline}
                    tier={tier}
                    value={raw != null ? `${raw.toFixed(meta.digits)}${unit}` : ""}
                    benchmark={meta.benchKey ? data.benchmarks?.[meta.benchKey] : undefined}
                    trend={meta.series && trendData ? meta.series(trendData) : undefined}
                  />
                );
              })}
              <KpiCard
                t={t}
                label={t("statAiAlerts")}
                tier={topAlert ? (topAlert.severity === "CRITICAL" ? "critical" : topAlert.severity === "WARNING" ? "warning" : "normal") : "normal"}
                value={String(alerts.length)}
                rawTierLabel={t("severeWarn", {
                  crit: alerts.filter((a) => a.severity === "CRITICAL").length,
                  warn: alerts.filter((a) => a.severity === "WARNING").length,
                })}
              />
            </div>

            {/* Pipeline */}
            <div className="flex gap-1 mb-5 overflow-x-auto">
              <PipeItem icon={<StageIcon stage="MATING" />} count={data.week_matings} name={t("pMating")} />
              <span className="flex items-center text-text3 text-xs">→</span>
              <PipeItem icon={<StageIcon stage="PREGNANT" />} count={data.gestating} name={t("pPregnant")} active />
              <span className="flex items-center text-text3 text-xs">→</span>
              <PipeItem icon={<StageIcon stage="FARROWING" />} count={data.week_farrowings} name={t("pFarrowing")} />
              <span className="flex items-center text-text3 text-xs">→</span>
              <PipeItem icon={<StageIcon stage="LACTATING" />} count={data.lactating} name={t("pLactating")} />
              <span className="flex items-center text-text3 text-xs">→</span>
              <PipeItem icon={<StageIcon stage="WEANING" />} count={data.week_weanings} name={t("pWeaning")} />
            </div>

            {/* 2-col: 알림(dedup) | 군집 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Card title={t("ruleAlerts")} badge={t("alertCount", { n: alerts.length })} badgeColor="green" className="mb-3" children={<></>} />
                {alerts.length === 0 ? (
                  <div className="bg-bg2/40 border border-border rounded-xl p-5 flex items-start gap-3">
                    <CheckCircle2 className="text-success flex-shrink-0 mt-0.5" size={16} />
                    <p className="text-xs text-text2 leading-relaxed">{t("emptyAlertsGuide")}</p>
                  </div>
                ) : (
                  alerts.map((alert, i) => <AlertCard key={i} alert={alert} />)
                )}
              </div>
              <div>
                <Card title={t("herdStatus")}>
                  <table className="w-full text-xs">
                    <tbody>
                      {[
                        { label: t("herdPregnant"), value: data.gestating },
                        { label: t("herdLactating"), value: data.lactating },
                        { label: t("herdWeanedOpen"), value: data.weaned },
                        { label: t("herdActiveTotal"), value: data.active_sows },
                      ].map((row, i) => (
                        <tr key={i} className="border-b border-border last:border-0">
                          <td className="py-2.5 text-text2">{row.label}</td>
                          <td className="py-2.5 text-right font-mono font-bold">{row.value}{t("unitHead")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
              </div>
            </div>
          </>
        );
      })()}
    </div>
  );
}

function TaskRow({ task }: { task: Task }) {
  const dot = task.priority === 1 ? "bg-danger" : task.priority === 2 ? "bg-warning" : "bg-text3";
  return (
    <Link href="/tasks" className="flex items-center gap-3 border border-border rounded-xl px-4 py-2.5 bg-surface hover:border-primary transition">
      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dot}`} />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold truncate">{task.title}</div>
        {(task.ear_tag || task.overdue_days) && (
          <div className="text-[11px] text-text3">
            {task.ear_tag}{task.overdue_days ? ` · +${task.overdue_days}d` : ""}
          </div>
        )}
      </div>
      <ArrowRight size={14} className="text-text3 flex-shrink-0" />
    </Link>
  );
}

function Sparkline({ data }: { data: (number | null)[] }) {
  const pts = data.map((v, i) => ({ v, i })).filter((p): p is { v: number; i: number } => p.v != null);
  if (pts.length < 2) return null;
  const vals = pts.map((p) => p.v);
  const min = Math.min(...vals), max = Math.max(...vals), range = max - min || 1;
  const W = 54, H = 16;
  const px = (i: number) => (data.length > 1 ? (i / (data.length - 1)) * W : 0);
  const py = (v: number) => H - ((v - min) / range) * (H - 2) - 1;
  const d = pts.map((p, k) => `${k === 0 ? "M" : "L"}${px(p.i).toFixed(1)},${py(p.v).toFixed(1)}`).join(" ");
  const last = pts[pts.length - 1];
  return (
    <svg width={W} height={H} className="flex-shrink-0" aria-hidden>
      <path d={d} fill="none" stroke="var(--color-text3)" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={px(last.i)} cy={py(last.v)} r="1.6" fill="var(--color-primary)" />
    </svg>
  );
}

function KpiCard({ t, label, tier, value, rawTierLabel, benchmark, trend, headline = false }: {
  t: ReturnType<typeof useTranslations>; label: string; tier: KpiTier; value: string; rawTierLabel?: string;
  benchmark?: KpiBenchmark; trend?: (number | null)[]; headline?: boolean;
}) {
  const s = TIER_STYLE[tier];
  const tierLabel = rawTierLabel ?? t(
    tier === "normal" ? "tierGood" : tier === "warning" ? "tierWarning" : tier === "critical" ? "tierCritical" : "tierInsufficient",
  );
  return (
    <div className="rounded-2xl border border-border bg-surface px-4 py-3.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] text-text3 font-semibold">
          {headline && <Star size={12} className="mr-1 inline-block align-[1px] text-primary" fill="currentColor" strokeWidth={0} aria-hidden />}{label}
        </span>
        {trend && <Sparkline data={trend} />}
      </div>
      {tier === "insufficient" ? (
        <div className="text-base font-bold text-text3 mt-2">{t("dataInsufficient")}</div>
      ) : (
        <div className={`text-[28px] font-extrabold font-mono mt-1 tracking-tight ${s.text}`}>{value}</div>
      )}
      <div className={`inline-flex items-center gap-1.5 mt-2 px-2 py-0.5 rounded-md text-[10px] font-bold border ${s.chip}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />{tierLabel}
      </div>
      {benchmark && (benchmark.avg != null || benchmark.top25 != null) && (
        <div className="mt-2 pt-2 border-t border-border/60 flex gap-3 text-[10px] font-mono text-text3">
          {benchmark.avg != null && <span>{t("benchAvg")} <b className="text-text2">{benchmark.avg.toFixed(1)}</b></span>}
          {benchmark.top25 != null && <span>{t("benchTop25")} <b className="text-text2">{benchmark.top25.toFixed(1)}</b></span>}
        </div>
      )}
    </div>
  );
}

function StageIcon({ stage }: { stage: keyof typeof STAGE_ICON }) {
  const Icon = STAGE_ICON[stage];
  return <Icon size={16} />;
}

function AlertCard({ alert }: { alert: Alert }) {
  const t = useTranslations("dashboard");
  const Icon = SEVERITY_ICON[alert.severity] ?? SEVERITY_ICON.INFO;
  const cls = alert.severity === "CRITICAL" ? "bg-red-soft border-danger/40 text-danger"
    : alert.severity === "WARNING" ? "bg-amber-soft border-warning/40 text-warning"
    : "bg-green-soft border-success/30 text-success";
  return (
    <div className={`border rounded-xl px-4 py-3 mb-2 flex items-start gap-3 ${cls}`}>
      <Icon size={16} className="flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="text-xs font-semibold">{alertTitle(alert)}</div>
        {alert.current_value != null && (
          <div className="text-[10px] mt-0.5 opacity-75">
            {t("currentTarget", { cur: alert.current_value.toFixed(1), tgt: alert.target_value?.toFixed(1) ?? "-" })}
          </div>
        )}
      </div>
    </div>
  );
}

// 대시보드 로딩 스켈레톤 — 실제 레이아웃(진단카드·KPI 4카드·파이프라인·2단) 형태의 shimmer.
function SkelBlock({ className = "" }: { className?: string }) {
  return <div className={`skeleton rounded-xl ${className}`} />;
}

function DashboardSkeleton() {
  const t = useTranslations("dashboard");
  return (
    <div className="space-y-5" aria-busy="true" aria-label={t("loading")}>
      {/* AI 진단 카드 */}
      <div className="rounded-2xl border border-border bg-surface p-5">
        <div className="flex items-start gap-3">
          <SkelBlock className="w-9 h-9 rounded-lg" />
          <div className="flex-1 space-y-2">
            <SkelBlock className="h-3 w-40" />
            <SkelBlock className="h-3 w-24" />
          </div>
          <SkelBlock className="h-8 w-16" />
        </div>
        <SkelBlock className="h-5 w-64 mt-4" />
        <SkelBlock className="h-9 w-40 mt-4 rounded-lg" />
      </div>
      {/* KPI 4카드 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-2xl border border-border bg-surface p-4 space-y-3">
            <SkelBlock className="h-3 w-20" />
            <SkelBlock className="h-7 w-16" />
            <SkelBlock className="h-4 w-24 rounded-full" />
          </div>
        ))}
      </div>
      {/* 파이프라인 5칸 */}
      <div className="grid grid-cols-3 lg:grid-cols-5 gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="rounded-2xl border border-border bg-surface p-5 flex flex-col items-center gap-2">
            <SkelBlock className="w-6 h-6 rounded-full" />
            <SkelBlock className="h-6 w-8" />
            <SkelBlock className="h-3 w-12" />
          </div>
        ))}
      </div>
      {/* 하단 2단 (알림 / 돈군상태) */}
      <div className="grid lg:grid-cols-2 gap-3">
        {Array.from({ length: 2 }).map((_, col) => (
          <div key={col} className="rounded-2xl border border-border bg-surface p-5 space-y-3">
            <SkelBlock className="h-4 w-32" />
            {Array.from({ length: 4 }).map((_, i) => <SkelBlock key={i} className="h-10 w-full" />)}
          </div>
        ))}
      </div>
    </div>
  );
}
