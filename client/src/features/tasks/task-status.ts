import type { Task } from '@/types/task';

/** How often to re-read a task, its log and its row while it is still in flight. */
export const RUNNING_POLL_MS = 2000;

export function isTaskInFlight(task: Pick<Task, 'status'>): boolean {
  return task.status === 'Pending' || task.status === 'Started';
}
