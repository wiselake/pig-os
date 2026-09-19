"use client";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquarePlus, Send, ChevronLeft, MessageCircle, Mail, Phone, type LucideIcon } from "lucide-react";
import { contentApi } from "@/lib/api/endpoints/content";
import type { SupportTicketOut } from "@/types/api.types";

const STATUS_CLS: Record<string, string> = {
  OPEN: "bg-amber-soft text-warning border-warning/40",
  ANSWERED: "bg-green-soft text-success border-success/30",
  CLOSED: "bg-bg2 text-text3 border-border",
};

export default function SupportPage() {
  const t = useTranslations("support");
  const [open, setOpen] = useState<number | null>(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [composing, setComposing] = useState(false);
  const faqs = t.raw("faqs") as { q: string; a: string }[];
  const contacts: [LucideIcon, string, string][] = [
    [MessageCircle, t("chat"), t("chatHours")],
    [Mail, t("email"), "help@pigos.io"],
    [Phone, t("phone"), "1588-0000"],
  ];

  const st = (s: string) => t(s === "OPEN" ? "statusOpen" : s === "ANSWERED" ? "statusAnswered" : "statusClosed");

  return (
    <div className="max-w-5xl mx-auto px-7 py-6">
      <h1 className="text-xl font-extrabold tracking-tight mb-5">{t("title")}</h1>

      <div className="grid grid-cols-3 gap-3 mb-7">
        {contacts.map(([Icon, label, s], i) => (
          <div key={i} className="bg-surface border border-border rounded-2xl p-5">
            <div className="mb-2.5 text-primary"><Icon size={20} strokeWidth={1.5} aria-hidden /></div>
            <div className="text-sm font-bold text-text">{label}</div>
            <div className="text-xs text-text3 mt-1">{s}</div>
          </div>
        ))}
      </div>

      {/* 내 문의함 */}
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold text-text3 tracking-wider font-mono">{t("myTicketsTitle")}</p>
        {!composing && !selected && (
          <button
            onClick={() => setComposing(true)}
            className="inline-flex items-center gap-1.5 text-xs font-semibold bg-primary text-white rounded-lg px-3 py-1.5 hover:opacity-90"
          >
            <MessageSquarePlus size={14} /> {t("newTicket")}
          </button>
        )}
      </div>

      {composing ? (
        <NewTicketForm t={t} onClose={() => setComposing(false)} onCreated={(id) => { setComposing(false); setSelected(id); }} />
      ) : selected ? (
        <TicketThread t={t} st={st} ticketId={selected} onBack={() => setSelected(null)} />
      ) : (
        <TicketList t={t} st={st} onSelect={setSelected} />
      )}

      <p className="text-xs font-semibold text-text3 tracking-wider font-mono mt-8 mb-3">{t("faqTitle")}</p>
      <div className="space-y-2">
        {faqs.map(({ q, a }, i) => (
          <div key={i} className="bg-surface border border-border rounded-2xl overflow-hidden">
            <button onClick={() => setOpen(open === i ? null : i)} className="w-full flex items-center justify-between px-5 py-4 text-left">
              <span className="text-sm font-semibold text-text">{q}</span>
              <span className="text-text3 text-xs ml-3">{open === i ? "▲" : "▼"}</span>
            </button>
            {open === i && (
              <div className="px-5 pb-4 text-sm text-text2 leading-relaxed border-t border-border pt-3">{a}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function TicketList({ t, st, onSelect }: { t: (k: string) => string; st: (s: string) => string; onSelect: (id: string) => void }) {
  const { data = [], isLoading } = useQuery({ queryKey: ["support", "tickets"], queryFn: () => contentApi.myTickets() });
  if (isLoading) return <div className="text-center text-text3 text-sm py-8">…</div>;
  if (data.length === 0) return <div className="bg-surface border border-border rounded-2xl p-8 text-center text-text3 text-sm">{t("noTickets")}</div>;
  return (
    <div className="space-y-2">
      {data.map((tk: SupportTicketOut) => (
        <button key={tk.id} onClick={() => onSelect(tk.id)} className="w-full bg-surface border border-border rounded-2xl px-5 py-4 text-left hover:bg-primary-soft/40 transition flex items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="text-sm font-semibold text-text truncate">{tk.subject}</div>
            <div className="text-xs text-text3 mt-0.5 font-mono">{tk.created_at?.slice(0, 10)}</div>
          </div>
          <span className={`shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-full border ${STATUS_CLS[tk.status]}`}>{st(tk.status)}</span>
        </button>
      ))}
    </div>
  );
}

function NewTicketForm({ t, onClose, onCreated }: { t: (k: string) => string; onClose: () => void; onCreated: (id: string) => void }) {
  const qc = useQueryClient();
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const create = useMutation({
    mutationFn: () => contentApi.createTicket({ subject, body }),
    onSuccess: (tk) => { qc.invalidateQueries({ queryKey: ["support", "tickets"] }); onCreated(tk.id); },
  });
  return (
    <div className="bg-surface border border-border rounded-2xl p-5 space-y-3">
      <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder={t("subjectPlaceholder")}
        className="w-full px-3 py-2 rounded-lg border border-border bg-bg2 text-sm outline-none focus:border-primary" />
      <textarea value={body} onChange={(e) => setBody(e.target.value)} placeholder={t("messagePlaceholder")} rows={5}
        className="w-full px-3 py-2 rounded-lg border border-border bg-bg2 text-sm outline-none focus:border-primary resize-y" />
      <div className="flex gap-2 justify-end">
        <button onClick={onClose} className="text-sm font-semibold px-4 py-2 rounded-lg border border-border hover:bg-bg2">{t("cancel")}</button>
        <button onClick={() => create.mutate()} disabled={!subject.trim() || !body.trim() || create.isPending}
          className="inline-flex items-center gap-1.5 text-sm font-semibold bg-primary text-white rounded-lg px-4 py-2 disabled:opacity-50">
          <Send size={14} /> {t("submit")}
        </button>
      </div>
    </div>
  );
}

function TicketThread({ t, st, ticketId, onBack }: { t: (k: string) => string; st: (s: string) => string; ticketId: string; onBack: () => void }) {
  const qc = useQueryClient();
  const [reply, setReply] = useState("");
  const { data: tk } = useQuery({ queryKey: ["support", "ticket", ticketId], queryFn: () => contentApi.ticket(ticketId) });
  const send = useMutation({
    mutationFn: () => contentApi.followup(ticketId, reply),
    onSuccess: () => { setReply(""); qc.invalidateQueries({ queryKey: ["support", "ticket", ticketId] }); },
  });
  if (!tk) return <div className="text-center text-text3 text-sm py-8">…</div>;
  return (
    <div className="bg-surface border border-border rounded-2xl p-5">
      <button onClick={onBack} className="inline-flex items-center gap-1 text-xs text-text3 hover:text-text mb-3"><ChevronLeft size={14} /> {t("backToList")}</button>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-base font-bold text-text">{tk.subject}</span>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${STATUS_CLS[tk.status]}`}>{st(tk.status)}</span>
      </div>
      <div className="text-[11px] text-text3 font-mono mb-4">{tk.created_at?.slice(0, 10)}</div>
      <div className="bg-bg2 rounded-xl p-3 text-sm text-text2 mb-3 whitespace-pre-wrap">{tk.body}</div>
      <div className="space-y-2 mb-4">
        {tk.replies.map((r) => (
          <div key={r.id} className={`rounded-xl p-3 text-sm text-text2 ${r.is_staff ? "bg-green-soft ml-6" : "bg-bg2 mr-6"}`}>
            <div className="text-[10px] font-bold text-text3 mb-1">{r.is_staff ? t("staff") : t("you")} · {r.created_at?.slice(0, 10)}</div>
            <div className="whitespace-pre-wrap">{r.body}</div>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <textarea value={reply} onChange={(e) => setReply(e.target.value)} placeholder={t("replyPlaceholder")} rows={2}
          className="flex-1 px-3 py-2 rounded-lg border border-border bg-bg2 text-sm outline-none focus:border-primary resize-y" />
        <button onClick={() => send.mutate()} disabled={!reply.trim() || send.isPending}
          className="inline-flex items-center gap-1.5 self-end bg-primary text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50">
          <Send size={14} /> {t("sendReply")}
        </button>
      </div>
    </div>
  );
}
