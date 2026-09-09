"use client";

import { useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { membersApi, type CreateMemberRequest, type FarmRole, type Member } from "@/lib/api/endpoints/members";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import { canOwn } from "@/lib/auth/permissions";
import { useActiveRole } from "@/lib/auth/useActiveRole";
import type { UserRole } from "@/types/api.types";

const ROLES: FarmRole[] = ["FARM_OWNER", "FARM_MANAGER", "FARM_WORKER", "VET", "VIEWER"];

const ROLE_BADGE: Record<FarmRole, string> = {
  FARM_OWNER: "bg-green-soft text-success",
  FARM_MANAGER: "bg-green-soft text-success",
  FARM_WORKER: "bg-slate-100 text-slate-600",
  VET: "bg-green-soft text-success",
  VIEWER: "bg-gray-100 text-gray-500",
};

// 멤버 관리는 소유자(OWNER) 전용 — MANAGER는 조회만(백엔드 require_farm_role과 일치).
function canManageMembers(role: string | null | undefined): boolean {
  return canOwn(role);
}

function getErrorMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

export default function UsersPage() {
  const t = useTranslations("users");
  const tErrors = useTranslations("errors");
  const tAlerts = useTranslations("alerts");
  const farmId = useAuthStore((s) => s.activeFarmId);
  const myRole = useActiveRole();
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);

  const canManage = canManageMembers(myRole);
  const membersKey = queryKeys.farms.members(farmId ?? "");

  const {
    data: members = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: membersKey,
    queryFn: () => membersApi.list(farmId!),
    enabled: !!farmId,
  });

  const updateMutation = useMutation({
    mutationFn: ({ userId, body }: { userId: string; body: { role?: FarmRole; active?: boolean } }) =>
      membersApi.update(farmId!, userId, body),
    onMutate: () => setRowError(null),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: membersKey }),
    onError: (err) => setRowError(getErrorMessage(err, tErrors("generic"))),
  });

  if (!farmId) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <p className="text-sm text-text3">{tAlerts("selectFarm")}</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-7 py-6">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
        <h1 className="text-xl font-extrabold tracking-tight text-text">{t("title")}</h1>
        {canManage && (
          <button
            type="button"
            onClick={() => setShowAdd(true)}
            className="inline-flex items-center gap-1.5 bg-primary text-white text-sm font-semibold px-3.5 py-2 rounded-lg hover:bg-success transition"
          >
            <Plus size={14} />
            {t("addMember")}
          </button>
        )}
      </div>
      <p className="text-[13px] text-text3 mb-2">{t("subtitle")}</p>
      {!canManage && <p className="text-xs text-text3 mb-5">{t("onlyManagers")}</p>}

      {rowError && (
        <div className="mb-4 rounded-xl border border-danger/40 bg-red-soft px-4 py-3 text-xs font-medium text-danger">
          {rowError}
        </div>
      )}

      {isLoading ? (
        <div className="space-y-2 mt-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 bg-border rounded-xl animate-pulse" />
          ))}
        </div>
      ) : isError ? (
        <div className="text-sm text-danger py-12 text-center">{tErrors("generic")}</div>
      ) : members.length === 0 ? (
        <div className="border border-dashed border-border rounded-2xl py-14 text-center text-text3 text-sm mt-6">
          {t("empty")}
        </div>
      ) : (
        <div className="bg-surface border border-border rounded-2xl overflow-x-auto mt-6">
          <table className="w-full min-w-[720px] text-sm">
            <thead>
              <tr className="bg-bg2 text-text3 text-[11px] uppercase tracking-wide">
                <th className="text-left font-semibold px-4 py-2.5">{t("colName")}</th>
                <th className="text-left font-semibold px-4 py-2.5">{t("colEmail")}</th>
                <th className="text-left font-semibold px-4 py-2.5">{t("colRole")}</th>
                <th className="text-left font-semibold px-4 py-2.5">{t("colStatus")}</th>
                {canManage && <th className="text-right font-semibold px-4 py-2.5">{t("colActions")}</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {members.map((member) => (
                <MemberRow
                  key={member.user_id}
                  member={member}
                  canManage={canManage}
                  isUpdating={updateMutation.isPending && updateMutation.variables?.userId === member.user_id}
                  onRoleChange={(role) => updateMutation.mutate({ userId: member.user_id, body: { role } })}
                  onActiveToggle={() =>
                    updateMutation.mutate({ userId: member.user_id, body: { active: !member.active } })
                  }
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAdd && (
        <AddMemberModal
          farmId={farmId}
          onClose={() => setShowAdd(false)}
          onSuccess={() => {
            setShowAdd(false);
            queryClient.invalidateQueries({ queryKey: membersKey });
          }}
        />
      )}
    </div>
  );
}

function MemberRow({
  member,
  canManage,
  isUpdating,
  onRoleChange,
  onActiveToggle,
}: {
  member: Member;
  canManage: boolean;
  isUpdating: boolean;
  onRoleChange: (role: FarmRole) => void;
  onActiveToggle: () => void;
}) {
  const t = useTranslations("users");

  return (
    <tr className="hover:bg-bg2/50 transition">
      <td className="px-4 py-3 font-semibold text-text">{member.name}</td>
      <td className="px-4 py-3 text-text2">{member.email ?? "-"}</td>
      <td className="px-4 py-3">
        {canManage ? (
          <select
            value={member.role}
            onChange={(e) => onRoleChange(e.target.value as FarmRole)}
            disabled={isUpdating}
            className="input h-8 w-40 text-xs"
          >
            {ROLES.map((role) => (
              <option key={role} value={role}>
                {t(`role${role}`)}
              </option>
            ))}
          </select>
        ) : (
          <span className={`inline-block px-2 py-0.5 rounded-md text-[11px] font-semibold ${ROLE_BADGE[member.role]}`}>
            {t(`role${member.role}`)}
          </span>
        )}
      </td>
      <td className="px-4 py-3">
        <span className={`text-[11px] font-medium ${member.active ? "text-success" : "text-text3"}`}>
          {member.active ? t("active") : t("inactive")}
        </span>
      </td>
      {canManage && (
        <td className="px-4 py-3 text-right">
          <button
            type="button"
            onClick={onActiveToggle}
            disabled={isUpdating}
            className="text-xs font-semibold text-text3 hover:text-text transition disabled:opacity-50"
          >
            {member.active ? t("deactivate") : t("activate")}
          </button>
        </td>
      )}
    </tr>
  );
}

function AddMemberModal({
  farmId,
  onClose,
  onSuccess,
}: {
  farmId: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const t = useTranslations("users");
  const tErrors = useTranslations("errors");
  const [form, setForm] = useState<CreateMemberRequest>({
    name: "",
    username: "",
    email: "",
    password: "",
    role: "FARM_WORKER",
  });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => membersApi.create(farmId, form),
    onMutate: () => setError(null),
    onSuccess,
    onError: (err) => setError(getErrorMessage(err, tErrors("generic"))),
  });

  const usernameValid = /^[a-zA-Z0-9_.-]{3,50}$/.test(form.username.trim());
  const valid = Boolean(
    form.name.trim() && usernameValid && form.email.trim() && form.password.length >= 8,
  );

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-text">{t("modalTitle")}</h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md text-text3 hover:text-text hover:bg-bg2 transition"
          >
            <X size={16} />
          </button>
        </div>

        <p className="text-[11px] text-text3 bg-bg2 rounded-lg px-3 py-2 mb-4 leading-relaxed">
          {t("inviteNote")}
        </p>

        <div className="space-y-3">
          <Field label={t("fName")}>
            <input
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              className="input"
            />
          </Field>
          <Field label={`${t("fUsername")} (${t("usernameHint")})`}>
            <input
              value={form.username}
              onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
              className="input"
              autoComplete="off"
              placeholder={t("workerPlaceholder")}
            />
          </Field>
          <Field label={t("fEmail")}>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              className="input"
            />
          </Field>
          <Field label={`${t("fPassword")} (${t("passwordHint")})`}>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              className="input"
            />
          </Field>
          <Field label={t("fRole")}>
            <select
              value={form.role}
              onChange={(e) => setForm((f) => ({ ...f, role: e.target.value as FarmRole }))}
              className="input"
            >
              {ROLES.map((role) => (
                <option key={role} value={role}>
                  {t(`role${role}`)}
                </option>
              ))}
            </select>
          </Field>
        </div>

        {error && <p className="text-xs text-danger mt-3">{error}</p>}

        <div className="flex gap-2 mt-5">
          <button type="button" onClick={onClose} className="flex-1 border border-border rounded-lg py-2 text-sm">
            {t("cancel")}
          </button>
          <button
            type="button"
            onClick={() => mutation.mutate()}
            disabled={!valid || mutation.isPending}
            className="flex-1 bg-primary text-white rounded-lg py-2 text-sm font-semibold disabled:opacity-50"
          >
            {t("create")}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}
