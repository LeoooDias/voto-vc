import { writable } from 'svelte/store';
import type { QuestionarioItem, RespostaItem } from '$lib/types';

export const items = writable<QuestionarioItem[]>([]);
export const respostas = writable<RespostaItem[]>([]);
export const currentIndex = writable(0);
