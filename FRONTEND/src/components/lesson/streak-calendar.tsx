"use client";

/**
 * The learner's month, as a calendar: real dates, intensity by how much they
 * did, consecutive learning days joined by a marigold ribbon, a flame on the
 * days of the current streak, and a tooltip per day. Months turn like pages.
 */
import { AnimatePresence, motion } from "motion/react";
import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Flame, Trophy } from "lucide-react";
import type { Journey, JourneyDay } from "@/core/types";
import { useI18n } from "@/providers/i18n";
import { EASE, cn } from "@/lib/utils";

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const score = (d?: JourneyDay) => (d ? d.answers + d.videos * 2 + d.practice + d.completed * 5 + (d.started ? 1 : 0) : 0);
const level = (s: number) => (s <= 0 ? 0 : s < 4 ? 1 : s < 10 ? 2 : s < 20 ? 3 : 4);
const SHADES = ["", "#dfeaf9", "#9cbce8", "#4c7cc7", "#2f528c"];

export function StreakCalendar({ journey }: { journey: Journey }) {
  const { t, n, lang } = useI18n();
  const locale = lang === "hi" ? "hi-IN" : "en-IN";
  const today = new Date(journey.today + "T00:00:00");
  const [cursor, setCursor] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [dir, setDir] = useState(0);
  const [hover, setHover] = useState<string | null>(null);

  const byDate = useMemo(() => new Map(journey.days.map((d) => [d.date, d])), [journey.days]);
  const first = journey.days[0]?.date ?? journey.today;
  const active = (key: string) => score(byDate.get(key)) > 0;

  // Days belonging to the current streak (ending today or yesterday).
  const streakDays = useMemo(() => {
    const set = new Set<string>();
    if (!journey.streak.current) return set;
    const d = new Date(today);
    if (!active(iso(d))) d.setDate(d.getDate() - 1);
    while (active(iso(d))) { set.add(iso(d)); d.setDate(d.getDate() - 1); }
    return set;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [journey]);

  const monthKey = `${cursor.getFullYear()}-${cursor.getMonth()}`;
  const cells = useMemo(() => {
    const start = new Date(cursor);
    const lead = (start.getDay() + 6) % 7; // Monday first
    start.setDate(start.getDate() - lead);
    return Array.from({ length: 42 }, (_, i) => { const d = new Date(start); d.setDate(start.getDate() + i); return d; });
  }, [cursor]);
  const weeks = cells[35].getMonth() !== cursor.getMonth() ? cells.slice(0, 35) : cells;

  const canPrev = iso(new Date(cursor.getFullYear(), cursor.getMonth(), 0)) >= first.slice(0, 8) + "01";
  const canNext = cursor.getFullYear() < today.getFullYear() || cursor.getMonth() < today.getMonth();
  const go = (delta: number) => { setDir(delta); setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + delta, 1)); };

  const weekdayNames = useMemo(() => {
    const f = new Intl.DateTimeFormat(locale, { weekday: "narrow" });
    return Array.from({ length: 7 }, (_, i) => f.format(new Date(2024, 0, 1 + i)));
  }, [locale]);
  const monthName = new Intl.DateTimeFormat(locale, { month: "long", year: "numeric" }).format(cursor);
  const longDate = new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "long" });
  const monthActive = weeks.filter((d) => d.getMonth() === cursor.getMonth() && active(iso(d))).length;
  const todayDone = active(journey.today);
  const hovered = hover ? byDate.get(hover) : undefined;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-2xl">{t("cal.title")}</h2>
        <div className="flex gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-marigold-50 px-3 py-1 text-sm font-medium text-marigold-600">
            <motion.span animate={journey.streak.current ? { rotate: [-6, 6, -6], y: [0, -1, 0] } : {}} transition={{ repeat: Infinity, duration: 1.6 }}>
              <Flame className="h-4 w-4" fill={journey.streak.current ? "currentColor" : "none"} />
            </motion.span>
            {t(journey.streak.current === 1 ? "cal.day1" : "cal.days", { n: n(journey.streak.current) })}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-paper-2 px-3 py-1 text-sm text-ink-2" title={t("cal.longest")}>
            <Trophy className="h-3.5 w-3.5" />{n(journey.streak.longest)}
          </span>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between">
        <button onClick={() => go(-1)} disabled={!canPrev} className="grid h-8 w-8 place-items-center rounded-lg text-ink-2 hover:bg-paper-2 disabled:opacity-30" aria-label="previous month"><ChevronLeft className="h-4 w-4" /></button>
        <AnimatePresence mode="popLayout" custom={dir} initial={false}>
          <motion.p key={monthKey} custom={dir} initial={{ opacity: 0, x: dir * 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: dir * -20 }} transition={{ duration: 0.3, ease: EASE }}
            className="font-medium text-ink">{monthName}</motion.p>
        </AnimatePresence>
        <button onClick={() => go(1)} disabled={!canNext} className="grid h-8 w-8 place-items-center rounded-lg text-ink-2 hover:bg-paper-2 disabled:opacity-30" aria-label="next month"><ChevronRight className="h-4 w-4" /></button>
      </div>

      <div className="mt-3 grid grid-cols-7 text-center text-[0.7rem] font-medium text-ink-3">
        {weekdayNames.map((w, i) => <span key={i}>{w}</span>)}
      </div>

      <div className="relative mt-1 overflow-hidden">
        <AnimatePresence mode="popLayout" custom={dir} initial={false}>
          <motion.div key={monthKey} className="grid grid-cols-7 gap-y-1.5"
            initial={{ opacity: 0, x: dir * 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: dir * -40 }} transition={{ duration: 0.35, ease: EASE }}>
            {weeks.map((d, i) => {
              const key = iso(d);
              const inMonth = d.getMonth() === cursor.getMonth();
              const future = key > journey.today;
              const day = byDate.get(key);
              const lv = level(score(day));
              const on = lv > 0;
              const col = i % 7;
              const prevOn = col > 0 && active(iso(new Date(d.getFullYear(), d.getMonth(), d.getDate() - 1)));
              const nextOn = col < 6 && active(iso(new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1)));
              const isToday = key === journey.today;
              const inStreak = streakDays.has(key);
              return (
                <div key={key} className="relative flex h-10 items-center justify-center"
                  onMouseEnter={() => setHover(key)} onMouseLeave={() => setHover(null)}>
                  {/* the ribbon joining consecutive learning days */}
                  {on && inMonth && prevOn && <motion.span className="absolute left-0 right-1/2 top-1/2 h-5 -translate-y-1/2 bg-marigold-200" initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} style={{ originX: 1 }} transition={{ delay: 0.25 + i * 0.008 }} />}
                  {on && inMonth && nextOn && <motion.span className="absolute left-1/2 right-0 top-1/2 h-5 -translate-y-1/2 bg-marigold-200" initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} style={{ originX: 0 }} transition={{ delay: 0.25 + i * 0.008 }} />}
                  <motion.span
                    initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.008, duration: 0.3 }}
                    className={cn("relative z-10 grid h-9 w-9 place-items-center rounded-full text-xs tabular-nums transition-shadow",
                      !inMonth && "opacity-25", future && "text-ink-3/50",
                      on ? (lv >= 3 ? "font-semibold text-white" : "font-semibold text-sky-700") : "text-ink-2",
                      isToday && "ring-2 ring-sky-600 ring-offset-2 ring-offset-surface",
                      hover === key && "shadow-[var(--shadow-lift)]")}
                    style={on ? { background: SHADES[lv] } : undefined}>
                    {n(d.getDate())}
                    {inStreak && inMonth && <Flame className="absolute -right-1 -top-1.5 h-3.5 w-3.5 text-marigold-600" fill="currentColor" />}
                  </motion.span>
                </div>
              );
            })}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* hovered day / footer */}
      <div className="mt-3 min-h-14 rounded-2xl bg-paper-2 px-4 py-2.5 text-sm">
        {hover ? (
          <>
            <p className="font-medium text-ink">{longDate.format(new Date(hover + "T00:00:00"))}</p>
            {hovered && score(hovered) > 0 ? (
              <p className="mt-0.5 text-xs text-ink-2">
                {[hovered.answers && t("cal.answers", { n: n(hovered.answers) }), hovered.videos && t("cal.videos", { n: n(hovered.videos) }),
                  hovered.minutes >= 1 && t("cal.minutes", { n: n(Math.round(hovered.minutes)) }), hovered.completed && t("cal.finished", { n: n(hovered.completed) })]
                  .filter(Boolean).join(" · ")}
              </p>
            ) : <p className="mt-0.5 text-xs text-ink-3">{t("cal.none")}</p>}
          </>
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className={cn("text-xs", todayDone ? "text-sage" : "text-marigold-600")}>{todayDone ? t("cal.done") : t("cal.keep")}</p>
            <p className="text-xs text-ink-3">{t("cal.activeDays", { n: n(monthActive) })}</p>
          </div>
        )}
      </div>
      <div className="mt-2 flex items-center justify-end gap-1.5 text-[0.68rem] text-ink-3">
        {t("cal.less")}
        {[0, 1, 2, 3, 4].map((l) => <i key={l} className="h-3 w-3 rounded-full" style={{ background: l ? SHADES[l] : "var(--paper-3)" }} />)}
        {t("cal.more")}
      </div>
    </div>
  );
}
