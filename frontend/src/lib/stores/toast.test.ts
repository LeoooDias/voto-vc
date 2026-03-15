import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { toasts, addToast, dismissToast } from './toast';

beforeEach(() => {
	toasts.set([]);
	vi.restoreAllMocks();
});

describe('addToast', () => {
	it('adds a toast to the store', () => {
		addToast('Hello', 'info');
		const current = get(toasts);
		expect(current).toHaveLength(1);
		expect(current[0].message).toBe('Hello');
		expect(current[0].type).toBe('info');
	});

	it('adds multiple toasts', () => {
		addToast('First', 'success');
		addToast('Second', 'error');
		const current = get(toasts);
		expect(current).toHaveLength(2);
	});
});

describe('dismissToast', () => {
	it('removes a toast by id', () => {
		addToast('To dismiss', 'info');
		const current = get(toasts);
		expect(current).toHaveLength(1);

		dismissToast(current[0].id);
		expect(get(toasts)).toHaveLength(0);
	});

	it('only removes the targeted toast', () => {
		addToast('Keep', 'info');
		addToast('Remove', 'error');
		const before = get(toasts);
		expect(before).toHaveLength(2);

		const removeId = before.find((t) => t.message === 'Remove')!.id;
		dismissToast(removeId);

		const after = get(toasts);
		expect(after).toHaveLength(1);
		expect(after[0].message).toBe('Keep');
	});
});

describe('auto-remove', () => {
	it('removes toast after duration', () => {
		vi.useFakeTimers();

		addToast('Temporary', 'info', 2000);
		expect(get(toasts)).toHaveLength(1);

		vi.advanceTimersByTime(1999);
		expect(get(toasts)).toHaveLength(1);

		vi.advanceTimersByTime(1);
		expect(get(toasts)).toHaveLength(0);

		vi.useRealTimers();
	});
});
