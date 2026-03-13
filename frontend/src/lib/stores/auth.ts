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

export async function checkAuth(): Promise<AuthUser | null> {
	try {
		const res = await fetch('/api/auth/me', { credentials: 'include' });
		if (res.ok) {
			const user: AuthUser = await res.json();
			authUser.set(user);
			return user;
		} else {
			authUser.set(null);
			return null;
		}
	} catch {
		authUser.set(null);
		return null;
	} finally {
		authLoading.set(false);
	}
}

export async function logout(): Promise<void> {
	await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
	authUser.set(null);
}
