<script lang="ts">
	import { onMount } from 'svelte';
	import { authUser, authLoading, checkAuth, logout } from '$lib/stores/auth';
	import { initTheme } from '$lib/stores/theme';
	import { respostas, carregarRespostas } from '$lib/stores/questionario';
	import { respostasPosicoes, carregarRespostasPosicoes } from '$lib/stores/posicoes';
	import SettingsModal from '$lib/components/SettingsModal.svelte';
	import Toast from '$lib/components/Toast.svelte';

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

	onMount(async () => {
		initTheme();
		const user = await checkAuth();
		if (user) {
			const saved = await carregarRespostas();
			if (saved.length > 0) {
				respostas.set(saved);
			}
			const savedPos = await carregarRespostasPosicoes();
			if (savedPos.length > 0) {
				respostasPosicoes.set(savedPos);
			}
		}
	});
</script>

<div class="app">
	<header>
		<nav>
			<a href="/" class="logo" aria-label="voto.vc">
				<span class="logo-text"><span class="logo-voto">voto</span><span class="logo-dot">.</span><span class="logo-vc">vc</span></span>
			</a>

			<button class="hamburger" onclick={() => menuOpen = !menuOpen} aria-label="Menu">
				{#if menuOpen}
					<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
				{:else}
					<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
				{/if}
			</button>

			<div class="nav-right" class:nav-open={menuOpen}>
				<div class="nav-links">
					{#if perfilEnabled}
						<a href="/parlamentares" onclick={closeMenu}>Parlamentares</a>
						<a href="/partidos" onclick={closeMenu}>Partidos</a>
					{:else}
						<span class="nav-disabled" title="Responda ao menos 10 proposições para desbloquear" aria-disabled="true" role="link">Parlamentares</span>
						<span class="nav-disabled" title="Responda ao menos 10 proposições para desbloquear" aria-disabled="true" role="link">Partidos</span>
					{/if}
					<span class="nav-sep">|</span>
					<a href="/sobre" onclick={closeMenu}>Sobre</a>
					{#if perfilEnabled}
						<a href="/perfil" class="nav-perfil" onclick={closeMenu}>Meu Perfil</a>
					{:else}
						<span class="nav-disabled" title="Responda ao menos 10 proposições para desbloquear" aria-disabled="true" role="link">Meu Perfil</span>
					{/if}
					<a href="/vote" class="nav-vote" onclick={closeMenu}>Vote</a>
				</div>
				{#if !$authLoading}
					<div class="nav-auth">
						{#if $authUser}
							<button class="nav-btn" onclick={() => { logout(); closeMenu(); }}>Sair</button>
						{:else}
							<a href="/login" class="nav-btn-login" onclick={closeMenu}>Entrar</a>
						{/if}
						<button class="nav-btn-icon" onclick={() => { settingsOpen = true; closeMenu(); }} title="Configurações" aria-label="Abrir configurações">
							<svg width="27" height="27" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd"/></svg>
						</button>
					</div>
				{/if}
			</div>
		</nav>
	</header>

	{#if menuOpen}
		<button class="menu-overlay" onclick={closeMenu} aria-label="Fechar menu"></button>
	{/if}

	<main>
		{@render children()}
	</main>

	<footer>
		<div class="footer-links">
			<a href="/sobre">Sobre</a>
			<span class="footer-sep">·</span>
			<a href="/proposicoes">Proposições</a>
			<span class="footer-sep">·</span>
			<a href="/vote">Vote</a>
		</div>
		<p>voto.vc — seja representado</p>
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
		--border-hover: #1d4ed8;
		--link: #1d4ed8;
		--link-hover: #1e40af;
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
		--border-hover: #3b82f6;
		--link: #3b82f6;
		--link-hover: #60a5fa;
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

	:global(body) {
		margin: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		color: var(--text-primary);
		background: var(--bg-page);
	}

	:global(h1), :global(h2), :global(h3) {
		font-family: var(--font-heading);
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
	}

	header {
		background: var(--bg-header);
		border-bottom: 1px solid var(--border);
		padding: 0 1.5rem;
		position: sticky;
		top: 0;
		z-index: 50;
	}

	nav {
		max-width: 1200px;
		margin: 0 auto;
		display: flex;
		align-items: center;
		justify-content: space-between;
		height: 90px;
	}

	.logo {
		text-decoration: none;
		display: flex;
		align-items: center;
	}

	.logo-text {
		font-family: var(--font-heading);
		font-size: 2rem;
		font-weight: 800;
		letter-spacing: -0.03em;
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
		align-items: center;
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
	}

	.nav-links a:hover {
		color: var(--link);
	}

	.nav-vote {
		background: var(--accent);
		color: white !important;
		border-radius: 6px;
		padding: 0.375rem 0.875rem;
		font-weight: 700;
		font-family: var(--font-heading);
		letter-spacing: -0.01em;
	}

	.nav-vote:hover {
		background: var(--accent-hover);
		color: white !important;
	}

	.nav-perfil {
		color: var(--link) !important;
		font-weight: 600 !important;
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

	.nav-btn {
		background: none;
		border: 1px solid var(--border);
		border-radius: 6px;
		padding: 0.375rem 0.75rem;
		color: var(--text-secondary);
		font-weight: 500;
		cursor: pointer;
		font-size: inherit;
	}

	.nav-btn:hover {
		background: var(--bg-page);
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

	.nav-btn-login {
		background: var(--link);
		color: white !important;
		text-decoration: none;
		border-radius: 6px;
		padding: 0.375rem 0.75rem;
		font-weight: 500;
	}

	.nav-btn-login:hover {
		background: var(--link-hover);
		color: white !important;
	}

	/* Menu overlay — only visible on mobile when menu is open */
	.menu-overlay {
		display: none;
	}

	main {
		flex: 1;
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem 1.5rem;
		width: 100%;
		box-sizing: border-box;
	}

	footer {
		background: var(--bg-footer);
		color: var(--text-footer);
		text-align: center;
		padding: 1.5rem;
		font-size: 0.875rem;
	}

	.footer-links {
		display: flex;
		justify-content: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.footer-links a {
		color: var(--text-footer);
		text-decoration: none;
		font-size: 0.813rem;
	}

	.footer-links a:hover {
		color: var(--text-footer-hover);
		text-decoration: underline;
	}

	.footer-sep {
		color: var(--text-footer);
		opacity: 0.5;
		font-size: 0.813rem;
	}

	.footer-company {
		margin: 0.25rem 0 0;
		font-size: 0.75rem;
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
			height: 70px;
		}

		.logo-text {
			font-size: 1.625rem;
		}

		.hamburger {
			display: flex;
			align-items: center;
		}

		.nav-right {
			display: none;
			position: absolute;
			top: 70px;
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
			top: 70px;
			background: rgba(0, 0, 0, 0.3);
			z-index: 49;
			border: none;
			cursor: default;
		}
	}
</style>
