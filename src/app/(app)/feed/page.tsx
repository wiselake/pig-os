"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { localToday } from "@/lib/date";
import { feedApi, type CreateFeedRecordRequest, type FeedMetric } from "@/lib/api/endpoints/feed";
import { farmsApi } from "@/lib/api/endpoints/farms";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import { canEntry, canManage } from "@/lib/auth/permissions";
import { useActiveRole } from "@/lib/auth/useActiveRole";

const CURRENCIES = ["USD", "KRW", "CNY", "VND", "THB", "BRL", "MXN", "EUR", "PHP", "RUB"];

function ym(d: string): string {
  return d.slice(0, 7);
}

function prevMonth(period: string): string {
  const [y, m] = period.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 2, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

function shiftMonths(period: string, n: number): string {
  const [y, m] = period.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + n, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

function fmtNum(v: number | null | undefined, digits = 0): string {
  return v == null ? "—" : v.toLocaleString(undefined, { maximumFractionDigits: digits });
}

export default function FeedPage() {
  const t = useTranslations("feed");
  const farmId = useAuthStore((s) => s.activeFarmId);
  const role = useActiveRole();
  const canWrite = canEntry(role);
  const canDelete = canManage(role);  // 백엔드 DELETE는 OWNER/MANAGER만 (WORKER 제외)
  const queryClient = useQueryClient();

  const { data: farm } = useQuery({
    queryKey: queryKeys.farms.detail(farmId ?? ""),
    queryFn: () => farmsApi.get(farmId!),
    enabled: !!farmId,
  });
  const farmCurrency = farm?.currency ?? "USD";

  const [recordDate, setRecordDate] = useState(localToday());
  const [feedType, setFeedType] = useState("");
  const [quantityKg, setQuantityKg] = useState("");
  const [unitCost, setUnitCost] = useState("");
  const [currency, setCurrency] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);
  // B-1: 기본 기간 = 직전 완료월. 진행 중인 달인지는 서버가 농장 현지 날짜로 판정한다(summary.period.partial).
  const [period, setPeriod] = useState(prevMonth(ym(localToday())));

  const { data: records = [], isLoading } = useQuery({
    queryKey: ["feed", farmId],
    queryFn: () => feedApi.list(farmId!),
    enabled: !!farmId,
  });

  // 결과 화면 — 수기 입력(AS_RECORDED) 기준. 값 없음(null)은 0 이 아니라 "못 냈다"(reason) 로 그린다.
  const { data: summary } = useQuery({
    queryKey: ["feed", farmId, "summary", period, "AS_RECORDED"],
    queryFn: () => feedApi.summary(farmId!, period, "AS_RECORDED"),
    enabled: !!farmId,
  });
  const monthsFrom = useMemo(() => shiftMonths(period, -5), [period]);
  const { data: months = [] } = useQuery({
    queryKey: ["feed", farmId, "months", monthsFrom, period, "AS_RECORDED"],
    queryFn: () => feedApi.months(farmId!, monthsFrom, period, "AS_RECORDED"),
    enabled: !!farmId,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["feed", farmId] });
  };

  const createMut = useMutation({
    mutationFn: (body: CreateFeedRecordRequest) => feedApi.create(farmId!, body),
    onSuccess: () => {
      invalidate();
      setQuantityKg("");
      setFeedType("");
      setUnitCost("");
      setErr(null);
    },
    onError: () => setErr(t("saveError")),
  });

  const delMut = useMutation({
    mutationFn: (id: string) => feedApi.delete(farmId!, id),
    onSuccess: () => {
      invalidate();
      setErr(null);
    },
    onError: () => setErr(t("deleteError")),
  });

  if (!farmId) {
    return <div className="p-6 text-text3">{t("noFarm")}</div>;
  }

  function submit() {
    const q = parseFloat(quantityKg);
    if (!q || q <= 0) {
      setErr(t("qtyError"));
      return;
    }
    const uc = unitCost.trim() === "" ? null : parseFloat(unitCost);
    if (uc !== null && (Number.isNaN(uc) || uc < 0)) {
      setErr(t("costError"));
      return;
    }
    createMut.mutate({
      record_date: recordDate,
      quantity_kg: q,
      feed_type: feedType.trim() || null,
      unit_cost: uc,
      currency: uc === null ? null : (currency || farmCurrency),
    });
  }

  const m = summary?.metrics ?? {};
  const reasonText = (r: FeedMetric | undefined): string => {
    if (!r || r.value != null) return "";
    const key = r.reason ?? "no_data";
    return t.has(`reason.${key}`) ? t(`reason.${key}`) : key;
  };
  const costMetric = m["FEED_COST"];
  const partialCost = costMetric?.evidence?.["partial_cost"] as number | undefined;
  const uncosted = costMetric?.evidence?.["uncosted_rows"] as number | undefined;
  const shares = (m["FEED_MIX_SHARE"]?.evidence?.["shares"] ?? {}) as Record<string, number>;
  const qtyChange = m["FEED_QTY_CHANGE"];
  const costChange = m["FEED_COST_CHANGE"];
  const cur = summary?.currency ?? farmCurrency;
  const partial = summary?.period?.partial === true;

  return (
    <div className="ml-[220px] max-md:ml-0 p-6 max-w-5xl">
      <h1 className="text-2xl font-extrabold text-text">{t("title")}</h1>

      {/* B-2: 영역 B "사료 급여·소비" — 여기에 기록한 급여량(AS_RECORDED). "FCR 입력원" 부제는 이 영역에만 둔다.
          영역 A "사료 입고 · PigPlan 연계"(DELIVERED)는 서버가 REFERENCE_VISIBLE 로 판정할 때만 따로 그린다(W6). */}
      <section data-testid="feed-area-fed" className="mt-4">
      <h2 className="text-lg font-bold text-text">{t("fedTitle")}</h2>
      <p className="text-sm text-text3 mt-1">{t("subtitle")}</p>

      {canWrite && (
        <div className="mt-6 rounded-2xl border border-border bg-surface p-5">
          <div className="text-sm font-bold text-text mb-1">{t("add")}</div>
          <p className="text-xs text-text3 mb-3">{t("guidance")}</p>
          <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
            <label className="block">
              <span className="text-xs text-text3">{t("recordDate")}</span>
              <input type="date" value={recordDate} onChange={(e) => setRecordDate(e.target.value)}
                     className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm" />
            </label>
            <label className="block">
              <span className="text-xs text-text3">{t("feedType")}</span>
              <input type="text" value={feedType} onChange={(e) => setFeedType(e.target.value)}
                     placeholder={t("feedTypePlaceholder")}
                     className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm" />
            </label>
            <label className="block">
              <span className="text-xs text-text3">{t("quantityKg")}</span>
              <input type="number" min="0" step="0.1" value={quantityKg}
                     onChange={(e) => setQuantityKg(e.target.value)}
                     className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm font-mono" />
            </label>
            <label className="block">
              <span className="text-xs text-text3">{t("unitCost")}</span>
              <input type="number" min="0" step="0.01" value={unitCost} aria-label={t("unitCost")}
                     onChange={(e) => setUnitCost(e.target.value)} placeholder={t("unitCostPlaceholder")}
                     className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm font-mono" />
            </label>
            <label className="block">
              <span className="text-xs text-text3">{t("currency")}</span>
              <select value={currency || farmCurrency} aria-label={t("currency")} onChange={(e) => setCurrency(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm">
                {[farmCurrency, ...CURRENCIES.filter((c) => c !== farmCurrency)].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>
          </div>
          <p className="text-[11px] text-text3 mt-2">{t("costHint")}</p>
          {err && <div className="mt-2 text-xs text-danger">{err}</div>}
          <button onClick={submit} disabled={createMut.isPending}
                  className="mt-4 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {createMut.isPending ? t("saving") : t("save")}
          </button>
        </div>
      )}

      {/* ── 월 결과 (엔진 계산 · 판정 없음 · null ≠ 0) ────────────────────────── */}
      <div className="mt-6 rounded-2xl border border-border bg-surface p-5" data-testid="feed-summary">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <div className="text-sm font-bold text-text">{t("summaryTitle")}</div>
            <div className="text-[11px] text-text3">{t("basisRecorded")}</div>
            {partial && (
              <span data-testid="feed-mtd-badge" className="inline-block mt-1 rounded-full bg-bg2 px-2 py-0.5 text-[11px] font-semibold text-warning">
                {t("mtdBadge")}
              </span>
            )}
          </div>
          <input type="month" value={period} aria-label={t("month")} onChange={(e) => e.target.value && setPeriod(e.target.value)}
                 className="rounded-lg border border-border bg-bg px-3 py-1.5 text-sm" />
        </div>
        {summary?.no_data ? (
          <div className="mt-4 rounded-xl border border-dashed border-border p-5 text-center text-text3 text-sm">{t("noDataMonth")}</div>
        ) : (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label={t("mQty")} value={fmtNum(m["FEED_QTY"]?.value, 1)} unit="kg" note={reasonText(m["FEED_QTY"])} />
            <Stat label={t("mCost")} value={costMetric?.value != null ? fmtNum(costMetric.value, 0) : (partialCost != null ? fmtNum(partialCost, 0) : "—")} unit={cur}
                  note={costMetric?.value == null
                    ? (partialCost != null ? t("costPartial", { n: uncosted ?? 0 }) : reasonText(costMetric))
                    : ""} warn={costMetric?.value == null && partialCost != null} />
            <Stat label={t("mUnitPrice")} value={fmtNum(m["FEED_UNIT_PRICE"]?.value, 2)} unit={`${cur}/kg`} note={reasonText(m["FEED_UNIT_PRICE"])} />
            {!partial && (   /* B-1: 진행 중인 달은 비교 UI 를 그리지 않는다 */
              <Stat label={t("mChange")} value={qtyChange?.value != null ? `${qtyChange.value > 0 ? "+" : ""}${fmtNum(qtyChange.value, 1)}` : "—"} unit="kg"
                    note={qtyChange?.value == null ? reasonText(qtyChange) : (costChange?.value != null ? `${t("mCostChange")} ${costChange.value > 0 ? "+" : ""}${fmtNum(costChange.value, 0)} ${cur}` : "")} />
            )}
          </div>
        )}
        {!summary?.no_data && Object.keys(shares).length > 0 && (
          <div className="mt-3 text-xs text-text3">
            <span className="font-semibold text-text2">{t("mMix")}: </span>
            {Object.entries(shares).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${(v * 100).toFixed(0)}%`).join(" · ")}
          </div>
        )}
        {months.length > 0 && (
          <table className="w-full text-xs mt-4">
            <thead className="text-text3">
              <tr>
                <th className="text-left py-1">{t("month")}</th>
                <th className="text-right py-1">{t("mQty")} (kg)</th>
                <th className="text-right py-1">{t("mCost")} ({cur})</th>
                <th className="text-right py-1">{t("mUnitPrice")}</th>
                <th className="text-left py-1 pl-3">{t("mDominant")}</th>
              </tr>
            </thead>
            <tbody>
              {months.map((mo) => (
                <tr key={mo.period} className="border-t border-border">
                  <td className="py-1 font-mono">
                    {mo.period}
                    {mo.partial && <span className="ml-1 font-sans text-[10px] text-warning">{t("mtdRow")}</span>}
                  </td>
                  <td className="py-1 text-right font-mono">{fmtNum(mo.feed_qty_kg, 1)}</td>
                  <td className="py-1 text-right font-mono">
                    {mo.feed_cost != null ? fmtNum(mo.feed_cost, 0) : mo.partial_cost != null ? `${fmtNum(mo.partial_cost, 0)}*` : "—"}
                  </td>
                  <td className="py-1 text-right font-mono">{fmtNum(mo.unit_price, 2)}</td>
                  <td className="py-1 pl-3">{mo.dominant_type ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {months.some((mo) => mo.feed_cost == null && mo.partial_cost != null) && (
          <p className="text-[11px] text-text3 mt-1">* {t("partialLegend")}</p>
        )}
      </div>

      <div className="mt-6">
        <div className="text-sm font-bold text-text mb-2">{t("recent")}</div>
        {isLoading ? (
          <div className="text-text3 text-sm">…</div>
        ) : records.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border p-6 text-center text-text3 text-sm">
            {t("empty")}
          </div>
        ) : (
          <div className="rounded-2xl border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-bg2 text-text3 text-xs">
                <tr>
                  <th className="text-left px-4 py-2">{t("recordDate")}</th>
                  <th className="text-left px-4 py-2">{t("feedType")}</th>
                  <th className="text-right px-4 py-2">{t("quantityKg")}</th>
                  <th className="text-right px-4 py-2">{t("unitCost")}</th>
                  {canDelete && <th className="px-4 py-2" />}
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id} className="border-t border-border">
                    <td className="px-4 py-2 font-mono">{r.record_date}</td>
                    <td className="px-4 py-2">{r.feed_type ?? "—"}</td>
                    <td className="px-4 py-2 text-right font-mono">{r.quantity_kg}</td>
                    <td className="px-4 py-2 text-right font-mono">{r.unit_cost != null ? `${r.unit_cost} ${r.currency ?? ""}` : "—"}</td>
                    {canDelete && (
                      <td className="px-4 py-2 text-right">
                        <button onClick={() => delMut.mutate(r.id)} disabled={delMut.isPending}
                                className="text-xs text-danger hover:underline disabled:opacity-50">{t("delete")}</button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      </section>
    </div>
  );
}

function Stat({ label, value, unit, note, warn }: { label: string; value: string; unit: string; note?: string; warn?: boolean }) {
  return (
    <div className="rounded-xl border border-border bg-bg p-3">
      <div className="text-[11px] text-text3">{label}</div>
      <div className={`font-mono text-lg font-extrabold ${warn ? "text-warning" : "text-text"}`}>
        {value} <span className="text-xs font-normal text-text3">{unit}</span>
      </div>
      {note ? <div className={`text-[11px] mt-0.5 ${warn ? "text-warning" : "text-text3"}`}>{note}</div> : null}
    </div>
  );
}
