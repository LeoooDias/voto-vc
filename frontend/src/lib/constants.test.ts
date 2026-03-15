import { describe, it, expect } from 'vitest';
import { UFS, UF_SIGLAS, TEMAS, getTema } from './constants';

describe('UFS', () => {
	it('has 27 items (all Brazilian states + DF)', () => {
		expect(UFS).toHaveLength(27);
	});
});

describe('UF_SIGLAS', () => {
	it('matches UFS siglas', () => {
		const expected = UFS.map((u) => u.sigla);
		expect(UF_SIGLAS).toEqual(expected);
	});

	it('contains known siglas', () => {
		expect(UF_SIGLAS).toContain('SP');
		expect(UF_SIGLAS).toContain('RJ');
		expect(UF_SIGLAS).toContain('DF');
	});
});

describe('getTema', () => {
	it('returns correct tema for a known slug', () => {
		const tema = getTema('economia');
		expect(tema.label).toBe('Economia');
		expect(tema.cor).toBe('#2563EB');
	});

	it('returns geral for unknown slug', () => {
		const tema = getTema('desconhecido');
		expect(tema).toEqual(TEMAS.geral);
	});

	it('returns geral for null', () => {
		expect(getTema(null)).toEqual(TEMAS.geral);
	});

	it('returns geral for undefined', () => {
		expect(getTema(undefined)).toEqual(TEMAS.geral);
	});
});

describe('TEMAS', () => {
	it('has all expected keys', () => {
		const expectedKeys = [
			'economia',
			'tributacao',
			'saude',
			'educacao',
			'meio-ambiente',
			'seguranca',
			'direitos-humanos',
			'trabalho',
			'agricultura',
			'defesa',
			'tecnologia',
			'corrupcao',
			'previdencia',
			'habitacao',
			'transporte',
			'cultura',
			'geral'
		];
		expect(Object.keys(TEMAS)).toEqual(expect.arrayContaining(expectedKeys));
		expect(Object.keys(TEMAS)).toHaveLength(expectedKeys.length);
	});

	it('each tema has label and cor', () => {
		for (const [, tema] of Object.entries(TEMAS)) {
			expect(tema).toHaveProperty('label');
			expect(tema).toHaveProperty('cor');
			expect(typeof tema.label).toBe('string');
			expect(tema.cor).toMatch(/^#[0-9A-Fa-f]{6}$/);
		}
	});
});
