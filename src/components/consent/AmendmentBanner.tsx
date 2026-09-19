"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { BellRing, X } from "lucide-react";
import { consentApi } from "@/lib/api/endpoints/consent";
import { useAuthStore } from "@/store/auth.store";

// 개정 재고지 배너 (TERMS_DISPLAY §6): 기록된 notice_version 이 현재 문서 버전과 다르면
// 로그인 시 변경 안내. 강제 재동의 여부는 법무 판정(후속) — 여기선 고지+설정 이동만.
//
// ★ 비교의 입력은 GET /consent/diff 하나다 (PLATFORM_PARITY §9-8). 예전에는 farms.list 로
//   farm.country 를 얻어 signupPlan 을 다시 부르고 클라이언트에서 비교했다 — 그러면
//   법역을 정하는 곳이 서버(가입 경로)와 여기 둘이 된다. 국가는 서버가 정한다.
//
// ★ 이 배너는 게이트가 아니다 (LEGAL-P0-MANDATORY-CONSENT-LOGIN-GATE). 기록이 0행이면
//   아무것도 뜨지 않는다 — "동의가 아예 없음"은 처음부터 범위 밖이다.
export default function AmendmentBanner() {
  const t = useTranslations("consent");
  const activeFarmId = useAuthStore((s) => s.activeFarmId);
  const isAuthed = useAuthStore((s) => !!s.accessToken);
  const [dismissed, setDismissed] = useState(false);

  const { data: diff } = useQuery({
    queryKey: ["consent", "diff", activeFarmId],
    queryFn: () => consentApi.diff(activeFarmId),
    enabled: isAuthed && !!activeFarmId,
  });

  // 기록이 있는 목적 중 하나라도 필요 버전과 다르면 개정 발생.
  // 필요 버전 자체가 초안(any_draft)이면 고지하지 않는다 — 초안에는 재동의를 받을 수
  // 없고(G-3, record 가 451), "검토하라"고 보내도 할 수 있는 일이 없다.
  const outdated = useMemo(() => {
    if (!diff || diff.any_draft) return false;
    return diff.items.some((i) => i.recorded_version && i.recorded_version !== i.required_version);
  }, [diff]);

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
