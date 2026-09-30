/**
 * The comparator's match scale, as the client has to render it.
 *
 * Scores run 0 to 15, bigger is better, and they are the scoring engine's own
 * numbers rather than a curve over them. They used to be a 0-1 similarity
 * shown as a percentage, which is why nothing here multiplies by 100 any
 * more: a "78 %" invited a reading — three quarters right — that the number
 * never supported.
 */
export const MATCH_SCALE_MAX = 15;

/** A match score as it is shown: one decimal, out of the scale's top. */
export function formatScore(score: number): string {
  return `${score.toFixed(1)} / ${MATCH_SCALE_MAX}`;
}

/** The same score without the denominator, for somewhere already labelled. */
export function formatScoreShort(score: number): string {
  return score.toFixed(1);
}

/**
 * Where the quality bands sit, mirroring the comparator's own defaults.
 *
 * The backend decides a comparison's band once and stores it, so these are
 * only for colouring a number the backend did not band — a single field or
 * subfield inside a record's comparison.
 */
export const EXCELLENT_MATCH = 12;
export const MODERATE_MATCH = 9;
