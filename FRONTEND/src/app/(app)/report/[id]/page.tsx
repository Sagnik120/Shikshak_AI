"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { ArrowRight, Check, CircleDot, Download, Hand, Plus, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/core/api";
import type { LessonDetail } from "@/core/types";
import { useI18n } from "@/providers/i18n";
import { Button } from "@/components/ui/button";
import { Badge, Card, Ring, Skeleton } from "@/components/ui/primitives";
import { CountUp, Reveal, Stagger, StaggerItem } from "@/components/motion/reveal";
import { PlaneMark } from "@/components/brand/logo";
import { cn, EASE } from "@/lib/utils";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useI18n();
  const q = useQuery({ queryKey: ["lesson", id], queryFn: () => api.getLesson(id) });
  const l = q.data;
  return (
    <div className="mx-auto max-w-5xl px-5 py-8 lg:px-10 lg:py-10">
      {q.isLoading && <Skeleton className="h-72 rounded-[28px]" />}
      {q.isError && <p className="text-rose">{(q.error as Error).message}</p>}
      {l && (l.status !== "completed" || !l.report) && (
        <Card className="ruled grid place-items-center px-6 py-16 text-center">
          <PlaneMark size={90} className="animate-float-soft" />
          <h1 className="mt-5 font-display text-4xl">{l.title}</h1>
          <p className="mt-2 text-ink-2">{l.review_pending ? t("report.reviewPending") : t("report.notReady")}</p>
          <div className="mt-6 flex gap-3">
            {l.review_pending && <Button variant="marigold" href={`/review/${id}`}>{t("dash.reviewBtn")}</Button>}
            <Button href={`/learn/${id}`} icon={<ArrowRight className="h-4 w-4" />}>{t("report.resume")}</Button>
          </div>
        </Card>
      )}
      {l?.report && l.status === "completed" && <Report l={l} />}
    </div>
  );
}

function Report({ l }: { l: LessonDetail }) {
  const { t, n } = useI18n();
  const r = l.report!;
  const qs = l.nodes.flatMap((x) => x.interactions);
  const right = qs.filter((x) => x.correct).length;
  const mastered = l.nodes.filter((x) => x.status === "mastered").length;
  const reexplained = l.nodes.reduce((s, x) => s + x.times_reexplained, 0);
  const helped = l.escalations.filter((e) => e.status !== "open");
  const [busy, setBusy] = useState(false);

  const download = async () => {
    setBusy(true);
    try {
      const blob = await api.notesMarkdown(l.id);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${l.title} - notes.md`;
      a.click();
      toast.success(t("class.notesSaved"));
    } catch (e) { toast.error((e as Error).message); } finally { setBusy(false); }
  };

  const stats = [
    { label: t("report.mastered"), v: mastered, of: l.node_count },
    { label: t("report.questions"), v: right, of: qs.length },
    { label: t("report.reexplained"), v: reexplained },
    { label: t("report.minutes"), v: Math.round(l.watch_minutes) },
  ];

  return (
    <div className="space-y-8">
      {/* certificate-like hero */}
      <motion.section initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: EASE }}
        className="ruled relative overflow-hidden rounded-[32px] border border-line bg-surface py-10 pl-20 pr-8 shadow-[var(--shadow-lift)] sm:pl-24">
        <PlaneMark size={120} className="absolute -right-4 -top-4 rotate-12 opacity-70" />
        <p className="font-hand text-2xl text-sky-700">{t("report.title")}</p>
        <h1 className="mt-1 max-w-2xl font-display text-4xl leading-tight text-ink sm:text-5xl">{l.title}</h1>
        <div className="mt-8 flex flex-wrap items-center gap-8">
          <Ring value={r.score_pct} size={140} stroke={12} label={<span className="font-display text-4xl"><CountUp to={Math.round(r.score_pct)} suffix="%" format={(v) => n(v)} /></span>} />
          <Stagger className="grid flex-1 grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-4">
            {stats.map((s) => (
              <StaggerItem key={s.label}>
                <p className="font-display text-4xl text-ink">{n(s.v)}{s.of != null && <span className="text-xl text-ink-3"> / {n(s.of)}</span>}</p>
                <p className="text-xs text-ink-3">{s.label}</p>
              </StaggerItem>
            ))}
          </Stagger>
        </div>
      </motion.section>

      {r.narrative_feedback && (
        <Reveal>
          <Card className="p-6">
            <p className="font-hand text-xl text-sky-700">{t("report.feedback")}</p>
            <p className="mt-2 text-lg leading-relaxed text-ink-2">{r.narrative_feedback}</p>
          </Card>
        </Reveal>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        {([["report.strong", r.strong_areas, "sage"], ["report.weak", r.weak_areas, "marigold"], ["report.next", r.recommended_next, "sky"]] as const).map(([k, items, tone], i) => (
          <Reveal key={k} delay={i * 0.08}>
            <Card className="h-full p-5">
              <h3 className="text-sm font-semibold text-ink">{t(k)}</h3>
              <div className="mt-3 flex flex-wrap gap-2">{items.length ? items.map((x) => <Badge key={x} tone={tone}>{x}</Badge>) : <span className="text-sm text-ink-3">{t("report.none")}</span>}</div>
            </Card>
          </Reveal>
        ))}
      </div>

      <section>
        <h2 className="font-display text-3xl">{t("report.timeline")}</h2>
        <ol className="relative mt-5 space-y-4 border-l-2 border-dashed border-line-2 pl-8">
          {l.nodes.map((node, i) => (
            <Reveal key={node.node_id} delay={i * 0.04}>
              <li className="relative">
                <span className={cn("absolute -left-[45px] top-4 grid h-8 w-8 place-items-center rounded-full text-xs font-semibold ring-4 ring-paper",
                  node.status === "mastered" ? "bg-sage text-white" : node.status === "skipped" ? "bg-marigold-100 text-marigold-600" : "bg-sky-100 text-sky-700")}>
                  {node.status === "mastered" ? <Check className="h-4 w-4" /> : n(i + 1)}
                </span>
                <Card className="p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-display text-2xl">{node.concept}</h3>
                    <div className="flex gap-2 text-xs text-ink-3">
                      <span>{t("report.attempts", { n: n(node.attempts) })}</span>
                      {node.times_reexplained > 0 && <span className="flex items-center gap-1"><RefreshCw className="h-3 w-3" />{t("report.reexplainedN", { n: n(node.times_reexplained) })}</span>}
                    </div>
                  </div>
                  <div className="mt-3 space-y-3">
                    {node.interactions.map((x) => (
                      <div key={x.id} className="rounded-2xl bg-paper-2 p-3 text-sm">
                        <p className="font-medium text-ink">{x.question_text}</p>
                        {x.raw_answer && <p className="mt-1 text-ink-2"><span className="text-ink-3">{t("report.youSaid")}: </span>{x.raw_answer}</p>}
                        <p className={cn("mt-1 flex items-start gap-1.5", x.correct ? "text-sage" : "text-rose")}>
                          {x.correct ? <Check className="mt-0.5 h-3.5 w-3.5" /> : <CircleDot className="mt-0.5 h-3.5 w-3.5" />}
                          <span>{x.feedback_text}</span>
                        </p>
                      </div>
                    ))}
                  </div>
                </Card>
              </li>
            </Reveal>
          ))}
        </ol>
      </section>

      {helped.length > 0 && (
        <Card className="p-5">
          <h3 className="flex items-center gap-2 font-semibold"><Hand className="h-4 w-4 text-amber" />{t("report.mentorHelp")}</h3>
          <ul className="mt-2 space-y-1 text-sm text-ink-2">{helped.map((e) => <li key={e.id}>{e.concept}{e.resolution ? ` — ${e.resolution}` : ""}</li>)}</ul>
        </Card>
      )}

      <div className="flex flex-wrap justify-end gap-3">
        <Button variant="outline" onClick={download} status={busy ? "loading" : "idle"} icon={<Download className="h-4 w-4" />}>{t("report.download")}</Button>
        <Button href={`/review/${l.id}`} variant="soft">{t("class.practise")}</Button>
        <Button href="/new" icon={<Plus className="h-4 w-4" />}>{t("report.newLesson")}</Button>
      </div>
    </div>
  );
}
