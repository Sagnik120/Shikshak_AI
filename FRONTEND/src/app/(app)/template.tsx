"use client";

import { motion } from "motion/react";
import { EASE } from "@/lib/utils";

/**
 * Every page change: the page lifts into place. Opacity and position only — a
 * lingering `filter`/`transform` would become the containing block for
 * fixed-position dialogs inside the page.
 */
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0, transitionEnd: { transform: "none" } }}
      transition={{ duration: 0.4, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}
