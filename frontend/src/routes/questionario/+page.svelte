<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { items, respostas, currentIndex } from '$lib/stores/questionario';
	import type { QuestionarioItem, RespostaItem } from '$lib/types';
	import { goto } from '$app/navigation';

	let loaded = $state(false);
	let currentItems: QuestionarioItem[] = $state([]);
	let idx = $state(0);

	onMount(async () => {
		try {
			const data = await api.get<QuestionarioItem[]>('/questionario/items');
			items.set(data);
			currentItems = data;
			loaded = true;
		} catch (e) {
			console.error('Failed to load questionnaire:', e);
		}
	});

	items.subscribe((v) => (currentItems = v));
	currentIndex.subscribe((v) => (idx = v));

	function votar(voto: 'sim' | 'nao' | 'pular') {
		if (!currentItems[idx]) return;

		const resposta: RespostaItem = {
			proposicao_id: currentItems[idx].proposicao_id,
			voto,
			peso: 1.0
		};

		respostas.update((r) => [...r, resposta]);

		if (idx + 1 >= currentItems.length) {
			goto('/resultado');
		} else {
			currentIndex.set(idx + 1);
		}
	}

	$effect(() => {
		// Keep idx in sync
	});
</script>

<svelte:head>
	<title>Questionário — voto.vc</title>
</svelte:head>

{#if !loaded}
	<div class="loading">Carregando proposições...</div>
{:else if currentItems.length === 0}
	<div class="empty">Nenhuma proposição disponível no momento.</div>
{:else}
	<div class="questionario">
		<div class="progress">
			<div class="progress-bar" style="width: {((idx + 1) / currentItems.length) * 100}%"></div>
		</div>
		<p class="counter">{idx + 1} de {currentItems.length}</p>

		<div class="card">
			<div class="card-header">
				<span class="tipo">{currentItems[idx].tipo} {currentItems[idx].numero}/{currentItems[idx].ano}</span>
			</div>
			<p class="resumo">{currentItems[idx].resumo}</p>
			{#if currentItems[idx].ementa_simplificada}
				<p class="ementa">{currentItems[idx].ementa_simplificada}</p>
			{/if}
		</div>

		<div class="actions">
			<button class="btn nao" onclick={() => votar('nao')}>Contra</button>
			<button class="btn pular" onclick={() => votar('pular')}>Pular</button>
			<button class="btn sim" onclick={() => votar('sim')}>A favor</button>
		</div>
	</div>
{/if}

<style>
	.questionario {
		max-width: 600px;
		margin: 0 auto;
	}

	.progress {
		background: #e5e7eb;
		border-radius: 4px;
		height: 6px;
		overflow: hidden;
	}

	.progress-bar {
		background: #2563eb;
		height: 100%;
		transition: width 0.3s ease;
	}

	.counter {
		text-align: center;
		color: #9ca3af;
		font-size: 0.875rem;
		margin: 0.5rem 0 1.5rem;
	}

	.card {
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 16px;
		padding: 2rem;
		min-height: 200px;
		display: flex;
		flex-direction: column;
		justify-content: center;
	}

	.card-header {
		margin-bottom: 1rem;
	}

	.tipo {
		background: #eff6ff;
		color: #2563eb;
		padding: 0.25rem 0.75rem;
		border-radius: 20px;
		font-size: 0.8rem;
		font-weight: 600;
	}

	.resumo {
		font-size: 1.25rem;
		line-height: 1.6;
		color: #1a1a2e;
		margin: 0;
	}

	.ementa {
		color: #6b7280;
		font-size: 0.9rem;
		margin-top: 1rem;
		line-height: 1.5;
	}

	.actions {
		display: flex;
		gap: 1rem;
		margin-top: 1.5rem;
		justify-content: center;
	}

	.btn {
		padding: 0.875rem 2rem;
		border: none;
		border-radius: 12px;
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
		transition: transform 0.1s, opacity 0.2s;
	}

	.btn:hover {
		transform: scale(1.05);
	}

	.btn:active {
		transform: scale(0.95);
	}

	.sim {
		background: #16a34a;
		color: white;
	}

	.nao {
		background: #dc2626;
		color: white;
	}

	.pular {
		background: #e5e7eb;
		color: #6b7280;
	}

	.loading,
	.empty {
		text-align: center;
		padding: 4rem;
		color: #6b7280;
		font-size: 1.125rem;
	}
</style>
