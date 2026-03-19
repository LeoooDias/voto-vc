/**
 * Maps between the 9-position vote slider and the voto/peso values.
 *
 * Position 1: Contra      (nao, 1.00)
 * Position 2:             (nao, 0.75)
 * Position 3:             (nao, 0.50)
 * Position 4:             (nao, 0.25)
 * Position 5: Neutro      (sim, 0.00)
 * Position 6:             (sim, 0.25)
 * Position 7:             (sim, 0.50)
 * Position 8:             (sim, 0.75)
 * Position 9: A favor     (sim, 1.00)
 */

const POSITION_MAP: Array<{ voto: 'sim' | 'nao'; peso: number }> = [
	{ voto: 'nao', peso: 1.0 }, // pos 1
	{ voto: 'nao', peso: 0.75 }, // pos 2
	{ voto: 'nao', peso: 0.5 }, // pos 3
	{ voto: 'nao', peso: 0.25 }, // pos 4
	{ voto: 'sim', peso: 0.0 }, // pos 5 (Neutro)
	{ voto: 'sim', peso: 0.25 }, // pos 6
	{ voto: 'sim', peso: 0.5 }, // pos 7
	{ voto: 'sim', peso: 0.75 }, // pos 8
	{ voto: 'sim', peso: 1.0 } // pos 9
];

export function positionToVote(pos: number): { voto: 'sim' | 'nao'; peso: number } {
	return POSITION_MAP[pos - 1] ?? POSITION_MAP[4]; // default Neutro
}

export function voteToPosition(voto: string, peso: number): number | null {
	if (voto === 'pular') return null;
	if (peso === 0) return 5; // Neutro
	// Find closest match
	for (let i = 0; i < POSITION_MAP.length; i++) {
		const m = POSITION_MAP[i];
		if (m.voto === voto && Math.abs(m.peso - peso) < 0.01) {
			return i + 1;
		}
	}
	// Fallback: approximate
	if (voto === 'nao') {
		if (peso >= 0.875) return 1;
		if (peso >= 0.625) return 2;
		if (peso >= 0.375) return 3;
		return 4;
	}
	if (peso >= 0.875) return 9;
	if (peso >= 0.625) return 8;
	if (peso >= 0.375) return 7;
	return 6;
}

export function voteLabel(voto: string, peso: number): string {
	if (voto === 'pular') return 'Pulou';
	if (peso === 0) return 'Neutro';
	const direction = voto === 'sim' ? 'A favor' : 'Contra';
	if (peso >= 0.875) return direction;
	if (peso >= 0.625) return direction;
	if (peso >= 0.375) return direction;
	return direction;
}
