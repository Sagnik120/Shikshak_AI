"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { ArrowRight, Brain, CalendarDays, CheckCheck, Clock, Flame, MessageSquareText, Sparkles, Target } from "lucide-react";
import { api } from "@/core/api";
import type { Analytics, Journey } from "@/core/types";
import { useI18n } from "@/providers/i18n";
import type { MessageKey } from "@/core/i18n";
import { Card, Skeleton } from "@/components/ui/primitives";
import { CountUp, Reveal } from "@/components/motion/reveal";
import { Donut, Legend, TimeChart } from "@/components/charts/charts";
import { BadgeCard, nextBadges } from "@/components/lesson/badges";
import { PlaneMark } from "@/components/brand/logo";
import { LoadError } from "@/components/ui/load-error";
import { cn, EASE } from "@/lib/utils";

const C = { right: "#7fb08f", wrong: "#e3a39a", minutes: "var(--sky-600)", acc: "var(--marigold-600)", rescued: "var(--sky-500)", stuck: "#e3a39a" };

export default function ProgressPage() {
  const { t } = useI18n();
  const j = useQuery({ queryKey: ["journey"], queryFn: api.journey, retry: 1 });
  const a = useQuery({ queryKey: ["analytics"], queryFn: api.analytics });
  return (
    <div className="mx-auto max-w-6xl px-5 py-8 lg:px-10 lg:py-10">
      <h1 className="font-display text-5xl text-ink sm:text-6xl">{t("progress.title")}</h1>
      <p className="mt-2 text-ink-2">{t("progress.sub")}</p>
      {j.isLoading && <Skeleton className="mt-8 h-80 rounded-[var(--radius)]" />}
      {j.isError && <LoadError className="mt-8" onRetry={() => j.refetch()} />}
      {j.data && (j.data.totals.answers === 0 && j.data.totals.lessons_started === 0 ? (
        <Card className="ruled mt-8 grid place-items-center px-6 py-16 text-center">
          <PlaneMark size={90} className="animate-float-soft" />
          <p className="mt-4 text-ink-2">{t("progress.empty")}</p>
        </Card>
      ) : <Body j={j.data} a={a.data} />)}
    </div>
  );
}

function LevelCard({ j }: { j: Journey }) {
  const { t, n } = useI18n();
  const lv = j.level;
  const pct = ((lv.xp - lv.floor) / Math.max(1, lv.next - lv.floor)) * 100;
  return (
    <motion.section initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: EASE }}
      className="ruled relative overflow-hidden rounded-[28px] border border-line bg-surface p-6 pl-20 shadow-[var(--shadow-lift)] sm:pl-24">
      <PlaneMark size={96} className="absolute -right-2 -top-3 rotate-12 opacity-70 animate-float-soft" />
      <div className="flex flex-wrap items-center gap-6">
        <div className="relative grid h-24 w-24 place-items-center rounded-full bg-gradient-to-br from-sky-500 to-sky-700 text-white shadow-[0_12px_30px_-10px_rgb(59_102_174/0.7)]">
          <span className="font-display text-5xl leading-none">{n(lv.level)}</span>
          <span className="absolute -bottom-2 rounded-full bg-marigold px-2 py-0.5 text-[0.65rem] font-bold text-ink">{t("lvl.level", { n: n(lv.level) })}</span>
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-hand text-xl text-sky-700">{t(`lvl.${lv.title}` as MessageKey)}</p>
          <p className="font-display text-4xl text-ink"><CountUp to={lv.xp} format={(v) => t("lvl.xp", { n: n(v) })} /></p>
          <div className="mt-3 h-3 max-w-xl overflow-hidden rounded-full bg-paper-3">
            <motion.div className="relative h-full rounded-full bg-gradient-to-r from-sky-300 via-sky-500 to-sky-600" initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 1.2, ease: EASE, delay: 0.3 }}>
              <span className="absolute inset-0 animate-[shimmer_2.5s_linear_infinite] bg-[linear-gradient(90deg,transparent,rgb(255_255_255/0.45),transparent)] bg-[length:200%_100%]" />
            </motion.div>
          </div>
          <p className="mt-1.5 text-xs text-ink-3">{t("lvl.toNext", { n: n(lv.next - lv.xp), l: n(lv.level + 1) })} · {t("lvl.how")}</p>
        </div>
        <div className="flex gap-3">
          <div className="rounded-2xl bg-marigold-50 px-4 py-3 text-center">
            <Flame className="mx-auto h-5 w-5 text-marigold-600" fill="currentColor" />
            <p className="font-display text-3xl text-ink">{n(j.streak.current)}</p>
            <p className="text-[0.68rem] text-ink-3">{t("cal.current")}</p>
          </div>
          <Link href="/profile#badges" className="rounded-2xl bg-sky-50 px-4 py-3 text-center transition-transform hover:-translate-y-0.5">
            <Sparkles className="mx-auto h-5 w-5 text-sky-700" />
            <p className="font-display text-3xl text-ink">{n(j.badges.filter((b) => b.earned).length)}</p>
            <p className="text-[0.68rem] text-ink-3">{t("badge.title")}</p>
          </Link>
        </div>
      </div>
    </motion.section>
  );
}

function Body({ j, a }: { j: Journey; a?: Analytics }) {
  const { t, n, lang } = useI18n();
  const [range, setRange] = useState(30);
  const tt = j.totals;
  const days = j.days.slice(-range);
  const dates = days.map((d) => d.date);
  // 7-day rolling accuracy, only where there were answers in the window.
  const accuracy = useMemo(() => j.days.map((_, i) => {
    const win = j.days.slice(Math.max(0, i - 6), i + 1);
    const ans = win.reduce((s, d) => s + d.answers, 0);
    return ans ? (win.reduce((s, d) => s + d.correct, 0) / ans) * 100 : NaN;
  }).slice(-range), [j.days, range]);
  const accFilled = accuracy.map((v, i) => (Number.isNaN(v) ? (accuracy.slice(0, i).reverse().find((x) => !Number.isNaN(x)) ?? 0) : v));
  const pctRight = tt.answers ? Math.round((tt.correct / tt.answers) * 100) : 0;
  const u = j.understanding;
  const m = j.mastery;
  const mTotal = Math.max(1, m.mastered + m.watched + m.learning + m.to_review + m.not_started);
  const mParts = [
    { k: "prog.m.mastered", v: m.mastered, c: "var(--sage)" }, { k: "prog.m.watched", v: m.watched, c: "#a9c9b4" },
    { k: "prog.m.learning", v: m.learning, c: "var(--sky-500)" }, { k: "prog.m.review", v: m.to_review, c: "var(--marigold-400)" },
    { k: "prog.m.new", v: m.not_started, c: "var(--paper-3)" },
  ];
  const wdNames = useMemo(() => Array.from({ length: 7 }, (_, i) => new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", { weekday: "short" }).format(new Date(2024, 0, 1 + i))), [lang]);
  const wdMax = Math.max(1, ...j.weekday);
  const hMax = Math.max(1, ...j.hours);
  const kpis = [
    { icon: <Clock />, label: t("prog.k.time"), v: tt.minutes, suffix: "", sub: t("prog.k.timeSub", { n: n(tt.videos) }) },
    { icon: <MessageSquareText />, label: t("prog.k.answers"), v: tt.answers, sub: t("prog.k.answersSub", { p: n(pctRight) }) },
    { icon: <CheckCheck />, label: t("prog.k.lessons"), v: tt.lessons_completed, sub: t("prog.k.lessonsSub", { n: n(tt.lessons_started) }) },
    { icon: <Brain />, label: t("prog.k.mastered"), v: tt.concepts_mastered, sub: t("prog.k.masteredSub", { n: n(m.to_review) }) },
    { icon: <Target />, label: t("prog.k.row"), v: tt.best_right_in_a_row, sub: t("prog.k.rowSub") },
    { icon: <CalendarDays />, label: t("prog.k.days"), v: j.streak.active_days, sub: t("prog.k.daysSub", { n: n(j.streak.longest) }) },
  ];

  return (
    <div className="mt-8 space-y-6">
      <LevelCard j={j} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {kpis.map((k, i) => (
          <motion.div key={k.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.05 }}>
            <Card lift className="h-full p-4">
              <span className="grid h-8 w-8 place-items-center rounded-xl bg-sky-50 text-sky-700 [&>svg]:h-4 [&>svg]:w-4">{k.icon}</span>
              <p className="mt-3 font-display text-4xl"><CountUp to={k.v} format={(v) => n(v)} /></p>
              <p className="text-xs font-medium text-ink">{k.label}</p>
              <p className="text-[0.7rem] text-ink-3">{k.sub}</p>
            </Card>
          </motion.div>
        ))}
      </div>

      <Card className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl">{t("prog.effort")}</h2>
            <p className="mt-1 text-sm text-ink-3">{t("prog.effortSub")}</p>
          </div>
          <div className="flex rounded-xl border border-line bg-paper-2 p-0.5 text-xs">
            {[7, 30, 90].map((d) => (
              <button key={d} onClick={() => setRange(d)} className={cn("relative rounded-lg px-3 py-1.5 font-medium", range === d ? "text-ink" : "text-ink-3")}>
                {range === d && <motion.span layoutId="prog-range" className="absolute inset-0 rounded-lg bg-surface shadow-[var(--shadow-soft)]" />}
                <span className="relative">{t("admin.days", { n: n(d) })}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4"><Legend items={[{ label: t("admin.s.right"), color: C.right }, { label: t("admin.s.wrong"), color: C.wrong }, { label: t("prog.minutes"), color: C.minutes, kind: "line" }]} /></div>
        <TimeChart className="mt-3" dates={dates} height={260} yLabel={t("admin.questions")} series={[
          { key: "right", label: t("admin.s.right"), color: C.right, kind: "bar", values: days.map((d) => d.correct) },
          { key: "wrong", label: t("admin.s.wrong"), color: C.wrong, kind: "bar", values: days.map((d) => d.answers - d.correct) },
          { key: "min", label: t("prog.minutes"), color: C.minutes, kind: "line", values: days.map((d) => d.minutes), format: (v) => t("cal.minutes", { n: n(Math.round(v)) }) },
        ]} />
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card className="p-6">
          <h2 className="font-display text-2xl">{t("prog.accuracy")}</h2>
          <p className="mt-1 text-sm text-ink-3">{t("prog.accuracySub")}</p>
          <TimeChart className="mt-4" dates={dates} height={220} yMax={100} yFormat={(v) => `${n(Math.round(v))}%`} series={[
            { key: "acc", label: t("prog.accuracyLine"), color: C.acc, kind: "line", values: accFilled, format: (v) => `${n(Math.round(v))}%` },
          ]} />
        </Card>
        <Card className="p-6">
          <h2 className="font-display text-2xl">{t("prog.understand")}</h2>
          <p className="mt-1 text-sm text-ink-3">{t("prog.understandSub")}</p>
          <div className="mt-5 flex flex-wrap items-center gap-6">
            <Donut size={150} parts={[
              { label: t("prog.firstTry"), value: u.first_try, color: C.right },
              { label: t("prog.afterHelp"), value: u.rescued, color: C.rescued },
              { label: t("prog.working"), value: u.still_stuck, color: C.stuck },
            ]} center={<div><p className="font-display text-3xl">{n(u.concepts_checked)}</p><p className="text-[0.65rem] text-ink-3">{t("admin.f.checked")}</p></div>} />
            <ul className="space-y-2.5 text-sm">
              {[[t("prog.firstTry"), u.first_try, C.right], [t("prog.afterHelp"), u.rescued, C.rescued], [t("prog.working"), u.still_stuck, C.stuck]].map(([l, v, c]) => (
                <li key={l as string} className="flex items-center gap-2"><i className="h-3 w-3 rounded-full" style={{ background: c as string }} /><span className="text-ink-2">{l}</span><span className="ml-auto pl-3 font-semibold tabular-nums">{n(v as number)}</span></li>
              ))}
            </ul>
          </div>
        </Card>
      </div>

      <Reveal>
        <Card className="p-6">
          <h2 className="font-display text-2xl">{t("prog.mastery")}</h2>
          <div className="mt-4 flex h-5 overflow-hidden rounded-full">
            {mParts.map((p, i) => p.v > 0 && (
              <motion.div key={p.k} title={`${t(p.k as MessageKey)}: ${p.v}`} style={{ background: p.c }} initial={{ width: 0 }} whileInView={{ width: `${(p.v / mTotal) * 100}%` }} viewport={{ once: true }} transition={{ duration: 0.8, ease: EASE, delay: i * 0.1 }} />
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm">
            {mParts.map((p) => <span key={p.k} className="flex items-center gap-1.5 text-ink-2"><i className="h-2.5 w-2.5 rounded-[3px]" style={{ background: p.c }} />{t(p.k as MessageKey)} <b className="tabular-nums text-ink">{n(p.v)}</b></span>)}
          </div>
        </Card>
      </Reveal>

      <div className="grid gap-6 lg:grid-cols-2">
        <Reveal>
          <Card className="h-full p-6">
            <h2 className="font-display text-2xl">{t("prog.strength")}</h2>
            <p className="mt-1 text-sm text-ink-3">{t("prog.strengthSub")}</p>
            <div className="mt-4 max-h-96 space-y-3 overflow-y-auto pr-1">
              {j.concepts.slice(0, 20).map((c, i) => (
                <div key={`${c.concept}-${i}`}>
                  <div className="flex items-baseline justify-between gap-3 text-sm">
                    <span className="truncate text-ink">{c.concept}</span>
                    <span className="shrink-0 tabular-nums text-ink-3">{n(c.mastery_pct)}%</span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-paper-3">
                    <motion.div className={cn("h-full rounded-full", c.mastery_pct >= 75 ? "bg-sage" : c.mastery_pct >= 50 ? "bg-marigold-400" : "bg-rose")}
                      initial={{ width: 0 }} whileInView={{ width: `${Math.max(3, c.mastery_pct)}%` }} viewport={{ once: true }} transition={{ duration: 0.8, ease: EASE, delay: i * 0.03 }} />
                  </div>
                  <p className="mt-0.5 text-[0.68rem] text-ink-3">{t("prog.tries", { n: n(c.attempts) })}{c.reexplains ? ` · ${t("prog.reexplained", { n: n(c.reexplains) })}` : ""}</p>
                </div>
              ))}
            </div>
          </Card>
        </Reveal>
        <Reveal delay={0.08}>
          <Card className="h-full p-6">
            <h2 className="font-display text-2xl">{t("prog.when")}</h2>
            <p className="mt-3 text-xs font-medium uppercase tracking-wider text-ink-3">{t("prog.weekday")}</p>
            <div className="mt-2 flex h-28 items-end gap-2">
              {j.weekday.map((v, i) => (
                <div key={i} className="flex flex-1 flex-col items-center gap-1">
                  <div className="flex h-20 w-full items-end"><motion.div className="w-full rounded-t-md bg-sky-500/80" initial={{ height: 0 }} whileInView={{ height: `${Math.max(4, (v / wdMax) * 100)}%` }} viewport={{ once: true }} transition={{ delay: i * 0.05, ease: EASE }} /></div>
                  <span className="text-[0.65rem] text-ink-3">{wdNames[i]}</span>
                </div>
              ))}
            </div>
            <p className="mt-5 text-xs font-medium uppercase tracking-wider text-ink-3">{t("prog.hour")}</p>
            <div className="mt-2 flex h-20 items-end gap-[3px]">
              {j.hours.map((v, h) => (
                <div key={h} className="group relative flex h-full flex-1 items-end">
                  <motion.div className="w-full rounded-t-sm bg-marigold-400/90" initial={{ height: 0 }} whileInView={{ height: `${Math.max(3, (v / hMax) * 100)}%` }} viewport={{ once: true }} transition={{ delay: h * 0.015 }} />
                  <span className="pointer-events-none absolute -top-6 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-ink px-1.5 py-0.5 text-[0.6rem] text-white group-hover:block">{n(h)}:00 · {n(v)}</span>
                </div>
              ))}
            </div>
            <div className="mt-1 flex justify-between text-[0.62rem] text-ink-3"><span>{n(0)}:00</span><span>{n(12)}:00</span><span>{n(23)}:00</span></div>
          </Card>
        </Reveal>
      </div>

      {a && a.misconceptions.length > 0 && (
        <Reveal>
          <Card className="p-6">
            <h2 className="font-display text-2xl">{t("progress.misconceptions")}</h2>
            <div className="mt-4 flex flex-wrap gap-2">
              {a.misconceptions.map((x) => <span key={x.tag} className="rounded-full border border-rose/30 bg-rose-100/50 px-3 py-1 text-sm text-ink-2">{x.tag} <b className="text-rose">×{n(x.count)}</b></span>)}
            </div>
          </Card>
        </Reveal>
      )}

      <Reveal>
        <Card className="p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-display text-2xl">{t("prog.nextBadges")}</h2>
            <Link href="/profile#badges" className="inline-flex items-center gap-1 text-sm text-sky-700 hover:underline">{t("prog.allBadges")}<ArrowRight className="h-4 w-4" /></Link>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">{nextBadges(j.badges, 4).map((b, i) => <BadgeCard key={b.id} b={b} index={i} />)}</div>
        </Card>
      </Reveal>
    </div>
  );
}
