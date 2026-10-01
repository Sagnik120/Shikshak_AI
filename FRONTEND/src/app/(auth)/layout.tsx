"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { BookOpenCheck, Languages, PauseCircle } from "lucide-react";
import { Logo, PlaneMark } from "@/components/brand/logo";
import { LanguageToggle } from "@/components/layout/language-toggle";
import { useI18n } from "@/providers/i18n";
import { EASE } from "@/lib/utils";

/** Auth pages: a ruled-notebook brand panel beside a calm, single form. */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();
  const points = [
    { icon: <PauseCircle className="h-5 w-5" />, text: t("auth.side1") },
    { icon: <BookOpenCheck className="h-5 w-5" />, text: t("auth.side2") },
    { icon: <Languages className="h-5 w-5" />, text: t("auth.side3") },
  ];
  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.05fr_1fr]">
      <aside className="ruled paper-grain relative hidden overflow-hidden border-r border-line bg-paper-2 py-10 pl-24 pr-10 lg:flex lg:flex-col">
        <Link href="/"><Logo /></Link>
        <div className="relative mt-auto max-w-md">
          <p className="font-hand text-2xl text-sky-700">{t("brand.tagline")}</p>
          <h2 className="mt-3 font-display text-5xl leading-[1.05] text-ink">
            {t("hero.title1")} <em className="text-sky-600">{t("hero.title2")}</em>
          </h2>
          <ul className="mt-8 space-y-3">
            {points.map((p, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.12, ease: EASE, duration: 0.5 }}
                className="flex items-center gap-3 text-ink-2"
              >
                <span className="grid h-9 w-9 place-items-center rounded-xl border border-line bg-surface text-sky-600">{p.icon}</span>
                {p.text}
              </motion.li>
            ))}
          </ul>
        </div>
        {/* a plane drifting across the page */}
        <motion.div
          className="pointer-events-none absolute right-16 top-28"
          animate={{ x: [0, 18, 0], y: [0, -12, 0], rotate: [-4, 3, -4] }}
          transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        >
          <PlaneMark size={120} />
        </motion.div>
        <svg className="pointer-events-none absolute right-24 top-52 h-40 w-72" viewBox="0 0 280 160" fill="none">
          <path d="M270 10 C 200 60, 150 20, 90 80 S 20 140, 4 150" stroke="var(--sky-300)" strokeWidth="2" strokeDasharray="4 7" className="animate-dash-flow" />
        </svg>
      </aside>
      <section className="relative flex flex-col px-5 py-6 sm:px-10">
        <div className="flex items-center justify-between">
          <Link href="/" className="lg:invisible"><Logo size={30} withWord={false} /></Link>
          <LanguageToggle />
        </div>
        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">{children}</div>
      </section>
    </div>
  );
}
