"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { motion } from "motion/react";
import { useEffect } from "react";
import { BookOpen, Gauge, Home, LogOut, Plus, Search, Shield, UserRound } from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { Avatar } from "@/components/brand/avatar";
import { LanguageToggle } from "./language-toggle";
import { CommandPalette, useCommandPalette } from "./command-palette";
import { useAuth } from "@/providers/auth";
import { useI18n } from "@/providers/i18n";
import type { MessageKey } from "@/core/i18n";
import { cn } from "@/lib/utils";
import { LEARNER_ONLY, isStaff, tabsFor } from "@/lib/staff";

const NAV: Array<{ href: string; key: MessageKey; icon: React.ReactNode }> = [
  { href: "/dashboard", key: "nav.dashboard", icon: <Home className="h-[18px] w-[18px]" /> },
  { href: "/new", key: "nav.newLesson", icon: <Plus className="h-[18px] w-[18px]" /> },
  { href: "/lessons", key: "nav.lessons", icon: <BookOpen className="h-[18px] w-[18px]" /> },
  { href: "/progress", key: "nav.progress", icon: <Gauge className="h-[18px] w-[18px]" /> },
  { href: "/profile", key: "nav.profile", icon: <UserRound className="h-[18px] w-[18px]" /> },
];

/** Signed-out visitors go to login, which sends them back here afterwards. */
export function useRequireAuth() {
  const { ready, signedIn } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (ready && !signedIn) {
      const here = window.location.pathname + window.location.search;
      router.replace(`/login?next=${encodeURIComponent(here)}`);
    }
  }, [ready, signedIn, router]);
  return ready && signedIn;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const allowed = useRequireAuth();
  const { user, signOut } = useAuth();
  const { t } = useI18n();
  const pathname = usePathname();
  const params = useSearchParams();
  const router = useRouter();
  const palette = useCommandPalette();
  const staff = isStaff(user);
  const tab = params.get("tab") || "overview";
  // Staff get their own portal navigation; learners get the learning app.
  const nav: Array<{ href: string; key: MessageKey; icon: React.ReactNode }> = staff
    ? [...tabsFor(user).map((x) => ({ href: `/admin?tab=${x.v}`, key: x.k, icon: x.icon })), NAV[NAV.length - 1]]
    : NAV;
  const isActive = (href: string) => {
    if (href.startsWith("/admin?")) return pathname === "/admin" && href.endsWith(`tab=${tab}`);
    return pathname === href || pathname.startsWith(`${href}/`);
  };
  const misplaced = staff && LEARNER_ONLY.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  useEffect(() => { if (misplaced) router.replace("/admin"); }, [misplaced, router]);

  if (!allowed || misplaced) {
    return <div className="grid min-h-dvh place-items-center"><div className="skeleton h-10 w-40" /></div>;
  }

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[264px_1fr]">
      {/* desktop sidebar */}
      <aside className="sticky top-0 hidden h-dvh flex-col border-r border-line bg-paper px-4 py-5 lg:flex">
        <Link href={staff ? "/admin" : "/dashboard"} className="px-2"><Logo size={32} /></Link>
        {staff && <span className="mx-2 mt-3 inline-flex w-fit items-center gap-1.5 rounded-full bg-ink px-2.5 py-0.5 text-[0.7rem] font-semibold text-white"><Shield className="h-3 w-3" />{t(user?.role === "admin" ? "staff.admin" : "staff.teacher")}</span>}
        <button
          onClick={() => palette.setOpen(true)}
          className="mt-6 flex items-center gap-2 rounded-2xl border border-line bg-surface px-3 py-2.5 text-sm text-ink-3 shadow-[var(--shadow-soft)] transition-colors hover:text-ink"
        >
          <Search className="h-4 w-4" />
          <span className="flex-1 text-left">{t("nav.command")}</span>
          <kbd className="rounded-md border border-line bg-paper-2 px-1.5 text-[0.68rem]">⌘K</kbd>
        </button>
        <nav className="mt-5 flex flex-col gap-1">
          {nav.map((item) => {
            const active = isActive(item.href);
            return (
              <Link key={item.href} href={item.href} className={cn("relative flex items-center gap-3 rounded-2xl px-3 py-2.5 text-[0.95rem] transition-colors", active ? "text-ink" : "text-ink-2 hover:text-ink")}>
                {active && (
                  <motion.span layoutId="nav-pill" className="absolute inset-0 rounded-2xl border border-line bg-surface shadow-[var(--shadow-soft)]" transition={{ type: "spring", stiffness: 420, damping: 34 }}>
                    <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-sky-600" />
                  </motion.span>
                )}
                <span className={cn("relative", active ? "text-sky-600" : "text-ink-3")}>{item.icon}</span>
                <span className="relative">{t(item.key)}</span>
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto space-y-3">
          <LanguageToggle className="w-fit" />
          <div className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-2.5">
            <Avatar user={user} size={38} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{user?.full_name}</p>
              <p className="truncate text-xs text-ink-3">{user?.email}</p>
            </div>
            <button onClick={() => void signOut()} className="grid h-8 w-8 place-items-center rounded-xl text-ink-3 hover:bg-paper-2 hover:text-rose" aria-label={t("nav.signOut")} title={t("nav.signOut")}>
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* mobile top bar */}
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-line bg-paper/85 px-4 py-3 backdrop-blur lg:hidden">
        <Link href={staff ? "/admin" : "/dashboard"}><Logo size={28} withWord={false} /></Link>
        <div className="flex items-center gap-2">
          <button onClick={() => palette.setOpen(true)} className="grid h-9 w-9 place-items-center rounded-xl border border-line bg-surface" aria-label={t("nav.command")}><Search className="h-4 w-4" /></button>
          <LanguageToggle />
          <Link href="/profile"><Avatar user={user} size={34} /></Link>
        </div>
      </header>

      <main className="min-w-0 pb-28 lg:pb-0">{children}</main>

      {/* mobile tab bar with a raised "new lesson" button */}
      <nav className="fixed inset-x-3 bottom-3 z-40 flex items-center justify-around rounded-3xl border border-line bg-surface/95 px-2 py-2 shadow-[var(--shadow-lift)] backdrop-blur lg:hidden">
        {(staff ? nav.filter((n) => n.href !== "/profile").slice(0, 5) : nav.filter((n) => n.href !== "/profile")).map((item) =>
          item.href === "/new" ? (
            <Link key={item.href} href={item.href} aria-label={t(item.key)} className="-mt-8 grid h-14 w-14 place-items-center rounded-2xl bg-sky-600 text-white shadow-[0_10px_24px_-8px_rgb(59_102_174/0.8)]">
              <Plus className="h-6 w-6" />
            </Link>
          ) : (
            <Link key={item.href} href={item.href} className={cn("relative flex flex-col items-center gap-0.5 rounded-2xl px-3 py-1.5 text-[0.68rem]", isActive(item.href) ? "text-sky-700" : "text-ink-3")}>
              {isActive(item.href) && <motion.span layoutId="tab-pill" className="absolute inset-0 rounded-2xl bg-sky-50" />}
              <span className="relative">{item.icon}</span>
              <span className="relative max-w-16 truncate">{t(item.key)}</span>
            </Link>
          )
        )}
      </nav>

      <CommandPalette open={palette.open} onClose={() => palette.setOpen(false)} />
    </div>
  );
}
