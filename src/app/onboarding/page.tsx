"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslations, useLocale } from "next-intl";
import { rateLimitMessage, resolveApiError } from "@/lib/api/errors";

import { authApi } from "@/lib/api/endpoints/auth";
import { consentApi } from "@/lib/api/endpoints/consent";
import ConsentForm from "@/components/consent/ConsentForm";
import { useAuthStore } from "@/store/auth.store";
import { track, identifyUser } from "@/lib/analytics";
import type { ConsentChoice, SignupPlan } from "@/types/api.types";

// 예약어 아이디 차단(백엔드 auth.py와 동일 규칙) — 사칭 방지, 즉시 피드백용.
const RESERVED_UN = /^(admin|administrator|root|superuser|superadmin|super_admin|system|sysadmin|support|helpdesk|info|contact|moderator|mod|staff|operator|owner|master|official|security|billing|api|www|pigos|pigplan|wiselake|null|undefined)$/;
function isReservedUsername(u: string): boolean {
  const norm = u.trim().toLowerCase().replace(/0/g, "o").replace(/1/g, "i").replace(/3/g, "e").replace(/4/g, "a").replace(/5/g, "s").replace(/@/g, "a").replace(/\$/g, "s");
  return RESERVED_UN.test(norm) || norm.startsWith("admin") || /administrator|pigos|wiselake|superadmin/.test(norm);
}
import type { CountryConfig, OnboardingRequest } from "@/types/api.types";

// 국가 설정 폴백 — 백엔드 app/core/countries.py 미러(오프라인/최초 렌더용).
// 실사용 목록은 GET /config/countries 로 fetch → 국가 추가 시 클라 재배포 없이 반영.
const COUNTRIES_FALLBACK: CountryConfig[] = [
  { code: "KR", name: "South Korea",   timezone: "Asia/Seoul",          currency: "KRW", unit_system: "METRIC",   dial: "+82", language: "ko" },
  { code: "US", name: "United States", timezone: "America/Chicago",     currency: "USD", unit_system: "IMPERIAL", dial: "+1",  language: "en" },
  { code: "CN", name: "China",         timezone: "Asia/Shanghai",       currency: "CNY", unit_system: "METRIC",   dial: "+86", language: "zh" },
  { code: "VN", name: "Vietnam",       timezone: "Asia/Ho_Chi_Minh",    currency: "VND", unit_system: "METRIC",   dial: "+84", language: "vi" },
  { code: "TH", name: "Thailand",      timezone: "Asia/Bangkok",        currency: "THB", unit_system: "METRIC",   dial: "+66", language: "th" },
  { code: "PH", name: "Philippines",   timezone: "Asia/Manila",         currency: "PHP", unit_system: "METRIC",   dial: "+63", language: "en" },
  { code: "BR", name: "Brazil",        timezone: "America/Sao_Paulo",   currency: "BRL", unit_system: "METRIC",   dial: "+55", language: "pt" },
  { code: "MX", name: "Mexico",        timezone: "America/Mexico_City", currency: "MXN", unit_system: "METRIC",   dial: "+52", language: "es" },
  { code: "CL", name: "Chile",         timezone: "America/Santiago",    currency: "CLP", unit_system: "METRIC",   dial: "+56", language: "es" },
  { code: "RU", name: "Russia",        timezone: "Europe/Moscow",       currency: "RUB", unit_system: "METRIC",   dial: "+7",  language: "ru" },
];

// 온보딩은 pre-auth — 한국어는 관리자 전용이라 노출 안 함(공개 7개어 + 미지정 en 폴백).

type Form = OnboardingRequest;

export default function OnboardingPage() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<Form>({
    org_name: "",
    country: "US",  // 기본=1차 출시 시장. KR은 레퍼런스 전용(가입 차단, 대표 override 시만 선택)
    name: "",
    username: "",
    email: "",
    password: "",
    farm_name: "",
    farm_type: "FARROW_TO_FINISH",
    sow_count: 100,
    timezone: "America/Chicago",
    currency: "USD",
    unit_system: "IMPERIAL",
  });
  const [confirmPw, setConfirmPw] = useState("");
  const [error, setError] = useState<string | null>(null);
  /** 게시 문서 미승인으로 해당 지역 가입이 닫힌 상태. 오류가 아니라 안내다. */
  const [blocked, setBlocked] = useState(false);

  // 동의 인프라(TERMS_DISPLAY §4): 확인 스텝에서 법역별 약관·목적 UI 표시 후 기록.
  const [plan, setPlan] = useState<SignupPlan | null>(null);
  const [planStatus, setPlanStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [consentState, setConsentState] = useState<{
    termsAck: boolean; privacyAck: boolean; choices: ConsentChoice[]; canSubmit: boolean;
  } | null>(null);

  const set = <K extends keyof Form>(k: K, v: Form[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  // 국가 목록 — 공개 엔드포인트 fetch(단일 소스), 실패 시 폴백 상수.
  const [countries, setCountries] = useState<CountryConfig[]>(COUNTRIES_FALLBACK);
  useEffect(() => {
    authApi.countries().then((rows) => {
      if (Array.isArray(rows) && rows.length) setCountries(rows);
    }).catch(() => { /* 폴백 유지 */ });
  }, []);

  // 국가 선택 → 타임존·통화·단위 자동 프리필(사용자가 이후 개별 변경 가능).
  const selectCountry = (code: string) => {
    const c = countries.find((x) => x.code === code);
    setForm((f) => ({
      ...f,
      country: code,
      ...(c ? { timezone: c.timezone, currency: c.currency, unit_system: c.unit_system } : {}),
    }));
  };

  // 로케일 = next-intl provider(= NEXT_LOCALE 쿠키). UI는 useTranslations, API엔 locale 전달.
  const locale = useLocale();
  const t = useTranslations("onboarding");
  const tErr = useTranslations("errors");

  /**
   * 서버가 준 detail 을 화면 상태로 옮긴다.
   *
   * ★ `PUBLICATION_NOT_APPROVED` 는 실패가 아니라 **정책 상태**다(G-3).
   *   해당 지역의 약관·개인정보 고지가 아직 확정되지 않아 가입을 받지 않는 것이고,
   *   사용자가 고쳐서 다시 시도할 수 있는 성질이 아니다. 빨간 오류 상자에 영문
   *   코드를 그대로 띄우면 장애로 읽힌다.
   */
  const applyDetail = (detail: unknown, fallback: string, err?: unknown) => {
    if (typeof detail === "string" && detail.includes("PUBLICATION_NOT_APPROVED")) {
      setBlocked(true);
      setError(null);
      return;
    }
    setBlocked(false);
    // ★ 429 는 "요청이 너무 잦다" 이지 가입 실패도 법역 차단도 아니다. detail 원문
    //   ("RATE_LIMITED:signup")을 그대로 띄우면 영문 상수가 화면에 나온다 — 451 에서
    //   겪은 것과 같은 모양. 입력값은 form state 에 그대로 남는다.
    if (err !== undefined) {
      const e = resolveApiError(err);
      if (e.kind === "rateLimited") {
        setError(rateLimitMessage(tErr, e));
        return;
      }
    }
    setError(typeof detail === "string" ? detail : fallback);
  };

  // 확인 스텝 진입 또는 국가/언어 변경 시 plan 조회(공개 엔드포인트 — pre-auth).
  useEffect(() => {
    if (step !== 2 || !form.country) return;
    setPlanStatus("loading");
    setConsentState(null);
    consentApi.signupPlan({
      selected_country: form.country, farm_country: form.country, lang: locale, include_body: true,
    })
      .then((p) => { setPlan(p); setPlanStatus("ready"); })
      .catch(() => { setPlan(null); setPlanStatus("error"); });
  }, [step, form.country, locale]);

  const STEPS = [t("s0"), t("s1"), t("s2")];
  const FARM_TYPES = [
    { value: "SOW_FARM", label: t("sowFarm") },
    { value: "FARROW_TO_FINISH", label: t("f2f") },
    { value: "NURSERY", label: t("nursery") },
    { value: "FINISHER", label: t("finisher") },
  ];

  const mutation = useMutation({
    mutationFn: () => authApi.onboard({ ...form, language: locale }),  // M3: 감지된 로케일 전송
    onSuccess: async (data) => {
      // ★ fail-closed (LEGAL-P0-WEB-CONSENT-FAIL-CLOSED)
      //
      //   이전에는 여기서 곧바로 setAuth·쿠키를 세우고 동의 기록은 try/catch 로
      //   삼켰다. 그래서 plan 을 못 받았거나 record 가 실패해도 대시보드로 들어갔고,
      //   DB 에는 org·user·farm 만 남고 consent_ledger 는 비었다.
      //   실제 프로덕션 원장이 0행인 유력한 경로가 이것이다.
      //
      //   이제 **필수 동의 기록이 성공해야** 로그인 상태를 확정한다.
      //   토큰은 그 전까지 이 호출에만 임시로 쓴다(store 에 저장하지 않는다).
      if (planStatus !== "ready" || !consentState) {
        setError(t("consentPlanUnavailable"));
        return;
      }
      try {
        await consentApi.record(
          {
            farm_id: data.farm_id,
            selected_country: form.country,
            farm_country: form.country,
            lang: locale,
            terms_ack: consentState.termsAck,
            privacy_ack: consentState.privacyAck,
            // 선택 목적을 전부 끈 것은 실패가 아니다 — 정상값 그대로 보낸다.
            choices: consentState.choices,
            collection_context: "UI_SIGNUP",
          },
          data.access_token,   // auth store 에 아직 없으므로 명시 주입
        );
      } catch (err: unknown) {
        // 절대 삼키지 않는다. 서버가 준 사유가 있으면 그대로 보여준다
        // (451 SIGNUP_BLOCKED:{reason} 계약 보존).
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        applyDetail(detail, t("consentRecordFailed"), err);
        return;   // ★ 여기서 멈춘다 — setAuth·쿠키·navigation 없음
      }

      // 여기부터가 "가입 완료" 다. 동의가 원장에 남은 뒤에만 도달한다.
      setAuth(
        { id: data.user_id, username: form.username, email: form.email, name: form.name, role: "FARM_OWNER", farm_ids: [data.farm_id] },
        data.access_token,
        data.refresh_token,
        data.farm_id,
      );
      document.cookie = `pigos_session=1; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
      identifyUser(data.user_id, { country: form.country });
      track("signup", { country: form.country });
      router.replace("/");
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      applyDetail(detail, "Something went wrong. Please try again.", err);
    },
  });

  const canProceed = () => {
    if (step === 0) return form.org_name.trim() && form.farm_name.trim() && form.country;
    if (step === 1) return form.name.trim() && /^[a-zA-Z0-9_.-]{3,50}$/.test(form.username) && form.email.trim() && form.password.length >= 8 && form.password === confirmPw;
    // step 2: 동의 게이트 — fail-closed.
    //
    //   이전에는 plan 조회 실패 시 `return true` 로 통과시켰다. 그러면 서버에는
    //   org·user·farm 이 만들어지는데 동의 원장은 비는 고아 계정이 생긴다.
    //   동의를 받을 수 없으면 애초에 제출을 막는 것이 옳다.
    if (plan?.gate.signup_blocked) return false;
    if (planStatus !== "ready") return false;
    return !!consentState?.canSubmit;   // 필수 약관·개인정보 미체크 → 제출 불가
  };

  const next = () => {
    setError(null);
    if (step === 1 && isReservedUsername(form.username)) {
      setError("This username is reserved and cannot be used.");
      return;
    }
    if (step < 2) setStep((s) => s + 1);
    else mutation.mutate();
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-[520px]">

        {/* Logo */}
        <div className="flex justify-center mb-8">
          <Image
            src="/logos/pigos-logo-horizontal-light.svg"
            alt="PigOS"
            width={140}
            height={53}
            className="object-contain"
            priority
          />
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-0 mb-8">
          {STEPS.map((label, i) => (
            <div key={i} className="flex items-center">
              <div className="flex flex-col items-center gap-1.5">
                <div className={`flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold border-2 transition-all ${
                  i < step
                    ? "bg-[#2563EB] border-[#2563EB] text-white"
                    : i === step
                    ? "bg-white border-[#2563EB] text-[#2563EB]"
                    : "bg-white border-slate-200 text-slate-400"
                }`}>
                  {i < step ? (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 6 9 17l-5-5"/>
                    </svg>
                  ) : (
                    i + 1
                  )}
                </div>
                <span className={`text-xs ${i === step ? "text-slate-700 font-medium" : "text-slate-400"}`}>
                  {label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`h-px w-16 mx-3 mb-5 ${i < step ? "bg-[#2563EB]" : "bg-slate-200"}`} />
              )}
            </div>
          ))}
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8">
          {step === 0 && (
            <div className="space-y-4">
              <div className="mb-6">
                <h2 className="text-lg font-bold text-slate-900">{t("t0")}</h2>
                <p className="text-sm text-slate-500 mt-0.5">{t("d0")}</p>
              </div>
              <Field label={t("org")}>
                <input value={form.org_name} onChange={(e) => set("org_name", e.target.value)} data-testid="onb-org-name"
                  placeholder={t("phOrg")} className="fin" />
              </Field>
              <Field label={t("farm")}>
                <input value={form.farm_name} onChange={(e) => set("farm_name", e.target.value)} data-testid="onb-farm-name"
                  placeholder={t("phFarm")} className="fin" />
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field label={t("country")}>
                  <select value={form.country} onChange={(e) => selectCountry(e.target.value)} className="fin">
                    {countries.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
                  </select>
                </Field>
                <Field label={t("ftype")}>
                  <select value={form.farm_type} onChange={(e) => set("farm_type", e.target.value as Form["farm_type"])} className="fin">
                    {FARM_TYPES.map((ft) => <option key={ft.value} value={ft.value}>{ft.label}</option>)}
                  </select>
                </Field>
              </div>
              <Field label={t("sows")}>
                <input type="number" min={1} value={form.sow_count ?? ""}
                  onChange={(e) => set("sow_count", Number(e.target.value))}
                  placeholder={t("phSows")} className="fin" />
              </Field>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <div className="mb-6">
                <h2 className="text-lg font-bold text-slate-900">{t("t1")}</h2>
                <p className="text-sm text-slate-500 mt-0.5">{t("d1")}</p>
              </div>
              <Field label={t("name")}>
                <input value={form.name} onChange={(e) => set("name", e.target.value)} data-testid="onb-name"
                  placeholder={t("phName")} className="fin" />
              </Field>
              <Field label={t("username")}>
                <input value={form.username} onChange={(e) => set("username", e.target.value)} data-testid="onb-username"
                  placeholder={t("phUsername")} autoComplete="username" className="fin" />
              </Field>
              <Field label={t("email")}>
                <input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} data-testid="onb-email"
                  placeholder={t("phEmail")} className="fin" />
              </Field>
              <Field label={t("pw")}>
                <input type="password" value={form.password} onChange={(e) => set("password", e.target.value)} data-testid="onb-password"
                  placeholder="••••••••" className="fin" />
              </Field>
              <Field label={t("cpw")}>
                <input type="password" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} data-testid="onb-confirm"
                  placeholder="••••••••" className={`fin ${confirmPw && form.password !== confirmPw ? "!border-red-400" : ""}`} />
                {confirmPw && form.password !== confirmPw && (
                  <p className="text-xs text-danger mt-1">{t("mismatch")}</p>
                )}
              </Field>
            </div>
          )}

          {step === 2 && (
            <div>
              <div className="mb-6">
                <h2 className="text-lg font-bold text-slate-900">{t("t2")}</h2>
                <p className="text-sm text-slate-500 mt-0.5">{t("d2")}</p>
              </div>
              <div className="rounded-xl border border-slate-200 overflow-hidden">
                {[
                  [t("rOrg"), form.org_name],
                  [t("rFarm"), form.farm_name],
                  [t("rCountry"), countries.find((c) => c.code === form.country)?.name ?? form.country],
                  [t("rFtype"), FARM_TYPES.find((ft) => ft.value === form.farm_type)?.label ?? form.farm_type ?? ""],
                  [t("rSows"), `${form.sow_count ?? "-"} ${t("head")}`],
                  [t("rName"), form.name],
                  [t("username"), form.username],
                  [t("rEmail"), form.email],
                ].map(([label, value], idx, arr) => (
                  <div key={label} className={`flex justify-between px-4 py-3 text-sm ${idx < arr.length - 1 ? "border-b border-slate-100" : ""}`}>
                    <span className="text-slate-500">{label}</span>
                    <span className="text-slate-900 font-medium">{value}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-slate-400 mt-4 flex items-center gap-1.5">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
                {t("free")}
              </p>

              {/* 동의 인프라 (TERMS_DISPLAY §4) */}
              <div className="mt-6 border-t border-slate-200 pt-5">
                {planStatus === "loading" && (
                  <p className="text-sm text-slate-400 text-center py-4">…</p>
                )}
                {planStatus === "error" && (
                  // ★ "나중에 설정에서" 가 아니다 — 동의 없이는 가입 자체가 안 된다.
                  //   인라인 로케일 분기도 제거(CLAUDE.md §4: messages 파일만 사용).
                  <p className="text-sm text-danger text-center py-2" data-testid="onb-consent-plan-error">
                    {t("consentPlanUnavailable")}
                  </p>
                )}
                {planStatus === "ready" && plan && (
                  <ConsentForm plan={plan} embedded mode="signup" onChange={setConsentState} />
                )}
              </div>
            </div>
          )}

          {blocked && (
            <div className="bg-bg2 border border-border rounded-lg px-4 py-3.5 mt-4">
              <p className="text-sm font-bold text-text mb-1.5">{t("publicationNotApprovedTitle")}</p>
              <p className="text-sm text-text2 leading-relaxed">{t("publicationNotApproved")}</p>
            </div>
          )}

          {error && (
            <div className="flex items-start gap-2.5 bg-red-soft border border-danger/40 rounded-lg px-4 py-3 mt-4">
              <svg className="w-4 h-4 text-danger mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              <p className="text-sm text-danger">{error}</p>
            </div>
          )}

          <div className="flex gap-3 mt-6">
            {step > 0 && (
              <button onClick={() => setStep((s) => s - 1)}
                className="flex-1 h-11 border border-slate-300 text-slate-700 rounded-lg text-sm
                  font-medium hover:bg-slate-50 transition">
                {t("back")}
              </button>
            )}
            <button onClick={next} data-testid="onb-next"
              disabled={!canProceed() || mutation.isPending}
              className="flex-1 h-11 bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-50
                text-white font-semibold rounded-lg text-sm transition shadow-sm shadow-blue-200/60">
              {mutation.isPending ? t("creating") : step === 2 ? t("get") : t("cont")}
            </button>
          </div>
        </div>

        <p className="text-center text-sm text-slate-500 mt-5">
          {t("have")}{" "}
          <a href="/login" className="text-[#2563EB] hover:underline font-medium">{t("signin")}</a>
        </p>
        <p className="text-center text-xs text-slate-400 mt-3">© 2026 WiseLake Inc.</p>
      </div>

      <style>{`
        .fin {
          width: 100%;
          height: 44px;
          padding: 0 0.875rem;
          border-radius: 0.5rem;
          background: #fff;
          border: 1px solid #CBD5E1;
          color: #0f172a;
          font-size: 0.875rem;
          outline: none;
          transition: border-color 0.15s, box-shadow 0.15s;
        }
        .fin:focus {
          border-color: #2563EB;
          box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
        }
        .fin::placeholder { color: #94a3b8; }
      `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1.5">{label}</label>
      {children}
    </div>
  );
}
