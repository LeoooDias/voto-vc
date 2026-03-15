import { addToast } from '$lib/stores/toast';

const BASE = '/api';

export class ApiError extends Error {
	status: number;
	requestId: string | null;

	constructor(status: number, message: string, requestId: string | null = null) {
		super(message);
		this.status = status;
		this.requestId = requestId;
	}
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
	const res = await fetch(`${BASE}${path}`, {
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json',
			...options?.headers
		},
		...options
	});

	if (!res.ok) {
		const requestId = res.headers.get('x-request-id');
		let message = `Erro ${res.status}`;

		try {
			const body = await res.json();
			if (body.erro) message = body.erro;
		} catch {
			// response body não é JSON
		}

		if (res.status === 429) {
			addToast('Muitas requisições. Aguarde um momento.', 'warning');
		} else if (res.status >= 500) {
			addToast('Erro no servidor. Tente novamente.', 'error');
		}

		throw new ApiError(res.status, message, requestId);
	}

	return res.json();
}

export const api = {
	get: <T>(path: string) => request<T>(path),
	post: <T>(path: string, body: unknown) =>
		request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
	patch: <T>(path: string, body: unknown) =>
		request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
	delete: <T>(path: string) => request<T>(path, { method: 'DELETE' })
};
