import type { Task } from './task';

/**
 * Live state of one harvest-capable plugin.
 *
 * The server also reports the source fingerprint and the SQL schema it owns.
 * Both are deliberately absent here: they are internal bookkeeping, and an
 * operator decides what to do from readiness and the last successful harvest.
 */
export interface HarvestPluginStatus {
  name: string;
  /** Settings scope the plugin is configured under, e.g. `validators`. */
  scope: string;
  enabled: boolean;
  /** Five-field cron expression, e.g. `0 2 * * *`. */
  cron: string;
  /** A local dataset exists and matches the current configuration. */
  ready: boolean;
  compatible: boolean;
  /** Records processed by the last successful run, not the dataset size. */
  records: number | null;
  last_harvest_at: string | null;
  current_task: Task | null;
}
