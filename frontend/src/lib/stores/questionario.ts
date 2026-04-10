import { writable } from 'svelte/store';
import type { QuestionarioItem, RespostaItem } from '$lib/types';
import { browser } from '$app/environment';

function loadFromStorage<T>(key: string, fallback: T): T {
	if (!browser) return fallback;
	try {
		const raw = localStorage.getItem(key);
		if (raw) return JSON.parse(raw);
	} catch { /* ignore */ }
	return fallback;
}

export const items = writable<QuestionarioItem[]>([]);
export const respostas = writable<RespostaItem[]>(loadFromStorage('voto_respostas', []));
export const currentIndex = writable(0);
export const selectedUf = writable<string>(loadFromStorage('voto_uf', ''));

// Persist to localStorage on changes
if (browser) {
	respostas.subscribe((v) => localStorage.setItem('voto_respostas', JSON.stringify(v)));
	selectedUf.subscribe((v) => localStorage.setItem('voto_uf', v));
}
