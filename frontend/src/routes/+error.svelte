<script lang="ts">
	import { page } from '$app/state';
</script>

<svelte:head>
	<title>Página não encontrada — voto.vc</title>
</svelte:head>

<div class="error-page">
	<h1>{page.status}</h1>
	<p class="error-message">{page.error?.message ?? 'Página não encontrada'}</p>
	<div class="error-actions">
		<a href="/" class="error-link">Página inicial</a>
		<a href="/vote" class="error-cta">Comece a votar</a>
	</div>
</div>

<style>
	.error-page {
		text-align: center;
		padding: 4rem 1.5rem;
		max-width: 500px;
		margin: 0 auto;
	}

	h1 {
		font-size: 4rem;
		color: var(--text-primary);
		margin: 0 0 0.5rem;
		line-height: 1;
	}

	.error-message {
		font-size: 1.25rem;
		color: var(--text-secondary);
		margin-bottom: 2rem;
	}

	.error-actions {
		display: flex;
		gap: 1rem;
		justify-content: center;
		flex-wrap: wrap;
	}

	.error-link {
		color: var(--link);
		text-decoration: none;
		padding: 0.6rem 1.5rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		font-weight: 500;
		transition: border-color 0.2s;
	}

	.error-link:hover {
		border-color: var(--link);
	}

	.error-cta {
		background: #2563eb;
		color: white;
		padding: 0.6rem 1.5rem;
		border-radius: 8px;
		text-decoration: none;
		font-weight: 600;
		transition: background 0.2s;
	}

	.error-cta:hover {
		background: #1d4ed8;
	}
</style>
