import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import apiClient from '@/lib/api-client';

function formatLockName(
  lock: string,
  t: (key: string, opts?: Record<string, string>) => string,
): string {
  const syncMatch = lock.match(/^catalog_sync_(.+)$/);
  if (syncMatch) {
    return t('common:lock-banner.catalog-sync', { base: syncMatch[1]! });
  }
  return lock;
}

/**
 * Every task run takes a `task-run-<id>` mutex of its own. That is an internal
 * guard against double execution, not a resource the user is locked out of —
 * the running task is already visible on the tasks page.
 */
function isInternalLock(lock: string): boolean {
  return lock.startsWith('task-run-');
}

export function LockBanner() {
  const { t } = useTranslation();

  const { data: allLocks = [] } = useQuery<string[]>({
    queryKey: ['system', 'locks'],
    queryFn: () => apiClient.get<string[]>('/system/locks').then(r => r.data),
  });

  const locks = allLocks.filter(lock => !isInternalLock(lock));

  if (locks.length === 0) {
    return null;
  }

  return (
    // The banner is sticky, so its background has to be opaque or the page
    // scrolls through it. The dark tint mixes into the page background rather
    // than into transparency, which keeps the colour and loses the leak.
    <div className="bg-amber-50 border-b border-amber-200 px-6 py-2 dark:bg-[color-mix(in_oklch,var(--color-amber-950)_30%,var(--background))] dark:border-amber-800">
      {locks.map(lock => (
        <div key={lock} className="text-sm text-amber-700 dark:text-amber-400">
          {formatLockName(lock, t)}
        </div>
      ))}
    </div>
  );
}
