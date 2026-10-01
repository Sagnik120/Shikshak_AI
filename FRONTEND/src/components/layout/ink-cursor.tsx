"use client";

/**
 * The cursor: an ink dot with a soft trailing ring that reads what it's over.
 *   links/buttons  -> the ring swells into a marigold highlighter circle
 *   the lesson video -> shows ॥ (playing) or ▶ (paused)
 *   text fields    -> a thin pen caret
 *   click          -> a tiny ink splash
 * Off on touch screens and for reduced motion; it never intercepts clicks.
 */
import { AnimatePresence, motion, useMotionValue, useSpring } from "motion/react";
import { useEffect, useState } from "react";

type Mode = "default" | "link" | "text" | "video-play" | "video-pause" | "hidden";

function modeFor(target: EventTarget | null): Mode {
  const el = target instanceof Element ? target : null;
  if (!el) return "default";
  const tagged = el.closest<HTMLElement>("[data-cursor]");
  if (tagged) {
    const kind = tagged.dataset.cursor;
    if (kind === "video") {
      const video = tagged.querySelector("video");
      return video && !video.paused ? "video-pause" : "video-play";
    }
    if (kind === "text") return "text";
    if (kind === "none") return "hidden";
    return "link";
  }
  if (el.closest("input:not([type=checkbox]):not([type=radio]):not([type=range]), textarea, [contenteditable=true]")) return "text";
  if (el.closest("a, button, [role=button], [role=tab], label, select, summary, [role=option], [role=slider]")) return "link";
  return "default";
}

export function InkCursor() {
  const [enabled, setEnabled] = useState(false);
  const [mode, setMode] = useState<Mode>("default");
  const [down, setDown] = useState(false);
  const [splashes, setSplashes] = useState<Array<{ id: number; x: number; y: number }>>([]);
  const x = useMotionValue(-100);
  const y = useMotionValue(-100);
  const rx = useSpring(x, { stiffness: 520, damping: 38, mass: 0.6 });
  const ry = useSpring(y, { stiffness: 520, damping: 38, mass: 0.6 });

  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)");
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => {
      const on = fine.matches && !reduce.matches;
      setEnabled(on);
      document.documentElement.classList.toggle("has-ink-cursor", on);
    };
    apply();
    fine.addEventListener("change", apply);
    reduce.addEventListener("change", apply);
    return () => {
      fine.removeEventListener("change", apply);
      reduce.removeEventListener("change", apply);
      document.documentElement.classList.remove("has-ink-cursor");
    };
  }, []);

  useEffect(() => {
    if (!enabled) return;
    let id = 0;
    const move = (e: PointerEvent) => {
      x.set(e.clientX);
      y.set(e.clientY);
      setMode(modeFor(e.target));
    };
    const press = (e: PointerEvent) => {
      setDown(true);
      const splash = { id: ++id, x: e.clientX, y: e.clientY };
      setSplashes((s) => [...s.slice(-4), splash]);
      setTimeout(() => setSplashes((s) => s.filter((p) => p.id !== splash.id)), 600);
    };
    const release = () => setDown(false);
    const leave = () => setMode("hidden");
    window.addEventListener("pointermove", move, { passive: true });
    window.addEventListener("pointerdown", press, { passive: true });
    window.addEventListener("pointerup", release, { passive: true });
    document.addEventListener("pointerleave", leave);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerdown", press);
      window.removeEventListener("pointerup", release);
      document.removeEventListener("pointerleave", leave);
    };
  }, [enabled, x, y]);

  if (!enabled) return null;

  const ring = {
    default: { width: 30, height: 30, background: "rgba(59,102,174,0)", borderColor: "rgba(30,41,66,0.28)" },
    link: { width: 46, height: 46, background: "rgba(249,225,154,0.45)", borderColor: "rgba(196,140,24,0.35)" },
    text: { width: 2, height: 26, background: "rgba(59,102,174,0.9)", borderColor: "rgba(59,102,174,0)" },
    "video-play": { width: 64, height: 64, background: "rgba(255,255,255,0.85)", borderColor: "rgba(30,41,66,0.15)" },
    "video-pause": { width: 64, height: 64, background: "rgba(255,255,255,0.85)", borderColor: "rgba(30,41,66,0.15)" },
    hidden: { width: 0, height: 0, background: "rgba(0,0,0,0)", borderColor: "rgba(0,0,0,0)" },
  }[mode];

  return (
    <div className="pointer-events-none fixed inset-0 z-[200]" aria-hidden="true">
      <motion.div
        className="absolute left-0 top-0 grid place-items-center rounded-full border backdrop-blur-[1px]"
        style={{ x: rx, y: ry, translateX: "-50%", translateY: "-50%" }}
        animate={{ ...ring, scale: down ? 0.82 : 1, borderRadius: mode === "text" ? 2 : 999 }}
        transition={{ type: "spring", stiffness: 420, damping: 30 }}
      >
        <AnimatePresence>
          {(mode === "video-play" || mode === "video-pause") && (
            <motion.span
              key={mode}
              initial={{ opacity: 0, scale: 0.6 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.6 }}
              className="font-display text-2xl leading-none text-ink"
            >
              {mode === "video-pause" ? "॥" : "▶"}
            </motion.span>
          )}
        </AnimatePresence>
      </motion.div>
      <motion.div
        className="absolute left-0 top-0 h-[6px] w-[6px] rounded-full bg-ink"
        style={{ x, y, translateX: "-50%", translateY: "-50%" }}
        animate={{ opacity: mode === "text" || mode === "hidden" || mode.startsWith("video") ? 0 : 1, scale: down ? 1.6 : 1 }}
        transition={{ duration: 0.15 }}
      />
      {splashes.map((s) => (
        <span key={s.id} className="absolute" style={{ left: s.x, top: s.y }}>
          {[0, 60, 120, 180, 240, 300].map((deg) => (
            <motion.span
              key={deg}
              className="absolute h-1 w-1 rounded-full bg-sky-500"
              initial={{ x: 0, y: 0, opacity: 0.9, scale: 1 }}
              animate={{
                x: Math.cos((deg * Math.PI) / 180) * 14,
                y: Math.sin((deg * Math.PI) / 180) * 14,
                opacity: 0,
                scale: 0.4,
              }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            />
          ))}
        </span>
      ))}
    </div>
  );
}
