import type { ValidationSummary } from "./types";

export const STATUS_ORDER: Record<string, number> = {
  Valid: 0,
  ForReview: 1,
  Invalid: 2,
  AdditionalInfo: 3,
};

export function groupValidations(validations: ValidationSummary[]) {
  const map = new Map<
    string,
    { validator: string; target_tag: string; status: string; count: number }
  >();
  for (const v of validations) {
    const key = `${v.validator}|${v.target_tag}|${v.status}`;
    const existing = map.get(key);
    if (existing) {
      existing.count++;
    } else {
      map.set(key, {
        validator: v.validator,
        target_tag: v.target_tag,
        status: v.status,
        count: 1,
      });
    }
  }
  return [...map.values()].sort(
    (a, b) => (STATUS_ORDER[a.status] ?? 99) - (STATUS_ORDER[b.status] ?? 99),
  );
}

export function stripPrefix(key: string): string {
  const i = key.indexOf(":");
  return i >= 0 ? key.slice(i + 1) : key;
}
