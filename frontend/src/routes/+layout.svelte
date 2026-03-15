<script lang="ts">
	import { onMount } from 'svelte';
	import { authUser, authLoading, checkAuth, logout } from '$lib/stores/auth';
	import { initTheme } from '$lib/stores/theme';
	import { respostas, carregarRespostas } from '$lib/stores/questionario';
	import SettingsModal from '$lib/components/SettingsModal.svelte';
	import Toast from '$lib/components/Toast.svelte';

	let { children } = $props();
	let settingsOpen = $state(false);
	let respostasArr: { voto: string }[] = $state([]);
	respostas.subscribe(r => respostasArr = r);
	let perfilEnabled = $derived(respostasArr.filter(r => r.voto !== 'pular').length >= 10);

	onMount(async () => {
		initTheme();
		const user = await checkAuth();
		if (user) {
			const saved = await carregarRespostas();
			if (saved.length > 0) {
				respostas.set(saved);
			}
		}
	});
</script>

<div class="app">
	<header>
		<nav>
			<a href="/" class="logo">
				<img src="/logo-claro-sm.png" alt="voto.vc" class="logo-img logo-claro" width="190" height="80" />
				<img src="/logo-escuro-sm.png" alt="voto.vc" class="logo-img logo-escuro" width="190" height="80" />
			</a>
			<div class="nav-right">
				<div class="nav-links">
					{#if perfilEnabled}
						<a href="/parlamentares">Parlamentares</a>
						<a href="/partidos">Partidos</a>
					{:else}
						<span class="nav-disabled">Parlamentares</span>
						<span class="nav-disabled">Partidos</span>
					{/if}
					<a href="/proposicoes">Proposições</a>
					<span class="nav-sep">|</span>
					<a href="/sobre">Sobre</a>
					{#if perfilEnabled}
						<a href="/resultado" class="nav-perfil">Meu Perfil</a>
					{:else}
						<span class="nav-disabled">Meu Perfil</span>
					{/if}
					<a href="/vote" class="nav-vote">Vote</a>
				</div>
				{#if !$authLoading}
					<div class="nav-auth">
						{#if $authUser}
							<button class="nav-btn" onclick={() => logout()}>Sair</button>
						{:else}
							<a href="/login" class="nav-btn-login">Entrar</a>
						{/if}
						<button class="nav-btn-icon" onclick={() => settingsOpen = true} title="Configurações">
							<svg width="27" height="27" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd"/></svg>
						</button>
					</div>
				{/if}
			</div>
		</nav>
	</header>

	<main>
		{@render children()}
	</main>

	<footer>
		<p>voto.vc — seja representado</p>
	</footer>
</div>

<SettingsModal bind:open={settingsOpen} />
<Toast />

<style>
	:global(:root),
	:global([data-theme='claro']) {
		--bg-page: #f8f9fa;
		--bg-card: #ffffff;
		--bg-header: #ffffff;
		--bg-footer: #1a1a2e;
		--text-primary: #1a1a2e;
		--text-secondary: #6b7280;
		--text-footer: #9ca3af;
		--border: #e5e7eb;
		--border-hover: #2563eb;
		--link: #2563eb;
		--link-hover: #1d4ed8;
	}

	:global([data-theme='escuro']) {
		--bg-page: #0f1117;
		--bg-card: #1a1d2e;
		--bg-header: #151822;
		--bg-footer: #0a0c12;
		--text-primary: #e5e7eb;
		--text-secondary: #9ca3af;
		--text-footer: #6b7280;
		--border: #2d3348;
		--border-hover: #3b82f6;
		--link: #3b82f6;
		--link-hover: #60a5fa;
	}

	:global(body) {
		margin: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		color: var(--text-primary);
		background: var(--bg-page);
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

	.logo-img {
		display: block;
		height: 80px;
		width: auto;
	}

	.logo-escuro { display: none; }

	:global([data-theme='escuro']) .logo-claro { display: none; }
	:global([data-theme='escuro']) .logo-escuro { display: block; }

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
		background: #2563eb;
		color: white !important;
		border-radius: 6px;
		padding: 0.375rem 0.75rem;
	}

	.nav-vote:hover {
		background: #1d4ed8;
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
		background: #2563eb;
		color: white !important;
		text-decoration: none;
		border-radius: 6px;
		padding: 0.375rem 0.75rem;
		font-weight: 500;
	}

	.nav-btn-login:hover {
		background: #1d4ed8;
		color: white !important;
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
</style>
