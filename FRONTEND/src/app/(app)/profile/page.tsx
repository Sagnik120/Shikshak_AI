"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { Camera, Check, Flame, KeyRound, LogOut, MonitorSmartphone, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/core/api";
import type { User } from "@/core/types";
import { useAuth } from "@/providers/auth";
import { useI18n } from "@/providers/i18n";
import type { MessageKey } from "@/core/i18n";
import { AVATARS, Avatar, AvatarGlyph } from "@/components/brand/avatar";
import { PlaneMark } from "@/components/brand/logo";
import { BadgeShelf, Medal } from "@/components/lesson/badges";
import { CountUp } from "@/components/motion/reveal";
import { LoadError } from "@/components/ui/load-error";
import { Button, type ButtonStatus } from "@/components/ui/button";
import { Card, Input, PasswordInput } from "@/components/ui/primitives";
import { Field } from "@/components/ui/field";
import { StrengthMeter, scorePassword } from "@/components/auth/auth-kit";
import { relativeDays } from "@/lib/lesson";
import { cn, EASE } from "@/lib/utils";
import { isStaff } from "@/lib/staff";

const SECTIONS: Array<{ id: string; key: MessageKey }> = [
  { id: "photo", key: "profile.photo" }, { id: "badges", key: "badge.title" }, { id: "details", key: "profile.details" },
  { id: "mentor", key: "profile.mentor" }, { id: "journey", key: "profile.journey" }, { id: "security", key: "profile.security" },
  { id: "danger", key: "profile.danger" },
];

export default function ProfilePage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const [active, setActive] = useState("photo");
  const staff = isStaff(user);
  // Staff profiles skip the learner-only parts (preferences, mentor, journey).
  const sections = SECTIONS.filter((x) => !staff || !["badges", "mentor", "journey"].includes(x.id));

  useEffect(() => {
    const io = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && setActive(e.target.id)), { rootMargin: "-30% 0px -60% 0px" });
    SECTIONS.forEach((s) => { const el = document.getElementById(s.id); if (el) io.observe(el); });
    return () => io.disconnect();
  }, []);

  if (!user) return null;
  return (
    <div className="mx-auto max-w-6xl px-5 py-8 lg:px-10 lg:py-10">
      <h1 className="font-display text-5xl text-ink sm:text-6xl">{t("profile.title")}</h1>
      <div className="mt-8 grid gap-10 lg:grid-cols-[200px_1fr]">
        {/* scroll-island table of contents */}
        <nav className="sticky top-6 hidden self-start lg:block" aria-label={t("profile.title")}>
          <ul className="space-y-1 border-l border-line">
            {sections.map((s) => (
              <li key={s.id} className="relative">
                {active === s.id && <motion.span layoutId="profile-toc" className="absolute -left-px top-0 h-full w-[2px] bg-sky-600" />}
                <a href={`#${s.id}`} className={cn("block py-1.5 pl-4 text-sm transition-colors", active === s.id ? "font-medium text-ink" : "text-ink-3 hover:text-ink-2")}>{t(s.key)}</a>
              </li>
            ))}
          </ul>
        </nav>
        <div className="min-w-0 space-y-6">
          <PhotoSection user={user} />
          {!staff && <BadgesSection />}
          <DetailsSection user={user} />
          {!staff && <MentorSection user={user} />}
          {!staff && <JourneySection />}
          <SecuritySection />
          <DangerSection />
        </div>
      </div>
    </div>
  );
}

function Section({ id, title, children, className }: { id: string; title: string; children: React.ReactNode; className?: string }) {
  return (
    <motion.section id={id} initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-40px" }} transition={{ duration: 0.5, ease: EASE }} className="scroll-mt-24">
      <Card className={cn("p-6", className)}>
        <h2 className="font-display text-2xl text-ink">{title}</h2>
        <div className="mt-5">{children}</div>
      </Card>
    </motion.section>
  );
}

function useSave() {
  const { setUser } = useAuth();
  const { t } = useI18n();
  const [status, setStatus] = useState<ButtonStatus>("idle");
  const save = async (patch: Record<string, unknown>, msg?: string) => {
    setStatus("loading");
    try {
      setUser(await api.updateProfile(patch));
      setStatus("success");
      toast.success(msg ?? t("common.saved"));
      setTimeout(() => setStatus("idle"), 1400);
    } catch (e) { setStatus("idle"); toast.error((e as Error).message); }
  };
  return { status, save };
}

function PhotoSection({ user }: { user: User }) {
  const { t, n, lang } = useI18n();
  const { setUser } = useAuth();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [over, setOver] = useState(false);
  const staff = isStaff(user);
  const journey = useQuery({ queryKey: ["journey"], queryFn: api.journey, enabled: !staff });
  const j = journey.data;
  const latest = (j?.badges ?? []).filter((b) => b.earned).sort((a, b) => (b.earned_at ?? "").localeCompare(a.earned_at ?? "")).slice(0, 5);

  const upload = async (file?: File) => {
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) return toast.error(t("profile.photoTooBig"));
    setBusy(true);
    try { setUser(await api.uploadAvatar(file)); toast.success(t("profile.photoSaved")); }
    catch (e) { toast.error((e as Error).message); } finally { setBusy(false); }
  };
  const choose = async (id: string) => {
    try { setUser(await api.updateProfile({ avatar_choice: id })); toast.success(t("profile.avatarSaved")); } catch (e) { toast.error((e as Error).message); }
  };
  const remove = async () => {
    try { setUser(await api.removeAvatar()); } catch (e) { toast.error((e as Error).message); }
  };
  const since = new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", { month: "long", year: "numeric" }).format(new Date(user.created_at));

  return (
    <section id="photo" className="scroll-mt-24">
      <div className="overflow-hidden rounded-[var(--radius)] border border-line bg-surface shadow-[var(--shadow-soft)]">
        {/* cover: a notebook page with a plane on its flight path */}
        <div className="ruled relative h-40 overflow-hidden bg-gradient-to-br from-sky-50 via-paper to-marigold-50 sm:h-44">
          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 800 180" preserveAspectRatio="none" aria-hidden>
            <motion.path d="M-10 150 C 160 40, 300 170, 460 80 S 700 20, 820 50" fill="none" stroke="var(--sky-300)" strokeWidth="2" strokeDasharray="5 9"
              initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.6, ease: EASE }} />
          </svg>
          <motion.div className="absolute right-[12%] top-5" animate={{ y: [0, -8, 0], rotate: [-4, 4, -4] }} transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}>
            <PlaneMark size={64} />
          </motion.div>
          {j && (
            <div className="absolute left-5 top-4 flex flex-wrap gap-2 sm:left-auto sm:right-5 sm:top-auto sm:bottom-4">
              <span className="rounded-full bg-surface/90 px-3 py-1 text-xs font-semibold text-sky-700 shadow-sm backdrop-blur">{t("lvl.level", { n: n(j.level.level) })} · {t(`lvl.${j.level.title}` as MessageKey)}</span>
              <span className="inline-flex items-center gap-1 rounded-full bg-surface/90 px-3 py-1 text-xs font-semibold text-marigold-600 shadow-sm backdrop-blur"><Flame className="h-3.5 w-3.5" fill="currentColor" />{t(j.streak.current === 1 ? "cal.day1" : "cal.days", { n: n(j.streak.current) })}</span>
            </div>
          )}
        </div>

        <div className="relative px-6 pb-6">
          <div className="-mt-14 flex flex-wrap items-end gap-5">
            <button type="button" onClick={() => input.current?.click()} disabled={busy} aria-label={t("profile.upload")}
              onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={(e) => { e.preventDefault(); setOver(false); void upload(e.dataTransfer.files[0]); }}
              className={cn("group relative rounded-full ring-4 ring-surface transition-transform", over && "-translate-y-1")}>
              <motion.div key={(user.avatar_url ?? "") + (user.avatar_choice ?? "")} initial={{ opacity: 0, rotate: -10 }} animate={{ opacity: 1, rotate: 0 }} transition={{ type: "spring", stiffness: 220, damping: 18 }}>
                <Avatar user={user} size={116} />
              </motion.div>
              <span className="absolute inset-0 grid place-items-center rounded-full bg-ink/45 text-white opacity-0 transition-opacity group-hover:opacity-100">
                {busy ? <span className="h-6 w-6 animate-spin rounded-full border-2 border-white border-t-transparent" /> : <Camera className="h-6 w-6" />}
              </span>
            </button>
            <div className="min-w-0 flex-1 pb-1">
              <p className="font-display text-4xl leading-tight text-ink">{user.full_name}</p>
              <p className="text-sm text-ink-2">{user.email}</p>
              <p className="font-hand text-lg text-sky-700">{t(staff ? "staff.joined" : "profile.memberSince", { d: since })}</p>
            </div>
            {latest.length > 0 && (
              <a href="#badges" className="flex -space-x-3 pb-1" aria-label={t("badge.title")}>
                {latest.map((b, i) => (
                  <motion.span key={b.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 + i * 0.08 }} title={b.id}>
                    <Medal group={b.group} tier={b.tier} earned size={46} />
                  </motion.span>
                ))}
              </a>
            )}
          </div>

          {j && (
            <div className="mt-5 grid grid-cols-3 divide-x divide-line rounded-2xl border border-line bg-paper text-center">
              {[[j.totals.lessons_completed, t("prog.k.lessons")], [j.totals.minutes, t("prog.k.time")], [j.totals.concepts_mastered, t("prog.k.mastered")]].map(([v, l]) => (
                <div key={l as string} className="px-2 py-3"><p className="font-display text-3xl text-ink"><CountUp to={v as number} format={(x) => n(x)} /></p><p className="text-[0.7rem] text-ink-3">{l}</p></div>
              ))}
            </div>
          )}

          <div className="mt-5 flex flex-wrap items-center gap-2">
            <Button size="sm" variant="soft" onClick={() => input.current?.click()} icon={<Upload className="h-4 w-4" />} status={busy ? "loading" : "idle"}>{t("profile.upload")}</Button>
            {user.avatar_url && <Button size="sm" variant="ghost" onClick={remove} icon={<Trash2 className="h-4 w-4" />}>{t("profile.remove")}</Button>}
            <span className="text-xs text-ink-3">{t("profile.photoHint")}</span>
            <input ref={input} type="file" hidden accept="image/png,image/jpeg,image/webp" onChange={(e) => { void upload(e.target.files?.[0]); e.target.value = ""; }} />
          </div>
          <p className="mt-5 text-sm font-medium text-ink">{t("profile.chooseAvatar")}</p>
          <div className="mt-3 grid grid-cols-6 gap-3 sm:grid-cols-12" role="radiogroup">
            {AVATARS.map((a, i) => {
              const sel = !user.avatar_url && user.avatar_choice === a.id;
              return (
                <motion.button key={a.id} type="button" role="radio" aria-checked={sel} aria-label={a.id} onClick={() => choose(a.id)}
                  initial={{ opacity: 0, y: 8 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.03 }}
                  whileHover={{ y: -4, rotate: -6 }} whileTap={{ y: 0 }} className="relative justify-self-center">
                  <AvatarGlyph choice={a} size={48} selected={sel} />
                  {sel && <span className="absolute -right-1 -top-1 grid h-5 w-5 place-items-center rounded-full bg-sky-600 text-white"><Check className="h-3 w-3" /></span>}
                </motion.button>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

function BadgesSection() {
  const { t } = useI18n();
  const j = useQuery({ queryKey: ["journey"], queryFn: api.journey });
  return (
    <Section id="badges" title={t("badge.title")}>
      <p className="-mt-3 mb-4 text-sm text-ink-3">{t("badge.sub")}</p>
      {j.data ? <BadgeShelf journey={j.data} /> : j.isError ? <LoadError onRetry={() => j.refetch()} /> : <div className="skeleton h-48 rounded-2xl" />}
    </Section>
  );
}

function DetailsSection({ user }: { user: User }) {
  const { t } = useI18n();
  const { status, save } = useSave();
  const [f, setF] = useState({ full_name: user.full_name, grade: user.grade ?? "", board: user.board ?? "" });
  if (isStaff(user)) {
    // Staff: just who they are — no class or board.
    return (
      <Section id="details" title={t("profile.details")}>
        <form className="grid gap-4 sm:grid-cols-[1fr_auto]" onSubmit={(e) => { e.preventDefault(); void save({ full_name: f.full_name.trim() }); }}>
          <Field id="fn" label={t("auth.fullName")} index={1}><Input id="fn" value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></Field>
          <div className="flex items-end"><Button type="submit" status={status} disabled={f.full_name.trim().length < 2}>{t("common.save")}</Button></div>
          <div className="flex flex-wrap gap-6 text-sm sm:col-span-2">
            <p><span className="text-ink-3">{t("auth.email")}: </span>{user.email}</p>
            <p><span className="text-ink-3">{t("staff.role")}: </span>{t(user.role === "admin" ? "staff.admin" : "staff.teacher")}</p>
          </div>
        </form>
      </Section>
    );
  }
  return (
    <Section id="details" title={t("profile.details")}>
      <form className="grid gap-4 sm:grid-cols-3" onSubmit={(e) => { e.preventDefault(); void save({ full_name: f.full_name.trim(), grade: f.grade.trim() || null, board: f.board.trim() || null }); }}>
        <Field id="fn" label={t("auth.fullName")} className="sm:col-span-3" index={1}><Input id="fn" value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></Field>
        <Field id="gr" label={t("auth.grade")} index={2}><Input id="gr" value={f.grade} onChange={(e) => setF({ ...f, grade: e.target.value })} /></Field>
        <Field id="bd" label={t("profile.board")} index={3}><Input id="bd" value={f.board} onChange={(e) => setF({ ...f, board: e.target.value })} /></Field>
        <div className="flex items-end justify-end"><Button type="submit" status={status} disabled={f.full_name.trim().length < 2}>{t("common.save")}</Button></div>
      </form>
    </Section>
  );
}

function MentorSection({ user }: { user: User }) {
  const { t } = useI18n();
  const { status, save } = useSave();
  const [name, setName] = useState(user.mentor_name ?? "");
  const [email, setEmail] = useState(user.mentor_email ?? "");
  return (
    <Section id="mentor" title={t("profile.mentor")}>
      <p className="-mt-2 mb-4 text-sm text-ink-3">{t("auth.mentorHint")}</p>
      <form className="grid gap-4 sm:grid-cols-[1fr_1fr_auto]" onSubmit={(e) => { e.preventDefault(); void save({ mentor_name: name.trim() || null, mentor_email: email.trim() || null }); }}>
        <Field id="mn" label={t("auth.mentorName")} index={4}><Input id="mn" value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Field id="me" label={t("auth.mentorEmail")} index={5}><Input id="me" type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <div className="flex items-end"><Button type="submit" status={status}>{t("common.save")}</Button></div>
      </form>
    </Section>
  );
}

/** Finished lessons as milestones (Work-Experience timeline, adapted). */
function JourneySection() {
  const { t, n, lang } = useI18n();
  const q = useQuery({ queryKey: ["lessons", "completed"], queryFn: () => api.listLessons({ status: "completed", limit: 20 }) });
  const items = q.data?.lessons ?? [];
  return (
    <Section id="journey" title={t("profile.journey")}>
      {items.length === 0 ? <p className="text-sm text-ink-3">{t("profile.journeyEmpty")}</p> : (
        <ol className="relative ml-3 border-l-2 border-dashed border-line-2">
          {items.map((l, i) => (
            <motion.li key={l.id} initial={{ opacity: 0, x: -10 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.05 }} className="relative pb-6 pl-6 last:pb-0">
              <span className="absolute -left-[9px] top-1 h-4 w-4 rounded-full border-2 border-surface bg-sky-600 ring-4 ring-sky-50" />
              <p className="text-xs text-ink-3">{l.completed_at ? relativeDays(l.completed_at, lang) : ""}</p>
              <a href={`/report/${l.id}`} className="font-medium text-ink hover:text-sky-700">{l.title}</a>
              <p className="text-sm text-ink-3">{t("common.concepts", { n: n(l.node_count) })}{l.score_pct != null ? ` · ${t("profile.scored", { n: n(Math.round(l.score_pct)) })}` : ""}</p>
            </motion.li>
          ))}
        </ol>
      )}
    </Section>
  );
}

function SecuritySection() {
  const { t, lang } = useI18n();
  const qc = useQueryClient();
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [status, setStatus] = useState<ButtonStatus>("idle");
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: api.listSessions });
  type S = { id: string; user_agent?: string; ip_address?: string; last_used_at?: string; created_at: string; current?: boolean };
  const list = (sessions.data ?? []) as unknown as S[];

  const change = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    try { await api.changePassword(cur, next); toast.success(t("profile.passwordChanged")); setCur(""); setNext(""); setStatus("success"); setTimeout(() => setStatus("idle"), 1200); }
    catch (err) { setStatus("idle"); toast.error((err as Error).message); }
  };
  const device = (ua?: string) => {
    if (!ua) return t("profile.unknownDevice");
    const b = /Edg\//.test(ua) ? "Edge" : /Chrome\//.test(ua) ? "Chrome" : /Firefox\//.test(ua) ? "Firefox" : /Safari\//.test(ua) ? "Safari" : "Browser";
    const o = /Android/.test(ua) ? "Android" : /iPhone|iPad/.test(ua) ? "iOS" : /Mac OS/.test(ua) ? "macOS" : /Windows/.test(ua) ? "Windows" : /Linux/.test(ua) ? "Linux" : "";
    return `${b}${o ? ` · ${o}` : ""}`;
  };

  return (
    <Section id="security" title={t("profile.security")}>
      <form onSubmit={change} className="grid gap-4 md:grid-cols-2">
        <Field id="cp" label={t("profile.currentPassword")} index={6}><PasswordInput id="cp" autoComplete="current-password" value={cur} onChange={(e) => setCur(e.target.value)} showLabel={t("auth.showPassword")} hideLabel={t("auth.hidePassword")} /></Field>
        <Field id="np" label={t("auth.newPassword")} index={7}><PasswordInput id="np" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} showLabel={t("auth.showPassword")} hideLabel={t("auth.hidePassword")} /></Field><StrengthMeter password={next} />
        <div className="md:col-span-2 flex justify-end"><Button type="submit" status={status} icon={<KeyRound className="h-4 w-4" />} disabled={!cur || scorePassword(next) === 0}>{t("profile.changePassword")}</Button></div>
      </form>
      <div className="mt-8 flex items-center justify-between">
        <h3 className="font-semibold">{t("profile.sessions")}</h3>
        <Button size="sm" variant="ghost" icon={<LogOut className="h-4 w-4" />} onClick={async () => { try { await api.revokeAllSessions(); toast.success(t("profile.signedOutOthers")); qc.invalidateQueries({ queryKey: ["sessions"] }); } catch (e) { toast.error((e as Error).message); } }}>{t("profile.signOutAll")}</Button>
      </div>
      <ul className="mt-3 divide-y divide-line rounded-2xl border border-line">
        {list.map((s) => (
          <li key={s.id} className="flex items-center gap-3 px-4 py-3">
            <MonitorSmartphone className="h-5 w-5 text-ink-3" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{device(s.user_agent)} {s.current && <span className="ml-1 rounded-full bg-sage-100 px-2 py-0.5 text-xs text-sage">{t("profile.thisDevice")}</span>}</p>
              <p className="text-xs text-ink-3">{t("profile.lastUsed", { t: relativeDays(s.last_used_at || s.created_at, lang) })}{s.ip_address ? ` · ${s.ip_address}` : ""}</p>
            </div>
            {!s.current && <Button size="sm" variant="ghost" onClick={async () => { await api.revokeSession(s.id).catch((e) => toast.error(e.message)); qc.invalidateQueries({ queryKey: ["sessions"] }); }}>{t("profile.revoke")}</Button>}
          </li>
        ))}
      </ul>
    </Section>
  );
}

function DangerSection() {
  const { t } = useI18n();
  const { signOut } = useAuth();
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <Section id="danger" title={t("profile.danger")} className="border-rose/30">
      <p className="-mt-2 text-sm text-ink-2">{t("profile.dangerBody")}</p>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <Field id="dp" label={t("profile.typePassword")} className="min-w-56 flex-1" index={8}><PasswordInput id="dp" value={pw} onChange={(e) => setPw(e.target.value)} showLabel={t("auth.showPassword")} hideLabel={t("auth.hidePassword")} /></Field>
        <Button variant="danger" disabled={!pw || busy} status={busy ? "loading" : "idle"} icon={<Trash2 className="h-4 w-4" />}
          onClick={async () => { setBusy(true); try { await api.deleteAccount(pw); await signOut(); } catch (e) { toast.error((e as Error).message); setBusy(false); } }}>
          {t("profile.danger")}
        </Button>
      </div>
    </Section>
  );
}
