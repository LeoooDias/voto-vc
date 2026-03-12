import { writable } from 'svelte/store';

export interface AuthUser {
	id: string;
	email: string | null;
	nome: string | null;
	uf: string | null;
	provedor_auth: string;
}

export const authUser = writable<AuthUser | null>(null);
export const authLoading = writable(true);

export async function checkAuth(): Promise<void> {
	try {
		const res = await fetch('/api/auth/me', { credentials: 'include' });
		if (res.ok) {
			authUser.set(await res.json());
		} else {
			authUser.set(null);
		}
	} catch {
		authUser.set(null);
	} finally {
		authLoading.set(false);
	}
}

export async function logout(): Promise<void> {
	await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
	authUser.set(null);
}
