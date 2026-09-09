"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { Bell, LayoutDashboard, Menu, PiggyBank, Sparkles, type LucideIcon } from "lucide-react";
import type { Locale } from "@/i18n/config";

interface BottomNavProps {
  lang?: Locale;   // 하위호환용(라벨은 next-intl 로케일 사용, 파일 단일소스)
  onAskAI?: () => void;
  alertCount?: number;
}

// 라벨은 messages/*.json 의 bottomNav 네임스페이스에서 로드(인라인 하드코딩 제거).
const TABS: { href: string | null; Icon: LucideIcon; k: string; isAI?: boolean; badge?: number }[] = [
  { href: "/",         Icon: LayoutDashboard, k: "home" },
  { href: "/sows",     Icon: PiggyBank,       k: "sows" },
  { href: null,        Icon: Sparkles,        k: "ai", isAI: true },
  { href: "/alerts",   Icon: Bell,            k: "alerts" },
  { href: "/settings", Icon: Menu,            k: "more" },
];

export function BottomNav({ onAskAI, alertCount = 0 }: BottomNavProps) {
  const pathname = usePathname();
  const t = useTranslations("bottomNav");

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-surface border-t border-border grid grid-cols-5 pb-safe">
      {TABS.map((tab, i) => {
        if (tab.isAI) {
          return (
            <button
              key={i}
              onClick={onAskAI}
              className="flex flex-col items-center justify-center py-2 gap-1"
            >
              <div
                className="w-10 h-10 rounded-xl -mt-2 flex items-center justify-center text-white text-lg"
                style={{
                  background: "linear-gradient(135deg, #0F6342 0%, #5F4B2C 100%)",
                  boxShadow: "0 4px 12px rgba(37,99,235,.4)",
                }}
              >
                <tab.Icon size={20} />
              </div>
              <span className="text-[10px] font-semibold text-primary">{t(tab.k)}</span>
            </button>
          );
        }

        const isActive = tab.href && (pathname === tab.href || pathname?.startsWith(tab.href + "/"));
        const actualBadge = tab.href === "/alerts" ? alertCount : (tab.badge ?? 0);

        return (
          <Link
            key={i}
            href={tab.href ?? "#"}
            className="flex flex-col items-center justify-center py-3 gap-1 relative"
          >
            <tab.Icon size={20} className={isActive ? "text-primary" : "text-faint"} />
            {actualBadge > 0 && (
              <span className="absolute top-2 right-1/4 min-w-[14px] h-3.5 px-1 rounded-full bg-red text-white font-mono text-[9px] font-bold flex items-center justify-center">
                {actualBadge}
              </span>
            )}
            <span className={`text-[10px] font-medium ${isActive ? "text-primary font-semibold" : "text-faint"}`}>
              {t(tab.k)}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
