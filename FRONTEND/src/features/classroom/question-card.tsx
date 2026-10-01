"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { AlertCircle, Check, CornerDownLeft, Loader2, PauseCircle } from "lucide-react";
import type { EvaluationEvent, InteractionEvent } from "@/core/types";
import type { MessageKey } from "@/core/i18n";
import { useI18n } from "@/providers/i18n";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/primitives";
import { cn, EASE } from "@/lib/utils";

/**
 * The checkpoint, laid over the paused video. The typed answer survives a
 * reconnect because it lives here, keyed by interaction_id.
 */
export function QuestionCard({ q, grading, feedback, onSubmit, checks }: {
  q: InteractionEvent; grading: boolean; feedback: EvaluationEvent | null; onSubmit: (a: string) => void;
  checks: { passed: number; total: number };
}) {
  const { t, n } = useI18n();
  const [picked, setPicked] = useState<string | null>(null);
  const [text, setText] = useState("");
  const area = useRef<HTMLTextAreaElement>(null);
  const isMcq = q.options?.length > 0;
  const answer = isMcq ? picked : text.trim();
  const canSubmit = !grading && !feedback && !!answer && (isMcq || text.trim().length >= 2);

  // A genuinely new question clears the old answer; a re-ask keeps it.
  const [forId, setForId] = useState(q.interaction_id);
  if (forId !== q.interaction_id) { setForId(q.interaction_id); setPicked(null); setText(""); }
  useEffect(() => { if (!isMcq) setTimeout(() => area.current?.focus(), 150); }, [q.interaction_id, isMcq]);

  const tone = feedback ? (feedback.correct ? "correct" : feedback.partial_credit >= 0.5 ? "partial" : "wrong") : null;

  return (
    <motion.div
      key={q.interaction_id}
      initial={{ y: 40, opacity: 0, scale: 0.98 }}
      animate={{ y: 0, opacity: 1, scale: 1 }}
      exit={{ y: 30, opacity: 0 }}
      transition={{ duration: 0.45, ease: EASE }}
      className="w-full max-w-xl rounded-[26px] border border-white/60 bg-surface/95 p-5 shadow-[0_30px_60px_-20px_rgb(30_41_66/0.45)] backdrop-blur-xl sm:p-6"
      role="dialog" aria-label={t("class.questionTime")}
      data-testid="question-card"
      data-interaction={q.interaction_id}
      data-grading={grading ? "1" : "0"}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 rounded-full bg-marigold-100 px-3 py-1 text-xs font-semibold text-marigold-600">
          <PauseCircle className="h-3.5 w-3.5" />{t((`class.kind.${q.type}` as MessageKey)) ?? t("class.questionTime")}
        </span>
        {checks.total > 0 && <span className="text-xs text-ink-3">{t("class.checkpointOf", { a: n(Math.min(checks.total, checks.passed + 1)), b: n(checks.total) })}</span>}
      </div>
      <p className="mt-3 font-display text-2xl leading-snug text-ink sm:text-[1.7rem]">{q.question_text}</p>

      {isMcq ? (
        <div className="mt-4 grid gap-2" role="radiogroup">
          {q.options.map((opt, i) => {
            const chosen = picked === opt;
            const mark = chosen && tone ? (tone === "correct" ? "correct" : "wrong") : null;
            return (
              <motion.button key={opt} type="button" role="radio" aria-checked={chosen} disabled={grading || !!feedback}
                onClick={() => setPicked(opt)} whileTap={{ scale: 0.985 }}
                animate={mark === "wrong" ? { x: [0, -7, 7, -4, 0] } : {}}
                className={cn("flex items-center gap-3 rounded-2xl border px-4 py-3 text-left text-[0.95rem] transition-colors",
                  mark === "correct" ? "border-sage bg-sage-100" : mark === "wrong" ? "border-rose/50 bg-rose-100/60" :
                  chosen ? "border-sky-500 bg-sky-50" : "border-line hover:border-sky-300")}>
                <span className={cn("grid h-7 w-7 shrink-0 place-items-center rounded-lg text-xs font-semibold",
                  mark === "correct" ? "bg-sage text-white" : mark === "wrong" ? "bg-rose text-white" : chosen ? "bg-sky-600 text-white" : "bg-paper-2 text-ink-2")}>
                  {mark === "correct" ? <Check className="h-4 w-4" /> : String.fromCharCode(65 + i)}
                </span>
                <span>{opt}</span>
              </motion.button>
            );
          })}
          <p className="text-xs text-ink-3">{t("class.pickOne")}</p>
        </div>
      ) : (
        <div className="mt-4">
          <Textarea ref={area} value={text} onChange={(e) => setText(e.target.value)} rows={3} disabled={grading || !!feedback}
            placeholder={t("class.answerPlaceholder")} aria-label={t("class.yourAnswer")}
            onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && canSubmit) onSubmit(text.trim()); }} />
          <p className="mt-1 flex items-center gap-1 text-xs text-ink-3"><CornerDownLeft className="h-3 w-3" />{t("class.submitHint")}</p>
        </div>
      )}

      <AnimatePresence mode="wait">
        {feedback ? (
          <motion.div key="fb" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className={cn("mt-4 rounded-2xl p-4", tone === "correct" ? "bg-sage-100" : tone === "partial" ? "bg-marigold-50" : "bg-rose-100/60")} role="status" data-testid="feedback">
            <p className={cn("flex items-center gap-2 font-semibold", tone === "correct" ? "text-sage" : tone === "partial" ? "text-marigold-600" : "text-rose")}>
              {tone === "correct" ? <Check className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
              {t(tone === "correct" ? "class.correct" : tone === "partial" ? "class.nearly" : "class.notQuite")}
            </p>
            {feedback.feedback_text && <p className="mt-1 text-sm text-ink-2">{feedback.feedback_text}</p>}
            {feedback.misconception_tag && <p className="mt-1.5 text-xs text-ink-3">{t("class.misconception", { t: feedback.misconception_tag })}</p>}
            <p className="mt-2 flex items-center gap-1.5 font-hand text-lg text-sky-700"><Loader2 className="h-3.5 w-3.5 animate-spin" />{t("class.continuing")}</p>
          </motion.div>
        ) : (
          <motion.div key="btn" className="mt-4 flex justify-end">
            <Button onClick={() => answer && onSubmit(answer)} disabled={!canSubmit} status={grading ? "loading" : "idle"} loadingLabel={t("class.grading")} data-testid="submit-answer">
              {t("class.submit")}
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
