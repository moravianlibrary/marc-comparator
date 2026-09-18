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
    <div className="bg-amber-50 border-b border-amber-200 px-6 py-2 dark:bg-amber-950/30 dark:border-amber-800">
      {locks.map(lock => (
        <div key={lock} className="text-sm text-amber-700 dark:text-amber-400">
          {formatLockName(lock, t)}
        </div>
      ))}
    </div>
  );
}
