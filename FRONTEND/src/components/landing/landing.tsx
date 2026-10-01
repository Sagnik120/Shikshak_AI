"use client";

import Lenis from "lenis";
import Link from "next/link";
import { useEffect } from "react";
import { Logo } from "@/components/brand/logo";
import { useAuth } from "@/providers/auth";
import { useI18n } from "@/providers/i18n";
import { IslandNav } from "./island-nav";
import { Hero } from "./hero";
import { Final, Grounded, Hood, Ladder, Langs, Loop, Numbers, Problem, VisitorCheck } from "./story";

/** Smooth, weighted scrolling for the landing story only (the app stays native). */
function useLenis() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const lenis = new Lenis({ lerp: 0.1, smoothWheel: true });
    let id = 0;
    const raf = (time: number) => { lenis.raf(time); id = requestAnimationFrame(raf); };
    id = requestAnimationFrame(raf);
    return () => { cancelAnimationFrame(id); lenis.destroy(); };
  }, []);
}

export function Landing() {
  const { t } = useI18n();
  const { signedIn } = useAuth();
  useLenis();
  return (
    <div className="bg-paper">
      <IslandNav />
      <main>
        <Hero />
        <Problem />
        <Loop />
        <VisitorCheck />
        <Ladder />
        <Grounded />
        <Langs />
        <Numbers />
        <Hood />
        <Final signedIn={signedIn} />
      </main>
      <footer className="border-t border-line bg-paper">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-8 text-sm text-ink-3">
          <Logo size={28} />
          <p className="font-hand text-lg text-ink-2">{t("landing.footer")}</p>
          <p className="flex items-center gap-4"><Link href="/staff/login" className="hover:text-ink">{t("staff.link")}</Link><span>© {new Date().getFullYear()} Shikshak</span></p>
        </div>
      </footer>
    </div>
  );
}
