import { formatScore, MATCH_SCALE_MAX } from './score';
import type { AuthorityLinkSummary } from './types';

/**
 * How a link's confidence should be labelled, or null when it needs no label.
 *
 * A pair the comparator found nothing to separate scores the top of the
 * scale, and putting "15.0 / 15" on every one of those badges would be noise.
 * Anything short of it is what tells an operator a plausible link from a
 * certain one.
 */
export function confidenceLabel(link: AuthorityLinkSummary): string | null {
  if (link.confidence === null || link.confidence >= MATCH_SCALE_MAX) {
    return null;
  }
  return formatScore(link.confidence);
}
