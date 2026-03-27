/**
 * Score utilities: confidence dampening and dot conversion.
 *
 * The confidence score uses a Bayesian prior (K=5) to pull scores with few
 * comparisons toward 50 (neutral). This is the score shown to users.
 */

const CONFIDENCE_K = 5;

/**
 * Bayesian-dampened score. Pulls toward 50 when n is low.
 *
 * @param rawScore - Raw match score (0-100)
 * @param nCompared - Number of effective comparisons (peso > 0)
 * @returns Adjusted score (0-100)
 */
export function confidenceScore(rawScore: number, nCompared: number): number {
	return (rawScore * nCompared + 50 * CONFIDENCE_K) / (nCompared + CONFIDENCE_K);
}

/**
 * Convert a 0-100 score to 0-10 in 0.5 increments (rendered as 5 dots).
 *
 * @returns Number from 0 to 10 in 0.5 steps
 */
export function scoreToDots(score: number): number {
	const raw = score / 10;
	return Math.round(raw * 2) / 2;
}
