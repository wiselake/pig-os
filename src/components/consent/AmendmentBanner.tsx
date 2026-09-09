"use client";
import { useMemo } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { BellRing, X } from "lucide-react";
import { consentApi } from "@/lib/api/endpoints/consent";
import { farmsApi } from "@/lib/api/endpoints/farms";
import { useAuthStore } from "@/store/auth.store";
import { useState } from "react";

// 개정 재고지 배너 (TERMS_DISPLAY §6): 기록된 notice_version 이 현재 문서 버전과 다르면
// 로그인 시 변경 안내. 강제 재동의 여부는 법무 판정(후속) — 여기선 고지+설정 이동만.
export default function AmendmentBanner() {
  const t = useTranslations("consent");
  const activeFarmId = useAuthStore((s) => s.activeFarmId);
  const isAuthed = useAuthStore((s) => !!s.accessToken);
  const [dismissed, setDismissed] = useState(false);

  const { data: farms } = useQuery({
    queryKey: ["farms"], queryFn: () => farmsApi.list(), enabled: isAuthed,
  });
  const farm = useMemo(
    () => farms?.find((f) => f.id === activeFarmId) ?? farms?.[0],
    [farms, activeFarmId],
  );

  const { data: current } = useQuery({
    queryKey: ["consent", "current", activeFarmId],
    queryFn: () => consentApi.current(activeFarmId ?? undefined),
    enabled: isAuthed && !!activeFarmId,
  });

  const { data: plan } = useQuery({
    queryKey: ["consent", "plan", farm?.country],
    queryFn: () => consentApi.signupPlan({
      selected_country: farm!.country, farm_country: farm!.country, include_body: false,
    }),
    enabled: !!farm?.country,
  });

  // 기록이 하나라도 있고, 그 중 어떤 것이든 현재 문서 버전과 다르면 개정 발생.
  const outdated = useMemo(() => {
    if (!current?.length || !plan) return false;
    return current.some((c) => c.notice_version && c.notice_version !== plan.notice_version);
  }, [current, plan]);

  if (dismissed || !outdated) return null;

  return (
    <div className="mx-4 mt-3 flex items-start gap-2.5 bg-amber-soft border border-warning/30 rounded-xl px-4 py-3">
      <BellRing size={16} className="text-warning mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-text">{t("amendment.title")}</p>
        <p className="text-xs text-text2 mt-0.5 leading-relaxed">{t("amendment.desc")}</p>
        <Link href="/settings/data" className="inline-block mt-1.5 text-xs font-semibold text-primary">
          {t("amendment.review")}
        </Link>
      </div>
      <button onClick={() => setDismissed(true)} aria-label={t("dismiss")} className="text-text3 hover:text-text shrink-0">
        <X size={14} />
      </button>
    </div>
  );
}
