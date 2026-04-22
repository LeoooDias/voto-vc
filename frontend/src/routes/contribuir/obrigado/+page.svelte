<script lang="ts">
	import { onMount } from 'svelte';
	import { _ } from 'svelte-i18n';
	import { page } from '$app/stores';
	import { api, ApiError } from '$lib/api';

	type Status = 'verificando' | 'paid' | 'pending' | 'expired' | 'erro';

	let status: Status = $state('verificando');
	let amountBrl = $state<number | null>(null);

	onMount(async () => {
		const sessionId = $page.url.searchParams.get('session_id');
		if (!sessionId) {
			status = 'erro';
			return;
		}
		try {
			const res = await api.get<{ status: string; amount_brl: number | null }>(
				`/contribuir/session/${encodeURIComponent(sessionId)}`
			);
			amountBrl = res.amount_brl;
			if (res.status === 'paid') status = 'paid';
			else if (res.status === 'pending') status = 'pending';
			else if (res.status === 'expired') status = 'expired';
			else status = 'pending';
		} catch (e) {
			if (e instanceof ApiError && e.status === 404) {
				status = 'erro';
			} else {
				status = 'erro';
			}
		}
	});

	let valorFormatado = $derived(
		amountBrl != null ? amountBrl.toFixed(2).replace('.', ',') : null
	);
</script>

<svelte:head>
	<title>{$_('contribuir.obrigadoTitle')}</title>
</svelte:head>

<div class="obrigado">
	<p class="eyebrow">voto.vc</p>
	<h1>{$_('contribuir.obrigadoH1')}</h1>

	<div class="status-card" class:status-paid={status === 'paid'}>
		{#if status === 'verificando'}
			<p class="status-msg">{$_('contribuir.obrigadoVerificando')}</p>
		{:else if status === 'paid'}
			<p class="status-msg">{$_('contribuir.obrigadoPago')}</p>
			{#if valorFormatado}
				<p class="status-valor">{$_('contribuir.obrigadoValor', { values: { valor: valorFormatado } })}</p>
			{/if}
		{:else if status === 'pending'}
			<p class="status-msg">{$_('contribuir.obrigadoPendente')}</p>
		{:else if status === 'expired'}
			<p class="status-msg">{$_('contribuir.obrigadoExpirado')}</p>
		{:else}
			<p class="status-msg">{$_('contribuir.obrigadoErro')}</p>
		{/if}
	</div>

	<div class="actions">
		<a class="btn-primary" href="/">{$_('contribuir.obrigadoVoltar')}</a>
		<a class="btn-secondary" href="/contribuir">{$_('contribuir.obrigadoNovaDoacao')}</a>
	</div>
</div>

<style>
	.obrigado {
		max-width: 640px;
		margin: 0 auto;
		text-align: center;
	}

	.eyebrow {
		font-family: var(--font-heading);
		font-size: 0.625rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.25em;
		color: var(--text-secondary);
		margin: 0 0 0.75rem;
	}

	h1 {
		color: var(--text-primary);
		font-family: var(--font-heading);
		font-size: 2.5rem;
		font-weight: 900;
		letter-spacing: -0.04em;
		margin: 0 0 2.5rem;
	}

	.status-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		padding: 2.5rem 2rem;
		margin-bottom: 2rem;
		text-align: left;
	}

	.status-paid {
		border-color: var(--color-favor);
	}

	.status-msg {
		color: var(--text-primary);
		font-size: 1rem;
		line-height: 1.7;
		margin: 0;
	}

	.status-valor {
		color: var(--text-secondary);
		font-family: var(--font-heading);
		font-weight: 700;
		font-size: 0.875rem;
		letter-spacing: -0.01em;
		margin: 1rem 0 0;
	}

	.actions {
		display: flex;
		gap: 0.75rem;
		justify-content: center;
		flex-wrap: wrap;
	}

	.btn-primary,
	.btn-secondary {
		display: inline-block;
		padding: 0.875rem 1.5rem;
		font-family: var(--font-heading);
		font-size: 0.813rem;
		font-weight: 800;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		text-decoration: none;
		border-radius: 0;
		transition: opacity 0.15s, background 0.15s, color 0.15s;
	}

	.btn-primary {
		background: var(--text-primary);
		color: var(--bg-page);
		border: 2px solid var(--text-primary);
	}

	.btn-primary:hover {
		opacity: 0.85;
	}

	.btn-secondary {
		background: transparent;
		color: var(--text-primary);
		border: 2px solid var(--border);
	}

	.btn-secondary:hover {
		border-color: var(--text-primary);
	}

	@media (max-width: 560px) {
		h1 {
			font-size: 2rem;
		}

		.status-card {
			padding: 2rem 1.5rem;
		}

		.actions {
			flex-direction: column;
		}

		.btn-primary,
		.btn-secondary {
			width: 100%;
			box-sizing: border-box;
		}
	}
</style>
