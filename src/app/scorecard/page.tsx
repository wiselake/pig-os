"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Sparkles, ArrowRight, RotateCcw, Trophy, Share2, ImageDown } from "lucide-react";
import { scorecardApi } from "@/lib/api/endpoints/scorecard";
import { authApi } from "@/lib/api/endpoints/auth";
import type { ScorecardBand, ScorecardResponse } from "@/types/api.types";

// 국가 벤치마크가 시드된 헤드라인 3종만 노출(모든 입력이 채점됨 → 깔끔한 퍼널).
// 백엔드는 born_alive/weaned도 수용(향후 벤치 시드 시 확장).
const METRICS = [
  { labelKey: "psy", field: "psy" as const, code: "PSY" },
  { labelKey: "fr", field: "farrowing_rate" as const, code: "FARROWING_RATE" },
  { labelKey: "npd", field: "npd" as const, code: "NPD" },
];
const CODE_TO_LABEL: Record<string, string> = {
  PSY: "psy", FARROWING_RATE: "fr", BORN_ALIVE: "ba", WEANED_COUNT: "weaned", NPD: "npd",
};

const BAND_STYLE: Record<ScorecardBand, { cls: string; ring: string }> = {
  TOP: { cls: "bg-green-soft text-success border-success/40", ring: "text-success" },
  GOOD: { cls: "bg-primary-soft text-primary border-primary/40", ring: "text-primary" },
  FAIR: { cls: "bg-amber-soft text-warning border-warning/40", ring: "text-warning" },
  LOW: { cls: "bg-red-soft text-danger border-danger/40", ring: "text-danger" },
  NA: { cls: "bg-bg2 text-text3 border-border", ring: "text-text3" },
};

export default function ScorecardPage() {
  const t = useTranslations("scorecard");
  const [country, setCountry] = useState("KR");
  const [vals, setVals] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);

  const { data: countries } = useQuery({
    queryKey: ["config", "countries"],
    queryFn: () => authApi.countries(),
    staleTime: Infinity,
  });

  const mut = useMutation<ScorecardResponse>({
    mutationFn: () => {
      const body: Record<string, number | string> = { country };
      for (const m of METRICS) {
        const raw = vals[m.field];
        if (raw != null && raw !== "") body[m.field] = Number(raw);
      }
      return scorecardApi.compute(body as never);
    },
    onError: () => setErr(t("needOne")),
  });

  const submit = () => {
    setErr(null);
    if (METRICS.every((m) => !vals[m.field])) { setErr(t("needOne")); return; }
    mut.mutate();
  };
  const reset = () => { mut.reset(); setVals({}); setErr(null); };

  // 공유 링크로 진입 시 입력 복원 + 자동 채점(수신자가 동일 결과를 봄 → 바이럴 루프).
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const c = q.get("c"); if (c) setCountry(c.toUpperCase());
    const v: Record<string, string> = {};
    for (const m of METRICS) { const x = q.get(m.field); if (x) v[m.field] = x; }
    if (Object.keys(v).length) { setVals(v); setTimeout(() => mut.mutate(), 0); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // SNS/카톡 공유용 스코어 이미지(PNG) 생성 — 클라이언트 canvas(서버 불필요).
  const BAND_HEX: Record<string, string> = { TOP: "#16a34a", GOOD: "#2563eb", FAIR: "#d97706", LOW: "#dc2626", NA: "#94a3b8" };
  const saveImage = async () => {
    if (!result) return;
    const W = 800, H = 1000, c = document.createElement("canvas");
    c.width = W; c.height = H;
    const x = c.getContext("2d"); if (!x) return;
    x.fillStyle = "#0D1B3E"; x.fillRect(0, 0, W, H);
    x.textAlign = "center";
    x.fillStyle = "#7dd3a8"; x.font = "bold 30px sans-serif"; x.fillText("PigOS", W / 2, 90);
    x.fillStyle = "#cbd5e1"; x.font = "500 26px sans-serif"; x.fillText(t("title"), W / 2, 135);
    // 종합 점수
    x.fillStyle = BAND_HEX[result.overall_band]; x.font = "bold 200px sans-serif";
    x.fillText(String(result.overall_score), W / 2, 380);
    x.fillStyle = "#ffffff"; x.font = "bold 34px sans-serif"; x.fillText(t(`band${result.overall_band}`), W / 2, 445);
    // 지표
    let y = 560; x.textAlign = "left";
    for (const m of result.metrics.slice(0, 3)) {
      x.fillStyle = "#e2e8f0"; x.font = "600 30px sans-serif";
      x.fillText(t(CODE_TO_LABEL[m.code] ?? m.code).replace(/\s*\(.*\)/, ""), 90, y);
      x.textAlign = "right"; x.fillStyle = "#ffffff"; x.font = "bold 34px sans-serif";
      x.fillText(String(m.value), 640, y);
      x.fillStyle = BAND_HEX[m.band]; x.font = "bold 22px sans-serif";
      x.fillText(t(`band${m.band}`), 710, y); x.textAlign = "left"; y += 80;
    }
    x.textAlign = "center"; x.fillStyle = "#64748b"; x.font = "500 26px sans-serif";
    x.fillText("pigos.io/scorecard", W / 2, 940);
    const blob: Blob | null = await new Promise((r) => c.toBlob(r, "image/png"));
    if (!blob) return;
    const file = new File([blob], "pigos-scorecard.png", { type: "image/png" });
    const text = t("shareText", { score: result.overall_score });
    if (navigator.canShare?.({ files: [file] })) { try { await navigator.share({ files: [file], text }); return; } catch { /* 취소 → 저장 폴백 */ } }
    const u = URL.createObjectURL(blob); const a = document.createElement("a");
    a.href = u; a.download = file.name; a.click(); URL.revokeObjectURL(u);
  };

  const [copied, setCopied] = useState(false);
  const share = async () => {
    const q = new URLSearchParams({ c: country });
    for (const m of METRICS) { const x = vals[m.field]; if (x) q.set(m.field, x); }
    const url = `${window.location.origin}/scorecard?${q.toString()}`;
    const text = t("shareText", { score: result?.overall_score ?? 0 });
    try {
      if (navigator.share) { await navigator.share({ title: "PigOS", text, url }); return; }
    } catch { /* 취소 등 → 폴백 */ }
    try { await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { /* noop */ }
  };

  const result = mut.data;

  return (
    <div className="min-h-screen bg-background flex flex-col items-center px-4 py-10">
      <div className="w-full max-w-lg">
        {/* Hero */}
        <div className="text-center mb-7">
          <div className="inline-flex items-center gap-1.5 text-xs font-bold text-primary bg-primary-soft rounded-full px-3 py-1 mb-3">
            <Sparkles size={12} /> PigOS
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-text">{t("title")}</h1>
          <p className="text-sm text-text3 mt-1.5">{t("subtitle")}</p>
        </div>

        {!result ? (
          /* ── 입력 폼 ── */
          <div className="bg-surface border border-border rounded-2xl p-6 space-y-4" style={{ boxShadow: "var(--shadow-card)" }}>
            <div>
              <label className="block text-xs font-semibold text-text3 mb-1.5">{t("country")}</label>
              <select
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="w-full border border-border rounded-xl px-3 py-2.5 bg-bg text-sm text-text outline-none focus:border-primary"
              >
                {(countries ?? [{ code: "KR", name: "Korea" }, { code: "US", name: "USA" }, { code: "BR", name: "Brazil" }, { code: "CN", name: "China" }]).map((c) => (
                  <option key={c.code} value={c.code}>{c.name} ({c.code})</option>
                ))}
              </select>
            </div>
            <p className="text-[11px] text-text3">{t("hint")}</p>
            <div className="grid grid-cols-1 gap-2.5">
              {METRICS.map((m) => (
                <div key={m.field} className="flex items-center gap-3">
                  <label className="flex-1 text-sm text-text2">{t(m.labelKey)}</label>
                  <input
                    type="number" inputMode="decimal" step="any"
                    value={vals[m.field] ?? ""}
                    onChange={(e) => setVals((v) => ({ ...v, [m.field]: e.target.value }))}
                    className="w-24 border border-border rounded-lg px-2.5 py-2 bg-bg text-sm text-text font-mono text-right outline-none focus:border-primary"
                    placeholder="—"
                  />
                </div>
              ))}
            </div>
            {err && <p className="text-xs text-danger">{err}</p>}
            <button
              onClick={submit}
              disabled={mut.isPending}
              className="w-full bg-navy text-white font-bold py-3 rounded-xl hover:opacity-90 transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {mut.isPending ? t("computing") : <>{t("compute")} <ArrowRight size={16} /></>}
            </button>
          </div>
        ) : (
          /* ── 결과 ── */
          <div className="space-y-4">
            {/* 종합 점수 */}
            <div className="bg-surface border border-border rounded-2xl p-6 text-center" style={{ boxShadow: "var(--shadow-card)" }}>
              <div className="text-[11px] font-bold uppercase tracking-widest text-text3 mb-1">{t("yourScore")}</div>
              <div className={`text-6xl font-extrabold font-mono ${BAND_STYLE[result.overall_band].ring}`}>
                {result.overall_score}
              </div>
              <div className={`inline-flex items-center gap-1.5 mt-2 text-xs font-bold px-3 py-1 rounded-full border ${BAND_STYLE[result.overall_band].cls}`}>
                {result.overall_band === "TOP" && <Trophy size={12} />}
                {t(`band${result.overall_band}`)}
              </div>
            </div>

            {/* 지표별 */}
            <div className="bg-surface border border-border rounded-2xl divide-y divide-border overflow-hidden">
              {result.metrics.map((m) => (
                <div key={m.code} className="px-4 py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-text">{t(CODE_TO_LABEL[m.code] ?? m.code)}</div>
                    {(m.avg != null || m.top25 != null) && (
                      <div className="text-[11px] text-text3 font-mono">
                        {m.avg != null && <>{t("countryAvg")} {m.avg}</>}
                        {m.top25 != null && <> · {t("top25")} {m.top25}</>}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2.5 shrink-0">
                    <span className="font-mono text-lg font-extrabold text-text tabular-nums">{m.value}</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${BAND_STYLE[m.band].cls}`}>
                      {t(`band${m.band}`)}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* 개선 기회 */}
            {result.opportunities.length > 0 && (
              <div className="bg-surface border border-border rounded-2xl p-4">
                <div className="text-[11px] font-bold uppercase tracking-widest text-faint mb-2">{t("oppsTitle")}</div>
                <div className="space-y-2">
                  {result.opportunities.map((o) => (
                    <div key={o.code} className="flex items-center gap-2.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${o.band === "LOW" ? "bg-danger" : "bg-warning"}`} />
                      <span className="text-sm font-semibold text-text flex-1">{t(CODE_TO_LABEL[o.code] ?? o.code)}</span>
                      {o.gap_to_avg != null && o.gap_to_avg > 0 && (
                        <span className="text-xs text-text3 font-mono">{t("gapToAvg", { n: o.gap_to_avg })}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* CTA */}
            <div className="bg-navy text-white rounded-2xl p-5 text-center">
              <p className="font-bold mb-3">{t("ctaTitle")}</p>
              <Link
                href="/onboarding"
                className="inline-flex items-center gap-2 bg-white text-navy font-bold px-5 py-2.5 rounded-xl hover:opacity-90 transition"
              >
                {t("cta")} <ArrowRight size={16} />
              </Link>
            </div>

            <div className="flex items-center gap-2">
              <button onClick={share} className="flex-1 flex items-center justify-center gap-1.5 text-sm font-semibold border border-border rounded-xl py-2.5 hover:border-primary transition">
                <Share2 size={14} /> {copied ? t("copied") : t("share")}
              </button>
              <button onClick={saveImage} className="flex-1 flex items-center justify-center gap-1.5 text-sm font-semibold border border-border rounded-xl py-2.5 hover:border-primary transition">
                <ImageDown size={14} /> {t("saveImage")}
              </button>
            </div>
            <button onClick={reset} className="w-full flex items-center justify-center gap-1.5 text-xs font-semibold text-text3 hover:text-text py-1">
              <RotateCcw size={12} /> {t("tryAnother")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
