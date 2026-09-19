"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, Check, X, Power, KeyRound } from "lucide-react";
import { adminApi } from "@/lib/api/endpoints/admin";
import type { AdminMemberRow, PilotSignupRow } from "@/types/api.types";

type Tab = "members" | "pilots";
const STATUS_FILTERS = ["ALL", "PENDING", "APPROVED", "REJECTED"] as const;

const STATUS_CLS: Record<string, string> = {
  PENDING: "bg-amber-soft text-warning border-warning/40",
  APPROVED: "bg-green-soft text-success border-success/30",
  REJECTED: "bg-red-soft text-danger border-danger/40",
};

export default function AdminUsersPage() {
  const t = useTranslations("admin");
  const [tab, setTab] = useState<Tab>("members");

  return (
    <div className="p-7 max-w-6xl">
      <header className="mb-5">
        <h1 className="text-[22px] font-extrabold tracking-tight">{t("usersTitle")}</h1>
        <p className="text-xs text-text3 mt-0.5">{t("usersSubtitle")}</p>
      </header>

      <div className="flex gap-1.5 mb-5 border-b border-border">
        {(["members", "pilots"] as Tab[]).map((tb) => (
          <button
            key={tb}
            onClick={() => setTab(tb)}
            className={`px-4 py-2 text-sm font-semibold -mb-px border-b-2 transition ${
              tab === tb ? "border-primary text-primary" : "border-transparent text-muted hover:text-text"
            }`}
          >
            {t(tb === "members" ? "tabMembers" : "tabPilots")}
          </button>
        ))}
      </div>

      {tab === "members" ? <MembersTab t={t} /> : <PilotsTab t={t} />}
    </div>
  );
}

function MembersTab({ t }: { t: (k: string, v?: Record<string, string | number>) => string }) {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<(typeof STATUS_FILTERS)[number]>("ALL");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "members", q, status, page],
    queryFn: () => adminApi.members({ q: q || undefined, status: status === "ALL" ? undefined : status, page, per_page: 20 }),
  });

  const mut = useMutation({
    mutationFn: ({ id, body }: { id: string; body: { approval_status?: string; active?: boolean } }) =>
      adminApi.updateMemberStatus(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "members"] }),
  });

  const resetMut = useMutation({
    mutationFn: (id: string) => adminApi.resetMemberPassword(id),
    // 무발송 환경: 임시 비번을 운영자에게 표시 → 사용자에게 직접 전달(가입승인 UX와 동일 패턴).
    onSuccess: (res) => window.alert(t("resetPwDone", { email: res.email, pw: res.temp_password })),
    onError: () => window.alert(t("resetPwError")),
  });

  const rows = data?.items ?? [];
  const meta = data?.meta;

  return (
    <>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <div className="relative w-64">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text3" />
          <input
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1); }}
            placeholder={t("searchPlaceholder")}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-surface text-sm outline-none focus:border-primary"
          />
        </div>
        <div className="flex gap-1.5">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => { setStatus(s); setPage(1); }}
              className={`px-3 py-1.5 rounded-full text-[13px] font-semibold border transition ${
                status === s ? "bg-console text-white border-console" : "bg-surface border-border text-text2 hover:bg-bg2"
              }`}
            >
              {s === "ALL" ? t("filterAll") : t(`st${s.charAt(0)}${s.slice(1).toLowerCase()}`)}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-surface border border-border rounded-2xl overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-text3 text-sm">…</div>
        ) : rows.length === 0 ? (
          <div className="p-12 text-center text-text3 text-sm">{t("empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-bg2 text-text3 text-[11px] uppercase tracking-wide">
                <th className="text-left px-4 py-2.5 font-bold">{t("colName")}</th>
                <th className="text-left px-4 py-2.5 font-bold">{t("colRole")}</th>
                <th className="text-left px-4 py-2.5 font-bold">{t("colStatus")}</th>
                <th className="text-left px-4 py-2.5 font-bold">{t("colOrg")}</th>
                <th className="text-right px-4 py-2.5 font-bold">{t("colFarms")}</th>
                <th className="text-right px-4 py-2.5 font-bold">{t("colActions")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((m: AdminMemberRow) => (
                <tr key={m.id} className="border-t border-border">
                  <td className="px-4 py-2.5">
                    <div className="font-semibold text-text">{m.name}</div>
                    <div className="text-[11px] text-text3 font-mono">{m.email ?? "—"}</div>
                  </td>
                  <td className="px-4 py-2.5 text-text2 text-xs font-mono">{m.system_role}</td>
                  <td className="px-4 py-2.5">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${STATUS_CLS[m.approval_status] ?? ""}`}>
                      {t(`st${m.approval_status.charAt(0)}${m.approval_status.slice(1).toLowerCase()}`)}
                    </span>
                    {!m.active && <span className="ml-1 text-[10px] text-text3">· {t("inactive")}</span>}
                  </td>
                  <td className="px-4 py-2.5 text-text3 text-xs">{m.org_name ?? "—"}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{m.farm_count}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center justify-end gap-1">
                      {m.approval_status !== "APPROVED" && (
                        <button onClick={() => mut.mutate({ id: m.id, body: { approval_status: "APPROVED", active: true } })}
                          title={t("actApprove")} className="p-1.5 rounded-md text-success hover:bg-green-soft transition"><Check size={14} /></button>
                      )}
                      {m.approval_status !== "REJECTED" && (
                        <button onClick={() => mut.mutate({ id: m.id, body: { approval_status: "REJECTED", active: false } })}
                          title={t("actReject")} className="p-1.5 rounded-md text-danger hover:bg-red-soft transition"><X size={14} /></button>
                      )}
                      <button onClick={() => mut.mutate({ id: m.id, body: { active: !m.active } })}
                        title={m.active ? t("actDeactivate") : t("actActivate")}
                        className={`p-1.5 rounded-md transition ${m.active ? "text-text3 hover:bg-bg2" : "text-warning hover:bg-amber-soft"}`}><Power size={14} /></button>
                      <button onClick={() => { if (window.confirm(t("resetPwConfirm", { name: m.name }))) resetMut.mutate(m.id); }}
                        title={t("actResetPw")}
                        className="p-1.5 rounded-md text-text3 hover:bg-bg2 transition"><KeyRound size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {meta && meta.pages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-4 text-xs">
          <button disabled={page === 1} onClick={() => setPage((p) => p - 1)} className="px-3 py-1.5 rounded-lg border border-border disabled:opacity-40">{t("prev")}</button>
          <span className="text-text3 font-mono">{page} / {meta.pages}</span>
          <button disabled={page >= meta.pages} onClick={() => setPage((p) => p + 1)} className="px-3 py-1.5 rounded-lg border border-border disabled:opacity-40">{t("next")}</button>
        </div>
      )}
    </>
  );
}

function PilotsTab({ t }: { t: (k: string, v?: Record<string, string | number>) => string }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "pilots"],
    queryFn: () => adminApi.pilotSignups({ per_page: 50 }),
  });

  const approve = useMutation({
    mutationFn: ({ id, pw }: { id: string; pw: string }) => adminApi.approvePilot(id, { initial_password: pw }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["admin", "pilots"] });
      window.alert(t("approveDone", { email: res.email, pw: res.initial_password }));
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      window.alert(typeof msg === "string" ? msg : "Error");
    },
  });

  const rows = data?.items ?? [];

  function onApprove(p: PilotSignupRow) {
    const pw = window.prompt(t("approvePrompt", { name: p.name }));
    if (pw && pw.length >= 8) approve.mutate({ id: p.id, pw });
    else if (pw) window.alert(t("pwTooShort"));
  }

  return (
    <div className="bg-surface border border-border rounded-2xl overflow-hidden">
      {isLoading ? (
        <div className="p-12 text-center text-text3 text-sm">…</div>
      ) : rows.length === 0 ? (
        <div className="p-12 text-center text-text3 text-sm">{t("emptyPilots")}</div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-bg2 text-text3 text-[11px] uppercase tracking-wide">
              <th className="text-left px-4 py-2.5 font-bold">{t("colName")}</th>
              <th className="text-left px-4 py-2.5 font-bold">{t("colCountry")}</th>
              <th className="text-left px-4 py-2.5 font-bold">{t("colSize")}</th>
              <th className="text-left px-4 py-2.5 font-bold">{t("colStatus")}</th>
              <th className="text-right px-4 py-2.5 font-bold">{t("colActions")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p: PilotSignupRow) => (
              <tr key={p.id} className="border-t border-border">
                <td className="px-4 py-2.5">
                  <div className="font-semibold text-text">{p.name}</div>
                  <div className="text-[11px] text-text3 font-mono">{p.email}</div>
                </td>
                <td className="px-4 py-2.5 text-text2 text-xs">{p.country}</td>
                <td className="px-4 py-2.5 text-text3 text-xs font-mono">{p.farm_size}</td>
                <td className="px-4 py-2.5 text-text3 text-xs">{p.status}</td>
                <td className="px-4 py-2.5 text-right">
                  {p.status !== "onboarded" ? (
                    <button onClick={() => onApprove(p)} className="text-xs font-semibold text-white bg-primary px-3 py-1.5 rounded-lg hover:opacity-90">
                      {t("actApproveAccount")}
                    </button>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[11px] text-success font-semibold"><Check size={12} strokeWidth={2.5} aria-hidden />{t("psOnboarded")}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
