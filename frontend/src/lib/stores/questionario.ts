import { writable } from 'svelte/store';
import type { QuestionarioItem, RespostaItem } from '$lib/types';
import { browser } from '$app/environment';
import { addToast } from '$lib/stores/toast';

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

export async function salvarResposta(resposta: RespostaItem): Promise<boolean> {
	try {
		const res = await fetch('/api/vote/responder', {
			method: 'POST',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(resposta)
		});
		if (!res.ok) {
			addToast('Erro ao salvar voto. Tente novamente.', 'error');
			return false;
		}
		return true;
	} catch {
		addToast('Erro de conexão ao salvar voto.', 'error');
		return false;
	}
}

export async function migrarRespostasAnonimas(): Promise<boolean> {
	if (!browser) return false;
	const raw = localStorage.getItem('voto_respostas');
	const uf = localStorage.getItem('voto_uf');
	if (!raw) return false;

	try {
		const saved: RespostaItem[] = JSON.parse(raw);
		if (saved.length === 0) return false;

		// Batch save to backend
		const res = await fetch('/api/vote/responder/batch', {
			method: 'POST',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ respostas: saved })
		});
		if (!res.ok) return false;

		// Save UF if present
		if (uf) {
			await fetch('/api/auth/me', {
				method: 'PATCH',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ uf })
			});
		}

		// Clear localStorage after successful migration
		localStorage.removeItem('voto_respostas');
		localStorage.removeItem('voto_uf');
		return true;
	} catch {
		// Migration failed — data stays in localStorage for next attempt
		return false;
	}
}

export async function carregarRespostas(): Promise<RespostaItem[]> {
	try {
		const res = await fetch('/api/vote/respostas', {
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
