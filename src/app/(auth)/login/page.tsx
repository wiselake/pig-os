"use client";

import Image from "next/image";
import { Sparkles } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslations } from "next-intl";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import { authApi } from "@/lib/api/endpoints/auth";
import { resolveApiError, withRequestId } from "@/lib/api/errors";
import { useAuthStore } from "@/store/auth.store";
import { identifyUser } from "@/lib/analytics";

// ── i18n ──────────────────────────────────────────────────────────────────────
const LANGS = ["en", "ko", "zh", "es", "vi", "th", "pt", "ru"] as const;
type Lang = (typeof LANGS)[number];

// 한국어는 로그인 전 화면에 노출하지 않음(해외 출시). admin 로그인 후 Topbar에서만 선택 가능.
const SELECTABLE_LANGS: Lang[] = LANGS.filter((l) => l !== "ko");

const LANG_LABELS: Record<Lang, string> = {
  en: "English", ko: "한국어", zh: "中文", es: "Español", vi: "Tiếng Việt", th: "ไทย", pt: "Português", ru: "Русский",
};
// ── Schema ────────────────────────────────────────────────────────────────────
const schema = z.object({
  username: z.string().min(3, "invalid"),
  password: z.string().min(1, "required"),
});
type FormValues = z.infer<typeof schema>;

// ── Sub-components ────────────────────────────────────────────────────────────
function LanguageSelector({ lang, onChange }: { lang: Lang; onChange: (l: Lang) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        data-testid="language-switcher"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
          text-slate-500 bg-white border border-slate-200 hover:border-slate-300
          hover:text-slate-700 shadow-sm transition select-none"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/>
          <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
        </svg>
        {LANG_LABELS[lang]}
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 mt-1.5 w-40 rounded-xl border border-slate-200
          bg-white shadow-lg py-1 z-50">
          {SELECTABLE_LANGS.map((l) => (
            <button key={l} type="button"
              data-testid={`language-option-${l}`}
              onClick={() => { onChange(l); setOpen(false); }}
              className={`w-full text-left px-4 py-2 text-sm transition hover:bg-slate-50
                ${l === lang ? "text-[#2563EB] font-semibold" : "text-slate-600"}`}>
              {LANG_LABELS[l]}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function BrandPanel() {
  return (
    <div className="hidden lg:flex lg:w-[40%] flex-col justify-between
      bg-[#0D1B3E] px-12 py-12 relative overflow-hidden">
      {/* Subtle grid overlay */}
      <div className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,.6) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,.6) 1px, transparent 1px)`,
          backgroundSize: "40px 40px",
        }} />
      {/* Radial glow */}
      <div className="absolute top-[-20%] left-[-10%] w-[70%] h-[70%] rounded-full
        bg-blue-500/10 blur-[80px] pointer-events-none" />

      {/* Logo */}
      <div className="relative z-10">
        <Image
          src="/logos/pigos-logo-horizontal-dark.svg"
          alt="PigOS"
          width={220}
          height={84}
          className="object-contain object-left"
          priority
        />
      </div>

      {/* Main message */}
      <div className="relative z-10 flex-1 flex flex-col justify-center py-12">
        <p className="text-white/60 text-xs font-semibold tracking-widest uppercase mb-4">
          Farm Operating System
        </p>
        <h2 className="text-white text-3xl font-bold leading-snug mb-6">
          AI-powered operating system<br />
          for global pig farm operations.
        </h2>
        <div className="space-y-3">
          {[
            { icon: "◈", text: "27 yrs of field expertise" },
            { icon: "◎", text: "5 global markets · 8 languages" },
            { icon: "◉", text: "AI-powered KPI alerts" },
          ].map(({ icon, text }) => (
            <div key={text} className="flex items-center gap-3">
              <span className="text-[#FF5A66] text-base">{icon}</span>
              <span className="text-white/70 text-sm">{text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="relative z-10">
        <p className="text-white/30 text-xs">© 2026 WiseLake Inc.</p>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [lang, setLang] = useState<Lang>("en");
  const [serverError, setServerError] = useState<string | null>(null);

  useEffect(() => {
    // NEXT_LOCALE 쿠키 우선(앱과 동일 소스), 없으면 localStorage.
    // 한국어는 관리자 전용 → 로그인 전엔 절대 노출 안 함.
    const m = document.cookie.match(/(?:^|;\s*)NEXT_LOCALE=([^;]+)/);
    const cookieLang = m?.[1] as Lang | undefined;
    const stored = (cookieLang ?? localStorage.getItem("pigos_lang")) as Lang | null;
    if (stored && SELECTABLE_LANGS.includes(stored)) {
      setLang(stored);
    } else if (cookieLang === "ko") {
      // 이전 관리자 세션이 남긴 ko 쿠키 → 로그인 전엔 en으로 정규화(next-intl 한국어 누수 차단)
      document.cookie = "NEXT_LOCALE=en; path=/; max-age=31536000; SameSite=Lax";
      try { localStorage.setItem("pigos_lang", "en"); } catch { /* ignore */ }
    }
  }, []);

  const switchLang = (l: Lang) => {
    setLang(l);
    localStorage.setItem("pigos_lang", l);
    // next-intl(앱 페이지)이 읽는 쿠키도 같이 설정 → 로그인 후 언어 일치
    document.cookie = `NEXT_LOCALE=${l}; path=/; max-age=31536000; SameSite=Lax`;
    router.refresh(); // next-intl 로케일 즉시 반영(파일 단일소스)
  };

  const t = useTranslations("login");
  const tErr = useTranslations("errors");

  const { register, handleSubmit, setValue, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });
  const [rememberId, setRememberId] = useState(false);

  // 저장된 아이디 프리필 (비밀번호는 보안상 저장 안 함 — 브라우저 비밀번호 관리자 사용)
  useEffect(() => {
    const saved = localStorage.getItem("pigos_saved_username");
    if (saved) {
      setValue("username", saved);
      setRememberId(true);
    }
  }, [setValue]);

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    if (rememberId) localStorage.setItem("pigos_saved_username", values.username);
    else localStorage.removeItem("pigos_saved_username");
    try {
      const data = await authApi.login(values);
      setAuth(
        {
          id: data.user_id,
          username: data.username,
          email: data.email,
          name: data.name,
          role: data.role,
          system_role: data.system_role,
          farm_ids: data.farm_ids,
          farm_roles: data.farm_roles,
        },
        data.access_token,
        data.refresh_token,
        data.farm_ids[0],
      );
      document.cookie = `pigos_session=1; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
      identifyUser(data.user_id, { system_role: data.system_role });
      // 운영자(SUPER_ADMIN)는 admin 콘솔로. 일반 사용자는 next 또는 대시보드(/).
      // 백엔드 권한기준(system_role)으로 판정 — role 컬럼은 FARM_OWNER여도 system_role이 운영자일 수 있음.
      const dest = data.system_role === "SUPER_ADMIN" ? "/admin" : (searchParams.get("next") ?? "/");
      router.replace(dest);
    } catch (err: unknown) {
      // ★ 실패 종류마다 사용자가 할 행동이 다르다 — 하나의 "Server error" 로 뭉치지 않는다.
      //   로그인 화면에서만 예외가 둘 있다: 401 은 "세션 만료"가 아니라 자격증명 불일치이고,
      //   422 는 서버 검증이 아니라 입력 형식 문제로 안내해야 한다.
      const e = resolveApiError(err);
      if (e.status === 401) setServerError(t("errInvalid"));
      else if (e.status === 422) setServerError(t("errFormat"));
      else setServerError(withRequestId(tErr(e.messageKey), e.requestId));
    }
  };

  return (
    <div className="min-h-screen flex w-full">
      <BrandPanel />

      {/* ── Right: Login form ── */}
      <div className="flex-1 flex flex-col bg-white lg:bg-slate-50">
        {/* Top bar */}
        <div className="flex items-center justify-between px-8 pt-8">
          {/* Mobile-only logo */}
          <div className="lg:hidden">
            <Image
              src="/logos/pigos-logo-horizontal-light.svg"
              alt="PigOS"
              width={120}
              height={46}
              className="object-contain"
              priority
            />
          </div>
          <div className="lg:ml-auto">
            <LanguageSelector lang={lang} onChange={switchLang} />
          </div>
        </div>

        {/* Form area */}
        <div className="flex-1 flex items-center justify-center px-6 py-12">
          <div className="w-full max-w-[420px]">
            {/* Heading */}
            <div className="mb-8">
              <h1 className="text-2xl font-bold text-slate-900">{t("heading")}</h1>
              <p className="text-sm text-slate-500 mt-1">{t("subheading")}</p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
              {/* Username (ID) */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  {t("username")}
                </label>
                <input
                  type="text"
                  data-testid="login-username"
                  autoComplete="username"
                  placeholder={t("usernamePlaceholder")}
                  {...register("username")}
                  className={`w-full h-11 px-3.5 rounded-lg text-sm text-slate-900
                    placeholder:text-slate-400 outline-none border bg-white transition
                    focus:ring-2 focus:ring-[#2563EB]/20 focus:border-[#2563EB]
                    ${errors.username ? "border-red-400" : "border-[#CBD5E1]"}`}
                />
                {errors.username && (
                  <p className="text-xs text-danger mt-1">{t("errUsername")}</p>
                )}
              </div>

              {/* Password */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-sm font-medium text-slate-700">{t("password")}</label>
                  <a href="/forgot-password" className="text-xs text-[#2563EB] hover:underline">
                    {t("forgotPassword")}
                  </a>
                </div>
                <input
                  type="password"
                  data-testid="login-password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  {...register("password")}
                  className={`w-full h-11 px-3.5 rounded-lg text-sm text-slate-900
                    placeholder:text-slate-400 outline-none border bg-white transition
                    focus:ring-2 focus:ring-[#2563EB]/20 focus:border-[#2563EB]
                    ${errors.password ? "border-red-400" : "border-[#CBD5E1]"}`}
                />
                {errors.password && (
                  <p className="text-xs text-danger mt-1">{t("errPassword")}</p>
                )}
              </div>

              {/* 아이디 저장 */}
              <label className="flex items-center gap-2 -mt-1 select-none cursor-pointer">
                <input
                  type="checkbox"
                  data-testid="remember-id"
                  checked={rememberId}
                  onChange={(e) => setRememberId(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-[#2563EB] focus:ring-[#2563EB]/30"
                />
                <span className="text-sm text-slate-600">{t("rememberId")}</span>
              </label>

              {/* Server error */}
              {serverError && (
                <div className="flex items-start gap-2.5 bg-red-soft border border-danger/40
                  rounded-lg px-4 py-3">
                  <svg className="w-4 h-4 text-danger mt-0.5 shrink-0" viewBox="0 0 24 24"
                    fill="none" stroke="currentColor" strokeWidth="2"
                    strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                  </svg>
                  <p className="text-sm text-danger">{serverError}</p>
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                data-testid="login-submit"
                disabled={isSubmitting}
                className="w-full h-11 bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-50
                  text-white font-semibold rounded-lg text-sm transition shadow-sm
                  shadow-blue-200/60"
              >
                {isSubmitting ? t("submitting") : t("submit")}
              </button>
            </form>

            <p className="text-sm text-slate-500 text-center mt-6">
              {t("noAccount")}{" "}
              <a href="/onboarding" className="text-[#2563EB] hover:underline font-medium">
                {t("register")}
              </a>
            </p>

            {/* 무가입 스코어카드 진입(퍼널 top) */}
            <a href="/scorecard" className="mt-3 flex items-center justify-center gap-1.5 text-xs font-semibold text-[#0F6342] hover:underline">
              <Sparkles size={12} /> {t("scorecardCta")}
            </a>

            <p className="text-xs text-slate-400 text-center mt-8">
              © 2026 WiseLake Inc. · pigos.io
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
