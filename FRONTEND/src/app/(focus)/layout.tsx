"use client";

import { useRequireAuth } from "@/components/layout/app-shell";

/** Focus pages (the classroom) take the whole screen: no sidebar. */
export default function FocusLayout({ children }: { children: React.ReactNode }) {
  const allowed = useRequireAuth();
  if (!allowed) return <div className="grid min-h-dvh place-items-center"><div className="skeleton h-10 w-40" /></div>;
  return <>{children}</>;
}
