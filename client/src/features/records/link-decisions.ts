import type { LinkAttemptSummary, RecordClaimSummary, RecordSummary } from './types';

/**
 * One pair of records — ours and a candidate — as a cataloguer meets it.
 *
 * Two sources have to be read together to say anything useful about a pair,
 * and neither is complete on its own. `link_attempts` is what the machine
 * concluded, and it drops a candidate the moment a claim rules it out; the
 * claim then names a record with no attempt row behind it. `claims` is what
 * people said, and it says nothing about the candidates nobody has ruled on
 * yet. A row here is the join: the pair, what linking stored about it, and
 * what a person said about it, with either half allowed to be missing.
 */
export interface DecisionRow {
  /** The target base, matching `LinkAttemptSummary.base`. */
  base: string;
  /** The candidate's natural key — what the claim endpoints are addressed by. */
  authorityBase: string;
  authoritySysno: string;
  /** What linking stored, or null where only a claim names this pair. */
  attempt: LinkAttemptSummary | null;
  /** What a cataloguer said, or null where nobody has yet. */
  claim: RecordClaimSummary | null;
  /** Whether this pair sits at the answer rank for its base. */
  isAnswer: boolean;
}

/** Everything the record has to say about one target base. */
export interface BaseDecision {
  base: string;
  /**
   * The answer row, whatever it says.
   *
   * Kept beside `rows` rather than inside it because an answer does not
   * always name a record: nothing found and a lookup that failed are both
   * answers, and neither has a pair to show.
   */
  answer: LinkAttemptSummary | null;
  /** The pairs, the answer first and the runner-ups behind it in rank order. */
  rows: DecisionRow[];
}

function pairKey(base: string, authorityBase: string, authoritySysno: string): string {
  return `${base}|${authorityBase}|${authoritySysno}`;
}

/** The key that identifies a row in a list, and in the mutation it triggers. */
export function rowKey(row: DecisionRow): string {
  return pairKey(row.base, row.authorityBase, row.authoritySysno);
}

/** What the record says about each base it was tried against, best first. */
export function decisionsByBase(record: RecordSummary): BaseDecision[] {
  const bases = [
    ...new Set([...record.link_attempts.map(a => a.base), ...record.claims.map(c => c.base)]),
  ].sort();

  return bases.map(base => {
    const attempts = record.link_attempts
      .filter(a => a.base === base)
      .sort((a, b) => a.rank - b.rank);
    const claims = record.claims.filter(c => c.base === base);
    const claimByPair = new Map(
      claims.map(c => [pairKey(c.base, c.authority_base, c.authority_sysno), c]),
    );

    const rows: DecisionRow[] = [];
    for (const attempt of attempts) {
      if (!attempt.authority_base || !attempt.authority_sysno) {
        // An answer that names no record: nothing was found, or the lookup
        // never completed. The outcome belongs on the base, not on a pair.
        continue;
      }
      const key = pairKey(base, attempt.authority_base, attempt.authority_sysno);
      rows.push({
        base,
        authorityBase: attempt.authority_base,
        authoritySysno: attempt.authority_sysno,
        attempt,
        claim: claimByPair.get(key) ?? null,
        isAnswer: attempt.rank === 0,
      });
      claimByPair.delete(key);
    }

    // Whatever is left named a record this pass did not return — a claim
    // against a candidate retrieval has since stopped finding, or one made
    // for a record no linker ever proposed. Both still decide the answer,
    // so both have to be visible and withdrawable.
    for (const claim of claimByPair.values()) {
      rows.push({
        base,
        authorityBase: claim.authority_base,
        authoritySysno: claim.authority_sysno,
        attempt: null,
        claim,
        isAnswer: false,
      });
    }

    return { base, answer: attempts.find(a => a.rank === 0) ?? null, rows };
  });
}

/** Whether a cataloguer has ruled on this record's link to a base. */
export function hasClaimFor(record: RecordSummary, base: string): boolean {
  return record.claims.some(c => c.base === base);
}
