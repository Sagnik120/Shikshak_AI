"use client";

/**
 * Landing navigation, adapted from the Dynamic Scroll Island TOC: a floating
 * pill that shows the logo at the top, then morphs into "where you are"
 * (section name + a reading-progress ring) as you scroll; tap it for the TOC.
 */
import Link from "next/link";
import { AnimatePresence, motion, useMotionValueEvent, useScroll, useSpring } from "motion/react";
import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { LanguageToggle } from "@/components/layout/language-toggle";
import { useAuth } from "@/providers/auth";
import { useI18n } from "@/providers/i18n";
import type { MessageKey } from "@/core/i18n";
import { Button } from "@/components/ui/button";
import { cn, EASE } from "@/lib/utils";
import { isStaff } from "@/lib/staff";

export const SECTIONS: Array<{ id: string; key: MessageKey }> = [
  { id: "problem", key: "problem.kicker" },
  { id: "loop", key: "loop.kicker" },
  { id: "ladder", key: "ladder.kicker" },
  { id: "grounded", key: "grounded.kicker" },
  { id: "langs", key: "langs.kicker" },
  { id: "hood", key: "hood.kicker" },
];

export function IslandNav() {
  const { t } = useI18n();
  const { signedIn, user } = useAuth();
  const { scrollY, scrollYProgress } = useScroll();
  const ring = useSpring(scrollYProgress, { stiffness: 200, damping: 30 });
  const [compact, setCompact] = useState(false);
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState<string | null>(null);

  useMotionValueEvent(scrollY, "change", (y) => setCompact(y > 520));

  useEffect(() => {
    const els = SECTIONS.map((s) => document.getElementById(s.id)).filter(Boolean) as HTMLElement[];
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setCurrent(e.target.id)),
      { rootMargin: "-45% 0px -50% 0px" }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  const currentKey = SECTIONS.find((s) => s.id === current)?.key;
  const jump = (id: string) => { setOpen(false); document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }); };

  return (
    <div className="pointer-events-none fixed inset-x-0 top-3 z-50 flex justify-center px-3">
      <motion.nav layout transition={{ duration: 0.5, ease: EASE }}
        className={cn("pointer-events-auto relative flex items-center gap-2 border border-line bg-surface/85 shadow-[var(--shadow-lift)] backdrop-blur-xl",
          compact ? "rounded-full py-1.5 pl-2 pr-1.5" : "w-full max-w-6xl rounded-[22px] px-3 py-2 sm:px-4")}>
        <motion.div layout="position"><Link href="/" aria-label="Shikshak"><Logo size={compact ? 28 : 32} withWord={!compact} /></Link></motion.div>

        <AnimatePresence mode="popLayout" initial={false}>
          {compact ? (
            <motion.button key="where" layout initial={{ opacity: 0, filter: "blur(4px)" }} animate={{ opacity: 1, filter: "blur(0px)" }} exit={{ opacity: 0 }}
              onClick={() => setOpen((o) => !o)} aria-expanded={open}
              className="flex min-w-0 items-center gap-2 rounded-full px-2 py-1 text-sm text-ink-2 hover:text-ink">
              <svg width="18" height="18" viewBox="0 0 20 20" className="-rotate-90 shrink-0" aria-hidden>
                <circle cx="10" cy="10" r="8" fill="none" stroke="var(--line)" strokeWidth="2.5" />
                <motion.circle cx="10" cy="10" r="8" fill="none" stroke="var(--sky-600)" strokeWidth="2.5" strokeLinecap="round" style={{ pathLength: ring }} />
              </svg>
              <span className="max-w-[9.5rem] truncate sm:max-w-none">{currentKey ? t(currentKey) : t("hero.kicker")}</span>
              <ChevronDown className={cn("h-4 w-4 shrink-0 transition-transform", open && "rotate-180")} />
            </motion.button>
          ) : (
            <motion.div key="links" layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="ml-6 hidden flex-1 items-center gap-1 md:flex">
              {[["loop", "nav.howItWorks"], ["ladder", "nav.forTeachers"], ["hood", "nav.underTheHood"]].map(([id, key]) => (
                <button key={id} onClick={() => jump(id)} className="rounded-full px-3 py-1.5 text-sm text-ink-2 transition-colors hover:bg-paper-2 hover:text-ink">{t(key as MessageKey)}</button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <motion.div layout="position" className={cn("flex items-center gap-2", !compact && "ml-auto")}>
          {!compact && <LanguageToggle className="hidden sm:flex" />}
          {signedIn ? (
            <Button href={isStaff(user) ? "/admin" : "/dashboard"} size="sm">{compact ? t("nav.dashboard") : t("nav.openApp")}</Button>
          ) : (
            <>
              {!compact && <Button href="/staff/login" size="sm" variant="ghost" className="hidden lg:inline-flex">{t("nav.forStaff")}</Button>}
              {!compact && <Button href="/login" size="sm" variant="ghost" className="hidden sm:inline-flex">{t("nav.signIn")}</Button>}
              <Button href="/signup" size="sm" className={compact ? "rounded-full" : ""}>{t("nav.getStarted")}</Button>
            </>
          )}
        </motion.div>

        <AnimatePresence>
          {open && compact && (
            <motion.ul initial={{ opacity: 0, y: -6, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -6, scale: 0.97 }} transition={{ duration: 0.25, ease: EASE }}
              className="absolute left-1/2 top-[calc(100%+8px)] w-64 -translate-x-1/2 rounded-3xl border border-line bg-surface p-2 shadow-[var(--shadow-lift)]">
              {SECTIONS.map((s, i) => (
                <li key={s.id}>
                  <button onClick={() => jump(s.id)} className={cn("flex w-full items-center gap-3 rounded-2xl px-3 py-2 text-left text-sm", current === s.id ? "bg-sky-50 text-ink" : "text-ink-2 hover:bg-paper-2")}>
                    <span className="font-hand text-base text-sky-600">{String(i + 1).padStart(2, "0")}</span>{t(s.key)}
                  </button>
                </li>
              ))}
              <li className="mt-1 flex justify-center border-t border-line pt-2"><LanguageToggle /></li>
            </motion.ul>
          )}
        </AnimatePresence>
      </motion.nav>
    </div>
  );
}
