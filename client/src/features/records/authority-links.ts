import type { AuthorityLinkSummary } from './types';

/**
 * How a link's confidence should be labelled, or null when it needs no label.
 *
 * Linkers that resolve an identifier report full confidence, and putting
 * "100 %" on every one of those badges would be noise. A linker that scored
 * the match reports what it measured, and that number is the only thing
 * telling an operator a plausible link from a certain one.
 */
export function confidenceLabel(link: AuthorityLinkSummary): string | null {
  if (link.confidence === null || link.confidence >= 1) {
    return null;
  }
  return `${Math.round(link.confidence * 100)} %`;
}
