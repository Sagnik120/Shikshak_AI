"use client";

/**
 * The button. Variants by intent, an ink ripple on press, and a `status`
 * mode (idle -> working -> done ✓ / error ✕) adapted from the StatusButton
 * idea — the label and icon morph instead of the button being swapped.
 */
import Link from "next/link";
import { cva, type VariantProps } from "class-variance-authority";
import { AnimatePresence, motion } from "motion/react";
import { Check, LoaderCircle, X } from "lucide-react";
import { forwardRef, useState, type ReactNode } from "react";
import { cn, EASE } from "@/lib/utils";

const buttonStyles = cva(
  "relative inline-flex select-none items-center justify-center gap-2 overflow-hidden whitespace-nowrap font-medium transition-[background,color,box-shadow,transform,border-color] duration-200 ease-[var(--ease-out-soft)] disabled:pointer-events-none disabled:opacity-55 active:translate-y-[1px]",
  {
    variants: {
      variant: {
        primary:
          "bg-sky-600 text-white shadow-[0_1px_0_rgb(255_255_255/0.25)_inset,0_6px_18px_-8px_rgb(59_102_174/0.7)] hover:bg-sky-700",
        ink: "bg-ink text-paper hover:bg-ink-2 shadow-[0_6px_18px_-10px_rgb(30_41_66/0.8)]",
        marigold: "bg-marigold-400 text-ink hover:bg-marigold-200 shadow-[0_6px_18px_-10px_rgb(196_140_24/0.8)]",
        outline: "border border-line-2 bg-surface text-ink hover:border-sky-300 hover:bg-sky-50",
        soft: "bg-sky-50 text-sky-700 hover:bg-sky-100",
        ghost: "text-ink-2 hover:bg-paper-2 hover:text-ink",
        danger: "bg-rose-100 text-rose hover:bg-rose hover:text-white",
        link: "text-sky-600 underline-offset-4 hover:underline px-0",
      },
      size: {
        sm: "h-9 rounded-xl px-3.5 text-sm",
        md: "h-11 rounded-2xl px-5 text-[0.95rem]",
        lg: "h-13 rounded-2xl px-7 text-base",
        icon: "h-10 w-10 rounded-xl",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  }
);

export type ButtonStatus = "idle" | "loading" | "success" | "error";

type Props = VariantProps<typeof buttonStyles> & {
  href?: string;
  status?: ButtonStatus;
  loadingLabel?: ReactNode;
  successLabel?: ReactNode;
  errorLabel?: ReactNode;
  icon?: ReactNode;
  className?: string;
  children?: ReactNode;
} & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "children">;

type Ripple = { id: number; x: number; y: number; size: number };

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant, size, href, status = "idle", loadingLabel, successLabel, errorLabel, icon, className, children, onPointerDown, disabled, ...rest },
  ref
) {
  const [ripples, setRipples] = useState<Ripple[]>([]);

  const addRipple = (e: React.PointerEvent<HTMLElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 2.2;
    const r = { id: Date.now() + Math.random(), x: e.clientX - rect.left - size / 2, y: e.clientY - rect.top - size / 2, size };
    setRipples((list) => [...list.slice(-3), r]);
    setTimeout(() => setRipples((list) => list.filter((p) => p.id !== r.id)), 650);
  };

  const label =
    status === "loading" ? loadingLabel ?? children : status === "success" ? successLabel ?? children : status === "error" ? errorLabel ?? children : children;
  const leading =
    status === "loading" ? <LoaderCircle className="h-4 w-4 animate-spin" /> :
    status === "success" ? <Check className="h-4 w-4" /> :
    status === "error" ? <X className="h-4 w-4" /> : icon;

  const inner = (
    <>
      {ripples.map((r) => (
        <motion.span
          key={r.id}
          className="pointer-events-none absolute rounded-full bg-white/35 mix-blend-soft-light"
          style={{ left: r.x, top: r.y, width: r.size, height: r.size }}
          initial={{ scale: 0, opacity: 0.6 }}
          animate={{ scale: 1, opacity: 0 }}
          transition={{ duration: 0.6, ease: EASE }}
        />
      ))}
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={status}
          className="relative inline-flex items-center gap-2"
          initial={{ opacity: 0, y: 8, filter: "blur(3px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          exit={{ opacity: 0, y: -8, filter: "blur(3px)" }}
          transition={{ duration: 0.22, ease: EASE }}
        >
          {leading}
          {label}
        </motion.span>
      </AnimatePresence>
    </>
  );

  const classes = cn(
    buttonStyles({ variant, size }),
    status === "success" && "!bg-sage !text-white",
    status === "error" && "!bg-rose !text-white",
    className
  );

  if (href) {
    return (
      <Link href={href} className={classes} onPointerDown={addRipple} data-cursor="link">
        {inner}
      </Link>
    );
  }
  return (
    <button
      ref={ref}
      className={classes}
      disabled={disabled || status === "loading"}
      aria-busy={status === "loading"}
      onPointerDown={(e) => {
        addRipple(e);
        onPointerDown?.(e);
      }}
      {...rest}
    >
      {inner}
    </button>
  );
});
