"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, Check, ChevronDown, CircleDot, Hand, Loader2, Play, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/core/api";
import type { LessonDetail, LessonNode, PracticeQuestion, PracticeResult } from "@/core/types";
import type { MessageKey } from "@/core/i18n";
import { useI18n } from "@/providers/i18n";
import { Button } from "@/components/ui/button";
import { Badge, Card, Skeleton, Tabs, Textarea, type Tone } from "@/components/ui/primitives";
import { cn, EASE } from "@/lib/utils";

type Tab = "watch" | "practice";

const NOTE: Record<string, [MessageKey, Tone]> = {
  "after help": ["review.afterHelp", "sage"], "after review": ["review.afterReview", "sage"], "needs review": ["review.needsReviewNote", "amber"],
};
const STATUS: Record<string, [MessageKey, Tone]> = {
  mastered: ["class.node.mastered", "sage"], completed: ["class.node.completed", "sage"], skipped: ["class.node.toReview", "amber"],
  struggling: ["review.inProgress", "amber"], teaching: ["review.inProgress", "amber"], questioning: ["review.inProgress", "amber"],
};

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const { t, n } = useI18n();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("watch");
  const q = useQuery({ queryKey: ["lesson", id], queryFn: () => api.getLesson(id) });

  useEffect(() => { if (window.location.hash === "#practice") setTab("practice"); }, []);
  const change = (v: Tab) => { setTab(v); history.replaceState(null, "", v === "practice" ? "#practice" : "#watch"); };

  const act = async (kind: "continue" | "skip" | "relearn", nodeId?: string) => {
    try {
      if (kind === "continue") await api.continueLesson(id);
      else if (kind === "skip") await api.skipConcept(id);
      else await api.relearnConcept(id, nodeId!);
      router.push(`/learn/${id}`);
    } catch (e) { toast.error((e as Error).message); }
  };

  const l = q.data;
  return (
    <div className="mx-auto max-w-4xl px-5 py-8 lg:px-10 lg:py-10">
      <Link href="/lessons" className="inline-flex items-center gap-1.5 text-sm text-ink-3 hover:text-ink"><ArrowLeft className="h-4 w-4" />{t("review.allLessons")}</Link>
      {q.isLoading && <Skeleton className="mt-6 h-40 rounded-[var(--radius)]" />}
      {l && (
        <>
          <header className="mt-3 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="font-hand text-xl text-sky-700">{t("review.title")}</p>
              <h1 className="font-display text-4xl text-ink sm:text-5xl">{l.title}</h1>
              <p className="mt-2 text-sm text-ink-2">{t("review.conceptsDone", { a: n(l.nodes_completed), b: n(l.node_count) })} · {t("review.sub")}</p>
            </div>
            {l.status === "completed" && !l.review_pending ? <Button variant="outline" href={`/report/${id}`}>{t("lessons.report")}</Button>
              : l.status !== "escalated" ? <Button href={`/learn/${id}`}>{t("report.resume")}</Button> : null}
          </header>

          {l.status === "escalated" && l.escalation?.status === "open" && (
            <div className="mt-6 rounded-[22px] border border-amber/30 bg-amber-100/60 p-5">
              <p className="flex items-center gap-2 font-semibold text-ink"><Hand className="h-4 w-4 text-amber" />{t("class.pausedTitle")}</p>
              <p className="mt-1 text-sm text-ink-2">{t("class.pausedBody", { c: l.escalation.concept })}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button size="sm" onClick={() => act("continue")}>{t("class.continueAgain")}</Button>
                <Button size="sm" variant="outline" onClick={() => act("skip")}>{t("class.skip")}</Button>
              </div>
            </div>
          )}

          <Tabs<Tab> className="mt-8 max-w-sm" value={tab} onChange={change} items={[{ value: "watch", label: t("review.watch") }, { value: "practice", label: t("review.practice") }]} />
          <AnimatePresence mode="wait">
            <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.25 }} className="mt-6">
              {tab === "watch" ? <Watch l={l} onRelearn={(nid) => act("relearn", nid)} /> : <Practice id={id} />}
            </motion.div>
          </AnimatePresence>
        </>
      )}
    </div>
  );
}

function Watch({ l, onRelearn }: { l: LessonDetail; onRelearn: (nodeId: string) => void }) {
  const { t, n } = useI18n();
  const taught = l.nodes.filter((x) => x.script_text || x.video_url);
  if (!taught.length) return <p className="py-14 text-center text-ink-3">{t("review.nothing")}</p>;
  const canRelearn = ["completed", "in_progress"].includes(l.status) && !l.relearning;
  return (
    <div className="space-y-4">
      {l.nodes.map((node, i) => (node.script_text || node.video_url) ? <WatchCard key={node.node_id} node={node} i={i} canRelearn={canRelearn} onRelearn={onRelearn} /> : null)}
      <p className="text-center text-xs text-ink-3">{n(taught.length)} / {n(l.node_count)}</p>
    </div>
  );
}

function WatchCard({ node, i, canRelearn, onRelearn }: { node: LessonNode; i: number; canRelearn: boolean; onRelearn: (id: string) => void }) {
  const { t, n } = useI18n();
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [label, tone] = NOTE[node.review_note ?? ""] ?? STATUS[node.status] ?? ["review.notReached", "neutral"];
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);
  const load = async () => {
    setLoading(true);
    try { setUrl(await api.mediaObjectUrl(node.video_url!)); } catch (e) { toast.error((e as Error).message); } finally { setLoading(false); }
  };
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-display text-2xl text-ink"><span className="text-sky-600">{n(i + 1)}.</span> {node.concept}</h3>
        <Badge tone={tone} dot>{t(label)}</Badge>
      </div>
      {url && <video src={url} controls autoPlay className="mt-4 aspect-video w-full rounded-2xl bg-ink" data-cursor="video" />}
      {node.notes?.key_points?.length ? <ul className="mt-3 space-y-1.5">{node.notes.key_points.map((p, j) => <li key={j} className="flex gap-2 text-ink-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-marigold-600" />{p}</li>)}</ul> : null}
      {node.notes?.example && <p className="mt-2 text-sm text-ink-3">{t("class.example")}: {node.notes.example}</p>}
      {node.script_text && (
        <div className="mt-3">
          <button onClick={() => setOpen(!open)} className="flex items-center gap-1 text-sm text-sky-700"><ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />{t("review.transcript")}</button>
          <AnimatePresence>{open && <motion.p initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden pt-2 leading-relaxed text-ink-2">{node.script_text}</motion.p>}</AnimatePresence>
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        {node.video_url && !url && <Button size="sm" variant="soft" onClick={load} status={loading ? "loading" : "idle"} icon={<Play className="h-4 w-4" />}>{t("review.watchBtn")}</Button>}
        {node.status === "skipped" && canRelearn && <Button size="sm" onClick={() => onRelearn(node.node_id)} icon={<RefreshCw className="h-4 w-4" />}>{t("review.learnAgain")}</Button>}
      </div>
    </Card>
  );
}

function Practice({ id }: { id: string }) {
  const { t } = useI18n();
  const q = useQuery({ queryKey: ["practice", id], queryFn: () => api.practice(id) });
  if (q.isLoading) return <Skeleton className="h-60 rounded-[var(--radius)]" />;
  const qs = q.data?.questions ?? [];
  if (!qs.length) return <p className="py-14 text-center text-ink-3">{t("review.noQuestions")}</p>;
  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-3">{t("review.practiceNote")}</p>
      {qs.map((x, i) => <PracticeCard key={x.interaction_id} q={x} i={i} lessonId={id} />)}
    </div>
  );
}

function PracticeCard({ q, i, lessonId }: { q: PracticeQuestion; i: number; lessonId: string }) {
  const { t, n } = useI18n();
  const [ans, setAns] = useState("");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<PracticeResult | null>(null);
  const mcq = q.options?.length > 0;
  const check = async () => {
    setBusy(true);
    try { setRes(await api.answerPractice(lessonId, q.interaction_id, ans)); } catch (e) { toast.error((e as Error).message); } finally { setBusy(false); }
  };
  return (
    <Card className="p-5" data-testid="practice-card">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-display text-xl text-sky-600">{n(i + 1)}</span>
        <Badge>{q.concept}</Badge>
        {q.needs_practice && <Badge tone="marigold" dot>{t("review.needsPractice")}</Badge>}
        {q.last_practice && <span className="text-xs text-ink-3">{t("review.lastTime", { r: t(q.last_practice.correct ? "review.right" : "review.wrong") })}</span>}
      </div>
      <p className="mt-2 text-lg font-medium text-ink">{q.question_text}</p>
      {q.your_lesson_answer && <p className="mt-1 text-sm text-ink-3">{t("review.inLesson", { a: q.your_lesson_answer })}</p>}
      {mcq ? (
        <div className="mt-3 grid gap-2">
          {q.options.map((o) => (
            <button key={o} type="button" onClick={() => { setAns(o); setRes(null); }}
              className={cn("rounded-2xl border px-4 py-2.5 text-left text-sm transition-colors", ans === o ? "border-sky-500 bg-sky-50" : "border-line hover:border-sky-300")}>{o}</button>
          ))}
        </div>
      ) : <Textarea className="mt-3" rows={3} value={ans} onChange={(e) => { setAns(e.target.value); setRes(null); }} placeholder={t("class.answerPlaceholder")} />}
      <div className="mt-3 flex justify-end">
        <Button size="sm" onClick={check} disabled={!ans.trim() || busy} status={busy ? "loading" : "idle"}>{res ? t("review.checkAgain") : t("review.check")}</Button>
      </div>
      <AnimatePresence>
        {res && (
          <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ ease: EASE }}
            className={cn("mt-3 rounded-2xl p-4", res.correct ? "bg-sage-100" : "bg-rose-100/60")}>
            <p className={cn("flex items-center gap-2 font-semibold", res.correct ? "text-sage" : "text-rose")}>
              {res.correct ? <Check className="h-4 w-4" /> : <CircleDot className="h-4 w-4" />}{t(res.correct ? "class.correct" : "class.notQuite")}
            </p>
            {res.feedback_text && <p className="mt-1 text-sm text-ink-2">{res.feedback_text}</p>}
            {res.model_answer && <p className="mt-2 text-sm text-ink-2"><span className="font-semibold">{t("review.modelAnswer")}: </span>{res.model_answer}</p>}
          </motion.div>
        )}
      </AnimatePresence>
      {busy && <Loader2 className="hidden" />}
    </Card>
  );
}
