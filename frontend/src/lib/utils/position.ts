/**
 * Maps between the 5-position stance slider and voto/peso values.
 *
 * Position 1: Contra       (nao, 1.0)
 * Position 2: Contra leve  (nao, 0.5)
 * Position 3: Neutro       (sim, 0.0)
 * Position 4: A favor leve (sim, 0.5)
 * Position 5: A favor      (sim, 1.0)
 */

import type { RespostaItem } from '$lib/types';
import type { PosicaoItem, RespostaPosicaoItem } from '$lib/types/posicao';

const POSITION5_MAP: Array<{ voto: 'sim' | 'nao'; peso: number }> = [
	{ voto: 'nao', peso: 1.0 }, // pos 1: Contra
	{ voto: 'nao', peso: 0.5 }, // pos 2: Contra leve
	{ voto: 'sim', peso: 0.0 }, // pos 3: Neutro
	{ voto: 'sim', peso: 0.5 }, // pos 4: A favor leve
	{ voto: 'sim', peso: 1.0 } // pos 5: A favor
];

export function positionToVote5(pos: number): { voto: 'sim' | 'nao'; peso: number } {
	return POSITION5_MAP[pos - 1] ?? POSITION5_MAP[2]; // default Neutro
}

export function voteToPosition5(voto: string, peso: number): number | null {
	if (voto === 'pular') return null;
	if (peso === 0) return 3; // Neutro
	for (let i = 0; i < POSITION5_MAP.length; i++) {
		const m = POSITION5_MAP[i];
		if (m.voto === voto && Math.abs(m.peso - peso) < 0.01) {
			return i + 1;
		}
	}
	// Fallback approximate
	if (voto === 'nao') return peso >= 0.75 ? 1 : 2;
	return peso >= 0.75 ? 5 : 4;
}

export function positionLabel5(pos: number): string {
	const labels: Record<number, string> = {
		1: 'Contra',
		2: 'Contra leve',
		3: 'Neutro',
		4: 'A favor leve',
		5: 'A favor'
	};
	return labels[pos] ?? 'Neutro';
}

/**
 * Expand position-level respostas into per-proposition respostas (client-side mirror).
 */
export function expandPositions(
	posicaoRespostas: RespostaPosicaoItem[],
	posicoes: PosicaoItem[],
	overrides: RespostaItem[]
): RespostaItem[] {
	const posicaoMap = new Map(posicoes.map((p) => [p.id, p]));
	const overrideMap = new Map(overrides.map((r) => [r.proposicao_id, r]));
	const result: RespostaItem[] = [];
	const seen = new Set<number>();

	for (const pr of posicaoRespostas) {
		const pos = posicaoMap.get(pr.posicao_id);
		if (!pos) continue;

		const n = pos.proposicoes.length;
		if (n === 0) continue;
		const pesoPorProp = pr.peso;

		for (const pp of pos.proposicoes) {
			const propId = pp.proposicao_id;

			if (overrideMap.has(propId)) {
				if (!seen.has(propId)) {
					seen.add(propId);
					result.push(overrideMap.get(propId)!);
				}
				continue;
			}

			if (seen.has(propId)) continue;
			seen.add(propId);

			if (pr.voto === 'pular') {
				result.push({ proposicao_id: propId, voto: 'pular', peso: pesoPorProp });
				continue;
			}

			let propVoto: 'sim' | 'nao';
			if (pr.voto === 'sim') {
				propVoto = pp.direcao === 'sim' ? 'sim' : 'nao';
			} else {
				propVoto = pp.direcao === 'sim' ? 'nao' : 'sim';
			}

			result.push({ proposicao_id: propId, voto: propVoto, peso: pesoPorProp });
		}
	}

	return result;
}

/**
 * Converts a user's position response (voto + peso) into stance + score_pct,
 * using the same scale as parlamentar/partido inference.
 */
export function userResponseToStance(voto: string, peso: number): { stance: string; score_pct: number } {
	if (voto === 'pular') return { stance: 'sem_dados', score_pct: 0 };

	// Map voto+peso to a 0-100 score (favor %)
	let score_pct: number;
	if (voto === 'sim') {
		if (peso === 0) score_pct = 50;       // Neutro
		else if (peso <= 0.5) score_pct = 75;  // A favor leve
		else score_pct = 100;                   // A favor
	} else {
		if (peso <= 0.5) score_pct = 25;       // Contra leve
		else score_pct = 0;                     // Contra
	}

	let stance: string;
	if (score_pct > 75) stance = 'fortemente_favor';
	else if (score_pct > 50) stance = 'levemente_favor';
	else if (score_pct === 50) stance = 'misto';
	else if (score_pct > 25) stance = 'levemente_contra';
	else stance = 'fortemente_contra';

	return { stance, score_pct };
}

export function stanceLabel(stance: string): string {
	const labels: Record<string, string> = {
		fortemente_favor: 'Fortemente a favor',
		levemente_favor: 'Levemente a favor',
		misto: 'Misto',
		levemente_contra: 'Levemente contra',
		fortemente_contra: 'Fortemente contra',
		sem_dados: 'Sem dados'
	};
	return labels[stance] ?? stance;
}

export function stanceColor(stance: string): string {
	const colors: Record<string, string> = {
		fortemente_favor: '#16a34a',
		levemente_favor: '#4ade80',
		misto: '#a3a3a3',
		levemente_contra: '#f87171',
		fortemente_contra: '#dc2626',
		sem_dados: '#d4d4d4'
	};
	return colors[stance] ?? '#a3a3a3';
}
