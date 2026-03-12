import { writable } from 'svelte/store';
import type { MatchResult, PartidoMatchResult } from '$lib/types';

export const resultados = writable<MatchResult[]>([]);
export const resultadosPartidos = writable<PartidoMatchResult[]>([]);
export const loading = writable(false);
