<script lang="ts">
	import { authUser, checkAuth } from '$lib/stores/auth';
	import { theme, setTheme, type Theme } from '$lib/stores/theme';
	import { selectedUf as selectedUfStore } from '$lib/stores/questionario';
	import { UF_SIGLAS } from '$lib/constants';
	import { get } from 'svelte/store';

	let { open = $bindable(false) } = $props();
	let selectedUf = $state(get(authUser)?.uf ?? '');
	let currentTheme: Theme = $state(get(theme));
	let saving = $state(false);

	$effect(() => {
		const user = $authUser;
		if (user) {
			selectedUf = user.uf ?? '';
		}
	});

	$effect(() => {
		currentTheme = $theme;
	});

	function handleTheme(t: Theme) {
		currentTheme = t;
		setTheme(t);
	}

	async function saveUf() {
		if (!get(authUser)) return;
		saving = true;
		try {
			const res = await fetch('/api/auth/me', {
				method: 'PATCH',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ uf: selectedUf || null })
			});
			if (res.ok) {
				selectedUfStore.set(selectedUf);
				await checkAuth();
			}
		} finally {
			saving = false;
		}
	}

	function close() {
		open = false;
	}

	let modalEl: HTMLDivElement | undefined = $state();

	function handleBackdropClick() {
		close();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			close();
			return;
		}
		// Focus trap
		if (e.key === 'Tab' && modalEl) {
			const focusable = modalEl.querySelectorAll<HTMLElement>(
				'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
			);
			if (focusable.length === 0) return;
			const first = focusable[0];
			const last = focusable[focusable.length - 1];
			if (e.shiftKey) {
				if (document.activeElement === first) {
					e.preventDefault();
					last.focus();
				}
			} else {
				if (document.activeElement === last) {
					e.preventDefault();
					first.focus();
				}
			}
		}
	}

	$effect(() => {
		if (open && modalEl) {
			const focusable = modalEl.querySelectorAll<HTMLElement>(
				'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
			);
			if (focusable.length > 0) {
				focusable[0].focus();
			}
		}
	});
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<button class="backdrop" onclick={handleBackdropClick} aria-label="Fechar configurações"></button>
	<div class="modal" role="dialog" aria-modal="true" aria-labelledby="settings-title" bind:this={modalEl}>
		<div class="modal-header">
			<h2 id="settings-title">Configurações</h2>
			<button class="close-btn" onclick={close} aria-label="Fechar configurações">&times;</button>
		</div>

		<div class="setting">
			<span class="setting-label" id="settings-uf-label">Estado (UF)</span>
			{#if $authUser}
				<div class="uf-row">
					<select bind:value={selectedUf} onchange={saveUf} aria-labelledby="settings-uf-label">
						<option value="">Selecione...</option>
						{#each UF_SIGLAS as uf}
							<option value={uf}>{uf}</option>
						{/each}
					</select>
					{#if saving}
						<span class="saving">Salvando...</span>
					{/if}
				</div>
			{:else}
				<p class="hint">Entre com sua conta para salvar seu estado.</p>
			{/if}
		</div>

		<div class="setting">
			<span class="setting-label">Tema</span>
			<div class="theme-options">
				<button
					class="theme-btn"
					class:active={currentTheme === 'claro'}
					aria-pressed={currentTheme === 'claro'}
					onclick={() => handleTheme('claro')}
				>Claro</button>
				<button
					class="theme-btn"
					class:active={currentTheme === 'escuro'}
					aria-pressed={currentTheme === 'escuro'}
					onclick={() => handleTheme('escuro')}
				>Escuro</button>
				<button
					class="theme-btn"
					class:active={currentTheme === 'auto'}
					aria-pressed={currentTheme === 'auto'}
					onclick={() => handleTheme('auto')}
				>Auto</button>
			</div>
		</div>

	</div>
{/if}

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		z-index: 100;
		border: none;
		cursor: default;
		padding: 0;
		margin: 0;
		width: 100%;
		height: 100%;
	}

	.modal {
		position: fixed;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		z-index: 101;
		background: var(--bg-card);
		border-radius: 16px;
		padding: 2rem;
		width: 90%;
		max-width: 420px;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
	}

	h2 {
		margin: 0;
		font-size: 1.25rem;
		color: var(--text-primary);
	}

	.close-btn {
		background: none;
		border: none;
		font-size: 1.5rem;
		cursor: pointer;
		color: var(--text-secondary);
		padding: 0;
		line-height: 1;
	}

	.setting {
		margin-bottom: 1.5rem;
	}

	.setting-label {
		display: block;
		font-weight: 600;
		margin-bottom: 0.5rem;
		color: var(--text-primary);
		font-size: 0.938rem;
	}

	.uf-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	select {
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-card);
		color: var(--text-primary);
		font-size: 0.938rem;
		cursor: pointer;
	}

	.saving {
		color: var(--text-secondary);
		font-size: 0.813rem;
	}

	.hint {
		color: var(--text-secondary);
		font-size: 0.875rem;
		margin: 0;
	}

	.theme-options {
		display: flex;
		gap: 0.5rem;
	}

	.theme-btn {
		flex: 1;
		padding: 0.5rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-page);
		color: var(--text-primary);
		font-weight: 500;
		cursor: pointer;
		font-size: 0.875rem;
		transition: border-color 0.15s, background 0.15s;
	}

	.theme-btn:hover {
		border-color: var(--link);
	}

	.theme-btn.active {
		background: var(--link);
		color: white;
		border-color: var(--link);
	}

</style>
