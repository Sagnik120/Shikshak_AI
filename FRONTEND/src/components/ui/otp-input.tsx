"use client";

/** Six boxes: auto-advance, paste a whole code, backspace back, shake on error. */
import { motion, useAnimationControls } from "motion/react";
import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { cn } from "@/lib/utils";

export type OtpHandle = { fill: (code: string) => void; clear: () => void; shake: () => void };

export const OtpInput = forwardRef<OtpHandle, { length?: number; value: string; onChange: (v: string) => void; onComplete?: (v: string) => void; disabled?: boolean }>(
  function OtpInput({ length = 6, value, onChange, onComplete, disabled }, ref) {
    const boxes = useRef<Array<HTMLInputElement | null>>([]);
    const controls = useAnimationControls();
    const digits = Array.from({ length }, (_, i) => value[i] ?? "");

    const set = (next: string) => {
      const clean = next.replace(/\D/g, "").slice(0, length);
      onChange(clean);
      if (clean.length === length) onComplete?.(clean);
    };

    useImperativeHandle(ref, () => ({
      fill: (code) => {
        set(code);
        boxes.current[Math.min(code.length, length - 1)]?.focus();
      },
      clear: () => {
        onChange("");
        boxes.current[0]?.focus();
      },
      shake: () => void controls.start({ x: [0, -10, 10, -6, 6, 0], transition: { duration: 0.4 } }),
    }));

    useEffect(() => {
      boxes.current[0]?.focus();
    }, []);

    return (
      <motion.div animate={controls} className="flex justify-between gap-2" onPaste={(e) => { e.preventDefault(); set(e.clipboardData.getData("text")); }}>
        {digits.map((d, i) => (
          <input
            key={i}
            ref={(el) => { boxes.current[i] = el; }}
            inputMode="numeric"
            autoComplete={i === 0 ? "one-time-code" : "off"}
            maxLength={1}
            disabled={disabled}
            aria-label={`Digit ${i + 1}`}
            value={d}
            onChange={(e) => {
              const ch = e.target.value.replace(/\D/g, "").slice(-1);
              const arr = digits.slice();
              arr[i] = ch;
              set(arr.join(""));
              if (ch && i < length - 1) boxes.current[i + 1]?.focus();
            }}
            onKeyDown={(e) => {
              if (e.key === "Backspace" && !digits[i] && i > 0) boxes.current[i - 1]?.focus();
              if (e.key === "ArrowLeft" && i > 0) boxes.current[i - 1]?.focus();
              if (e.key === "ArrowRight" && i < length - 1) boxes.current[i + 1]?.focus();
            }}
            onFocus={(e) => e.target.select()}
            className={cn(
              "h-14 w-full min-w-0 rounded-2xl border bg-surface text-center font-display text-3xl text-ink outline-none transition-[border-color,box-shadow,transform] duration-200",
              d ? "border-sky-300 bg-sky-50/50" : "border-line-2",
              "focus:-translate-y-0.5 focus:border-sky-500 focus:shadow-[0_0_0_4px_var(--sky-50)]"
            )}
          />
        ))}
      </motion.div>
    );
  }
);
