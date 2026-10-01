"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { ArrowRight, BookCheck, Clock, Flame, Gauge, Hand, Plus, RefreshCw, Target, Trophy } from "lucide-react";
import { api } from "@/core/api";
import type { Dashboard } from "@/core/types";
import { useAuth } from "@/providers/auth";
import { useI18n } from "@/providers/i18n";
import { Button } from "@/components/ui/button";
import { Badge, Card, Ring, Skeleton } from "@/components/ui/primitives";
import { CountUp, Stagger, StaggerItem } from "@/components/motion/reveal";
import { LessonRow } from "@/components/lesson/lesson-row";
import { PlaneMark } from "@/components/brand/logo";
import { StreakCalendar } from "@/components/lesson/streak-calendar";
import { LoadError } from "@/components/ui/load-error";
import { relativeDays } from "@/lib/lesson";
import { cn, EASE } from "@/lib/utils";

function greetingKey() {
  const h = new Date().getHours();
  return h < 12 ? "dash.morning" : h < 17 ? "dash.afternoon" : "dash.evening";
}

export default function DashboardPage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const q = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard, refetchOnWindowFocus: true });
  const d = q.data;
  const empty = d && d.stats.lessons_started === 0;
  const first = user?.full_name.split(" ")[0] ?? "";

  return (
    <div className="mx-auto max-w-6xl px-5 py-8 lg:px-10 lg:py-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="font-hand text-xl text-sky-700">{t(greetingKey())},</motion.p>
          <motion.h1 initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: EASE }} className="font-display text-5xl text-ink sm:text-6xl">
            <span className="highlight">{first}</span>
          </motion.h1>
          <p className="mt-2 text-ink-2">{empty ? t("dash.subEmpty") : t("dash.sub")}</p>
        </div>
        <Button href="/new" icon={<Plus className="h-4 w-4" />}>{t("nav.newLesson")}</Button>
      </header>

      {q.isLoading && <DashSkeleton />}
      {q.isError && (
        <Card className="mt-8 flex items-center justify-between p-6">
          <p className="text-ink-2">{(q.error as Error).message}</p>
          <Button variant="outline" size="sm" onClick={() => q.refetch()} icon={<RefreshCw className="h-4 w-4" />}>{t("common.retry")}</Button>
        </Card>
      )}
      {empty && <EmptyState />}
      {d && !empty && <Filled d={d} />}
    </div>
  );
}

function Filled({ d }: { d: Dashboard }) {
  const { t, n } = useI18n();
  const s = d.stats;
  const journey = useQuery({ queryKey: ["journey"], queryFn: api.journey, retry: 1 });
  const stats = [
    { icon: <BookCheck />, label: t("dash.stat.lessons"), value: s.lessons_completed, tint: "text-sky-700 bg-sky-50" },
    { icon: <Trophy />, label: t("dash.stat.score"), value: s.average_score_pct, suffix: "%", tint: "text-marigold-600 bg-marigold-50" },
    { icon: <Target />, label: t("dash.stat.accuracy"), value: s.accuracy_pct, suffix: "%", tint: "text-sage bg-sage-100" },
    { icon: <Clock />, label: t("dash.stat.minutes"), value: s.learning_minutes, tint: "text-sky-700 bg-sky-50" },
    { icon: <Flame />, label: t("dash.stat.streak"), value: journey.data?.streak.current ?? s.streak_days, tint: "text-margin bg-margin-100" },
    { icon: <Gauge />, label: t("dash.stat.mastered"), value: s.concepts_mastered, tint: "text-sage bg-sage-100" },
  ];
  return (
    <div className="mt-8 space-y-6">
      {d.needs_attention.length > 0 && <Attention items={d.needs_attention} />}
      {d.resume_lesson && <Resume d={d} />}

      <Stagger className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {stats.map((x) => (
          <StaggerItem key={x.label}>
            <Card lift className="h-full p-4">
              <span className={cn("grid h-9 w-9 place-items-center rounded-xl [&>svg]:h-[18px] [&>svg]:w-[18px]", x.tint)}>{x.icon}</span>
              <p className="mt-4 font-display text-4xl text-ink"><CountUp to={x.value} suffix={x.suffix} format={(v) => n(v)} /></p>
              <p className="mt-0.5 text-xs text-ink-3">{x.label}</p>
            </Card>
          </StaggerItem>
        ))}
      </Stagger>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card className="p-5">
          <div className="mb-2 flex items-center justify-between px-1">
            <h2 className="font-display text-2xl">{t("dash.recent")}</h2>
            <Link href="/lessons" className="text-sm text-sky-700 hover:underline">{t("dash.viewAll")}</Link>
          </div>
          <div className="divide-y divide-line/70">
            {d.recent_lessons.slice(0, 6).map((l) => <LessonRow key={l.id} lesson={l} />)}
          </div>
        </Card>
        <div className="space-y-6">
          <Card className="p-5">
            {journey.data ? <StreakCalendar journey={journey.data} /> : journey.isError ? <LoadError onRetry={() => journey.refetch()} /> : <Skeleton className="h-96 rounded-2xl" />}
          </Card>
          <Card className="p-5">
            <h2 className="font-display text-2xl">{t("dash.trend")}</h2>
            <Trend points={d.score_trend} />
          </Card>
        </div>
      </div>

      {(d.strong_concepts.length > 0 || d.weak_concepts.length > 0) && (
        <div className="grid gap-6 md:grid-cols-2">
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-sage">{t("dash.strong")}</h3>
            <div className="mt-3 flex flex-wrap gap-2">{d.strong_concepts.map((c) => <Badge key={c} tone="sage">{c}</Badge>)}</div>
          </Card>
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-marigold-600">{t("dash.weak")}</h3>
            <div className="mt-3 flex flex-wrap gap-2">{d.weak_concepts.map((c) => <Badge key={c} tone="marigold">{c}</Badge>)}</div>
          </Card>
        </div>
      )}
    </div>
  );
}

function Attention({ items }: { items: Dashboard["needs_attention"] }) {
  const { t, lang } = useI18n();
  return (
    <section>
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink-2"><span className="h-2 w-2 animate-pulse rounded-full bg-marigold-600" />{t("dash.attention")}</h2>
      <div className="grid gap-3 md:grid-cols-2">
        {items.map((a) => (
          <motion.div key={`${a.kind}-${a.lesson_id}-${a.node_id ?? ""}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className={cn("flex items-center gap-4 rounded-[22px] border p-4", a.kind === "paused" ? "border-amber/30 bg-amber-100/60" : "border-marigold-200 bg-marigold-50")}>
            <span className={cn("grid h-11 w-11 shrink-0 place-items-center rounded-2xl text-white", a.kind === "paused" ? "bg-amber" : "bg-marigold-600")}>
              {a.kind === "paused" ? <Hand className="h-5 w-5" /> : <RefreshCw className="h-5 w-5" />}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium text-ink">{a.concept}</p>
              <p className="truncate text-xs text-ink-2">{a.lesson_title}{a.since ? ` · ${relativeDays(a.since, lang)}` : ""}</p>
            </div>
            <Button size="sm" variant={a.kind === "paused" ? "ink" : "marigold"} href={a.kind === "paused" ? `/learn/${a.lesson_id}` : `/review/${a.lesson_id}`}>
              {a.kind === "paused" ? t("dash.openLesson") : t("dash.reviewBtn")}
            </Button>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function Resume({ d }: { d: Dashboard }) {
  const { t, n } = useI18n();
  const l = d.resume_lesson!;
  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: EASE }}
      className="ruled relative overflow-hidden rounded-[28px] border border-line bg-surface p-6 pl-20 shadow-[var(--shadow-lift)] sm:p-8 sm:pl-24">
      <PlaneMark size={90} className="absolute -right-3 -top-3 rotate-12 opacity-80 animate-float-soft" />
      <p className="font-hand text-xl text-sky-700">{t("dash.resume")}</p>
      <h2 className="mt-1 max-w-xl font-display text-4xl leading-tight text-ink">{l.title}</h2>
      <div className="mt-5 flex flex-wrap items-center gap-5">
        <Ring value={l.progress_pct} size={64} stroke={6} color="var(--sky-600)" label={<span className="text-sm font-semibold">{n(Math.round(l.progress_pct))}%</span>} />
        <p className="text-sm text-ink-2">{n(l.nodes_completed)} / {n(l.node_count)}</p>
        <Button href={`/learn/${l.id}`} icon={<ArrowRight className="h-4 w-4" />} className="ml-auto">{t("dash.resumeBtn")}</Button>
      </div>
    </motion.div>
  );
}

function Trend({ points }: { points: Dashboard["score_trend"] }) {
  const { n } = useI18n();
  if (points.length < 2) return <p className="mt-6 text-sm text-ink-3">—</p>;
  const W = 300, H = 110;
  const xs = points.map((_, i) => (i / (points.length - 1)) * W);
  const ys = points.map((p) => H - (p.score_pct / 100) * (H - 10) - 5);
  const d = xs.map((x, i) => `${i ? "L" : "M"}${x.toFixed(1)} ${ys[i].toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H + 4}`} className="mt-4 w-full overflow-visible">
      {[25, 50, 75].map((g) => <line key={g} x1="0" x2={W} y1={H - (g / 100) * (H - 10) - 5} y2={H - (g / 100) * (H - 10) - 5} stroke="var(--line)" strokeDasharray="3 5" />)}
      <motion.path d={`${d} L${W} ${H} L0 ${H} Z`} fill="var(--sky-50)" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }} />
      <motion.path d={d} fill="none" stroke="var(--sky-600)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.2, ease: EASE }} />
      {xs.map((x, i) => (
        <g key={i}>
          <circle cx={x} cy={ys[i]} r="4" fill="var(--surface)" stroke="var(--sky-600)" strokeWidth="2" />
          <title>{n(Math.round(points[i].score_pct))}%</title>
        </g>
      ))}
    </svg>
  );
}

function EmptyState() {
  const { t } = useI18n();
  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} className="ruled mt-10 grid place-items-center rounded-[32px] border border-dashed border-line-2 bg-surface px-6 py-16 text-center">
      <PlaneMark size={110} animateIn className="animate-float-soft" />
      <h2 className="mt-6 font-display text-4xl">{t("dash.emptyTitle")}</h2>
      <p className="mt-2 max-w-md text-ink-2">{t("dash.emptyBody")}</p>
      <Button href="/new" size="lg" className="mt-8" icon={<Plus className="h-4 w-4" />}>{t("dash.startFirst")}</Button>
    </motion.div>
  );
}

function DashSkeleton() {
  return (
    <div className="mt-8 space-y-6">
      <Skeleton className="h-44 rounded-[28px]" />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-32 rounded-[var(--radius)]" />)}</div>
      <Skeleton className="h-72 rounded-[var(--radius)]" />
    </div>
  );
}
