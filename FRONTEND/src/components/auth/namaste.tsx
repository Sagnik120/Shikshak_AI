"use client";

/** After verification: "नमस्ते" is hand-written, then "hello" beneath it, then we fly on. */
import { motion } from "motion/react";
import { useEffect } from "react";
import { PlaneMark } from "@/components/brand/logo";
import { useI18n } from "@/providers/i18n";

export function NamasteOverlay({ onDone }: { onDone: () => void }) {
  const { t } = useI18n();
  useEffect(() => {
    const id = setTimeout(onDone, 2600);
    return () => clearTimeout(id);
  }, [onDone]);
  const reveal = (delay: number, duration: number) => ({
    initial: { clipPath: "inset(0 100% 0 0)" },
    animate: { clipPath: "inset(0 0% 0 0)" },
    transition: { delay, duration, ease: [0.65, 0, 0.35, 1] as const },
  });
  return (
    <motion.div className="ruled fixed inset-0 z-[95] grid place-items-center bg-paper" initial={{ opacity: 0 }} animate={{ opacity: 1 }} role="status">
      <div className="text-center">
        <motion.p {...reveal(0.15, 1.1)} className="font-display text-[clamp(4rem,14vw,9rem)] leading-none text-ink" lang="hi">नमस्ते</motion.p>
        <motion.p {...reveal(1.1, 0.7)} className="mt-2 font-hand text-[clamp(2rem,6vw,3.5rem)] text-sky-600">hello</motion.p>
        <motion.p initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.7 }} className="mt-6 text-ink-2">{t("auth.namaste")}</motion.p>
      </div>
      <motion.div className="absolute" initial={{ x: "-55vw", y: "20vh", rotate: -10 }} animate={{ x: "60vw", y: "-30vh", rotate: 8 }} transition={{ delay: 1.4, duration: 1.4, ease: "easeIn" }}>
        <PlaneMark size={64} />
      </motion.div>
    </motion.div>
  );
}
