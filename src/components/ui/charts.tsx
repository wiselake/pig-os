"use client";

/**
 * 경량 SVG 차트 원자 — raw hex 금지. 색은 부모의 text-* 토큰을 currentColor로 상속.
 * (예: <span className="text-success"><Spark .../></span>)
 * 디자인 핸드오프 tpl-output.jsx 의 Spark/LineChart/MiniBars 재구현.
 */

export function Spark({ data, w = 200, h = 34 }: { data: number[]; w?: number; h?: number }) {
  if (!data || data.length < 2) return <svg width={w} height={h} />;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const r = max - min || 1;
  const pts = data.map((v, i) => [(i / (data.length - 1)) * w, h - ((v - min) / r) * (h - 6) - 3]);
  const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const last = pts[pts.length - 1];
  return (
    <svg width={w} height={h} className="block text-current">
      <path d={`${d} L ${w} ${h} L 0 ${h} Z`} fill="currentColor" opacity={0.1} />
      <path d={d} fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={last[0]} cy={last[1]} r={3} fill="currentColor" />
    </svg>
  );
}

export interface ChartSeries {
  data: number[];
  /** Tailwind text-* class for this line's color (currentColor 상속용) */
  colorClass: string;
  fill?: boolean;
}

/**
 * 다계열 라인차트. 각 계열은 colorClass(text-*)로 색 지정.
 * bench: 점선 기준선(벤치마크). xLabels: 하단 라벨(격행 표시).
 */
export function LineChart({
  series,
  w = 600,
  h = 210,
  xLabels,
  bench,
}: {
  series: ChartSeries[];
  w?: number;
  h?: number;
  xLabels?: string[];
  bench?: number;
}) {
  const all = series.flatMap((s) => s.data).concat(bench != null ? [bench] : []);
  if (all.length === 0) return <svg width={w} height={h} />;
  const min = Math.min(...all);
  const max = Math.max(...all);
  const pad = (max - min) * 0.18 || 1;
  const lo = min - pad;
  const hi = max + pad;
  const range = hi - lo || 1;
  const pL = 38, pR = 14, pT = 14, pB = 26;
  const iw = w - pL - pR, ih = h - pT - pB;
  const len = Math.max(...series.map((s) => s.data.length));
  const x = (i: number) => pL + (i / Math.max(1, len - 1)) * iw;
  const y = (v: number) => pT + ih - ((v - lo) / range) * ih;
  const grid = [0, 1, 2, 3].map((i) => lo + (range * i) / 3);
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} className="block overflow-visible">
      {grid.map((v, i) => (
        <g key={i} className="text-border">
          <line x1={pL} x2={w - pR} y1={y(v)} y2={y(v)} stroke="currentColor" strokeDasharray="2 4" />
          <text x={pL - 7} y={y(v) + 3} fontSize={9.5} className="fill-muted font-mono" textAnchor="end">
            {v.toFixed(0)}
          </text>
        </g>
      ))}
      {bench != null && (
        <line x1={pL} x2={w - pR} y1={y(bench)} y2={y(bench)} className="text-text3" stroke="currentColor" strokeWidth={1.5} strokeDasharray="5 4" />
      )}
      {xLabels?.map((l, i) =>
        i % 2 === 0 ? (
          <text key={i} x={x(i)} y={h - 8} fontSize={9.5} className="fill-muted font-mono" textAnchor="middle">
            {l}
          </text>
        ) : null,
      )}
      {series.map((s, si) => {
        const pts = s.data.map((v, i) => [x(i), y(v)]);
        const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
        const last = pts[pts.length - 1];
        return (
          <g key={si} className={s.colorClass}>
            {s.fill !== false && (
              <path d={`${d} L ${x(len - 1)} ${y(lo)} L ${x(0)} ${y(lo)} Z`} fill="currentColor" opacity={0.08} />
            )}
            <path d={d} fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
            {last && <circle cx={last[0]} cy={last[1]} r={3.5} fill="currentColor" className="stroke-surface" strokeWidth={1.5} />}
          </g>
        );
      })}
    </svg>
  );
}

/** 미니 막대 — 마지막 막대만 풀 불투명(임계 초과 강조용) */
export function MiniBars({ data, w = 200, h = 44 }: { data: number[]; w?: number; h?: number }) {
  if (!data || data.length === 0) return <svg width={w} height={h} />;
  const max = Math.max(...data) || 1;
  const bw = w / data.length;
  return (
    <svg width={w} height={h} className="block text-current">
      {data.map((v, i) => (
        <rect
          key={i}
          x={i * bw + 1.5}
          y={h - (v / max) * h}
          width={bw - 3}
          height={(v / max) * h}
          rx={2}
          fill="currentColor"
          opacity={i === data.length - 1 ? 1 : 0.4}
        />
      ))}
    </svg>
  );
}
