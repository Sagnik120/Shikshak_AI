"use client";

import Link from "next/link";
import { useDeferredValue, useState } from "react";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { FileText, Plus, Sparkles, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/core/api";
import type { Lesson, LessonStatus } from "@/core/types";
import { useI18n } from "@/providers/i18n";
import { Button } from "@/components/ui/button";
import { Badge, Ring, Skeleton } from "@/components/ui/primitives";
import { GlassSearch } from "@/components/ui/glass-search";
import { STATUS_TONE, lessonHref, relativeDays } from "@/lib/lesson";
import { cn } from "@/lib/utils";

const FILTERS: Array<"all" | LessonStatus> = ["all", "in_progress", "escalated", "completed", "planned"];

export default function LessonsPage() {
  const { t, n, lang } = useI18n();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<(typeof FILTERS)[number]>("all");
  const term = useDeferredValue(search.trim());
  const q = useQuery({ queryKey: ["lessons", "list", status, term], queryFn: () => api.listLessons({ status, search: term || undefined, limit: 100 }), placeholderData: keepPreviousData });

  const del = async (l: Lesson) => {
    if (!window.confirm(t("lessons.deleteConfirm", { t: l.title }))) return;
    try { await api.deleteLesson(l.id); toast.success(t("lessons.deleted")); qc.invalidateQueries({ queryKey: ["lessons"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); }
    catch (e) { toast.error((e as Error).message); }
  };

  return (
    <div className="mx-auto max-w-6xl px-5 py-8 lg:px-10 lg:py-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-5xl text-ink sm:text-6xl">{t("lessons.title")}</h1>
          <p className="mt-2 text-ink-2">{t("lessons.sub")}</p>
        </div>
        <Button href="/new" icon={<Plus className="h-4 w-4" />}>{t("nav.newLesson")}</Button>
      </header>

      <GlassSearch className="mt-8" value={search} onChange={setSearch} placeholder={t("lessons.search")} />
      <div className="no-scrollbar mt-4 flex gap-2 overflow-x-auto">
        {FILTERS.map((f) => (
          <button key={f} onClick={() => setStatus(f)}
            className={cn("relative shrink-0 rounded-full px-4 py-1.5 text-sm transition-colors", status === f ? "text-white" : "border border-line bg-surface text-ink-2 hover:text-ink")}>
            {status === f && <motion.span layoutId="lesson-filter" className="absolute inset-0 -z-0 rounded-full bg-ink" transition={{ type: "spring", stiffness: 450, damping: 34 }} />}
            <span className="relative">{f === "all" ? t("lessons.all") : t(`status.${f}` as "status.completed")}</span>
          </button>
        ))}
      </div>

      {q.isLoading ? (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-48 rounded-[24px]" />)}</div>
      ) : (q.data?.lessons.length ?? 0) === 0 ? (
        <p className="py-20 text-center text-ink-3">{t("lessons.empty")}</p>
      ) : (
        <motion.div layout className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <AnimatePresence>
            {q.data!.lessons.map((l, i) => (
              <motion.div key={l.id} layout initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0, transition: { delay: Math.min(i, 8) * 0.03 } }} exit={{ opacity: 0, scale: 0.96 }}>
                <article className="group relative flex h-full flex-col rounded-[24px] border border-line bg-surface p-5 shadow-[var(--shadow-soft)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[var(--shadow-lift)]">
                  <div className="flex items-start justify-between gap-3">
                    <span className="grid h-10 w-10 place-items-center rounded-xl bg-sky-50 text-sky-700">{l.source === "document" ? <FileText className="h-5 w-5" /> : <Sparkles className="h-5 w-5" />}</span>
                    <Ring value={l.progress_pct} size={46} stroke={4} color="var(--sky-600)" label={<span className="text-[0.62rem] font-semibold">{n(Math.round(l.progress_pct))}</span>} />
                  </div>
                  <Link href={lessonHref(l)} className="mt-4 line-clamp-2 font-display text-2xl leading-tight text-ink after:absolute after:inset-0">{l.title}</Link>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    <Badge tone={STATUS_TONE[l.status]} dot>{t(`status.${l.status}` as "status.completed")}</Badge>
                    {l.to_review > 0 && <Badge tone="marigold">{t("status.toReview", { n: n(l.to_review) })}</Badge>}
                    {l.score_pct != null && l.status === "completed" && <Badge tone="sage">{n(Math.round(l.score_pct))}%</Badge>}
                  </div>
                  <div className="mt-auto flex items-center justify-between pt-5 text-xs text-ink-3">
                    <span>{t("common.concepts", { n: n(l.node_count) })} · {relativeDays(l.updated_at, lang)}</span>
                    <button onClick={() => del(l)} className="relative z-10 grid h-8 w-8 place-items-center rounded-lg opacity-0 transition-opacity hover:bg-rose-100 hover:text-rose focus:opacity-100 group-hover:opacity-100" aria-label={t("common.delete")}>
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </article>
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
      )}
    </div>
  );
}
