"use client";

import { localToday } from "@/lib/date";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Pencil, LogOut, X, PiggyBank, ArrowRight, Search, AlertTriangle } from "lucide-react";
import { sowsApi } from "@/lib/api/endpoints/sows";
import { track } from "@/lib/analytics";
import { alertsApi } from "@/lib/api/endpoints/alerts";
import { reportsApi } from "@/lib/api/endpoints/reports";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import { canEntry, canManage } from "@/lib/auth/permissions";
import { useActiveRole } from "@/lib/auth/useActiveRole";
import { apiError } from "@/lib/api/error";
import { ALERT_META, SEVERITY_PILL } from "@/lib/alerts/meta";
import type { OverdueType } from "@/types/api.types";
import { sowEntrySchema, firstError } from "@/lib/validation/eventSchemas";
import type {
  Sow,
  SowStatus,
  SowEntryType,
  CreateSowRequest,
  UpdateSowRequest,
  SowCullRequest,
} from "@/types/api.types";

// SCREEN_MENU_SPEC: All / Gilt / Open / Pregnant / Lactating / Accident / Culled
// 라벨은 sowStatus i18n 키로 해석, tabAll은 sows.tabAll
const STATUS_TABS: (SowStatus | "ALL")[] = ["ALL", "GILT", "OPEN", "PREGNANT", "LACTATING", "ACCIDENT", "CULLED"];

// 활성(편집 가능) 상태 — 종료상태(CULLED/DEAD/SOLD/TRANSFER)는 도폐사 모달 전용
const ACTIVE_SOW_STATUSES = ["GILT", "OPEN", "PREGNANT", "LACTATING", "ACCIDENT"] as const;
type ActiveSowStatus = (typeof ACTIVE_SOW_STATUSES)[number];

// 상태 → 배지 색상 (Forest Green 토큰만 사용 — raw 팔레트/블루 금지. 라벨은 sowStatus 키)
const STATUS_CLS: Record<string, string> = {
  GILT:      "bg-green-soft text-brand-2",
  OPEN:      "bg-bg2 text-text2",
  PREGNANT:  "bg-green-soft text-success",
  LACTATING: "bg-green-soft text-success",
  ACCIDENT:  "bg-amber-soft text-warning",
  CULLED:    "bg-red-soft text-danger",
  DEAD:      "bg-red-soft text-danger",
  SOLD:      "bg-green-soft text-success",
  TRANSFER:  "bg-amber-soft text-warning",
};

export default function SowsPage() {
  const t = useTranslations("sows");
  const tStatus = useTranslations("sowStatus");
  const farmId = useAuthStore((s) => s.activeFarmId);
  const role = useActiveRole();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<SowStatus | "ALL">("ALL");
  const [search, setSearch] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [editTarget, setEditTarget] = useState<Sow | null>(null);
  const [cullTarget, setCullTarget] = useState<Sow | null>(null);
  const [page, setPage] = useState(1);

  const params = {
    status: statusFilter === "ALL" ? undefined : statusFilter,
    page,
    per_page: 50,
  };

  const { data, isLoading, isError } = useQuery({
    queryKey: queryKeys.sows.list(farmId ?? "", params),
    queryFn: () => sowsApi.list(farmId!, params),
    enabled: !!farmId,
  });

  // 위험 신호(관리대상) 연동 — sow_id → overdue type. 실제 룰엔진 결과만 사용.
  const { data: overdue } = useQuery({
    queryKey: queryKeys.alerts.overdue(farmId ?? ""),
    queryFn: () => alertsApi.overdue(farmId!),
    enabled: !!farmId,
  });
  // 돈군 구성(상태별 두수) — 필터칩에 병기해 한눈에. 활성 상태만 집계(sow-status 리포트 재사용).
  const { data: statusCounts } = useQuery({
    queryKey: ["reports", "sow-status-counts", farmId ?? ""],
    queryFn: () => reportsApi.sowStatus(farmId!),
    enabled: !!farmId,
  });
  const byStatus = statusCounts?.by_status ?? {};
  const activeTotal = statusCounts?.total ?? 0;
  const chipCount = (tab: SowStatus | "ALL"): number | null =>
    tab === "ALL" ? activeTotal : (byStatus[tab] ?? null);

  const riskBySow = new Map<string, OverdueType>();
  for (const o of overdue?.items ?? []) if (!riskBySow.has(o.sow_id)) riskBySow.set(o.sow_id, o.type);

  const sows = data?.items ?? [];
  const meta = data?.meta;

  const filtered = search
    ? sows.filter((s) => s.ear_tag.toLowerCase().includes(search.toLowerCase()))
    : sows;

  if (!farmId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-text3">{t("selectFarm")}</p>
      </div>
    );
  }

  return (
    <div className="p-7">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-[22px] font-extrabold tracking-tight">{t("title")}</h1>
            <p className="text-xs text-text3 mt-0.5">
              {meta ? t("totalCount", { n: meta.total }) : t("loading")}
            </p>
          </div>
          {canEntry(role) && (
            <button
              onClick={() => setShowAddModal(true)}
              data-testid="sows-add-btn"
              className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-primary/90 transition"
            >
              {t("addSow")}
            </button>
          )}
        </div>

        {/* Search + filter chips */}
        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <div className="relative w-60">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text3" />
            <input
              type="text"
              placeholder={t("searchPlaceholder")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-surface text-sm text-text1 outline-none focus:border-primary"
            />
          </div>
          <div className="flex gap-1.5 flex-wrap">
            {STATUS_TABS.map((tab) => {
              const n = chipCount(tab);
              const active = statusFilter === tab;
              return (
                <button
                  key={tab}
                  onClick={() => { setStatusFilter(tab); setPage(1); }}
                  className={`px-3.5 py-1.5 rounded-full text-[13px] font-semibold border transition inline-flex items-center gap-1.5 ${
                    active
                      ? "bg-console text-white border-console"
                      : "bg-surface border-border text-text2 hover:bg-bg2"
                  }`}
                >
                  {tab === "ALL" ? t("tabAll") : tStatus(tab)}
                  {n != null && n > 0 && (
                    <span className={`font-mono text-[11px] tabular-nums ${active ? "text-white/80" : "text-text3"}`}>{n}</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Table */}
        <div className="bg-surface border border-border rounded-2xl overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center text-text3 text-sm">{t("loading")}</div>
          ) : isError ? (
            <div className="p-12 text-center text-danger text-sm">{t("loadError")}</div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center text-center gap-3 py-16 px-6">
              <div className="w-14 h-14 rounded-2xl bg-bg2 border border-border flex items-center justify-center text-text3">
                <PiggyBank size={28} />
              </div>
              <p className="text-sm font-bold text-text1">
                {search ? t("emptyNoResult", { q: search }) : t("emptyNoSows")}
              </p>
              {!search && (
                <>
                  <p className="text-xs text-text3 max-w-xs">{t("emptyGuide")}</p>
                  {canEntry(role) && (
                    <button
                      onClick={() => setShowAddModal(true)}
                      className="inline-flex items-center gap-1.5 bg-primary text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-primary/90 transition mt-1"
                    >
                      {t("addSow")} <ArrowRight size={14} />
                    </button>
                  )}
                </>
              )}
            </div>
          ) : (
            <>
            {/* 데스크톱: 테이블 / 모바일(md 미만): 카드 — 현장 폰 가로스크롤 제거 */}
            <table className="w-full text-sm hidden md:table">
              <thead>
                <tr className="border-b border-border bg-background text-text3 text-xs">
                  <th className="text-left px-4 py-3 font-medium">{t("thEarTag")}</th>
                  <th className="text-left px-4 py-3 font-medium">{t("thStatus")}</th>
                  <th className="text-right px-4 py-3 font-medium">{t("thParity")}</th>
                  <th className="text-left px-4 py-3 font-medium">{t("thBreed")}</th>
                  <th className="text-left px-4 py-3 font-medium">{t("thEntryDate")}</th>
                  <th className="text-left px-4 py-3 font-medium">{t("thRisk")}</th>
                  <th className="text-right px-4 py-3 font-medium">{t("thActions")}</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((sow, i) => {
                  const cls = STATUS_CLS[sow.status] ?? "bg-gray-100 text-gray-500";
                  return (
                    <tr
                      key={sow.id}
                      onClick={() => router.push(`/sows/${sow.id}`)}
                      className={`border-b border-border hover:bg-background/50 transition cursor-pointer ${
                        i % 2 === 0 ? "" : "bg-background/20"
                      }`}
                    >
                      <td className="px-4 py-3 font-mono font-bold text-text1">{sow.ear_tag}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${cls}`}>
                          {tStatus(sow.status)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono">{t("parityUnit", { n: sow.parity })}</td>
                      <td className="px-4 py-3 text-text2">{sow.breed ?? "-"}</td>
                      <td className="px-4 py-3 text-text3 font-mono text-xs">
                        {sow.entry_date.slice(0, 10)}
                      </td>
                      <td className="px-4 py-3">
                        {(() => {
                          const rt = riskBySow.get(sow.id);
                          if (!rt) return <span className="text-text3 text-xs">—</span>;
                          const m = ALERT_META[rt];
                          return (
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${SEVERITY_PILL[m.severity]}`}>
                              <AlertTriangle size={12} />
                              {t(`riskShort.${rt}`)}
                            </span>
                          );
                        })()}
                      </td>
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1">
                          {/* 수정=입력권한(canEntry, 백엔드 PATCH _ENTRY_ROLES) */}
                          {canEntry(role) && (
                            <button
                              onClick={() => setEditTarget(sow)}
                              title={t("editTooltip")}
                              className="p-1.5 rounded-md text-text3 hover:text-text hover:bg-bg2 transition"
                            >
                              <Pencil size={12} />
                            </button>
                          )}
                          {/* 도폐사=관리권한(canManage, 백엔드 cull _MANAGE_ROLES — WORKER 제외) */}
                          {canManage(role) && sow.status !== "CULLED" && sow.status !== "DEAD" && (
                            <button
                              onClick={() => setCullTarget(sow)}
                              title={t("removalTooltip")}
                              className="p-1.5 rounded-md text-text3 hover:text-danger hover:bg-red-soft transition"
                            >
                              <LogOut size={12} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* 모바일 카드 뷰 (md 미만) — 데스크톱 테이블과 동일 데이터·동작 */}
            <ul className="md:hidden divide-y divide-border">
              {filtered.map((sow) => {
                const cls = STATUS_CLS[sow.status] ?? "bg-gray-100 text-gray-500";
                const rt = riskBySow.get(sow.id);
                const m = rt ? ALERT_META[rt] : null;
                return (
                  <li
                    key={sow.id}
                    onClick={() => router.push(`/sows/${sow.id}`)}
                    className="p-4 flex flex-col gap-2 cursor-pointer hover:bg-background/50 transition"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono font-bold text-text1">{sow.ear_tag}</span>
                      <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${cls}`}>
                        {tStatus(sow.status)}
                      </span>
                    </div>
                    <div className="flex items-center flex-wrap gap-x-4 gap-y-1 text-xs text-text2">
                      <span>{t("thParity")}: <span className="font-mono text-text1">{t("parityUnit", { n: sow.parity })}</span></span>
                      <span>{t("thBreed")}: <span className="text-text1">{sow.breed ?? "-"}</span></span>
                      <span className="font-mono text-text3">{sow.entry_date.slice(0, 10)}</span>
                      {m && (
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${SEVERITY_PILL[m.severity]}`}>
                          <AlertTriangle size={12} />
                          {t(`riskShort.${rt}`)}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 pt-1" onClick={(e) => e.stopPropagation()}>
                      {canEntry(role) && (
                        <button
                          onClick={() => setEditTarget(sow)}
                          className="flex items-center gap-1 text-xs px-2 py-1 rounded-md text-text2 hover:text-text hover:bg-bg2 transition"
                        >
                          <Pencil size={12} /> {t("editTooltip")}
                        </button>
                      )}
                      {canManage(role) && sow.status !== "CULLED" && sow.status !== "DEAD" && (
                        <button
                          onClick={() => setCullTarget(sow)}
                          className="flex items-center gap-1 text-xs px-2 py-1 rounded-md text-text2 hover:text-danger hover:bg-red-soft transition"
                        >
                          <LogOut size={12} /> {t("removalTooltip")}
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
            </>
          )}
        </div>

        {/* Pagination */}
        {meta && meta.pages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-4">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded-lg border border-border text-xs disabled:opacity-40"
            >
              {t("prev")}
            </button>
            <span className="text-xs text-text3">{page} / {meta.pages}</span>
            <button
              onClick={() => setPage((p) => Math.min(meta.pages, p + 1))}
              disabled={page === meta.pages}
              className="px-3 py-1.5 rounded-lg border border-border text-xs disabled:opacity-40"
            >
              {t("next")}
            </button>
          </div>
        )}

      {/* Add Sow Modal */}
      {showAddModal && (
        <AddSowModal
          farmId={farmId}
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            setShowAddModal(false);
            queryClient.invalidateQueries({ queryKey: queryKeys.sows.all(farmId) });
          }}
        />
      )}

      {/* Edit Sow Modal */}
      {editTarget && (
        <EditSowModal
          farmId={farmId}
          sow={editTarget}
          onClose={() => setEditTarget(null)}
          onSuccess={() => {
            setEditTarget(null);
            queryClient.invalidateQueries({ queryKey: queryKeys.sows.all(farmId) });
          }}
        />
      )}

      {/* Cull Sow Modal */}
      {cullTarget && (
        <CullSowModal
          farmId={farmId}
          sow={cullTarget}
          onClose={() => setCullTarget(null)}
          onSuccess={() => {
            setCullTarget(null);
            queryClient.invalidateQueries({ queryKey: queryKeys.sows.all(farmId) });
          }}
        />
      )}
    </div>
  );
}

function EditSowModal({
  farmId,
  sow,
  onClose,
  onSuccess,
}: {
  farmId: string;
  sow: Sow;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState<UpdateSowRequest>({
    ear_tag: sow.ear_tag,
    breed: sow.breed ?? "",
    breed_company: sow.breed_company ?? "",
    genetics_id: sow.genetics_id ?? "",
    rfid_tag: sow.rfid_tag ?? "",
    parity: sow.parity,
    entry_date: sow.entry_date ? sow.entry_date.slice(0, 10) : undefined,
    entry_type: (sow.entry_type as UpdateSowRequest["entry_type"]) ?? undefined,
    status: ACTIVE_SOW_STATUSES.includes(sow.status as ActiveSowStatus)
      ? (sow.status as UpdateSowRequest["status"])
      : undefined,
  });
  const [error, setError] = useState<string | null>(null);
  const t = useTranslations("sows");
  const tStatus = useTranslations("sowStatus");

  const isTerminal = !ACTIVE_SOW_STATUSES.includes(sow.status as ActiveSowStatus);

  const mutation = useMutation({
    mutationFn: () =>
      sowsApi.update(farmId, sow.id, {
        ear_tag: form.ear_tag,
        breed: form.breed || undefined,
        breed_company: form.breed_company || undefined,
        genetics_id: form.genetics_id || undefined,
        rfid_tag: form.rfid_tag || undefined,
        parity: form.parity,
        entry_date: form.entry_date || undefined,
        entry_type: form.entry_type || undefined,
        // 종료상태 모돈은 status 변경 불가(cull 모달 전용)
        status: isTerminal ? undefined : form.status,
      }),
    onSuccess,
    onError: (err: unknown) => {
      setError(apiError(err, t("editFailed")));
    },
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold">{t("editTitle", { tag: sow.ear_tag })}</h2>
          <button onClick={onClose} className="p-1 rounded-md text-text3 hover:text-text hover:bg-bg2 transition">
            <X size={16} />
          </button>
        </div>

        <div className="space-y-3">
          <Field label={t("fEarTag")}>
            <input
              value={form.ear_tag}
              onChange={(e) => setForm((f) => ({ ...f, ear_tag: e.target.value }))}
              className="input"
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("fBreed")}>
              <input
                value={form.breed ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, breed: e.target.value }))}
                placeholder={t("phBreed")}
                className="input"
              />
            </Field>
            <Field label={t("fBreedCompany")}>
              <input
                value={form.breed_company ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, breed_company: e.target.value }))}
                className="input"
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("fRfid")}>
              <input
                value={form.rfid_tag ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, rfid_tag: e.target.value }))}
                placeholder={t("phRfid")}
                className="input"
              />
            </Field>
            <Field label={t("fGenetics")}>
              <input
                value={form.genetics_id ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, genetics_id: e.target.value }))}
                className="input"
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("fParity")}>
              <input
                type="number" min={0} max={20}
                value={form.parity ?? 0}
                onChange={(e) => setForm((f) => ({ ...f, parity: +e.target.value }))}
                className="input"
              />
            </Field>
            <Field label={t("fStatus")}>
              {isTerminal ? (
                <input value={tStatus(sow.status)} disabled className="input opacity-60" />
              ) : (
                <select
                  value={form.status ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, status: e.target.value as UpdateSowRequest["status"] }))}
                  className="input"
                >
                  {ACTIVE_SOW_STATUSES.map((s) => (
                    <option key={s} value={s}>{tStatus(s)}</option>
                  ))}
                </select>
              )}
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("fEntryDate")}>
              <input
                type="date"
                value={form.entry_date ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, entry_date: e.target.value }))}
                className="input"
              />
            </Field>
            <Field label={t("fEntryType")}>
              <select
                value={form.entry_type ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, entry_type: e.target.value as UpdateSowRequest["entry_type"] }))}
                className="input"
              >
                <option value="GILT">{t("etGilt")}</option>
                <option value="PURCHASE">{t("etPurchase")}</option>
                <option value="TRANSFER">{t("etTransfer")}</option>
                <option value="BORN">{t("etBorn")}</option>
              </select>
            </Field>
          </div>
        </div>

        {isTerminal && <p className="text-[11px] text-text3 mt-3">{t("editTerminalNote")}</p>}
        {error && <p className="text-xs text-danger mt-3">{error}</p>}

        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="flex-1 border border-gray-200 rounded-lg py-2 text-sm">
            {t("cancel")}
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!form.ear_tag?.trim() || mutation.isPending}
            className="flex-1 bg-primary text-white rounded-lg py-2 text-sm font-semibold disabled:opacity-50"
          >
            {mutation.isPending ? t("saving") : t("save")}
          </button>
        </div>
      </div>
    </div>
  );
}

const REMOVAL_TYPE_VALUES: SowCullRequest["removal_type"][] = ["CULLED", "DEAD", "SOLD", "TRANSFER"];
const REASON_CATEGORY_KEYS: { value: NonNullable<SowCullRequest["reason_category"]>; key: string }[] = [
  { value: "REPRODUCTIVE", key: "rcReproductive" },
  { value: "LAMENESS",     key: "rcLameness" },
  { value: "DISEASE",      key: "rcDisease" },
  { value: "AGE",          key: "rcAge" },
  { value: "PERFORMANCE",  key: "rcPerformance" },
  { value: "INJURY",       key: "rcInjury" },
  { value: "BEHAVIOR",     key: "rcBehavior" },
  { value: "UNKNOWN",      key: "rcUnknown" },
  { value: "OTHER",        key: "rcOther" },
];

function CullSowModal({
  farmId,
  sow,
  onClose,
  onSuccess,
}: {
  farmId: string;
  sow: Sow;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const t = useTranslations("sows");
  const tStatus = useTranslations("sowStatus");
  const [form, setForm] = useState<SowCullRequest>({
    removal_type: "CULLED",
    removal_date: localToday(),
  });
  // 글로벌 SaaS — 통화 하드코딩(KRW) 금지(C14). 사용자가 선택, 기본 USD.
  const [currency, setCurrency] = useState("USD");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => sowsApi.cull(farmId, sow.id, form),
    onSuccess,
    onError: (err: unknown) => {
      setError(apiError(err, t("cullFailed")));
    },
  });

  const isSold = form.removal_type === "SOLD";

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-base font-bold">{t("cullTitle", { tag: sow.ear_tag })}</h2>
          <button onClick={onClose} className="p-1 rounded-md text-text3 hover:text-text hover:bg-bg2 transition">
            <X size={16} />
          </button>
        </div>
        <p className="text-xs text-text3 mb-4">{t("cullNote")}</p>

        <div className="space-y-3">
          <Field label={t("fRemovalType")}>
            <div className="grid grid-cols-4 gap-1.5">
              {REMOVAL_TYPE_VALUES.map((rt) => (
                <button
                  key={rt}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, removal_type: rt }))}
                  className={`py-2 rounded-lg text-xs font-semibold border transition ${
                    form.removal_type === rt
                      ? "bg-primary text-white border-primary"
                      : "bg-white text-text2 border-border hover:border-text3/50"
                  }`}
                >
                  {tStatus(rt)}
                </button>
              ))}
            </div>
          </Field>
          <Field label={t("fRemovalDate")}>
            <input
              type="date"
              value={form.removal_date}
              onChange={(e) => setForm((f) => ({ ...f, removal_date: e.target.value }))}
              className="input"
            />
          </Field>
          <Field label={t("fReason")}>
            <select
              value={form.reason_category ?? ""}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  reason_category: (e.target.value || undefined) as SowCullRequest["reason_category"],
                }))
              }
              className="input"
            >
              <option value="">{t("select")}</option>
              {REASON_CATEGORY_KEYS.map((r) => (
                <option key={r.value} value={r.value}>{t(r.key)}</option>
              ))}
            </select>
          </Field>
          {isSold && (
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("fWeight")}>
                <input
                  type="number"
                  min={0}
                  value={form.body_weight_kg ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, body_weight_kg: e.target.value ? Number(e.target.value) : undefined }))
                  }
                  className="input"
                />
              </Field>
              <Field label={t("fSalePrice")}>
                <div className="flex gap-1.5">
                  <input
                    type="number"
                    min={0}
                    value={form.sale_price ?? ""}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        sale_price: e.target.value ? Number(e.target.value) : undefined,
                        sale_currency: e.target.value ? currency : undefined,
                      }))
                    }
                    className="input flex-1"
                  />
                  <select
                    value={currency}
                    onChange={(e) => {
                      setCurrency(e.target.value);
                      setForm((f) => ({
                        ...f,
                        sale_currency: f.sale_price ? e.target.value : undefined,
                      }));
                    }}
                    className="input w-20"
                  >
                    {["USD", "KRW", "CNY", "VND", "BRL", "EUR", "THB", "MXN"].map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </Field>
            </div>
          )}
          <Field label={t("fNote")}>
            <input
              value={form.notes ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value || undefined }))}
              placeholder={t("phNote")}
              className="input"
            />
          </Field>
        </div>

        {error && <p className="text-xs text-danger mt-3">{error}</p>}

        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="flex-1 border border-gray-200 rounded-lg py-2 text-sm">
            {t("cancel")}
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!form.removal_date || mutation.isPending}
            className="flex-1 bg-red-500 hover:bg-red-600 text-white rounded-lg py-2 text-sm font-semibold disabled:opacity-50 transition"
          >
            {mutation.isPending ? t("culling") : t("cullConfirm")}
          </button>
        </div>
      </div>
    </div>
  );
}

function AddSowModal({
  farmId,
  onClose,
  onSuccess,
}: {
  farmId: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const t = useTranslations("sows");
  const tv = useTranslations("validation");
  const [form, setForm] = useState<CreateSowRequest>({
    ear_tag: "",
    entry_date: localToday(),
    entry_type: "GILT",
    parity: 0,
    breed: "",
  });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => sowsApi.create(farmId, form),
    onSuccess: () => { track("sow_added", { entry_type: form.entry_type }); onSuccess(); },
    onError: (err: unknown) => {
      setError(apiError(err, t("regFailed")));
    },
  });

  const set = (k: keyof CreateSowRequest, v: string | number) =>
    setForm((f) => ({ ...f, [k]: v }));

  function submit() {
    const err = firstError(sowEntrySchema, {
      ear_tag: form.ear_tag, entry_date: form.entry_date, entry_type: form.entry_type,
    }, tv);
    if (err) { setError(err); return; }
    mutation.mutate();
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl">
        <h2 className="text-base font-bold mb-4">{t("regTitle")}</h2>

        <div className="space-y-3">
          <Field label={t("fEarTag")}>
            <input
              value={form.ear_tag}
              onChange={(e) => set("ear_tag", e.target.value)}
              placeholder={t("phEarTag")}
              data-testid="add-sow-ear-tag"
              className="input"
            />
          </Field>
          <Field label={t("fEntryDate")}>
            <input
              type="date"
              value={form.entry_date}
              onChange={(e) => set("entry_date", e.target.value)}
              className="input"
            />
          </Field>
          <Field label={t("fEntryType")}>
            <select
              value={form.entry_type}
              onChange={(e) => set("entry_type", e.target.value as SowEntryType)}
              className="input"
            >
              <option value="GILT">{t("entryGilt")}</option>
              <option value="PURCHASE">{t("entryPurchase")}</option>
              <option value="TRANSFER">{t("entryTransfer")}</option>
              <option value="BORN">{t("entryBorn")}</option>
            </select>
          </Field>
          <Field label={t("fParity")}>
            <input
              type="number"
              value={form.parity}
              min={0}
              onChange={(e) => set("parity", Number(e.target.value))}
              className="input"
            />
          </Field>
          <Field label={t("fBreed")}>
            <input
              value={form.breed ?? ""}
              onChange={(e) => set("breed", e.target.value)}
              placeholder={t("phBreed")}
              className="input"
            />
          </Field>
        </div>

        {error && <p className="text-xs text-danger mt-3">{error}</p>}

        <div className="flex gap-2 mt-5">
          <button
            onClick={onClose}
            className="flex-1 border border-gray-200 rounded-lg py-2 text-sm"
          >
            {t("cancel")}
          </button>
          <button
            onClick={submit}
            disabled={!form.ear_tag || mutation.isPending}
            data-testid="add-sow-submit"
            className="flex-1 bg-primary text-white rounded-lg py-2 text-sm font-semibold disabled:opacity-50"
          >
            {mutation.isPending ? t("regging") : t("reg")}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}
