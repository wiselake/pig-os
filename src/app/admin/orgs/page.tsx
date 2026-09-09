"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, ChevronDown, Building2, Tractor, Pencil, Plus, MoveRight, X } from "lucide-react";
import { adminApi } from "@/lib/api/endpoints/admin";
import { apiError } from "@/lib/api/error";
import type { AdminOrgRow, AdminOrgFarm } from "@/types/api.types";

const ORG_TYPES = ["VENDOR", "DISTRIBUTOR", "DEALER", "INDEPENDENT"] as const;
const TYPE_META: Record<string, { key: string; cls: string }> = {
  VENDOR: { key: "orgVendor", cls: "bg-console text-white border-console" },
  DISTRIBUTOR: { key: "orgDistributor", cls: "bg-green-soft text-success border-success/30" },
  DEALER: { key: "orgDealer", cls: "bg-amber-soft text-warning border-warning/40" },
  INDEPENDENT: { key: "orgIndependent", cls: "bg-bg2 text-text2 border-border" },
};

type T = (k: string, v?: Record<string, string | number>) => string;

export default function AdminOrgsPage() {
  const t = useTranslations("admin");
  const { data, isLoading } = useQuery({ queryKey: ["admin", "orgs"], queryFn: () => adminApi.orgs() });
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<AdminOrgRow | null>(null);
  const [movingFarm, setMovingFarm] = useState<AdminOrgFarm | null>(null);

  const orgs = data ?? [];
  const childrenOf = (id: string | null) => orgs.filter((o) => o.parent_org_id === id);
  const roots = childrenOf(null);

  return (
    <div className="p-7 max-w-4xl">
      <header className="mb-5 flex items-start justify-between">
        <div>
          <h1 className="text-[22px] font-extrabold tracking-tight">{t("orgsTitle")}</h1>
          <p className="text-xs text-text3 mt-0.5">{t("orgsSubtitle")}</p>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="flex items-center gap-1.5 bg-console text-white text-xs font-semibold px-3 py-2 rounded-lg hover:opacity-90 transition"
        >
          <Plus size={14} /> {t("orgAdd")}
        </button>
      </header>

      {isLoading ? (
        <div className="py-12 text-center text-text3 text-sm">…</div>
      ) : roots.length === 0 ? (
        <div className="border border-border rounded-2xl py-14 text-center text-text3 text-sm">{t("orgsEmpty")}</div>
      ) : (
        <div className="bg-surface border border-border rounded-2xl p-2">
          {roots.map((o) => (
            <OrgNode key={o.id} org={o} childrenOf={childrenOf} depth={0} t={t}
                     onEdit={setEditing} onMoveFarm={setMovingFarm} />
          ))}
        </div>
      )}

      {createOpen && <OrgModal mode="create" orgs={orgs} t={t} onClose={() => setCreateOpen(false)} />}
      {editing && <OrgModal mode="edit" org={editing} orgs={orgs} t={t} onClose={() => setEditing(null)} />}
      {movingFarm && <MoveFarmModal farm={movingFarm} orgs={orgs} t={t} onClose={() => setMovingFarm(null)} />}
    </div>
  );
}

function OrgNode({
  org, childrenOf, depth, t, onEdit, onMoveFarm,
}: {
  org: AdminOrgRow;
  childrenOf: (id: string | null) => AdminOrgRow[];
  depth: number;
  t: T;
  onEdit: (o: AdminOrgRow) => void;
  onMoveFarm: (f: AdminOrgFarm) => void;
}) {
  const [open, setOpen] = useState(depth === 0);
  const [showFarms, setShowFarms] = useState(false);
  const kids = childrenOf(org.id);
  const meta = TYPE_META[org.org_type] ?? TYPE_META.INDEPENDENT;
  const expandable = kids.length > 0 || org.farm_count > 0;

  const { data: farms } = useQuery({
    queryKey: ["admin", "orgFarms", org.id],
    queryFn: () => adminApi.orgFarms(org.id),
    enabled: showFarms,
  });

  return (
    <div>
      <div className="flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-bg2 transition group" style={{ paddingLeft: depth * 20 + 8 }}>
        <button onClick={() => setOpen((v) => !v)} className={`w-5 h-5 flex items-center justify-center text-text3 ${expandable ? "" : "invisible"}`}>
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        <Building2 size={14} className="text-text3 shrink-0" />
        <span className="font-semibold text-text text-sm">{org.name}</span>
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${meta.cls}`}>{t(meta.key)}</span>
        <button
          onClick={() => onEdit(org)}
          title={t("orgEdit")}
          className="opacity-0 group-hover:opacity-100 p-1 rounded text-text3 hover:text-primary hover:bg-primary/5 transition"
        >
          <Pencil size={12} />
        </button>
        <span className="text-[11px] text-text3 font-mono ml-auto">
          {t("orgFarmCount", { n: org.farm_count })} · {t("orgUserCount", { n: org.user_count })}
        </span>
      </div>

      {open && (
        <div>
          {kids.map((k) => (
            <OrgNode key={k.id} org={k} childrenOf={childrenOf} depth={depth + 1} t={t} onEdit={onEdit} onMoveFarm={onMoveFarm} />
          ))}
          {org.farm_count > 0 && (
            <div style={{ paddingLeft: (depth + 1) * 20 + 8 }}>
              <button onClick={() => setShowFarms((v) => !v)} className="flex items-center gap-1.5 px-2 py-1.5 text-xs text-primary font-semibold hover:underline">
                <Tractor size={12} /> {showFarms ? t("orgHideFarms") : t("orgShowFarms", { n: org.farm_count })}
              </button>
              {showFarms && (farms ?? []).map((f: AdminOrgFarm) => (
                <div key={f.id} className="flex items-center gap-2 px-2 py-1.5 text-xs text-text2 group/farm" style={{ paddingLeft: 24 }}>
                  <Tractor size={12} className="text-text3" />
                  <span className="font-medium">{f.name}</span>
                  <span className="text-text3 font-mono">{f.farm_code}</span>
                  {!f.active && <span className="text-[10px] text-text3">({t("inactive")})</span>}
                  <button
                    onClick={() => onMoveFarm(f)}
                    title={t("farmMove")}
                    className="opacity-0 group-hover/farm:opacity-100 ml-1 inline-flex items-center gap-0.5 text-[11px] text-text3 hover:text-primary transition"
                  >
                    <MoveRight size={12} /> {t("farmMove")}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ModalShell({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="bg-background border border-border rounded-2xl w-full max-w-sm p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold">{title}</h2>
          <button onClick={onClose} className="p-1 rounded text-text3 hover:bg-border transition"><X size={16} /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

const inputCls = "w-full border border-border rounded-lg px-2.5 py-1.5 text-sm bg-surface focus:outline-none focus:ring-1 focus:ring-primary";

function OrgModal({
  mode, org, orgs, t, onClose,
}: {
  mode: "create" | "edit";
  org?: AdminOrgRow;
  orgs: AdminOrgRow[];
  t: T;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [name, setName] = useState(org?.name ?? "");
  const [orgType, setOrgType] = useState(org?.org_type ?? "DISTRIBUTOR");
  const [parentId, setParentId] = useState<string>(org?.parent_org_id ?? "");
  const [country, setCountry] = useState(org?.country ?? "KR");
  const [error, setError] = useState<string | null>(null);

  // 부모 후보: 자기 자신 제외(하위 사이클은 백엔드가 추가 차단).
  const parentOptions = orgs.filter((o) => o.id !== org?.id);

  const mut = useMutation({
    mutationFn: () =>
      mode === "create"
        ? adminApi.createOrg({ name, org_type: orgType, parent_org_id: parentId || null, country })
        : adminApi.updateOrg(org!.id, { name, org_type: orgType, parent_org_id: parentId || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "orgs"] }); onClose(); },
    onError: (e) => setError(apiError(e, t("orgSaveError"))),
  });

  const valid = name.trim().length > 0 && (mode === "edit" || country.trim().length === 2);

  return (
    <ModalShell title={mode === "create" ? t("orgCreateTitle") : t("orgEditTitle")} onClose={onClose}>
      <div className="space-y-3">
        <label className="block">
          <span className="text-[11px] font-medium text-text3 mb-1 block">{t("orgName")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} />
        </label>
        <label className="block">
          <span className="text-[11px] font-medium text-text3 mb-1 block">{t("orgTypeLabel")}</span>
          <select value={orgType} onChange={(e) => setOrgType(e.target.value)} className={inputCls}>
            {ORG_TYPES.map((ot) => <option key={ot} value={ot}>{t(TYPE_META[ot].key)}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="text-[11px] font-medium text-text3 mb-1 block">{t("orgParent")}</span>
          <select value={parentId} onChange={(e) => setParentId(e.target.value)} className={inputCls}>
            <option value="">{t("orgParentNone")}</option>
            {parentOptions.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
          </select>
        </label>
        {mode === "create" && (
          <label className="block">
            <span className="text-[11px] font-medium text-text3 mb-1 block">{t("orgCountry")}</span>
            <input value={country} maxLength={2} onChange={(e) => setCountry(e.target.value.toUpperCase())} className={inputCls} />
          </label>
        )}
      </div>
      {error && <p className="text-xs text-danger mt-3">{error}</p>}
      <div className="flex gap-2 mt-5">
        <button onClick={onClose} className="flex-1 text-sm border border-border rounded-lg py-2 hover:bg-border transition">{t("orgCancel")}</button>
        <button onClick={() => mut.mutate()} disabled={!valid || mut.isPending}
                className="flex-1 text-sm font-medium text-white bg-console rounded-lg py-2 hover:opacity-90 transition disabled:opacity-50">
          {t("orgSave")}
        </button>
      </div>
    </ModalShell>
  );
}

function MoveFarmModal({
  farm, orgs, t, onClose,
}: {
  farm: AdminOrgFarm;
  orgs: AdminOrgRow[];
  t: T;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [target, setTarget] = useState<string>(orgs[0]?.id ?? "");
  const [error, setError] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: () => adminApi.reassignFarm(farm.id, target),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "orgs"] });
      qc.invalidateQueries({ queryKey: ["admin", "orgFarms"] });
      onClose();
    },
    onError: (e) => setError(apiError(e, t("orgSaveError"))),
  });

  return (
    <ModalShell title={t("farmMoveTitle")} onClose={onClose}>
      <p className="text-xs text-text3 mb-3">{farm.name} · {farm.farm_code}</p>
      <label className="block">
        <span className="text-[11px] font-medium text-text3 mb-1 block">{t("farmMoveTarget")}</span>
        <select value={target} onChange={(e) => setTarget(e.target.value)} className={inputCls}>
          {orgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
        </select>
      </label>
      {error && <p className="text-xs text-danger mt-3">{error}</p>}
      <div className="flex gap-2 mt-5">
        <button onClick={onClose} className="flex-1 text-sm border border-border rounded-lg py-2 hover:bg-border transition">{t("orgCancel")}</button>
        <button onClick={() => mut.mutate()} disabled={!target || mut.isPending}
                className="flex-1 text-sm font-medium text-white bg-console rounded-lg py-2 hover:opacity-90 transition disabled:opacity-50">
          {t("orgSave")}
        </button>
      </div>
    </ModalShell>
  );
}
