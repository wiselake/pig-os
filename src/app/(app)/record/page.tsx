"use client";

import { useState, useMemo, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, PiggyBank, X } from "lucide-react";
import { eventsApi } from "@/lib/api/endpoints/events";
import { track } from "@/lib/analytics";
import { sowsApi } from "@/lib/api/endpoints/sows";
import {
  farrowingSchema, weaningSchema, matingSchema, cullSchema, pigletEventSchema, firstError,
} from "@/lib/validation/eventSchemas";
import {
  Group, SowChip, Segmented, DateField, ValidationBanner, RecordFooter, Lifecycle, AutoCalc,
} from "@/components/record/kit";
import { RecentEventsSection } from "@/components/RecentEventsSection";
import { InsightBanner } from "@/components/InsightBanner";
import { queryKeys } from "@/lib/api/queryKeys";
import { useAuthStore } from "@/store/auth.store";
import { canEntry } from "@/lib/auth/permissions";
import { useActiveRole } from "@/lib/auth/useActiveRole";
import type {
  Sow,
  SowStatus,
  CreateMatingRequest,
  CreateFarrowingRequest,
  CreateWeaningRequest,
  CreateReproductiveEventRequest,
  CreatePregnancyCheckRequest,
  SowCullRequest,
  CreatePigletEventRequest,
  EventInsight,
} from "@/types/api.types";

// ─── Constants ────────────────────────────────────────────────────────────────

type EventType = "farrowing" | "mating" | "weaning" | "preg_check" | "repro" | "cull" | "piglet_death" | "foster";

// label은 record.tabXxx 키로 해석
const EVENT_TYPES: { value: EventType; labelKey: string; color: string; bg: string }[] = [
  { value: "farrowing",    labelKey: "tabFarrowing",   color: "#0E9F6E", bg: "#0E9F6E18" },
  { value: "mating",       labelKey: "tabMating",      color: "#0F6342", bg: "#0F634218" },
  { value: "weaning",      labelKey: "tabWeaning",     color: "#D97706", bg: "#D9770618" },
  { value: "preg_check",   labelKey: "tabPregCheck",   color: "#2563EB", bg: "#2563EB18" },
  { value: "repro",        labelKey: "tabRepro",       color: "#5F4B2C", bg: "#5F4B2C18" },
  { value: "cull",         labelKey: "tabCull",        color: "#DC2626", bg: "#DC262618" },
  { value: "piglet_death", labelKey: "tabPigletDeath", color: "#9D174D", bg: "#9D174D18" },
  { value: "foster",       labelKey: "tabFoster",      color: "#7C3AED", bg: "#7C3AED18" },
];

const STATUS_BADGE: Record<SowStatus, string> = {
  GILT:      "bg-cyan-50 text-cyan-600 border-cyan-100",
  OPEN:      "bg-green-soft text-success border-success/30",
  PREGNANT:  "bg-green-soft text-success border-success/30",
  LACTATING: "bg-green-soft text-success border-success/30",
  ACCIDENT:  "bg-orange-50 text-orange-600 border-orange-100",
  CULLED:    "bg-red-soft text-danger border-danger/30",
  DEAD:      "bg-gray-100 text-gray-400 border-gray-200",
  SOLD:      "bg-emerald-50 text-emerald-600 border-emerald-100",
  TRANSFER:  "bg-amber-soft text-warning border-warning/30",
};

// ─── Stepper ──────────────────────────────────────────────────────────────────

function Stepper({
  label, sub, value, onChange, colorClass = "text-text",
  min = 0, max = 40,
}: {
  label: string; sub?: string; value: number;
  onChange: (v: number) => void; colorClass?: string;
  min?: number; max?: number;
}) {
  return (
    <div className="flex items-center justify-between py-3.5 px-1">
      <div>
        <div className="text-sm font-semibold text-text">{label}</div>
        {sub && <div className="text-[11px] text-text3 mt-0.5">{sub}</div>}
      </div>
      <div className="flex items-center gap-3.5">
        <button
          type="button"
          onClick={() => onChange(Math.max(min, value - 1))}
          className="w-11 h-11 rounded-xl border border-border bg-surface text-text2 text-xl font-semibold flex items-center justify-center hover:bg-border transition"
        >−</button>
        <input
          type="text"
          inputMode="numeric"
          value={value}
          onChange={(e) => {
            const digits = e.target.value.replace(/[^0-9]/g, "");
            const n = digits === "" ? min : Math.min(max, Math.max(min, parseInt(digits, 10)));
            onChange(n);
          }}
          onFocus={(e) => e.target.select()}
          aria-label={label}
          data-testid={`stepper-${label}`}
          className={`w-[56px] text-center text-[28px] font-bold font-mono tracking-tight bg-transparent outline-none focus:ring-2 focus:ring-primary/30 rounded-lg ${colorClass}`}
        />
        <button
          type="button"
          onClick={() => onChange(Math.min(max, value + 1))}
          className="w-11 h-11 rounded-xl bg-navy text-white text-xl font-semibold flex items-center justify-center hover:opacity-90 transition"
        >+</button>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const PAGE_SIZE = 50;

// 딥링크(?tab=) 별칭 → EventType. 알림 액션·QuickInputDrawer가 보내는 값 흡수.
const TAB_ALIASES: Record<string, EventType> = {
  farrowing: "farrowing", mating: "mating", weaning: "weaning",
  preg_check: "preg_check", repro: "repro", cull: "cull",
  piglet_death: "piglet_death", foster: "foster",
};

export default function RecordPage() {
  const t = useTranslations("record");
  const tStatus = useTranslations("sowStatus");
  const farmId = useAuthStore((s) => s.activeFarmId);
  const role = useActiveRole();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const sowIdParam = searchParams.get("sowId");
  const [selectedSow, setSelectedSow] = useState<Sow | null>(null);
  // 딥링크로 들어온 탭은 초기값으로 반영(알림→교배/이유 입력 워크플로 복구, C2).
  const [eventType, setEventType] = useState<EventType>(
    (tabParam && TAB_ALIASES[tabParam]) || "farrowing",
  );
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [visible, setVisible] = useState(PAGE_SIZE);
  const [doneIds, setDoneIds] = useState<Set<string>>(new Set());
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const [lastInsights, setLastInsights] = useState<EventInsight[]>([]);

  // 검색어 디바운스 → 서버사이드 검색 (500개 캡 너머 모돈도 검색됨)
  useEffect(() => {
    const id = setTimeout(() => { setDebounced(search.trim()); setVisible(PAGE_SIZE); }, 300);
    return () => clearTimeout(id);
  }, [search]);

  const queryClient = useQueryClient();

  const { data: sowData } = useQuery({
    queryKey: queryKeys.sows.list(farmId ?? "", { search: debounced }),
    queryFn: () => sowsApi.list(farmId!, { per_page: 200, search: debounced || undefined }),
    enabled: !!farmId,
  });

  const allSows = useMemo(() => sowData?.items ?? [], [sowData]);
  const sows = useMemo(() => allSows.slice(0, visible), [allSows, visible]);
  const hasMore = allSows.length > visible;

  // 딥링크 ?sowId= → 로드된 목록에서 해당 모돈 자동 선택(알림 액션 연결, C2).
  useEffect(() => {
    if (!sowIdParam || selectedSow) return;
    const found = allSows.find((s) => s.id === sowIdParam);
    if (found) setSelectedSow(found);
  }, [sowIdParam, allSows, selectedSow]);

  // 수정/삭제 후 목록이 refetch되면 선택된 모돈의 상태/산차도 최신으로 동기화(헤더 배지 stale 방지).
  useEffect(() => {
    if (!selectedSow) return;
    const fresh = allSows.find((s) => s.id === selectedSow.id);
    if (fresh && (fresh.status !== selectedSow.status || fresh.parity !== selectedSow.parity)) {
      setSelectedSow(fresh);
    }
  }, [allSows, selectedSow]);

  const handleSaved = (msg: string, sowId: string, goNext: boolean, insights?: EventInsight[]) => {
    track("event_added", { event_type: eventType });
    setDoneIds((prev) => new Set([...prev, sowId]));
    // 이벤트 저장 후 모돈 상태 배지·최근이벤트 레일이 stale로 남던 버그 수정:
    // sows 전체(목록+상세) + 해당 모돈 이벤트 쿼리 무효화(검색 파라미터 무관 prefix 매칭).
    if (farmId) {
      queryClient.invalidateQueries({ queryKey: queryKeys.sows.all(farmId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.events.matings(farmId, sowId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.events.farrowings(farmId, sowId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.events.weanings(farmId, sowId) });
    }
    setLastSaved(msg);
    setLastInsights(insights ?? []);   // 인사이트는 다음 저장 전까지 유지(경고 놓치지 않게)
    if (goNext) {
      const currentIndex = sows.findIndex((s) => s.id === sowId);
      const next = sows[currentIndex + 1];
      setSelectedSow(next ?? null);
    }
    setTimeout(() => setLastSaved(null), 3000);
  };

  if (!farmId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-text3">{t("selectFarm")}</p>
      </div>
    );
  }

  // 권한 게이트: 이벤트 입력은 OWNER/MANAGER/WORKER만. 읽기전용(VIEWER/VET)엔 안내.
  if (!canEntry(role)) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-center gap-3 px-6">
        <div className="w-14 h-14 rounded-2xl bg-bg2 border border-border flex items-center justify-center text-text3">
          <PiggyBank size={28} />
        </div>
        <p className="text-sm font-bold text-text1">{t("readOnlyTitle")}</p>
        <p className="text-xs text-text3 max-w-xs">{t("readOnlyDesc")}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col md:flex-row h-[calc(100vh-3.5rem)] pb-16 md:pb-0">
      {/* ── LEFT: Sow list ───────────────────────────────────────── */}
      <div className="w-full md:w-72 shrink-0 flex flex-col max-h-[38vh] md:max-h-none border-b md:border-b-0 md:border-r border-border bg-surface">
        <div className="px-4 py-3 border-b border-border">
          <h1 className="text-sm font-extrabold tracking-tight mb-2">{t("eventRecord")}</h1>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm outline-none focus:border-primary transition"
          />
        </div>
        <div className="flex-1 overflow-y-auto">
          {sows.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-text3 text-xs gap-2">
              <PiggyBank size={28} className="text-text3" />
              <span>{t("emptyNoSows")}</span>
            </div>
          ) : (
            sows.map((sow) => {
              const isSelected = selectedSow?.id === sow.id;
              const isDone = doneIds.has(sow.id);
              return (
                <button
                  key={sow.id}
                  onClick={() => { setSelectedSow(sow); setLastInsights([]); }}
                  className={`w-full flex items-center gap-3 px-4 py-3 border-b border-border text-left transition ${
                    isSelected
                      ? "bg-primary/5 border-l-2 border-l-primary"
                      : "hover:bg-background"
                  }`}
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-bold font-mono shrink-0 ${
                    isDone ? "bg-green-100 text-success" : "bg-navy/10 text-navy"
                  }`}>
                    {isDone ? <Check size={14} /> : sow.ear_tag.slice(0, 2)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold font-mono text-text truncate">{sow.ear_tag}</div>
                    <div className="text-[11px] text-text3">{t("paritySuffix", { n: sow.parity })}</div>
                  </div>
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${STATUS_BADGE[sow.status]}`}>
                    {tStatus(sow.status)}
                  </span>
                </button>
              );
            })
          )}
          {hasMore && (
            <button
              onClick={() => setVisible((v) => v + PAGE_SIZE)}
              className="w-full py-2.5 text-xs font-semibold text-primary hover:bg-primary/5 transition border-b border-border"
            >
              {t("loadMore", { n: allSows.length - visible })}
            </button>
          )}
        </div>
        <div className="px-4 py-2 border-t border-border">
          <p className="text-[11px] text-text3 font-mono">{t("doneCount", { done: doneIds.size, total: allSows.length })}</p>
        </div>
      </div>

      {/* ── RIGHT: Event drawer ──────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {lastSaved && (
          <div className="mx-6 mt-4 px-4 py-2.5 bg-green-soft border border-success/30 rounded-xl text-sm text-success font-medium flex items-center gap-1.5">
            <Check size={14} /> {lastSaved}
          </div>
        )}
        {/* 경고/위험 인사이트는 다음 저장/모돈전환 전까지 유지(놓치지 않게) */}
        {lastInsights.length > 0 && (
          <div className="mx-6 mt-2">
            <InsightBanner insights={lastInsights} />
          </div>
        )}
        {/* 이상 없으면 작은 정상요약만 (저장 직후 3초) */}
        {lastSaved && lastInsights.length === 0 && (
          <div className="mx-6 mt-2">
            <InsightBanner insights={[]} savedNoIssue />
          </div>
        )}

        {!selectedSow ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center px-6">
            <div className="w-16 h-16 rounded-2xl bg-surface border border-border flex items-center justify-center text-text3"><PiggyBank size={28} /></div>
            <div>
              <p className="text-base font-bold text-text1">{t("selectSowTitle")}</p>
              <p className="text-xs text-text3 mt-1">{t("selectSowDesc")}</p>
            </div>
            {/* 입력 가능한 이벤트 미리보기 — 모돈 선택 후 활성화됨 */}
            <div className="flex flex-wrap gap-2 justify-center max-w-md mt-1">
              {EVENT_TYPES.map((et) => (
                <span
                  key={et.value}
                  className="px-3 py-1.5 rounded-full text-xs font-semibold border"
                  style={{ background: et.bg, borderColor: et.color, color: et.color }}
                >
                  {t(et.labelKey)}
                </span>
              ))}
            </div>
            <p className="text-[11px] text-text3 mt-1">{t("selectSowHint")}</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Sow header */}
            <div className="px-6 py-4 border-b border-border flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-navy/10 flex items-center justify-center font-bold font-mono text-navy text-sm">
                {selectedSow.ear_tag.slice(0, 2)}
              </div>
              <div className="flex-1">
                <div className="text-base font-extrabold font-mono tracking-tight">{selectedSow.ear_tag}</div>
                <div className="text-xs text-text3">{t("paritySuffix", { n: selectedSow.parity })} · <span className={`font-semibold ${STATUS_BADGE[selectedSow.status].split(" ")[1]}`}>{tStatus(selectedSow.status)}</span></div>
              </div>
              <button
                onClick={() => setSelectedSow(null)}
                className="w-8 h-8 rounded-lg border border-border flex items-center justify-center text-text3 hover:bg-border transition"
              ><X size={14} aria-hidden /></button>
            </div>

            {/* Event type chips */}
            <div className="px-6 py-3 border-b border-border flex gap-2 flex-wrap">
              {EVENT_TYPES.map((et) => (
                <button
                  key={et.value}
                  onClick={() => setEventType(et.value)}
                  data-testid={`event-tab-${et.value}`}
                  style={eventType === et.value
                    ? { background: et.bg, borderColor: et.color, color: et.color }
                    : undefined
                  }
                  className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition ${
                    eventType === et.value
                      ? "border-current"
                      : "border-border bg-surface text-text3 hover:bg-border"
                  }`}
                >
                  {t(et.labelKey)}
                </button>
              ))}
            </div>

            {/* Form area — 2열: 입력 폼 | 모돈 컨텍스트 레일 (우측 빈공간 채움) */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,34rem)_minmax(0,1fr)] gap-6 items-start">
                <div className="min-w-0">
                  {eventType === "farrowing" && (
                    <FarrowingPanel farmId={farmId} sow={selectedSow} onSaved={handleSaved} />
                  )}
                  {eventType === "mating" && (
                    <MatingPanel farmId={farmId} sow={selectedSow} onSaved={handleSaved} />
                  )}
                  {eventType === "weaning" && (
                    <WeaningPanel farmId={farmId} sow={selectedSow} onSaved={handleSaved} />
                  )}
                  {eventType === "preg_check" && (
                    <PregnancyCheckPanel farmId={farmId} sow={selectedSow} onSaved={handleSaved} />
                  )}
                  {eventType === "repro" && (
                    <ReproPanel farmId={farmId} sow={selectedSow} onSaved={handleSaved} />
                  )}
                  {eventType === "cull" && (
                    <CullPanel farmId={farmId} sow={selectedSow} onSaved={handleSaved} />
                  )}
                  {eventType === "piglet_death" && (
                    <PigletDeathPanel farmId={farmId} sow={selectedSow} onSaved={handleSaved} />
                  )}
                  {eventType === "foster" && (
                    <FosterPanel farmId={farmId} sow={selectedSow} onSaved={handleSaved} />
                  )}
                </div>

                {/* 우측 컨텍스트 레일 — 이 모돈의 최근 기록(입력 맥락) */}
                <aside className="min-w-0">
                  <RecentEventsSection
                    farmId={farmId}
                    sowId={selectedSow.id}
                    onChanged={() => {
                      // 수정/삭제 시 서버에서 모돈 상태가 롤백되므로 좌측 목록·상태배지도 갱신
                      // (RecentEventsSection 자체는 events + sows.detail만 무효화 → 목록 stale 버그 수정)
                      queryClient.invalidateQueries({ queryKey: queryKeys.sows.all(farmId) });
                    }}
                  />
                </aside>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Farrowing Panel ──────────────────────────────────────────────────────────

function FarrowingPanel({ farmId, sow, onSaved }: PanelProps) {
  const t = useTranslations("record");
  const tv = useTranslations("validation");
  const [total, setTotal] = useState(0);
  const [still, setStill] = useState(0);
  const [mummy, setMummy] = useState(0);
  const [weight, setWeight] = useState(1.4);
  const [unit, setUnit] = useState<"kg" | "lbs">("kg");
  const [difficulty, setDifficulty] = useState<"NORMAL" | "ASSISTED" | "DIFFICULT">("NORMAL");
  const [date, setDate] = useState(today());
  const [error, setError] = useState<string | null>(null);

  const alive = Math.max(0, total - still - mummy);
  const hasError = (still + mummy) > total;

  const mutation = useMutation({
    mutationFn: (goNext: boolean) =>
      eventsApi.farrowings.create(farmId, {
        sow_id: sow.id,
        farrowing_date: date,
        born_alive: alive,
        stillborn: still,
        mummified: mummy,
        // 입력단위(kg/lbs) → 저장은 항상 kg. 스텝퍼로 수집한 평균 생시체중 누락 버그 수정.
        avg_birth_weight_kg: weight > 0 ? (unit === "lbs" ? +(weight / 2.20462).toFixed(3) : weight) : undefined,
        // UI 난이도(NORMAL/ASSISTED/DIFFICULT) → 백엔드 farrowing_ease(EASY/ASSISTED/DIFFICULT)
        farrowing_ease: difficulty === "NORMAL" ? "EASY" : difficulty,
      } as CreateFarrowingRequest).then((resp) => ({ goNext, insights: resp.insights })),
    onSuccess: ({ goNext, insights }) => {
      onSaved(t("savedFarrowing", { tag: sow.ear_tag, n: alive }), sow.id, goNext, insights);
      setTotal(0); setStill(0); setMummy(0); setWeight(1.4);
      setDifficulty("NORMAL"); setDate(today()); setError(null);
    },
    onError: (err: unknown) => setError(apiError(err, t("errGeneric"))),
  });

  function submit(goNext: boolean) {
    const err = firstError(farrowingSchema, {
      farrowing_date: date, total_born: total, born_alive: alive,
      stillborn: still, mummified: mummy, avg_birth_weight_kg: weight,
    }, tv);
    if (err) { setError(err); return; }
    mutation.mutate(goNext);
  }

  return (
    <div className="max-w-lg space-y-4">
      <Lifecycle steps={[t("tabMating"), t("lcGest"), t("tabFarrowing"), t("tabWeaning")]} active={2} />
      <SowChip tag={sow.ear_tag} meta={sow.breed ?? undefined} tone="brand" />

      <Group label={t("farrowDate")}>
        <DateField value={date} onChange={setDate} />
      </Group>

      {/* 산자수 스텝퍼 (testid 유지) */}
      <Group label={t("litterCounts")}>
        <div className="-my-1 divide-y divide-border">
          <Stepper label={t("totalBorn")} sub="Total born" value={total} onChange={setTotal} max={35} />
          <Stepper label={t("stillborn")} sub="Stillborn" value={still} onChange={setStill} colorClass="text-danger" />
          <Stepper label={t("mummified")} sub="Mummified" value={mummy} onChange={setMummy} colorClass="text-warning" />
        </div>
      </Group>

      {/* 실산자 자동계산 히어로 */}
      <AutoCalc
        label={t("bornAliveAuto")}
        sub={hasError ? t("errExceed") : t("formula")}
        value={alive}
        error={hasError}
        tone="brand"
      />

      {/* 평균 생시체중 */}
      <Group label={t("avgBirthWeight")}>
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-text2">kg / lbs</span>
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => setWeight((w) => Math.max(0, +(w - 0.1).toFixed(1)))}
              className="w-10 h-10 rounded-[9px] border border-border-strong bg-surface text-text2 text-lg flex items-center justify-center hover:bg-bg2 transition">−</button>
            <span className="min-w-[52px] text-center text-xl font-bold font-mono">{weight.toFixed(1)}</span>
            <button type="button" onClick={() => setWeight((w) => +(w + 0.1).toFixed(1))}
              className="w-10 h-10 rounded-[9px] bg-text text-white text-lg flex items-center justify-center hover:opacity-90 transition">+</button>
            <div className="flex bg-surface3 rounded-md overflow-hidden border border-border p-0.5">
              {(["kg", "lbs"] as const).map((u) => (
                <button key={u} type="button" onClick={() => setUnit(u)}
                  className={`px-3 py-1.5 text-xs font-bold font-mono rounded transition ${unit === u ? "bg-text text-white" : "text-muted"}`}>{u}</button>
              ))}
            </div>
          </div>
        </div>
      </Group>

      {/* 분만 난이도 */}
      <Group label={t("difficulty")}>
        <Segmented<"NORMAL" | "ASSISTED" | "DIFFICULT">
          value={difficulty}
          options={[{ v: "NORMAL", l: t("diffNormal") }, { v: "ASSISTED", l: t("diffAssisted") }, { v: "DIFFICULT", l: t("diffDifficult") }]}
          onChange={setDifficulty} />
      </Group>

      {/* 양자(cross-foster) CTA — forest/green */}
      <button type="button"
        className="w-full bg-green-soft border border-dashed border-success/40 rounded-[13px] px-4 py-3 flex items-center gap-3 hover:opacity-90 transition">
        <div className="w-8 h-8 rounded-lg bg-success flex items-center justify-center text-white text-sm font-bold flex-shrink-0">+</div>
        <div className="flex-1 text-left">
          <div className="text-sm font-semibold text-success">{t("fosterTitle")}</div>
          <div className="text-[11px] text-muted mt-0.5">{t("fosterDesc")}</div>
        </div>
        <span className="text-success text-xs">›</span>
      </button>

      {error && <ValidationBanner tone="red" title={error} />}

      <RecordFooter>
        <button type="button" disabled={hasError || total === 0 || mutation.isPending} onClick={() => submit(false)}
          data-testid="event-save"
          className="px-4 py-2.5 rounded-[9px] border border-border-strong text-text2 text-sm font-semibold bg-surface hover:bg-bg2 disabled:opacity-50 transition inline-flex items-center gap-1.5">
          <Check size={14} /> {t("save")}
        </button>
        <button type="button" disabled={hasError || total === 0 || mutation.isPending} onClick={() => submit(true)}
          className="px-4 py-2.5 rounded-[9px] bg-success text-white text-sm font-bold hover:opacity-90 disabled:opacity-50 transition">
          {mutation.isPending ? t("saving") : t("saveNext")}
        </button>
      </RecordFooter>
    </div>
  );
}

// ─── Mating Panel ─────────────────────────────────────────────────────────────

function MatingPanel({ farmId, sow, onSaved }: PanelProps) {
  const t = useTranslations("record");
  const tv = useTranslations("validation");
  const [form, setForm] = useState<CreateMatingRequest>({
    sow_id: sow.id, mating_date: today(), mating_type: "AI", semen_batch: "", notes: "",
  });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (goNext: boolean) =>
      eventsApi.matings.create(farmId, { ...form, sow_id: sow.id }).then((resp) => ({ goNext, insights: resp.insights })),
    onSuccess: ({ goNext, insights }) => {
      onSaved(t("savedMating", { tag: sow.ear_tag }), sow.id, goNext, insights);
      setForm({ sow_id: sow.id, mating_date: today(), mating_type: "AI", semen_batch: "", notes: "" });
      setError(null);
    },
    onError: (err: unknown) => setError(apiError(err, t("errGeneric"))),
  });

  function submit(goNext: boolean) {
    const err = firstError(matingSchema, { mating_date: form.mating_date }, tv);
    if (err) { setError(err); return; }
    mutation.mutate(goNext);
  }

  return (
    <div className="max-w-lg space-y-4">
      <Lifecycle steps={[t("tabMating"), t("lcGest"), t("tabFarrowing"), t("tabWeaning")]} active={0} />
      <SowChip tag={sow.ear_tag} meta={sow.breed ?? undefined} tone="brand" />

      <Group label={t("matingInfo")} accent="brand">
        <DateField label={t("matingDate")} value={form.mating_date}
          onChange={(v) => setForm((f) => ({ ...f, mating_date: v }))} />
        <Segmented<"AI" | "NATURAL">
          label={t("matingMethod")} value={form.mating_type}
          options={[{ v: "AI", l: t("methodAI") }, { v: "NATURAL", l: t("methodNatural") }]}
          onChange={(v) => setForm((f) => ({ ...f, mating_type: v }))} />
        <Field label={t("semenNo")}>
          <input value={form.semen_batch ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, semen_batch: e.target.value }))}
            placeholder={t("phSemen")} className="input" />
        </Field>
        <Field label={t("note")}>
          <input value={form.notes ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            className="input" />
        </Field>
      </Group>

      {error && <ValidationBanner tone="red" title={error} />}

      <RecordFooter>
        <button type="button" disabled={mutation.isPending} onClick={() => submit(false)}
          data-testid="event-save"
          className="px-4 py-2.5 rounded-[9px] border border-border-strong text-text2 text-sm font-semibold bg-surface hover:bg-bg2 disabled:opacity-50 transition inline-flex items-center gap-1.5">
          <Check size={14} /> {t("save")}
        </button>
        <button type="button" disabled={mutation.isPending} onClick={() => submit(true)}
          className="px-4 py-2.5 rounded-[9px] bg-success text-white text-sm font-bold hover:opacity-90 disabled:opacity-50 transition">
          {mutation.isPending ? t("saving") : t("saveNext")}
        </button>
      </RecordFooter>
    </div>
  );
}

// ─── Weaning Panel ────────────────────────────────────────────────────────────

function WeaningPanel({ farmId, sow, onSaved }: PanelProps) {
  const t = useTranslations("record");
  const tv = useTranslations("validation");
  const [count, setCount] = useState(0);
  const [weight, setWeight] = useState("");
  const [date, setDate] = useState(today());
  const [partial, setPartial] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (goNext: boolean) =>
      eventsApi.weanings.create(farmId, {
        sow_id: sow.id, weaning_date: date, weaned_count: count,
        avg_weaning_weight_kg: weight ? Number(weight) : undefined,
        is_partial: partial,
      } as CreateWeaningRequest).then((resp) => ({ goNext, insights: resp.insights })),
    onSuccess: ({ goNext, insights }) => {
      onSaved(t("savedWeaning", { tag: sow.ear_tag, n: count }), sow.id, goNext, insights);
      setCount(0); setWeight(""); setDate(today()); setPartial(false); setError(null);
    },
    onError: (err: unknown) => setError(apiError(err, t("errGeneric"))),
  });

  function submit(goNext: boolean) {
    const err = firstError(weaningSchema, {
      weaning_date: date, weaned_count: count,
      avg_weaning_weight_kg: weight ? Number(weight) : undefined,
    }, tv);
    if (err) { setError(err); return; }
    mutation.mutate(goNext);
  }

  return (
    <div className="max-w-lg space-y-4">
      <Lifecycle steps={[t("tabMating"), t("lcGest"), t("tabFarrowing"), t("tabWeaning")]} active={3} />
      <SowChip tag={sow.ear_tag} meta={sow.breed ?? undefined} tone="brand" />

      <Group label={t("weaningDate")}>
        <DateField value={date} onChange={setDate} />
      </Group>

      <Group label={t("weanedCount")}>
        <div className="-my-1">
          <Stepper label={t("weanedCount")} sub="Weaned count" value={count} onChange={setCount} colorClass="text-success" />
        </div>
      </Group>

      <Group label={t("avgWeanWeight")}>
        <input type="number" step="0.1" min={0} value={weight}
          onChange={(e) => setWeight(e.target.value)}
          placeholder={t("phWeanWeight")} className="input" />
      </Group>

      {/* 부분이유 토글 */}
      <Group>
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input type="checkbox" checked={partial} onChange={(e) => setPartial(e.target.checked)}
            className="w-4 h-4 accent-[var(--color-brand)]" />
          <span className="text-sm font-semibold text-text2">{t("partialWeaning")}</span>
        </label>
        <p className="text-[11px] text-muted">{partial ? t("partialHint") : t("finalHint")}</p>
      </Group>

      {error && <ValidationBanner tone="red" title={error} />}

      <RecordFooter>
        <button type="button" disabled={count < 1 || mutation.isPending} onClick={() => submit(false)}
          data-testid="event-save"
          className="px-4 py-2.5 rounded-[9px] border border-border-strong text-text2 text-sm font-semibold bg-surface hover:bg-bg2 disabled:opacity-50 transition inline-flex items-center gap-1.5">
          <Check size={14} /> {t("save")}
        </button>
        <button type="button" disabled={count < 1 || mutation.isPending} onClick={() => submit(true)}
          className="px-4 py-2.5 rounded-[9px] bg-success text-white text-sm font-bold hover:opacity-90 disabled:opacity-50 transition">
          {mutation.isPending ? t("saving") : t("saveNext")}
        </button>
      </RecordFooter>
    </div>
  );
}

// ─── Pregnancy Check Panel (D1) ───────────────────────────────────────────────

const PREG_RESULT_KEYS = [
  { value: "POSITIVE",  key: "pcPositive" },
  { value: "NEGATIVE",  key: "pcNegative" },
  { value: "UNCERTAIN", key: "pcUncertain" },
];

function PregnancyCheckPanel({ farmId, sow, onSaved }: PanelProps) {
  const t = useTranslations("record");
  const [form, setForm] = useState<CreatePregnancyCheckRequest>({
    sow_id: sow.id, check_date: today(), result: "POSITIVE",
  });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (goNext: boolean) =>
      eventsApi.pregnancyChecks
        .create(farmId, { ...form, sow_id: sow.id })
        .then((resp) => ({ goNext, insights: resp.insights })),
    onSuccess: ({ goNext, insights }) => {
      const k = PREG_RESULT_KEYS.find((x) => x.value === form.result)?.key;
      onSaved(t("savedPregCheck", { tag: sow.ear_tag, label: k ? t(k) : "" }), sow.id, goNext, insights);
      setForm({ sow_id: sow.id, check_date: today(), result: "POSITIVE" });
      setError(null);
    },
    onError: (err: unknown) => setError(apiError(err, t("errGeneric"))),
  });

  return (
    <div className="max-w-lg space-y-4">
      <SowChip tag={sow.ear_tag} meta={sow.breed ?? undefined} tone="brand" />
      <Group label={t("pcResult")}>
        <p className="text-xs text-muted -mt-1">{t("pcDesc")}</p>
        <Field label={t("pcResult")}>
          <select value={form.result}
            onChange={(e) => setForm((f) => ({ ...f, result: e.target.value as CreatePregnancyCheckRequest["result"] }))}
            className="input" data-testid="pc-result">
            {PREG_RESULT_KEYS.map((r) => <option key={r.value} value={r.value}>{t(r.key)}</option>)}
          </select>
        </Field>
        {form.result === "NEGATIVE" && (
          <p className="text-xs text-warning">{t("pcNegativeHint")}</p>
        )}
        <DateField label={t("pcCheckDate")} value={form.check_date}
          onChange={(v) => setForm((f) => ({ ...f, check_date: v }))} />
        <Field label={t("pcDaysAfter")}>
          <input type="number" min={1} max={120} value={form.days_after_mating ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, days_after_mating: e.target.value ? Number(e.target.value) : undefined }))}
            placeholder={t("pcDaysAfterPh")} className="input" />
        </Field>
        <Field label={t("pcMethod")}>
          <select value={form.method ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, method: (e.target.value || undefined) as CreatePregnancyCheckRequest["method"] }))}
            className="input">
            <option value="">—</option>
            <option value="ULTRASOUND">{t("pcmUltrasound")}</option>
            <option value="DOPPLER">{t("pcmDoppler")}</option>
            <option value="VISUAL">{t("pcmVisual")}</option>
            <option value="BLOOD">{t("pcmBlood")}</option>
            <option value="OTHER">{t("pcmOther")}</option>
          </select>
        </Field>
      </Group>
      {error && <ValidationBanner tone="red" title={error} />}
      <RecordFooter>
        <button type="button" disabled={mutation.isPending} onClick={() => mutation.mutate(false)}
          data-testid="event-save"
          className="px-4 py-2.5 rounded-[9px] border border-border-strong text-text2 text-sm font-semibold bg-surface hover:bg-bg2 disabled:opacity-50 transition inline-flex items-center gap-1.5">
          <Check size={14} /> {t("save")}
        </button>
        <button type="button" disabled={mutation.isPending} onClick={() => mutation.mutate(true)}
          className="px-4 py-2.5 rounded-[9px] bg-success text-white text-sm font-bold hover:opacity-90 disabled:opacity-50 transition">
          {mutation.isPending ? t("saving") : t("saveNext")}
        </button>
      </RecordFooter>
    </div>
  );
}

// ─── Repro Panel ──────────────────────────────────────────────────────────────

const REPRO_TYPE_KEYS = [
  { value: "RETURN_TO_ESTRUS", key: "rRTS" },
  { value: "ABORTION",         key: "rAbortion" },
  { value: "EMPTY",            key: "rEmpty" },
  { value: "INFERTILE",        key: "rInfertile" },
  { value: "HEAT_DETECTED",    key: "rHeat" },
];

function ReproPanel({ farmId, sow, onSaved }: PanelProps) {
  const t = useTranslations("record");
  const [form, setForm] = useState<CreateReproductiveEventRequest>({
    sow_id: sow.id, event_type: "RETURN_TO_ESTRUS", event_date: today(),
  });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (goNext: boolean) =>
      eventsApi.reproductive.create(farmId, { ...form, sow_id: sow.id }).then(() => goNext),
    onSuccess: (goNext) => {
      const k = REPRO_TYPE_KEYS.find((x) => x.value === form.event_type)?.key;
      const label = k ? t(k) : "";
      onSaved(t("savedRepro", { tag: sow.ear_tag, label }), sow.id, goNext);
      setForm({ sow_id: sow.id, event_type: "RETURN_TO_ESTRUS", event_date: today() });
      setError(null);
    },
    onError: (err: unknown) => setError(apiError(err, t("errGeneric"))),
  });

  return (
    <div className="max-w-lg space-y-4">
      <SowChip tag={sow.ear_tag} meta={sow.breed ?? undefined} tone="amber" />
      <Group label={t("eventType")} accent="amber">
        <p className="text-xs text-muted -mt-1">{t("reproDesc")}</p>
        <Field label={t("eventType")}>
          <select value={form.event_type}
            onChange={(e) => setForm((f) => ({ ...f, event_type: e.target.value as CreateReproductiveEventRequest["event_type"] }))}
            className="input">
            {REPRO_TYPE_KEYS.map((rt) => <option key={rt.value} value={rt.value}>{t(rt.key)}</option>)}
          </select>
        </Field>
        <DateField label={t("eventDate")} value={form.event_date}
          onChange={(v) => setForm((f) => ({ ...f, event_date: v }))} />
      </Group>
      {error && <ValidationBanner tone="red" title={error} />}
      <RecordFooter>
        <button type="button" disabled={mutation.isPending} onClick={() => mutation.mutate(false)}
          data-testid="event-save"
          className="px-4 py-2.5 rounded-[9px] border border-border-strong text-text2 text-sm font-semibold bg-surface hover:bg-bg2 disabled:opacity-50 transition inline-flex items-center gap-1.5">
          <Check size={14} /> {t("save")}
        </button>
        <button type="button" disabled={mutation.isPending} onClick={() => mutation.mutate(true)}
          className="px-4 py-2.5 rounded-[9px] bg-success text-white text-sm font-bold hover:opacity-90 disabled:opacity-50 transition">
          {mutation.isPending ? t("saving") : t("saveNext")}
        </button>
      </RecordFooter>
    </div>
  );
}

// ─── Cull Panel ───────────────────────────────────────────────────────────────

const REMOVAL_TYPE_KEYS = [
  { value: "CULLED",   key: "rmCulled" },
  { value: "DEAD",     key: "rmDead" },
  { value: "SOLD",     key: "rmSold" },
  { value: "TRANSFER", key: "rmTransfer" },
];

const REASON_CATEGORY_KEYS = [
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

function CullPanel({ farmId, sow, onSaved }: PanelProps) {
  const t = useTranslations("record");
  const tv = useTranslations("validation");
  const tStatus = useTranslations("sowStatus");
  const queryClient = useQueryClient();
  const [form, setForm] = useState<SowCullRequest>({
    removal_type: "CULLED",
    removal_date: today(),
  });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (goNext: boolean) =>
      sowsApi.cull(farmId, sow.id, form).then(() => goNext),
    onSuccess: (goNext) => {
      const label = tStatus(form.removal_type);
      onSaved(t("savedCull", { tag: sow.ear_tag, label }), sow.id, goNext);
      queryClient.invalidateQueries({ queryKey: queryKeys.sows.list(farmId, {}) });
      setForm({ removal_type: "CULLED", removal_date: today() });
      setError(null);
    },
    onError: (err: unknown) => setError(apiError(err, t("errGeneric"))),
  });

  function submit(goNext: boolean) {
    const err = firstError(cullSchema, {
      removal_type: form.removal_type, removal_date: form.removal_date,
    }, tv);
    if (err) { setError(err); return; }
    mutation.mutate(goNext);
  }

  return (
    <div className="max-w-lg space-y-4">
      <SowChip tag={sow.ear_tag} meta={sow.breed ?? undefined} tone="red" />
      <ValidationBanner tone="red" title={t("cullWarn")} />
      <Group label={t("removalType")} accent="red">
        <Field label={t("removalType")}>
          <select value={form.removal_type}
            onChange={(e) => setForm((f) => ({ ...f, removal_type: e.target.value as SowCullRequest["removal_type"] }))}
            className="input">
            {REMOVAL_TYPE_KEYS.map((r) => <option key={r.value} value={r.value}>{t(r.key)}</option>)}
          </select>
        </Field>
        <DateField label={t("removalDate")} value={form.removal_date}
          onChange={(v) => setForm((f) => ({ ...f, removal_date: v }))} />
        <Field label={t("reasonCat")}>
          <select value={form.reason_category ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, reason_category: (e.target.value || undefined) as SowCullRequest["reason_category"] }))}
            className="input">
            <option value="">{t("selectNone")}</option>
            {REASON_CATEGORY_KEYS.map((r) => <option key={r.value} value={r.value}>{t(r.key)}</option>)}
          </select>
        </Field>
        <Field label={t("reasonDetail")}>
          <input value={form.reason_detail ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, reason_detail: e.target.value || undefined }))}
            placeholder={t("phReasonDetail")} className="input" />
        </Field>
      </Group>
      {error && <ValidationBanner tone="red" title={error} />}
      <RecordFooter>
        {/* 위험 동작 → 저장 버튼 danger red */}
        <button type="button" disabled={!form.removal_date || mutation.isPending} onClick={() => submit(false)}
          data-testid="event-save"
          className="px-4 py-2.5 rounded-[9px] bg-danger text-white text-sm font-bold hover:opacity-90 disabled:opacity-50 transition">
          {mutation.isPending ? t("saving") : t("save")}
        </button>
      </RecordFooter>
    </div>
  );
}

// ─── Piglet Death Panel ───────────────────────────────────────────────────────

const PIGLET_DEATH_REASON_KEYS = [
  { value: "CRUSHING",    key: "pcCrushing" },
  { value: "SCOURS",      key: "pcScours" },
  { value: "STARVATION",  key: "pcStarvation" },
  { value: "CONGENITAL",  key: "pcCongenital" },
  { value: "HYPOTHERMIA", key: "pcHypothermia" },
  { value: "OTHER",       key: "pcOther" },
];

function PigletDeathPanel({ farmId, sow, onSaved }: PanelProps) {
  const t = useTranslations("record");
  const tv = useTranslations("validation");
  const queryClient = useQueryClient();
  const [form, setForm] = useState<CreatePigletEventRequest>({
    sow_id: sow.id,
    event_date: today(),
    event_type: "DEATH",
    piglet_count: 1,
  });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (goNext: boolean) =>
      eventsApi.pigletEvents.create(farmId, { ...form, sow_id: sow.id }).then(() => goNext),
    onSuccess: (goNext) => {
      onSaved(t("savedPigletDeath", { tag: sow.ear_tag, n: form.piglet_count }), sow.id, goNext);
      queryClient.invalidateQueries({ queryKey: queryKeys.sows.list(farmId, {}) });
      setForm({ sow_id: sow.id, event_date: today(), event_type: "DEATH", piglet_count: 1 });
      setError(null);
    },
    onError: (err: unknown) => setError(apiError(err, t("errGeneric"))),
  });

  function submit(goNext: boolean) {
    const err = firstError(pigletEventSchema, {
      event_type: form.event_type, event_date: form.event_date, piglet_count: form.piglet_count,
    }, tv);
    if (err) { setError(err); return; }
    mutation.mutate(goNext);
  }

  return (
    <div className="max-w-lg space-y-4">
      <SowChip tag={sow.ear_tag} meta={sow.breed ?? undefined} tone="red" />
      <ValidationBanner tone="amber" title={t("pdDesc")} />
      <Group label={t("deathDate")} accent="red">
        <DateField label={t("deathDate")} value={form.event_date}
          onChange={(v) => setForm((f) => ({ ...f, event_date: v }))} />
        <Field label={t("deathCount")}>
          <div className="-my-1">
            <Stepper label="" value={form.piglet_count} onChange={(v) => setForm((f) => ({ ...f, piglet_count: v }))}
              min={1} max={30} colorClass="text-danger" />
          </div>
        </Field>
        <Field label={t("deathCause")}>
          <select value={form.reason ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, reason: (e.target.value || undefined) as CreatePigletEventRequest["reason"] }))}
            className="input">
            <option value="">{t("selectNone")}</option>
            {PIGLET_DEATH_REASON_KEYS.map((r) => <option key={r.value} value={r.value}>{t(r.key)}</option>)}
          </select>
        </Field>
        <Field label={t("memo")}>
          <input value={form.notes ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value || undefined }))}
            placeholder={t("phMemo")} className="input" />
        </Field>
      </Group>
      {error && <ValidationBanner tone="red" title={error} />}
      <RecordFooter>
        <button type="button" disabled={!form.event_date || mutation.isPending} onClick={() => submit(false)}
          data-testid="event-save"
          className="px-4 py-2.5 rounded-[9px] border border-border-strong text-text2 text-sm font-semibold bg-surface hover:bg-bg2 disabled:opacity-50 transition inline-flex items-center gap-1.5">
          <Check size={14} /> {t("save")}
        </button>
        <button type="button" disabled={!form.event_date || mutation.isPending} onClick={() => submit(true)}
          className="px-4 py-2.5 rounded-[9px] bg-success text-white text-sm font-bold hover:opacity-90 disabled:opacity-50 transition">
          {mutation.isPending ? t("saving") : t("saveNext")}
        </button>
      </RecordFooter>
    </div>
  );
}


/**
 * 양자(cross-foster) 입력 — FOSTER_IN / FOSTER_OUT.
 *
 * 왜 이제야 붙는가: 스키마(eventSchemas.ts)·API(POST /piglet_events)·백엔드 검증은
 * 진작 있었는데 **웹에 패널이 없어서** 실고객이 유모돈을 기록할 방법이 없었다.
 * 즉 프로덕션에 FOSTER 이벤트가 0건인 것은 "안 한다"가 아니라 "못 한다"였다.
 *
 * ★ 이 갭이 KPI 정합성과 연결된다 — 포유폐사율 경로 ②는
 *   (born_alive − weaned) / born_alive 라서, 유모돈이 기록되지 않으면 전출 자돈이
 *   폐사로 계상된다. 지금은 유모돈 0건이라 발현되지 않을 뿐 잠복해 있다.
 *
 * 백엔드가 이미 강제하는 것(event_service.py:768~)을 UI 에서 **먼저** 막는다 —
 * 서버 에러로 알려주는 것보다 선택 자체를 못 하게 하는 편이 낫다.
 *   · target_sow_id 필수 · 자기 자신 금지 · 상대 모돈은 LACTATING
 *   · FOSTER_IN 과혼잡 상한 / FOSTER_OUT 음수 가드는 서버 판정(UI 는 에러만 표시)
 */
function FosterPanel({ farmId, sow, onSaved }: PanelProps) {
  const t = useTranslations("record");
  const tv = useTranslations("validation");
  const queryClient = useQueryClient();
  const [form, setForm] = useState<CreatePigletEventRequest>({
    sow_id: sow.id,
    event_date: today(),
    event_type: "FOSTER_OUT",
    piglet_count: 1,
  });
  const [error, setError] = useState<string | null>(null);

  // 상대 후보 = 같은 농장의 포유 중 모돈에서 자기 자신 제외.
  const { data: lactating } = useQuery({
    queryKey: queryKeys.sows.list(farmId, { status: "LACTATING", per_page: 200 }),
    queryFn: () => sowsApi.list(farmId, { status: "LACTATING", per_page: 200 }),
    enabled: !!farmId,
  });
  const targets = (lactating?.items ?? []).filter((s) => s.id !== sow.id);

  // 모돈을 바꾸면 이전 선택이 남지 않게 초기화(다른 농장·다른 상태일 수 있다).
  useEffect(() => {
    setForm((f) => ({ ...f, sow_id: sow.id, target_sow_id: undefined }));
  }, [sow.id]);

  const mutation = useMutation({
    mutationFn: (goNext: boolean) =>
      eventsApi.pigletEvents.create(farmId, { ...form, sow_id: sow.id }).then(() => goNext),
    onSuccess: (goNext) => {
      onSaved(t("savedFoster", { tag: sow.ear_tag, n: form.piglet_count }), sow.id, goNext);
      queryClient.invalidateQueries({ queryKey: queryKeys.sows.list(farmId, {}) });
      setForm({ sow_id: sow.id, event_date: today(), event_type: "FOSTER_OUT", piglet_count: 1 });
      setError(null);
    },
    onError: (err: unknown) => setError(apiError(err, t("errGeneric"))),
  });

  function submit(goNext: boolean) {
    const err = firstError(pigletEventSchema, {
      event_type: form.event_type, event_date: form.event_date,
      piglet_count: form.piglet_count, target_sow_id: form.target_sow_id,
    }, tv);
    if (err) { setError(err); return; }
    mutation.mutate(goNext);
  }

  const canSave = !!form.event_date && !!form.target_sow_id && !mutation.isPending;

  return (
    <div className="max-w-lg space-y-4">
      <SowChip tag={sow.ear_tag} meta={sow.breed ?? undefined} tone="blue" />
      <ValidationBanner tone="amber" title={t("fosterDesc")} />
      <Group label={t("fosterDate")} accent="blue">
        <Field label={t("fosterDirection")}>
          <select value={form.event_type}
            onChange={(e) => setForm((f) => ({ ...f, event_type: e.target.value as CreatePigletEventRequest["event_type"] }))}
            className="input" data-testid="foster-direction">
            <option value="FOSTER_OUT">{t("fosterOut")}</option>
            <option value="FOSTER_IN">{t("fosterIn")}</option>
          </select>
        </Field>
        <DateField label={t("fosterDate")} value={form.event_date}
          onChange={(v) => setForm((f) => ({ ...f, event_date: v }))} />
        <Field label={t("fosterCount")}>
          <div className="-my-1">
            <Stepper label="" value={form.piglet_count}
              onChange={(v) => setForm((f) => ({ ...f, piglet_count: v }))}
              min={1} max={30} colorClass="text-primary" />
          </div>
        </Field>
        <Field label={t("fosterTarget")}>
          <select value={form.target_sow_id ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, target_sow_id: e.target.value || undefined }))}
            className="input" disabled={targets.length === 0} data-testid="foster-target">
            <option value="">{targets.length === 0 ? t("fosterNoTarget") : t("selectNone")}</option>
            {targets.map((s) => (
              <option key={s.id} value={s.id}>
                {s.ear_tag}{s.breed ? ` · ${s.breed}` : ""}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-text3">{t("fosterTargetHint")}</p>
        </Field>
      </Group>
      {error && <ValidationBanner tone="red" title={error} />}
      <RecordFooter>
        <button type="button" disabled={!canSave} onClick={() => submit(false)}
          data-testid="event-save"
          className="px-4 py-2.5 rounded-[9px] border border-border-strong text-text2 text-sm font-semibold bg-surface hover:bg-bg2 disabled:opacity-50 transition inline-flex items-center gap-1.5">
          <Check size={14} /> {t("save")}
        </button>
        <button type="button" disabled={!canSave} onClick={() => submit(true)}
          className="px-4 py-2.5 rounded-[9px] bg-success text-white text-sm font-bold hover:opacity-90 disabled:opacity-50 transition">
          {mutation.isPending ? t("saving") : t("saveNext")}
        </button>
      </RecordFooter>
    </div>
  );
}

// ─── Shared UI ────────────────────────────────────────────────────────────────

type PanelProps = {
  farmId: string;
  sow: Sow;
  onSaved: (msg: string, sowId: string, goNext: boolean, insights?: EventInsight[]) => void;
};

function SaveFooter({
  disabled, loading, onSave, onSaveNext,
}: { disabled: boolean; loading: boolean; onSave: () => void; onSaveNext: () => void }) {
  const t = useTranslations("record");
  return (
    <div className="flex gap-2 pt-2">
      <button
        type="button"
        disabled={disabled || loading}
        onClick={onSave}
        data-testid="event-save"
        className="flex-1 bg-surface border border-border text-text2 py-3 rounded-xl text-sm font-semibold disabled:opacity-50 hover:bg-border transition"
      >
        {loading ? t("saving") : t("save")}
      </button>
      <button
        type="button"
        disabled={disabled || loading}
        onClick={onSaveNext}
        className="flex-[1.4] bg-success text-white py-3 rounded-xl text-sm font-bold disabled:opacity-50 hover:opacity-90 transition flex items-center justify-center gap-2"
      >
        {t("saveNext")}
      </button>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-text3 mb-1.5">{label}</label>
      {children}
    </div>
  );
}

function today() {
  // 로컬 캘린더 날짜(YYYY-MM-DD). toISOString(UTC)는 KST 자정 경계에서 하루 밀림 → 로컬 기준 보정.
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function apiError(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string | { msg: string }[] } } })
    ?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(", ");
  return fallback;
}
