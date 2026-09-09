"use client";
import { useTranslations } from "next-intl";
import { Wrench } from "lucide-react";

export default function MaintenancePage() {
  const t = useTranslations("util");
  return (
    <div className="min-h-screen flex items-center justify-center text-center px-6"
      style={{ background: "linear-gradient(170deg,#0D1B3E,#16264f)" }}>
      <div className="max-w-sm">
        <div className="mb-6 flex justify-center">
          <span className="w-16 h-16 rounded-2xl bg-white/10 border border-white/15 flex items-center justify-center">
            <Wrench size={30} className="text-white" strokeWidth={1.75} aria-hidden />
          </span>
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight mb-3">{t("mtTitle")}</h1>
        <p className="text-base text-white/70 leading-relaxed mb-6">
          {t("mtDesc")}
        </p>
        <div className="inline-flex items-center gap-2 bg-white/10 border border-white/15 rounded-full px-5 py-2.5 font-mono text-sm text-white mb-8">
          <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
          {t("mtEta")}
        </div>
        <p className="text-xs text-white/40 leading-relaxed">
          {t("mtNote")}
        </p>
      </div>
    </div>
  );
}
