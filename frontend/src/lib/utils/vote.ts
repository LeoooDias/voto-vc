/**
 * Maps between the 5-position vote slider and the voto/peso values.
 *
 * Position 1: Fortemente Contra (nao, 1.0)
 * Position 2: Contra            (nao, 0.5)
 * Position 3: Neutro            (sim, 0.0)
 * Position 4: A favor           (sim, 0.5)
 * Position 5: Fortemente A favor(sim, 1.0)
 */

const POSITION_MAP: Array<{ voto: 'sim' | 'nao'; peso: number }> = [
	{ voto: 'nao', peso: 1.0 }, // pos 1
	{ voto: 'nao', peso: 0.5 }, // pos 2
	{ voto: 'sim', peso: 0.0 }, // pos 3 (Neutro)
	{ voto: 'sim', peso: 0.5 }, // pos 4
	{ voto: 'sim', peso: 1.0 } // pos 5
];

export function positionToVote(pos: number): { voto: 'sim' | 'nao'; peso: number } {
	return POSITION_MAP[pos - 1] ?? POSITION_MAP[2]; // default Neutro
}

export function voteToPosition(voto: string, peso: number): number | null {
	if (voto === 'pular') return null;
	if (peso === 0) return 3; // Neutro
	if (voto === 'nao' && peso >= 0.75) return 1;
	if (voto === 'nao') return 2;
	if (voto === 'sim' && peso >= 0.75) return 5;
	if (voto === 'sim') return 4;
	return null;
}

const LABELS: Record<number, string> = {
	1: 'Fortemente Contra',
	2: 'Contra',
	3: 'Neutro',
	4: 'A favor',
	5: 'Fortemente A favor'
};

export function voteLabel(voto: string, peso: number): string {
	if (voto === 'pular') return 'Pulou';
	const pos = voteToPosition(voto, peso);
	return pos ? LABELS[pos] : voto === 'sim' ? 'A favor' : 'Contra';
}
