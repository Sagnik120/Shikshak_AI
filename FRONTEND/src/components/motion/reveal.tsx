"use client";

/** The motion vocabulary: things arrive by lifting off the page and un-blurring. */
import { animate, motion, useInView, useMotionValue, useTransform } from "motion/react";
import { useEffect, useRef, type ReactNode } from "react";
import { cn, EASE } from "@/lib/utils";

export function Reveal({ children, className, delay = 0, y = 18 }: { children: ReactNode; className?: string; delay?: number; y?: number }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y, filter: "blur(6px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.7, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  );
}

export function Stagger({ children, className, gap = 0.07 }: { children: ReactNode; className?: string; gap?: number }) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-40px" }}
      variants={{ hidden: {}, show: { transition: { staggerChildren: gap } } }}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      className={className}
      variants={{
        hidden: { opacity: 0, y: 14, filter: "blur(4px)" },
        show: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.55, ease: EASE } },
      }}
    >
      {children}
    </motion.div>
  );
}

/** Counts up when scrolled into view; `format` localises the digits. */
export function CountUp({ to, decimals = 0, suffix = "", format, className }: { to: number; decimals?: number; suffix?: string; format?: (s: string) => string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const mv = useMotionValue(0);
  const text = useTransform(mv, (v) => {
    const s = v.toFixed(decimals) + suffix;
    return format ? format(s) : s;
  });
  useEffect(() => {
    if (!inView) return;
    const controls = animate(mv, to, { duration: 1.4, ease: EASE });
    return () => controls.stop();
  }, [inView, mv, to]);
  return <motion.span ref={ref} className={cn("tabular-nums", className)}>{text}</motion.span>;
}

/** Text with a moving shine for "the teacher is working…" (ShimmeringText, adapted). */
export function Shimmer({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn("inline-block bg-clip-text text-transparent", className)}
      style={{
        backgroundImage: "linear-gradient(100deg, var(--ink-3) 40%, var(--ink) 50%, var(--ink-3) 60%)",
        backgroundSize: "250% 100%",
        animation: "shimmer-text 2.2s linear infinite",
      }}
    >
      {children}
      <style>{`@keyframes shimmer-text { from { background-position: 100% 0 } to { background-position: -150% 0 } }`}</style>
    </span>
  );
}
