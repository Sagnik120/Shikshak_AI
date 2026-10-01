"use client";

/** EN / हिं pill with a sliding paper background — every string switches, nothing reflows away. */
import { motion } from "motion/react";
import { LANGS } from "@/core/i18n";
import { useI18n } from "@/providers/i18n";
import { cn } from "@/lib/utils";

export function LanguageToggle({ className }: { className?: string }) {
  const { lang, setLang, t } = useI18n();
  return (
    <div role="radiogroup" aria-label={t("common.language")} className={cn("relative flex rounded-full border border-line bg-paper-2 p-0.5", className)}>
      {LANGS.map((l) => {
        const active = l.code === lang;
        return (
          <button
            key={l.code}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => setLang(l.code)}
            className={cn("relative z-10 min-w-11 rounded-full px-3 py-1 text-xs font-semibold transition-colors", active ? "text-ink" : "text-ink-3 hover:text-ink-2")}
          >
            {active && (
              <motion.span layoutId="lang-pill" className="absolute inset-0 -z-10 rounded-full bg-surface shadow-[var(--shadow-soft)]" transition={{ type: "spring", stiffness: 500, damping: 34 }} />
            )}
            {l.short}
          </button>
        );
      })}
    </div>
  );
}
