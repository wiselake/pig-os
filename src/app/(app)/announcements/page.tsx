"use client";

import { useTranslations, useLocale } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { contentApi } from "@/lib/api/endpoints/content";
import { Pin } from "lucide-react";

// 분류 → 태그 색(Forest 토큰). 텍스트(제목/내용)는 실 API.
const CAT_CLS: Record<string, string> = {
  GENERAL: "text-success bg-green-soft border-success/30",
  UPDATE: "text-warning bg-amber-soft border-warning/40",
  MAINTENANCE: "text-danger bg-red-soft border-danger/40",
};

export default function AnnouncementsPage() {
  const t = useTranslations("announcements");
  const locale = useLocale();

  const { data, isLoading } = useQuery({
    queryKey: ["announcements", locale],
    queryFn: () => contentApi.announcements(locale),
  });

  const items = data ?? [];

  return (
    <div className="max-w-5xl mx-auto px-7 py-6">
      <h1 className="text-xl font-extrabold tracking-tight mb-5">{t("title")}</h1>
      {isLoading ? (
        <div className="py-12 text-center text-text3 text-sm">…</div>
      ) : items.length === 0 ? (
        <div className="border border-border rounded-2xl py-14 text-center text-text3 text-sm">{t("empty")}</div>
      ) : (
        <div className="space-y-3">
          {items.map((n) => (
            <div key={n.id} className="bg-surface border border-border rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                {n.pinned && <Pin size={14} className="text-primary" strokeWidth={2} aria-hidden />}
                <span className={`text-[11px] font-bold font-mono px-2 py-0.5 rounded-md border ${CAT_CLS[n.category] ?? CAT_CLS.GENERAL}`}>{n.category}</span>
                <span className="text-[11px] text-text3 font-mono ml-auto">{n.created_at?.slice(0, 10)}</span>
              </div>
              <div className="text-sm font-bold text-text mb-2">{n.title}</div>
              <p className="text-sm text-text2 leading-relaxed whitespace-pre-wrap">{n.body}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
