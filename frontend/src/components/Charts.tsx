import { useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import type { Series } from "../api/types";

function useWidth(initial: number) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(initial);
  useLayoutEffect(() => {
    if (!ref.current) return;
    if (ref.current.clientWidth > 0) setWidth(Math.max(120, ref.current.clientWidth));
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(120, entry.contentRect.width)));
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return { ref, width };
}

type Num = number | null;
const present = (v: Num): v is number => v !== null;

function linePath(xs: number[], ys: Num[], y: (v: number) => number): string {
  let path = "";
  ys.forEach((v, i) => {
    if (present(v)) path += `${path ? "L" : "M"}${xs[i].toFixed(1)} ${y(v).toFixed(1)}`;
  });
  return path;
}

function bandPath(xs: number[], low: Num[], high: Num[], y: (v: number) => number): string {
  const idx = xs.map((_, i) => i).filter((i) => present(low[i]) && present(high[i]));
  if (idx.length < 2) return "";
  const top = idx.map((i) => `${xs[i].toFixed(1)} ${y(high[i]!).toFixed(1)}`);
  const bottom = idx.reverse().map((i) => `${xs[i].toFixed(1)} ${y(low[i]!).toFixed(1)}`);
  return `M${top.join("L")}L${bottom.join("L")}Z`;
}

const fmt = (v: number, decimals: number) => v.toFixed(decimals);

const M = { left: 58, right: 14, top: 12, bottom: 30 };

/** One signal over time, with the person's own normal drawn behind it as a band. */
export function SeriesChart({ series, height = 220 }: { series: Series; height?: number }) {
  const { ref, width } = useWidth(560);
  const [picked, setPicked] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const n = series.days.length;
  const plotW = width - M.left - M.right;
  const plotH = height - M.top - M.bottom;
  const x = (i: number) => M.left + (n > 1 ? (i / (n - 1)) * plotW : plotW / 2);
  const xs = useMemo(() => series.days.map((_, i) => M.left + (n > 1 ? (i / (n - 1)) * plotW : plotW / 2)), [series.days, n, plotW]);

  const [lo, hi] = useMemo(() => {
    const all = [...series.values, ...series.low, ...series.high].filter(present);
    const min = Math.min(...all);
    const max = Math.max(...all);
    const pad = (max - min || 1) * 0.08;
    return [min - pad, max + pad];
  }, [series]);
  const y = (v: number) => M.top + (1 - (v - lo) / (hi - lo)) * plotH;

  const nearestReading = (i: number) => {
    for (let step = 0; step < n; step++) {
      for (const j of [i - step, i + step]) if (j >= 0 && j < n && present(series.values[j])) return j;
    }
    return null;
  };
  const pickFromPointer = (e: PointerEvent<SVGSVGElement>) => {
    const box = svgRef.current!.getBoundingClientRect();
    const ratio = ((e.clientX - box.left) / box.width) * width;
    setPicked(nearestReading(Math.round(((ratio - M.left) / plotW) * (n - 1))));
  };
  const onKey = (e: KeyboardEvent) => {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    const start = picked ?? n - 1;
    setPicked(Math.max(0, Math.min(n - 1, start + (e.key === "ArrowLeft" ? -1 : 1))));
  };

  const shown = picked ?? nearestReading(n - 1);
  const value = shown === null ? null : series.values[shown];
  const low = shown === null ? null : series.low[shown];
  const high = shown === null ? null : series.high[shown];
  const ticks = [lo + (hi - lo) * 0.1, (lo + hi) / 2, hi - (hi - lo) * 0.1];
  const tickDecimals = hi - lo < 3 ? Math.max(series.decimals, 1) : series.decimals;
  const firstBand = series.low.findIndex(present);

  return (
    <div className="chart" ref={ref}>
      <div className="readout" aria-live="off">
        {shown !== null && value !== null && value !== undefined ? (
          <>
            <b>Day {series.days[shown]}</b>
            <span className="mono">{fmt(value, series.decimals)} {series.unit}</span>
            {present(low) && present(high) ? (
              <span>Your normal {fmt(low, tickDecimals)} to {fmt(high, tickDecimals)}</span>
            ) : (
              <span>Learning your normal</span>
            )}
            {series.flagged[shown] && <span className="drift-tag">Drifting</span>}
          </>
        ) : (
          <span>No reading on this day</span>
        )}
      </div>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        role="img"
        tabIndex={0}
        aria-label={`${series.name} chart. Latest ${series.current ?? "no reading"} ${series.unit}. Use left and right arrows to read each day.`}
        onPointerDown={pickFromPointer}
        onPointerMove={(e) => e.buttons && pickFromPointer(e)}
        onKeyDown={onKey}
      >
        {ticks.map((t) => (
          <g key={t}>
            <line x1={M.left} x2={width - M.right} y1={y(t)} y2={y(t)} className="grid" />
            <text x={M.left - 8} y={y(t) + 5} textAnchor="end" className="tick">{fmt(t, tickDecimals)}</text>
          </g>
        ))}
        <path d={bandPath(xs, series.low, series.high, y)} className="band" />
        <path d={linePath(xs, series.median, y)} className="median" />
        {firstBand > 0 && <text x={x(firstBand) - 6} y={M.top + 16} textAnchor="end" className="tick">Learning</text>}
        <path d={linePath(xs, series.values, y)} className="trace" />
        {series.cadence > 1 &&
          series.values.map((v, i) => present(v) && <circle key={i} cx={xs[i]} cy={y(v)} r={3.5} className="trace-dot" />)}
        {series.values.map(
          (v, i) => present(v) && series.flagged[i] && <circle key={i} cx={xs[i]} cy={y(v)} r={5} className="flag-dot" />,
        )}
        {shown !== null && <line x1={xs[shown]} x2={xs[shown]} y1={M.top} y2={M.top + plotH} className="crosshair" />}
        <text x={M.left} y={height - 8} className="tick">Day {series.days[0]}</text>
        <text x={width - M.right} y={height - 8} textAnchor="end" className="tick">Day {series.days[n - 1]}</text>
      </svg>
    </div>
  );
}

/** A 30-day score trend for the system cards. */
export function Sparkline({ values, label, height = 72 }: { values: number[]; label: string; height?: number }) {
  const { ref, width } = useWidth(300);
  const pad = 7;
  const n = values.length;
  const x = (i: number) => pad + (n > 1 ? (i / (n - 1)) * (width - 2 * pad) : 0);
  const y = (v: number) => pad + (1 - v / 100) * (height - 2 * pad);
  const d = values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join("");
  const last = values[n - 1];
  return (
    <div ref={ref} className="spark">
      <svg width={width} height={height} role="img" aria-label={`${label}. 30-day drift trend, latest ${last ?? 0} of 100.`}>
        <line x1={pad} x2={width - pad} y1={y(30)} y2={y(30)} className="grid" />
        <line x1={pad} x2={width - pad} y1={y(60)} y2={y(60)} className="grid" />
        {n > 0 && <path d={d} className="trace" />}
        {n > 0 && <circle cx={x(n - 1)} cy={y(last)} r={5} className="spark-end" />}
      </svg>
    </div>
  );
}
