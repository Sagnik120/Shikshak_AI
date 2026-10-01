"use client";

/**
 * Snapping slider with a liquid-glass thumb (adapted from Liquid Glass Slider):
 * the thumb magnifies the track beneath it and squashes while dragged.
 * Keyboard: arrows step between stops.
 */
import { animate, motion, useMotionValue, useSpring, useTransform } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export function GlassSlider({ stops, value, onChange, format, ariaLabel }: { stops: number[]; value: number; onChange: (v: number) => void; format: (v: number) => React.ReactNode; ariaLabel: string }) {
  const track = useRef<HTMLDivElement>(null);
  const idx = Math.max(0, stops.indexOf(value));
  const pct = useMotionValue((idx / (stops.length - 1)) * 100);
  const left = useSpring(pct, { stiffness: 500, damping: 40 });
  const [drag, setDrag] = useState(false);
  const width = useTransform(left, (x) => `${x}%`);

  useEffect(() => { if (!drag) animate(pct, (idx / (stops.length - 1)) * 100, { duration: 0.25 }); }, [idx, drag, pct, stops.length]);

  const fromPointer = (clientX: number) => {
    const r = track.current!.getBoundingClientRect();
    const p = Math.min(1, Math.max(0, (clientX - r.left) / r.width));
    pct.set(p * 100);
    const i = Math.round(p * (stops.length - 1));
    if (stops[i] !== value) onChange(stops[i]);
  };

  return (
    <div className="select-none">
      <div
        ref={track}
        role="slider"
        tabIndex={0}
        aria-label={ariaLabel}
        aria-valuemin={stops[0]}
        aria-valuemax={stops[stops.length - 1]}
        aria-valuenow={value}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight" || e.key === "ArrowUp") { e.preventDefault(); onChange(stops[Math.min(stops.length - 1, idx + 1)]); }
          if (e.key === "ArrowLeft" || e.key === "ArrowDown") { e.preventDefault(); onChange(stops[Math.max(0, idx - 1)]); }
        }}
        onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); setDrag(true); fromPointer(e.clientX); }}
        onPointerMove={(e) => drag && fromPointer(e.clientX)}
        onPointerUp={() => setDrag(false)}
        onPointerCancel={() => setDrag(false)}
        className="relative h-12 cursor-pointer touch-none rounded-full outline-none focus-visible:ring-4 focus-visible:ring-sky-100"
      >
        <div className="absolute inset-x-0 top-1/2 h-3 -translate-y-1/2 rounded-full bg-paper-3 shadow-[var(--shadow-press)]" />
        <motion.div className="absolute left-0 top-1/2 h-3 -translate-y-1/2 rounded-full bg-gradient-to-r from-sky-300 to-sky-600" style={{ width }} />
        {stops.map((s, i) => (
          <span key={s} className={cn("absolute top-1/2 h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full", i <= idx ? "bg-white/90" : "bg-line-2")} style={{ left: `${(i / (stops.length - 1)) * 100}%` }} />
        ))}
        <motion.div
          className="absolute top-1/2 h-10 w-16 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/70 bg-white/35 shadow-[0_6px_20px_-6px_rgb(30_41_66/0.35),inset_0_1px_0_white,inset_0_-6px_12px_rgb(59_102_174/0.12)] backdrop-blur-[2px] backdrop-saturate-150"
          style={{ left: width }}
          animate={{ scaleX: drag ? 1.15 : 1, scaleY: drag ? 0.88 : 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 22 }}
        />
      </div>
      <div className="mt-2 flex justify-between text-xs text-ink-3">
        {stops.map((s) => (
          <button key={s} type="button" onClick={() => onChange(s)} className={cn("min-w-8 rounded-md px-1 transition-colors", s === value ? "font-semibold text-ink" : "hover:text-ink-2")}>{format(s)}</button>
        ))}
      </div>
    </div>
  );
}
