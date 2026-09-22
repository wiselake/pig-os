import { ReactNode } from "react";
import { AlertOctagon, Brain, Lightbulb, Sparkles, Zap } from "lucide-react";

// Stat Card
export function Stat({
  label,
  value,
  sub,
  subType = "default",
  aiDot = true,
  valueColor,
}: {
  label: string;
  value: string;
  sub?: string;
  subType?: "up" | "down" | "ai" | "default";
  aiDot?: boolean;
  valueColor?: string;
}) {
  const subColors = {
    up: "text-success",
    down: "text-danger",
    ai: "text-purple",
    default: "text-text3",
  };

  return (
    <div className="bg-surface border border-border rounded-xl p-[18px]">
      <div className="text-[11px] text-text3 mb-1.5 flex items-center gap-1.5">
        {aiDot && (
          <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
        )}
        {label}
      </div>
      <div
        className="font-mono text-[28px] font-extrabold tracking-tight"
        style={valueColor ? { color: valueColor } : {}}
      >
        {value}
      </div>
      {sub && (
        <div className={`font-mono text-[11px] mt-1 ${subColors[subType]}`}>
          {sub}
        </div>
      )}
    </div>
  );
}

// AI Bubble
export function AIBubble({
  label = "AI",
  children,
}: {
  label?: string;
  children: ReactNode;
}) {
  return (
    <div className="bg-green-soft border border-ai-border rounded-xl rounded-bl-sm p-4 mb-3">
      <div className="text-[9px] font-bold tracking-wider uppercase text-success mb-1.5 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
        {label}
      </div>
      <div className="text-[13px] text-text2 leading-relaxed">{children}</div>
    </div>
  );
}

// AI Action Card
export function AIAction({
  priority,
  title,
  desc,
  impact,
  impactNegative = false,
  actionLabel,
  actionHref,
}: {
  priority: "critical" | "high" | "medium" | "insight";
  title: string;
  desc: string;
  impact?: string;
  impactNegative?: boolean;
  actionLabel?: string;
  actionHref?: string;
}) {
  const priorityStyles = {
    critical: { bg: "bg-red-soft", text: "text-danger", Icon: AlertOctagon, label: "Critical" },
    high: { bg: "bg-amber-soft", text: "text-warning", Icon: Zap, label: "High" },
    medium: { bg: "bg-emerald-50", text: "text-primary", Icon: Lightbulb, label: "Optimization" },
    insight: { bg: "bg-green-soft", text: "text-purple", Icon: Sparkles, label: "Prediction" },
  };

  const p = priorityStyles[priority];

  return (
    <div className="bg-surface border border-border rounded-xl p-[18px] mb-3 cursor-pointer transition-all hover:border-primary hover:shadow-[0_2px_12px_rgba(13,124,102,.08)]">
      <span className={`inline-flex items-center gap-1 text-[9px] font-bold tracking-wider uppercase px-2 py-0.5 rounded ${p.bg} ${p.text} mb-2`}>
        <p.Icon size={12} /> {p.label}
      </span>
      <div className="text-sm font-bold mb-1">{title}</div>
      <div className="text-xs text-text2 leading-relaxed mb-2.5">{desc}</div>
      <div className="flex items-center gap-3">
        {impact && (
          <span className={`inline-flex items-center gap-1.5 font-mono text-[11px] font-semibold px-2.5 py-1 rounded-md ${
            impactNegative ? "bg-red-soft text-danger" : "bg-green-soft text-success"
          }`}>
            {impact}
          </span>
        )}
        {actionLabel && (
          <span className="text-[11px] font-semibold text-primary">
            {actionLabel} →
          </span>
        )}
      </div>
    </div>
  );
}

// Tag
export function Tag({
  children,
  color = "green",
}: {
  children: ReactNode;
  color?: "green" | "red" | "yellow" | "blue" | "purple";
}) {
  const colors = {
    green: "bg-green-soft text-success",
    red: "bg-red-soft text-danger",
    yellow: "bg-amber-soft text-warning",
    blue: "bg-green-soft text-blue",
    purple: "bg-green-soft text-purple",
  };

  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${colors[color]}`}>
      {children}
    </span>
  );
}

// Card
export function Card({
  title,
  badge,
  badgeColor,
  children,
  className = "",
}: {
  title?: string;
  badge?: string;
  badgeColor?: "green" | "red" | "yellow" | "blue" | "purple";
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`bg-surface border border-border rounded-xl ${className}`}>
      {title && (
        <div className="px-[18px] py-3.5 text-[13px] font-semibold border-b border-border flex items-center justify-between">
          {title}
          {badge && <Tag color={badgeColor}>{badge}</Tag>}
        </div>
      )}
      <div className="p-[18px]">{children}</div>
    </div>
  );
}

// Pipeline Item
export function PipeItem({
  icon,
  count,
  name,
  active = false,
  aiIcon,
  aiDanger = false,
}: {
  icon: ReactNode;
  count: number;
  name: string;
  active?: boolean;
  aiIcon?: boolean;
  aiDanger?: boolean;
}) {
  return (
    <div
      className={`flex-1 bg-surface border rounded-xl p-3.5 text-center transition-all relative ${
        active
          ? "border-primary bg-primary-light shadow-[0_0_16px_rgba(13,124,102,.1)]"
          : "border-border hover:border-primary"
      }`}
    >
      <div className="mb-1.5 flex items-center justify-center text-text2">{icon}</div>
      <div className="font-mono text-[22px] font-extrabold">{count}</div>
      <div className="text-[10px] text-text3 font-semibold">{name}</div>
      {aiIcon && (
        <div
          className={`absolute top-1.5 right-1.5 w-4 h-4 rounded-full flex items-center justify-center text-[8px] text-white ${
            aiDanger ? "bg-danger" : "bg-purple"
          }`}
        >
          {aiDanger ? "!" : <Brain size={12} />}
        </div>
      )}
    </div>
  );
}
