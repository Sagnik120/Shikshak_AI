import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));

/** The one easing curve used everywhere (matches --ease-out-soft). */
export const EASE = [0.22, 1, 0.36, 1] as const;
export const SPRING = { type: "spring", stiffness: 380, damping: 30, mass: 0.8 } as const;

export function clamp(n: number, min: number, max: number) {
  return Math.min(max, Math.max(min, n));
}
