"use client";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { useMutation } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth.store";
import { authApi } from "@/lib/api/endpoints/auth";
import { Check } from "lucide-react";

export default function ProfilePage() {
  const t = useTranslations("profile");
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const [name, setName] = useState(user?.name ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 기존엔 저장 버튼이 no-op(가짜 '저장됨' 토스트)이던 버그 — 실제 PATCH /me 연동.
  const mutation = useMutation({
    mutationFn: () => authApi.updateMe({ name: name.trim(), phone: phone.trim() }),
    onSuccess: (me) => {
      if (user) setUser({ ...user, name: me.name, phone: me.phone ?? null });
      setError(null);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    },
    onError: () => setError(t("saveError")),
  });

  const handleSave = () => {
    if (!name.trim()) { setError(t("nameRequired")); return; }
    mutation.mutate();
  };

  const initials = name.slice(0, 2).toUpperCase() || "??";

  return (
    <div className="max-w-xl mx-auto px-7 py-6">
      <h1 className="text-xl font-extrabold tracking-tight mb-5">{t("title")}</h1>

      {saved && (
        <div className="mb-4 px-4 py-2.5 bg-green-soft border border-success/30 rounded-xl text-sm text-success font-medium flex items-center gap-2">
          <Check size={14} strokeWidth={2.5} aria-hidden />
          {t("saved")}
        </div>
      )}
      {error && (
        <div className="mb-4 px-4 py-2.5 bg-red-soft border border-danger/30 rounded-xl text-sm text-danger font-medium">
          {error}
        </div>
      )}

      <div className="flex items-center gap-4 mb-6">
        <div className="w-16 h-16 rounded-full bg-success text-white flex items-center justify-center text-xl font-bold">
          {initials}
        </div>
        <button className="px-4 py-2 rounded-xl border border-border bg-surface text-xs font-semibold text-text2 hover:bg-border transition">
          {t("changePhoto")}
        </button>
      </div>

      <div className="bg-surface border border-border rounded-2xl p-6 space-y-4">
        {[
          { label: t("name"), value: name, set: setName, type: "text", placeholder: t("namePh") },
          { label: t("email"), value: user?.email ?? "", set: () => {}, type: "email", placeholder: "", disabled: true },
          { label: t("phone"), value: phone, set: setPhone, type: "tel", placeholder: "010-0000-0000" },
        ].map(({ label, value, set, type, placeholder, disabled }) => (
          <div key={label}>
            <label className="block text-xs font-semibold text-text3 mb-1.5">{label}</label>
            <input
              type={type}
              value={value}
              onChange={(e) => (set as (v: string) => void)(e.target.value)}
              placeholder={placeholder}
              disabled={disabled}
              className="input w-full disabled:opacity-50 disabled:bg-background"
            />
          </div>
        ))}
      </div>

      <button
        onClick={handleSave}
        disabled={mutation.isPending}
        className="w-full mt-4 bg-navy text-white py-3.5 rounded-xl text-sm font-bold hover:opacity-90 transition disabled:opacity-50"
      >
        {mutation.isPending ? t("saving") : t("save")}
      </button>
    </div>
  );
}
