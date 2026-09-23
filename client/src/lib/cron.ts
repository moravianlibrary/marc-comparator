/**
 * Validation and a plain-language reading of the five-field cron expressions
 * the scheduled jobs are configured with.
 *
 * The backend is the authority — it builds the celery schedule and rejects what
 * it cannot parse. This exists so a typo is caught in the form instead of on
 * submit, and so the field says what it will do rather than leaving the reader
 * to decode it.
 */

const FIELD_RANGES: Array<{ min: number; max: number; names?: Record<string, number> }> = [
  { min: 0, max: 59 }, // minute
  { min: 0, max: 23 }, // hour
  { min: 1, max: 31 }, // day of month
  {
    min: 1,
    max: 12,
    names: {
      jan: 1,
      feb: 2,
      mar: 3,
      apr: 4,
      may: 5,
      jun: 6,
      jul: 7,
      aug: 8,
      sep: 9,
      oct: 10,
      nov: 11,
      dec: 12,
    },
  }, // month
  {
    min: 0,
    max: 6,
    names: { sun: 0, mon: 1, tue: 2, wed: 3, thu: 4, fri: 5, sat: 6 },
  }, // day of week
];

export const CRON_FIELDS = FIELD_RANGES.length;

/** Every day at midnight — the default every schedule starts from. */
export const DAILY_CRON = '0 0 * * *';

function isValidValue(token: string, index: number): boolean {
  const { min, max, names } = FIELD_RANGES[index]!;
  const named = names?.[token.toLowerCase()];
  const value = named ?? Number(token);
  return Number.isInteger(value) && value >= min && value <= max;
}

function isValidPart(part: string, index: number): boolean {
  if (part === '') {
    return false;
  }

  const [range, step, ...rest] = part.split('/');
  if (rest.length > 0 || range === undefined) {
    return false;
  }
  if (step !== undefined && !(Number.isInteger(Number(step)) && Number(step) > 0)) {
    return false;
  }

  if (range === '*') {
    return true;
  }

  const [from, to, ...extra] = range.split('-');
  if (extra.length > 0 || from === undefined) {
    return false;
  }
  if (!isValidValue(from, index)) {
    return false;
  }
  return to === undefined ? true : isValidValue(to, index);
}

/** Whether every field is one the backend's parser will accept. */
export function isValidCron(expression: string): boolean {
  const fields = expression.trim().split(/\s+/);
  if (fields.length !== CRON_FIELDS) {
    return false;
  }
  return fields.every((field, index) => field.split(',').every(part => isValidPart(part, index)));
}

function pad(value: string): string {
  return value.padStart(2, '0');
}

export interface CronDescription {
  /** Translation key under `settings:cron.describe`. */
  key: string;
  values: Record<string, string>;
}

/**
 * Read back the common shapes in words. Anything more elaborate is left
 * undescribed rather than described approximately — a schedule the reader
 * believes runs nightly but does not is worse than one they have to decode.
 */
export function describeCron(expression: string): CronDescription | null {
  if (!isValidCron(expression)) {
    return null;
  }

  const [minute, hour, dayOfMonth, month, dayOfWeek] = expression.trim().split(/\s+/) as [
    string,
    string,
    string,
    string,
    string,
  ];

  const everyDate = dayOfMonth === '*' && month === '*';
  const isPlainNumber = (value: string) => /^\d+$/.test(value);

  if (everyDate && dayOfWeek === '*' && isPlainNumber(minute) && isPlainNumber(hour)) {
    return { key: 'daily', values: { time: `${pad(hour)}:${pad(minute)}` } };
  }

  if (everyDate && dayOfWeek === '*' && isPlainNumber(minute) && hour === '*') {
    return { key: 'hourly', values: { minute } };
  }

  const stepHours =
    everyDate && dayOfWeek === '*' && isPlainNumber(minute) && hour.match(/^\*\/(\d+)$/);
  if (stepHours) {
    return { key: 'every-n-hours', values: { hours: stepHours[1]!, minute } };
  }

  if (everyDate && isPlainNumber(minute) && isPlainNumber(hour) && isPlainNumber(dayOfWeek)) {
    return {
      key: 'weekly',
      values: { day: `weekday.${dayOfWeek}`, time: `${pad(hour)}:${pad(minute)}` },
    };
  }

  return null;
}

/** Ready-made expressions covering what these jobs are usually set to. */
export const CRON_PRESETS = [
  { key: 'hourly', expression: '0 * * * *' },
  { key: 'every-6-hours', expression: '0 */6 * * *' },
  { key: 'nightly', expression: '0 2 * * *' },
  { key: 'weekly', expression: '0 3 * * 0' },
] as const;
