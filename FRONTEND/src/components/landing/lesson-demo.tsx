"use client";

/**
 * The hero's live mini-lesson. It plays captions over a chalk-blue board,
 * then pauses on its own (॥) and asks the visitor. Wrong → it re-explains
 * differently and asks again. Right → it resumes. Exactly what the product does.
 */
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { Check, Pause, Play, RotateCcw, X } from "lucide-react";
import { useI18n } from "@/providers/i18n";
import { cn, EASE } from "@/lib/utils";

type Phase = "playing" | "asking" | "wrong" | "right";
const PAUSE_AT = 72;

export function LessonDemo() {
  const { t } = useI18n();
  const [phase, setPhase] = useState<Phase>("playing");
  const [progress, setProgress] = useState(0);
  const [picked, setPicked] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const raf = useRef(0);

  useEffect(() => {
    if (phase !== "playing" && phase !== "right") return;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = now - last;
      last = now;
      setProgress((p) => {
        const next = p + dt / 90;
        if (phase === "playing" && p < PAUSE_AT && next >= PAUSE_AT) { setPhase("asking"); return PAUSE_AT; }
        if (next >= 100) return 100;
        return next;
      });
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [phase]);

  const restart = () => { setProgress(0); setPicked(null); setAttempt(0); setPhase("playing"); };
  useEffect(() => {
    if (progress < 100) return;
    const id = setTimeout(restart, 1800);
    return () => clearTimeout(id);
  }, [progress]);
  const answer = (id: string) => {
    setPicked(id);
    setAttempt((a) => a + 1);
    if (id === "A") { setPhase("right"); setProgress((p) => p + 0.5); }
    else setPhase("wrong");
  };

  const captions = [t("demo.caption1"), t("demo.caption2"), t("demo.caption3")];
  const caption = captions[Math.min(2, Math.floor((progress / PAUSE_AT) * 3))];
  const paused = phase === "asking" || phase === "wrong";
  const opts = [["A", t("demo.optA")], ["B", t("demo.optB")], ["C", t("demo.optC")]] as const;

  return (
    <div className="relative w-full overflow-hidden rounded-[28px] border border-line bg-surface shadow-[var(--shadow-lift)]" data-cursor="video">
      {/* window bar */}
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <span className="flex gap-1.5">{["#e5917f", "#f0c35a", "#9cbce8"].map((c) => <i key={c} className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />)}</span>
        <span className="truncate px-3 text-xs text-ink-3">{t("demo.label")}</span>
        <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[0.68rem] font-semibold", paused ? "bg-marigold-100 text-marigold-600" : "bg-sky-50 text-sky-700")}>
          <span className={cn("h-1.5 w-1.5 rounded-full", paused ? "bg-marigold-600" : "animate-pulse bg-sky-600")} />
          {paused ? t("demo.paused") : t("demo.playing")}
        </span>
      </div>

      {/* the "video" board */}
      <div className="relative aspect-[16/10] overflow-hidden bg-[#2a3a5c]">
        <div className="absolute inset-0 opacity-[0.08]" style={{ backgroundImage: "radial-gradient(#fff 1px, transparent 1px)", backgroundSize: "14px 14px" }} />
        {/* the diagram: a bus and a passenger leaning */}
        <svg viewBox="0 0 320 200" className="absolute inset-x-6 top-5 h-[62%] w-[calc(100%-3rem)]" fill="none" stroke="#f5f1e6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <motion.path d="M20 150 H300" strokeDasharray="6 8" animate={{ strokeDashoffset: paused ? 0 : [-28, 0] }} transition={{ repeat: Infinity, duration: 0.6, ease: "linear" }} />
          <rect x="70" y="70" width="170" height="70" rx="12" />
          <circle cx="105" cy="146" r="10" /><circle cx="205" cy="146" r="10" />
          <rect x="92" y="84" width="34" height="22" rx="3" opacity="0.6" /><rect x="138" y="84" width="34" height="22" rx="3" opacity="0.6" /><rect x="184" y="84" width="34" height="22" rx="3" opacity="0.6" />
          <motion.g style={{ originX: "155px", originY: "132px" }} animate={{ rotate: progress > 30 ? 16 : 0 }} transition={{ type: "spring", stiffness: 120, damping: 8 }}>
            <circle cx="155" cy="96" r="7" fill="#f0c35a" stroke="none" />
            <path d="M155 103 V128 M155 110 L166 116" stroke="#f0c35a" />
          </motion.g>
          <motion.path d="M250 105 h34 m-8 -7 l8 7 l-8 7" stroke="#e5917f" initial={{ pathLength: 0 }} animate={{ pathLength: progress > 30 ? 1 : 0 }} />
        </svg>
        {/* caption */}
        <AnimatePresence mode="wait">
          <motion.p key={phase === "wrong" ? "re" : caption} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.35, ease: EASE }}
            className="absolute inset-x-4 bottom-4 mx-auto w-fit max-w-[92%] rounded-xl bg-black/45 px-3 py-1.5 text-center text-[0.82rem] text-white backdrop-blur-sm sm:text-sm">
            {phase === "wrong" ? t("demo.reexplain") : phase === "right" ? t("demo.resumes") : caption}
          </motion.p>
        </AnimatePresence>
        {/* the ॥ that appears when it pauses */}
        <AnimatePresence>
          {paused && (
            <motion.div initial={{ scale: 0.4, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 1.4, opacity: 0 }} className="absolute right-4 top-4 grid h-11 w-11 place-items-center rounded-full bg-marigold text-ink">
              <Pause className="h-5 w-5" fill="currentColor" />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* progress with a checkpoint notch */}
      <div className="relative mx-4 mt-3 h-1.5 rounded-full bg-paper-3">
        <div className="h-full rounded-full bg-sky-600" style={{ width: `${progress}%` }} />
        <span className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface bg-marigold shadow" style={{ left: `${PAUSE_AT}%` }} />
      </div>

      {/* the question panel */}
      <div className="relative min-h-[178px] px-4 pb-4 pt-3">
        <AnimatePresence mode="wait">
          {paused ? (
            <motion.div key="q" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.35, ease: EASE }}>
              <p className="font-medium text-ink">{t("demo.question")}</p>
              <div className="mt-2.5 grid gap-2">
                {opts.map(([id, label]) => {
                  const wrongPick = phase === "wrong" && picked === id;
                  return (
                    <motion.button key={id} onClick={() => answer(id)} disabled={wrongPick}
                      animate={wrongPick ? { x: [0, -6, 6, -3, 0] } : {}}
                      className={cn("flex items-center gap-3 rounded-xl border px-3 py-2 text-left text-sm transition-colors",
                        wrongPick ? "border-rose/40 bg-rose-100/60 text-ink-2" : "border-line hover:border-sky-300 hover:bg-sky-50")}>
                      <span className={cn("grid h-6 w-6 shrink-0 place-items-center rounded-lg text-xs font-semibold", wrongPick ? "bg-rose text-white" : "bg-paper-2 text-ink-2")}>
                        {wrongPick ? <X className="h-3.5 w-3.5" /> : id}
                      </span>
                      {label}
                    </motion.button>
                  );
                })}
              </div>
              {phase === "wrong" && <p className="mt-2 text-xs text-rose">{t("demo.wrong")} · {t("demo.tryAgain")}</p>}
            </motion.div>
          ) : phase === "right" ? (
            <motion.div key="ok" initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} className="flex items-start gap-3 rounded-2xl bg-sage-100 p-4">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-sage text-white"><Check className="h-4 w-4" /></span>
              <div>
                <p className="text-sm text-ink">{t("demo.right")}</p>
                {attempt > 1 && <p className="mt-1 font-hand text-lg text-sky-700">{t("demo.resumes")}</p>}
              </div>
              <button onClick={restart} className="ml-auto grid h-8 w-8 shrink-0 place-items-center rounded-lg text-ink-3 hover:bg-white/60" aria-label="Replay"><RotateCcw className="h-4 w-4" /></button>
            </motion.div>
          ) : (
            <motion.div key="wait" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-2 pt-1">
              <div className="flex items-center gap-2 text-xs text-ink-3"><Play className="h-3 w-3" fill="currentColor" /> {t("hero.ctaSecondary")}</div>
              <div className="skeleton h-3 w-4/5" /><div className="skeleton h-3 w-3/5" /><div className="skeleton h-3 w-2/3" />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
