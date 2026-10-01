import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  // The shell reads ?tab= for the staff navigation.
  return <Suspense><AppShell>{children}</AppShell></Suspense>;
}
