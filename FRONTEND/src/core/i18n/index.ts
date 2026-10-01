/**
 * i18n core (framework-free). `en` defines every key; `hi` must define the
 * same keys — TypeScript fails the build if one is missing, so a Hindi page
 * never silently falls back to English.
 */
import { en } from "./en";
import { hi } from "./hi";

export type Lang = "en" | "hi";
export type MessageKey = keyof typeof en;
export type Messages = Record<MessageKey, string>;

export const MESSAGES: Record<Lang, Messages> = { en, hi };
export const LANGS: Array<{ code: Lang; label: string; short: string }> = [
  { code: "en", label: "English", short: "EN" },
  { code: "hi", label: "हिन्दी", short: "हिं" },
];

/** "Hello {name}" + { name: "Asha" } -> "Hello Asha". */
export function translate(lang: Lang, key: MessageKey, vars?: Record<string, string | number>): string {
  let text = MESSAGES[lang][key] ?? MESSAGES.en[key] ?? key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) text = text.replaceAll(`{${k}}`, String(v));
  }
  return text;
}

/** Numbers in the reader's script (१२३ in Hindi) — never digits glued to letters. */
const DEVANAGARI = "०१२३४५६७८९";
export function localizeDigits(lang: Lang, value: string | number): string {
  const text = String(value);
  if (lang !== "hi") return text;
  return text.replace(/(?<![A-Za-z])\d+(?![A-Za-z])/g, (run) =>
    run.replace(/\d/g, (d) => DEVANAGARI[Number(d)])
  );
}
