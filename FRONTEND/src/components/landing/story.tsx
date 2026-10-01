"use client";

import { AnimatePresence, motion, useInView, useMotionTemplate, useMotionValue, useMotionValueEvent, useScroll, useSpring, useTransform } from "motion/react";
import { useLayoutEffect, useRef, useState } from "react";
import {
  ArrowRight, BookOpen, Brain, CheckCheck, Clapperboard, FileSearch, Film, Hand, Layers, ListChecks,
  Mail, PauseCircle, RefreshCw, ShieldCheck, Sparkles, Wand2, Wifi,
} from "lucide-react";
import { useI18n } from "@/providers/i18n";
import { translate, type MessageKey } from "@/core/i18n";
import { CountUp, Reveal, Stagger, StaggerItem } from "@/components/motion/reveal";
import { LanguageToggle } from "@/components/layout/language-toggle";
import { PlaneMark } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { cn, EASE } from "@/lib/utils";

function Kicker({ children, className }: { children: React.ReactNode; className?: string }) {
  return <p className={cn("font-hand text-xl text-sky-700", className)}>{children}</p>;
}
function Title({ children, className }: { children: React.ReactNode; className?: string }) {
  return <h2 className={cn("mt-2 font-display text-[clamp(2.2rem,5vw,4rem)] leading-[1.02] tracking-[-0.01em] text-ink", className)}>{children}</h2>;
}

/* ── 1. The problem: forty seats, one quiet student ─────────────────────── */

export function Problem() {
  const { t, n } = useI18n();
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const lostOn = useTransform(scrollYProgress, [0.2, 0.32], [0, 1]);
  const seenOn = useTransform(scrollYProgress, [0.55, 0.68], [0, 1]);
  const ringScale = useTransform(seenOn, [0, 1], [2.4, 1]);
  const [stage, setStage] = useState(0);
  useMotionValueEvent(scrollYProgress, "change", (v) => setStage(v < 0.3 ? 0 : v < 0.62 ? 1 : 2));
  const lostColor = useTransform(lostOn, [0, 1], ["#dfeaf9", "#e5917f"]);
  const LOST = 27;

  return (
    <section id="problem" ref={ref} className="relative h-[260vh] bg-paper">
      <div className="sticky top-0 flex min-h-dvh items-center overflow-hidden py-24">
        <div className="mx-auto grid w-full max-w-6xl items-center gap-12 px-5 lg:grid-cols-2">
          <div>
            <Kicker>{t("problem.kicker")}</Kicker>
            <Title>{t("problem.title")}</Title>
            <p className="mt-5 max-w-lg text-lg leading-relaxed text-ink-2">{t("problem.body")}</p>
            <div className="mt-6 h-16">
              <AnimatePresence mode="wait">
                <motion.p key={stage} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.4, ease: EASE }}
                  className={cn("font-display text-3xl", stage === 2 ? "text-sky-700" : stage === 1 ? "text-margin" : "text-ink-3")}>
                  {stage === 0 ? "…" : stage === 1 ? <>{t("landing.lost")} <span className="block text-lg text-ink-3">{t("landing.lostSub")}</span></> : t("landing.seen")}
                </motion.p>
              </AnimatePresence>
            </div>
          </div>
          {/* the classroom: 40 desks */}
          <div className="relative rounded-[28px] border border-line bg-surface p-6 shadow-[var(--shadow-soft)] sm:p-8">
            <div className="mb-5 h-2 w-1/2 rounded-full bg-[#2a3a5c]/85" title="board" />
            <div className="grid grid-cols-8 gap-3 sm:gap-4">
              {Array.from({ length: 40 }, (_, i) => (
                <div key={i} className="relative grid aspect-square place-items-center">
                  {i === LOST ? (
                    <>
                      <motion.span className="h-full w-full rounded-full border-2" style={{ backgroundColor: lostColor, borderColor: "var(--line-2)" }} />
                      <motion.span style={{ opacity: seenOn, scale: ringScale }} className="absolute -inset-2 rounded-full border-2 border-sky-600" />
                      <motion.span style={{ opacity: seenOn }} className="absolute -inset-2 animate-pulse-ring rounded-full border-2 border-sky-300" />
                    </>
                  ) : (
                    <motion.span className="h-full w-full rounded-full bg-sky-100" initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }} transition={{ delay: (i % 8) * 0.03 + Math.floor(i / 8) * 0.05 }} />
                  )}
                </div>
              ))}
            </div>
            <div className="mt-8 grid grid-cols-3 gap-4 border-t border-dashed border-line-2 pt-6 text-center">
              {[[40, "", "problem.stat1"], [70, "%", "problem.stat2"], [90, "", "problem.stat3"]].map(([v, s, k]) => (
                <div key={k as string}>
                  <p className="font-display text-4xl text-ink"><CountUp to={v as number} suffix={s as string} format={(x) => n(x)} /></p>
                  <p className="mt-1 text-xs leading-snug text-ink-3">{t(k as MessageKey)}</p>
                </div>
              ))}
            </div>
            <p className="mt-4 text-center text-[0.7rem] text-ink-3">{t("problem.note")}</p>
          </div>
        </div>
      </div>
    </section>
  );
}


/* ── 2. The loop: eight steps, scrolled sideways ────────────────────────── */

const STEPS: Array<{ k: MessageKey; d: MessageKey; icon: React.ReactNode; tint: string }> = [
  { k: "loop.s1", d: "loop.s1d", icon: <FileSearch />, tint: "bg-sky-50" },
  { k: "loop.s2", d: "loop.s2d", icon: <ListChecks />, tint: "bg-marigold-50" },
  { k: "loop.s3", d: "loop.s3d", icon: <Wand2 />, tint: "bg-sage-100" },
  { k: "loop.s4", d: "loop.s4d", icon: <Clapperboard />, tint: "bg-sky-50" },
  { k: "loop.s5", d: "loop.s5d", icon: <PauseCircle />, tint: "bg-marigold-100" },
  { k: "loop.s6", d: "loop.s6d", icon: <CheckCheck />, tint: "bg-sage-100" },
  { k: "loop.s7", d: "loop.s7d", icon: <RefreshCw />, tint: "bg-margin-100" },
  { k: "loop.s8", d: "loop.s8d", icon: <Hand />, tint: "bg-amber-100" },
];

function StepCard({ i, s }: { i: number; s: (typeof STEPS)[number] }) {
  const { t, n } = useI18n();
  return (
    <article className={cn("ruled-plain relative flex h-full flex-col rounded-[26px] border border-line bg-surface p-6 shadow-[var(--shadow-soft)] transition-transform duration-500 hover:-translate-y-1.5 hover:rotate-[-0.6deg]")}>
      <div className="flex items-start justify-between">
        <span className={cn("grid h-12 w-12 place-items-center rounded-2xl text-sky-700 [&>svg]:h-6 [&>svg]:w-6", s.tint)}>{s.icon}</span>
        <span className="font-display text-6xl leading-none text-line-2">{n(String(i + 1).padStart(2, "0"))}</span>
      </div>
      <p className="mt-auto pt-10 text-xs uppercase tracking-widest text-ink-3">{t("landing.step")} {n(i + 1)}</p>
      <h3 className="mt-1 font-display text-3xl text-ink">{t(s.k)}</h3>
      <p className="mt-2 text-ink-2">{t(s.d)}</p>
    </article>
  );
}

export function Loop() {
  const { t } = useI18n();
  const ref = useRef<HTMLElement>(null);
  const track = useRef<HTMLDivElement>(null);
  const [dist, setDist] = useState(0);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const x = useSpring(useTransform(scrollYProgress, [0.05, 0.95], [0, -dist]), { stiffness: 120, damping: 26, mass: 0.4 });
  const bar = useTransform(scrollYProgress, [0.05, 0.95], ["0%", "100%"]);

  useLayoutEffect(() => {
    const measure = () => track.current && setDist(Math.max(0, track.current.scrollWidth - window.innerWidth + 40));
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  return (
    <section id="loop" ref={ref} className="relative bg-paper-2 md:h-[340vh]">
      <div className="dotted md:sticky md:top-0 md:flex md:h-dvh md:flex-col md:justify-center md:overflow-hidden">
        <div className="mx-auto w-full max-w-6xl px-5 pt-24 md:pt-0">
          <Kicker>{t("loop.kicker")}</Kicker>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <Title>{t("loop.title")}</Title>
            <p className="max-w-sm text-ink-2">{t("loop.sub")}</p>
          </div>
        </div>
        {/* desktop: horizontal */}
        <motion.div ref={track} style={{ x }} className="mt-10 hidden gap-5 pl-[max(1.25rem,calc(50%-36rem))] pr-10 md:flex">
          {STEPS.map((s, i) => <div key={s.k} className="h-[340px] w-[300px] shrink-0"><StepCard i={i} s={s} /></div>)}
        </motion.div>
        <div className="mx-auto mt-8 hidden h-1 w-full max-w-6xl px-5 md:block">
          <div className="h-full rounded-full bg-line"><motion.div style={{ width: bar }} className="h-full rounded-full bg-sky-600" /></div>
        </div>
        {/* mobile: stacked */}
        <Stagger className="mt-8 grid gap-4 px-5 pb-20 md:hidden">
          {STEPS.map((s, i) => <StaggerItem key={s.k}><StepCard i={i} s={s} /></StaggerItem>)}
        </Stagger>
      </div>
    </section>
  );
}

/* ── 3. The visitor's own checkpoint ────────────────────────────────────── */

export function VisitorCheck() {
  const { t } = useI18n();
  const [pick, setPick] = useState<string | null>(null);
  const opts: Array<[string, MessageKey]> = [["a1", "visitorCheck.a1"], ["a2", "visitorCheck.a2"], ["a3", "visitorCheck.a3"]];
  const right = pick === "a2";
  return (
    <section className="relative bg-paper py-28">
      <Reveal className="mx-auto max-w-3xl px-5">
        <div className="relative rounded-[30px] border-2 border-dashed border-marigold-400 bg-marigold-50 p-7 sm:p-10">
          <span className="absolute -top-5 left-8 grid h-10 w-10 place-items-center rounded-full bg-marigold text-ink shadow"><PauseCircle className="h-5 w-5" /></span>
          <Kicker className="text-marigold-600">{t("visitorCheck.kicker")}</Kicker>
          <h3 className="mt-2 font-display text-3xl leading-tight text-ink sm:text-4xl">{t("visitorCheck.q")}</h3>
          <div className="mt-6 grid gap-3">
            {opts.map(([id, key]) => {
              const chosen = pick === id;
              return (
                <motion.button key={id} onClick={() => setPick(id)} whileTap={{ scale: 0.98 }}
                  animate={chosen && id !== "a2" ? { x: [0, -8, 8, -4, 0] } : {}}
                  className={cn("rounded-2xl border bg-surface px-5 py-4 text-left transition-colors",
                    chosen ? (id === "a2" ? "border-sage bg-sage-100" : "border-rose/50 bg-rose-100/50") : "border-line hover:border-sky-300")}>
                  {t(key)}
                </motion.button>
              );
            })}
          </div>
          <AnimatePresence mode="wait">
            {pick && (
              <motion.p key={String(right)} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className={cn("mt-5 flex items-start gap-2 font-medium", right ? "text-sage" : "text-rose")} role="status">
                {right ? <Sparkles className="mt-0.5 h-5 w-5 shrink-0" /> : <RefreshCw className="mt-0.5 h-5 w-5 shrink-0" />}
                {right ? t("visitorCheck.right") : t("visitorCheck.wrong")}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      </Reveal>
    </section>
  );
}

/* ── 4. The adaptation ladder ───────────────────────────────────────────── */

export function Ladder() {
  const { t } = useI18n();
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 75%", "end 55%"] });
  const fill = useSpring(scrollYProgress, { stiffness: 140, damping: 30 });
  const rungs: Array<{ k: MessageKey; d: MessageKey; icon: React.ReactNode; tone: string }> = [
    { k: "ladder.r1", d: "ladder.r1d", icon: <RefreshCw className="h-5 w-5" />, tone: "bg-sky-600" },
    { k: "ladder.r2", d: "ladder.r2d", icon: <Film className="h-5 w-5" />, tone: "bg-marigold-600" },
    { k: "ladder.r3", d: "ladder.r3d", icon: <Hand className="h-5 w-5" />, tone: "bg-margin" },
  ];
  return (
    <section id="ladder" className="relative bg-paper py-28">
      <div className="mx-auto grid max-w-6xl gap-14 px-5 lg:grid-cols-[1fr_1.1fr]">
        <div className="lg:sticky lg:top-32 lg:self-start">
          <Kicker>{t("ladder.kicker")}</Kicker>
          <Title>{t("ladder.title")}</Title>
        </div>
        <div ref={ref} className="relative pl-14">
          <div className="absolute bottom-6 left-[22px] top-6 w-[3px] rounded-full bg-line" />
          <motion.div style={{ scaleY: fill }} className="absolute bottom-6 left-[22px] top-6 w-[3px] origin-top rounded-full bg-gradient-to-b from-sky-600 via-marigold-400 to-margin" />
          {rungs.map((r, i) => (
            <Reveal key={r.k} delay={i * 0.05} className="relative mb-6 last:mb-0">
              <span className={cn("absolute -left-14 top-5 grid h-11 w-11 place-items-center rounded-full text-white shadow-[var(--shadow-soft)] ring-4 ring-paper", r.tone)}>{r.icon}</span>
              <div className="rounded-[24px] border border-line bg-surface p-6 shadow-[var(--shadow-soft)]">
                <h3 className="font-display text-3xl text-ink">{t(r.k)}</h3>
                <p className="mt-1.5 text-ink-2">{t(r.d)}</p>
                {i === 2 && (
                  <motion.div initial={{ opacity: 0, y: 12, rotate: -2 }} whileInView={{ opacity: 1, y: 0, rotate: -1 }} viewport={{ once: true }} transition={{ delay: 0.3, ease: EASE, duration: 0.6 }}
                    className="mt-5 rounded-2xl border border-line bg-paper-2 p-4">
                    <p className="flex items-center gap-2 text-xs text-ink-3"><Mail className="h-3.5 w-3.5" />{t("landing.mentorTo")}</p>
                    <p className="mt-1.5 text-sm text-ink">{t("landing.mentorMail")}</p>
                    <p className="mt-2 font-hand text-lg text-margin">— {t("landing.human")}</p>
                  </motion.div>
                )}
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── 5. Grounded in your own notes ──────────────────────────────────────── */

export function Grounded() {
  const { t } = useI18n();
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-120px" });
  return (
    <section id="grounded" className="relative overflow-hidden bg-paper-2 py-28">
      <div className="mx-auto grid max-w-6xl items-center gap-14 px-5 lg:grid-cols-2">
        <div>
          <Kicker>{t("grounded.kicker")}</Kicker>
          <Title>{t("grounded.title")}</Title>
          <p className="mt-5 max-w-lg text-lg leading-relaxed text-ink-2">{t("grounded.body")}</p>
        </div>
        <div ref={ref} className="relative">
          {/* the uploaded chapter */}
          <motion.div initial={{ rotate: 3, y: 30, opacity: 0 }} animate={inView ? { rotate: 1.5, y: 0, opacity: 1 } : {}} transition={{ duration: 0.8, ease: EASE }}
            className="ruled relative rounded-[6px] border border-line bg-surface px-10 pb-12 pt-10 shadow-[var(--shadow-lift)]">
            <div className="absolute inset-y-0 left-7 w-px bg-margin/70" />
            <p className="font-display text-2xl text-ink">9.4 Second Law of Motion</p>
            {[92, 78, 85].map((w, i) => <div key={i} className="mt-[13px] h-2.5 rounded bg-paper-3" style={{ width: `${w}%` }} />)}
            <p className="relative mt-4 text-[0.95rem] leading-7 text-ink-2">
              <motion.span className="absolute -inset-x-1 inset-y-0 origin-left rounded bg-marigold/45" initial={{ scaleX: 0 }} animate={inView ? { scaleX: 1 } : {}} transition={{ delay: 0.7, duration: 0.9, ease: EASE }} />
              <span className="relative">{t("grounded.quote")}</span>
            </p>
            {[88, 64].map((w, i) => <div key={i} className="mt-[13px] h-2.5 rounded bg-paper-3" style={{ width: `${w}%` }} />)}
          </motion.div>
          {/* the citation it produces */}
          <motion.div initial={{ opacity: 0, x: 40, y: 10 }} animate={inView ? { opacity: 1, x: 0, y: 0 } : {}} transition={{ delay: 1.4, duration: 0.6, ease: EASE }}
            className="absolute -bottom-6 -left-4 flex max-w-[90%] items-center gap-3 rounded-2xl border border-line bg-surface px-4 py-3 shadow-[var(--shadow-lift)] sm:-left-10">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-sky-50 text-sky-700"><BookOpen className="h-4 w-4" /></span>
            <span className="text-sm text-ink-2">{t("grounded.source")}</span>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

/* ── 6. Your language ───────────────────────────────────────────────────── */

export function Langs() {
  const { t } = useI18n();
  const keys: MessageKey[] = ["demo.caption1", "demo.caption2", "demo.caption3"];
  return (
    <section id="langs" className="relative bg-paper py-28">
      <div className="mx-auto max-w-6xl px-5">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <Kicker>{t("langs.kicker")}</Kicker>
            <Title>{t("langs.title")}</Title>
            <p className="mt-4 max-w-lg text-lg text-ink-2">{t("langs.body")}</p>
          </div>
          <LanguageToggle className="scale-125" />
        </div>
        <p className="mt-12 text-sm text-ink-3">{t("landing.sameLesson")}</p>
        <div className="mt-3 grid gap-5 md:grid-cols-2">
          {(["en", "hi"] as const).map((l, col) => (
            <Reveal key={l} delay={col * 0.12}>
              <div className="rounded-[26px] border border-line bg-surface p-6 shadow-[var(--shadow-soft)]" lang={l}>
                <p className="font-display text-4xl text-ink">{l === "en" ? "English" : "हिन्दी"}</p>
                <ol className="mt-4 space-y-3">
                  {keys.map((k, i) => (
                    <li key={k} className="flex gap-3 text-ink-2">
                      <span className="font-hand text-lg text-sky-600">{l === "hi" ? "१२३"[i] : i + 1}</span>
                      <span>{translate(l, k)}</span>
                    </li>
                  ))}
                </ol>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── 7. Numbers ─────────────────────────────────────────────────────────── */

export function Numbers() {
  const { t, n } = useI18n();
  const items: Array<{ v: React.ReactNode; k: MessageKey }> = [
    { v: n(t("landing.n1v")), k: "numbers.n1" },
    { v: <CountUp to={2} format={(x) => n(x)} />, k: "numbers.n2" },
    { v: <CountUp to={100} suffix="%" format={(x) => n(x)} />, k: "numbers.n3" },
    { v: <CountUp to={2} format={(x) => n(x)} />, k: "numbers.n4" },
  ];
  return (
    <section className="border-y border-line bg-surface py-16">
      <div className="mx-auto max-w-6xl px-5">
        <Kicker>{t("numbers.kicker")}</Kicker>
        <Stagger className="mt-6 grid grid-cols-2 gap-8 lg:grid-cols-4">
          {items.map((it) => (
            <StaggerItem key={it.k}>
              <p className="font-display text-6xl text-ink">{it.v}</p>
              <p className="mt-2 text-sm text-ink-2">{t(it.k)}</p>
            </StaggerItem>
          ))}
        </Stagger>
      </div>
    </section>
  );
}

/* ── 8. Under the hood: a bento with a spotlight ────────────────────────── */

function Spot({ children, className }: { children: React.ReactNode; className?: string }) {
  const mx = useMotionValue(-200), my = useMotionValue(-200);
  const bg = useMotionTemplate`radial-gradient(260px circle at ${mx}px ${my}px, rgb(59 102 174 / 0.09), transparent 70%)`;
  return (
    <div onPointerMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); mx.set(e.clientX - r.left); my.set(e.clientY - r.top); }}
      onPointerLeave={() => { mx.set(-200); my.set(-200); }}
      className={cn("group relative overflow-hidden rounded-[26px] border border-line bg-surface p-6 transition-shadow hover:shadow-[var(--shadow-lift)]", className)}>
      <motion.div className="pointer-events-none absolute inset-0" style={{ background: bg }} />
      <div className="relative">{children}</div>
    </div>
  );
}

export function Hood() {
  const { t } = useI18n();
  const cells: Array<{ k: MessageKey; d: MessageKey; icon: React.ReactNode; span: string }> = [
    { k: "hood.b1", d: "hood.b1d", icon: <FileSearch />, span: "md:col-span-2" },
    { k: "hood.b2", d: "hood.b2d", icon: <PauseCircle />, span: "" },
    { k: "hood.b3", d: "hood.b3d", icon: <Layers />, span: "" },
    { k: "hood.b4", d: "hood.b4d", icon: <Clapperboard />, span: "md:col-span-2" },
    { k: "hood.b5", d: "hood.b5d", icon: <Wifi />, span: "" },
    { k: "hood.b6", d: "hood.b6d", icon: <ShieldCheck />, span: "md:col-span-2" },
  ];
  return (
    <section id="hood" className="bg-paper-2 py-28">
      <div className="mx-auto max-w-6xl px-5">
        <Kicker>{t("hood.kicker")}</Kicker>
        <Title>{t("hood.title")}</Title>
        <Stagger className="mt-12 grid gap-4 md:grid-cols-3">
          {cells.map((c) => (
            <StaggerItem key={c.k} className={c.span}>
              <Spot className="h-full">
                <span className="grid h-11 w-11 place-items-center rounded-2xl bg-sky-50 text-sky-700 transition-transform duration-500 group-hover:rotate-[-8deg] group-hover:scale-110 [&>svg]:h-5 [&>svg]:w-5">{c.icon}</span>
                <h3 className="mt-5 text-lg font-semibold text-ink">{t(c.k)}</h3>
                <p className="mt-1.5 text-ink-2">{t(c.d)}</p>
              </Spot>
            </StaggerItem>
          ))}
        </Stagger>
        <p className="mt-6 flex items-center gap-2 text-sm text-ink-3"><Brain className="h-4 w-4" />Gemini · FastAPI · hybrid RAG · Next.js</p>
      </div>
    </section>
  );
}

/* ── 9. Final call: the page folds and flies ────────────────────────────── */

export function Final({ signedIn }: { signedIn: boolean }) {
  const { t } = useI18n();
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end end"] });
  const dist = useTransform(scrollYProgress, [0.1, 0.95], ["0%", "100%"]);
  const draw = useTransform(scrollYProgress, [0.1, 0.95], [0, 1]);
  return (
    <section ref={ref} className="ruled relative overflow-hidden bg-paper pb-16 pt-36">
      <svg className="pointer-events-none absolute left-1/2 top-10 h-[200px] w-[1200px] -translate-x-1/2" viewBox="0 0 1200 200" aria-hidden>
        <motion.path d="M-20 170 C 250 40, 420 210, 640 100 S 1000 10, 1220 60" fill="none" stroke="var(--sky-300)" strokeWidth="2" strokeDasharray="5 9" style={{ pathLength: draw }} />
      </svg>
      <motion.div className="pointer-events-none absolute left-[calc(50%-600px)] top-10 h-0 w-0" aria-hidden
        style={{ offsetPath: "path('M-20 170 C 250 40, 420 210, 640 100 S 1000 10, 1220 60')", offsetDistance: dist, offsetRotate: "auto 20deg" }}>
        <PlaneMark size={56} />
      </motion.div>
      <div className="relative mx-auto max-w-4xl px-5 text-center">
        <Reveal>
          <h2 className="font-display text-[clamp(2.6rem,7vw,5.5rem)] leading-[1] text-ink">{t("final.title")}</h2>
        </Reveal>
        <Reveal delay={0.15} className="mt-10 flex flex-wrap justify-center gap-3">
          <Button href={signedIn ? "/dashboard" : "/signup"} size="lg" icon={<ArrowRight className="h-4 w-4" />}>{signedIn ? t("nav.openApp") : t("final.cta")}</Button>
          {!signedIn && <Button href="/login" size="lg" variant="outline">{t("final.signin")}</Button>}
        </Reveal>
      </div>
    </section>
  );
}
