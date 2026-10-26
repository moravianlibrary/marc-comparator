// A record's link decisions and stored comparisons, grouped by the base they compare against.
//
// Linking and comparison describe the same pairs: the record linked to a base is the one the
// stored comparison was made with, and the candidates weighed against it are compared on demand.
// The record detail shows them as one entry per base — the chosen record first, the rest behind —
// instead of an authority link, a comparison and a candidate list that each name the same base.

import { buildCandidateKey, type DecisionRow, decisionsByBase } from './link-decisions';
import type { ComparisonSummary, LinkAttemptSummary, RecordSummary } from './types';

/** Where a record stands among the ones compared against the same base. */
export type ComparedRole = 'chosen' | 'best' | 'alternative';

export interface ComparedRecord {
  /** The catalogue id of the compared record, `<base>-<system number>`. */
  recordId: string;
  role: ComparedRole;
  /** What linking and cataloguers said about the pair, or null for a comparison alone. */
  decision: DecisionRow | null;
  /** The stored comparison, which only the linked record has. */
  comparison: ComparisonSummary | null;
  /** The stored comparison's score, else the linker's own score for the pair. */
  score: number | null;
  /** The record detail view that compares this record with ours. */
  viewKey: string;
}

export interface ComparisonGroup {
  base: string;
  /** What linking concluded for the base, or null where it never ran. */
  answer: LinkAttemptSummary | null;
  /** The chosen or best record first, then the alternatives in rank order. */
  records: ComparedRecord[];
}

const ROLE_ORDER: Record<ComparedRole, number> = { chosen: 0, best: 1, alternative: 2 };

/** The carousel view key for a stored comparison. */
export function buildComparisonKey(comparator: string, otherRecordId: string): string {
  return `comp:${comparator}:${otherRecordId}`;
}

/** Every base the record was linked or compared against, in base order. */
export function comparisonGroups(record: RecordSummary): ComparisonGroup[] {
  const decisions = new Map(decisionsByBase(record).map(d => [d.base, d]));
  const bases = [...new Set([...decisions.keys(), ...record.comparisons.map(c => c.base)])].sort();

  return bases.map(base => {
    const decision = decisions.get(base);
    const comparisons = record.comparisons.filter(c => c.base === base);
    const answer = decision?.answer ?? null;
    const fromDecisions = (decision?.rows ?? []).map(row =>
      fromDecisionRow(row, answer, comparisons),
    );
    const named = new Set(fromDecisions.map(r => r.recordId));
    const hasChosen = fromDecisions.some(r => r.role === 'chosen');
    const fromComparisons = comparisons
      .filter(c => !named.has(c.other_record_id))
      .map(c => fromComparison(c, hasChosen));
    const records = [...fromDecisions, ...fromComparisons].sort(
      (a, b) => ROLE_ORDER[a.role] - ROLE_ORDER[b.role],
    );

    return { base, answer, records };
  });
}

function fromDecisionRow(
  row: DecisionRow,
  answer: LinkAttemptSummary | null,
  comparisons: ComparisonSummary[],
): ComparedRecord {
  const recordId = `${row.authorityBase}-${row.authoritySysno}`;
  const comparison = comparisons.find(c => c.other_record_id === recordId) ?? null;
  const role: ComparedRole = !row.isAnswer
    ? 'alternative'
    : answer?.outcome === 'Linked'
      ? 'chosen'
      : 'best';

  return {
    recordId,
    role,
    decision: row,
    comparison,
    score: comparison?.overall_score ?? row.attempt?.confidence ?? null,
    viewKey: comparison
      ? buildComparisonKey(comparison.comparator, comparison.other_record_id)
      : buildCandidateKey(row.authorityBase, row.authoritySysno),
  };
}

// A comparison that no link decision names: one made before linking recorded its attempts.
// It is the chosen record unless linking has since chosen another.
function fromComparison(comparison: ComparisonSummary, hasChosen: boolean): ComparedRecord {
  return {
    recordId: comparison.other_record_id,
    role: hasChosen ? 'alternative' : 'chosen',
    decision: null,
    comparison,
    score: comparison.overall_score,
    viewKey: buildComparisonKey(comparison.comparator, comparison.other_record_id),
  };
}
