"use client";

/**
 * Small, dependency-free SVG charts with real axes: labelled y ticks and
 * gridlines, dated x labels, a hover crosshair with a tooltip listing every
 * series, and a draw-in animation. Shared by the learner and staff views.
 */
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useI18n } from "@/providers/i18n";
import { EASE, cn } from "@/lib/utils";

export type Series = { key: string; label: string; color: string; kind: "bar" | "line" | "dot"; values: number[]; format?: (v: number) => string };

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [w, setW] = useState(0);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

function niceMax(v: number) {
  if (v <= 4) return 4;
  const p = 10 ** Math.floor(Math.log10(v));
  const m = v / p;
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p;
}

export function useDateLabel() {
  const { lang } = useI18n();
  return useMemo(() => {
    const f = new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short" });
    return (iso: string) => f.format(new Date(iso));
  }, [lang]);
}

/** Bars (stacked), lines and markers over a shared date axis. */
export function TimeChart({ dates, series, height = 240, yMax, yFormat, yLabel, className }: {
  dates: string[]; series: Series[]; height?: number; yMax?: number; yFormat?: (v: number) => string; yLabel?: string; className?: string;
}) {
  const { n } = useI18n();
  const dateLabel = useDateLabel();
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const pad = { l: 40, r: 12, t: yLabel ? 26 : 14, b: 28 };
  const W = Math.max(280, width), H = height;
  const iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
  const bars = series.filter((s) => s.kind === "bar");
  const stackTop = dates.map((_, i) => bars.reduce((a, s) => a + (s.values[i] || 0), 0));
  const peak = Math.max(1, ...stackTop, ...series.filter((s) => s.kind !== "bar").flatMap((s) => s.values));
  const top = yMax ?? niceMax(peak);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => top * f);
  const step = iw / Math.max(1, dates.length);
  const bw = Math.max(3, Math.min(28, step * 0.62));
  const x = (i: number) => pad.l + step * i + step / 2;
  const y = (v: number) => pad.t + ih - (v / top) * ih;
  const fmt = yFormat ?? ((v: number) => n(Math.round(v)));
  const every = Math.max(1, Math.ceil(dates.length / Math.max(2, Math.floor(iw / 64))));

  return (
    <div ref={ref} className={cn("relative w-full select-none", className)} onMouseLeave={() => setHover(null)}>
      {width > 0 && (
        <svg width={W} height={H} className="block overflow-visible" role="img" aria-label={yLabel}>
          {/* grid + y axis */}
          {ticks.map((tv, i) => (
            <g key={i}>
              <line x1={pad.l} x2={W - pad.r} y1={y(tv)} y2={y(tv)} stroke="var(--line)" strokeDasharray={i ? "3 5" : undefined} />
              <text x={pad.l - 8} y={y(tv)} dy="0.32em" textAnchor="end" className="fill-ink-3 text-[10px] tabular-nums">{fmt(tv)}</text>
            </g>
          ))}
          {yLabel && <text x={4} y={10} className="fill-ink-3 text-[10px] font-medium">{yLabel}</text>}
          {/* x axis labels */}
          {dates.map((d, i) => (i % every === 0 || i === dates.length - 1) && (
            <text key={d} x={x(i)} y={H - 8} textAnchor="middle" className={cn("text-[10px]", hover === i ? "fill-ink" : "fill-ink-3")}>{dateLabel(d)}</text>
          ))}
          {/* hover band */}
          {hover !== null && <rect x={x(hover) - step / 2} y={pad.t} width={step} height={ih} fill="var(--sky-50)" />}
          {/* stacked bars */}
          {dates.map((d, i) => {
            let acc = 0;
            return (
              <g key={d}>
                {bars.map((s, si) => {
                  const v = s.values[i] || 0;
                  const y0 = y(acc), y1 = y(acc + v);
                  acc += v;
                  if (!v) return null;
                  const isTop = bars.slice(si + 1).every((b) => !(b.values[i] || 0));
                  return (
                    <motion.rect key={s.key} x={x(i) - bw / 2} width={bw} fill={s.color} rx={isTop ? Math.min(5, bw / 2) : 0}
                      initial={{ y: y0, height: 0 }} animate={{ y: y1, height: y0 - y1 }}
                      transition={{ duration: 0.6, ease: EASE, delay: i * 0.015 + si * 0.08 }} />
                  );
                })}
              </g>
            );
          })}
          {/* lines */}
          {series.filter((s) => s.kind === "line").map((s) => {
            const d = s.values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
            return (
              <g key={s.key}>
                <motion.path d={d} fill="none" stroke={s.color} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round"
                  initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.1, ease: EASE }} />
                {s.values.map((v, i) => <circle key={i} cx={x(i)} cy={y(v)} r={hover === i ? 5 : 3} fill="var(--surface)" stroke={s.color} strokeWidth={2} />)}
              </g>
            );
          })}
          {/* markers (e.g. a learner handed to a human) */}
          {series.filter((s) => s.kind === "dot").map((s) => s.values.map((v, i) => v > 0 && (
            <g key={`${s.key}-${i}`}>
              <motion.circle cx={x(i)} cy={pad.t + 6} r={6 + Math.min(4, v)} fill={s.color} initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.8 + i * 0.02 }} />
              <text x={x(i)} y={pad.t + 6} dy="0.32em" textAnchor="middle" className="fill-white text-[9px] font-bold">{n(v)}</text>
            </g>
          )))}
          {/* hit areas */}
          {dates.map((d, i) => (
            <rect key={`h-${d}`} x={x(i) - step / 2} y={pad.t} width={step} height={ih} fill="transparent" onMouseEnter={() => setHover(i)} onTouchStart={() => setHover(i)} />
          ))}
        </svg>
      )}
      <AnimatePresence>
        {hover !== null && width > 0 && (
          <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}
            className="pointer-events-none absolute top-0 z-10 min-w-40 rounded-xl border border-line bg-surface/95 p-3 text-xs shadow-[var(--shadow-lift)] backdrop-blur"
            style={{ left: Math.min(Math.max(0, x(hover) - 80), W - 170) }}>
            <p className="mb-1.5 font-semibold text-ink">{dateLabel(dates[hover])}</p>
            {series.map((s) => (
              <p key={s.key} className="flex items-center justify-between gap-4 text-ink-2">
                <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full" style={{ background: s.color }} />{s.label}</span>
                <span className="font-medium tabular-nums text-ink">{(s.format ?? ((v: number) => n(Math.round(v))))(s.values[hover] || 0)}</span>
              </p>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function Legend({ items }: { items: Array<{ label: string; color: string; kind?: "bar" | "line" | "dot" }> }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
      {items.map((it) => (
        <span key={it.label} className="flex items-center gap-1.5">
          {it.kind === "line" ? <i className="h-0.5 w-4 rounded-full" style={{ background: it.color }} /> : <i className={cn("h-2.5 w-2.5", it.kind === "dot" ? "rounded-full" : "rounded-[3px]")} style={{ background: it.color }} />}
          {it.label}
        </span>
      ))}
    </div>
  );
}

/** A ring split into labelled parts. */
export function Donut({ parts, size = 160, stroke = 18, center }: { parts: Array<{ label: string; value: number; color: string }>; size?: number; stroke?: number; center?: React.ReactNode }) {
  const total = Math.max(1, parts.reduce((a, p) => a + p.value, 0));
  const r = (size - stroke) / 2, c = 2 * Math.PI * r;
  const lens = parts.map((p) => (p.value / total) * c);
  const starts = lens.map((_, i) => lens.slice(0, i).reduce((a, b) => a + b, 0));
  return (
    <div className="relative inline-grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--paper-3)" strokeWidth={stroke} />
        {parts.map((p, i) => (
          <motion.circle key={p.label} cx={size / 2} cy={size / 2} r={r} fill="none" stroke={p.color} strokeWidth={stroke}
            strokeDasharray={`${Math.max(0, lens[i] - 2)} ${c}`} initial={{ strokeDashoffset: -starts[i] + lens[i] }} animate={{ strokeDashoffset: -starts[i] }}
            transition={{ duration: 0.9, ease: EASE, delay: i * 0.15 }} />
        ))}
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">{center}</div>
    </div>
  );
}
