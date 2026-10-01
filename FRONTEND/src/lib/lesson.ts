import type { Lesson } from "@/core/types";
import type { Tone } from "@/components/ui/primitives";

/** Where a lesson card should take the learner. */
export function lessonHref(l: Pick<Lesson, "id" | "status" | "review_pending">) {
  if (l.status === "completed") return l.review_pending ? `/review/${l.id}` : `/report/${l.id}`;
  return `/learn/${l.id}`;
}

export const STATUS_TONE: Record<string, Tone> = {
  created: "neutral", planned: "sky", in_progress: "sky", completed: "sage", escalated: "amber", abandoned: "rose",
};

export function relativeDays(iso: string, lang: string) {
  const diff = (new Date(iso).getTime() - Date.now()) / 86400000;
  const rtf = new Intl.RelativeTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", { numeric: "auto" });
  if (Math.abs(diff) < 1) {
    const h = Math.round(diff * 24);
    return Math.abs(h) < 1 ? rtf.format(Math.round(diff * 1440), "minute") : rtf.format(h, "hour");
  }
  return rtf.format(Math.round(diff), "day");
}
