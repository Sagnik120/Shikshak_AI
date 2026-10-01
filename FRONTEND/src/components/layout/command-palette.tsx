"use client";

/**
 * ⌘K / Ctrl+K: jump to any page or any of your lessons, switch language,
 * start a lesson. Adapted from the Command Box idea: one input, grouped
 * results, full keyboard navigation.
 */
import { AnimatePresence, motion } from "motion/react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BookOpen, Command, Gauge, Home, Languages, LogOut, Plus, Search, Shield, UserRound } from "lucide-react";
import { api } from "@/core/api";
import { useI18n } from "@/providers/i18n";
import { useAuth } from "@/providers/auth";
import { cn, EASE } from "@/lib/utils";
import { tabsFor } from "@/lib/staff";

type Item = { id: string; group: string; label: string; hint?: string; icon: React.ReactNode; run: () => void };

export function useCommandPalette() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return { open, setOpen };
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t, lang, setLang } = useI18n();
  const { signOut, user } = useAuth();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const lessons = useQuery({ queryKey: ["lessons", "palette"], queryFn: () => api.listLessons({ limit: 50 }), enabled: open });

  const go = useCallback((href: string) => {
    onClose();
    router.push(href);
  }, [onClose, router]);

  const items = useMemo<Item[]>(() => {
    const staff = user?.role === "admin" || user?.role === "teacher";
    const staffPages: Item[] = tabsFor(user).map((x) => ({ id: `t-${x.v}`, group: t("cmd.pages"), label: t(x.k), icon: <Shield className="h-4 w-4" />, run: () => go(`/admin?tab=${x.v}`) }));
    const learnerPages: Item[] = [
      { id: "home", group: t("cmd.pages"), label: t("nav.dashboard"), icon: <Home className="h-4 w-4" />, run: () => go("/dashboard") },
      { id: "new", group: t("cmd.pages"), label: t("nav.newLesson"), icon: <Plus className="h-4 w-4" />, run: () => go("/new") },
      { id: "lessons", group: t("cmd.pages"), label: t("nav.lessons"), icon: <BookOpen className="h-4 w-4" />, run: () => go("/lessons") },
      { id: "progress", group: t("cmd.pages"), label: t("nav.progress"), icon: <Gauge className="h-4 w-4" />, run: () => go("/progress") },
      { id: "profile", group: t("cmd.pages"), label: t("nav.profile"), icon: <UserRound className="h-4 w-4" />, run: () => go("/profile") },
    ];
    const pages = staff ? [...staffPages, learnerPages[learnerPages.length - 1]] : learnerPages;
    const lessonItems: Item[] = staff ? [] : (lessons.data?.lessons ?? []).map((l) => ({
      id: `l-${l.id}`,
      group: t("cmd.lessons"),
      label: l.title,
      hint: t(`status.${l.status}` as "status.completed"),
      icon: <BookOpen className="h-4 w-4" />,
      run: () => go(l.status === "completed" ? `/report/${l.id}` : `/learn/${l.id}`),
    }));
    const actions: Item[] = [
      { id: "lang", group: t("cmd.actions"), label: t("cmd.switchLang"), icon: <Languages className="h-4 w-4" />, run: () => { setLang(lang === "en" ? "hi" : "en"); onClose(); } },
      { id: "out", group: t("cmd.actions"), label: t("nav.signOut"), icon: <LogOut className="h-4 w-4" />, run: () => { onClose(); void signOut(); } },
    ];
    const all = [...pages, ...lessonItems, ...actions];
    const needle = q.trim().toLowerCase();
    return needle ? all.filter((i) => i.label.toLowerCase().includes(needle)) : all;
  }, [t, user, lessons.data, go, q, lang, setLang, onClose, signOut]);

  useEffect(() => {
    if (open) {
      setQ("");
      setActive(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);
  useEffect(() => setActive(0), [q]);

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(items.length - 1, a + 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
    if (e.key === "Enter") { e.preventDefault(); items[active]?.run(); }
    if (e.key === "Escape") onClose();
  };

  const groups = [...new Set(items.map((i) => i.group))];

  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-[90] flex items-start justify-center px-4 pt-[14vh]" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <div className="absolute inset-0 bg-ink/20 backdrop-blur-[3px]" onClick={onClose} />
          <motion.div
            role="dialog"
            aria-modal="true"
            className="relative w-full max-w-xl overflow-hidden rounded-3xl border border-line bg-surface shadow-[var(--shadow-lift)]"
            initial={{ y: 16, scale: 0.97, opacity: 0 }}
            animate={{ y: 0, scale: 1, opacity: 1 }}
            exit={{ y: 10, scale: 0.98, opacity: 0 }}
            transition={{ duration: 0.25, ease: EASE }}
            onKeyDown={onKey}
          >
            <div className="flex items-center gap-3 border-b border-line px-5">
              <Search className="h-4 w-4 text-ink-3" />
              <input
                ref={inputRef}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={t("cmd.placeholder")}
                className="h-14 flex-1 bg-transparent text-[0.98rem] outline-none placeholder:text-ink-3"
                aria-label={t("cmd.placeholder")}
              />
              <kbd className="rounded-md border border-line bg-paper-2 px-1.5 py-0.5 text-[0.7rem] text-ink-3">esc</kbd>
            </div>
            <div className="max-h-[50vh] overflow-y-auto p-2 no-scrollbar">
              {items.length === 0 && <p className="px-4 py-10 text-center text-sm text-ink-3">{t("cmd.empty", { q })}</p>}
              {groups.map((g) => (
                <div key={g} className="mb-1">
                  <p className="px-3 pb-1 pt-2 text-[0.7rem] font-semibold tracking-wider text-ink-3 uppercase">{g}</p>
                  {items.filter((i) => i.group === g).map((item) => {
                    const index = items.indexOf(item);
                    return (
                      <button
                        key={item.id}
                        onMouseMove={() => setActive(index)}
                        onClick={item.run}
                        className={cn("relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm", index === active ? "text-ink" : "text-ink-2")}
                      >
                        {index === active && <motion.span layoutId="cmd-active" className="absolute inset-0 -z-0 rounded-xl bg-sky-50" transition={{ type: "spring", stiffness: 500, damping: 38 }} />}
                        <span className="relative text-ink-3">{item.icon}</span>
                        <span className="relative flex-1 truncate">{item.label}</span>
                        {item.hint && <span className="relative text-xs text-ink-3">{item.hint}</span>}
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
            <div className="flex items-center justify-between border-t border-line bg-paper px-4 py-2.5 text-[0.72rem] text-ink-3">
              <span className="inline-flex items-center gap-1.5"><Command className="h-3 w-3" /> K</span>
              <span>↑↓ {t("cmd.navigate")} · ↵ {t("cmd.select")}</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
