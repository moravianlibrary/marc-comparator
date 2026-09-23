import type { TFunction } from 'i18next';

/**
 * Name a task so two runs of the same type can be told apart.
 *
 * Every plugin harvest reads "Stažení dat pro rozšíření" without this, whichever
 * plugin it was for, and a sync of one base looks like a sync of any other. The
 * backend reports what the task acts on as `target`; a type that has no single
 * subject reports none and keeps its plain label.
 */
export function taskLabel(task: { type: string; target?: string | null }, t: TFunction): string {
  const base = t(`tasks:type.${task.type}`, { defaultValue: task.type });
  if (!task.target) {
    return base;
  }
  // Plugin registry names are identifiers ("skc"); show the name the settings
  // screens use, and fall back to the identifier for a plugin we cannot name.
  const target = t(`tasks:target.${task.target}`, { defaultValue: task.target });
  return t('tasks:type-with-target', { type: base, target });
}
