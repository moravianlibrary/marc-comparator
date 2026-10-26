import type { LinkAttemptSummary, RecordSummary } from './types';

/** The answer for each base: what linking concluded, link or not. */
function linkAnswers(record: RecordSummary): LinkAttemptSummary[] {
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
