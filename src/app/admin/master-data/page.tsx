"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, X, Check } from "lucide-react";
import { adminApi } from "@/lib/api/endpoints/admin";
import { apiError } from "@/lib/api/error";
import type { ReactNode } from "react";

// 운영자 코드데이터 관리 (G4). admin은 ko 전용 운영자 콘솔 → 라벨 한글 직접 사용.
type Col = { key: string; label: string; type: "text" | "num" | "bool" | "textarea"; pk?: boolean; required?: boolean };
type Kind = { id: string; label: string; pk: string; cols: Col[] };

const KINDS: Kind[] = [
  {
    id: "diseases", label: "질병코드", pk: "disease_code",
    cols: [
      { key: "disease_code", label: "코드", type: "text", pk: true, required: true },
      { key: "label_en", label: "명칭(EN)", type: "text", required: true },
      { key: "label_ko", label: "명칭(KO)", type: "text" },
      { key: "category", label: "분류", type: "text", required: true },
      { key: "woah_code", label: "WOAH", type: "text" },
      { key: "notifiable", label: "신고대상", type: "bool" },
      { key: "typical_mortality_pct", label: "전형폐사율%", type: "num" },
      { key: "typical_treatment", label: "치료", type: "textarea" },
    ],
  },
  {
    id: "vaccines", label: "백신", pk: "vaccine_code",
    cols: [
      { key: "vaccine_code", label: "코드", type: "text", pk: true, required: true },
      { key: "disease_target", label: "대상질병", type: "text" },
      { key: "vaccine_type", label: "유형", type: "text" },
      { key: "product_name", label: "제품명", type: "text" },
      { key: "manufacturer", label: "제조사", type: "text" },
      { key: "route", label: "투여경로", type: "text" },
      { key: "withdrawal_days", label: "휴약일", type: "num" },
      { key: "notes", label: "비고", type: "textarea" },
    ],
  },
  {
    id: "medications", label: "약품", pk: "active_substance",
    cols: [
      { key: "active_substance", label: "성분", type: "text", pk: true, required: true },
      { key: "atcvet_code", label: "ATCvet", type: "text" },
      { key: "antibiotic_class", label: "항생제계열", type: "text" },
      { key: "ddda_mg_per_kg", label: "DDDA", type: "num" },
      { key: "standard_dose_mg_kg", label: "표준용량", type: "num" },
      { key: "withdrawal_days_meat", label: "휴약일(육)", type: "num" },
      { key: "route", label: "투여경로", type: "text" },
      { key: "vfd_required_us", label: "US-VFD", type: "bool" },
      { key: "eu_restricted", label: "EU제한", type: "bool" },
      { key: "notes", label: "비고", type: "textarea" },
    ],
  },
  {
    id: "event-definitions", label: "이벤트정의", pk: "event_code",
    cols: [
      { key: "event_code", label: "코드", type: "text", pk: true, required: true },
      { key: "category", label: "분류", type: "text", required: true },
      { key: "label_en", label: "명칭(EN)", type: "text", required: true },
      { key: "label_ko", label: "명칭(KO)", type: "text" },
      { key: "regional_applicability", label: "지역", type: "text" },
      { key: "phase", label: "단계", type: "text" },
      { key: "sort_order", label: "순서", type: "num" },
    ],
  },
];

type Row = Record<string, unknown>;

export default function AdminMasterDataPage() {
  const [kindId, setKindId] = useState(KINDS[0].id);
  const [editing, setEditing] = useState<Row | "new" | null>(null);
  const [page, setPage] = useState(1);
  const kind = KINDS.find((k) => k.id === kindId)!;
  const qc = useQueryClient();
  const PAGE_SIZE = 25;

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["admin", "master", kindId],
    queryFn: () => adminApi.masterList(kindId),
  });

  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paged = rows.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const del = useMutation({
    mutationFn: (pk: string) => adminApi.masterDelete(kindId, pk),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "master", kindId] }),
  });

  return (
    <div className="p-7 max-w-6xl">
      <header className="mb-5 flex items-start justify-between">
        <div>
          <h1 className="text-[22px] font-extrabold tracking-tight">코드데이터 관리</h1>
          <p className="text-xs text-text3 mt-0.5">질병·백신·약품·이벤트정의 마스터 코드</p>
        </div>
        <button onClick={() => setEditing("new")}
          className="flex items-center gap-1.5 bg-console text-white text-xs font-semibold px-3 py-2 rounded-lg hover:opacity-90">
          <Plus size={14} /> 추가
        </button>
      </header>

      <div className="flex gap-1.5 mb-5 border-b border-border">
        {KINDS.map((k) => (
          <button key={k.id} onClick={() => { setKindId(k.id); setPage(1); }}
            className={`px-4 py-2 text-sm font-semibold -mb-px border-b-2 transition ${
              kindId === k.id ? "border-primary text-primary" : "border-transparent text-muted hover:text-text"}`}>
            {k.label}
          </button>
        ))}
      </div>

      <div className="bg-surface border border-border rounded-2xl overflow-x-auto">
        {isLoading ? (
          <div className="p-12 text-center text-text3 text-sm">…</div>
        ) : rows.length === 0 ? (
          <div className="p-12 text-center text-text3 text-sm">데이터 없음 — &quot;추가&quot;로 등록하세요</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-bg2 text-text3 text-[11px] uppercase tracking-wide">
                {kind.cols.map((c) => <th key={c.key} className="text-left px-3 py-2 font-bold">{c.label}</th>)}
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {paged.map((r) => (
                <tr key={String(r[kind.pk])} className="border-t border-border">
                  {kind.cols.map((c) => (
                    <td key={c.key} className="px-3 py-2 text-text2">{fmt(r[c.key])}</td>
                  ))}
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    <button onClick={() => setEditing(r)} title="수정"
                      className="p-1 rounded text-text3 hover:text-primary hover:bg-primary/5"><Pencil size={13} /></button>
                    <button onClick={() => { if (confirm(`삭제: ${r[kind.pk]} ?`)) del.mutate(String(r[kind.pk])); }}
                      title="삭제" className="p-1 rounded text-text3 hover:text-danger hover:bg-red-soft ml-1"><Trash2 size={13} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!isLoading && totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border text-xs">
            <span className="text-text3 font-mono">
              {(safePage - 1) * PAGE_SIZE + 1}–{Math.min(safePage * PAGE_SIZE, rows.length)} / {rows.length}
            </span>
            <div className="flex items-center gap-1.5">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={safePage <= 1}
                className="px-3 py-1.5 rounded-lg border border-border bg-surface font-semibold disabled:opacity-40 hover:bg-bg2 transition">이전</button>
              <span className="font-mono text-text3 px-1">{safePage} / {totalPages}</span>
              <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={safePage >= totalPages}
                className="px-3 py-1.5 rounded-lg border border-border bg-surface font-semibold disabled:opacity-40 hover:bg-bg2 transition">다음</button>
            </div>
          </div>
        )}
      </div>

      {editing && (
        <EditModal kind={kind} row={editing === "new" ? null : editing} onClose={() => setEditing(null)} />
      )}
    </div>
  );
}

function fmt(v: unknown): ReactNode {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") {
    return v ? <Check size={14} className="text-success" strokeWidth={3} aria-hidden /> : "—";
  }
  if (Array.isArray(v)) return v.join(", ");
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function EditModal({ kind, row, onClose }: { kind: Kind; row: Row | null; onClose: () => void }) {
  const qc = useQueryClient();
  const isNew = row === null;
  const [form, setForm] = useState<Record<string, unknown>>(() => {
    const init: Record<string, unknown> = {};
    for (const c of kind.cols) init[c.key] = row ? row[c.key] ?? "" : (c.type === "bool" ? false : "");
    return init;
  });
  const [error, setError] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: () => {
      // 폼 값을 타입에 맞춰 정제(빈 텍스트→null, 숫자 변환). PK는 수정 시 제외.
      const body: Record<string, unknown> = {};
      for (const c of kind.cols) {
        if (!isNew && c.pk) continue;
        const v = form[c.key];
        if (c.type === "num") body[c.key] = v === "" || v === null ? null : Number(v);
        else if (c.type === "bool") body[c.key] = !!v;
        else body[c.key] = v === "" ? null : v;
      }
      return isNew
        ? adminApi.masterCreate(kind.id, body)
        : adminApi.masterUpdate(kind.id, String(row![kind.pk]), body);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "master", kind.id] }); onClose(); },
    onError: (e) => setError(apiError(e, "저장 실패")),
  });

  const inputCls = "w-full border border-border rounded-lg px-2.5 py-1.5 text-sm bg-surface focus:outline-none focus:ring-1 focus:ring-primary";
  const valid = kind.cols.every((c) => !c.required || String(form[c.key] ?? "").trim() !== "");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="bg-background border border-border rounded-2xl w-full max-w-md p-5 shadow-xl max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold">{isNew ? `${kind.label} 추가` : `${kind.label} 수정`}</h2>
          <button onClick={onClose} className="p-1 rounded text-text3 hover:bg-border"><X size={16} /></button>
        </div>
        <div className="space-y-3">
          {kind.cols.map((c) => (
            <label key={c.key} className="block">
              <span className="text-[11px] font-medium text-text3 mb-1 block">
                {c.label}{c.required && " *"}{c.pk && !isNew && " (수정불가)"}
              </span>
              {c.type === "bool" ? (
                <input type="checkbox" checked={!!form[c.key]}
                  onChange={(e) => setForm((f) => ({ ...f, [c.key]: e.target.checked }))} />
              ) : c.type === "textarea" ? (
                <textarea value={String(form[c.key] ?? "")} rows={2}
                  onChange={(e) => setForm((f) => ({ ...f, [c.key]: e.target.value }))} className={inputCls} />
              ) : (
                <input type={c.type === "num" ? "number" : "text"} value={String(form[c.key] ?? "")}
                  disabled={c.pk && !isNew}
                  onChange={(e) => setForm((f) => ({ ...f, [c.key]: e.target.value }))}
                  className={`${inputCls} ${c.pk && !isNew ? "opacity-60" : ""}`} />
              )}
            </label>
          ))}
        </div>
        {error && <p className="text-xs text-danger mt-3">{error}</p>}
        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="flex-1 text-sm border border-border rounded-lg py-2 hover:bg-border">취소</button>
          <button onClick={() => mut.mutate()} disabled={!valid || mut.isPending}
            className="flex-1 text-sm font-medium text-white bg-console rounded-lg py-2 hover:opacity-90 disabled:opacity-50">저장</button>
        </div>
      </div>
    </div>
  );
}
