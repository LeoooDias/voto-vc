<script lang="ts">
	import { onMount } from 'svelte';
	import { _, isLoading as i18nLoading } from 'svelte-i18n';
	import { initI18n } from '$lib/i18n';
	import { initTheme } from '$lib/stores/theme';
	import { initColorTheme } from '$lib/stores/colorTheme';
	import { respostas } from '$lib/stores/questionario';
	import { respostasPosicoes } from '$lib/stores/posicoes';
	import SettingsModal from '$lib/components/SettingsModal.svelte';
	import Toast from '$lib/components/Toast.svelte';

	initI18n();

	let { children } = $props();
	let settingsOpen = $state(false);
	let menuOpen = $state(false);
	let respostasArr: { voto: string }[] = $state([]);
	let posRespostasArr: { voto: string }[] = $state([]);
	respostas.subscribe(r => respostasArr = r);
	respostasPosicoes.subscribe(r => posRespostasArr = r);
	let directVotes = $derived(respostasArr.filter(r => r.voto !== 'pular').length);
	let posVotes = $derived(posRespostasArr.filter(r => r.voto !== 'pular').length);
	let perfilEnabled = $derived(directVotes >= 10 || posVotes >= 10);

	function closeMenu() {
		menuOpen = false;
	}

	onMount(() => {
		initTheme();
		initColorTheme();
	});
</script>

<div class="app">
	<header>
		<nav>
			<a href="/" class="logo" aria-label="voto.vc">
				<span class="logo-text"><span class="logo-voto">voto</span><span class="logo-dot">.</span><span class="logo-vc">vc</span></span>
			</a>

			<button class="hamburger" onclick={() => menuOpen = !menuOpen} aria-label={$_('nav.menu')}>
				{#if menuOpen}
					<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
				{:else}
					<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
				{/if}
			</button>

			<div class="nav-right" class:nav-open={menuOpen}>
				<div class="nav-links">
					{#if perfilEnabled}
						<a href="/parlamentares" onclick={closeMenu}>{$_('nav.parlamentares')}</a>
						<a href="/partidos" onclick={closeMenu}>{$_('nav.partidos')}</a>
					{:else}
						<span class="nav-disabled" title={$_('nav.desbloquear')} aria-disabled="true" role="link">{$_('nav.parlamentares')}</span>
						<span class="nav-disabled" title={$_('nav.desbloquear')} aria-disabled="true" role="link">{$_('nav.partidos')}</span>
					{/if}
					<span class="nav-sep">|</span>
					<a href="/sobre" onclick={closeMenu}>{$_('nav.sobre')}</a>
					{#if perfilEnabled}
						<a href="/perfil" class="nav-perfil" onclick={closeMenu}>{$_('nav.meuPerfil')}</a>
					{:else}
						<span class="nav-disabled" title={$_('nav.desbloquear')} aria-disabled="true" role="link">{$_('nav.meuPerfil')}</span>
					{/if}
					<a href="/vote" class="nav-vote" onclick={closeMenu}>{$_('nav.vote')}</a>
				</div>
					<div class="nav-auth">
						<button class="nav-btn-icon" onclick={() => { settingsOpen = true; closeMenu(); }} title={$_('nav.configuracoes')} aria-label={$_('nav.abrirConfiguracoes')}>
							<svg width="27" height="27" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd"/></svg>
						</button>
					</div>
			</div>
		</nav>
	</header>

	{#if menuOpen}
		<button class="menu-overlay" onclick={closeMenu} aria-label={$_('nav.fecharMenu')}></button>
	{/if}

	<main>
		{@render children()}
	</main>

	<footer>
		<p>{$_('footer.slogan')}</p>
		<p class="footer-links"><a href="/privacidade">{$_('footer.privacidade')}</a></p>
		<p class="footer-company"><a href="https://clearworks.ca" target="_blank" rel="noopener noreferrer">© 2026 ClearWorks Foundry Inc.</a></p>
	</footer>
</div>

<SettingsModal bind:open={settingsOpen} />
<Toast />

<style>
	:global(:root),
	:global([data-theme='claro']) {
		--bg-page: #f6f5f1;
		--bg-card: #ffffff;
		--bg-header: #ffffff;
		--bg-footer: #1a1a2e;
		--text-primary: #1a1a2e;
		--text-secondary: #64748b;
		--text-footer: #9ca3af;
		--text-footer-hover: #d1d5db;
		--border: #e2e0d8;
		--border-hover: #d97706;
		--link: #b45309;
		--link-hover: #92400e;
		--accent: #d97706;
		--accent-hover: #b45309;
		--accent-bg: #fef3c7;
		--color-contra: #dc2626;
		--color-contra-leve: #f87171;
		--color-neutro: #a3a3a3;
		--color-neutro-dark: #737373;
		--color-favor-leve: #4ade80;
		--color-favor: #16a34a;
		--color-warning: #ea580c;
		--color-code-bg: rgba(0, 0, 0, 0.08);
		--font-heading: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
	}

	:global([data-theme='escuro']) {
		--bg-page: #0d0f14;
		--bg-card: #181b28;
		--bg-header: #131620;
		--bg-footer: #0a0c12;
		--text-primary: #e5e7eb;
		--text-secondary: #94a3b8;
		--text-footer: #6b7280;
		--text-footer-hover: #e5e7eb;
		--border: #2a2f42;
		--border-hover: #f59e0b;
		--link: #f59e0b;
		--link-hover: #fbbf24;
		--accent: #f59e0b;
		--accent-hover: #d97706;
		--accent-bg: #78350f;
		--color-contra: #ef4444;
		--color-contra-leve: #f87171;
		--color-neutro: #a3a3a3;
		--color-neutro-dark: #9ca3af;
		--color-favor-leve: #4ade80;
		--color-favor: #22c55e;
		--color-warning: #f97316;
		--color-code-bg: rgba(255, 255, 255, 0.08);
		--font-heading: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
	}

	/* ---- Color Themes (accent overrides) ---- */

	/* Canarinho — claro */
	:global([data-color-theme='canarinho'][data-theme='claro']),
	:global([data-color-theme='canarinho'] [data-theme='claro']) {
		--accent: #009c3b;
		--accent-hover: #007a2e;
		--accent-bg: #d4edda;
		--link: #006b27;
		--link-hover: #004d1c;
		--border-hover: #009c3b;
	}
	:global([data-color-theme='canarinho'][data-theme='claro']) .logo-vc,
	:global([data-color-theme='canarinho'] [data-theme='claro']) .logo-vc {
		color: #009c3b;
	}

	/* Canarinho — escuro */
	:global([data-color-theme='canarinho'][data-theme='escuro']),
	:global([data-color-theme='canarinho'] [data-theme='escuro']) {
		--accent: #2dd665;
		--accent-hover: #009c3b;
		--accent-bg: #0a3d1a;
		--link: #2dd665;
		--link-hover: #5eed8a;
		--border-hover: #2dd665;
	}
	:global([data-color-theme='canarinho'][data-theme='escuro']) .logo-vc,
	:global([data-color-theme='canarinho'] [data-theme='escuro']) .logo-vc {
		color: #2dd665;
	}

	/* Canarinho — special accents: nav-vote uses blue */
	:global([data-color-theme='canarinho']) :global(.nav-vote) {
		background: #1a4fc9 !important;
		color: white !important;
	}
	:global([data-color-theme='canarinho']) :global(.nav-vote:hover) {
		background: #1a4fc9 !important;
		opacity: 0.8;
	}

	/* Oceano — claro */
	:global([data-color-theme='oceano'][data-theme='claro']),
	:global([data-color-theme='oceano'] [data-theme='claro']) {
		--accent: #0284c7;
		--accent-hover: #0369a1;
		--accent-bg: #e0f2fe;
		--link: #0369a1;
		--link-hover: #075985;
		--border-hover: #0284c7;
	}

	/* Oceano — escuro */
	:global([data-color-theme='oceano'][data-theme='escuro']),
	:global([data-color-theme='oceano'] [data-theme='escuro']) {
		--accent: #38bdf8;
		--accent-hover: #0284c7;
		--accent-bg: #0c4a6e;
		--link: #38bdf8;
		--link-hover: #7dd3fc;
		--border-hover: #38bdf8;
	}

	/* Lavanda — claro */
	:global([data-color-theme='lavanda'][data-theme='claro']),
	:global([data-color-theme='lavanda'] [data-theme='claro']) {
		--accent: #7c3aed;
		--accent-hover: #6d28d9;
		--accent-bg: #ede9fe;
		--link: #6d28d9;
		--link-hover: #5b21b6;
		--border-hover: #7c3aed;
	}

	/* Lavanda — escuro */
	:global([data-color-theme='lavanda'][data-theme='escuro']),
	:global([data-color-theme='lavanda'] [data-theme='escuro']) {
		--accent: #a78bfa;
		--accent-hover: #7c3aed;
		--accent-bg: #3b0764;
		--link: #a78bfa;
		--link-hover: #c4b5fd;
		--border-hover: #a78bfa;
	}

	/* Rosa — claro */
	:global([data-color-theme='rosa'][data-theme='claro']),
	:global([data-color-theme='rosa'] [data-theme='claro']) {
		--accent: #db2777;
		--accent-hover: #be185d;
		--accent-bg: #fce7f3;
		--link: #be185d;
		--link-hover: #9d174d;
		--border-hover: #db2777;
	}

	/* Rosa — escuro */
	:global([data-color-theme='rosa'][data-theme='escuro']),
	:global([data-color-theme='rosa'] [data-theme='escuro']) {
		--accent: #f472b6;
		--accent-hover: #db2777;
		--accent-bg: #831843;
		--link: #f472b6;
		--link-hover: #f9a8d4;
		--border-hover: #f472b6;
	}

	/* Alto Contraste — claro */
	:global([data-color-theme='alto-contraste'][data-theme='claro']),
	:global([data-color-theme='alto-contraste'] [data-theme='claro']) {
		--bg-page: #ffffff;
		--bg-card: #ffffff;
		--bg-header: #ffffff;
		--text-primary: #000000;
		--text-secondary: #1a1a1a;
		--border: #000000;
		--border-hover: #0000ff;
		--accent: #0000cc;
		--accent-hover: #000099;
		--accent-bg: #ffffcc;
		--link: #0000cc;
		--link-hover: #000099;
		--color-contra: #cc0000;
		--color-contra-leve: #ee0000;
		--color-favor: #006600;
		--color-favor-leve: #009900;
	}

	/* Alto Contraste — escuro */
	:global([data-color-theme='alto-contraste'][data-theme='escuro']),
	:global([data-color-theme='alto-contraste'] [data-theme='escuro']) {
		--bg-page: #000000;
		--bg-card: #0a0a0a;
		--bg-header: #000000;
		--bg-footer: #000000;
		--text-primary: #ffffff;
		--text-secondary: #e0e0e0;
		--text-footer: #cccccc;
		--text-footer-hover: #ffffff;
		--border: #ffffff;
		--border-hover: #ffff00;
		--accent: #ffff00;
		--accent-hover: #cccc00;
		--accent-bg: #333300;
		--link: #ffff00;
		--link-hover: #ffff66;
		--color-contra: #ff4444;
		--color-contra-leve: #ff6666;
		--color-favor: #44ff44;
		--color-favor-leve: #66ff66;
		--color-code-bg: rgba(255, 255, 255, 0.15);
	}

	:global(body) {
		margin: 0;
		font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		color: var(--text-primary);
		background: var(--bg-footer);
		font-weight: 400;
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
	}

	:global(h1), :global(h2), :global(h3) {
		font-family: var(--font-heading);
	}

	:global(h1) {
		letter-spacing: -0.04em;
	}

	@media (prefers-reduced-motion: reduce) {
		:global(*) {
			animation-duration: 0.01ms !important;
			animation-iteration-count: 1 !important;
			transition-duration: 0.01ms !important;
		}
	}

	:global(:focus-visible) {
		outline: 2px solid var(--link);
		outline-offset: 2px;
	}

	:global(input:focus-visible),
	:global(select:focus-visible),
	:global(textarea:focus-visible) {
		outline: none;
		border-color: var(--link);
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--link) 25%, transparent);
	}

	.app {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		background: var(--bg-page);
	}

	header {
		background: var(--bg-header);
		border-bottom: 1px solid var(--border);
		padding: 0 2rem;
		position: sticky;
		top: 0;
		z-index: 50;
	}

	nav {
		max-width: 1200px;
		margin: 0 auto;
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		padding: 0.75rem 0;
	}

	.logo {
		text-decoration: none;
		display: flex;
		align-items: center;
	}

	.logo-text {
		font-family: var(--font-heading);
		font-size: 2.25rem;
		font-weight: 900;
		letter-spacing: -0.05em;
		line-height: 1;
	}

	.logo-voto {
		color: var(--text-primary);
	}

	.logo-dot {
		color: #a3a3a3;
	}

	.logo-vc {
		color: #d97706;
	}

	:global([data-theme='escuro']) .logo-vc {
		color: #f59e0b;
	}

	/* Logo color per color theme */
	:global([data-color-theme='oceano'][data-theme='claro']) .logo-vc { color: #0284c7; }
	:global([data-color-theme='oceano'][data-theme='escuro']) .logo-vc { color: #38bdf8; }
	:global([data-color-theme='lavanda'][data-theme='claro']) .logo-vc { color: #7c3aed; }
	:global([data-color-theme='lavanda'][data-theme='escuro']) .logo-vc { color: #a78bfa; }
	:global([data-color-theme='rosa'][data-theme='claro']) .logo-vc { color: #db2777; }
	:global([data-color-theme='rosa'][data-theme='escuro']) .logo-vc { color: #f472b6; }
	:global([data-color-theme='alto-contraste'][data-theme='claro']) .logo-vc { color: #0000cc; }
	:global([data-color-theme='alto-contraste'][data-theme='escuro']) .logo-vc { color: #ffff00; }

	/* Hamburger button — hidden on desktop */
	.hamburger {
		display: none;
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 6px;
	}

	.hamburger:hover {
		background: var(--bg-page);
		color: var(--text-primary);
	}

	.nav-right {
		display: flex;
		align-items: baseline;
		gap: 2rem;
	}

	.nav-links {
		display: flex;
		align-items: center;
		gap: 1.5rem;
	}

	.nav-links a {
		color: var(--text-secondary);
		text-decoration: none;
		font-weight: 500;
		font-size: 0.875rem;
		letter-spacing: -0.01em;
		transition: color 0.15s;
	}

	.nav-links a:hover {
		color: var(--text-primary);
	}

	.nav-vote {
		background: var(--text-primary);
		color: var(--bg-page) !important;
		border-radius: 0;
		padding: 0.5rem 1.25rem;
		font-weight: 800;
		font-family: var(--font-heading);
		letter-spacing: -0.02em;
		font-size: 0.813rem;
		text-transform: uppercase;
		transition: opacity 0.15s;
	}

	.nav-vote:hover {
		background: var(--text-primary);
		color: var(--bg-page) !important;
		opacity: 0.8;
	}

	.nav-perfil {
		color: var(--text-primary) !important;
		font-weight: 700 !important;
	}

	.nav-sep {
		color: var(--border);
		font-weight: 300;
		user-select: none;
	}

	.nav-auth {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding-left: 1.25rem;
		border-left: 1px solid var(--border);
	}

	.nav-btn-icon {
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 0.375rem;
		border-radius: 6px;
		display: flex;
		align-items: center;
		min-width: 44px;
		min-height: 44px;
		justify-content: center;
	}

	.nav-btn-icon:hover {
		background: var(--bg-page);
		color: var(--text-primary);
	}

	.nav-disabled {
		color: var(--border);
		font-weight: 500;
		cursor: default;
	}

	/* Menu overlay — only visible on mobile when menu is open */
	.menu-overlay {
		display: none;
	}

	main {
		flex: 1;
		max-width: 1200px;
		margin: 0 auto;
		padding: 3rem 2rem;
		width: 100%;
		box-sizing: border-box;
	}

	footer {
		background: var(--bg-footer);
		color: var(--text-footer);
		text-align: center;
		padding: 3rem 2rem;
		font-size: 0.75rem;
		letter-spacing: 0.05em;
		text-transform: uppercase;
		font-weight: 500;
	}

	footer p {
		margin: 0;
	}

.footer-links {
		margin: 0.5rem 0 0;
		font-size: 0.75rem;
	}

	.footer-links a {
		color: var(--text-footer);
		text-decoration: none;
	}

	.footer-links a:hover {
		color: var(--text-footer-hover);
		text-decoration: underline;
	}

	.footer-company {
		margin: 0.5rem 0 0;
		font-size: 0.688rem;
		letter-spacing: 0.08em;
	}

	.footer-company a {
		color: var(--text-footer);
		text-decoration: none;
	}

	.footer-company a:hover {
		color: var(--text-footer-hover);
		text-decoration: underline;
	}

	/* ---- Mobile ---- */
	@media (max-width: 768px) {
		nav {
			padding: 0.375rem 0;
		}

		.logo-text {
			font-size: 1.875rem;
		}

		.hamburger {
			display: flex;
			align-items: center;
		}

		.nav-right {
			display: none;
			position: absolute;
			top: 100%;
			left: 0;
			right: 0;
			background: var(--bg-header);
			border-bottom: 1px solid var(--border);
			flex-direction: column;
			padding: 1rem 1.5rem;
			gap: 0;
			z-index: 100;
			box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		}

		.nav-right.nav-open {
			display: flex;
		}

		.nav-links {
			flex-direction: column;
			align-items: stretch;
			gap: 0;
			width: 100%;
		}

		.nav-links a,
		.nav-links .nav-disabled {
			padding: 0.75rem 0;
			border-bottom: 1px solid var(--border);
			font-size: 1rem;
		}

		.nav-links .nav-vote {
			text-align: center;
			margin-top: 0.5rem;
			border-bottom: none;
			padding: 0.625rem 0;
		}

		.nav-sep {
			display: none;
		}

		.nav-auth {
			padding-left: 0;
			border-left: none;
			border-top: 1px solid var(--border);
			padding-top: 0.75rem;
			margin-top: 0.5rem;
			width: 100%;
			justify-content: space-between;
		}

		.menu-overlay {
			display: block;
			position: fixed;
			inset: 0;
			background: rgba(0, 0, 0, 0.3);
			z-index: 49;
			border: none;
			cursor: default;
		}
	}
</style>
