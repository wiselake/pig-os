"use client";

/**
 * Record 화면 디자인 키트 — Operational Console (design_handoff).
 * 폼 원자: Lifecycle 리본 · Group 카드 · Segmented · SowChip · ValidationBanner
 *          · AutoCalc 히어로 · RecordFooter(sticky) · SaveHint.
 * 토큰: ink/brand/red + paper/surface. 숫자 mono. 색의미: ink=구조, brand=저장·활성, red=위험.
 */
import type { ReactNode } from "react";
import { AlertTriangle, Check, Calendar, ScanLine, ChevronDown } from "lucide-react";

type Tone = "brand" | "ink" | "red" | "amber" | "blue";
const TONE_TEXT: Record<Tone, string> = {
  brand: "text-success", ink: "text-text", red: "text-danger", amber: "text-warning", blue: "text-blue",
};
const TONE_SOFT: Record<Tone, string> = {
  brand: "bg-green-soft", ink: "bg-surface3", red: "bg-red-soft", amber: "bg-amber-soft", blue: "bg-blue-soft",
};

/** 생애주기 리본 — 교배→임신→분만→이유 중 현재 위치. */
export function Lifecycle({ steps, active }: { steps: string[]; active: number }) {
  return (
    <div className="flex items-center gap-1.5">
      {steps.map((s, i) => {
        const on = i === active, done = i < active;
        return (
          <span key={s} className="flex items-center gap-1.5">
            {i > 0 && <span className={`w-3 h-px ${done ? "bg-success" : "bg-border-strong"}`} />}
            <span
              className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold ${
                on ? "bg-success text-white" : done ? "bg-green-soft text-success" : "bg-surface3 text-faint"
              }`}
            >
              {s}
            </span>
          </span>
        );
      })}
    </div>
  );
}

/** 라벨 그룹 카드 (좌측 accent 바 + 대문자 라벨). */
export function Group({
  label, hint, accent, children, className = "",
}: { label?: string; hint?: string; accent?: Tone; children: ReactNode; className?: string }) {
  return (
    <div className={`relative bg-surface border border-border rounded-[13px] px-4 py-4 flex flex-col gap-3 ${className}`}
      style={{ boxShadow: "var(--shadow-card)" }}>
      {accent && <span className={`absolute left-0 top-3.5 bottom-3.5 w-[3px] rounded-full ${accent === "brand" ? "bg-success" : accent === "blue" ? "bg-blue" : "bg-text"}`} />}
      {label && (
        <div className="flex items-baseline justify-between">
          <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-muted">{label}</div>
          {hint && <div className="text-[11px] text-faint">{hint}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

/** 선택된 모돈 칩 (스캔 결과 표시). */
export function SowChip({ tag, meta, tone = "brand" }: { tag: string; meta?: string; tone?: Tone }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 bg-surface border border-border-strong rounded-[9px]">
      <div className={`w-9 h-9 rounded-md ${TONE_SOFT[tone]} flex items-center justify-center flex-shrink-0`}>
        <ScanLine size={16} className={TONE_TEXT[tone]} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[16px] font-bold text-text tracking-tight">{tag}</span>
          <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-green-soft text-success">scanned</span>
        </div>
        {meta && <div className="text-[11.5px] text-muted mt-0.5 truncate">{meta}</div>}
      </div>
    </div>
  );
}

/** 세그먼트 컨트롤 (활성 = ink). */
export function Segmented<T extends string>({
  label, value, options, onChange,
}: { label?: string; value: T; options: { v: T; l: string }[]; onChange: (v: T) => void }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && <div className="text-[13px] font-semibold text-text2">{label}</div>}
      <div className="flex gap-2">
        {options.map((o) => {
          const on = o.v === value;
          return (
            <button key={o.v} type="button" onClick={() => onChange(o.v)}
              className={`flex-1 px-2 py-2.5 rounded-[9px] text-sm font-semibold border transition ${
                on ? "bg-text text-white border-text" : "bg-surface text-text2 border-border-strong hover:bg-bg2"
              }`}>
              {o.l}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/** 자동계산 히어로 (큰 mono 숫자, 오류 시 red). */
export function AutoCalc({
  label, sub, value, unit, tone = "brand", error,
}: { label: string; sub?: string; value: ReactNode; unit?: string; tone?: Tone; error?: boolean }) {
  const c = error ? "text-danger" : TONE_TEXT[tone];
  return (
    <div className={`flex items-center justify-between rounded-[13px] px-5 py-4 border ${
      error ? "bg-red-soft border-danger/30" : `${TONE_SOFT[tone]} border-success/30`
    }`}>
      <div>
        <div className="flex items-center gap-1.5">
          <span className={`text-[12.5px] font-bold ${c}`}>{label}</span>
          <span className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded ${error ? "bg-red-soft text-danger" : "bg-green-soft text-success"}`}>auto</span>
        </div>
        {sub && <div className="text-[11.5px] text-muted mt-0.5">{sub}</div>}
      </div>
      <div className="flex items-baseline gap-1">
        <span className={`text-[38px] leading-none font-bold font-mono tracking-tight ${c}`}>{value}</span>
        {unit && <span className="text-[13px] text-muted font-semibold">{unit}</span>}
      </div>
    </div>
  );
}

/** 소프트 검증 배너 (amber 경고 / red 차단). */
export function ValidationBanner({
  tone = "amber", title, items,
}: { tone?: "amber" | "red" | "blue"; title: string; items?: string[] }) {
  const tc = tone === "red" ? "text-danger" : tone === "blue" ? "text-blue" : "text-warning";
  const bg = tone === "red" ? "bg-red-soft border-danger/30" : tone === "blue" ? "bg-blue-soft border-blue/30" : "bg-amber-soft border-warning/30";
  return (
    <div className={`flex gap-3 px-4 py-3 rounded-[13px] border ${bg}`}>
      <AlertTriangle size={20} className={`${tc} flex-shrink-0 mt-0.5`} />
      <div className="flex-1">
        <div className={`text-[13px] font-bold ${tc}`}>{title}</div>
        {items && (
          <ul className="mt-1.5 pl-4 list-disc flex flex-col gap-1">
            {items.map((it, i) => <li key={i} className="text-[12.5px] text-text2 leading-relaxed">{it}</li>)}
          </ul>
        )}
      </div>
    </div>
  );
}

/** 날짜 표시 행 (오늘 배지). */
export function DateField({ label, value, onChange }: { label?: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && <div className="text-[13px] font-semibold text-text2">{label}</div>}
      <div className="flex items-center gap-2.5 px-3 py-2.5 bg-surface border border-border-strong rounded-[9px]">
        <Calendar size={16} className="text-muted flex-shrink-0" />
        <input type="date" value={value} onChange={(e) => onChange(e.target.value)}
          className="flex-1 bg-transparent text-[14px] text-text font-medium outline-none font-mono" />
      </div>
    </div>
  );
}

/** 하단 고정 푸터 (좌측 저장힌트 + 우측 액션들). */
export function RecordFooter({ left, children }: { left?: ReactNode; children: ReactNode }) {
  return (
    <div className="flex items-center gap-3 pt-4 mt-2 border-t border-border">
      {left}
      <div className="flex-1" />
      {children}
    </div>
  );
}

export function SaveHint({ state = "saved", label }: { state?: "saved" | "offline"; label: string }) {
  const tone = state === "offline" ? "text-warning" : "text-success";
  return (
    <span className={`inline-flex items-center gap-1.5 text-[12px] font-medium ${tone}`}>
      <Check size={14} /> {label}
    </span>
  );
}

/** 페이지 헤더 (아이콘 칩 + 타이틀 + 라이프사이클). */
export function RecordHeader({
  icon, title, sub, lifecycle, tone = "brand", actions,
}: { icon: ReactNode; title: string; sub?: string; lifecycle?: ReactNode; tone?: Tone; actions?: ReactNode }) {
  return (
    <div className="flex items-start gap-4 pb-4 mb-4 border-b border-border">
      <div className={`w-11 h-11 rounded-[9px] ${TONE_SOFT[tone]} flex items-center justify-center flex-shrink-0 ${TONE_TEXT[tone]}`}>
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2.5 flex-wrap">
          <h1 className="text-[22px] font-bold text-text tracking-tight">{title}</h1>
          {lifecycle}
        </div>
        {sub && <div className="text-[13px] text-muted mt-0.5">{sub}</div>}
      </div>
      {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
    </div>
  );
}

export const ChevDown = ChevronDown;
