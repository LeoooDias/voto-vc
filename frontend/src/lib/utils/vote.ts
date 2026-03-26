/**
 * Maps between the 5-position vote slider and the voto/peso values.
 *
 * Position 1: Contra       (nao, 1.00)
 * Position 2: Contra leve  (nao, 0.50)
 * Position 3: Neutro       (sim, 0.00)
 * Position 4: A favor leve (sim, 0.50)
 * Position 5: A favor      (sim, 1.00)
 */

const POSITION_MAP: Array<{ voto: 'sim' | 'nao'; peso: number }> = [
	{ voto: 'nao', peso: 1.0 }, // pos 1: Contra
	{ voto: 'nao', peso: 0.5 }, // pos 2: Contra leve
	{ voto: 'sim', peso: 0.0 }, // pos 3: Neutro
	{ voto: 'sim', peso: 0.5 }, // pos 4: A favor leve
	{ voto: 'sim', peso: 1.0 } // pos 5: A favor
];

export function positionToVote(pos: number): { voto: 'sim' | 'nao'; peso: number } {
	return POSITION_MAP[pos - 1] ?? POSITION_MAP[2]; // default Neutro
}

export function voteToPosition(voto: string, peso: number): number | null {
	if (voto === 'pular') return null;
	if (peso === 0) return 3; // Neutro
	for (let i = 0; i < POSITION_MAP.length; i++) {
		const m = POSITION_MAP[i];
		if (m.voto === voto && Math.abs(m.peso - peso) < 0.01) {
			return i + 1;
		}
	}
	// Fallback approximate
	if (voto === 'nao') return peso >= 0.75 ? 1 : 2;
	return peso >= 0.75 ? 5 : 4;
}

export function voteLabel(voto: string, peso: number): string {
	if (voto === 'pular') return 'Pulou';
	if (peso === 0) return 'Neutro';
	const direction = voto === 'sim' ? 'A favor' : 'Contra';
	if (peso >= 0.75) return direction;
	return direction + ' (leve)';
}
