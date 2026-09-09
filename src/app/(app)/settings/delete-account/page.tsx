"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { authApi } from "@/lib/api/endpoints/auth";
import { resolveApiError, withRequestId } from "@/lib/api/errors";
import { useAuthStore } from "@/store/auth.store";
import { X } from "lucide-react";

/**
 * 계정 삭제 — Apple Guideline 5.1.1(v) / PIPA §21 / GDPR Art.17.
 *
 * ★ 2026-08-25 독립검증(BLOCKER)에서 잡힌 두 가지를 고쳤다:
 *   ① 삭제 버튼에 onClick 이 없어 **아무 일도 일어나지 않는 죽은 UI** 였다.
 *   ② `ownerOnly` 로 일반 구성원의 **자기 계정** 삭제를 막고 있었다.
 *      계정을 만들 수 있는 사람은 누구나 지울 수 있어야 한다 — 농장 소유 여부와 무관하다.
 *      (Apple 은 "모든 사용자"를 명시하고, PIPA·GDPR 의 삭제권도 본인 계정에 대한 권리다.)
 *
 * 문구도 실제 서버 동작에 맞췄다. 이전 문구는 "30일간 복구 가능"과 "농장 데이터 삭제"를
 * 약속했는데 서버는 즉시 비가역 익명화 + 농장 비활성화다. 지킬 수 없는 고지였다.
 */
export default function DeleteAccountPage() {
  const t = useTranslations("deleteAccount");
  const tErr = useTranslations("errors");
  const router = useRouter();
  const clearAuth = useAuthStore((s) => s.clearAuth);

  const [confirm, setConfirm] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confirmWord = t("confirmWord");
  const canDelete = confirm === confirmWord && password.length > 0 && !busy;

  const onDelete = async () => {
    setError(null);
    setBusy(true);
    try {
      await authApi.deleteAccount(password);
      // 서버에서 이미 세션이 무효화됐다 — 로컬 상태도 즉시 비운다.
      clearAuth();
      document.cookie = "pigos_session=; path=/; max-age=0; SameSite=Lax";
      router.replace("/login?deleted=1");
    } catch (err: unknown) {
      const e = resolveApiError(err);
      // 403 은 "권한 없음"이 아니라 비밀번호 불일치다 — 이 화면에서만 뜻이 다르다.
      setError(
        e.status === 403
          ? t("wrongPassword")
          : withRequestId(tErr(e.messageKey), e.requestId),
      );
      setBusy(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto px-7 py-6">
      <h1 className="text-xl font-extrabold tracking-tight mb-5">{t("title")}</h1>
      <div className="bg-surface border border-border rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-11 h-11 rounded-xl bg-red-soft flex items-center justify-center shrink-0">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#DC2626" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </div>
          <div>
            <div className="text-base font-bold text-text">{t("sure")}</div>
            <div className="text-xs text-text3 mt-0.5">{t("irreversible")}</div>
          </div>
        </div>

        <div className="bg-red-soft border border-danger/30 rounded-xl p-4 mb-4">
          <div className="text-xs font-bold text-danger mb-2">{t("lostTitle")}</div>
          {[t("l1"), t("l2"), t("l3")].map((x, i) => (
            <div key={i} className="text-xs text-text2 flex items-start gap-2 py-1">
              <X size={14} className="text-danger shrink-0 mt-0.5" strokeWidth={2.75} aria-hidden />
              <span>{x}</span>
            </div>
          ))}
        </div>

        {/* 남는 것도 함께 고지한다 — 안 적으면 "영구 삭제" 약속과 실제가 어긋난다. */}
        <div className="bg-bg2 border border-border rounded-xl p-4 mb-5">
          <div className="text-xs font-bold text-text2 mb-2">{t("keptTitle")}</div>
          {[t("k1"), t("k2"), t("k3")].map((x, i) => (
            <div key={i} className="text-xs text-text3 flex items-start gap-2 py-1">
              <span className="text-text3 leading-5">•</span>
              <span>{x}</span>
            </div>
          ))}
          <p className="text-[11px] text-text3 mt-2 leading-relaxed">{t("policyNote")}</p>
        </div>

        <p className="text-xs text-text3 leading-relaxed mb-5">
          {t("exportPre")}
          <span className="text-primary font-semibold cursor-pointer">{t("exportLink")}</span>
          {t("exportPost")}
        </p>

        <div className="mb-4">
          <label htmlFor="confirm-word" className="block text-xs font-semibold text-text2 mb-2">
            {t("typeToConfirm", { word: confirmWord })}
          </label>
          <input
            id="confirm-word"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder={confirmWord}
            className="input w-full"
          />
        </div>

        <div className="mb-5">
          <label htmlFor="delete-password" className="block text-xs font-semibold text-text2 mb-2">
            {t("passwordLabel")}
          </label>
          <input
            id="delete-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input w-full"
          />
          <p className="text-[11px] text-text3 mt-1.5">{t("passwordHint")}</p>
        </div>

        {error && (
          <p role="alert" className="text-sm text-danger mb-4">{error}</p>
        )}

        <div className="flex gap-2">
          <button type="button" onClick={() => router.back()} disabled={busy}
            className="flex-1 bg-surface border border-border text-text2 py-3 rounded-xl text-sm font-semibold hover:bg-border transition disabled:opacity-40">
            {t("cancel")}
          </button>
          <button type="button" onClick={onDelete} disabled={!canDelete}
            className="flex-1 bg-danger text-white py-3 rounded-xl text-sm font-bold disabled:opacity-40 hover:opacity-90 transition">
            {busy ? t("deleting") : t("deleteForever")}
          </button>
        </div>
      </div>
    </div>
  );
}
