"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { ArrowLeft, Hand, Loader2, RefreshCw, Sparkles, Wifi, WifiOff } from "lucide-react";
import { useClassroom } from "@/features/classroom/use-classroom";
import type { ClassroomState, Connection, NodeView } from "@/features/classroom/controller";
import { ConceptRail, RewatchDialog, StageOverlay, StudyPanel } from "@/features/classroom/panels";
import { QuestionCard } from "@/features/classroom/question-card";
import { LanguageToggle } from "@/components/layout/language-toggle";
import { PlaneMark } from "@/components/brand/logo";
import { useI18n } from "@/providers/i18n";
import type { MessageKey } from "@/core/i18n";
import { cn, EASE } from "@/lib/utils";

const CONN: Record<Connection, { key: MessageKey; tone: string; icon: React.ReactNode }> = {
  connecting: { key: "class.status.connecting", tone: "bg-paper-2 text-ink-2", icon: <Loader2 className="h-3 w-3 animate-spin" /> },
  live: { key: "class.live", tone: "bg-sage-100 text-sage", icon: <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-sage" /> },
  reconnecting: { key: "class.reconnecting", tone: "bg-amber-100 text-amber", icon: <Wifi className="h-3 w-3" /> },
  offline: { key: "class.offline", tone: "bg-rose-100 text-rose", icon: <WifiOff className="h-3 w-3" /> },
  paused: { key: "class.paused", tone: "bg-amber-100 text-amber", icon: <Hand className="h-3 w-3" /> },
  unavailable: { key: "class.status.unavailable", tone: "bg-rose-100 text-rose", icon: <WifiOff className="h-3 w-3" /> },
  elsewhere: { key: "class.status.elsewhere", tone: "bg-rose-100 text-rose", icon: <WifiOff className="h-3 w-3" /> },
  done: { key: "class.status.done", tone: "bg-sage-100 text-sage", icon: <Sparkles className="h-3 w-3" /> },
};

export default function ClassroomPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useI18n();
  const { ctl, state: s } = useClassroom(id);
  const [video, setVideo] = useState<HTMLVideoElement | null>(null);
  const [rewatch, setRewatch] = useState<NodeView | null>(null);

  useEffect(() => { ctl?.attachVideo(video); }, [ctl, video]);
  useEffect(() => { if (s?.title) document.title = `${s.title} — Shikshak`; }, [s?.title]);

  // Controller toasts → sonner (translated here, so they follow the language).
  const toastId = s?.toast?.id;
  useEffect(() => {
    if (!s?.toast) return;
    const msg = s.toast.raw && s.toast.key === "common.error" ? s.toast.raw : t(s.toast.key);
    (s.toast.tone === "error" ? toast.error : s.toast.tone === "success" ? toast.success : s.toast.tone === "warning" ? toast.warning : toast)(msg);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toastId]);

  const openRewatch = useCallback((n: NodeView) => { ctl?.beginRewatch(); setRewatch(n); }, [ctl]);
  const closeRewatch = useCallback(() => { setRewatch(null); ctl?.endRewatch(); }, [ctl]);

  if (!s || !ctl) return <div className="grid min-h-dvh place-items-center"><PlaneMark size={72} className="animate-float-soft" /></div>;
  const conn = CONN[s.connection];

  return (
    <div className="flex min-h-dvh flex-col bg-paper lg:h-dvh lg:overflow-hidden">
      {/* top bar */}
      <header className="flex items-center gap-3 border-b border-line bg-paper/90 px-4 py-2.5 backdrop-blur lg:px-6">
        <Link href="/dashboard" className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-line bg-surface text-ink-2 hover:text-ink" aria-label={t("class.leave")}>
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="min-w-0 flex-1">
          <p className="truncate font-display text-xl leading-tight text-ink sm:text-2xl" data-testid="lesson-title">{s.title || "…"}</p>
          <p className="truncate text-xs text-ink-3">{s.statusKey ? t(s.statusKey) : ""}</p>
        </div>
        <Progress s={s} />
        <span className={cn("hidden items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold sm:inline-flex", conn.tone)} data-testid="connection">{conn.icon}{t(conn.key)}</span>
        <LanguageToggle className="hidden md:flex" />
      </header>

      <div className="grid min-h-0 flex-1 gap-4 p-3 sm:p-4 lg:grid-cols-[minmax(0,1fr)_400px] lg:p-5 xl:grid-cols-[minmax(0,1fr)_440px]">
        {/* left: stage + concept rail */}
        <div className="flex min-h-0 min-w-0 flex-col gap-3">
          <div className="relative overflow-hidden rounded-[26px] bg-[#1d2a44] shadow-[var(--shadow-lift)] lg:min-h-0 lg:flex-1">
            <div className="relative aspect-video w-full lg:absolute lg:inset-0 lg:aspect-auto">
              <video ref={setVideo} playsInline controls={!s.stopped}
                className={cn("h-full w-full bg-black object-contain transition-[filter] duration-500", !s.videoVisible && "invisible", s.question && "blur-[3px] brightness-75")}
                data-cursor="video" data-testid="lesson-video" />
              {!s.videoVisible && !s.overlay && (
                <div className="absolute inset-0 grid place-items-center"><PlaneMark size={80} className="animate-float-soft opacity-80" /></div>
              )}

              {/* adaptation pill */}
              <AnimatePresence>
                {s.adaptation && !s.overlay && (
                  <motion.div initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: -20, opacity: 0 }}
                    className="absolute left-1/2 top-4 z-30 flex -translate-x-1/2 items-center gap-2 rounded-full bg-surface/95 px-4 py-2 text-sm shadow-[var(--shadow-lift)] backdrop-blur" role="status" data-testid="adaptation">
                    {s.adaptation.action === "HUMAN" ? <Hand className="h-4 w-4 text-amber" /> : <RefreshCw className="h-4 w-4 animate-spin text-sky-600 [animation-duration:2s]" />}
                    {t(s.adaptation.slow ? "class.stillWorking" : s.adaptation.action === "MODIFY" ? "class.modify" : s.adaptation.action === "REGENERATE" ? "class.regenerate" : "class.mentorNotified")}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* question over the paused video (desktop); bottom sheet on phones */}
              <AnimatePresence>
                {s.question && !s.overlay && (
                  <motion.div key="q" className="fixed inset-x-0 bottom-0 z-40 flex justify-center p-3 sm:absolute sm:inset-0 sm:items-center sm:overflow-y-auto sm:bg-ink/25 sm:p-6"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    <QuestionCard q={s.question} grading={s.grading} feedback={s.feedbackFor === s.question.interaction_id ? s.feedback : null}
                      onSubmit={(a) => ctl.submit(a)} checks={s.checkpoints} />
                  </motion.div>
                )}
              </AnimatePresence>

              <AnimatePresence>{s.overlay && <StageOverlay key={s.overlay.kind} s={s} ctl={ctl} lessonId={id} />}</AnimatePresence>
            </div>
          </div>
          <ConceptRail s={s} onRewatch={openRewatch} />
        </div>

        {/* right: study panel (sits beside the video, not under it) */}
        <motion.aside initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5, ease: EASE, delay: 0.1 }} className="min-h-[420px] lg:min-h-0">
          <StudyPanel s={s} lessonId={id} />
        </motion.aside>
      </div>

      <RewatchDialog node={rewatch} onClose={closeRewatch} />
    </div>
  );
}

function Progress({ s }: { s: ClassroomState }) {
  const { n } = useI18n();
  return (
    <div className="hidden w-40 items-center gap-2 md:flex" aria-label="progress">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-paper-3">
        <motion.div className="h-full rounded-full bg-sky-600" animate={{ width: `${s.progress.pct}%` }} transition={{ duration: 0.6, ease: EASE }} />
      </div>
      <span className="text-xs tabular-nums text-ink-3" data-testid="progress-label">{n(s.progress.done)}/{n(s.progress.total)}</span>
    </div>
  );
}
