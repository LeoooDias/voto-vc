<script>
	import { onMount } from 'svelte';
	import { authUser, authLoading, checkAuth, logout } from '$lib/stores/auth';
	import { initTheme } from '$lib/stores/theme';
	import SettingsModal from '$lib/components/SettingsModal.svelte';

	let { children } = $props();
	let settingsOpen = $state(false);

	onMount(() => {
		initTheme();
		checkAuth();
	});
</script>

<div class="app">
	<header>
		<nav>
			<a href="/" class="logo"><span class="logo-flag"><span class="logo-text">voto.vc</span></span></a>
			<div class="nav-right">
				<div class="nav-links">
					<a href="/questionario">Questionário</a>
					<a href="/sobre">Sobre</a>
				</div>
				{#if !$authLoading}
					<div class="nav-auth">
						{#if $authUser}
							<span class="user-name">{$authUser.nome ?? $authUser.email}</span>
							<button class="nav-btn" onclick={() => settingsOpen = true}>Config</button>
							<button class="nav-btn" onclick={() => logout()}>Sair</button>
						{:else}
							<button class="nav-btn" onclick={() => settingsOpen = true}>Config</button>
							<a href="/login" class="nav-btn-login">Entrar</a>
						{/if}
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
		height: 60px;
	}

	.logo {
		text-decoration: none;
		display: flex;
		align-items: center;
	}

	.logo-flag {
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(to right, #009C3B 33.33%, #FFDF00 33.33%, #FFDF00 66.66%, #002776 66.66%);
		border-radius: 4px;
		padding: 0.2rem 0.5rem;
		line-height: 1;
	}

	.logo-text {
		font-size: 2.2rem;
		font-weight: 800;
		color: white;
		letter-spacing: 0.03em;
		text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
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

	.nav-auth {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding-left: 1.25rem;
		border-left: 1px solid var(--border);
	}

	.user-name {
		color: var(--text-secondary);
		font-weight: 500;
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
