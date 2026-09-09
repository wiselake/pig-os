"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import Image from "next/image";
import {
  BrainCircuit,
  ListChecks,
  Package,
  Thermometer,
  FileSpreadsheet,
  Link2,
  QrCode,
  TrendingUp,
  ArrowRight,
  type LucideIcon,
} from "lucide-react";

type Category = "all" | "analytics" | "ops" | "iot" | "integration";

interface AddonCard {
  key: string;
  icon: LucideIcon;
  iconBg: string;
  iconColor: string;
  tag: "coming_soon" | "beta" | "free";
  category: Exclude<Category, "all">;
}

const ADDONS: AddonCard[] = [
  { key: "aiInsight", icon: BrainCircuit,    iconBg: "bg-green-soft",  iconColor: "text-success", tag: "beta",        category: "analytics" },
  { key: "autoTask",  icon: ListChecks,      iconBg: "bg-green-soft",    iconColor: "text-success",   tag: "coming_soon", category: "ops" },
  { key: "feed",      icon: Package,         iconBg: "bg-amber-soft",   iconColor: "text-warning",  tag: "coming_soon", category: "ops" },
  { key: "iot",       icon: Thermometer,     iconBg: "bg-rose-50",    iconColor: "text-rose-500",   tag: "coming_soon", category: "iot" },
  { key: "export",    icon: FileSpreadsheet, iconBg: "bg-emerald-50", iconColor: "text-emerald-600",tag: "coming_soon", category: "analytics" },
  { key: "slaughter", icon: Link2,           iconBg: "bg-cyan-50",    iconColor: "text-cyan-600",   tag: "coming_soon", category: "integration" },
  { key: "qr",        icon: QrCode,          iconBg: "bg-slate-100",  iconColor: "text-slate-600",  tag: "coming_soon", category: "integration" },
  { key: "dividend",  icon: TrendingUp,      iconBg: "bg-green-soft",   iconColor: "text-success",  tag: "coming_soon", category: "analytics" },
];

const CATEGORIES: { value: Category; labelKey: string }[] = [
  { value: "all",         labelKey: "catAll" },
  { value: "analytics",   labelKey: "catAnalytics" },
  { value: "ops",         labelKey: "catOps" },
  { value: "iot",         labelKey: "catIot" },
  { value: "integration", labelKey: "catIntegration" },
];

const TAG_STYLE: Record<AddonCard["tag"], string> = {
  free:        "bg-green-soft text-success border-success/30",
  beta:        "bg-green-soft text-success border-success/30",
  coming_soon: "bg-bg2 text-text3 border-border",
};

const TAG_KEY: Record<AddonCard["tag"], string> = {
  free:        "tagFree",
  beta:        "tagBeta",
  coming_soon: "tagSoon",
};

export default function AddonsPage() {
  const t = useTranslations("addons");
  const [category, setCategory] = useState<Category>("all");

  const filtered = category === "all" ? ADDONS : ADDONS.filter((a) => a.category === category);
  const betaCount = ADDONS.filter((a) => a.tag !== "coming_soon").length;

  return (
    <div className="p-7 max-w-[1600px]">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-[22px] font-extrabold tracking-tight text-text">{t("storeTitle")}</h1>
        <p className="text-[13px] text-text3 mt-1">
          {t("storeSubtitle", { avail: betaCount, soon: ADDONS.length - betaCount })}
        </p>
      </div>

      {/* Data Dividend hero */}
      <div className="relative rounded-2xl overflow-hidden mb-8 bg-[#0D1B3E]">
        {/* Watermark symbol */}
        <div className="absolute -right-10 -bottom-16 w-[260px] h-[260px] opacity-[0.07] pointer-events-none select-none">
          <Image src="/logos/pigos-symbol-dark.svg" alt="" fill className="object-contain" />
        </div>
        <div className="absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r from-[#FF5A66] via-[#0F6342] to-transparent" />

        <div className="relative z-10 px-7 py-7 lg:flex lg:items-center lg:justify-between lg:gap-10">
          <div className="max-w-md">
            <p className="text-[11px] font-bold tracking-[0.18em] uppercase text-[#FF5A66] mb-2.5">
              {t("heroProgram")}
            </p>
            <h2 className="text-white text-lg font-bold leading-snug">
              {t("heroTitle")}
            </h2>
            <p className="text-slate-400 text-[13px] leading-relaxed mt-2">
              {t("heroDesc")}
            </p>
            <button className="mt-4 inline-flex items-center gap-1.5 text-[13px] font-semibold text-white/90 hover:text-white transition group">
              {t("heroMore")}
              <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
            </button>
          </div>

          {/* How it works — quiet 3-step */}
          <div className="hidden lg:block flex-shrink-0 w-[260px]">
            <div className="space-y-0">
              {[
                { n: "01", title: t("step1Title"), sub: t("step1Sub") },
                { n: "02", title: t("step2Title"), sub: t("step2Sub") },
                { n: "03", title: t("step3Title"), sub: t("step3Sub") },
              ].map((s, i, arr) => (
                <div key={s.n} className="flex gap-3.5">
                  <div className="flex flex-col items-center">
                    <span className="font-mono text-[10px] text-slate-500 w-7 h-7 rounded-full border border-white/15 flex items-center justify-center flex-shrink-0">
                      {s.n}
                    </span>
                    {i < arr.length - 1 && <div className="w-px flex-1 bg-white/10 my-1" />}
                  </div>
                  <div className={i < arr.length - 1 ? "pb-4" : ""}>
                    <div className="text-[13px] font-semibold text-white/90 leading-7">{s.title}</div>
                    <div className="text-[11px] text-slate-500 -mt-0.5">{s.sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Category filter */}
      <div className="flex items-center gap-1.5 mb-5">
        {CATEGORIES.map((c) => (
          <button
            key={c.value}
            onClick={() => setCategory(c.value)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition border ${
              category === c.value
                ? "bg-navy text-white border-navy"
                : "bg-surface text-text3 border-border hover:text-text hover:border-text3/40"
            }`}
          >
            {t(c.labelKey)}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {filtered.map((addon) => {
          const Icon = addon.icon;
          const disabled = addon.tag === "coming_soon";
          return (
            <div
              key={addon.key}
              className={`group bg-surface border border-border rounded-2xl p-5 flex flex-col gap-3.5 transition ${
                disabled ? "" : "hover:border-primary/40 hover:shadow-sm"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className={`w-10 h-10 rounded-xl ${addon.iconBg} flex items-center justify-center`}>
                  <Icon size={20} className={addon.iconColor} />
                </div>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${TAG_STYLE[addon.tag]}`}>
                  {t(TAG_KEY[addon.tag])}
                </span>
              </div>
              <div className="flex-1">
                <div className="font-bold text-[14px] text-text">{t(`n_${addon.key}`)}</div>
                <div className="text-xs text-text3 mt-1 leading-relaxed">{t(`d_${addon.key}`)}</div>
              </div>
              {/* free만 동작 — beta(AI Insight 등)는 아직 미연동이라 버튼 비활성화 */}
              <button
                disabled={addon.tag !== "free"}
                className={`text-xs font-semibold rounded-lg px-3 py-2 transition ${
                  addon.tag !== "free"
                    ? "bg-bg2 text-text3/60 cursor-not-allowed"
                    : "bg-primary text-white hover:bg-success"
                }`}
              >
                {disabled ? t("btnSoon") : addon.tag === "beta" ? t("btnBeta") : t("btnFree")}
              </button>
            </div>
          );
        })}
      </div>

      {/* Request */}
      <div className="mt-8 border border-dashed border-border rounded-2xl px-6 py-5 flex items-center justify-between gap-4">
        <div>
          <div className="text-sm font-bold text-text">{t("requestTitle")}</div>
          <div className="text-xs text-text3 mt-0.5">{t("requestDesc")}</div>
        </div>
        <a
          href="/support"
          className="flex-shrink-0 text-xs font-semibold text-primary border border-primary/30 rounded-lg px-4 py-2 hover:bg-primary/5 transition"
        >
          {t("requestBtn")}
        </a>
      </div>
    </div>
  );
}
