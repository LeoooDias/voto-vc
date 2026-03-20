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

export async function salvarRespostaPosicao(resposta: RespostaPosicaoItem): Promise<void> {
	try {
		await fetch('/api/posicoes/responder', {
			method: 'POST',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(resposta)
		});
	} catch {
		// Silently fail — resposta já está no store local
	}
}

export async function migrarPosicaoRespostasAnonimas(): Promise<boolean> {
	if (!browser) return false;
	const raw = localStorage.getItem('voto_posicao_respostas');
	if (!raw) return false;

	try {
		const saved: RespostaPosicaoItem[] = JSON.parse(raw);
		if (saved.length === 0) return false;

		const res = await fetch('/api/posicoes/responder/batch', {
			method: 'POST',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ respostas: saved })
		});
		if (!res.ok) return false;

		localStorage.removeItem('voto_posicao_respostas');
		localStorage.removeItem('voto_posicao_overrides');
		return true;
	} catch {
		return false;
	}
}

export async function carregarRespostasPosicoes(): Promise<RespostaPosicaoItem[]> {
	try {
		const res = await fetch('/api/posicoes/respostas', {
			credentials: 'include'
		});
		if (res.ok) {
			return await res.json();
		}
	} catch {
		// Not logged in or error
	}
	return [];
}
