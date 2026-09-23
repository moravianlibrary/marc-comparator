import type { Task } from '@/types/task';

/** How often to re-read a task, its log and its row while it is still in flight. */
export const RUNNING_POLL_MS = 2000;

/**
 * How often to re-read a task list that currently shows nothing running.
 *
 * Deciding "nothing is running, so stop polling" from the list's own data is
 * self-defeating: a task started after the last fetch is exactly what the stale
 * data cannot show, so the list would never learn of it and never poll again.
 * WebSocket events normally invalidate these queries, but they are a push
 * channel — when it is down the UI must still converge on its own.
 */
export const IDLE_POLL_MS = 15000;

export function isTaskInFlight(task: Pick<Task, 'status'>): boolean {
  return task.status === 'Pending' || task.status === 'Started';
}
