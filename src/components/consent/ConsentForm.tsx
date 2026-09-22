"use client";
import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { FileText, ShieldAlert, ChevronDown, Lock } from "lucide-react";
import type {
  ConsentChoice, ConsentDocMeta, ConsentPurposePlan, SignupPlan,
} from "@/types/api.types";

// 가입·설정 공용 동의 UI (TERMS_DISPLAY §4·§7). plan 을 그대로 그린다 —
// 법역별 분기(NE 서면·VN⑤미노출·CN차단·② 고지형)는 전부 서버 plan 이 결정.
// embedded=true: 자체 제출 버튼 없이 onChange 로 상태만 방출(온보딩이 자체 버튼으로 제어).
export default function ConsentForm({
  plan, submitting, onSubmit, onChange, mode = "signup", embedded = false,
}: {
  plan: SignupPlan;
  submitting?: boolean;
  onSubmit?: (args: { termsAck: boolean; privacyAck: boolean; choices: ConsentChoice[] }) => void;
  onChange?: (args: { termsAck: boolean; privacyAck: boolean; choices: ConsentChoice[]; canSubmit: boolean }) => void;
  mode?: "signup" | "settings";
  embedded?: boolean;
}) {
  const t = useTranslations("consent");
  const [termsAck, setTermsAck] = useState(false);
  const [privacyAck, setPrivacyAck] = useState(false);
  const [toggles, setToggles] = useState<Record<string, boolean>>({});

  const visiblePurposes = useMemo(
    () => plan.purposes.filter((p) => p.visible).sort((a, b) => a.order - b.order),
    [plan.purposes],
  );

  const buildChoices = (): ConsentChoice[] =>
    visiblePurposes
      .filter((p) => p.is_toggle)
      .map((p) => ({
        purpose_code: p.purpose_code,
        granted: !!toggles[p.purpose_code] && !p.auto_off_if_uoom,
        evidence_ref: p.ui_kind === "WRITTEN_OPT_IN" ? "UI_WRITTEN_OPT_IN" : null,
      }));

  const canSubmitState =
    !plan.gate.signup_blocked && (mode === "settings" || (termsAck && privacyAck));

  // 임베드 모드: 상태 변화를 부모로 방출
  useEffect(() => {
    if (!embedded || !onChange) return;
    onChange({ termsAck, privacyAck, choices: buildChoices(), canSubmit: canSubmitState });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [termsAck, privacyAck, toggles, embedded]);

  // CN 등 가입 차단
  if (plan.gate.signup_blocked) {
    return (
      <div className="bg-surface border border-border rounded-2xl p-8 text-center">
        <Lock className="mx-auto mb-3 text-text3" size={28} />
        <p className="text-sm font-semibold text-text">{t("blocked.title")}</p>
        <p className="text-xs text-text3 mt-1">{t("blocked.desc")}</p>
      </div>
    );
  }

  const setTg = (code: string, v: boolean) => setToggles((s) => ({ ...s, [code]: v }));

  const canSubmit = canSubmitState;

  const submit = () => onSubmit?.({ termsAck, privacyAck, choices: buildChoices() });

  return (
    <div className="space-y-5">
      {/* DRAFT / 게이트 배너 */}
      {plan.any_draft && (
        <Banner tone="warn" icon={<ShieldAlert size={14} />} text={t("banner.draft")} />
      )}
      {plan.lang_gate && <Banner tone="warn" text={t("banner.langGate")} />}
      {plan.gate.release_hold && <Banner tone="info" text={t("banner.releaseHold")} />}
      {plan.gate.paid_blocked && <Banner tone="info" text={t("banner.paidGate")} />}
      {plan.jurisdiction.counsel_review && <Banner tone="info" text={t("banner.counsel")} />}

      {/* 문서 세트 */}
      <section>
        <p className="text-xs font-semibold text-text3 tracking-wider font-mono mb-2">
          {t("documentsTitle")} · <span className="text-text2">{plan.notice_version}</span>
        </p>
        <div className="space-y-2">
          {plan.documents.map((d) => <DocCard key={d.doc_id} doc={d} t={t} />)}
        </div>
      </section>

      {/* 필수 동의 2체크 (묶음 금지 — 개별) */}
      {mode === "signup" && (
        <section className="space-y-2">
          <CheckRow checked={termsAck} onChange={setTermsAck} required label={t("ack.terms")} />
          <CheckRow checked={privacyAck} onChange={setPrivacyAck} required label={t("ack.privacy")} />
        </section>
      )}

      {/* 목적별 */}
      <section className="space-y-2">
        {visiblePurposes.map((p) => (
          <PurposeRow
            key={p.purpose_code}
            p={p}
            t={t}
            checked={!!toggles[p.purpose_code]}
            onToggle={(v) => setTg(p.purpose_code, v)}
            doNotSellLink={plan.state_flags.do_not_sell_link}
            excludeLocation={plan.state_flags.exclude_location_from_sale}
          />
        ))}
      </section>

      {!embedded && (
        <button
          onClick={submit}
          disabled={!canSubmit || submitting}
          className="w-full bg-primary text-white rounded-xl py-3 text-sm font-bold disabled:opacity-50"
        >
          {submitting ? "…" : mode === "signup" ? t("submit.signup") : t("submit.settings")}
        </button>
      )}
    </div>
  );
}

function Banner({ tone, text, icon }: { tone: "warn" | "info"; text: string; icon?: React.ReactNode }) {
  const cls = tone === "warn"
    ? "bg-amber-soft text-warning border-warning/30"
    : "bg-primary-soft/40 text-text2 border-primary/20";
  return (
    <div className={`flex items-start gap-2 text-xs rounded-xl border px-3 py-2 ${cls}`}>
      {icon}<span className="leading-relaxed">{text}</span>
    </div>
  );
}

function DocCard({ doc, t }: { doc: ConsentDocMeta; t: (k: string) => string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden">
      <button onClick={() => setOpen((o) => !o)} className="w-full flex items-center gap-2 px-4 py-3 text-left">
        <FileText size={14} className="text-text3 shrink-0" />
        <span className="text-sm font-semibold text-text flex-1 truncate">
          {t(`doc.${doc.doc_id}`)}
        </span>
        <span className="text-[10px] font-mono text-text3">v{doc.version}</span>
        {doc.status.startsWith("DRAFT") && (
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-soft text-warning border border-warning/30">DRAFT</span>
        )}
        {doc.lang_pending && (
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-bg2 text-text3 border border-border">
            {t("langPending")}
          </span>
        )}
        <ChevronDown size={14} className={`text-text3 transition ${open ? "rotate-180" : ""}`} />
      </button>
      {open && doc.body && (
        <pre className="px-4 pb-4 text-xs text-text2 whitespace-pre-wrap font-sans leading-relaxed border-t border-border pt-3 max-h-64 overflow-y-auto">
          {doc.body}
        </pre>
      )}
    </div>
  );
}

function CheckRow({
  checked, onChange, label, required,
}: { checked: boolean; onChange: (v: boolean) => void; label: string; required?: boolean }) {
  return (
    <label className="flex items-start gap-2.5 cursor-pointer bg-surface border border-border rounded-xl px-4 py-3">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 accent-primary" />
      <span className="text-sm text-text leading-relaxed">
        {required && <span className="text-danger font-bold mr-1">*</span>}{label}
      </span>
    </label>
  );
}

function PurposeRow({
  p, t, checked, onToggle, doNotSellLink, excludeLocation,
}: {
  p: ConsentPurposePlan; t: (k: string) => string;
  checked: boolean; onToggle: (v: boolean) => void;
  doNotSellLink: boolean; excludeLocation: boolean;
}) {
  const label = t(`purpose.${p.purpose_code}.label`);
  const desc = t(`purpose.${p.purpose_code}.desc`);

  // ① 서비스 운영 = 계약 이행 고지(토글 아님)
  const isNoticeOnly = !p.is_toggle;

  return (
    <div className="bg-surface border border-border rounded-xl px-4 py-3">
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-text">{label}</span>
            <KindBadge kind={p.ui_kind} t={t} />
          </div>
          <p className="text-xs text-text3 mt-1 leading-relaxed">{desc}</p>

          {/* ② 고지형: 제외/이의 링크 */}
          {p.ui_kind === "NOTICE_EXCLUSION" && (
            <a className="text-xs text-primary font-semibold mt-1.5 inline-block" href="#exclusion">
              {t("action.exclusion")}
            </a>
          )}
          {p.ui_kind === "LI_OBJECT" && (
            <a className="text-xs text-primary font-semibold mt-1.5 inline-block" href="#object">
              {t("action.object")}
            </a>
          )}
          {p.ui_kind === "WRITTEN_OPT_IN" && (
            <p className="text-[11px] text-warning mt-1.5">{t("action.written")}</p>
          )}
          {p.purpose_code === "TRANSACTION_MATCHING" && excludeLocation && (
            <p className="text-[11px] text-text3 mt-1">{t("note.locationExcluded")}</p>
          )}
          {p.purpose_code === "TRANSACTION_MATCHING" && doNotSellLink && (
            <a className="text-xs text-primary font-semibold mt-1 inline-block" href="#do-not-sell">
              {t("action.doNotSell")}
            </a>
          )}
          {p.auto_off_if_uoom && (
            <p className="text-[11px] text-text3 mt-1">{t("note.uoomAutoOff")}</p>
          )}
        </div>

        {/* 토글(옵트인/서면/이전동의) */}
        {!isNoticeOnly && (
          <button
            type="button"
            onClick={() => onToggle(!checked)}
            disabled={p.auto_off_if_uoom}
            aria-pressed={checked}
            className={`shrink-0 w-11 h-6 rounded-full transition relative ${
              checked ? "bg-primary" : "bg-bg2"
            } ${p.auto_off_if_uoom ? "opacity-40" : ""}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition ${checked ? "translate-x-5" : ""}`} />
          </button>
        )}
      </div>
    </div>
  );
}

function KindBadge({ kind, t }: { kind: string; t: (k: string) => string }) {
  const map: Record<string, string> = {
    NOTICE: "bg-bg2 text-text3 border-border",
    NOTICE_EXCLUSION: "bg-bg2 text-text3 border-border",
    LI_OBJECT: "bg-bg2 text-text3 border-border",
    OPT_IN: "bg-primary-soft/50 text-primary border-primary/30",
    WRITTEN_OPT_IN: "bg-amber-soft text-warning border-warning/30",
    TRANSFER_CONSENT: "bg-amber-soft text-warning border-warning/30",
  };
  return (
    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${map[kind] || "bg-bg2 text-text3 border-border"}`}>
      {t(`kind.${kind}`)}
    </span>
  );
}
