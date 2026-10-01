"use client";

/**
 * A form field in the notebook style: the label sits on the line, an ink
 * stroke draws under the field while it has focus, and an error nudges the
 * field once and writes itself in underneath. No zooming.
 */
import { AnimatePresence, motion, useAnimationControls } from "motion/react";
import { useEffect, type ReactNode } from "react";
import { EASE, cn } from "@/lib/utils";

export function Field({ id, label, hint, optional, error, children, className, index = 0 }: {
  id?: string; label: ReactNode; hint?: ReactNode; optional?: string; error?: string | null; children: ReactNode; className?: string; index?: number;
}) {
  // Nudge once when an error appears. Animating (not re-keying) keeps the
  // input mounted, so nothing the user typed is lost.
  const shake = useAnimationControls();
  useEffect(() => {
    if (error) void shake.start({ x: [0, -6, 6, -3, 0], transition: { duration: 0.35 } });
  }, [error, shake]);
  return (
    <motion.div
      className={cn("group", className)}
      initial={{ opacity: 0, clipPath: "inset(0 100% 0 0)" }}
      animate={{ opacity: 1, clipPath: "inset(0 0% 0 0)" }}
      transition={{ duration: 0.55, ease: EASE, delay: 0.08 + index * 0.06 }}
    >
      <label htmlFor={id} className="mb-1.5 flex items-baseline justify-between gap-2 text-sm font-medium text-ink transition-colors group-focus-within:text-sky-700">
        <span>
          {label}
          {optional && <span className="ml-1.5 rounded-full bg-paper-2 px-1.5 py-px text-[0.68rem] font-normal text-ink-3">{optional}</span>}
        </span>
        {hint && <span className="text-xs font-normal text-ink-3">{hint}</span>}
      </label>
      <motion.div className="relative" animate={shake}>
        {children}
        <span aria-hidden className="pointer-events-none absolute inset-x-4 bottom-0 h-[2px] origin-left scale-x-0 rounded-full bg-sky-500 transition-transform duration-500 ease-[cubic-bezier(.22,1,.36,1)] group-focus-within:scale-x-100" />
      </motion.div>
      <AnimatePresence>
        {error && (
          <motion.p id={id ? `${id}-error` : undefined} role="alert" className="mt-1.5 text-sm text-rose"
            initial={{ opacity: 0, clipPath: "inset(0 100% 0 0)" }} animate={{ opacity: 1, clipPath: "inset(0 0% 0 0)" }} exit={{ opacity: 0 }} transition={{ duration: 0.35, ease: EASE }}>
            {error}
          </motion.p>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/** Values exactly as the browser holds them at submit time (covers autofill). */
export function formValues(form: HTMLFormElement): Record<string, string> {
  const out: Record<string, string> = {};
  new FormData(form).forEach((v, k) => { out[k] = typeof v === "string" ? v : ""; });
  return out;
}

export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
