<script>
	import { onMount } from 'svelte';
	import { authUser, authLoading, checkAuth, logout } from '$lib/stores/auth';

	let { children } = $props();

	onMount(() => {
		checkAuth();
	});
</script>

<div class="app">
	<header>
		<nav>
			<a href="/" class="logo"><span class="logo-flag"><span class="logo-text">voto.vc</span></span></a>
			<div class="nav-links">
				<a href="/questionario">Questionário</a>
				<a href="/sobre">Sobre</a>
				{#if !$authLoading}
					{#if $authUser}
						<span class="user-name">{$authUser.nome ?? $authUser.email}</span>
						<button class="nav-btn" onclick={() => logout()}>Sair</button>
					{:else}
						<a href="/login" class="nav-btn-login">Entrar</a>
					{/if}
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

<style>
	:global(body) {
		margin: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		color: #1a1a2e;
		background: #f8f9fa;
	}

	.app {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	header {
		background: white;
		border-bottom: 1px solid #e5e7eb;
		padding: 0 1.5rem;
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
		padding: 0.42rem 0.84rem;
		line-height: 1;
	}

	.logo-text {
		font-size: 1.96rem;
		font-weight: 800;
		color: white;
		letter-spacing: 0.03em;
		text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
	}

	.nav-links {
		display: flex;
		gap: 1.5rem;
	}

	.nav-links a {
		color: #4b5563;
		text-decoration: none;
		font-weight: 500;
	}

	.nav-links a:hover {
		color: #2563eb;
	}

	.user-name {
		color: #1a1a2e;
		font-weight: 500;
		font-size: 0.875rem;
	}

	.nav-btn {
		background: none;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		padding: 0.375rem 0.75rem;
		color: #4b5563;
		font-weight: 500;
		cursor: pointer;
		font-size: 0.875rem;
	}

	.nav-btn:hover {
		background: #f3f4f6;
	}

	.nav-btn-login {
		background: #2563eb;
		color: white !important;
		border-radius: 6px;
		padding: 0.375rem 0.75rem;
		font-size: 0.875rem;
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
		background: #1a1a2e;
		color: #9ca3af;
		text-align: center;
		padding: 1.5rem;
		font-size: 0.875rem;
	}
</style>
