"use client";

/** Small shared pieces for the auth pages. */
import { motion } from "motion/react";
import { useEffect as useEffectSafe, useState as useStateSafe } from "react";
import { ApiError } from "@/core/api";
import { useI18n } from "@/providers/i18n";
import { EASE, cn } from "@/lib/utils";

const PENDING = "shk_pending_otp";
export type PendingOtp = { email: string; code?: string; purpose: "verify_email" | "reset_password"; staff?: boolean };

/** The demo code travels in sessionStorage, never in the URL. */
export const pendingOtp = {
  save(p: PendingOtp) { try { sessionStorage.setItem(PENDING, JSON.stringify(p)); } catch {} },
  load(): PendingOtp | null { try { return JSON.parse(sessionStorage.getItem(PENDING) || "null"); } catch { return null; } },
  clear() { try { sessionStorage.removeItem(PENDING); } catch {} },
};

export const errText = (e: unknown, fallback: string) => (e instanceof ApiError || e instanceof Error ? e.message : fallback);

export function AuthHeading({ title, sub }: { title: string; sub?: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: EASE }} className="mb-8">
      <h1 className="font-display text-[2.6rem] leading-[1.05] text-ink">{title}</h1>
      {sub && <p className="mt-2 text-ink-2">{sub}</p>}
    </motion.div>
  );
}

export function FormAlert({ children }: { children?: React.ReactNode }) {
  if (!children) return null;
  return (
    <motion.p role="alert" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} className="rounded-2xl border border-rose/30 bg-rose/5 px-4 py-3 text-sm text-rose">
      {children}
    </motion.p>
  );
}

export function scorePassword(pw: string) {
  if (pw.length < 8) return 0;
  let s = 0;
  if (/[a-z]/i.test(pw) && /\d/.test(pw)) s++;
  if (/[^a-z0-9]/i.test(pw) || /[A-Z]/.test(pw)) s++;
  if (pw.length >= 12) s++;
  return Math.max(1, s);
}

export function passwordOk(pw: string) {
  return scorePassword(pw) > 0 && /\d/.test(pw) && /[a-z]/i.test(pw);
}

export function StrengthMeter({ password }: { password: string }) {
  const { t } = useI18n();
  const s = scorePassword(password);
  const colors = ["bg-rose", "bg-amber", "bg-sky-500", "bg-sage"];
  return (
    <div className="mt-2" aria-live="polite">
      <div className="flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <span key={i} className="h-1.5 flex-1 overflow-hidden rounded-full bg-line">
            <motion.span className={cn("block h-full rounded-full", colors[s])} initial={false} animate={{ width: password && i < Math.max(s, password ? 1 : 0) ? "100%" : "0%" }} transition={{ duration: 0.35, ease: EASE }} />
          </span>
        ))}
      </div>
      <p className="mt-1.5 text-xs text-ink-3">{password ? t(`auth.strength${s}` as "auth.strength0") : t("auth.passwordRule")}</p>
    </div>
  );
}

/** On-screen demo code (no email is sent) with a one-tap fill. */
export function DemoCode({ code, onFill }: { code?: string; onFill: () => void }) {
  const { t } = useI18n();
  if (!code) return null;
  return (
    <motion.div initial={{ opacity: 0, rotate: -1.5, y: 8 }} animate={{ opacity: 1, rotate: -1, y: 0 }} transition={{ duration: 0.5, ease: EASE }}
      className="relative mb-6 rounded-2xl border border-amber/40 bg-amber-100/70 px-5 py-4 shadow-[var(--shadow-soft)]">
      <span className="absolute -top-2.5 left-6 h-5 w-16 rotate-[-4deg] rounded-sm bg-marigold/40" aria-hidden />
      <p className="text-sm text-ink-2">{t("auth.demoCode")}</p>
      <div className="mt-1 flex items-center justify-between gap-3">
        <span className="font-display text-3xl tracking-[0.3em] text-ink" data-testid="demo-code">{code}</span>
        <button type="button" onClick={onFill} className="rounded-xl bg-surface px-3 py-1.5 text-sm font-medium text-sky-700 shadow-[var(--shadow-soft)] hover:bg-sky-50">{t("auth.fillForMe")}</button>
      </div>
    </motion.div>
  );
}

/** Resend with a 30s cooldown. */
export function useCooldown(seconds = 30) {
  const [left, setLeft] = useStateSafe(seconds);
  useEffectSafe(() => {
    if (left <= 0) return;
    const id = setTimeout(() => setLeft(left - 1), 1000);
    return () => clearTimeout(id);
  }, [left]);
  return { left, restart: () => setLeft(seconds) };
}
