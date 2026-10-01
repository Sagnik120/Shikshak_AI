"use client";

/**
 * The mark: a paper plane folded from a ruled notebook page. Its two creases
 * sit like "॥" — the Devanagari pause, and a pause button: the teacher who
 * stops to check you're with it. Hover: it loops and leaves a flight trail.
 */
import { motion, useAnimationControls } from "motion/react";
import { useEffect } from "react";
import { cn, EASE } from "@/lib/utils";

export function PlaneMark({ size = 36, className, animateIn = false }: { size?: number; className?: string; animateIn?: boolean }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} className={className} aria-hidden="true">
      <defs>
        <clipPath id="sk-body">
          <path d="M6 30 L58 9 L27 37 Z" />
        </clipPath>
      </defs>
      {/* lower wing (in shadow) */}
      <motion.path
        d="M27 37 L58 9 L35 56 Z"
        fill="var(--sky-100)"
        stroke="var(--ink)"
        strokeWidth="1.6"
        strokeLinejoin="round"
        initial={animateIn ? { opacity: 0, x: -6 } : false}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, ease: EASE, delay: 0.15 }}
      />
      {/* fold flap */}
      <path d="M27 37 L31 47 L35 56 Z" fill="var(--sky-200)" stroke="var(--ink)" strokeWidth="1.4" strokeLinejoin="round" />
      {/* the page itself, with its ruled lines */}
      <motion.g initial={animateIn ? { opacity: 0, y: 4 } : false} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: EASE }}>
        <path d="M6 30 L58 9 L27 37 Z" fill="var(--surface)" stroke="var(--ink)" strokeWidth="1.6" strokeLinejoin="round" />
        <g clipPath="url(#sk-body)" stroke="var(--rule)" strokeWidth="1.1">
          <line x1="0" y1="20" x2="64" y2="20" />
          <line x1="0" y1="26" x2="64" y2="26" />
          <line x1="0" y1="32" x2="64" y2="32" />
          <line x1="16" y1="0" x2="16" y2="64" stroke="var(--margin)" strokeWidth="0.9" />
        </g>
      </motion.g>
      {/* ॥ — the pause */}
      <motion.g
        stroke="var(--sky-600)"
        strokeWidth="2.6"
        strokeLinecap="round"
        initial={animateIn ? { pathLength: 0 } : false}
        animate={{ pathLength: 1 }}
      >
        <motion.line x1="31" y1="21" x2="28.5" y2="29" initial={animateIn ? { pathLength: 0 } : false} animate={{ pathLength: 1 }} transition={{ delay: 0.35, duration: 0.35, ease: EASE }} />
        <motion.line x1="37" y1="18.5" x2="34.5" y2="26.5" initial={animateIn ? { pathLength: 0 } : false} animate={{ pathLength: 1 }} transition={{ delay: 0.5, duration: 0.35, ease: EASE }} />
      </motion.g>
    </svg>
  );
}

export function Logo({ className, withWord = true, size = 34 }: { className?: string; withWord?: boolean; size?: number }) {
  const plane = useAnimationControls();
  const trail = useAnimationControls();

  // Replays a little take-off each time the page (re)loads.
  useEffect(() => {
    plane.start({ x: [-10, 0], y: [6, 0], rotate: [-14, 0], opacity: [0, 1], transition: { duration: 0.8, ease: EASE } });
  }, [plane]);

  const loop = () => {
    plane.start({
      x: [0, 10, 16, 8, -2, 0],
      y: [0, -10, -2, 8, 4, 0],
      rotate: [0, -24, -120, -250, -350, -360],
      transition: { duration: 1.1, ease: EASE },
    });
    trail.start({ pathLength: [0, 1, 1], opacity: [0, 1, 0], transition: { duration: 1.2, ease: EASE } });
  };

  return (
    <span className={cn("group inline-flex items-center gap-2.5 select-none", className)} onMouseEnter={loop} data-cursor="link">
      <span className="relative inline-grid place-items-center" style={{ width: size, height: size }}>
        <svg viewBox="0 0 64 64" className="pointer-events-none absolute -left-4 -top-3 h-[150%] w-[150%] overflow-visible" aria-hidden="true">
          <motion.path
            d="M4 58 C 14 40, 30 64, 40 46 S 60 30, 46 20"
            fill="none"
            stroke="var(--sky-300)"
            strokeWidth="1.6"
            strokeDasharray="3 4"
            strokeLinecap="round"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={trail}
          />
        </svg>
        <motion.span animate={plane} className="inline-block" style={{ originX: 0.5, originY: 0.5 }}>
          <PlaneMark size={size} />
        </motion.span>
      </span>
      {withWord && (
        <span className="leading-none">
          <span className="block font-display text-[1.55rem] tracking-tight text-ink">
            Shikshak<span className="text-sky-600">.</span>
          </span>
          <span className="mt-0.5 block text-[0.62rem] font-medium tracking-[0.22em] text-ink-3 uppercase">शिक्षक · AI teacher</span>
        </span>
      )}
    </span>
  );
}
