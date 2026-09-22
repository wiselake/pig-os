"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Wheat,
  User,
  Users,
  CreditCard,
  Globe,
  Bell,
  Building2,
  Sliders,
  SlidersHorizontal,
  Target,
  FileText,
  LifeBuoy,
  Megaphone,
  ShieldCheck,
  LogOut,
  Trash2,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";
import { useAuthStore } from "@/store/auth.store";

interface SettingItem {
  icon: LucideIcon;
  label: string;
  desc?: string;
  href?: string;
  onClick?: () => void;
  danger?: boolean;
}

export default function SettingsPage() {
  const t = useTranslations("settings");
  const tUsers = useTranslations("users");
  const tThr = useTranslations("thresholds");
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);

  const handleLogout = () => {
    clearAuth();
    document.cookie = "pigos_session=; path=/; max-age=0";
    router.replace("/login");
  };

  const sections: { title: string; items: SettingItem[] }[] = [
    {
      title: t("secAccount"),
      items: [
        { icon: User,       label: t("profile"),       desc: t("profileDesc"),       href: "/settings/profile" },
        { icon: Globe,      label: t("language"),      desc: t("currentLanguage"),   href: "/settings/profile" },
        { icon: Bell,       label: t("notifications"), desc: t("notificationsDesc"), href: "/notifications" },
      ],
    },
    {
      title: t("secFarm"),
      items: [
        { icon: Wheat,      label: t("feed"),        desc: t("feedDesc"),        href: "/feed" },   // 모바일 뷰포트 진입점 — 사이드바는 md 미만에서 숨김
        { icon: Building2,  label: t("farmInfo"),    desc: t("farmInfoDesc"),    href: "/settings/profile" },
        { icon: Users,      label: tUsers("title"),  desc: tUsers("subtitle"),   href: "/settings/users" },
        { icon: Sliders,    label: t("reproConfig"), desc: t("reproConfigDesc"), href: "/settings/farm" },
        { icon: Target,     label: t("benchmarks"),  desc: t("benchmarksDesc"),  href: "/settings/benchmarks" },
        { icon: SlidersHorizontal, label: tThr("title"), desc: tThr("subtitle"), href: "/settings/thresholds" },
        { icon: CreditCard, label: t("billing"),     desc: t("billingDesc"),     href: "/settings/billing" },
      ],
    },
    {
      title: t("secSupport"),
      items: [
        { icon: Megaphone,  label: t("announcements"), href: "/announcements" },
        { icon: LifeBuoy,   label: t("support"),       href: "/support" },
        { icon: ShieldCheck, label: t("dataPrivacy"),  desc: t("dataPrivacyDesc"), href: "/settings/data" },
        { icon: FileText,   label: t("legal"),         href: "/legal" },
      ],
    },
    {
      title: t("secEtc"),
      items: [
        { icon: LogOut, label: t("logout"), onClick: handleLogout },
        { icon: Trash2, label: t("deleteAccount"), desc: t("deleteAccountDesc"), href: "/settings/delete-account", danger: true },
      ],
    },
  ];

  return (
    <div className="max-w-2xl mx-auto px-7 py-6">
      <h1 className="text-xl font-extrabold tracking-tight text-text mb-1">{t("pageTitle")}</h1>
      <p className="text-[13px] text-text3 mb-6">{t("pageSubtitle")}</p>

      {/* User card */}
      {user && (
        <div className="flex items-center gap-3.5 bg-surface border border-border rounded-2xl px-5 py-4 mb-6">
          <div className="w-11 h-11 rounded-full bg-purple flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
            {user.name.slice(0, 2).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-bold text-text truncate">{user.name}</div>
            <div className="text-xs text-text3 truncate">{user.email}</div>
          </div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-primary bg-primary/8 border border-primary/20 rounded-full px-2.5 py-1">
            {user.role}
          </span>
        </div>
      )}

      {/* Sections */}
      <div className="space-y-6">
        {sections.map((section) => (
          <div key={section.title}>
            <div className="px-1 pb-2 text-[11px] font-bold text-text3 uppercase tracking-widest">
              {section.title}
            </div>
            <div className="bg-surface border border-border rounded-2xl overflow-hidden divide-y divide-border">
              {section.items.map((item) => {
                const Icon = item.icon;
                const inner = (
                  <>
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      item.danger ? "bg-red-soft" : "bg-bg2"
                    }`}>
                      <Icon size={15} className={item.danger ? "text-danger" : "text-text2"} strokeWidth={1.8} />
                    </div>
                    <div className="flex-1 min-w-0 text-left">
                      <div className={`text-[13px] font-semibold ${item.danger ? "text-danger" : "text-text"}`}>
                        {item.label}
                      </div>
                      {item.desc && <div className="text-[11px] text-text3 mt-0.5">{item.desc}</div>}
                    </div>
                    <ChevronRight size={14} className="text-text3/50 flex-shrink-0" />
                  </>
                );
                const cls = "w-full flex items-center gap-3 px-4 py-3 hover:bg-bg2/60 transition";
                return item.href ? (
                  <Link key={item.label} href={item.href} className={cls}>{inner}</Link>
                ) : (
                  <button key={item.label} onClick={item.onClick} className={cls}>{inner}</button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <p className="text-center text-[11px] text-text3/60 mt-8">PigOS v0.1.0 · © 2026 WiseLake Inc.</p>
    </div>
  );
}
