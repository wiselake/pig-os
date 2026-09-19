"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations, useLocale } from "next-intl";
import { ShieldCheck, ArrowLeft, Languages } from "lucide-react";
import { useAuthStore } from "@/store/auth.store";
import { ADMIN_NAV } from "@/lib/admin/nav";
import { locales } from "@/i18n/config";

// 운영자 콘솔 언어 선택 — 관리자는 전 로케일(한국어 포함) 사용 가능.
const ADMIN_LANG_LABEL: Record<string, string> = {
  en: "English", ko: "한국어", zh: "中文", es: "Español",
  vi: "Tiếng Việt", th: "ไทย", pt: "Português", ru: "Русский",
};

// 운영자 어드민 셸 — SUPER_ADMIN 전용. 고객 앱 셸((app))과 분리된 자체 chrome.
// 게이트: ①클라이언트(이 레이아웃) ②백엔드 require_super_admin(403). 도메인은 admin.pigos.io로 분기 가능.
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("admin");
  const locale = useLocale();
  const user = useAuthStore((s) => s.user);

  // 언어 변경: NEXT_LOCALE 쿠키 set + refresh (고객 앱 Topbar와 동일 소스).
  const changeLang = (l: string) => {
    document.cookie = `NEXT_LOCALE=${l}; path=/; max-age=31536000; SameSite=Lax`;
    router.refresh();
  };
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  // 미로그인만 /login 으로. (비관리자는 redirect 대신 접근거부 화면 — admin 도메인 무한루프 방지)
  useEffect(() => {
    if (mounted && !user) router.replace("/login");
  }, [mounted, user, router]);

  // 하이드레이트 전 / 미로그인
  if (!mounted || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg">
        <p className="text-text3 text-sm">{t("checkingAccess")}</p>
      </div>
    );
  }

  // 로그인했으나 비관리자 → 접근거부(루프 안전: redirect 안 함). 로그아웃 제공.
  // 백엔드 require_super_admin과 동일 기준: system_role === SUPER_ADMIN.
  // (role 컬럼은 pilot 승인 운영자처럼 FARM_OWNER일 수 있어 권한기준이 아님 — half-render 방지.)
  if (user.system_role !== "SUPER_ADMIN") {
    const logout = () => {
      clearAuth();
      document.cookie = "pigos_session=; path=/; max-age=0; SameSite=Lax";
      router.replace("/login");
    };
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3 bg-bg text-center px-6">
        <ShieldCheck size={28} className="text-text3" />
        <p className="text-sm font-bold text-text">{t("accessDeniedTitle")}</p>
        <p className="text-xs text-text3 max-w-xs">{t("accessDeniedDesc")}</p>
        <button onClick={logout} className="mt-1 text-xs font-semibold text-white bg-primary px-4 py-2 rounded-lg hover:opacity-90">
          {t("accessDeniedLogout")}
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-bg">
      {/* Admin sidebar (dark console) */}
      <aside className="w-56 shrink-0 bg-console text-white flex flex-col">
        <div className="h-14 flex items-center gap-2 px-4 border-b border-white/10">
          <ShieldCheck size={16} className="text-primary" />
          <span className="font-extrabold tracking-tight">PigOS <span className="text-primary">Admin</span></span>
        </div>
        <nav className="flex-1 py-3">
          {ADMIN_NAV.map(({ href, labelKey, icon: Icon, status }) => {
            const active = href === "/admin" ? pathname === href : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2.5 px-4 py-2.5 text-sm font-medium transition border-l-[3px] ${
                  active ? "border-primary bg-white/10 text-white" : "border-transparent text-white/70 hover:text-white hover:bg-white/5"
                }`}
              >
                <Icon size={16} /> <span className="flex-1">{t(labelKey)}</span>
                {status === "soon" && <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-white/10 text-white/50">{t("soon")}</span>}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-white/10 space-y-2.5">
          <div className="text-[11px] text-white/60 truncate">{user.name} · {user.role}</div>
          {/* 언어 선택 (관리자 = 한국어 포함 전 로케일) */}
          <label className="flex items-center gap-1.5 text-xs text-white/70">
            <Languages size={12} className="shrink-0" />
            <select
              value={locale}
              onChange={(e) => changeLang(e.target.value)}
              aria-label="Language"
              className="flex-1 bg-white/10 text-white text-xs rounded px-1.5 py-1 outline-none border border-white/10 hover:bg-white/15 cursor-pointer"
            >
              {locales.map((l) => (
                <option key={l} value={l} className="bg-console text-white">
                  {ADMIN_LANG_LABEL[l] ?? l}
                </option>
              ))}
            </select>
          </label>
          <Link href="/" className="flex items-center gap-1.5 text-xs text-white/70 hover:text-white">
            <ArrowLeft size={12} /> {t("backToApp")}
          </Link>
        </div>
      </aside>

      <main className="flex-1 min-w-0">{children}</main>
    </div>
  );
}
