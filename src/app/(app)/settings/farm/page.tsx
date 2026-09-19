"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save } from "lucide-react";
import { farmsApi } from "@/lib/api/endpoints/farms";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import type { FarmReproConfig } from "@/types/api.types";

const FIELDS: {
  key: keyof FarmReproConfig;
  labelKey: string;
  min: number;
  max: number;
  descKey: string;
}[] = [
  { key: "gestation_days",        labelKey: "gestation",    min: 100, max: 130, descKey: "gestationDesc" },
  { key: "lactation_days",        labelKey: "lactation",    min: 10,  max: 40,  descKey: "lactationDesc" },
  { key: "wei_target_days",       labelKey: "wsi",          min: 1,   max: 30,  descKey: "wsiDesc" },
  { key: "gilt_first_mating_age", labelKey: "giltAge",      min: 180, max: 400, descKey: "giltAgeDesc" },
  { key: "slaughter_age",         labelKey: "slaughterAge", min: 120, max: 300, descKey: "slaughterAgeDesc" },
];

export default function FarmConfigPage() {
  const t = useTranslations("settingsFarm");
  const farmId = useAuthStore((s) => s.activeFarmId);
  const qc = useQueryClient();
  const [form, setForm] = useState<FarmReproConfig | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.farms.reproConfig(farmId ?? ""),
    queryFn: () => farmsApi.getReproConfig(farmId!),
    enabled: !!farmId,
  });

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const mut = useMutation({
    mutationFn: (body: Partial<FarmReproConfig>) => farmsApi.updateReproConfig(farmId!, body),
    onSuccess: (res) => {
      setForm(res);
      qc.invalidateQueries({ queryKey: queryKeys.farms.reproConfig(farmId ?? "") });
    },
  });

  if (!farmId) return <div className="p-7 text-text3">{t("selectFarm")}</div>;

  const setField = (key: keyof FarmReproConfig, value: number) =>
    setForm((f) => (f ? { ...f, [key]: value } : f));

  const outOfRange = form
    ? FIELDS.some((fl) => form[fl.key] < fl.min || form[fl.key] > fl.max)
    : false;

  return (
    <div className="max-w-2xl mx-auto px-7 py-6">
      <h1 className="text-xl font-extrabold tracking-tight text-text mb-1">{t("title")}</h1>
      <p className="text-[13px] text-text3 mb-6">
        {t("subtitle")}
      </p>

      {isLoading || !form ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-16 bg-border rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : (
        <>
          <div className="bg-surface border border-border rounded-2xl divide-y divide-border mb-5">
            {FIELDS.map((fl) => {
              const val = form[fl.key];
              const bad = val < fl.min || val > fl.max;
              return (
                <div key={fl.key} className="flex items-center justify-between gap-4 px-5 py-4">
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-text">{t(fl.labelKey)}</div>
                    <div className="text-[11px] text-text3 mt-0.5">{t(fl.descKey)}</div>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <input
                      type="number"
                      min={fl.min}
                      max={fl.max}
                      value={val}
                      onChange={(e) => setField(fl.key, Number(e.target.value))}
                      className={`w-20 text-right font-mono text-sm rounded-lg border px-2.5 py-1.5 bg-bg ${
                        bad ? "border-danger text-danger" : "border-border text-text"
                      }`}
                    />
                    <span className="text-xs text-text3 w-4">{t("daysUnit")}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {outOfRange && (
            <p className="text-xs text-danger mb-3">{t("outOfRange")}</p>
          )}

          <button
            onClick={() => form && mut.mutate(form)}
            disabled={outOfRange || mut.isPending}
            className="inline-flex items-center gap-2 bg-primary text-white text-sm font-semibold rounded-xl px-5 py-2.5 disabled:opacity-50"
          >
            <Save size={16} />
            {mut.isPending ? t("saving") : t("save")}
          </button>
          {mut.isSuccess && !mut.isPending && (
            <span className="ml-3 text-xs text-success font-semibold">{t("saved")}</span>
          )}
        </>
      )}
    </div>
  );
}
