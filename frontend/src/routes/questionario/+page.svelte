<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { items, respostas, currentIndex } from '$lib/stores/questionario';
	import type { QuestionarioItem, RespostaItem } from '$lib/types';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';

	const MIN_RESPOSTAS = 10;
	const META_RESPOSTAS = 20;

	let loaded = $state(false);
	let currentItems: QuestionarioItem[] = $state([]);
	let idx = $state(0);
	let answeredCount = $state(0);
	let canFinish = $derived(answeredCount >= MIN_RESPOSTAS);
	let reachedMeta = $derived(answeredCount >= META_RESPOSTAS);

	onMount(async () => {
		try {
			const data = await api.get<QuestionarioItem[]>('/questionario/items?n_items=50');
			items.set(data);
			currentItems = data;
			// Restore progress if returning
			const existing = get(respostas);
			answeredCount = existing.filter((r) => r.voto !== 'pular').length;
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
		if (voto !== 'pular') {
			answeredCount++;
		}

		if (idx + 1 >= currentItems.length) {
			goto('/resultado');
		} else {
			currentIndex.set(idx + 1);
		}
	}

	function verResultado() {
		goto('/resultado');
	}

	const temaInfo: Record<string, { label: string; cor: string }> = {
		economia: { label: 'Economia', cor: '#2563EB' },
		tributacao: { label: 'Tributação', cor: '#7C3AED' },
		saude: { label: 'Saúde', cor: '#DC2626' },
		educacao: { label: 'Educação', cor: '#EA580C' },
		'meio-ambiente': { label: 'Meio Ambiente', cor: '#16A34A' },
		seguranca: { label: 'Segurança', cor: '#475569' },
		'direitos-humanos': { label: 'Direitos Humanos', cor: '#DB2777' },
		trabalho: { label: 'Trabalho', cor: '#CA8A04' },
		agricultura: { label: 'Agricultura', cor: '#65A30D' },
		defesa: { label: 'Defesa', cor: '#0F766E' },
		tecnologia: { label: 'Tecnologia', cor: '#6366F1' },
		corrupcao: { label: 'Transparência', cor: '#B91C1C' },
		previdencia: { label: 'Previdência', cor: '#78716C' },
		habitacao: { label: 'Habitação', cor: '#0891B2' },
		transporte: { label: 'Transporte', cor: '#F59E0B' },
		cultura: { label: 'Cultura', cor: '#A855F7' },
		geral: { label: 'Legislação', cor: '#6B7280' }
	};
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
		<div class="counter-row">
			<p class="counter">{idx + 1} de {currentItems.length}</p>
			<p class="answered">
				{answeredCount} respondida{answeredCount !== 1 ? 's' : ''}
				{#if !canFinish}
					<span class="hint">· mínimo {MIN_RESPOSTAS}</span>
				{/if}
			</p>
		</div>

		{#if reachedMeta && !canFinish}
			<!-- shouldn't happen but just in case -->
		{:else if reachedMeta}
			<div class="meta-banner success">
				Excelente! Você já respondeu {answeredCount} proposições. Seu perfil está bem definido.
				<button class="btn-resultado" onclick={verResultado}>Ver meu resultado</button>
			</div>
		{:else if canFinish}
			<div class="meta-banner ready">
				Já dá pra ver seu perfil! Mas quanto mais você responder, mais preciso fica.
				<button class="btn-resultado" onclick={verResultado}>Ver resultado parcial</button>
			</div>
		{/if}

		<div class="card">
			<div class="card-header">
				<span class="tipo">{currentItems[idx].tipo} {currentItems[idx].numero}/{currentItems[idx].ano}</span>
				{#if temaInfo[currentItems[idx].tema]}
					<span class="tema-tag" style="background: {temaInfo[currentItems[idx].tema].cor}1a; color: {temaInfo[currentItems[idx].tema].cor}; border-color: {temaInfo[currentItems[idx].tema].cor}33">{temaInfo[currentItems[idx].tema].label}</span>
				{:else}
					<span class="tema-tag" style="background: {temaInfo.geral.cor}1a; color: {temaInfo.geral.cor}; border-color: {temaInfo.geral.cor}33">{temaInfo.geral.label}</span>
				{/if}
			</div>
			<p class="resumo">{currentItems[idx].resumo}</p>
			{#if currentItems[idx].descricao_detalhada}
				<p class="descricao">{currentItems[idx].descricao_detalhada}</p>
			{/if}
			<div class="links">
				{#if currentItems[idx].url_camara}
					<a href={currentItems[idx].url_camara} target="_blank" rel="noopener" class="link-camara">Ver na Câmara</a>
				{/if}
			</div>
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

	.counter-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin: 0.5rem 0 1rem;
	}

	.counter {
		color: #9ca3af;
		font-size: 0.875rem;
		margin: 0;
	}

	.answered {
		color: #6b7280;
		font-size: 0.875rem;
		font-weight: 600;
		margin: 0;
	}

	.hint {
		color: #9ca3af;
		font-weight: 400;
	}

	.meta-banner {
		border-radius: 12px;
		padding: 1rem 1.25rem;
		margin-bottom: 1rem;
		font-size: 0.9rem;
		line-height: 1.5;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.75rem;
		text-align: center;
	}

	.meta-banner.ready {
		background: #fef9c3;
		color: #854d0e;
		border: 1px solid #fde68a;
	}

	.meta-banner.success {
		background: #dcfce7;
		color: #166534;
		border: 1px solid #bbf7d0;
	}

	.btn-resultado {
		background: #2563eb;
		color: white;
		border: none;
		padding: 0.5rem 1.5rem;
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.9rem;
		cursor: pointer;
		transition: background 0.2s;
	}

	.btn-resultado:hover {
		background: #1d4ed8;
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

	.card-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.tipo {
		background: #eff6ff;
		color: #2563eb;
		padding: 0.25rem 0.75rem;
		border-radius: 20px;
		font-size: 0.8rem;
		font-weight: 600;
	}

	.tema-tag {
		padding: 0.2rem 0.6rem;
		border-radius: 20px;
		font-size: 0.75rem;
		font-weight: 600;
		border: 1px solid;
	}

	.resumo {
		font-size: 1.25rem;
		line-height: 1.6;
		color: #1a1a2e;
		margin: 0;
	}

	.descricao {
		color: #374151;
		font-size: 0.95rem;
		margin-top: 1rem;
		line-height: 1.6;
	}

	.links {
		display: flex;
		gap: 1rem;
		margin-top: 0.75rem;
	}

	.link-camara {
		color: #2563eb;
		font-size: 0.8rem;
		text-decoration: none;
	}

	.link-camara:hover {
		text-decoration: underline;
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
