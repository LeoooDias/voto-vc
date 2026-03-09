import { writable } from 'svelte/store';
import type { MatchResult } from '$lib/types';

export const resultados = writable<MatchResult[]>([]);
export const loading = writable(false);
