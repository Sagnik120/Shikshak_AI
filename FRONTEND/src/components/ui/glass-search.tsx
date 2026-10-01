"use client";

/** Liquid-glass search box (adapted): a frosted pill whose sheen follows the pointer; "/" focuses it. */
import { motion, useMotionTemplate, useMotionValue } from "motion/react";
import { useEffect, useRef } from "react";
import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function GlassSearch({ value, onChange, placeholder, className }: { value: string; onChange: (v: string) => void; placeholder: string; className?: string }) {
  const ref = useRef<HTMLInputElement>(null);
  const mx = useMotionValue(50);
  const sheen = useMotionTemplate`radial-gradient(180px circle at ${mx}% 0%, rgb(255 255 255 / 0.9), transparent 70%)`;
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if (e.key === "/" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "TEXTAREA") { e.preventDefault(); ref.current?.focus(); }
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, []);
  return (
    <div onPointerMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); mx.set(((e.clientX - r.left) / r.width) * 100); }}
      className={cn("group relative flex h-14 items-center gap-3 overflow-hidden rounded-full border border-white/70 bg-gradient-to-b from-white/80 to-sky-50/60 px-5 shadow-[0_10px_30px_-12px_rgb(59_102_174/0.35),inset_0_1px_0_white,inset_0_-8px_16px_rgb(59_102_174/0.06)] backdrop-blur-xl transition-shadow focus-within:shadow-[0_0_0_4px_var(--sky-100),0_10px_30px_-12px_rgb(59_102_174/0.45)]", className)}>
      <motion.div className="pointer-events-none absolute inset-0 opacity-60" style={{ background: sheen }} />
      <Search className="relative h-5 w-5 text-sky-600" />
      <input ref={ref} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} aria-label={placeholder}
        className="relative h-full flex-1 bg-transparent text-[1rem] text-ink outline-none placeholder:text-ink-3" />
      {value ? (
        <button type="button" onClick={() => onChange("")} className="relative grid h-7 w-7 place-items-center rounded-full bg-paper-2 text-ink-3 hover:text-ink" aria-label="clear"><X className="h-3.5 w-3.5" /></button>
      ) : <kbd className="relative rounded-md border border-line bg-surface px-1.5 text-xs text-ink-3">/</kbd>}
    </div>
  );
}
