import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";

function formatLockName(
  lock: string,
  t: (key: string, opts?: Record<string, string>) => string,
): string {
  const syncMatch = lock.match(/^catalog_sync_(.+)$/);
  if (syncMatch) {
    return t("common:lock-banner.catalog-sync", { base: syncMatch[1] });
  }
  return lock;
}

export function LockBanner() {
  const { t } = useTranslation();

  const { data: locks = [] } = useQuery<string[]>({
    queryKey: ["system", "locks"],
    queryFn: () => apiClient.get<string[]>("/system/locks").then((r) => r.data),
  });

  if (locks.length === 0) return null;

  return (
    <div className="bg-amber-50 border-b border-amber-200 px-6 py-2 dark:bg-amber-950/30 dark:border-amber-800">
      {locks.map((lock) => (
        <div key={lock} className="text-sm text-amber-700 dark:text-amber-400">
          {formatLockName(lock, t)}
        </div>
      ))}
    </div>
  );
}
