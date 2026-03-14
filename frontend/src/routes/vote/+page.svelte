<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import {
		items,
		respostas,
		currentIndex,
		selectedUf,
		salvarResposta,
		carregarRespostas
	} from '$lib/stores/questionario';
	import { authUser, authLoading } from '$lib/stores/auth';
	import type { QuestionarioItem, RespostaItem } from '$lib/types';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';

	const TIER1 = 10;
	const TIER2 = 25;
	const TIER3 = 50;

	const UFS = [
		{ sigla: 'AC', nome: 'Acre' },
		{ sigla: 'AL', nome: 'Alagoas' },
		{ sigla: 'AP', nome: 'Amapá' },
		{ sigla: 'AM', nome: 'Amazonas' },
		{ sigla: 'BA', nome: 'Bahia' },
		{ sigla: 'CE', nome: 'Ceará' },
		{ sigla: 'DF', nome: 'Distrito Federal' },
		{ sigla: 'ES', nome: 'Espírito Santo' },
		{ sigla: 'GO', nome: 'Goiás' },
		{ sigla: 'MA', nome: 'Maranhão' },
		{ sigla: 'MT', nome: 'Mato Grosso' },
		{ sigla: 'MS', nome: 'Mato Grosso do Sul' },
		{ sigla: 'MG', nome: 'Minas Gerais' },
		{ sigla: 'PA', nome: 'Pará' },
		{ sigla: 'PB', nome: 'Paraíba' },
		{ sigla: 'PR', nome: 'Paraná' },
		{ sigla: 'PE', nome: 'Pernambuco' },
		{ sigla: 'PI', nome: 'Piauí' },
		{ sigla: 'RJ', nome: 'Rio de Janeiro' },
		{ sigla: 'RN', nome: 'Rio Grande do Norte' },
		{ sigla: 'RS', nome: 'Rio Grande do Sul' },
		{ sigla: 'RO', nome: 'Rondônia' },
		{ sigla: 'RR', nome: 'Roraima' },
		{ sigla: 'SC', nome: 'Santa Catarina' },
		{ sigla: 'SP', nome: 'São Paulo' },
		{ sigla: 'SE', nome: 'Sergipe' },
		{ sigla: 'TO', nome: 'Tocantins' }
	];

	let uf = $state(get(selectedUf));
	let loaded = $state(false);
	let currentItems: QuestionarioItem[] = $state([]);
	let idx = $state(0);
	let answeredCount = $state(0);
	let canFinish = $derived(answeredCount >= TIER1);
	let reachedTier2 = $derived(answeredCount >= TIER2);
	let reachedTier3 = $derived(answeredCount >= TIER3);

	// Progress segments: each tier fills 1/3 of the bar
	let seg1 = $derived(Math.min(answeredCount / TIER1, 1) * 33.33);
	let seg2 = $derived(answeredCount > TIER1 ? Math.min((answeredCount - TIER1) / (TIER2 - TIER1), 1) * 33.33 : 0);
	let seg3 = $derived(answeredCount > TIER2 ? Math.min((answeredCount - TIER2) / (TIER3 - TIER2), 1) * 33.34 : 0);

	let tierLabel = $derived(
		reachedTier3 ? 'Expert' :
		reachedTier2 ? 'Avançado' :
		canFinish ? 'Básico' : ''
	);

	function escolherUf(sigla: string) {
		uf = sigla;
		selectedUf.set(sigla);
		loadQuestions();

		// Persistir UF no perfil se logado
		if (get(authUser)) {
			fetch('/api/auth/me', {
				method: 'PATCH',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ uf: sigla })
			});
		}
	}

	async function loadQuestions() {
		try {
			const data = await api.get<QuestionarioItem[]>('/vote/items?n_items=50');

			// Se logado, carregar respostas salvas do DB
			const user = get(authUser);
			if (user) {
				const saved = await carregarRespostas();
				if (saved.length > 0) {
					respostas.set(saved);
					const answeredIds = new Set(saved.map((r) => r.proposicao_id));
					const remaining = data.filter((q) => !answeredIds.has(q.proposicao_id));
					items.set(remaining);
					currentItems = remaining;
					currentIndex.set(0);
					answeredCount = saved.filter((r) => r.voto !== 'pular').length;
					loaded = true;
					return;
				}
			}

			items.set(data);
			currentItems = data;
			const existing = get(respostas);
			answeredCount = existing.filter((r) => r.voto !== 'pular').length;
			loaded = true;
		} catch (e) {
			console.error('Failed to load questionnaire:', e);
		}
	}

	async function initPage() {
		if (!uf) {
			const user = get(authUser);
			if (user?.uf) {
				uf = user.uf;
				selectedUf.set(user.uf);
			}
		}
		if (uf) {
			await loadQuestions();
		}
	}

	onMount(() => {
		// Se auth já resolveu, iniciar direto
		if (!get(authLoading)) {
			initPage();
			return;
		}
		// Senão, esperar auth resolver
		const unsub = authLoading.subscribe((loading) => {
			if (!loading) {
				unsub();
				initPage();
			}
		});
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

		// Salvar no backend se logado (fire-and-forget)
		if (get(authUser)) {
			salvarResposta(resposta);
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
	<title>Vote — voto.vc</title>
</svelte:head>

{#if !uf}
	<div class="uf-selector">
		<h1>De qual estado você é?</h1>
		<p class="uf-subtitle">Vamos mostrar parlamentares do seu estado</p>
		<div class="uf-grid">
			{#each UFS as estado}
				<button class="uf-btn" onclick={() => escolherUf(estado.sigla)}>
					<span class="uf-sigla">{estado.sigla}</span>
					<span class="uf-nome">{estado.nome}</span>
				</button>
			{/each}
		</div>
	</div>
{:else if !loaded}
	<div class="loading">Carregando proposições...</div>
{:else if currentItems.length === 0}
	<div class="empty">Nenhuma proposição disponível no momento.</div>
{:else}
	<div class="questionario">
		<div class="progress">
			{#if seg1 > 0}<div class="progress-seg yellow" style="width: {seg1}%"></div>{/if}
			{#if seg2 > 0}<div class="progress-seg green" style="width: {seg2}%"></div>{/if}
			{#if seg3 > 0}<div class="progress-seg blue" style="width: {seg3}%"></div>{/if}
		</div>
		<div class="counter-row">
			<p class="answered">
				{answeredCount} voto{answeredCount !== 1 ? 's' : ''}
				{#if tierLabel}
					<span class="tier-badge">{tierLabel}</span>
				{:else}
					<span class="hint">· mínimo {TIER1}</span>
				{/if}
			</p>
		</div>

		{#if reachedTier3}
			<div class="meta-banner success">
				Perfil expert! {answeredCount} respostas. Altíssima precisão.
				<button class="btn-resultado" onclick={verResultado}>Ver meu resultado</button>
			</div>
		{:else if reachedTier2}
			<div class="meta-banner success">
				Perfil avançado! Quanto mais você responder, mais preciso fica.
				<button class="btn-resultado" onclick={verResultado}>Ver meu resultado</button>
			</div>
		{:else if canFinish}
			<div class="meta-banner ready">
				Seu perfil Básico está pronto. Continue votando para aumentar a precisão.
				<button class="btn-resultado" onclick={verResultado}>Ver perfil</button>
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
		background: var(--border);
		border-radius: 4px;
		height: 8px;
		overflow: hidden;
		display: flex;
	}

	.progress-seg {
		height: 100%;
		transition: width 0.3s ease;
	}

	.progress-seg.yellow { background: #eab308; }
	.progress-seg.green { background: #16a34a; }
	.progress-seg.blue { background: #2563eb; }

	.counter-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin: 0.5rem 0 1rem;
	}

	.answered {
		color: var(--text-secondary);
		font-size: 0.875rem;
		font-weight: 600;
		margin: 0;
	}

	.hint {
		color: var(--text-secondary);
		font-weight: 400;
	}

	.tier-badge {
		font-size: 0.75rem;
		font-weight: 600;
		padding: 0.125rem 0.5rem;
		border-radius: 10px;
		background: var(--link);
		color: white;
		margin-left: 0.25rem;
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
		background: #fef3c7;
		color: #92400e;
		border: 1px solid #f59e0b66;
	}

	:global([data-theme='escuro']) .meta-banner.ready {
		background: #eab3081a;
		color: #fbbf24;
		border: 1px solid #eab30833;
	}

	.meta-banner.success {
		background: #16a34a1a;
		color: #16a34a;
		border: 1px solid #16a34a33;
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
		background: var(--bg-card);
		border: 1px solid var(--border);
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
		color: var(--text-primary);
		margin: 0;
	}

	.descricao {
		color: var(--text-secondary);
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
		color: var(--link);
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
		white-space: nowrap;
		flex: 1;
		min-width: 0;
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
		background: var(--border);
		color: var(--text-secondary);
	}

	.loading,
	.empty {
		text-align: center;
		padding: 4rem;
		color: var(--text-secondary);
		font-size: 1.125rem;
	}

	.uf-selector {
		max-width: 700px;
		margin: 0 auto;
		text-align: center;
	}

	.uf-selector h1 {
		color: var(--text-primary);
		margin-bottom: 0.25rem;
	}

	.uf-subtitle {
		color: var(--text-secondary);
		margin-bottom: 2rem;
	}

	.uf-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
		gap: 0.5rem;
	}

	.uf-btn {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 10px;
		cursor: pointer;
		transition: border-color 0.2s, background 0.2s;
		text-align: left;
	}

	.uf-btn:hover {
		border-color: var(--link);
		background: var(--bg-page);
	}

	.uf-sigla {
		font-weight: 700;
		color: var(--link);
		font-size: 1rem;
		min-width: 1.75rem;
	}

	.uf-nome {
		color: var(--text-primary);
		font-size: 0.85rem;
	}
</style>
