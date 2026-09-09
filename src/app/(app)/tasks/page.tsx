"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, ListTodo, RefreshCw, X, CheckCircle2 } from "lucide-react";
import { tasksApi } from "@/lib/api/endpoints/tasks";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import type { Task, TaskStatus } from "@/types/api.types";

const PRIORITY_STYLE: Record<number, string> = {
  1: "border-l-red-400",
  2: "border-l-amber-400",
  3: "border-l-slate-300",
};

export default function TasksPage() {
  const t = useTranslations("tasks");
  const farmId = useAuthStore((s) => s.activeFarmId);
  const qc = useQueryClient();
  const status: TaskStatus = "OPEN";

  const { data, isLoading, isError } = useQuery({
    queryKey: queryKeys.tasks.list(farmId ?? "", status),
    queryFn: () => tasksApi.list(farmId!, status),
    enabled: !!farmId,
  });

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: queryKeys.tasks.list(farmId ?? "", status) });

  const generate = useMutation({
    mutationFn: () => tasksApi.generate(farmId!),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ id, next }: { id: string; next: TaskStatus }) =>
      tasksApi.update(farmId!, id, { status: next }),
    onSuccess: invalidate,
  });

  if (!farmId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-text3">{t("selectFarm")}</p>
      </div>
    );
  }

  const tasks = data ?? [];

  return (
    <div className="p-7">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[22px] font-extrabold tracking-tight flex items-center gap-2">
            <ListTodo className="w-5 h-5 text-primary" />
            {t("pageTitle")}
          </h1>
          <p className="text-xs text-text3 mt-0.5">{t("subtitle", { n: tasks.length })}</p>
        </div>
        <button
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
          className="text-xs font-medium text-white bg-primary rounded-lg px-3 py-2 hover:opacity-90 transition flex items-center gap-1.5 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${generate.isPending ? "animate-spin" : ""}`} />
          {t("refreshTasks")}
        </button>
      </div>

      {isLoading && <div className="text-center text-text3 py-20">{t("loading")}</div>}
      {isError && (
        <div className="bg-red-soft border border-danger/40 rounded-xl p-4 text-sm text-red-700">
          {t("loadError")}
        </div>
      )}

      {data && tasks.length === 0 && (
        <div className="bg-green-soft border border-success/30 rounded-xl p-6 text-sm text-success text-center">
          <CheckCircle2 size={26} className="mx-auto mb-2.5" strokeWidth={1.75} aria-hidden />
          {t("allClear")}
        </div>
      )}

      <div className="space-y-2">
        {tasks.map((task) => (
          <TaskRow
            key={task.id}
            task={task}
            onDone={() => update.mutate({ id: task.id, next: "DONE" })}
            onDismiss={() => update.mutate({ id: task.id, next: "DISMISSED" })}
            disabled={update.isPending}
          />
        ))}
      </div>
    </div>
  );
}

function TaskRow({
  task, onDone, onDismiss, disabled,
}: {
  task: Task; onDone: () => void; onDismiss: () => void; disabled: boolean;
}) {
  const t = useTranslations("tasks");
  const border = PRIORITY_STYLE[task.priority] ?? PRIORITY_STYLE[3];
  return (
    <div className={`bg-surface border border-border border-l-4 ${border} rounded-xl px-4 py-3 flex items-center gap-3`}>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold truncate">{task.title}</div>
        {task.overdue_days != null && (
          <div className="text-[11px] text-text3 mt-0.5">{t("overdueDays", { n: task.overdue_days })}</div>
        )}
      </div>

      {task.action && (
        <Link
          href={task.action}
          className="text-xs font-medium text-primary border border-primary/30 rounded-lg px-2.5 py-1.5 hover:bg-primary/5 transition flex items-center gap-1 flex-shrink-0"
        >
          {t("go")}
          <ArrowRight className="w-3 h-3" />
        </Link>
      )}

      <button
        onClick={onDone}
        disabled={disabled}
        title={t("done")}
        className="p-1.5 rounded-lg text-success hover:bg-green-soft transition disabled:opacity-50 flex-shrink-0"
      >
        <Check className="w-4 h-4" />
      </button>
      <button
        onClick={onDismiss}
        disabled={disabled}
        title={t("dismiss")}
        className="p-1.5 rounded-lg text-text3 hover:bg-border transition disabled:opacity-50 flex-shrink-0"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
