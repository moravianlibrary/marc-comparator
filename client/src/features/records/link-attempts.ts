import type { LinkAttemptSummary, RecordSummary } from './types';

/** The answer for each base: what linking concluded, link or not. */
export function linkAnswers(record: RecordSummary): LinkAttemptSummary[] {
  return record.link_attempts.filter(a => a.rank === 0);
}

/**
 * The answers that are not links, which are the ones worth a badge.
 *
 * A record that linked already says so through its authority-link badge, so
 * repeating "Linked" beside it would be noise. What was missing is the other
 * four fifths of the story: found nothing, could not look, found something
 * and refused it.
 */
export function linkGaps(record: RecordSummary): LinkAttemptSummary[] {
  return linkAnswers(record).filter(a => a.outcome !== 'Linked');
}

/** The runner-ups for one base, best first. */
export function candidatesFor(record: RecordSummary, base: string): LinkAttemptSummary[] {
  return record.link_attempts
    .filter(a => a.base === base && a.rank > 0)
    .sort((a, b) => a.rank - b.rank);
}

/** Every runner-up the record kept, whatever base it was for. */
export function allCandidates(record: RecordSummary): LinkAttemptSummary[] {
  return record.link_attempts.filter(a => a.rank > 0);
}

/**
 * How a candidate names the record it stands for.
 *
 * A candidate has no `catalog_records` row — that is what makes keeping it
 * affordable — so it is identified by its natural key and not by an id that
 * resolves to anything.
 */
export function candidateLabel(attempt: LinkAttemptSummary): string {
  if (attempt.authority_base && attempt.authority_sysno) {
    return `${attempt.authority_base}-${attempt.authority_sysno}`;
  }
  return attempt.authority_record_id ?? '';
}

/** A score as a percentage, or null where the linker reported none. */
export function scoreLabel(attempt: LinkAttemptSummary): string | null {
  return attempt.confidence === null ? null : `${Math.round(attempt.confidence * 100)} %`;
}
