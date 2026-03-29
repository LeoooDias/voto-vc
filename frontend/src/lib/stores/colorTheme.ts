import { writable } from 'svelte/store';

export type ColorTheme = 'padrao' | 'canarinho' | 'oceano' | 'lavanda' | 'rosa' | 'alto-contraste';

export const COLOR_THEMES: { id: ColorTheme; label: string; colors: [string, string, string] }[] = [
	{ id: 'padrao', label: 'Padrão', colors: ['#d97706', '#b45309', '#fef3c7'] },
	{ id: 'canarinho', label: 'Canarinho', colors: ['#009c3b', '#ffdf00', '#002776'] },
	{ id: 'oceano', label: 'Oceano', colors: ['#0284c7', '#0369a1', '#bae6fd'] },
	{ id: 'lavanda', label: 'Lavanda', colors: ['#7c3aed', '#6d28d9', '#ede9fe'] },
	{ id: 'rosa', label: 'Rosa', colors: ['#db2777', '#be185d', '#fce7f3'] },
	{ id: 'alto-contraste', label: 'Alto Contraste', colors: ['#000000', '#ffff00', '#ffffff'] }
];

const STORAGE_KEY = 'votovc-color-theme';

function getInitialColorTheme(): ColorTheme {
	if (typeof localStorage === 'undefined') return 'padrao';
	return (localStorage.getItem(STORAGE_KEY) as ColorTheme) || 'padrao';
}

export const colorTheme = writable<ColorTheme>(getInitialColorTheme());

export function setColorTheme(t: ColorTheme): void {
	colorTheme.set(t);
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem(STORAGE_KEY, t);
	}
	applyColorTheme(t);
}

export function applyColorTheme(t: ColorTheme): void {
	if (typeof document === 'undefined') return;
	document.documentElement.setAttribute('data-color-theme', t);
}

export function initColorTheme(): void {
	applyColorTheme(getInitialColorTheme());
}
