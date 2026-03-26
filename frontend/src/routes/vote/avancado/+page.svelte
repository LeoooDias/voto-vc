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
	import VoteSlider from '$lib/components/VoteSlider.svelte';
	import ChatWidget from '$lib/components/ChatWidget.svelte';
	import { voteToPosition, positionToVote, voteLabel } from '$lib/utils/vote';
	import type { QuestionarioItem, RespostaItem } from '$lib/types';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { UFS, TIER1, TIER2, TIER3, getTema } from '$lib/constants';

	const TIPOS_LEGENDA: Record<string, string> = {
		PL: 'Projeto de Lei',
		PEC: 'Proposta de Emenda à Constituição',
		MPV: 'Medida Provisória',
		PLP: 'Projeto de Lei Complementar',
		PDL: 'Projeto de Decreto Legislativo',
		MIP: 'Medida de Implementação Provisória'
	};

	let uf = $state(get(selectedUf));
	let loaded = $state(false);
	let currentItems: QuestionarioItem[] = $state([]);
	let idx = $state(0);
	let answeredCount = $state(0);
	let showVotesPanel = $state(false);
	let showModeModal = $state(false);
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
			// Coletar IDs já respondidos (do DB para logado, ou do store/localStorage)
			const user = get(authUser);
			let existing = get(respostas);
			if (user) {
				const saved = await carregarRespostas();
				if (saved.length > 0) {
					respostas.set(saved);
					existing = saved;
				}
			}

			// Pedir ao backend que exclua apenas proposições efetivamente votadas (sim/nao), não pular
			const excludeIds = existing.filter((r) => r.voto !== 'pular').map((r) => r.proposicao_id);
			const excludeParam = excludeIds.length > 0 ? `&exclude=${excludeIds.join(',')}` : '';
			const data = await api.get<QuestionarioItem[]>(`/vote/items?n_items=50${excludeParam}`);

			answeredCount = existing.filter((r) => r.voto !== 'pular').length;
			items.set(data);
			currentItems = data;
			currentIndex.set(0);
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

	let respostaAtual = $derived.by(() => {
		if (!currentItems[idx]) return undefined;
		const pid = currentItems[idx].proposicao_id;
		return get(respostas).find((r) => r.proposicao_id === pid);
	});

	// Selected position on slider (not yet confirmed)
	let selectedPos: number | null = $state(null);

	// When navigating to a new question, reset selection to existing answer (if any)
	let lastIdx: number | null = $state(null);
	$effect(() => {
		const curIdx = idx;
		if (curIdx !== lastIdx) {
			lastIdx = curIdx;
			if (respostaAtual && respostaAtual.voto !== 'pular') {
				selectedPos = voteToPosition(respostaAtual.voto, respostaAtual.peso);
			} else {
				selectedPos = null;
			}
		}
	});

	let sliderValue = $derived(selectedPos);

	function voltar() {
		if (idx > 0) {
			currentIndex.set(idx - 1);
		}
	}

	function avancar() {
		if (idx + 1 < currentItems.length) {
			currentIndex.set(idx + 1);
		}
	}

	let canAdvance = $derived.by(() => {
		if (idx + 1 >= currentItems.length) return false;
		const pid = currentItems[idx]?.proposicao_id;
		if (!pid) return false;
		return get(respostas).some((r) => r.proposicao_id === pid);
	});

	function votar(voto: 'sim' | 'nao' | 'pular', peso: number = 1.0) {
		if (!currentItems[idx]) return;

		const pid = currentItems[idx].proposicao_id;
		const resposta: RespostaItem = {
			proposicao_id: pid,
			voto,
			peso
		};

		respostas.update((r) => {
			const existing = r.findIndex((x) => x.proposicao_id === pid);
			if (existing >= 0) {
				const old = r[existing];
				// Ajustar contagem
				if (old.voto === 'pular' && voto !== 'pular') answeredCount++;
				else if (old.voto !== 'pular' && voto === 'pular') answeredCount--;
				const updated = [...r];
				updated[existing] = resposta;
				return updated;
			}
			if (voto !== 'pular') answeredCount++;
			return [...r, resposta];
		});

		// Salvar no backend se logado (fire-and-forget)
		if (get(authUser)) {
			salvarResposta(resposta);
		}

		if (idx + 1 >= currentItems.length) {
			goto('/perfil');
		} else {
			currentIndex.set(idx + 1);
		}
	}

	function confirmarVoto() {
		if (selectedPos == null) return;
		const { voto, peso } = positionToVote(selectedPos);
		votar(voto, peso);
	}

	function verResultado() {
		goto('/perfil');
	}

	let answeredItems = $derived.by(() => {
		const r = get(respostas);
		return r
			.filter(x => x.voto !== 'pular')
			.map(x => {
				const item = currentItems.find(i => i.proposicao_id === x.proposicao_id);
				return { ...x, item };
			})
			.filter(x => x.item);
	});

	function handleGlobalKeydown(e: KeyboardEvent) {
		if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
		if (!loaded || !uf || currentItems.length === 0) return;

		if (e.key >= '1' && e.key <= '5') {
			e.preventDefault();
			selectedPos = parseInt(e.key);
		} else if (e.key === 'Enter' && selectedPos != null) {
			e.preventDefault();
			confirmarVoto();
		} else if (e.key === 'Escape') {
			e.preventDefault();
			votar('pular', 1.0);
		} else if (e.key === 'ArrowLeft') {
			e.preventDefault();
			voltar();
		} else if (e.key === 'ArrowRight' && canAdvance) {
			e.preventDefault();
			avancar();
		}
	}

</script>

<svelte:head>
	<title>Modo Avançado — voto.vc</title>
</svelte:head>

<svelte:window onkeydown={handleGlobalKeydown} />

<div class="top-bar">
	<a href="/vote" class="back-link-a">&#8592; Modo por posições</a>
	{#if uf}
		<div class="top-right">
			<span class="uf-badge">
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
				{uf}
			</span>
			<button class="votes-panel-btn" onclick={() => showVotesPanel = !showVotesPanel}>
				Meus votos ({answeredCount})
			</button>
		</div>
	{/if}
</div>

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
			<div class="meta-banner expert">
				Perfil expert! {answeredCount} respostas. Altíssima precisão.
				<button class="btn-resultado" onclick={verResultado}>Ver meu perfil</button>
			</div>
		{:else if reachedTier2}
			<div class="meta-banner success">
				Perfil avançado! Quanto mais você responder, mais preciso fica.
				<button class="btn-resultado" onclick={verResultado}>Ver meu perfil</button>
			</div>
		{:else if canFinish}
			<div class="meta-banner ready">
				Seu perfil Básico está pronto. Continue votando para aumentar a precisão.
				<button class="btn-resultado" onclick={verResultado}>Ver perfil</button>
			</div>
		{/if}

		<div class="card">
			<div class="card-header">
				<span class="tipo" title={TIPOS_LEGENDA[currentItems[idx].tipo] ?? currentItems[idx].tipo}>{currentItems[idx].tipo} {currentItems[idx].numero}/{currentItems[idx].ano}</span>
				{#if getTema(currentItems[idx].tema)}
					<span class="tema-tag" style="background: {getTema(currentItems[idx].tema).cor}1a; color: {getTema(currentItems[idx].tema).cor}; border-color: {getTema(currentItems[idx].tema).cor}33">{getTema(currentItems[idx].tema).label}</span>
				{:else}
					<span class="tema-tag" style="background: {getTema('geral').cor}1a; color: {getTema('geral').cor}; border-color: {getTema('geral').cor}33">{getTema('geral').label}</span>
				{/if}
			</div>
			<p class="resumo">{currentItems[idx].resumo}</p>
			{#if currentItems[idx].descricao_detalhada}
				<p class="descricao">{currentItems[idx].descricao_detalhada}</p>
			{/if}
			{#if currentItems[idx].casas.length > 0}
				<div class="casa-pills">
					{#each currentItems[idx].casas as info}
						{#if info.url}
							<a href={info.url} target="_blank" rel="noopener" class="casa-pill" class:camara={info.casa === 'camara'} class:senado={info.casa === 'senado'}>{info.casa === 'camara' ? 'Câmara' : 'Senado'}</a>
						{:else}
							<span class="casa-pill" class:camara={info.casa === 'camara'} class:senado={info.casa === 'senado'}>{info.casa === 'camara' ? 'Câmara' : 'Senado'}</span>
						{/if}
					{/each}
				</div>
			{/if}
		</div>

		<div class="slider-area">
			<VoteSlider
				value={sliderValue}
				onselect={(pos) => { selectedPos = pos; }}
			/>
		</div>

		<div class="actions">
			<button class="btn-nav" onclick={voltar} disabled={idx === 0} aria-label="Voltar">&#8592;</button>
			<button class="btn-pular" onclick={() => votar('pular', 1.0)}>Pular</button>
			<button class="btn-votar" class:active={selectedPos != null} onclick={confirmarVoto} disabled={selectedPos == null}>Votar</button>
			<button class="btn-nav" onclick={avancar} disabled={!canAdvance} aria-label="Avançar">&#8594;</button>
		</div>
		<ChatWidget
			proposicaoId={currentItems[idx].proposicao_id}
			proposicaoTitulo="{currentItems[idx].tipo} {currentItems[idx].numero}/{currentItems[idx].ano}"
		/>

		<p class="keyboard-hint">Atalhos: <kbd>1</kbd>-<kbd>5</kbd> posição · <kbd>Enter</kbd> votar · <kbd>Esc</kbd> pular · <kbd>&#8592;</kbd><kbd>&#8594;</kbd> navegar</p>
	</div>

	{#if showVotesPanel}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="votes-panel-backdrop" onclick={() => showVotesPanel = false}></div>
		<div class="votes-panel">
			<div class="votes-panel-header">
				<h3>Meus votos ({answeredCount})</h3>
				<button class="votes-panel-close" onclick={() => showVotesPanel = false}>&times;</button>
			</div>
			<div class="votes-panel-list">
				{#if answeredItems.length === 0}
					<p class="votes-panel-empty">Nenhum voto registrado ainda.</p>
				{:else}
					{#each answeredItems as v}
						<div class="votes-panel-item">
							<div class="votes-panel-info">
								<span class="votes-panel-tipo">{v.item?.tipo} {v.item?.numero}/{v.item?.ano}</span>
								<span class="votes-panel-resumo">{v.item?.resumo?.slice(0, 80)}{(v.item?.resumo?.length ?? 0) > 80 ? '...' : ''}</span>
							</div>
							<span class="votes-panel-voto" class:favor={v.voto === 'sim'} class:contra={v.voto === 'nao'}>
								{voteLabel(v.voto, v.peso)}
							</span>
						</div>
					{/each}
				{/if}
			</div>
		</div>
	{/if}
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

	.meta-banner.expert {
		background: #2563eb1a;
		color: #2563eb;
		border: 1px solid #2563eb33;
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

	.casa-pills {
		display: flex;
		gap: 0.25rem;
		margin-top: 0.75rem;
	}

	.casa-pill {
		font-size: 0.7rem;
		font-weight: 600;
		padding: 0.15rem 0.5rem;
		border-radius: 10px;
		border: 1px solid;
		text-decoration: none;
		transition: opacity 0.2s;
	}

	a.casa-pill:hover {
		opacity: 0.8;
	}

	.casa-pill.camara {
		background: #dbeafe;
		color: #1d4ed8;
		border-color: #93c5fd;
	}

	.casa-pill.senado {
		background: #fce7f3;
		color: #be185d;
		border-color: #f9a8d4;
	}

	:global([data-theme='escuro']) .casa-pill.camara {
		background: #1e3a5f;
		color: #93c5fd;
		border-color: #2563eb44;
	}

	:global([data-theme='escuro']) .casa-pill.senado {
		background: #4a1942;
		color: #f9a8d4;
		border-color: #be185d44;
	}

	.slider-area {
		margin-top: 1.5rem;
	}

	.actions {
		display: flex;
		gap: 0.75rem;
		margin-top: 1rem;
		justify-content: center;
		align-items: center;
	}

	.btn-pular {
		padding: 0.6rem 1.5rem;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 12px;
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--text-secondary);
		cursor: pointer;
		transition: border-color 0.2s, color 0.2s;
	}

	.btn-pular:hover {
		border-color: var(--text-secondary);
		color: var(--text-primary);
	}

	.btn-votar {
		padding: 0.6rem 2rem;
		background: var(--border);
		border: none;
		border-radius: 12px;
		font-size: 0.9rem;
		font-weight: 700;
		color: var(--text-secondary);
		cursor: default;
		transition: background 0.2s, color 0.2s, transform 0.15s;
	}

	.btn-votar.active {
		background: #2563eb;
		color: white;
		cursor: pointer;
	}

	.btn-votar.active:hover {
		background: #1d4ed8;
		transform: scale(1.03);
	}

	.btn-nav {
		width: 44px;
		height: 44px;
		flex-shrink: 0;
		border: 1px solid var(--border);
		border-radius: 12px;
		background: var(--bg-card);
		color: var(--text-secondary);
		font-size: 1.25rem;
		cursor: pointer;
		transition: border-color 0.2s, color 0.2s;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.btn-nav:hover:not(:disabled) {
		border-color: var(--link);
		color: var(--text-primary);
	}

	.btn-nav:disabled {
		opacity: 0.3;
		cursor: default;
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

	.top-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1rem;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.back-link-a {
		color: var(--link);
		text-decoration: none;
		font-size: 0.875rem;
	}

	.back-link-a:hover {
		text-decoration: underline;
	}

	.top-right {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.uf-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		background: var(--link);
		color: white;
		padding: 0.2rem 0.6rem;
		border-radius: 6px;
		font-size: 0.8rem;
		font-weight: 700;
	}

	.votes-panel-btn {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 0.3rem 0.75rem;
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--text-secondary);
		cursor: pointer;
		font-family: inherit;
		transition: border-color 0.2s;
	}

	.votes-panel-btn:hover {
		border-color: var(--link);
		color: var(--text-primary);
	}

	.keyboard-hint {
		text-align: center;
		font-size: 0.7rem;
		color: var(--text-secondary);
		margin-top: 1.5rem;
		opacity: 0.7;
	}

	.keyboard-hint kbd {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 3px;
		padding: 0.1rem 0.3rem;
		font-size: 0.65rem;
		font-family: inherit;
	}

	/* Votes panel */
	.votes-panel-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.3);
		z-index: 99;
	}

	.votes-panel {
		position: fixed;
		top: 0;
		right: 0;
		bottom: 0;
		width: 360px;
		max-width: 90vw;
		background: var(--bg-card);
		border-left: 1px solid var(--border);
		box-shadow: -4px 0 16px rgba(0, 0, 0, 0.1);
		z-index: 100;
		display: flex;
		flex-direction: column;
	}

	.votes-panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem 1.25rem;
		border-bottom: 1px solid var(--border);
	}

	.votes-panel-header h3 {
		margin: 0;
		font-size: 1rem;
		color: var(--text-primary);
	}

	.votes-panel-close {
		background: none;
		border: none;
		font-size: 1.5rem;
		cursor: pointer;
		color: var(--text-secondary);
		padding: 0;
		line-height: 1;
	}

	.votes-panel-list {
		flex: 1;
		overflow-y: auto;
		padding: 0.75rem;
	}

	.votes-panel-empty {
		text-align: center;
		color: var(--text-secondary);
		padding: 2rem;
		font-size: 0.875rem;
	}

	.votes-panel-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.6rem 0.5rem;
		border-bottom: 1px solid var(--border);
	}

	.votes-panel-info {
		flex: 1;
		min-width: 0;
	}

	.votes-panel-tipo {
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--link);
		display: block;
	}

	.votes-panel-resumo {
		font-size: 0.75rem;
		color: var(--text-secondary);
		line-height: 1.3;
		display: block;
		margin-top: 0.15rem;
	}

	.votes-panel-voto {
		font-size: 0.7rem;
		font-weight: 700;
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
		flex-shrink: 0;
		white-space: nowrap;
	}

	.votes-panel-voto.favor {
		background: #16a34a1a;
		color: #16a34a;
	}

	.votes-panel-voto.contra {
		background: #dc26261a;
		color: #dc2626;
	}
</style>
