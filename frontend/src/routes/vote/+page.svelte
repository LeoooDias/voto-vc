<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { api } from '$lib/api';
	import { selectedUf, respostas as respostasAvancado } from '$lib/stores/questionario';
	import { authUser, authLoading } from '$lib/stores/auth';
	import {
		posicaoItems,
		respostasPosicoes,
		overridesPosicoes,
		salvarRespostaPosicao,
		carregarRespostasPosicoes
	} from '$lib/stores/posicoes';
	import PositionSlider from '$lib/components/PositionSlider.svelte';
	import ChatWidget from '$lib/components/ChatWidget.svelte';
	import { positionToVote5, voteToPosition5 } from '$lib/utils/position';
	import type { PosicaoItem, RespostaPosicaoItem } from '$lib/types/posicao';
	import type { RespostaItem } from '$lib/types';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { UFS, getTema } from '$lib/constants';
	import { addToast } from '$lib/stores/toast';
	import { browser } from '$app/environment';

	const TIPOS_LEGENDA: Record<string, string> = {
		PL: 'Projeto de Lei',
		PEC: 'Proposta de Emenda à Constituição',
		MPV: 'Medida Provisória',
		PLP: 'Projeto de Lei Complementar',
		PDL: 'Projeto de Decreto Legislativo',
		MIP: 'Medida de Implementação Provisória'
	};

	interface Categoria {
		id: string;
		label: string;
		cor: string;
		corBg: string;
		ordens: number[];
	}

	const CATEGORIAS: Categoria[] = [
		{
			id: 'economia',
			label: 'Economia & Tributação',
			cor: '#CA8A04',
			corBg: '#CA8A041a',
			ordens: [1, 2, 3, 4, 5]
		},
		{
			id: 'seguranca',
			label: 'Segurança & Direitos Humanos',
			cor: '#2563EB',
			corBg: '#2563EB1a',
			ordens: [6, 7, 11, 12, 13]
		},
		{
			id: 'social',
			label: 'Educação, Saúde & Meio Ambiente',
			cor: '#16A34A',
			corBg: '#16A34A1a',
			ordens: [9, 10, 17, 18, 19]
		},
		{
			id: 'outros',
			label: 'Outros temas',
			cor: '#6B7280',
			corBg: '#6B72801a',
			ordens: [8, 14, 15, 16, 20]
		}
	];

	let uf = $state(get(selectedUf));
	let loaded = $state(false);
	let items: PosicaoItem[] = $state([]);
	let respostas: RespostaPosicaoItem[] = $state(get(respostasPosicoes));
	let overrides: RespostaItem[] = $state(get(overridesPosicoes));
	let expandedId: number | null = $state(null);
	let openCategoryId: string | null = $state(null);
	let showOnboarding = $state(false);
	let savedFeedback: number | null = $state(null);

	let answeredCount = $derived(respostas.filter((r) => r.voto !== 'pular').length);
	let canFinish = $derived(answeredCount >= 10);
	let remaining = $derived(Math.max(10 - answeredCount, 0));
	let progressPct = $derived(Math.min((answeredCount / 20) * 100, 100));

	function categorizedItems(cat: Categoria): PosicaoItem[] {
		return items.filter((i) => cat.ordens.includes(i.ordem));
	}

	function categoryAnswered(cat: Categoria): number {
		const catItems = categorizedItems(cat);
		return catItems.filter((i) =>
			respostas.some((r) => r.posicao_id === i.id && r.voto !== 'pular')
		).length;
	}

	async function toggleCategory(catId: string) {
		const isOpening = openCategoryId !== catId;
		openCategoryId = isOpening ? catId : null;
		expandedId = null;

		if (isOpening) {
			await tick();
			const el = document.getElementById(`cat-${catId}`);
			if (el) {
				el.scrollIntoView({ behavior: 'instant', block: 'start' });
			}
		}
	}

	function escolherUf(sigla: string) {
		uf = sigla;
		selectedUf.set(sigla);
		loadPositions();

		if (get(authUser)) {
			fetch('/api/auth/me', {
				method: 'PATCH',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ uf: sigla })
			});
		}
	}

	async function loadPositions() {
		try {
			const user = get(authUser);
			if (user) {
				const saved = await carregarRespostasPosicoes();
				if (saved.length > 0) {
					respostas = saved;
					respostasPosicoes.set(saved);
				}
			}

			const data = await api.get<PosicaoItem[]>('/posicoes/items');
			items = data;
			posicaoItems.set(data);
			loaded = true;

			// Show onboarding on first visit
			if (browser && !localStorage.getItem('voto_onboarding_seen') && respostas.filter(r => r.voto !== 'pular').length === 0) {
				showOnboarding = true;
			}
		} catch (e) {
			console.error('Failed to load positions:', e);
		}
	}

	function dismissOnboarding() {
		showOnboarding = false;
		if (browser) localStorage.setItem('voto_onboarding_seen', '1');
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
			await loadPositions();
		}
	}

	onMount(() => {
		if (!get(authLoading)) {
			initPage();
			return;
		}
		const unsub = authLoading.subscribe((loading) => {
			if (!loading) {
				unsub();
				initPage();
			}
		});
	});

	function getRespostaPos(posicaoId: number): number | null {
		const r = respostas.find((r) => r.posicao_id === posicaoId);
		if (!r) return null;
		return voteToPosition5(r.voto, r.peso);
	}

	function votarPosicao(posicaoId: number, sliderPos: number) {
		const { voto, peso } = positionToVote5(sliderPos);
		const resposta: RespostaPosicaoItem = {
			posicao_id: posicaoId,
			voto,
			peso
		};

		respostas = respostas.filter((r) => r.posicao_id !== posicaoId);
		respostas = [...respostas, resposta];
		respostasPosicoes.set(respostas);

		// Show brief "saved" feedback
		savedFeedback = posicaoId;
		setTimeout(() => { if (savedFeedback === posicaoId) savedFeedback = null; }, 1200);

		if (get(authUser)) {
			salvarRespostaPosicao(resposta);
		}
	}

	function toggleExpand(posicaoId: number) {
		expandedId = expandedId === posicaoId ? null : posicaoId;
	}

	function getOverride(proposicaoId: number): RespostaItem | undefined {
		return overrides.find((o) => o.proposicao_id === proposicaoId);
	}

	function setOverride(proposicaoId: number, voto: 'sim' | 'nao') {
		const existing = overrides.findIndex((o) => o.proposicao_id === proposicaoId);
		const item: RespostaItem = { proposicao_id: proposicaoId, voto, peso: 1.0 };
		if (existing >= 0) {
			const updated = [...overrides];
			if (overrides[existing].voto === voto) {
				updated.splice(existing, 1);
				overrides = updated;
			} else {
				updated[existing] = item;
				overrides = updated;
			}
		} else {
			overrides = [...overrides, item];
		}
		overridesPosicoes.set(overrides);
	}

	function verResultado() {
		goto('/perfil');
	}

	let showModeModal = $state(false);
	let confirmingReset = $state(false);
	let resetting = $state(false);

	async function resetarVotos() {
		resetting = true;
		try {
			const user = get(authUser);
			if (user) {
				await Promise.all([
					fetch('/api/posicoes/respostas', { method: 'DELETE', credentials: 'include' }),
					fetch('/api/vote/respostas', { method: 'DELETE', credentials: 'include' })
				]);
			}
			respostas = [];
			overrides = [];
			respostasPosicoes.set([]);
			overridesPosicoes.set([]);
			respostasAvancado.set([]);
			confirmingReset = false;
		} finally {
			resetting = false;
		}
	}
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
	<div class="loading">Carregando posições...</div>
{:else if items.length === 0}
	<div class="empty">Nenhuma posição disponível no momento.</div>
{:else}
	{#if showOnboarding}
		<div class="onboarding-overlay">
			<div class="onboarding-modal">
				<h2>Como funciona</h2>
				<div class="onboarding-steps">
					<div class="onboarding-step">
						<span class="onboarding-num">1</span>
						<p>Escolha sua posição em cada tema: <strong>a favor</strong>, <strong>contra</strong> ou <strong>neutro</strong></p>
					</div>
					<div class="onboarding-step">
						<span class="onboarding-num">2</span>
						<p>Responda ao menos <strong>10 de 20 posições</strong> para ver seu perfil</p>
					</div>
					<div class="onboarding-step">
						<span class="onboarding-num">3</span>
						<p>Descubra quais parlamentares e partidos mais se alinham com você</p>
					</div>
				</div>
				<button class="onboarding-btn" onclick={dismissOnboarding}>Entendi, vamos lá</button>
			</div>
		</div>
	{/if}

	<div class="posicoes-page">
		<div class="uf-badge-row">
			<span class="uf-badge" title="Trocar estado">
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
				{uf}
			</span>
			<button class="uf-change-btn" onclick={() => { uf = ''; selectedUf.set(''); }}>Trocar estado</button>
		</div>
		<div class="progress-sticky">
			<div class="progress">
				<div class="progress-fill" style="width: {progressPct}%"></div>
			</div>
			<div class="counter-row">
				<p class="answered-text">
					{answeredCount}/20 posições respondidas
					{#if remaining > 0}
						<span class="remaining-hint"> · faltam {remaining} para ver seu perfil</span>
				{/if}
			</p>
			</div>
		</div>

		<div class="categories-grid">
			{#each CATEGORIAS as cat}
				{@const catItems = categorizedItems(cat)}
				{@const catAnswered = categoryAnswered(cat)}
				{@const isOpen = openCategoryId === cat.id}
				{@const isDone = catAnswered === catItems.length}
				<div id="cat-{cat.id}" class="cat-section" class:open={isOpen}>
					<button
						class="cat-card"
						class:done={isDone}
						style="border-color: {isOpen ? cat.cor : ''}; background: {isOpen ? cat.corBg : ''}"
						onclick={() => toggleCategory(cat.id)}
					>
						<div class="cat-left">
							<span class="cat-dot" style="background: {cat.cor}"></span>
							<div>
								<span class="cat-label">{cat.label}</span>
								<span class="cat-count">{catAnswered}/{catItems.length}</span>
							</div>
						</div>
						<svg class="cat-chevron" class:open={isOpen} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
					</button>

					{#if isOpen}
						<div class="cat-positions">
							{#each catItems as pos}
								{@const currentPos = getRespostaPos(pos.id)}
								{@const isExpanded = expandedId === pos.id}
								{@const temaInfo = getTema(pos.tema)}
								<div class="pos-card" class:answered={currentPos != null}>
									<div class="pos-header">
										<div class="pos-title-row">
											<span class="pos-check" class:done={currentPos != null} style="border-color: {cat.cor}; background: {currentPos != null ? cat.cor : ''}">
												{#if currentPos != null}&#10003;{/if}
											</span>
											<div class="pos-title-block">
												<h3 class="pos-titulo">{pos.titulo}</h3>
												<span class="tema-tag" style="background: {temaInfo.cor}1a; color: {temaInfo.cor}; border-color: {temaInfo.cor}33">{temaInfo.label}</span>
											</div>
										</div>
										<p class="pos-descricao">{pos.descricao}</p>
									</div>

									<div class="slider-area">
										<PositionSlider
											value={currentPos}
											onselect={(p) => votarPosicao(pos.id, p)}
										/>
										{#if savedFeedback === pos.id}
											<span class="saved-indicator">Salvo</span>
										{/if}
									</div>

									<ChatWidget
										posicaoId={pos.id}
										proposicaoTitulo={pos.titulo}
										inline={true}
									/>

									{#if pos.proposicoes.length > 0}
										<button class="drill-toggle" onclick={() => toggleExpand(pos.id)}>
											<span class="drill-label">{pos.proposicoes.length} {pos.proposicoes.length === 1 ? 'proposição' : 'proposições'}</span>
											<svg class="expand-icon" class:open={isExpanded} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
										</button>
									{/if}

									{#if isExpanded}
										<div class="drill-down">
											{#each pos.proposicoes as prop}
												{@const override = getOverride(prop.proposicao_id)}
												<div class="drill-item">
													<div class="drill-info">
														<div class="drill-title-row">
														<span class="drill-tipo" title={TIPOS_LEGENDA[prop.tipo] ?? prop.tipo}>{prop.tipo} {prop.numero}/{prop.ano}</span>
														<span class="casa-pill" class:camara={prop.casa_origem === 'camara'} class:senado={prop.casa_origem === 'senado'}>
															{prop.casa_origem === 'camara' ? 'Câmara' : 'Senado'}
														</span>
													</div>
														<p class="drill-resumo">{prop.resumo ?? 'Sem descrição'}</p>
														<span class="drill-direcao">
															Direção na posição: {prop.direcao === 'sim' ? 'A favor' : 'Contra'}
														</span>
													</div>
													<div class="drill-actions">
														<button
															class="drill-btn favor"
															class:active={override?.voto === 'sim'}
															onclick={() => setOverride(prop.proposicao_id, 'sim')}
															title="A favor"
														>&#10003;</button>
														<button
															class="drill-btn contra"
															class:active={override?.voto === 'nao'}
															onclick={() => setOverride(prop.proposicao_id, 'nao')}
															title="Contra"
														>&#10007;</button>
													</div>
												</div>
											{/each}
										</div>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</div>
			{/each}
		</div>

		{#if canFinish}
			<div class="bottom-cta">
				<button class="btn-resultado" onclick={verResultado}>Ver meu perfil</button>
			</div>
		{/if}

		<div class="mode-link">
			<button class="link-btn" onclick={() => showModeModal = true}>Modo avançado (proposições individuais)</button>
		</div>

		{#if showModeModal}
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="mode-overlay" onclick={() => showModeModal = false}>
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div class="mode-modal" onclick={(e) => e.stopPropagation()}>
					<h2>Escolha o modo de votação</h2>
					<div class="mode-options">
						<div class="mode-option current">
							<h3>Por posições</h3>
							<p>Vote em 20 temas agrupados por categoria. Mais rápido e intuitivo.</p>
							<span class="mode-tag">Atual</span>
						</div>
						<a href="/vote/avancado" class="mode-option">
							<h3>Avançado</h3>
							<p>Vote em proposições individuais com mais detalhes. Maior precisão e controle.</p>
							<span class="mode-tag go">Ir para modo avançado &#8594;</span>
						</a>
					</div>
					<p class="mode-note">Seus votos são mantidos ao trocar de modo. Os dois modos contribuem para seu perfil.</p>
					<button class="mode-close" onclick={() => showModeModal = false}>Fechar</button>
				</div>
			</div>
		{/if}

		{#if answeredCount > 0}
			<div class="mode-link">
				{#if confirmingReset}
					<span class="reset-confirm">
						Apagar todos os votos?
						<button class="reset-confirm-btn yes" onclick={resetarVotos} disabled={resetting}>
							{resetting ? 'Apagando...' : 'Sim'}
						</button>
						<button class="reset-confirm-btn no" onclick={() => confirmingReset = false}>Não</button>
					</span>
				{:else}
					<button class="link-btn" onclick={() => confirmingReset = true}>Recomeçar (apagar votos)</button>
				{/if}
			</div>
		{/if}
	</div>

{/if}

<style>
	.posicoes-page {
		max-width: 650px;
		margin: 0 auto;
	}

	.progress-sticky {
		position: sticky;
		top: 90px;
		z-index: 40;
		background: var(--bg-page);
		padding: 0.75rem 0 0;
		margin: -0.75rem 0 0;
	}

	.progress {
		background: var(--border);
		border-radius: 4px;
		height: 8px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: #16a34a;
		transition: width 0.3s ease;
	}

	.counter-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin: 0.25rem 0 0.5rem;
	}

	.answered-text {
		color: var(--text-secondary);
		font-size: 0.875rem;
		font-weight: 600;
		margin: 0;
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

	/* Category cards grid */
	.categories-grid {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.cat-section {
		scroll-margin-top: 150px;
	}

	.cat-card {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: 1rem 1.25rem;
		background: var(--bg-card);
		border: 2px solid var(--border);
		border-radius: 14px;
		cursor: pointer;
		transition: border-color 0.2s, background 0.2s;
		text-align: left;
		font: inherit;
	}

	.cat-card:hover {
		border-color: var(--text-secondary);
	}

	.cat-left {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.cat-dot {
		width: 14px;
		height: 14px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.cat-label {
		font-weight: 700;
		font-size: 1rem;
		color: var(--text-primary);
		display: block;
	}

	.cat-count {
		font-size: 0.8rem;
		color: var(--text-secondary);
		font-weight: 500;
	}

	.cat-chevron {
		color: var(--text-secondary);
		transition: transform 0.2s;
		flex-shrink: 0;
	}

	.cat-chevron.open {
		transform: rotate(180deg);
	}

	.cat-positions {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		padding: 0.75rem 0 0;
	}

	/* Position cards */
	.pos-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 16px;
		padding: 1.25rem;
		transition: border-color 0.2s;
	}

	.pos-card.answered {
		border-color: #16a34a44;
	}

	.pos-header {
		margin-bottom: 0.75rem;
	}

	.pos-title-row {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
	}

	.pos-check {
		width: 24px;
		height: 24px;
		border-radius: 50%;
		border: 2px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		font-size: 0.7rem;
		color: white;
		transition: all 0.2s;
	}

	.pos-check.done {
		color: white;
	}

	.pos-title-block {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.pos-titulo {
		margin: 0;
		font-size: 1.05rem;
		color: var(--text-primary);
	}

	.tema-tag {
		padding: 0.15rem 0.5rem;
		border-radius: 20px;
		font-size: 0.7rem;
		font-weight: 600;
		border: 1px solid;
	}

	.pos-descricao {
		color: var(--text-secondary);
		font-size: 0.875rem;
		line-height: 1.5;
		margin: 0.5rem 0 0;
		padding-left: calc(24px + 0.75rem);
	}

	.slider-area {
		padding: 0 0.5rem;
	}

	.drill-toggle {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		background: none;
		border: none;
		color: var(--link);
		font-size: 0.8rem;
		font-weight: 600;
		cursor: pointer;
		margin-top: 0.75rem;
		padding: 0.25rem 0;
	}

	.drill-toggle:hover {
		text-decoration: underline;
	}

	.drill-label {
		color: var(--text-secondary);
		font-weight: 500;
	}

	.expand-icon {
		color: var(--text-secondary);
		transition: transform 0.2s;
	}

	.expand-icon.open {
		transform: rotate(180deg);
	}

	.drill-down {
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.drill-item {
		display: flex;
		gap: 0.75rem;
		align-items: flex-start;
	}

	.drill-info {
		flex: 1;
	}

	.drill-title-row {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		flex-wrap: wrap;
	}

	.casa-pill {
		font-size: 0.65rem;
		font-weight: 600;
		padding: 0.1rem 0.4rem;
		border-radius: 4px;
		border: 1px solid;
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

	:global(.dark) .casa-pill.camara {
		background: #1e3a5f;
		color: #93c5fd;
		border-color: #2563eb;
	}

	:global(.dark) .casa-pill.senado {
		background: #4a1942;
		color: #f9a8d4;
		border-color: #be185d;
	}

	.drill-tipo {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--link);
		background: #2563eb1a;
		padding: 0.1rem 0.5rem;
		border-radius: 4px;
	}

	.drill-resumo {
		font-size: 0.85rem;
		color: var(--text-primary);
		margin: 0.3rem 0 0;
		line-height: 1.4;
	}

	.drill-direcao {
		font-size: 0.7rem;
		color: var(--text-secondary);
	}

	.drill-actions {
		display: flex;
		gap: 0.25rem;
		flex-shrink: 0;
	}

	.drill-btn {
		width: 32px;
		height: 32px;
		border-radius: 8px;
		border: 1px solid var(--border);
		background: var(--bg-card);
		font-size: 1rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s;
	}

	.drill-btn.favor {
		color: #16a34a;
	}

	.drill-btn.contra {
		color: #dc2626;
	}

	.drill-btn.favor.active {
		background: #16a34a;
		color: white;
		border-color: #16a34a;
	}

	.drill-btn.contra.active {
		background: #dc2626;
		color: white;
		border-color: #dc2626;
	}

	.drill-btn:hover:not(.active) {
		border-color: var(--text-secondary);
	}

	.bottom-cta {
		text-align: center;
		margin-top: 1.5rem;
	}

	.mode-link {
		text-align: center;
		margin-top: 1rem;
	}

	.mode-link:last-child {
		padding-bottom: 2rem;
	}

	.mode-link .link-btn:hover {
		color: var(--link);
		text-decoration: underline;
	}

	.mode-link .link-btn {
		background: none;
		border: none;
		padding: 0;
		color: var(--text-secondary);
		text-decoration: none;
		font-size: 0.85rem;
		cursor: pointer;
		font-family: inherit;
	}

	.reset-confirm {
		color: var(--text-secondary);
		font-size: 0.85rem;
	}

	.reset-confirm-btn {
		background: none;
		border: 1px solid var(--border);
		border-radius: 6px;
		padding: 0.2rem 0.6rem;
		font-size: 0.8rem;
		cursor: pointer;
		margin-left: 0.4rem;
		font-family: inherit;
	}

	.reset-confirm-btn.yes {
		color: #dc2626;
		border-color: #dc26264d;
	}

	.reset-confirm-btn.yes:hover {
		background: #dc26261a;
	}

	.reset-confirm-btn.yes:disabled {
		opacity: 0.6;
		cursor: default;
	}

	.reset-confirm-btn.no {
		color: var(--text-secondary);
	}

	.reset-confirm-btn.no:hover {
		border-color: var(--text-secondary);
	}

	.remaining-hint {
		font-weight: 400;
		color: var(--text-secondary);
	}

	.uf-badge-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.75rem;
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

	.uf-change-btn {
		background: none;
		border: none;
		color: var(--text-secondary);
		font-size: 0.75rem;
		cursor: pointer;
		padding: 0;
		text-decoration: underline;
		font-family: inherit;
	}

	.uf-change-btn:hover {
		color: var(--link);
	}

	.saved-indicator {
		display: inline-block;
		font-size: 0.7rem;
		font-weight: 600;
		color: #16a34a;
		margin-top: 0.25rem;
		animation: fadeInOut 1.2s ease forwards;
	}

	@keyframes fadeInOut {
		0% { opacity: 0; transform: translateY(4px); }
		20% { opacity: 1; transform: translateY(0); }
		80% { opacity: 1; }
		100% { opacity: 0; }
	}

	/* Onboarding modal */
	.onboarding-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 200;
		padding: 1rem;
	}

	.onboarding-modal {
		background: var(--bg-card);
		border-radius: 16px;
		padding: 2rem;
		max-width: 440px;
		width: 100%;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
	}

	.onboarding-modal h2 {
		margin: 0 0 1.5rem;
		color: var(--text-primary);
		text-align: center;
		font-size: 1.25rem;
	}

	.onboarding-steps {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.onboarding-step {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
	}

	.onboarding-num {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: #2563eb;
		color: white;
		font-weight: 700;
		font-size: 0.875rem;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.onboarding-step p {
		margin: 0;
		color: var(--text-secondary);
		font-size: 0.9rem;
		line-height: 1.5;
		padding-top: 0.15rem;
	}

	.onboarding-btn {
		width: 100%;
		padding: 0.75rem;
		background: #2563eb;
		color: white;
		border: none;
		border-radius: 10px;
		font-weight: 600;
		font-size: 1rem;
		cursor: pointer;
		transition: background 0.2s;
	}

	.onboarding-btn:hover {
		background: #1d4ed8;
	}

	/* Mode selection modal */
	.mode-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 200;
		padding: 1rem;
	}

	.mode-modal {
		background: var(--bg-card);
		border-radius: 16px;
		padding: 2rem;
		max-width: 520px;
		width: 100%;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
	}

	.mode-modal h2 {
		margin: 0 0 1.5rem;
		color: var(--text-primary);
		text-align: center;
		font-size: 1.2rem;
	}

	.mode-options {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.mode-option {
		padding: 1rem 1.25rem;
		border: 2px solid var(--border);
		border-radius: 12px;
		text-decoration: none;
		color: inherit;
		transition: border-color 0.2s;
		display: block;
	}

	.mode-option:hover:not(.current) {
		border-color: var(--link);
	}

	.mode-option.current {
		border-color: #16a34a44;
		background: #16a34a0a;
	}

	.mode-option h3 {
		margin: 0 0 0.25rem;
		color: var(--text-primary);
		font-size: 1rem;
	}

	.mode-option p {
		margin: 0 0 0.5rem;
		color: var(--text-secondary);
		font-size: 0.85rem;
		line-height: 1.4;
	}

	.mode-tag {
		font-size: 0.7rem;
		font-weight: 700;
		color: #16a34a;
	}

	.mode-tag.go {
		color: var(--link);
	}

	.mode-note {
		font-size: 0.75rem;
		color: var(--text-secondary);
		text-align: center;
		margin: 0 0 1rem;
		line-height: 1.4;
	}

	.mode-close {
		width: 100%;
		padding: 0.6rem;
		background: var(--bg-page);
		border: 1px solid var(--border);
		border-radius: 8px;
		color: var(--text-secondary);
		font-weight: 500;
		cursor: pointer;
		font-family: inherit;
		font-size: 0.875rem;
	}

	.mode-close:hover {
		border-color: var(--text-secondary);
		color: var(--text-primary);
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

	@media (max-width: 768px) {
		.progress-sticky {
			top: 70px;
		}

		.cat-section {
			scroll-margin-top: 130px;
		}
	}
</style>
