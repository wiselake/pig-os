"use client";

import { localToday } from "@/lib/date";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, X } from "lucide-react";
import { useAuthStore } from "@/store/auth.store";
import { canEntry } from "@/lib/auth/permissions";
import { useActiveRole } from "@/lib/auth/useActiveRole";
import {
  boarsApi,
  type Boar,
  type CreateBoarRequest,
  type UpdateBoarRequest,
} from "@/lib/api/endpoints/boars";

// 상태 → i18n 키 (boars.statusXxx)
const STATUS_KEY: Record<string, string> = {
  ACTIVE: "statusActive",
  CULLED: "statusCulled",
  DEAD: "statusDead",
  TRANSFERRED: "statusTransferred",
};

const STATUS_CLASS: Record<string, string> = {
  ACTIVE:      "bg-green-soft text-success border-success/30",
  CULLED:      "bg-red-soft text-danger border-danger/30",
  DEAD:        "bg-gray-100 text-gray-400 border-gray-200",
  TRANSFERRED: "bg-amber-soft text-warning border-warning/30",
};

const BREEDS = ["Duroc", "Landrace", "Yorkshire", "Berkshire", "Pietrain", "Hampshire"];
const SEMEN_QUALITY_KEYS = [
  { value: "EXCELLENT", key: "semenExcellent" },
  { value: "GOOD",      key: "semenGood" },
  { value: "FAIR",      key: "semenFair" },
  { value: "POOR",      key: "semenPoor" },
];
const ENTRY_TYPE_KEYS = [
  { value: "PURCHASE", key: "entryPurchase" },
  { value: "BORN",     key: "entryBorn" },
  { value: "TRANSFER", key: "entryTransfer" },
];

const EMPTY_FORM: CreateBoarRequest = {
  ear_tag: "",
  breed: "",
  breed_company: "",
  entry_date: "",
  entry_type: "PURCHASE",
  semen_quality: "",
};

export default function BoarsPage() {
  const t = useTranslations("boars");
  const activeFarmId = useAuthStore((s) => s.activeFarmId);
  const canWrite = canEntry(useActiveRole());
  const farmId = activeFarmId ?? "";
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [modal, setModal] = useState<"create" | "edit" | null>(null);
  const [editTarget, setEditTarget] = useState<Boar | null>(null);
  const [form, setForm] = useState<CreateBoarRequest>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const { data: boars = [], isLoading, error } = useQuery({
    queryKey: ["boars", farmId, statusFilter],
    queryFn: () => boarsApi.list(farmId, statusFilter || undefined),
    enabled: !!farmId,
  });

  const PER_PAGE = 20;
  const totalPages = Math.max(1, Math.ceil(boars.length / PER_PAGE));
  // 필터 전환으로 페이지가 총페이지를 넘으면 빈 표+페이저 사라짐(스트랜딩) 버그 방지 — finishers와 동일 클램프.
  const safePage = Math.min(page, totalPages);
  const paged = boars.slice((safePage - 1) * PER_PAGE, safePage * PER_PAGE);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["boars", farmId] });

  const closeModal = () => {
    setModal(null);
    setEditTarget(null);
    setForm(EMPTY_FORM);
    setFormError(null);
  };

  const createMutation = useMutation({
    mutationFn: (body: CreateBoarRequest) => boarsApi.create(farmId, body),
    onSuccess: () => { invalidate(); closeModal(); },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(typeof detail === "string" ? detail : t("createFailed"));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: UpdateBoarRequest }) =>
      boarsApi.update(farmId, id, body),
    onSuccess: () => { invalidate(); closeModal(); },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(typeof detail === "string" ? detail : t("editFailed"));
    },
  });

  const openCreate = () => {
    setForm({ ...EMPTY_FORM, entry_date: localToday() });
    setModal("create");
  };

  const openEdit = (boar: Boar) => {
    setEditTarget(boar);
    setForm({
      ear_tag: boar.ear_tag,
      breed: boar.breed ?? "",
      breed_company: boar.breed_company ?? "",
      entry_date: boar.entry_date.slice(0, 10),
      entry_type: boar.entry_type ?? "PURCHASE",
      semen_quality: boar.semen_quality ?? "",
    });
    setModal("edit");
  };

  const submit = () => {
    setFormError(null);
    if (!form.ear_tag.trim()) { setFormError(t("reqEarTag")); return; }
    if (modal === "create") {
      if (!form.entry_date) { setFormError(t("reqEntryDate")); return; }
      createMutation.mutate({
        ...form,
        breed: form.breed || undefined,
        breed_company: form.breed_company || undefined,
        semen_quality: form.semen_quality || undefined,
      });
    } else if (modal === "edit" && editTarget) {
      updateMutation.mutate({
        id: editTarget.id,
        body: {
          ear_tag: form.ear_tag,
          breed: form.breed || undefined,
          breed_company: form.breed_company || undefined,
          semen_quality: form.semen_quality || undefined,
        },
      });
    }
  };

  const changeStatus = (boar: Boar, status: Boar["status"]) => {
    updateMutation.mutate({ id: boar.id, body: { status } });
  };

  const activeCount = boars.filter((b) => b.status === "ACTIVE").length;
  const pending = createMutation.isPending || updateMutation.isPending;

  return (
    <main className="p-6 max-w-[1600px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-text">{t("title")}</h1>
          <p className="text-sm text-text3 mt-0.5">{t("activeCount", { n: activeCount })}</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="text-sm border border-border rounded-lg px-3 py-1.5 bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary/30"
          >
            <option value="">{t("allStatus")}</option>
            <option value="ACTIVE">{t("statusActive")}</option>
            <option value="CULLED">{t("statusCulled")}</option>
            <option value="DEAD">{t("statusDead")}</option>
            <option value="TRANSFERRED">{t("statusTransferred")}</option>
          </select>
          {canWrite && (
            <button
              onClick={openCreate}
              className="flex items-center gap-1.5 bg-primary text-white text-sm font-semibold px-3.5 py-1.5 rounded-lg hover:bg-success transition"
            >
              <Plus size={14} />
              {t("addBoar")}
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-sm text-text3 py-12 text-center">{t("loading")}</div>
      ) : error ? (
        <div className="text-sm text-danger py-12 text-center">{t("loadError")}</div>
      ) : boars.length === 0 ? (
        <div className="border border-dashed border-border rounded-xl py-14 text-center">
          <p className="text-sm text-text3 mb-3">
            {statusFilter ? t("emptyFiltered") : t("emptyNone")}
          </p>
          {!statusFilter && canWrite && (
            <button onClick={openCreate} className="text-sm font-semibold text-primary hover:underline">
              {t("emptyCta")}
            </button>
          )}
        </div>
      ) : (
        <div className="bg-surface border border-border rounded-xl overflow-hidden">
          {/* 데스크톱: 테이블 / 모바일(md 미만): 카드 — 현장 폰 가로스크롤 제거 */}
          <table className="w-full text-sm hidden md:table">
            <thead>
              <tr className="border-b border-border bg-bg2">
                <th className="text-left px-4 py-3 text-text3 font-medium">{t("thEarTag")}</th>
                <th className="text-left px-4 py-3 text-text3 font-medium">{t("thBreed")}</th>
                <th className="text-left px-4 py-3 text-text3 font-medium">{t("thEntryDate")}</th>
                <th className="text-left px-4 py-3 text-text3 font-medium">{t("thSemen")}</th>
                <th className="text-left px-4 py-3 text-text3 font-medium">{t("thStatus")}</th>
                <th className="text-right px-4 py-3 text-text3 font-medium">{t("thActions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {paged.map((boar: Boar) => (
                <tr key={boar.id} className="hover:bg-bg2/50 transition-colors">
                  <td className="px-4 py-3 font-mono font-semibold text-text">{boar.ear_tag}</td>
                  <td className="px-4 py-3 text-text1">{boar.breed ?? "—"}</td>
                  <td className="px-4 py-3 text-text2">{boar.entry_date.slice(0, 10)}</td>
                  <td className="px-4 py-3 text-text2">
                    {(() => {
                      const q = SEMEN_QUALITY_KEYS.find((x) => x.value === boar.semen_quality);
                      return q ? t(q.key) : "—";
                    })()}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${STATUS_CLASS[boar.status] ?? "bg-gray-50 text-gray-500"}`}>
                      {STATUS_KEY[boar.status] ? t(STATUS_KEY[boar.status]) : boar.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {!canWrite && <span className="text-text3 text-xs">—</span>}
                      {canWrite && (
                      <button
                        onClick={() => openEdit(boar)}
                        title={t("editTooltip")}
                        className="p-1.5 rounded-md text-text3 hover:text-text hover:bg-bg2 transition"
                      >
                        <Pencil size={12} />
                      </button>
                      )}
                      {canWrite && boar.status === "ACTIVE" && (
                        <select
                          value=""
                          onChange={(e) => {
                            if (e.target.value) changeStatus(boar, e.target.value as Boar["status"]);
                          }}
                          className="text-xs border border-border rounded-md px-1.5 py-1 bg-surface text-text3 focus:outline-none"
                        >
                          <option value="">{t("changeStatus")}</option>
                          <option value="CULLED">{t("statusCulled")}</option>
                          <option value="DEAD">{t("statusDead")}</option>
                          <option value="TRANSFERRED">{t("statusTransferred")}</option>
                        </select>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {/* 모바일 카드 뷰 (md 미만) — 데스크톱 테이블과 동일 데이터 */}
          <ul className="md:hidden divide-y divide-border">
            {paged.map((boar: Boar) => {
              const q = SEMEN_QUALITY_KEYS.find((x) => x.value === boar.semen_quality);
              return (
                <li key={boar.id} className="p-4 flex flex-col gap-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono font-semibold text-text">{boar.ear_tag}</span>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${STATUS_CLASS[boar.status] ?? "bg-gray-50 text-gray-500"}`}>
                      {STATUS_KEY[boar.status] ? t(STATUS_KEY[boar.status]) : boar.status}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-y-1 text-xs text-text2">
                    <span>{t("thBreed")}: <span className="text-text1">{boar.breed ?? "—"}</span></span>
                    <span>{t("thEntryDate")}: <span className="text-text1">{boar.entry_date.slice(0, 10)}</span></span>
                    <span className="col-span-2">{t("thSemen")}: <span className="text-text1">{q ? t(q.key) : "—"}</span></span>
                  </div>
                  {canWrite && (
                    <div className="flex items-center gap-2 pt-1">
                      <button
                        onClick={() => openEdit(boar)}
                        className="flex items-center gap-1 text-xs px-2 py-1 rounded-md text-text2 hover:text-text hover:bg-bg2 transition"
                      >
                        <Pencil size={12} /> {t("editTooltip")}
                      </button>
                      {boar.status === "ACTIVE" && (
                        <select
                          value=""
                          onChange={(e) => {
                            if (e.target.value) changeStatus(boar, e.target.value as Boar["status"]);
                          }}
                          className="text-xs border border-border rounded-md px-1.5 py-1 bg-surface text-text3 focus:outline-none"
                        >
                          <option value="">{t("changeStatus")}</option>
                          <option value="CULLED">{t("statusCulled")}</option>
                          <option value="DEAD">{t("statusDead")}</option>
                          <option value="TRANSFERRED">{t("statusTransferred")}</option>
                        </select>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-border text-xs text-text3">
              <span>{t("pageInfo", { n: boars.length, p: safePage, tp: totalPages })}</span>
              <div className="flex gap-1.5">
                <button
                  onClick={() => setPage(Math.max(1, safePage - 1))}
                  disabled={safePage <= 1}
                  className="px-2.5 py-1 rounded-md border border-border disabled:opacity-40 hover:border-primary"
                >
                  {t("prev")}
                </button>
                <button
                  onClick={() => setPage(Math.min(totalPages, safePage + 1))}
                  disabled={safePage >= totalPages}
                  className="px-2.5 py-1 rounded-md border border-border disabled:opacity-40 hover:border-primary"
                >
                  {t("next")}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Create / Edit modal */}
      {modal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 p-4" onClick={closeModal}>
          <div
            className="w-full max-w-md bg-surface rounded-2xl border border-border shadow-xl p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-bold text-text">
                {modal === "create" ? t("modalCreate") : t("modalEdit", { tag: editTarget?.ear_tag ?? "" })}
              </h2>
              <button onClick={closeModal} className="p-1 rounded-md text-text3 hover:text-text hover:bg-bg2 transition">
                <X size={16} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-text3 mb-1.5">{t("fEarTag")}</label>
                <input
                  value={form.ear_tag}
                  onChange={(e) => setForm((f) => ({ ...f, ear_tag: e.target.value }))}
                  placeholder={t("phEarTag")}
                  className="w-full h-10 px-3 text-sm border border-border rounded-lg bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-text3 mb-1.5">{t("fBreed")}</label>
                  <select
                    value={form.breed}
                    onChange={(e) => setForm((f) => ({ ...f, breed: e.target.value }))}
                    className="w-full h-10 px-3 text-sm border border-border rounded-lg bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary/30"
                  >
                    <option value="">{t("select")}</option>
                    {BREEDS.map((b) => <option key={b} value={b}>{b}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-text3 mb-1.5">{t("fStud")}</label>
                  <input
                    value={form.breed_company}
                    onChange={(e) => setForm((f) => ({ ...f, breed_company: e.target.value }))}
                    placeholder={t("phStud")}
                    className="w-full h-10 px-3 text-sm border border-border rounded-lg bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                </div>
              </div>

              {modal === "create" && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-text3 mb-1.5">{t("fEntryDate")}</label>
                    <input
                      type="date"
                      value={form.entry_date}
                      onChange={(e) => setForm((f) => ({ ...f, entry_date: e.target.value }))}
                      className="w-full h-10 px-3 text-sm border border-border rounded-lg bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary/30"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-text3 mb-1.5">{t("fEntryType")}</label>
                    <select
                      value={form.entry_type}
                      onChange={(e) => setForm((f) => ({ ...f, entry_type: e.target.value }))}
                      className="w-full h-10 px-3 text-sm border border-border rounded-lg bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary/30"
                    >
                      {ENTRY_TYPE_KEYS.map((et) => <option key={et.value} value={et.value}>{t(et.key)}</option>)}
                    </select>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-text3 mb-1.5">{t("fSemen")}</label>
                <select
                  value={form.semen_quality}
                  onChange={(e) => setForm((f) => ({ ...f, semen_quality: e.target.value }))}
                  className="w-full h-10 px-3 text-sm border border-border rounded-lg bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary/30"
                >
                  <option value="">{t("select")}</option>
                  {SEMEN_QUALITY_KEYS.map((q) => <option key={q.value} value={q.value}>{t(q.key)}</option>)}
                </select>
              </div>

              {formError && (
                <div className="bg-red-soft border border-danger/40 rounded-lg px-3.5 py-2.5 text-sm text-danger">
                  {formError}
                </div>
              )}

              <div className="flex gap-2.5 pt-1">
                <button
                  onClick={closeModal}
                  className="flex-1 h-10 border border-border text-text2 rounded-lg text-sm font-medium hover:bg-bg2 transition"
                >
                  {t("cancel")}
                </button>
                <button
                  onClick={submit}
                  disabled={pending}
                  className="flex-1 h-10 bg-primary text-white rounded-lg text-sm font-semibold hover:bg-success disabled:opacity-50 transition"
                >
                  {pending ? t("saving") : modal === "create" ? t("create") : t("save")}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
