"use client";

import { RefreshCw } from "lucide-react";
import { useI18n } from "@/providers/i18n";
import { Button } from "@/components/ui/button";

/** Shown instead of an endless skeleton when a request fails. */
export function LoadError({ onRetry, className }: { onRetry: () => void; className?: string }) {
  const { t } = useI18n();
  return (
    <div className={`grid place-items-center gap-3 rounded-2xl border border-dashed border-line-2 px-6 py-10 text-center ${className ?? ""}`}>
      <p className="max-w-sm text-sm text-ink-2">{t("common.loadFailed")}</p>
      <Button size="sm" variant="outline" onClick={onRetry} icon={<RefreshCw className="h-4 w-4" />}>{t("common.retry")}</Button>
    </div>
  );
}
