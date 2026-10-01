"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { BookOpen, Check, CircleDot, Download, Eye, FileText, Hand, Loader2, MessageSquareText, Play, RefreshCw, ScrollText, Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/core/api";
import { useI18n } from "@/providers/i18n";
import type { MessageKey } from "@/core/i18n";
import { Badge, Tabs } from "@/components/ui/primitives";
import { Button } from "@/components/ui/button";
import { SlideToConfirm } from "@/components/ui/slide-to-confirm";
import { PlaneMark } from "@/components/brand/logo";
import { Shimmer } from "@/components/motion/reveal";
import { cn, EASE } from "@/lib/utils";
import type { ClassroomController, ClassroomState, NodeView } from "./controller";

/* ── study panel: Notes / Transcript / Questions / Source ─────────────── */

type Tab = "notes" | "transcript" | "questions" | "source";

export function StudyPanel({ s, lessonId }: { s: ClassroomState; lessonId: string }) {
  const { t, n } = useI18n();
  const [tab, setTab] = useState<Tab>("notes");
  const answered = s.qa.filter((x) => x.result).length;
  const [busy, setBusy] = useState(false);

  const download = async () => {
    setBusy(true);
    try {
      const blob = await api.notesMarkdown(lessonId);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${s.title || "lesson"} - notes.md`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
      toast.success(t("class.notesSaved"));
    } catch (e) { toast.error((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <div className="flex h-full min-h-0 flex-col rounded-[26px] border border-line bg-surface shadow-[var(--shadow-soft)]">
      <div className="p-3">
        <Tabs<Tab> value={tab} onChange={setTab} items={[
          { value: "notes", label: <><BookOpen className="h-4 w-4" /><span className="hidden sm:inline">{t("class.tabs.notes")}</span></> },
          { value: "transcript", label: <><ScrollText className="h-4 w-4" /><span className="hidden sm:inline">{t("class.tabs.transcript")}</span></> },
          { value: "questions", label: <><MessageSquareText className="h-4 w-4" /><span className="hidden sm:inline">{t("class.tabs.questions")}</span></>, badge: s.qa.length ? <span className="rounded-full bg-sky-100 px-1.5 text-[0.65rem] text-sky-700">{n(answered)}</span> : undefined },
          { value: "source", label: <><FileText className="h-4 w-4" /><span className="hidden sm:inline">{t("class.tabs.source")}</span></> },
        ]} />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5" data-lenis-prevent>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={tab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.2 }}>
            {tab === "notes" && <NotesTab s={s} />}
            {tab === "transcript" && (s.notes?.transcript
              ? <TranscriptTab text={s.notes.transcript} concept={s.notes.concept} />
              : <Empty icon={<ScrollText />} text={t("class.noNotes")} />)}
            {tab === "questions" && <QuestionsTab s={s} />}
            {tab === "source" && <SourceTab s={s} />}
          </motion.div>
        </AnimatePresence>
      </div>
      {s.collected.length > 0 && (
        <div className="border-t border-line p-3">
          <Button variant="soft" size="sm" className="w-full" onClick={download} status={busy ? "loading" : "idle"} icon={<Download className="h-4 w-4" />}>{t("class.downloadNotes")}</Button>
        </div>
      )}
    </div>
  );
}

function Empty({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="grid place-items-center gap-3 py-14 text-center text-sm text-ink-3">
      <span className="grid h-12 w-12 place-items-center rounded-2xl bg-paper-2 [&>svg]:h-5 [&>svg]:w-5">{icon}</span>
      {text}
    </div>
  );
}

function NotesTab({ s }: { s: ClassroomState }) {
  const { t, n } = useI18n();
  const nn = s.notes;
  if (!nn && s.collected.length === 0) return <Empty icon={<BookOpen />} text={t("class.noNotes")} />;
  return (
    <div className="space-y-6">
      {nn && (
        <section className="ruled-plain -mx-1 rounded-2xl px-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display text-2xl text-ink">{nn.concept}</h3>
            {nn.depth && <Badge>{nn.depth}</Badge>}
            {nn.est_minutes ? <Badge tone="sky">{t("common.minutes", { n: n(nn.est_minutes) })}</Badge> : null}
          </div>
          {nn.formula && (
            <div className="mt-3 rounded-2xl bg-sky-50 px-4 py-3 font-mono text-[0.95rem] text-sky-700">
              <span className="mr-2 text-xs font-sans font-semibold uppercase tracking-wider text-sky-600/70">{t("class.formula")}</span>{nn.formula}
            </div>
          )}
          <p className="mt-4 text-xs font-semibold uppercase tracking-wider text-ink-3">{t("class.keyPoints")}</p>
          <ul className="mt-2 space-y-2">
            {nn.points.map((p, i) => (
              <motion.li key={i} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }} className="flex gap-2.5 leading-relaxed text-ink-2">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-marigold-600" />{p}
              </motion.li>
            ))}
          </ul>
          {nn.example && (
            <div className="mt-4 rounded-2xl border-l-4 border-marigold-400 bg-marigold-50 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-marigold-600">{t("class.example")}</p>
              <p className="mt-1 text-ink-2">{nn.example}</p>
            </div>
          )}
        </section>
      )}
      {s.collected.length > (nn ? 1 : 0) && (
        <section>
          <p className="font-hand text-lg text-sky-700">{t("class.allNotes")}</p>
          <ol className="mt-2 space-y-3">
            {s.collected.filter((c) => c.node_id !== nn?.node_id).map((c, i) => (
              <li key={c.node_id} className="rounded-2xl border border-line p-3">
                <p className="text-sm font-semibold text-ink">{n(i + 1)}. {c.concept}</p>
                <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-ink-2">{c.points.map((p, j) => <li key={j}>{p}</li>)}</ul>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

function TranscriptTab({ text, concept }: { text: string; concept: string }) {
  const paras = text.split(/\n{2,}|(?<=[.!?।])\s+(?=[A-Zअ-ह])/).filter(Boolean);
  return (
    <div>
      <h3 className="font-display text-xl text-ink">{concept}</h3>
      <div className="mt-3 space-y-3 leading-relaxed text-ink-2">{paras.map((p, i) => <p key={i}>{p}</p>)}</div>
    </div>
  );
}

function QuestionsTab({ s }: { s: ClassroomState }) {
  const { t } = useI18n();
  if (!s.qa.length) return <Empty icon={<MessageSquareText />} text={t("class.noQuestions")} />;
  return (
    <ol className="space-y-3">
      {[...s.qa].reverse().map(({ question, answer, result }) => (
        <li key={question.interaction_id} className="rounded-2xl border border-line p-4">
          <p className="font-medium text-ink">{question.question_text}</p>
          {answer && <p className="mt-2 text-sm text-ink-2"><span className="text-ink-3">{t("class.answered")}: </span>{answer}</p>}
          {result ? (
            <p className={cn("mt-2 flex items-start gap-1.5 text-sm", result.correct ? "text-sage" : result.partial_credit >= 0.5 ? "text-marigold-600" : "text-rose")}>
              {result.correct ? <Check className="mt-0.5 h-4 w-4 shrink-0" /> : <CircleDot className="mt-0.5 h-4 w-4 shrink-0" />}
              <span>{t(result.correct ? "class.correct" : result.partial_credit >= 0.5 ? "class.nearly" : "class.notQuite")}{result.feedback_text ? ` — ${result.feedback_text}` : ""}</span>
            </p>
          ) : <Badge tone="marigold" className="mt-2">{t("class.yourTurn")}</Badge>}
        </li>
      ))}
    </ol>
  );
}

function SourceTab({ s }: { s: ClassroomState }) {
  const { t, n } = useI18n();
  const c = s.citation;
  if (!s.isDocument) return <Empty icon={<Sparkles />} text={t("class.noSource")} />;
  if (!c || c.none) return <Empty icon={<FileText />} text={t("class.noMatch")} />;
  const weak = c.risk_level && c.risk_level !== "low";
  const where = [c.section_title, c.page_or_slide ? t("class.page", { n: n(c.page_or_slide) }) : ""].filter(Boolean).join(" · ");
  return (
    <div>
      <Badge tone={weak ? "amber" : "sage"} dot>{t(weak ? "class.loose" : "class.grounded")}</Badge>
      <p className="mt-3 font-semibold text-ink">{c.source_title}{where ? ` — ${where}` : ""}</p>
      <blockquote className="mt-3 rounded-2xl border-l-4 border-sky-300 bg-sky-50/60 px-4 py-3 leading-relaxed text-ink-2">
        <span className="highlight">{c.excerpt}</span>
      </blockquote>
      {c.chunk_count ? <p className="mt-3 text-xs text-ink-3">{t("class.passages", { n: n(c.chunk_count) })}</p> : null}
      {(c.attempts ?? 0) > 1 && <p className="mt-1 text-xs text-ink-3">{t("class.refined", { q: c.refined_query || "" })}</p>}
    </div>
  );
}

/* ── concept rail ──────────────────────────────────────────────────────── */

export function ConceptRail({ s, onRewatch }: { s: ClassroomState; onRewatch: (n: NodeView) => void }) {
  const { t, n } = useI18n();
  const ref = useRef<HTMLOListElement>(null);
  useEffect(() => {
    ref.current?.querySelector("[data-active=true]")?.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
  }, [s.currentNodeId]);
  return (
    <ol ref={ref} className="fade-x no-scrollbar flex gap-2 overflow-x-auto py-1" aria-label={t("class.curriculum")}>
      {s.nodes.map((node, i) => {
        const active = node.node_id === s.currentNodeId;
        const done = node.status === "mastered" || node.status === "completed";
        const review = node.status === "skipped";
        const rewatchable = !!node.video_url && !active && (done || review);
        const label: MessageKey = active ? "class.node.now" : node.status === "mastered" ? "class.node.mastered" : node.status === "completed" ? "class.node.completed"
          : review ? "class.node.toReview" : node.status === "struggling" ? "class.node.struggling" : "class.node.next";
        return (
          <li key={node.node_id} data-active={active}>
            <button type="button" disabled={!rewatchable} onClick={() => rewatchable && onRewatch(node)} title={rewatchable ? t("class.rewatch") : undefined}
              className={cn("group relative flex w-56 shrink-0 items-center gap-3 rounded-2xl border px-3 py-2.5 text-left transition-all",
                active ? "border-sky-300 bg-sky-50 shadow-[var(--shadow-soft)]" : "border-line bg-surface",
                rewatchable && "hover:-translate-y-0.5 hover:border-sky-200")}>
              <span className={cn("grid h-8 w-8 shrink-0 place-items-center rounded-xl text-xs font-semibold",
                done ? "bg-sage text-white" : review ? "bg-marigold-100 text-marigold-600" : active ? "bg-sky-600 text-white" : "bg-paper-2 text-ink-3")}>
                {done ? <Check className="h-4 w-4" /> : active ? <span className="h-2 w-2 animate-pulse rounded-full bg-white" /> : n(i + 1)}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium text-ink">{node.concept}</span>
                <span className="flex items-center gap-1 text-[0.7rem] text-ink-3">{t(label)}{rewatchable && <><span>·</span><Eye className="h-3 w-3" />{t("class.rewatch")}</>}</span>
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

/* ── overlays over the stage ─────────────────────────────────────────── */

export function StageOverlay({ s, ctl, lessonId }: { s: ClassroomState; ctl: ClassroomController; lessonId: string }) {
  const { t, n } = useI18n();
  const o = s.overlay;
  const [busy, setBusy] = useState<string | null>(null);
  if (!o) return null;

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    try { await fn(); window.location.reload(); } catch (e) { toast.error((e as Error).message); setBusy(null); }
  };

  const shell = (children: React.ReactNode, tone = "bg-paper/92") => (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className={cn("absolute inset-0 z-20 grid place-items-center overflow-y-auto p-5 backdrop-blur-md", tone)} data-testid={`overlay-${o.kind}`}>
      <motion.div initial={{ y: 14, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ ease: EASE, duration: 0.45 }} className="w-full max-w-lg text-center">{children}</motion.div>
    </motion.div>
  );

  switch (o.kind) {
    case "loading":
      return shell(<>
        <div className="relative mx-auto h-24 w-24">
          <PlaneMark size={96} className="animate-float-soft" />
          <svg className="absolute -inset-3 h-[120px] w-[120px] animate-spin [animation-duration:3s]" viewBox="0 0 120 120"><circle cx="60" cy="60" r="56" fill="none" stroke="var(--sky-200)" strokeWidth="2" strokeDasharray="4 10" /></svg>
        </div>
        {o.title && <p className="mt-6 font-display text-3xl text-ink">{o.title}</p>}
        <Shimmer className="mt-2 text-sm">{t(o.bodyKey)}</Shimmer>
      </>);
    case "text":
      return shell(<div className="text-left">
        <Badge tone="amber">{t("class.noVideo")}</Badge>
        <p className="mt-3 font-display text-3xl text-ink">{o.title}</p>
        <p className="mt-3 max-h-[40vh] overflow-y-auto whitespace-pre-line leading-relaxed text-ink-2">{o.body}</p>
      </div>);
    case "error":
      return shell(<>
        <p className="font-display text-3xl text-ink">{t(o.titleKey)}</p>
        <p className="mt-2 text-ink-2">{o.body}</p>
        <div className="mt-6 flex justify-center gap-3">
          <Button variant="outline" onClick={() => window.location.reload()} icon={<RefreshCw className="h-4 w-4" />}>{t("class.reload")}</Button>
          <Button href="/new">{t("class.goNew")}</Button>
        </div>
      </>);
    case "elsewhere":
      return shell(<>
        <p className="font-display text-3xl">{t("class.otherTab")}</p>
        <p className="mt-2 text-ink-2">{t("class.otherTabBody")}</p>
        <Button className="mt-6" onClick={() => window.location.reload()}>{t("class.reload")}</Button>
      </>);
    case "offline":
      return shell(<>
        <p className="font-display text-3xl">{t("class.cantReach")}</p>
        <p className="mt-2 text-ink-2">{t("class.cantReachBody")}</p>
        <Button className="mt-6" onClick={() => window.location.reload()}>{t("class.reload")}</Button>
      </>);
    case "complete":
      return shell(<>
        <motion.div initial={{ scale: 0.6, rotate: -20 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: "spring", stiffness: 200, damping: 12 }}
          className="mx-auto grid h-24 w-24 place-items-center rounded-full bg-sage text-white"><Check className="h-12 w-12" /></motion.div>
        <p className="mt-6 font-display text-4xl">{t("class.completeTitle")}</p>
        <p className="mt-2 text-ink-2">{t("class.completeBody", { n: n(Math.round(o.score)) })}</p>
      </>);
    case "paused":
      return shell(<div className="text-left" data-testid="paused-panel">
        <span className="grid h-14 w-14 place-items-center rounded-2xl bg-amber text-white"><Hand className="h-7 w-7" /></span>
        <p className="mt-4 font-display text-4xl text-ink">{t("class.pausedTitle")}</p>
        <p className="mt-2 text-ink-2">{t("class.pausedBody", { c: o.concept })}</p>
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <Button variant="outline" href={`/review/${lessonId}`}>{t("class.practise")}</Button>
          <Button onClick={() => run("continue", () => ctl.act("continue"))} status={busy === "continue" ? "loading" : "idle"} disabled={!!busy} icon={<Play className="h-4 w-4" />} data-testid="continue-lesson">
            {t("class.continueAgain")}
          </Button>
        </div>
        <SlideToConfirm className="mt-3" label={t("class.slideSkip")} disabled={!!busy}
          onConfirm={() => run("skip", async () => { await ctl.act("skip"); toast.success(t("class.skipped")); })} />
      </div>, "bg-amber-100/85");
    case "review": {
      const next = o.concepts[0];
      return shell(<div className="text-left" data-testid="review-panel">
        <span className="grid h-14 w-14 place-items-center rounded-2xl bg-marigold-600 text-white"><RefreshCw className="h-7 w-7" /></span>
        <p className="mt-4 font-display text-4xl text-ink">{t("class.reviewTitle", { n: n(o.concepts.length) })}</p>
        <p className="mt-2 text-ink-2">{t("class.reviewBody", { list: o.concepts.map((c) => c.concept).join(", ") })}</p>
        <div className="mt-6 flex flex-wrap gap-3">
          {next && <Button onClick={() => run("relearn", () => ctl.act("relearn", next.node_id))} status={busy ? "loading" : "idle"}>{t("class.reviewNext", { c: next.concept })}</Button>}
          <Button variant="outline" href={`/review/${lessonId}`}>{t("class.practise")}</Button>
        </div>
      </div>, "bg-marigold-50/90");
    }
  }
}

/* ── rewatch dialog ──────────────────────────────────────────────────── */

export function RewatchDialog({ node, onClose }: { node: NodeView | null; onClose: () => void }) {
  const { t } = useI18n();
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!node?.video_url) return;
    let alive = true, made: string | null = null;
    api.mediaObjectUrl(node.video_url).then((u) => { made = u; if (alive) setUrl(u); else URL.revokeObjectURL(u); })
      .catch((e) => { toast.error((e as Error).message); onClose(); });
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => { alive = false; window.removeEventListener("keydown", esc); if (made) URL.revokeObjectURL(made); setUrl(null); };
  }, [node, onClose]);
  return (
    <AnimatePresence>
      {node && (
        <motion.div className="fixed inset-0 z-[80] grid place-items-center p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <div className="absolute inset-0 bg-ink/45 backdrop-blur-sm" onClick={onClose} />
          <motion.div role="dialog" aria-modal="true" aria-label={t("class.rewatching", { c: node.concept })}
            initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.97, opacity: 0 }} transition={{ ease: EASE, duration: 0.35 }}
            className="relative w-full max-w-4xl overflow-hidden rounded-[28px] bg-surface shadow-[var(--shadow-lift)]">
            <div className="flex items-center justify-between gap-3 px-5 py-3">
              <p className="truncate font-medium">{t("class.rewatching", { c: node.concept })}</p>
              <button onClick={onClose} className="grid h-9 w-9 place-items-center rounded-xl hover:bg-paper-2" aria-label={t("class.backToLesson")}><X className="h-5 w-5" /></button>
            </div>
            <div className="aspect-video bg-ink">
              {url ? <video src={url} controls autoPlay className="h-full w-full" data-cursor="video" /> : <div className="grid h-full place-items-center text-white/70"><Loader2 className="h-6 w-6 animate-spin" /></div>}
            </div>
            <div className="flex items-center justify-between gap-3 px-5 py-3">
              <p className="text-xs text-ink-3">{t("class.rewatchNote")}</p>
              <Button size="sm" onClick={onClose}>{t("class.backToLesson")}</Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

