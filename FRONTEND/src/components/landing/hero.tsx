"use client";

import dynamic from "next/dynamic";
import { motion, useMotionValueEvent, useScroll, useTransform } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowRight, BookOpenCheck, Languages, UserRoundCheck } from "lucide-react";
import { PlaneMark } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/providers/i18n";
import { EASE } from "@/lib/utils";
import { LessonDemo } from "./lesson-demo";

const Plane3D = dynamic(() => import("./plane-3d"), { ssr: false, loading: () => <PlaneFallback /> });

function PlaneFallback() {
  return <div className="grid h-full w-full place-items-center"><PlaneMark size={180} className="animate-float-soft" /></div>;
}

function canWebGL() {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch { return false; }
}

/** Words lift in one by one, like a teacher writing them. */
function Words({ text, delay = 0, className }: { text: string; delay?: number; className?: string }) {
  return (
    <span className={className}>
      {text.split(" ").map((w, i) => (
        <span key={`${w}-${i}`} className="inline-block overflow-hidden pb-[0.08em] align-bottom">
          <motion.span className="inline-block" initial={{ y: "105%", rotate: 4 }} animate={{ y: 0, rotate: 0 }} transition={{ duration: 0.8, ease: EASE, delay: delay + i * 0.06 }}>
            {w}&nbsp;
          </motion.span>
        </span>
      ))}
    </span>
  );
}

export function Hero() {
  const { t, lang } = useI18n();
  const ref = useRef<HTMLElement>(null);
  const scrollRef = useRef(0);
  const [webgl, setWebgl] = useState(false);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  useMotionValueEvent(scrollYProgress, "change", (v) => { scrollRef.current = v; });
  const demoY = useTransform(scrollYProgress, [0, 1], [0, -80]);
  const textY = useTransform(scrollYProgress, [0, 1], [0, 60]);
  const fade = useTransform(scrollYProgress, [0, 0.7], [1, 0]);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setWebgl(!reduced && canWebGL());
  }, []);

  const trust = [
    { icon: <Languages className="h-4 w-4" />, text: t("hero.trust1") },
    { icon: <BookOpenCheck className="h-4 w-4" />, text: t("hero.trust2") },
    { icon: <UserRoundCheck className="h-4 w-4" />, text: t("hero.trust3") },
  ];

  return (
    <section ref={ref} className="ruled-plain paper-grain relative overflow-hidden pb-24 pt-32 sm:pt-36">
      {/* the red margin line of the notebook */}
      <div className="pointer-events-none absolute inset-y-0 left-[calc(50%-36rem)] hidden w-px bg-margin/60 xl:block" aria-hidden />

      {/* 3D plane, floating over the page */}
      <motion.div style={{ opacity: fade }} className="pointer-events-none absolute -right-16 -top-2 z-0 h-[220px] w-[300px] opacity-40 sm:opacity-60 lg:right-[1%] lg:top-4 lg:z-20 lg:h-[320px] lg:w-[460px] lg:opacity-100" aria-hidden>
        {webgl ? <Plane3D scrollRef={scrollRef} /> : <PlaneFallback />}
      </motion.div>

      <div className="relative z-10 mx-auto grid max-w-6xl items-center gap-14 px-5 lg:grid-cols-[1.08fr_1fr]">
        <motion.div style={{ y: textY }}>
          <motion.p initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="inline-flex items-center gap-2 rounded-full border border-line bg-surface/80 px-3 py-1 text-sm text-ink-2 backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-sage" />{t("hero.kicker")}
          </motion.p>
          <h1 key={lang} className="mt-6 font-display text-[clamp(2.9rem,7vw,5.6rem)] leading-[0.98] tracking-[-0.015em] text-ink">
            <Words text={t("hero.title1")} />
            <span className="relative inline-block">
              <Words text={t("hero.title2")} delay={0.35} className="relative z-10 italic text-sky-700" />
              <motion.span aria-hidden className="absolute inset-x-0 bottom-[0.12em] z-0 h-[0.38em] origin-left -rotate-1 rounded-sm bg-marigold/55"
                initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: 1.1, duration: 0.7, ease: EASE }} />
            </span>
          </h1>
          <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7, duration: 0.6 }} className="mt-6 max-w-xl text-lg leading-relaxed text-ink-2">
            {t("hero.sub")}
          </motion.p>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.85, duration: 0.6 }} className="mt-8 flex flex-wrap gap-3">
            <Button href="/signup" size="lg" icon={<ArrowRight className="h-4 w-4" />}>{t("hero.cta")}</Button>
            <Button size="lg" variant="outline" onClick={() => document.getElementById("demo")?.scrollIntoView({ behavior: "smooth", block: "center" })}>{t("hero.ctaSecondary")}</Button>
          </motion.div>
          <ul className="mt-10 flex flex-wrap gap-x-6 gap-y-2 text-sm text-ink-2">
            {trust.map((x, i) => (
              <motion.li key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1 + i * 0.1 }} className="inline-flex items-center gap-2">
                <span className="text-sky-600">{x.icon}</span>{x.text}
              </motion.li>
            ))}
          </ul>
        </motion.div>

        <motion.div id="demo" style={{ y: demoY }} initial={{ opacity: 0, y: 40, rotate: 2 }} animate={{ opacity: 1, rotate: 0 }} transition={{ delay: 0.4, duration: 0.9, ease: EASE }} className="relative">
          <span className="absolute -left-5 -top-7 rotate-[-6deg] font-hand text-xl text-sky-700">↓ {t("demo.label").split("·")[0].trim()}</span>
          <LessonDemo />
          {/* tape */}
          <span className="absolute -top-3 right-10 h-6 w-20 rotate-[5deg] rounded-sm bg-marigold-200/80 shadow-sm" aria-hidden />
        </motion.div>
      </div>

      <motion.button style={{ opacity: fade }} onClick={() => document.getElementById("problem")?.scrollIntoView({ behavior: "smooth" })}
        className="relative mx-auto mt-16 flex items-center gap-2 text-sm text-ink-3 hover:text-ink">
        <ArrowDown className="h-4 w-4 animate-bounce" />{t("hero.scroll")}
      </motion.button>
    </section>
  );
}
