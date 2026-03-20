import { describe, it, expect } from 'vitest';
import { positionToVote5, voteToPosition5, positionLabel5, expandPositions } from './position';

describe('positionToVote5', () => {
	it('maps position 1 to nao/1.0', () => {
		expect(positionToVote5(1)).toEqual({ voto: 'nao', peso: 1.0 });
	});

	it('maps position 3 to sim/0.0 (Neutro)', () => {
		expect(positionToVote5(3)).toEqual({ voto: 'sim', peso: 0.0 });
	});

	it('maps position 5 to sim/1.0', () => {
		expect(positionToVote5(5)).toEqual({ voto: 'sim', peso: 1.0 });
	});
});

describe('voteToPosition5', () => {
	it('maps nao/1.0 to position 1', () => {
		expect(voteToPosition5('nao', 1.0)).toBe(1);
	});

	it('maps sim/0.0 to position 3 (Neutro)', () => {
		expect(voteToPosition5('sim', 0.0)).toBe(3);
	});

	it('maps sim/1.0 to position 5', () => {
		expect(voteToPosition5('sim', 1.0)).toBe(5);
	});

	it('returns null for pular', () => {
		expect(voteToPosition5('pular', 1.0)).toBeNull();
	});
});

describe('positionLabel5', () => {
	it('returns correct labels', () => {
		expect(positionLabel5(1)).toBe('Contra');
		expect(positionLabel5(3)).toBe('Neutro');
		expect(positionLabel5(5)).toBe('A favor');
	});
});

describe('expandPositions', () => {
	const posicoes = [
		{
			id: 1,
			slug: 'test',
			titulo: 'Test',
			descricao: 'Test desc',
			tema: 'economia',
			ordem: 1,
			proposicoes: [
				{ proposicao_id: 10, tipo: 'PL', numero: 1, ano: 2024, resumo: null, direcao: 'sim' as const },
				{ proposicao_id: 20, tipo: 'PL', numero: 2, ano: 2024, resumo: null, direcao: 'nao' as const }
			]
		}
	];

	it('expands position into per-prop respostas with P/N', () => {
		const result = expandPositions(
			[{ posicao_id: 1, voto: 'sim', peso: 1.0 }],
			posicoes,
			[]
		);
		expect(result).toHaveLength(2);
		expect(result[0]).toEqual({ proposicao_id: 10, voto: 'sim', peso: 0.5 });
		expect(result[1]).toEqual({ proposicao_id: 20, voto: 'nao', peso: 0.5 });
	});

	it('overrides take precedence', () => {
		const result = expandPositions(
			[{ posicao_id: 1, voto: 'sim', peso: 1.0 }],
			posicoes,
			[{ proposicao_id: 10, voto: 'nao', peso: 1.0 }]
		);
		const r10 = result.find((r) => r.proposicao_id === 10)!;
		expect(r10.voto).toBe('nao');
		expect(r10.peso).toBe(1.0);
	});
});
