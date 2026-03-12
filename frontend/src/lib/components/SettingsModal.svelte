<script lang="ts">
	import { authUser, checkAuth } from '$lib/stores/auth';
	import { theme, setTheme, type Theme } from '$lib/stores/theme';
	import { get } from 'svelte/store';

	let { open = $bindable(false) } = $props();

	const UFS = [
		'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS',
		'MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'
	];

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
				await checkAuth();
			}
		} finally {
			saving = false;
		}
	}

	function close() {
		open = false;
	}

	function handleBackdrop(e: MouseEvent) {
		if (e.target === e.currentTarget) close();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') close();
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="backdrop" onclick={handleBackdrop}>
		<div class="modal">
			<div class="modal-header">
				<h2>Configurações</h2>
				<button class="close-btn" onclick={close}>&times;</button>
			</div>

			<div class="setting">
				<span class="setting-label">Estado (UF)</span>
				{#if $authUser}
					<div class="uf-row">
						<select bind:value={selectedUf} onchange={saveUf}>
							<option value="">Selecione...</option>
							{#each UFS as uf}
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
						onclick={() => handleTheme('claro')}
					>Claro</button>
					<button
						class="theme-btn"
						class:active={currentTheme === 'escuro'}
						onclick={() => handleTheme('escuro')}
					>Escuro</button>
					<button
						class="theme-btn"
						class:active={currentTheme === 'auto'}
						onclick={() => handleTheme('auto')}
					>Auto</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
	}

	.modal {
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
		border-color: #2563eb;
	}

	.theme-btn.active {
		background: #2563eb;
		color: white;
		border-color: #2563eb;
	}
</style>
