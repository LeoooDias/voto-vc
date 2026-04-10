<script lang="ts">
	import { _, locale } from 'svelte-i18n';
	import { getStoredLocale, setStoredLocale, type Locale } from '$lib/i18n';
	import { theme, setTheme, type Theme } from '$lib/stores/theme';
	import { colorTheme, setColorTheme, COLOR_THEMES, type ColorTheme } from '$lib/stores/colorTheme';

	const COLOR_THEME_KEYS: Record<ColorTheme, string> = {
		'padrao': 'colorTheme.padrao',
		'canarinho': 'colorTheme.canarinho',
		'oceano': 'colorTheme.oceano',
		'lavanda': 'colorTheme.lavanda',
		'rosa': 'colorTheme.rosa',
		'alto-contraste': 'colorTheme.altoContraste',
	};
	import { selectedUf as selectedUfStore } from '$lib/stores/questionario';
	import { UF_SIGLAS } from '$lib/constants';
	import { get } from 'svelte/store';

	let { open = $bindable(false) } = $props();
	let selectedUf = $state(get(selectedUfStore));
	let currentTheme: Theme = $state(get(theme));
	let currentColorTheme: ColorTheme = $state(get(colorTheme));
	let currentLocale: Locale = $state(getStoredLocale());

	$effect(() => {
		currentTheme = $theme;
	});

	$effect(() => {
		currentColorTheme = $colorTheme;
	});

	function handleTheme(t: Theme) {
		currentTheme = t;
		setTheme(t);
	}

	function handleColorTheme(t: ColorTheme) {
		currentColorTheme = t;
		setColorTheme(t);
	}

	function handleLocale(l: Locale) {
		currentLocale = l;
		setStoredLocale(l);
		locale.set(l);
	}

	function saveUf() {
		selectedUfStore.set(selectedUf);
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
	<button class="backdrop" onclick={handleBackdropClick} aria-label={$_('nav.fecharConfiguracoes')}></button>
	<div class="modal" role="dialog" aria-modal="true" aria-labelledby="settings-title" bind:this={modalEl}>
		<div class="modal-header">
			<h2 id="settings-title">{$_('settings.titulo')}</h2>
			<button class="close-btn" onclick={close} aria-label={$_('nav.fecharConfiguracoes')}>&times;</button>
		</div>

		<div class="setting">
			<span class="setting-label" id="settings-uf-label">{$_('settings.estado')}</span>
			<div class="uf-row">
				<select bind:value={selectedUf} onchange={saveUf} aria-labelledby="settings-uf-label">
					<option value="">{$_('settings.selecione')}</option>
					{#each UF_SIGLAS as uf}
						<option value={uf}>{uf}</option>
					{/each}
				</select>
			</div>
		</div>

		<div class="setting">
			<span class="setting-label">{$_('settings.modo')}</span>
			<div class="theme-options">
				<button
					class="theme-btn"
					class:active={currentTheme === 'claro'}
					aria-pressed={currentTheme === 'claro'}
					onclick={() => handleTheme('claro')}
				>{$_('settings.claro')}</button>
				<button
					class="theme-btn"
					class:active={currentTheme === 'escuro'}
					aria-pressed={currentTheme === 'escuro'}
					onclick={() => handleTheme('escuro')}
				>{$_('settings.escuro')}</button>
				<button
					class="theme-btn"
					class:active={currentTheme === 'auto'}
					aria-pressed={currentTheme === 'auto'}
					onclick={() => handleTheme('auto')}
				>{$_('settings.auto')}</button>
			</div>
		</div>

		<div class="setting">
			<span class="setting-label">{$_('settings.tema')}</span>
			<div class="color-theme-grid">
				{#each COLOR_THEMES as ct}
					<button
						class="color-theme-btn"
						class:active={currentColorTheme === ct.id}
						aria-pressed={currentColorTheme === ct.id}
						onclick={() => handleColorTheme(ct.id)}
						title={$_(COLOR_THEME_KEYS[ct.id])}
					>
						<span class="color-swatches">
							<span class="swatch" style="background:{ct.colors[0]}"></span>
							<span class="swatch" style="background:{ct.colors[1]}"></span>
							<span class="swatch" style="background:{ct.colors[2]}"></span>
						</span>
						<span class="color-theme-label">{$_(COLOR_THEME_KEYS[ct.id])}</span>
					</button>
				{/each}
			</div>
		</div>

		<div class="setting">
			<span class="setting-label">{$_('settings.idioma')}</span>
			<div class="theme-options">
				<button
					class="theme-btn"
					class:active={currentLocale === 'pt-BR'}
					aria-pressed={currentLocale === 'pt-BR'}
					onclick={() => handleLocale('pt-BR')}
				>{$_('settings.portugues')}</button>
				<button
					class="theme-btn"
					class:active={currentLocale === 'en'}
					aria-pressed={currentLocale === 'en'}
					onclick={() => handleLocale('en')}
				>{$_('settings.english')}</button>
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
		border-radius: 0;
		padding: 2.5rem;
		width: 90%;
		max-width: 420px;
		box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
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

	.theme-options {
		display: flex;
		gap: 0.5rem;
	}

	.theme-btn {
		flex: 1;
		padding: 0.5rem;
		border: 1.5px solid var(--border);
		border-radius: 0;
		background: transparent;
		color: var(--text-primary);
		font-weight: 600;
		cursor: pointer;
		font-size: 0.813rem;
		transition: border-color 0.15s, background 0.15s;
	}

	.theme-btn:hover {
		border-color: var(--text-primary);
	}

	.theme-btn.active {
		background: var(--text-primary);
		color: var(--bg-page);
		border-color: var(--text-primary);
	}

	.color-theme-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.5rem;
	}

	.color-theme-btn {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.375rem;
		padding: 0.5rem 0.25rem;
		border: 1.5px solid var(--border);
		border-radius: 0;
		background: transparent;
		cursor: pointer;
		transition: border-color 0.15s, background 0.15s;
	}

	.color-theme-btn:hover {
		border-color: var(--text-primary);
	}

	.color-theme-btn.active {
		border-color: var(--text-primary);
		background: var(--accent-bg);
	}

	.color-swatches {
		display: flex;
		gap: 3px;
	}

	.swatch {
		width: 16px;
		height: 16px;
		border-radius: 50%;
		border: 1px solid rgba(0, 0, 0, 0.15);
	}

	.color-theme-label {
		font-size: 0.75rem;
		font-weight: 500;
		color: var(--text-primary);
		line-height: 1.2;
	}

</style>
