"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, Pin, X } from "lucide-react";
import { adminApi, type AnnouncementInput } from "@/lib/api/endpoints/admin";
import type { AnnouncementOut } from "@/types/api.types";

const CATEGORIES = ["GENERAL", "UPDATE", "MAINTENANCE"] as const;
const CAT_CLS: Record<string, string> = {
  GENERAL: "bg-green-soft text-success border-success/30",
  UPDATE: "bg-amber-soft text-warning border-warning/40",
  MAINTENANCE: "bg-red-soft text-danger border-danger/40",
};

export default function AdminAnnouncementsPage() {
  const t = useTranslations("admin");
  const qc = useQueryClient();
  const [editing, setEditing] = useState<AnnouncementOut | null>(null);
  const [creating, setCreating] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "announcements"],
    queryFn: () => adminApi.announcements(),
  });

  const del = useMutation({
    mutationFn: (id: string) => adminApi.deleteAnnouncement(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "announcements"] }),
  });

  const rows = data ?? [];

  return (
    <div className="p-7 max-w-4xl">
      <header className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-[22px] font-extrabold tracking-tight">{t("annTitle")}</h1>
          <p className="text-xs text-text3 mt-0.5">{t("annSubtitle")}</p>
        </div>
        <button onClick={() => setCreating(true)} className="inline-flex items-center gap-1.5 bg-primary text-white px-4 py-2 rounded-lg text-sm font-semibold hover:opacity-90">
          <Plus size={14} /> {t("annNew")}
        </button>
      </header>

      {isLoading ? (
        <div className="py-12 text-center text-text3 text-sm">…</div>
      ) : rows.length === 0 ? (
        <div className="border border-border rounded-2xl py-14 text-center text-text3 text-sm">{t("annEmpty")}</div>
      ) : (
        <div className="space-y-2.5">
          {rows.map((a) => (
            <div key={a.id} className="bg-surface border border-border rounded-2xl p-4 flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  {a.pinned && <Pin size={12} className="text-primary" />}
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${CAT_CLS[a.category]}`}>{a.category}</span>
                  {!a.published && <span className="text-[10px] text-text3">· {t("annHidden")}</span>}
                  <span className="text-[11px] text-text3 font-mono ml-auto">{a.created_at?.slice(0, 10)}</span>
                </div>
                <div className="text-sm font-bold text-text">{a.title}</div>
                <p className="text-xs text-text2 leading-relaxed mt-1 line-clamp-2">{a.body}</p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button onClick={() => setEditing(a)} className="p-1.5 rounded-md text-text3 hover:text-text hover:bg-bg2"><Pencil size={14} /></button>
                <button onClick={() => { if (confirm(t("annDeleteConfirm"))) del.mutate(a.id); }} className="p-1.5 rounded-md text-text3 hover:text-danger hover:bg-red-soft"><Trash2 size={14} /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      {(creating || editing) && (
        <AnnouncementModal
          t={t}
          existing={editing}
          onClose={() => { setCreating(false); setEditing(null); }}
          onSaved={() => { setCreating(false); setEditing(null); qc.invalidateQueries({ queryKey: ["admin", "announcements"] }); }}
        />
      )}
    </div>
  );
}

function AnnouncementModal({
  t, existing, onClose, onSaved,
}: {
  t: (k: string) => string;
  existing: AnnouncementOut | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<AnnouncementInput>({
    title: existing?.title ?? "",
    body: existing?.body ?? "",
    category: existing?.category ?? "GENERAL",
    pinned: existing?.pinned ?? false,
    published: existing?.published ?? true,
  });

  const save = useMutation({
    mutationFn: () => existing ? adminApi.updateAnnouncement(existing.id, form) : adminApi.createAnnouncement(form),
    onSuccess: onSaved,
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-surface rounded-2xl p-6 max-w-lg w-full shadow-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold">{existing ? t("annEdit") : t("annNew")}</h2>
          <button onClick={onClose} className="p-1 rounded-md text-text3 hover:bg-bg2"><X size={16} /></button>
        </div>
        <div className="space-y-3">
          <input value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            placeholder={t("annFieldTitle")} className="w-full px-3 py-2 rounded-lg border border-border bg-bg2 text-sm outline-none focus:border-primary" />
          <textarea value={form.body} onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
            placeholder={t("annFieldBody")} rows={5} className="w-full px-3 py-2 rounded-lg border border-border bg-bg2 text-sm outline-none focus:border-primary resize-y" />
          <div className="flex gap-1.5">
            {CATEGORIES.map((c) => (
              <button key={c} onClick={() => setForm((f) => ({ ...f, category: c }))}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${form.category === c ? "bg-console text-white border-console" : "bg-surface border-border text-text2"}`}>{c}</button>
            ))}
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm text-text2"><input type="checkbox" checked={form.pinned} onChange={(e) => setForm((f) => ({ ...f, pinned: e.target.checked }))} /> {t("annPinned")}</label>
            <label className="flex items-center gap-2 text-sm text-text2"><input type="checkbox" checked={form.published} onChange={(e) => setForm((f) => ({ ...f, published: e.target.checked }))} /> {t("annPublished")}</label>
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="flex-1 border border-border rounded-lg py-2 text-sm">{t("cancel") ?? "Cancel"}</button>
          <button onClick={() => save.mutate()} disabled={!form.title.trim() || !form.body.trim() || save.isPending}
            className="flex-1 bg-primary text-white rounded-lg py-2 text-sm font-semibold disabled:opacity-50">{t("annSave")}</button>
        </div>
      </div>
    </div>
  );
}
