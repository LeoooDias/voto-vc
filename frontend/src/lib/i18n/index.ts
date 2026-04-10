import { register, init, getLocaleFromNavigator } from 'svelte-i18n';

const STORAGE_KEY = 'votovc-locale';

register('pt-BR', () => import('./pt-BR.json'));
register('en', () => import('./en.json'));

export type Locale = 'pt-BR' | 'en';

export function getStoredLocale(): Locale {
	if (typeof localStorage === 'undefined') return 'pt-BR';
	return (localStorage.getItem(STORAGE_KEY) as Locale) || 'pt-BR';
}

export function setStoredLocale(locale: Locale): void {
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem(STORAGE_KEY, locale);
	}
}

/** Returns the current locale for API `lang` query params. */
export function getLang(): string {
	return getStoredLocale();
}

export function initI18n(): void {
	// Check URL ?lang= parameter
	if (typeof window !== 'undefined') {
		const params = new URLSearchParams(window.location.search);
		const lang = params.get('lang')?.toUpperCase();
		if (lang === 'EN') {
			setStoredLocale('en');
		} else if (lang === 'PT') {
			setStoredLocale('pt-BR');
		}
	}

	const stored = getStoredLocale();
	init({
		fallbackLocale: 'pt-BR',
		initialLocale: stored
	});
}
