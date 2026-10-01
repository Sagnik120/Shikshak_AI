"use client";

import { forwardRef, useId, useState, type ReactNode } from "react";
import { Eye, EyeOff } from "lucide-react";
import { motion } from "motion/react";
import { cn, EASE } from "@/lib/utils";

/* -- Card ---------------------------------------------------------------- */

export function Card({ className, children, lift = false, ...rest }: React.HTMLAttributes<HTMLDivElement> & { lift?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius)] border border-line bg-surface shadow-[var(--shadow-soft)]",
        lift && "transition-[transform,box-shadow] duration-300 ease-[var(--ease-out-soft)] hover:-translate-y-1 hover:shadow-[var(--shadow-lift)]",
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

/* -- Badge --------------------------------------------------------------- */

const TONES = {
  neutral: "bg-paper-2 text-ink-2 border-line",
  sky: "bg-sky-50 text-sky-700 border-sky-100",
  marigold: "bg-marigold-50 text-marigold-600 border-marigold-100",
  sage: "bg-sage-100 text-sage border-sage-100",
  amber: "bg-amber-100 text-amber border-amber-100",
  rose: "bg-rose-100 text-rose border-rose-100",
} as const;
export type Tone = keyof typeof TONES;

export function Badge({ tone = "neutral", className, children, dot = false }: { tone?: Tone; className?: string; children: ReactNode; dot?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium", TONES[tone], className)}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

/* -- Fields -------------------------------------------------------------- */

export function Label({ children, htmlFor, hint }: { children: ReactNode; htmlFor?: string; hint?: ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 flex items-baseline justify-between gap-2 text-sm font-medium text-ink">
      <span>{children}</span>
      {hint && <span className="text-xs font-normal text-ink-3">{hint}</span>}
    </label>
  );
}

const fieldBase =
  "w-full rounded-2xl border border-line-2 bg-surface px-4 text-[0.95rem] text-ink placeholder:text-ink-3 outline-none transition-[border-color,box-shadow] duration-200 focus:border-sky-500 focus:shadow-[0_0_0_4px_var(--sky-50)] aria-[invalid=true]:border-rose aria-[invalid=true]:shadow-[0_0_0_4px_var(--rose-100)]";

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(function Input({ className, ...rest }, ref) {
  return <input ref={ref} className={cn(fieldBase, "h-12", className)} {...rest} />;
});

export const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea({ className, ...rest }, ref) {
  return <textarea ref={ref} className={cn(fieldBase, "min-h-28 py-3 leading-relaxed", className)} {...rest} />;
});

export function Select({ className, children, ...rest }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cn(fieldBase, "h-12 appearance-none bg-[length:16px] bg-[right_14px_center] bg-no-repeat pr-10", className)}
      style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%238691a7' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")" }}
      {...rest}
    >
      {children}
    </select>
  );
}

export function PasswordInput({ showLabel, hideLabel, ...rest }: React.InputHTMLAttributes<HTMLInputElement> & { showLabel: string; hideLabel: string }) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <Input type={show ? "text" : "password"} className="pr-12" {...rest} />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        className="absolute right-2 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-xl text-ink-3 hover:bg-paper-2 hover:text-ink"
        aria-label={show ? hideLabel : showLabel}
      >
        {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
}

export function FieldError({ children }: { children?: ReactNode }) {
  if (!children) return null;
  return (
    <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} className="mt-1.5 text-sm text-rose" role="alert">
      {children}
    </motion.p>
  );
}

/* -- Skeleton ------------------------------------------------------------ */

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton", className)} />;
}

/* -- Ring (mastery / score / progress) ------------------------------------ */

export function Ring({ value, size = 88, stroke = 8, label, className, color: fixed }: { value: number; size?: number; stroke?: number; label?: ReactNode; className?: string; color?: string }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const v = Math.max(0, Math.min(100, value));
  const color = fixed ?? (v >= 75 ? "var(--sage)" : v >= 50 ? "var(--marigold-600)" : "var(--rose)");
  return (
    <div className={cn("relative inline-grid place-items-center", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--paper-3)" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          whileInView={{ strokeDashoffset: c * (1 - v / 100) }}
          viewport={{ once: true }}
          transition={{ duration: 1.2, ease: EASE }}
        />
      </svg>
      <span className="absolute inset-0 grid place-items-center text-center">{label}</span>
    </div>
  );
}

/* -- Tabs with a sliding ink underline ------------------------------------ */

export function Tabs<T extends string>({ value, onChange, items, className }: { value: T; onChange: (v: T) => void; items: Array<{ value: T; label: ReactNode; badge?: ReactNode }>; className?: string }) {
  const id = useId();
  return (
    <div role="tablist" className={cn("relative flex gap-1 rounded-2xl bg-paper-2 p-1", className)}>
      {items.map((item) => {
        const active = item.value === value;
        return (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.value)}
            className={cn("relative z-10 flex flex-1 items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors", active ? "text-ink" : "text-ink-3 hover:text-ink-2")}
          >
            {active && (
              <motion.span layoutId={`tab-${id}`} className="absolute inset-0 -z-10 rounded-xl bg-surface shadow-[var(--shadow-soft)]" transition={{ type: "spring", stiffness: 420, damping: 34 }} />
            )}
            {item.label}
            {item.badge}
          </button>
        );
      })}
    </div>
  );
}
