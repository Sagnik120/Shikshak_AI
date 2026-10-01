"use client";

import { MotionConfig } from "motion/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { useState } from "react";
import { ApiError } from "@/core/api";
import { AuthProvider } from "./auth";
import { I18nProvider } from "./i18n";

export function AppProviders({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 15_000,
            refetchOnWindowFocus: false,
            // Don't hammer a server that said "no": only retry network blips.
            retry: (count, error) => count < 2 && error instanceof ApiError && (error.status === 0 || error.status >= 500),
          },
        },
      })
  );
  return (
    <MotionConfig reducedMotion="user">
      <QueryClientProvider client={client}>
        <I18nProvider>
          <AuthProvider>
            {children}
            <Toaster
              position="bottom-center"
              toastOptions={{
                classNames: {
                  toast:
                    "!rounded-2xl !border !border-line !bg-surface !text-ink !shadow-[var(--shadow-lift)] !font-sans",
                  description: "!text-ink-2",
                },
              }}
            />
          </AuthProvider>
        </I18nProvider>
      </QueryClientProvider>
    </MotionConfig>
  );
}
