import { writable } from 'svelte/store';
import type { PosicaoItem, RespostaPosicaoItem } from '$lib/types/posicao';
import type { RespostaItem } from '$lib/types';
import { browser } from '$app/environment';

function loadFromStorage<T>(key: string, fallback: T): T {
	if (!browser) return fallback;
	try {
		const raw = localStorage.getItem(key);
		if (raw) return JSON.parse(raw);
	} catch {
		/* ignore */
	}
	return fallback;
}

export const posicaoItems = writable<PosicaoItem[]>([]);
export const respostasPosicoes = writable<RespostaPosicaoItem[]>(
	loadFromStorage('voto_posicao_respostas', [])
);
export const overridesPosicoes = writable<RespostaItem[]>(
	loadFromStorage('voto_posicao_overrides', [])
);

// Persist to localStorage on changes
if (browser) {
	respostasPosicoes.subscribe((v) =>
		localStorage.setItem('voto_posicao_respostas', JSON.stringify(v))
	);
	overridesPosicoes.subscribe((v) =>
		localStorage.setItem('voto_posicao_overrides', JSON.stringify(v))
	);
}
