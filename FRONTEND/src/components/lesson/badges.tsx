"use client";

/**
 * Achievement badges: paper rosettes coloured by tier (bronze → silver → gold
 * → sky → ink …), one icon per achievement. Locked ones stay grey with a
 * progress ring showing how close the learner is.
 */
import { AnimatePresence, motion } from "motion/react";
import { useMemo, useState } from "react";
import {
  BookOpen, Brain, CalendarDays, CalendarHeart, CheckCheck, Dumbbell, FileText, Flame, Languages, Lock,
  MessageSquareText, RefreshCw, Star, Target,
} from "lucide-react";
import type { Badge, Journey } from "@/core/types";
import type { MessageKey } from "@/core/i18n";
import { useI18n } from "@/providers/i18n";
import { EASE, cn } from "@/lib/utils";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  first_lesson: BookOpen, lessons_completed: CheckCheck, streak: Flame, active_days: CalendarDays, answers: MessageSquareText,
  right_in_a_row: Target, concepts_mastered: Brain, perfect_lesson: Star, comeback: RefreshCw, own_notes: FileText,
  practice: Dumbbell, bilingual: Languages, month: CalendarHeart,
};
const TIERS = [
  { fill: "#e9c4a2", edge: "#b8794a", ink: "#7a4a24" }, // bronze
  { fill: "#e3e8ef", edge: "#93a1b5", ink: "#4a5671" }, // silver
  { fill: "#fbe7a8", edge: "#d9a62a", ink: "#8a6510" }, // gold
  { fill: "#dfeaf9", edge: "#4c7cc7", ink: "#2f528c" }, // sky
  { fill: "#d7dbe6", edge: "#1e2942", ink: "#1e2942" }, // ink
  { fill: "#fbe1da", edge: "#e5917f", ink: "#a2493a" }, // coral
  { fill: "#e3f0e7", edge: "#5f9474", ink: "#3d6b50" }, // sage
  { fill: "#f5e6ff", edge: "#8b63c9", ink: "#5b3b8f" }, // violet
];

function rosette(cx: number, cy: number, r: number, points = 16, depth = 0.08) {
  const pts = Array.from({ length: points * 2 }, (_, i) => {
    const a = (Math.PI * i) / points - Math.PI / 2;
    const rr = i % 2 ? r * (1 - depth) : r;
    return `${(cx + rr * Math.cos(a)).toFixed(2)},${(cy + rr * Math.sin(a)).toFixed(2)}`;
  });
  return `M${pts.join("L")}Z`;
}

export function Medal({ group, tier, earned, progress = 0, size = 76, label }: { group: string; tier: number; earned: boolean; progress?: number; size?: number; label?: string }) {
  const Icon = ICONS[group] ?? Star;
  const c = TIERS[Math.min(tier, TIERS.length - 1)];
  const r = 30;
  const ring = 2 * Math.PI * 34;
  return (
    <div className="relative" style={{ width: size, height: size * 1.12 }}>
      <svg viewBox="0 0 80 90" width={size} height={size * 1.12} className={cn(!earned && "grayscale")} aria-hidden>
        {/* ribbon tails */}
        <path d="M28 58 L22 86 L31 80 L36 88 L40 62Z" fill={earned ? c.edge : "#cfd4dc"} opacity={0.9} />
        <path d="M52 58 L58 86 L49 80 L44 88 L40 62Z" fill={earned ? c.edge : "#cfd4dc"} opacity={0.75} />
        <path d={rosette(40, 38, r + 5)} fill={earned ? c.edge : "#d5d9e0"} />
        <circle cx="40" cy="38" r={r - 1} fill={earned ? c.fill : "#eef0f3"} stroke="#fff" strokeWidth="1.5" />
        <circle cx="40" cy="38" r={r - 6} fill="none" stroke={earned ? c.edge : "#cfd4dc"} strokeDasharray="2 3" strokeWidth="1" />
        {!earned && progress > 0 && (
          <circle cx="40" cy="38" r="34" fill="none" stroke="var(--sky-500)" strokeWidth="3" strokeLinecap="round"
            strokeDasharray={`${ring * Math.min(1, progress)} ${ring}`} transform="rotate(-90 40 38)" />
        )}
      </svg>
      <span className="absolute left-1/2 top-[38%] grid -translate-x-1/2 -translate-y-1/2 place-items-center" style={{ color: earned ? c.ink : "#9aa3b2" }}>
        {earned ? <Icon className="h-6 w-6" /> : <Lock className="h-5 w-5" />}
      </span>
      {label && <span className="absolute left-1/2 top-[63%] -translate-x-1/2 rounded-full bg-surface px-1.5 text-[0.6rem] font-bold tabular-nums shadow-sm" style={{ color: earned ? c.ink : "#9aa3b2" }}>{label}</span>}
    </div>
  );
}

function useBadgeText() {
  const { t, n, lang } = useI18n();
  const fmt = new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short", year: "numeric" });
  return {
    title: (b: Badge) => t(`badge.${b.group}` as MessageKey, { n: n(b.threshold) }),
    desc: (b: Badge) => t(`badge.${b.group}.d` as MessageKey, { n: n(b.threshold) }),
    date: (iso: string) => fmt.format(new Date(iso + "T00:00:00")),
    n,
    t,
  };
}

/** The closest unearned badges, for "up next". */
export function nextBadges(badges: Badge[], count = 3) {
  const firstLockedPerGroup = new Map<string, Badge>();
  for (const b of badges) if (!b.earned && !firstLockedPerGroup.has(b.group)) firstLockedPerGroup.set(b.group, b);
  return [...firstLockedPerGroup.values()].sort((a, b) => b.value / b.threshold - a.value / a.threshold).slice(0, count);
}

export function BadgeCard({ b, index = 0 }: { b: Badge; index?: number }) {
  const x = useBadgeText();
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: Math.min(index, 12) * 0.03, ease: EASE }}
      className={cn("group flex flex-col items-center rounded-2xl border p-3 text-center transition-all duration-300",
        b.earned ? "border-line bg-surface hover:-translate-y-1 hover:shadow-[var(--shadow-lift)]" : "border-dashed border-line-2 bg-paper/60")}>
      <motion.div whileHover={b.earned ? { rotate: [0, -8, 8, 0] } : {}} transition={{ duration: 0.5 }}>
        <Medal group={b.group} tier={b.tier} earned={b.earned} progress={b.value / b.threshold} label={b.threshold > 1 ? x.n(b.threshold) : undefined} />
      </motion.div>
      <p className={cn("mt-1 text-sm font-semibold leading-tight", b.earned ? "text-ink" : "text-ink-3")}>{x.title(b)}</p>
      <p className="mt-0.5 text-[0.7rem] leading-snug text-ink-3">{x.desc(b)}</p>
      <p className={cn("mt-1.5 text-[0.68rem] font-medium", b.earned ? "text-sage" : "text-ink-3")}>
        {b.earned ? (b.earned_at ? x.t("badge.earned", { d: x.date(b.earned_at) }) : "✓") : x.t("badge.progress", { a: x.n(b.value), b: x.n(b.threshold) })}
      </p>
    </motion.div>
  );
}

export function BadgeShelf({ journey }: { journey: Journey }) {
  const { t, n, lang } = useI18n();
  const [filter, setFilter] = useState<"all" | "earned">("all");
  const earned = journey.badges.filter((b) => b.earned);
  // Within a group, show earned tiers plus the next locked one — not every far-off tier.
  const visible = useMemo(() => {
    const out: Badge[] = [];
    const seenLocked = new Set<string>();
    for (const b of journey.badges) {
      if (b.earned) out.push(b);
      else if (filter === "all" && !seenLocked.has(b.group)) { out.push(b); seenLocked.add(b.group); }
    }
    return out.sort((a, b) => Number(b.earned) - Number(a.earned));
  }, [journey.badges, filter]);
  const monthFmt = new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", { month: "short", year: "numeric" });

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-3">{t("badge.count", { a: n(earned.length), b: n(journey.badges.length) })}</p>
        <div className="flex rounded-xl border border-line bg-paper-2 p-0.5 text-xs">
          {(["all", "earned"] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)} className={cn("relative rounded-lg px-3 py-1.5 font-medium", filter === f ? "text-ink" : "text-ink-3")}>
              {filter === f && <motion.span layoutId="badge-filter" className="absolute inset-0 rounded-lg bg-surface shadow-[var(--shadow-soft)]" />}
              <span className="relative">{t(f === "all" ? "badge.all" : "badge.earnedTab")}</span>
            </button>
          ))}
        </div>
      </div>
      <motion.div layout className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        <AnimatePresence>{visible.map((b, i) => <BadgeCard key={b.id} b={b} index={i} />)}</AnimatePresence>
      </motion.div>

      <h3 className="mt-8 font-semibold text-ink">{t("badge.monthly")}</h3>
      <p className="text-xs text-ink-3">{t("badge.monthlySub", { n: n(journey.months[0]?.needed ?? 20) })}</p>
      <div className="no-scrollbar mt-3 flex gap-3 overflow-x-auto pb-1">
        {journey.months.slice(-12).map((m, i) => (
          <div key={m.month} className="flex w-24 shrink-0 flex-col items-center rounded-2xl border border-line bg-surface p-2 text-center">
            <Medal group="month" tier={(new Date(m.month + "-01").getMonth()) % 8} earned={m.earned} progress={m.active_days / m.needed} size={56} />
            <p className={cn("text-xs font-medium", m.earned ? "text-ink" : "text-ink-3")}>{monthFmt.format(new Date(m.month + "-01T00:00:00"))}</p>
            <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-paper-3">
              <motion.div className="h-full rounded-full bg-marigold-400" initial={{ width: 0 }} whileInView={{ width: `${Math.min(100, (m.active_days / m.needed) * 100)}%` }} viewport={{ once: true }} transition={{ delay: i * 0.05 }} />
            </div>
            <p className="mt-0.5 text-[0.62rem] text-ink-3">{n(m.active_days)}/{n(m.needed)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
