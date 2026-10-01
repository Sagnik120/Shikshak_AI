"use client";

import Link from "next/link";
import { ArrowUpRight, FileText, Sparkles } from "lucide-react";
import type { Lesson } from "@/core/types";
import { Badge, Ring } from "@/components/ui/primitives";
import { useI18n } from "@/providers/i18n";
import { STATUS_TONE, lessonHref, relativeDays } from "@/lib/lesson";

export function LessonRow({ lesson }: { lesson: Lesson }) {
  const { t, n, lang } = useI18n();
  return (
    <Link href={lessonHref(lesson)} className="group flex items-center gap-4 rounded-2xl px-3 py-3 transition-colors hover:bg-paper-2" data-cursor="link">
      <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-sky-50 text-sky-700">
        {lesson.source === "document" ? <FileText className="h-5 w-5" /> : <Sparkles className="h-5 w-5" />}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-ink">{lesson.title}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ink-3">
          <Badge tone={STATUS_TONE[lesson.status]} dot>{t(`status.${lesson.status}` as "status.completed")}</Badge>
          {lesson.to_review > 0 && <Badge tone="marigold">{t("status.toReview", { n: n(lesson.to_review) })}</Badge>}
          <span>{relativeDays(lesson.updated_at, lang)}</span>
        </div>
      </div>
      <Ring value={lesson.progress_pct} size={44} stroke={4} color="var(--sky-600)" label={<span className="text-[0.62rem] font-semibold">{n(Math.round(lesson.progress_pct))}</span>} />
      <ArrowUpRight className="h-4 w-4 shrink-0 text-ink-3 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-ink" />
    </Link>
  );
}
