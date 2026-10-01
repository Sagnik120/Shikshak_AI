"use client";

/**
 * Slide-to-unlock, adapted: a deliberate gesture for a consequential action
 * (skipping a concept). Pointer-captured, so mouse, touch and pen behave the
 * same; Enter/Space on the handle confirms for keyboard users.
 */
import { animate, motion, useMotionValue, useTransform } from "motion/react";
import { useRef, useState } from "react";
import { ChevronsRight, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const HANDLE = 48;
const PAD = 4;

export function SlideToConfirm({ label, onConfirm, disabled, className }: { label: string; onConfirm: () => Promise<void> | void; disabled?: boolean; className?: string }) {
  const track = useRef<HTMLDivElement>(null);
  const start = useRef<{ px: number; x: number } | null>(null);
  const x = useMotionValue(0);
  const [busy, setBusy] = useState(false);
  const max = () => (track.current ? track.current.offsetWidth - HANDLE - PAD * 2 : 200);
  const textOpacity = useTransform(x, (v) => 1 - Math.min(1, v / (max() * 0.6 || 1)));
  const fill = useTransform(x, (v) => v + HANDLE);

  const confirm = async () => {
    animate(x, max(), { duration: 0.15 });
    setBusy(true);
    try { await onConfirm(); } finally {
      setBusy(false);
      animate(x, 0, { type: "spring", stiffness: 300, damping: 28 });
    }
  };
  const release = () => {
    start.current = null;
    if (x.get() >= max() * 0.85) void confirm();
    else animate(x, 0, { type: "spring", stiffness: 400, damping: 30 });
  };
  const locked = disabled || busy;

  return (
    <div ref={track} className={cn("relative h-14 select-none overflow-hidden rounded-full border border-line bg-paper-2", locked && "opacity-60", className)} role="group" aria-label={label}>
      <motion.div className="absolute bottom-1 left-1 top-1 rounded-full bg-margin-100" style={{ width: fill }} />
      <motion.span style={{ opacity: textOpacity }} className="pointer-events-none absolute inset-0 grid place-items-center pl-10 text-sm font-medium text-ink-2">{label}</motion.span>
      <motion.button
        type="button"
        aria-label={label}
        disabled={locked}
        style={{ x, top: PAD, left: PAD, width: HANDLE, height: HANDLE }}
        onPointerDown={(e) => {
          if (locked) return;
          e.currentTarget.setPointerCapture(e.pointerId);
          start.current = { px: e.clientX, x: x.get() };
        }}
        onPointerMove={(e) => {
          if (!start.current) return;
          x.set(Math.min(max(), Math.max(0, start.current.x + e.clientX - start.current.px)));
        }}
        onPointerUp={release}
        onPointerCancel={release}
        onKeyDown={(e) => { if (!locked && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); void confirm(); } }}
        className="absolute z-10 grid touch-none cursor-grab place-items-center rounded-full bg-margin text-white shadow-[var(--shadow-soft)] active:cursor-grabbing"
      >
        {busy ? <Loader2 className="h-5 w-5 animate-spin" /> : <ChevronsRight className="h-5 w-5" />}
      </motion.button>
    </div>
  );
}
