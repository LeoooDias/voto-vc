import { writable } from 'svelte/store';

export type Theme = 'claro' | 'escuro' | 'auto';

const STORAGE_KEY = 'votovc-theme';

function getInitialTheme(): Theme {
	if (typeof localStorage === 'undefined') return 'auto';
	return (localStorage.getItem(STORAGE_KEY) as Theme) || 'auto';
}

export const theme = writable<Theme>(getInitialTheme());

export function setTheme(t: Theme): void {
	theme.set(t);
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem(STORAGE_KEY, t);
	}
	applyTheme(t);
}

export function applyTheme(t: Theme): void {
	if (typeof document === 'undefined') return;
	const root = document.documentElement;
	if (t === 'auto') {
		const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
		root.setAttribute('data-theme', prefersDark ? 'escuro' : 'claro');
	} else {
		root.setAttribute('data-theme', t);
	}
}

export function initTheme(): void {
	const t = getInitialTheme();
	applyTheme(t);

	// Listen for system theme changes when on auto
	if (typeof window !== 'undefined') {
		window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
			const current = (localStorage.getItem(STORAGE_KEY) as Theme) || 'auto';
			if (current === 'auto') {
				applyTheme('auto');
			}
		});
	}
}
