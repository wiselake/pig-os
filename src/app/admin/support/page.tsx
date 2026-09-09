"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, MessageSquare } from "lucide-react";
import { adminApi } from "@/lib/api/endpoints/admin";
import type { SupportTicketOut } from "@/types/api.types";

const STATUS_FILTERS = ["ALL", "OPEN", "ANSWERED", "CLOSED"] as const;
const ST_CLS: Record<string, string> = {
  OPEN: "bg-amber-soft text-warning border-warning/40",
  ANSWERED: "bg-green-soft text-success border-success/30",
  CLOSED: "bg-bg2 text-text3 border-border",
};

export default function AdminSupportPage() {
  const t = useTranslations("admin");
  const [status, setStatus] = useState<(typeof STATUS_FILTERS)[number]>("ALL");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const PER_PAGE = 25;

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "tickets", status, page],
    queryFn: () => adminApi.tickets({ status: status === "ALL" ? undefined : status, page, per_page: PER_PAGE }),
  });

  const rows = data?.items ?? [];
  const totalPages = data?.meta?.pages ?? 1;
  const setStatusReset = (s: (typeof STATUS_FILTERS)[number]) => { setStatus(s); setPage(1); };

  return (
    <div className="p-7 max-w-6xl">
      <header className="mb-5">
        <h1 className="text-[22px] font-extrabold tracking-tight">{t("supTitle")}</h1>
        <p className="text-xs text-text3 mt-0.5">{t("supSubtitle")}</p>
      </header>

      <div className="flex gap-1.5 mb-4">
        {STATUS_FILTERS.map((s) => (
          <button key={s} onClick={() => setStatusReset(s)}
            className={`px-3 py-1.5 rounded-full text-[13px] font-semibold border transition ${status === s ? "bg-console text-white border-console" : "bg-surface border-border text-text2 hover:bg-bg2"}`}>
            {s === "ALL" ? t("filterAll") : t(`ts${s.charAt(0)}${s.slice(1).toLowerCase()}`)}
          </button>
        ))}
      </div>

      <div className="bg-surface border border-border rounded-2xl overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-text3 text-sm">…</div>
        ) : rows.length === 0 ? (
          <div className="p-12 text-center text-text3 text-sm">{t("supEmpty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-bg2 text-text3 text-[11px] uppercase tracking-wide">
                <th className="text-left px-4 py-2.5 font-bold">{t("supColSubject")}</th>
                <th className="text-left px-4 py-2.5 font-bold">{t("colStatus")}</th>
                <th className="text-left px-4 py-2.5 font-bold">{t("supColDate")}</th>
                <th className="text-right px-4 py-2.5 font-bold">{t("colActions")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((tk: SupportTicketOut) => (
                <tr key={tk.id} className="border-t border-border">
                  <td className="px-4 py-2.5 font-semibold text-text">{tk.subject}</td>
                  <td className="px-4 py-2.5">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${ST_CLS[tk.status]}`}>
                      {t(`ts${tk.status.charAt(0)}${tk.status.slice(1).toLowerCase()}`)}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-text3 text-xs font-mono">{tk.created_at?.slice(0, 10)}</td>
                  <td className="px-4 py-2.5 text-right">
                    <button onClick={() => setSelected(tk.id)} className="inline-flex items-center gap-1 text-primary text-xs font-semibold hover:underline">
                      <MessageSquare size={12} /> {t("supOpen")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!isLoading && totalPages > 1 && (
          <div className="flex items-center justify-end gap-1.5 px-4 py-3 border-t border-border text-xs">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}
              className="px-3 py-1.5 rounded-lg border border-border bg-surface font-semibold disabled:opacity-40 hover:bg-bg2 transition">
              {t("prev")}
            </button>
            <span className="font-mono text-text3 px-1">{page} / {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
              className="px-3 py-1.5 rounded-lg border border-border bg-surface font-semibold disabled:opacity-40 hover:bg-bg2 transition">
              {t("next")}
            </button>
          </div>
        )}
      </div>

      {selected && <TicketDrawer t={t} ticketId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function TicketDrawer({ t, ticketId, onClose }: { t: (k: string) => string; ticketId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [reply, setReply] = useState("");
  const { data: ticket } = useQuery({
    queryKey: ["admin", "ticket", ticketId],
    queryFn: () => adminApi.ticket(ticketId),
  });

  const send = useMutation({
    mutationFn: () => adminApi.replyTicket(ticketId, reply),
    onSuccess: () => {
      setReply("");
      qc.invalidateQueries({ queryKey: ["admin", "ticket", ticketId] });
      qc.invalidateQueries({ queryKey: ["admin", "tickets"] });
    },
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex justify-end" onClick={onClose}>
      <div className="bg-surface w-full max-w-md h-full overflow-y-auto p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        {!ticket ? (
          <p className="text-text3 text-sm">…</p>
        ) : (
          <>
            <div className="text-base font-bold text-text mb-1">{ticket.subject}</div>
            <div className="text-[11px] text-text3 font-mono mb-4">{ticket.status} · {ticket.created_at?.slice(0, 10)}</div>
            <div className="bg-bg2 rounded-xl p-3 text-sm text-text2 mb-3 whitespace-pre-wrap">{ticket.body}</div>
            <div className="space-y-2 mb-4">
              {ticket.replies.map((r) => (
                <div key={r.id} className={`rounded-xl p-3 text-sm ${r.is_staff ? "bg-green-soft text-text2 ml-6" : "bg-bg2 text-text2 mr-6"}`}>
                  <div className="text-[10px] font-bold text-text3 mb-1">{r.is_staff ? t("supStaff") : t("supCustomer")} · {r.created_at?.slice(0, 10)}</div>
                  <div className="whitespace-pre-wrap">{r.body}</div>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <textarea value={reply} onChange={(e) => setReply(e.target.value)} placeholder={t("supReplyPlaceholder")} rows={3}
                className="flex-1 px-3 py-2 rounded-lg border border-border bg-bg2 text-sm outline-none focus:border-primary resize-y" />
            </div>
            <button onClick={() => send.mutate()} disabled={!reply.trim() || send.isPending}
              className="mt-2 w-full inline-flex items-center justify-center gap-1.5 bg-primary text-white rounded-lg py-2 text-sm font-semibold disabled:opacity-50">
              <Send size={14} /> {t("supSendReply")}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
