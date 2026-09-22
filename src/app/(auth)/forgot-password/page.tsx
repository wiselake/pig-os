"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { rateLimitMessage, resolveApiError } from "@/lib/api/errors";

import { authApi } from "@/lib/api/endpoints/auth";

// (auth) 공개 레이아웃 사용. middleware의 PUBLIC_PATHS에 /forgot-password 이미 포함.
// 이메일 실발송 채널은 아직 미설정(백엔드 _deliver_reset_token = 로그/운영자 중개) → 문구도 그에 맞춤.


const INPUT = `w-full h-11 px-3.5 rounded-lg text-sm text-slate-900 placeholder:text-slate-400
  outline-none border bg-white transition focus:ring-2 focus:ring-[#2563EB]/20
  focus:border-[#2563EB] border-[#CBD5E1]`;

export default function ForgotPasswordPage() {
  const params = useSearchParams();
  const token = params.get("token");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const t = useTranslations("forgotPassword");
  const tErr = useTranslations("errors");

  async function onRequest(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await authApi.requestPasswordReset(email.trim());
      setDone(true);  // 열거방지: 성공/실패 무관 동일 메시지
    } catch (e1: unknown) {
      // ★ 429 만 예외다. 속도 제한은 요청자에 대한 사실이지 계정 존재에 대한 정보가 아니므로
      //   열거방지를 깨지 않는다. 반대로 429 를 "메일을 보냈다" 로 보이면 사용자는 오지 않을
      //   메일을 기다린다. 그 외 실패는 그대로 동일 처리(계정 존재 노출 금지).
      const e = resolveApiError(e1);
      if (e.kind === "rateLimited") setErr(rateLimitMessage(tErr, e));
      else setDone(true);
    } finally {
      setBusy(false);
    }
  }

  async function onConfirm(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    if (pw.length < 8) return setErr(t("pwShort"));
    if (pw !== pw2) return setErr(t("pwMismatch"));
    setBusy(true);
    try {
      await authApi.confirmPasswordReset(token!, pw);
      setDone(true);
    } catch (e2: unknown) {
      const e = resolveApiError(e2);
      if (e.kind === "rateLimited") setErr(rateLimitMessage(tErr, e));
      else setErr(e.status === 400 || e.status === 404 || e.status === 422 ? t("badToken") : t("err"));
    } finally {
      setBusy(false);
    }
  }

  const isConfirm = !!token;

  return (
    <div className="w-full max-w-sm mx-auto bg-white rounded-2xl shadow-sm border border-slate-100 p-7">
      <h1 className="text-xl font-bold text-slate-900">{isConfirm ? t("cfmTitle") : t("reqTitle")}</h1>
      <p className="text-sm text-slate-500 mt-1.5 mb-5">{isConfirm ? t("cfmSub") : t("reqSub")}</p>

      {done ? (
        <div className="space-y-4">
          <p className="text-sm text-slate-700 bg-green-soft border border-success/30 rounded-lg px-4 py-3">
            {isConfirm ? t("resetOk") : t("sent")}
          </p>
          <Link href="/login" className="block text-center text-sm font-semibold text-[#2563EB] hover:underline">
            {t("back")}
          </Link>
        </div>
      ) : isConfirm ? (
        <form onSubmit={onConfirm} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">{t("newPw")}</label>
            <input type="password" autoComplete="new-password" placeholder="••••••••"
              value={pw} onChange={(e) => setPw(e.target.value)} className={INPUT} required />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">{t("confirmPw")}</label>
            <input type="password" autoComplete="new-password" placeholder="••••••••"
              value={pw2} onChange={(e) => setPw2(e.target.value)} className={INPUT} required />
          </div>
          {err && <p className="text-xs text-danger">{err}</p>}
          <button type="submit" disabled={busy}
            className="w-full h-11 rounded-lg bg-[#2563EB] text-white text-sm font-semibold hover:opacity-90 disabled:opacity-50">
            {busy ? t("resetting") : t("reset")}
          </button>
          <Link href="/login" className="block text-center text-sm text-slate-500 hover:underline">{t("back")}</Link>
        </form>
      ) : (
        <form onSubmit={onRequest} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">{t("email")}</label>
            <input type="email" autoComplete="email" placeholder={t("emailPlaceholder")}
              value={email} onChange={(e) => setEmail(e.target.value)} className={INPUT} required />
          </div>
          {err && <p className="text-xs text-danger">{err}</p>}
          <button type="submit" disabled={busy}
            className="w-full h-11 rounded-lg bg-[#2563EB] text-white text-sm font-semibold hover:opacity-90 disabled:opacity-50">
            {busy ? t("sending") : t("send")}
          </button>
          <Link href="/login" className="block text-center text-sm text-slate-500 hover:underline">{t("back")}</Link>
        </form>
      )}
    </div>
  );
}
