import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiError, api } from './api';

// Mock the toast store to avoid side effects
vi.mock('$lib/stores/toast', () => ({
	addToast: vi.fn()
}));

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

beforeEach(() => {
	mockFetch.mockReset();
});

describe('ApiError', () => {
	it('has status, message, and requestId', () => {
		const err = new ApiError(404, 'Not found', 'req-123');
		expect(err).toBeInstanceOf(Error);
		expect(err.status).toBe(404);
		expect(err.message).toBe('Not found');
		expect(err.requestId).toBe('req-123');
	});

	it('defaults requestId to null', () => {
		const err = new ApiError(500, 'Server error');
		expect(err.requestId).toBeNull();
	});
});

describe('api.get', () => {
	it('returns parsed JSON on success', async () => {
		const data = { items: [1, 2, 3] };
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(data),
			headers: new Headers()
		});

		const result = await api.get('/test');
		expect(result).toEqual(data);
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/test',
			expect.objectContaining({
				credentials: 'include',
				headers: expect.objectContaining({
					'Content-Type': 'application/json'
				})
			})
		);
	});

	it('throws ApiError on error response', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: false,
			status: 422,
			json: () => Promise.resolve({ erro: 'Dados inválidos' }),
			headers: new Headers({ 'x-request-id': 'req-abc' })
		});

		await expect(api.get('/fail')).rejects.toThrow(ApiError);
		try {
			await api.get('/fail');
		} catch {
			// second call also mocked - just verifying the first throw
		}
	});

	it('includes request id from response headers in ApiError', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: false,
			status: 500,
			json: () => Promise.resolve({}),
			headers: new Headers({ 'x-request-id': 'req-xyz' })
		});

		try {
			await api.get('/error');
			expect.unreachable('Should have thrown');
		} catch (e) {
			expect(e).toBeInstanceOf(ApiError);
			expect((e as ApiError).requestId).toBe('req-xyz');
		}
	});
});

describe('api.post', () => {
	it('sends JSON body with POST method', async () => {
		const responseData = { id: 1 };
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: () => Promise.resolve(responseData),
			headers: new Headers()
		});

		const result = await api.post('/items', { name: 'test' });
		expect(result).toEqual(responseData);
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/items',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ name: 'test' })
			})
		);
	});
});
