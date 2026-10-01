"use client";

import { useDeferredValue, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { Activity, AlertTriangle, BookOpen, Brain, Clock, Cpu, Gauge, Hand, Mail, MailX, Radio, Server, ShieldAlert, Sparkles, Users, Video, X } from "lucide-react";
import { api, ApiError } from "@/core/api";
import type { AdminLearners } from "@/core/types";
import { useAuth } from "@/providers/auth";
import { useI18n } from "@/providers/i18n";
import type { MessageKey } from "@/core/i18n";
import { Avatar } from "@/components/brand/avatar";
import { Badge, Card, Ring, Skeleton } from "@/components/ui/primitives";
import { GlassSearch } from "@/components/ui/glass-search";
import { CountUp } from "@/components/motion/reveal";
import { LessonRow } from "@/components/lesson/lesson-row";
import { Legend, TimeChart } from "@/components/charts/charts";
import { relativeDays } from "@/lib/lesson";
import { cn, EASE } from "@/lib/utils";
import { tabsFor, type StaffTab } from "@/lib/staff";
import { useRouter, useSearchParams } from "next/navigation";

type Tab = StaffTab;

export default function AdminPage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const tabs = tabsFor(user);
  const asked = params.get("tab") as Tab | null;
  const tab: Tab = tabs.some((x) => x.v === asked) ? asked! : "overview";
  const setTab = (v: Tab) => router.replace(`/admin?tab=${v}`, { scroll: false });
  const teacher = user?.role === "teacher";
  const overview = useQuery({ queryKey: ["admin", "overview", 14], queryFn: () => api.admin.overview(14), refetchInterval: 15000, retry: false });
  const forbidden = overview.error instanceof ApiError && overview.error.status === 403;
  if (forbidden || (user && user.role !== "admin" && user.role !== "teacher" && overview.isError)) {
    return <div className="grid min-h-[60vh] place-items-center text-center"><div><ShieldAlert className="mx-auto h-10 w-10 text-rose" /><p className="mt-3 text-ink-2">{t("admin.forbidden")}</p></div></div>;
  }
  const o = overview.data;
  return (
    <div className="mx-auto max-w-7xl px-5 py-8 lg:px-10 lg:py-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="flex items-center gap-2 font-hand text-xl text-sky-700"><span className="relative flex h-2.5 w-2.5"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-sage opacity-60" /><span className="relative h-2.5 w-2.5 rounded-full bg-sage" /></span>{t("admin.refresh", { n: 15 })}</p>
          <h1 className="font-display text-5xl text-ink sm:text-6xl">{t(teacher ? "staff.teacherTitle" : "admin.title")}</h1>
          <p className="mt-2 text-ink-2">{t(teacher ? "staff.teacherSub" : "admin.sub")}</p>
        </div>
      </header>

      <div className="no-scrollbar sticky top-0 z-30 -mx-5 mt-8 overflow-x-auto bg-paper/90 px-5 py-2 backdrop-blur lg:hidden">
        <div className="flex w-max gap-1 rounded-2xl border border-line bg-surface p-1">
          {tabs.map((x) => (
            <button key={x.v} onClick={() => setTab(x.v)} className={cn("relative flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-medium transition-colors", tab === x.v ? "text-white" : "text-ink-2 hover:text-ink")}>
              {tab === x.v && <motion.span layoutId="admin-tab" className="absolute inset-0 rounded-xl bg-ink" transition={{ type: "spring", stiffness: 450, damping: 34 }} />}
              <span className="relative">{x.icon}</span><span className="relative">{t(x.k)}</span>
              {x.v === "escalations" && (o?.open_escalations ?? 0) > 0 && <span className="relative rounded-full bg-marigold px-1.5 text-[0.65rem] font-bold text-ink">{o!.open_escalations}</span>}
              {x.v === "live" && (o?.live_now ?? 0) > 0 && <span className="relative h-1.5 w-1.5 animate-pulse rounded-full bg-sage" />}
            </button>
          ))}
        </div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={tab} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.3, ease: EASE }} className="mt-6 lg:mt-10">
          <h2 className="hidden items-center gap-2 font-display text-3xl text-ink lg:flex">{tabs.find((x) => x.v === tab)?.icon}{t(tabs.find((x) => x.v === tab)!.k)}</h2>
          <p className="mb-6 mt-1 max-w-3xl text-sm text-ink-3">{t(`admin.desc.${tab}` as MessageKey)}</p>
          {tab === "overview" && <Overview />}
          {tab === "live" && <Live />}
          {tab === "escalations" && <Escalations />}
          {tab === "insights" && <Insights />}
          {tab === "quality" && <Quality />}
          {tab === "pipeline" && <Pipeline />}
          {tab === "learners" && <Learners />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

function Stat({ icon, label, value, suffix, tone = "sky" }: { icon: React.ReactNode; label: string; value: number; suffix?: string; tone?: "sky" | "sage" | "marigold" | "rose" }) {
  const { n } = useI18n();
  const tones = { sky: "bg-sky-50 text-sky-700", sage: "bg-sage-100 text-sage", marigold: "bg-marigold-50 text-marigold-600", rose: "bg-rose-100 text-rose" };
  return (
    <Card lift className="p-5">
      <span className={cn("grid h-9 w-9 place-items-center rounded-xl [&>svg]:h-[18px] [&>svg]:w-[18px]", tones[tone])}>{icon}</span>
      <p className="mt-4 font-display text-4xl"><CountUp to={value} suffix={suffix} format={(v) => n(v)} /></p>
      <p className="text-xs text-ink-3">{label}</p>
    </Card>
  );
}

function Loading() { return <div className="grid gap-4 md:grid-cols-3">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-32 rounded-[var(--radius)]" />)}</div>; }
function NoData() { const { t } = useI18n(); return <p className="py-6 text-sm text-ink-3">{t("admin.noData")}</p>; }

function Kpi({ icon, label, value, sub, tone = "sky" }: { icon: React.ReactNode; label: string; value: React.ReactNode; sub: string; tone?: "sky" | "sage" | "marigold" | "rose" }) {
  const tones = { sky: "bg-sky-50 text-sky-700", sage: "bg-sage-100 text-sage", marigold: "bg-marigold-50 text-marigold-600", rose: "bg-rose-100 text-rose" };
  return (
    <Card lift className="p-5">
      <div className="flex items-center gap-2">
        <span className={cn("grid h-8 w-8 place-items-center rounded-xl [&>svg]:h-4 [&>svg]:w-4", tones[tone])}>{icon}</span>
        <p className="text-sm font-medium text-ink">{label}</p>
      </div>
      <p className="mt-3 font-display text-4xl text-ink">{value}</p>
      <p className="mt-0.5 text-xs text-ink-3">{sub}</p>
    </Card>
  );
}

const C = { right: "#7fb08f", wrong: "#e3a39a", rescued: "var(--sky-600)", human: "var(--margin)", started: "var(--sky-200)", completed: "var(--sky-600)" };

function Overview() {
  const { t, n } = useI18n();
  const [days, setDays] = useState(14);
  const q = useQuery({ queryKey: ["admin", "overview", days], queryFn: () => api.admin.overview(days), refetchInterval: 15000, placeholderData: (p) => p });
  const o = q.data;
  if (!o) return <Loading />;
  // Tolerate an older backend that predates the funnel / richer daily series.
  const daily = (o.daily ?? []).map((d) => ({
    ...d, right: d.right ?? 0, wrong: d.wrong ?? 0, rescued: d.rescued ?? 0,
    escalations: d.escalations ?? 0, completed: d.completed ?? 0, started: d.started ?? d.lessons ?? 0,
  }));
  const dates = daily.map((d) => d.date);
  const f = o.funnel ?? { concepts_checked: 0, first_time: 0, rescued: 0, still_stuck: 0, needed_human: 0 };
  const struggled = f.rescued + f.still_stuck;
  const saved = struggled ? Math.round((f.rescued / struggled) * 100) : 0;
  const rows = [
    { label: t("admin.f.checked"), v: f.concepts_checked, color: "var(--ink-3)" },
    { label: t("admin.f.first"), v: f.first_time, color: C.right },
    { label: t("admin.f.rescued"), v: f.rescued, color: C.rescued },
    { label: t("admin.f.stuck"), v: f.still_stuck, color: C.wrong },
    { label: t("admin.f.human"), v: f.needed_human, color: C.human },
  ];
  const max = Math.max(1, f.concepts_checked);
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Kpi icon={<Users />} label={t("admin.kpi.students")} value={<CountUp to={o.learners} format={(v) => n(v)} />} sub={t("admin.kpi.studentsSub")} />
        <Kpi icon={<Activity />} label={t("admin.activeToday")} value={<CountUp to={o.active_today} format={(v) => n(v)} />} sub={t("admin.kpi.activeSub")} tone="sage" />
        <Kpi icon={<Radio />} label={t("admin.liveNow")} value={<CountUp to={o.live_now} format={(v) => n(v)} />} sub={t("admin.kpi.liveSub")} tone="sage" />
        <Kpi icon={<Hand />} label={t("admin.openEsc")} value={<CountUp to={o.open_escalations} format={(v) => n(v)} />} sub={t("admin.kpi.waitingSub")} tone={o.open_escalations ? "marigold" : "sky"} />
        <Kpi icon={<BookOpen />} label={t("admin.kpi.finished")} value={<CountUp to={o.completed} format={(v) => n(v)} />} sub={t("admin.kpi.finishedSub", { n: n(o.lessons) })} />
        <Kpi icon={<Gauge />} label={t("admin.avgScore")} value={<CountUp to={Math.round(o.avg_score_pct)} suffix="%" format={(v) => n(v)} />} sub={t("admin.kpi.scoreSub")} tone="marigold" />
      </div>

      <Card className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="max-w-2xl">
            <h2 className="font-display text-2xl">{t("admin.pulse")}</h2>
            <p className="mt-1 text-sm text-ink-3">{t("admin.pulseSub")}</p>
          </div>
          <div className="flex rounded-xl border border-line bg-paper-2 p-0.5 text-xs">
            {[7, 14, 30].map((d) => (
              <button key={d} onClick={() => setDays(d)} className={cn("relative rounded-lg px-3 py-1.5 font-medium", days === d ? "text-ink" : "text-ink-3")}>
                {days === d && <motion.span layoutId="pulse-range" className="absolute inset-0 rounded-lg bg-surface shadow-[var(--shadow-soft)]" />}
                <span className="relative">{t("admin.days", { n: n(d) })}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4"><Legend items={[
          { label: t("admin.s.right"), color: C.right }, { label: t("admin.s.wrong"), color: C.wrong },
          { label: t("admin.s.rescued"), color: C.rescued, kind: "line" }, { label: t("admin.s.human"), color: C.human, kind: "dot" },
        ]} /></div>
        <TimeChart className="mt-3" dates={dates} height={280} yLabel={t("admin.questions")} series={[
          { key: "right", label: t("admin.s.right"), color: C.right, kind: "bar", values: daily.map((d) => d.right) },
          { key: "wrong", label: t("admin.s.wrong"), color: C.wrong, kind: "bar", values: daily.map((d) => d.wrong) },
          { key: "rescued", label: t("admin.s.rescued"), color: C.rescued, kind: "line", values: daily.map((d) => d.rescued) },
          { key: "human", label: t("admin.s.human"), color: C.human, kind: "dot", values: daily.map((d) => d.escalations) },
        ]} />
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Card className="p-6">
          <h2 className="font-display text-2xl">{t("admin.funnel")}</h2>
          <p className="mt-1 text-sm text-ink-3">{t("admin.funnelSub")}</p>
          <div className="mt-5 space-y-3">
            {rows.map((r, i) => (
              <div key={r.label}>
                <div className="flex items-baseline justify-between text-sm">
                  <span className={cn("text-ink-2", i === 0 && "font-semibold text-ink")}>{r.label}</span>
                  <span className="tabular-nums text-ink">{n(r.v)}{i > 0 && f.concepts_checked > 0 && <span className="ml-1.5 text-xs text-ink-3">{n(Math.round((r.v / max) * 100))}%</span>}</span>
                </div>
                <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-paper-3">
                  <motion.div className="h-full rounded-full" style={{ background: r.color }} initial={{ width: 0 }} animate={{ width: `${(r.v / max) * 100}%` }} transition={{ duration: 0.8, ease: EASE, delay: i * 0.08 }} />
                </div>
              </div>
            ))}
          </div>
          {struggled > 0 && <p className="mt-5 rounded-2xl bg-sky-50 px-4 py-3 text-sm text-sky-700">{t("admin.f.story", { p: n(saved) })}</p>}
        </Card>
        <Card className="p-6">
          <h2 className="font-display text-2xl">{t("admin.lessonFlow")}</h2>
          <div className="mt-3"><Legend items={[{ label: t("admin.s.started"), color: C.started }, { label: t("admin.s.completed"), color: C.completed, kind: "line" }]} /></div>
          <TimeChart className="mt-3" dates={dates} height={220} series={[
            { key: "started", label: t("admin.s.started"), color: C.started, kind: "bar", values: daily.map((d) => d.started) },
            { key: "completed", label: t("admin.s.completed"), color: C.completed, kind: "line", values: daily.map((d) => d.completed) },
          ]} />
        </Card>
      </div>
    </div>
  );
}

function Live() {
  const { t, n } = useI18n();
  const q = useQuery({ queryKey: ["admin", "live"], queryFn: api.admin.live, refetchInterval: 5000 });
  if (!q.data) return <Loading />;
  if (!q.data.sessions.length) return <Card className="grid place-items-center px-6 py-16 text-center text-ink-3"><Radio className="h-8 w-8" /><p className="mt-3">{t("admin.noLive")}</p></Card>;
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <AnimatePresence>
        {q.data.sessions.map((s) => (
          <motion.div key={s.lesson_id} layout initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }}>
            <Card className="relative overflow-hidden p-5">
              <span className="absolute right-4 top-4 flex items-center gap-1.5 text-xs font-semibold text-sage"><span className="h-2 w-2 animate-pulse rounded-full bg-sage" />{s.fsm_state}</span>
              <p className="pr-20 font-medium text-ink">{s.learner}</p>
              <p className="mt-0.5 truncate text-sm text-ink-2">{s.title}</p>
              {s.concept && <Badge tone="sky" className="mt-3">{s.concept}</Badge>}
              <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-paper-3"><motion.div className="h-full bg-sky-600" animate={{ width: `${s.progress_pct}%` }} /></div>
              <p className="mt-2 text-xs text-ink-3">{t("admin.connectedFor", { n: n(Math.round(s.connected_for_sec / 60)) })}</p>
            </Card>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

function Escalations() {
  const { t, n } = useI18n();
  const [status, setStatus] = useState<string>("open");
  const q = useQuery({ queryKey: ["admin", "esc", status], queryFn: () => api.admin.escalations(status === "all" ? undefined : status), refetchInterval: 10000 });
  const statuses = ["open", "continued", "resolved", "skipped", "all"];
  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {statuses.map((s) => (
          <button key={s} onClick={() => setStatus(s)} className={cn("rounded-full border px-3 py-1 text-sm", status === s ? "border-ink bg-ink text-white" : "border-line bg-surface text-ink-2")}>
            {s === "all" ? t("admin.all") : t(`admin.esc.${s}` as MessageKey)}{q.data?.counts?.[s] != null && <span className="ml-1.5 opacity-70">{n(q.data.counts[s])}</span>}
          </button>
        ))}
      </div>
      {!q.data ? <div className="mt-4"><Loading /></div> : q.data.escalations.length === 0 ? (
        <Card className="mt-4 px-6 py-14 text-center text-ink-3">{t("admin.noEsc")}</Card>
      ) : (
        <div className="mt-4 space-y-3">
          {q.data.escalations.map((e) => (
            <Card key={e.id} className={cn("p-5", e.status === "open" && "border-marigold-200")}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-ink">{e.learner} <span className="text-sm font-normal text-ink-3">· {e.learner_email}</span></p>
                  <p className="text-sm text-ink-2">{e.lesson_title} → <span className="font-medium">{e.concept}</span></p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={e.status === "open" ? "marigold" : e.status === "resolved" ? "sage" : "neutral"} dot>{t(`admin.esc.${e.status}` as MessageKey)}</Badge>
                  <Badge tone={e.mentor_notified ? "sky" : "rose"}>{e.mentor_notified ? <Mail className="h-3 w-3" /> : <MailX className="h-3 w-3" />}{t(e.mentor_notified ? "admin.mentorEmailed" : "admin.noMentor")}</Badge>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-4 text-xs text-ink-3">
                <span className="flex items-center gap-1"><AlertTriangle className="h-3.5 w-3.5 text-rose" />{t("admin.wrongAnswers", { n: n(e.wrong_answers) })}</span>
                <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" />{t("admin.minutesOpen", { n: n(Math.round(e.minutes_open)) })}</span>
              </div>
              {e.last_question && (
                <div className="mt-3 rounded-2xl bg-paper-2 p-3 text-sm">
                  <p className="text-ink">{e.last_question}</p>
                  {e.last_answer && <p className="mt-1 text-ink-2"><span className="text-ink-3">{t("admin.lastAnswer")}: </span>{e.last_answer}</p>}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function Insights() {
  const { t, n } = useI18n();
  const q = useQuery({ queryKey: ["admin", "insights"], queryFn: api.admin.insights });
  const d = q.data;
  if (!d) return <Loading />;
  const mix = Object.entries(d.adaptation_mix);
  const total = mix.reduce((s, [, v]) => s + v, 0) || 1;
  const colors: Record<string, string> = { ALLOW: "var(--sage)", MODIFY: "var(--sky-500)", REGENERATE: "var(--marigold-400)", HUMAN: "var(--margin)" };
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="p-6">
        <h2 className="font-display text-2xl">{t("admin.hardest")}</h2>
        {d.hardest_concepts.length ? <div className="mt-4 space-y-3">{d.hardest_concepts.map((c) => (
          <div key={c.concept} className="grid grid-cols-[minmax(0,1fr)_2fr_3rem] items-center gap-3 text-sm">
            <span className="truncate">{c.concept}</span>
            <div className="h-2.5 overflow-hidden rounded-full bg-paper-3"><motion.div className={cn("h-full rounded-full", c.accuracy_pct < 50 ? "bg-rose" : "bg-marigold-400")} initial={{ width: 0 }} animate={{ width: `${c.accuracy_pct}%` }} transition={{ duration: 0.8, ease: EASE }} /></div>
            <span className="text-right tabular-nums text-ink-3">{n(Math.round(c.accuracy_pct))}%</span>
          </div>
        ))}</div> : <NoData />}
      </Card>
      <Card className="p-6">
        <h2 className="font-display text-2xl">{t("admin.adaptMix")}</h2>
        {mix.length ? (
          <>
            <div className="mt-5 flex h-4 overflow-hidden rounded-full">
              {mix.map(([k, v], i) => <motion.div key={k} title={k} style={{ background: colors[k] ?? "var(--ink-3)" }} initial={{ width: 0 }} animate={{ width: `${(v / total) * 100}%` }} transition={{ delay: i * 0.1, duration: 0.7, ease: EASE }} />)}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">{mix.map(([k, v]) => <span key={k} className="flex items-center gap-2"><i className="h-2.5 w-2.5 rounded-full" style={{ background: colors[k] ?? "var(--ink-3)" }} />{k} <span className="text-ink-3">{n(v)}</span></span>)}</div>
          </>
        ) : <NoData />}
        <p className="mt-6 text-sm text-ink-3">{t("admin.attemptsToMastery")}</p>
        <p className="font-display text-4xl">{n(d.attempts_to_mastery.toFixed(1))}</p>
      </Card>
      <Card className="p-6 lg:col-span-2">
        <h2 className="font-display text-2xl">{t("admin.missed")}</h2>
        {d.missed_questions.length ? <ul className="mt-4 divide-y divide-line">{d.missed_questions.map((m, i) => (
          <li key={i} className="flex flex-wrap items-center justify-between gap-2 py-3">
            <div className="min-w-0"><p className="text-ink">{m.question}</p><p className="text-xs text-ink-3">{m.concept} · {t("admin.asked", { n: n(m.asked) })}</p></div>
            <Badge tone="rose">{t("admin.wrongPct", { n: n(Math.round(m.wrong_pct)) })}</Badge>
          </li>
        ))}</ul> : <NoData />}
      </Card>
      {d.misconceptions.length > 0 && (
        <Card className="p-6 lg:col-span-2">
          <h2 className="font-display text-2xl">{t("progress.misconceptions")}</h2>
          <div className="mt-4 flex flex-wrap gap-2">{d.misconceptions.map((m) => <Badge key={m.tag} tone="rose">{m.tag} ×{n(m.count)}</Badge>)}</div>
        </Card>
      )}
    </div>
  );
}

function KV({ data }: { data: Record<string, number> }) {
  const { n } = useI18n();
  const entries = Object.entries(data);
  const max = Math.max(1, ...entries.map(([, v]) => v));
  if (!entries.length) return <NoData />;
  return <div className="mt-4 space-y-2.5">{entries.map(([k, v]) => (
    <div key={k} className="grid grid-cols-[8rem_1fr_3rem] items-center gap-3 text-sm">
      <span className="truncate text-ink-2">{k}</span>
      <div className="h-2 overflow-hidden rounded-full bg-paper-3"><motion.div className="h-full rounded-full bg-sky-500" initial={{ width: 0 }} animate={{ width: `${(v / max) * 100}%` }} transition={{ duration: 0.7, ease: EASE }} /></div>
      <span className="text-right tabular-nums text-ink-3">{n(v)}</span>
    </div>
  ))}</div>;
}

function Quality() {
  const { t, n } = useI18n();
  const q = useQuery({ queryKey: ["admin", "quality"], queryFn: api.admin.quality, refetchInterval: 15000 });
  const d = q.data;
  if (!d) return <Loading />;
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="p-6">
        <h2 className="font-display text-2xl">{t("admin.llm")}</h2>
        <div className="mt-4 flex items-center gap-3">
          <span className={cn("grid h-12 w-12 place-items-center rounded-2xl text-white", d.llm.live && !d.llm.cooldown_active ? "bg-sage" : "bg-amber")}><Cpu className="h-6 w-6" /></span>
          <div><p className="font-semibold">{d.llm.live && !d.llm.cooldown_active ? t("admin.liveModel") : t("admin.offlineModel")}</p><p className="text-sm text-ink-3">{d.llm.model}</p></div>
        </div>
        {d.llm.cooldown_active && <p className="mt-3 text-sm text-amber">{t("admin.cooldown", { n: n(Math.round(d.llm.cooldown_remaining_sec)) })}</p>}
        <p className="mt-6 text-sm text-ink-3">{t("admin.explanations")}</p><p className="font-display text-4xl">{n(d.explanations)}</p>
        {d.script_words_vs_target != null && <><p className="mt-3 text-sm text-ink-3">{t("admin.scriptLen")}</p><p className="font-display text-4xl">{n(Math.round(d.script_words_vs_target * 100))}%</p></>}
      </Card>
      <Card className="p-6"><h2 className="font-display text-2xl">{t("admin.grounding")}</h2><KV data={d.grounding} /></Card>
      <Card className="p-6"><h2 className="font-display text-2xl">{t("admin.questionsByType")}</h2><KV data={d.questions_by_type} /></Card>
    </div>
  );
}

function Pipeline() {
  const { t, n } = useI18n();
  const q = useQuery({ queryKey: ["admin", "pipeline"], queryFn: api.admin.pipeline, refetchInterval: 10000 });
  const d = q.data;
  if (!d) return <Loading />;
  const up = d.uptime_sec;
  const upText = up >= 3600 ? `${n(Math.floor(up / 3600))}h ${n(Math.floor((up % 3600) / 60))}m` : `${n(Math.floor(up / 60))}m`;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat icon={<Video />} label={t("admin.renders")} value={d.renders.total} />
        <Stat icon={<AlertTriangle />} label={t("admin.failed")} value={d.renders.failed} tone={d.renders.failed ? "rose" : "sage"} />
        <Stat icon={<Clock />} label={t("admin.avgVideo")} value={Math.round(d.renders.avg_video_sec)} suffix="s" />
        <Stat icon={<Radio />} label={t("admin.reconnects")} value={d.reconnects_today} tone="marigold" />
        <Card className="p-5"><span className="grid h-9 w-9 place-items-center rounded-xl bg-sage-100 text-sage"><Server className="h-[18px] w-[18px]" /></span><p className="mt-4 font-display text-4xl">{upText}</p><p className="text-xs text-ink-3">{t("admin.uptime")}{d.memory_mb != null ? ` · ${t("admin.memory")} ${n(Math.round(d.memory_mb))} MB` : ""}</p></Card>
      </div>
      <Card className="p-6"><h2 className="font-display text-2xl">{t("admin.events")}</h2><KV data={d.events_last_hour} /></Card>
    </div>
  );
}

function Learners() {
  const { t, n, lang } = useI18n();
  const [search, setSearch] = useState("");
  const term = useDeferredValue(search.trim());
  const [open, setOpen] = useState<string | null>(null);
  const q = useQuery({ queryKey: ["admin", "learners", term], queryFn: () => api.admin.learners(term || undefined) });
  return (
    <div>
      <GlassSearch value={search} onChange={setSearch} placeholder={t("admin.searchLearners")} />
      <Card className="mt-4 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="bg-paper-2 text-left text-xs uppercase tracking-wider text-ink-3">
              <tr><th className="px-4 py-3">{t("admin.learners")}</th><th className="px-4 py-3">{t("admin.learnerLessons")}</th><th className="px-4 py-3">{t("admin.accuracy")}</th><th className="px-4 py-3">{t("admin.lastActive")}</th><th className="px-4 py-3" /></tr>
            </thead>
            <tbody className="divide-y divide-line">
              {(q.data?.learners ?? []).map((l) => (
                <tr key={l.id} onClick={() => setOpen(l.id)} className="cursor-pointer transition-colors hover:bg-sky-50/50">
                  <td className="px-4 py-3"><div className="flex items-center gap-3"><Avatar user={l} size={34} /><div><p className="font-medium">{l.full_name}</p><p className="text-xs text-ink-3">{l.email}</p></div></div></td>
                  <td className="px-4 py-3 tabular-nums">{n(l.completed)} / {n(l.lessons)}</td>
                  <td className="px-4 py-3"><div className="flex items-center gap-2"><div className="h-1.5 w-16 overflow-hidden rounded-full bg-paper-3"><div className="h-full bg-sky-500" style={{ width: `${l.accuracy_pct}%` }} /></div><span className="tabular-nums text-ink-3">{n(Math.round(l.accuracy_pct))}%</span></div></td>
                  <td className="px-4 py-3 text-ink-3">{l.last_active ? relativeDays(l.last_active, lang) : "—"}</td>
                  <td className="px-4 py-3 text-right">{l.open_escalations > 0 && <Badge tone="marigold"><Hand className="h-3 w-3" />{n(l.open_escalations)}</Badge>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <LearnerDrawer id={open} onClose={() => setOpen(null)} />
    </div>
  );
}

function LearnerDrawer({ id, onClose }: { id: string | null; onClose: () => void }) {
  const { t, n } = useI18n();
  const q = useQuery({ queryKey: ["admin", "learner", id], queryFn: () => api.admin.learner(id!), enabled: !!id });
  const d = q.data;
  return (
    <AnimatePresence>
      {id && (
        <motion.div className="fixed inset-0 z-[70]" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <div className="absolute inset-0 bg-ink/30 backdrop-blur-[2px]" onClick={onClose} />
          <motion.aside initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }} transition={{ type: "spring", stiffness: 300, damping: 34 }}
            className="absolute inset-y-0 right-0 w-full max-w-lg overflow-y-auto bg-paper p-6 shadow-[var(--shadow-lift)]" role="dialog" aria-modal="true">
            <button onClick={onClose} className="absolute right-4 top-4 grid h-9 w-9 place-items-center rounded-xl hover:bg-paper-2" aria-label={t("common.close")}><X className="h-5 w-5" /></button>
            {!d ? <Skeleton className="mt-10 h-60 rounded-2xl" /> : (
              <>
                <div className="flex items-center gap-4"><Avatar user={d.learner as AdminLearners["learners"][number]} size={64} /><div><p className="font-display text-3xl">{d.learner.full_name}</p><p className="text-sm text-ink-3">{d.learner.email}{d.learner.grade ? ` · ${d.learner.grade}` : ""}</p></div></div>
                <div className="mt-6 grid grid-cols-3 gap-3 text-center">
                  {[[d.learner.completed, t("admin.completed")], [Math.round(d.learner.accuracy_pct), t("admin.accuracy")], [d.practice_attempts, t("admin.practiceAttempts")]].map(([v, l]) => (
                    <Card key={l as string} className="p-3"><p className="font-display text-3xl">{n(v as number)}</p><p className="text-[0.7rem] text-ink-3">{l}</p></Card>
                  ))}
                </div>
                {d.weak_concepts.length > 0 && <><p className="mt-6 text-sm font-semibold text-marigold-600">{t("dash.weak")}</p><div className="mt-2 flex flex-wrap gap-1.5">{d.weak_concepts.map((c) => <Badge key={c} tone="marigold">{c}</Badge>)}</div></>}
                {d.strong_concepts.length > 0 && <><p className="mt-4 text-sm font-semibold text-sage">{t("dash.strong")}</p><div className="mt-2 flex flex-wrap gap-1.5">{d.strong_concepts.map((c) => <Badge key={c} tone="sage">{c}</Badge>)}</div></>}
                <p className="mt-6 text-sm font-semibold">{t("admin.learnerLessons")}</p>
                <div className="mt-2 divide-y divide-line rounded-2xl border border-line bg-surface">{d.lessons.map((l) => <div key={l.id} className="pointer-events-none"><LessonRow lesson={l} /></div>)}</div>
              </>
            )}
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
