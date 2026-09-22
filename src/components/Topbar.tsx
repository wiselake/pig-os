"use client";

import { Bell, ChevronDown, LogOut, Search, User } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/store/auth.store";
import { visibleLocales } from "@/i18n/config";
import { FarmSwitcher } from "@/components/FarmSwitcher";

import type { Locale } from "@/i18n/config";

// LANG_LABELS는 언어 선택기 표시명(로케일 불변 상수 — 번역 대상 아님). search/qi는 topbar 네임스페이스.
const LANG_LABELS: Record<Locale, string> = {
  en: "EN", ko: "KO", zh: "中文", es: "ES", vi: "VI", th: "ไทย", pt: "PT", ru: "RU",
};

// 사용자 메뉴 — 로그아웃이 설정 페이지 3~4단 안쪽에만 있어 찾기 어려웠다.
// 상시 노출하되 오클릭 방지를 위해 드롭다운 + 확인 단계를 둔다.
function AccountMenu() {
  const t = useTranslations("topbar");
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const [open, setOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // 바깥 클릭·ESC 로 닫기 — 열어놓고 다른 걸 누르면 메뉴가 남아 가리는 걸 막는다.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) { setOpen(false); setConfirming(false); }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { setOpen(false); setConfirming(false); }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open]);

  const doLogout = () => {
    clearAuth();
    document.cookie = "pigos_session=; path=/; max-age=0";
    router.replace("/login");
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => { setOpen((v) => !v); setConfirming(false); }}
        data-testid="account-menu"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("account")}
        className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-muted hover:bg-bg2 hover:text-text transition"
      >
        <User size={16} />
        <span className="hidden sm:inline text-xs font-semibold max-w-[110px] truncate">
          {user?.name ?? user?.username ?? t("account")}
        </span>
        <ChevronDown size={12} className={open ? "rotate-180 transition" : "transition"} />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-1 w-56 bg-surface border border-border rounded-xl shadow-lg z-50 overflow-hidden"
          style={{ boxShadow: "var(--shadow-card)" }}
        >
          {user && (
            <div className="px-3 py-2.5 border-b border-border">
              <div className="text-xs font-bold text-text truncate">{user.name ?? user.username}</div>
              {user.email && <div className="text-[11px] text-text3 truncate">{user.email}</div>}
            </div>
          )}
          {confirming ? (
            <div className="p-3">
              <p className="text-xs text-text2 mb-2.5">{t("logoutConfirm")}</p>
              <div className="flex gap-2">
                <button
                  onClick={doLogout}
                  data-testid="logout-confirm"
                  className="flex-1 text-xs font-bold text-white bg-danger px-3 py-2 rounded-lg hover:opacity-90 transition"
                >
                  {t("logout")}
                </button>
                <button
                  onClick={() => setConfirming(false)}
                  className="flex-1 text-xs font-semibold text-text2 border border-border px-3 py-2 rounded-lg hover:bg-bg2 transition"
                >
                  {t("cancel")}
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setConfirming(true)}
              role="menuitem"
              data-testid="logout-button"
              className="w-full flex items-center gap-2 px-3 py-2.5 text-xs font-semibold text-danger hover:bg-red-soft transition text-left"
            >
              <LogOut size={14} /> {t("logout")}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

interface TopbarProps {
  lang?: Locale;
  onLangToggle?: (l: Locale) => void;
  onQuickInput?: () => void;
  onBell?: () => void;
  alertCount?: number;
}

export function Topbar({
  lang = "ko",
  onLangToggle,
  onQuickInput,
  onBell,
  alertCount = 0,
}: TopbarProps) {
  const t = useTranslations("topbar");
  // 한국어 가시성은 system_role 기준(농장 role이 아니라 플랫폼 권한 — 코드리뷰 #2).
  const systemRole = useAuthStore((s) => s.user?.system_role);
  // 한국어는 플랫폼 관리자만. 현재 lang이 목록에 없으면(엣지) 깨지지 않게 포함.
  const localeOpts = visibleLocales(systemRole);
  const langOpts = localeOpts.includes(lang) ? localeOpts : [lang, ...localeOpts];

  return (
    <header className="h-14 flex-shrink-0 bg-bg border-b border-border flex items-center px-5 gap-3">
      {/* Farm switcher (멀티팜: 접근 가능 농장 전환) */}
      <FarmSwitcher />

      {/* Search */}
      <div className="flex-1 max-w-[360px] relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-faint" size={14} />
        <input
          placeholder={t("search")}
          className="w-full bg-surface border border-border text-text text-xs pl-8 pr-10 py-2 rounded-lg outline-none focus:border-primary transition"
        />
        <span className="absolute right-2.5 top-1/2 -translate-y-1/2 font-mono text-[9px] text-faint bg-panel-hi px-1.5 py-0.5 rounded">
          ⌘K
        </span>
      </div>

      <div className="flex items-center gap-2 ml-auto">
        {/* Lang select */}
        <select
          value={lang}
          data-testid="language-switcher"
          onChange={(e) => onLangToggle?.(e.target.value as Locale)}
          className="bg-surface border border-border text-text text-[11px] font-bold px-2 py-1.5 rounded-md outline-none focus:border-primary cursor-pointer"
        >
          {langOpts.map((l) => (
            <option key={l} value={l}>{LANG_LABELS[l]}</option>
          ))}
        </select>

        {/* Bell */}
        <button
          onClick={onBell}
          className="relative p-2 rounded-lg text-muted hover:bg-bg2 hover:text-text transition"
        >
          <Bell size={16} />
          {alertCount > 0 && (
            <span className="absolute top-1 right-1 min-w-[14px] h-3.5 px-1 rounded-full bg-red text-white font-mono text-[9px] font-bold flex items-center justify-center">
              {alertCount}
            </span>
          )}
        </button>

        {/* Quick Input */}
        <button
          onClick={onQuickInput}
          className="flex items-center gap-1.5 bg-navy text-white text-xs font-semibold px-3 py-2 rounded-lg hover:bg-primary transition"
        >
          <span className="text-sm font-bold leading-none">+</span>
          {t("qi")}
        </button>

        {/* Account / Logout — 상시 노출(설정 안쪽에만 있어 찾기 어려웠음) */}
        <AccountMenu />
      </div>
    </header>
  );
}
