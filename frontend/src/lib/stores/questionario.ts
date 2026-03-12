import { writable } from 'svelte/store';
import type { QuestionarioItem, RespostaItem } from '$lib/types';

export const items = writable<QuestionarioItem[]>([]);
export const respostas = writable<RespostaItem[]>([]);
export const currentIndex = writable(0);
export const selectedUf = writable<string>('');

export async function salvarResposta(resposta: RespostaItem): Promise<void> {
	try {
		await fetch('/api/questionario/responder', {
			method: 'POST',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(resposta)
		});
	} catch {
		// Silently fail — resposta já está no store local
	}
}

export async function carregarRespostas(): Promise<RespostaItem[]> {
	try {
		const res = await fetch('/api/questionario/respostas', {
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
