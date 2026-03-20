<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { respostas, selectedUf, carregarRespostas, salvarResposta } from '$lib/stores/questionario';
	import { respostasPosicoes, overridesPosicoes, carregarRespostasPosicoes } from '$lib/stores/posicoes';
	import { expandPositions } from '$lib/utils/position';
	import { posicaoItems } from '$lib/stores/posicoes';
	import type { RespostaPosicaoItem, PosicaoItem } from '$lib/types/posicao';
	import { authUser, authLoading } from '$lib/stores/auth';
	import { resultados, resultadosPartidos, loading } from '$lib/stores/resultado';
	import VoteSlider from '$lib/components/VoteSlider.svelte';
	import { voteToPosition, voteLabel } from '$lib/utils/vote';
	import type { MatchResult, PartidoMatchResult, MatchResponse, RespostaItem } from '$lib/types';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { UF_SIGLAS, getTema, fmtPct } from '$lib/constants';

	interface ProposicaoInfo {
		proposicao_id: number;
		tipo: string;
		numero: number;
		ano: number;
		resumo: string | null;
		descricao_detalhada: string | null;
		tema: string;
		casas: Array<{ casa: string; url: string }>;
	}

	let parlResults: MatchResult[] = $state([]);
	let partidoResults: PartidoMatchResult[] = $state([]);
	let isLoading = $state(true);
	let scopeLoading = $state(false);
	let totalRespostas = $state(0);
	let tab: 'parlamentares' | 'partidos' | 'votos' = $state('partidos');
	let casaFilter: 'todos' | 'camara' | 'senado' = $state('todos');

	let parlFiltered = $derived(
		casaFilter === 'todos' ? parlResults : parlResults.filter((r) => r.casa === casaFilter)
	);
	let countCamara = $derived(parlResults.filter((r) => r.casa === 'camara').length);
	let countSenado = $derived(parlResults.filter((r) => r.casa === 'senado').length);

	// Escopo
	let escopo: 'brasil' | 'estado' = $state('brasil');
	let ufSelecionada = $state('');
	let showUfPicker = $state(false);

	// Votos tab
	let userRespostas: RespostaItem[] = $state([]);
	let userPosicaoRespostas: RespostaPosicaoItem[] = $state([]);
	let cachedPosicaoItems: PosicaoItem[] = $state([]);
	let proposicoes = $state<Map<number, ProposicaoInfo>>(new Map());
	let votosLoaded = $state(false);
	let expandedVotoId: number | null = $state(null);

	let expandedPosVotes = $derived.by(() => {
		if (userPosicaoRespostas.length === 0 || cachedPosicaoItems.length === 0) return [];
		return expandPositions(userPosicaoRespostas, cachedPosicaoItems, []);
	});

	let allVotes = $derived.by(() => {
		const direct = userRespostas.filter((r) => r.voto !== 'pular');
		// Also include expanded posicao votes (only those not already in direct)
		const directIds = new Set(direct.map((r) => r.proposicao_id));
		const expanded = expandedPosVotes.filter((r) => !directIds.has(r.proposicao_id));
		return [...direct, ...expanded];
	});

	let meusVotos = $derived(
		allVotes
			.map((r) => ({
				...r,
				prop: proposicoes.get(r.proposicao_id)
			}))
			.filter((r) => r.prop)
	);

	resultados.subscribe((v) => (parlResults = v));
	resultadosPartidos.subscribe((v) => (partidoResults = v));
	loading.subscribe((v) => (isLoading = v));

	async function loadMatching() {
		const isInitial = parlResults.length === 0 && partidoResults.length === 0;
		if (isInitial) loading.set(true);
		scopeLoading = true;
		try {
			const body: Record<string, unknown> = {
				respostas: userRespostas,
				uf: escopo === 'estado' && ufSelecionada ? ufSelecionada : undefined
			};
			if (userPosicaoRespostas.length > 0) {
				body.posicao_respostas = userPosicaoRespostas;
			}
			const data = await api.post<MatchResponse>('/matching/calcular', body);
			resultados.set(data.parlamentares);
			resultadosPartidos.set(data.partidos);
		} catch (e) {
			console.error('Failed to calculate matching:', e);
		} finally {
			loading.set(false);
			scopeLoading = false;
		}
	}

	async function loadVotosData() {
		if (votosLoaded) return;

		// Load posicao items if we have posicao respostas but no cached items
		if (userPosicaoRespostas.length > 0 && cachedPosicaoItems.length === 0) {
			try {
				const posItems = await api.get<PosicaoItem[]>('/posicoes/items');
				cachedPosicaoItems = posItems;
				posicaoItems.set(posItems);
			} catch (e) {
				console.error('Failed to load posicao items:', e);
			}
		}

		// Collect all proposition IDs from direct votes + expanded position votes
		const directIds = userRespostas.filter((r) => r.voto !== 'pular').map((r) => r.proposicao_id);
		const expandedIds = expandedPosVotes.map((r) => r.proposicao_id);
		const allIds = [...new Set([...directIds, ...expandedIds])];
		if (allIds.length === 0) return;

		try {
			const data = await api.post<ProposicaoInfo[]>('/proposicoes/batch', { ids: allIds });
			const map = new Map<number, ProposicaoInfo>();
			for (const p of data) map.set(p.proposicao_id, p);
			proposicoes = map;
			votosLoaded = true;
		} catch (e) {
			console.error('Failed to load proposições:', e);
		}
	}

	function setEscopo(novo: 'brasil' | 'estado') {
		if (novo === 'estado' && !ufSelecionada) {
			showUfPicker = true;
			return;
		}
		escopo = novo;
		loadMatching();
	}

	function escolherUf(sigla: string) {
		ufSelecionada = sigla;
		selectedUf.set(sigla);
		showUfPicker = false;
		escopo = 'estado';
		loadMatching();
	}

	function selectTab(t: typeof tab) {
		tab = t;
		if (t === 'votos') loadVotosData();
	}

	function toggleVotoExpand(propId: number) {
		expandedVotoId = expandedVotoId === propId ? null : propId;
	}

	function reVotar(proposicaoId: number, voto: 'sim' | 'nao', peso: number = 1.0) {
		const resposta: RespostaItem = { proposicao_id: proposicaoId, voto, peso };
		respostas.update((r) => {
			const idx = r.findIndex((x) => x.proposicao_id === proposicaoId);
			if (idx >= 0) {
				const updated = [...r];
				updated[idx] = resposta;
				return updated;
			}
			return [...r, resposta];
		});
		userRespostas = userRespostas.map((r) =>
			r.proposicao_id === proposicaoId ? resposta : r
		);
		if (get(authUser)) salvarResposta(resposta);
		loadMatching();
	}

	onMount(() => {
		async function init() {
			userRespostas = get(respostas);
			userPosicaoRespostas = get(respostasPosicoes);

			if (userRespostas.length === 0 && get(authUser)) {
				const saved = await carregarRespostas();
				if (saved.length > 0) {
					respostas.set(saved);
					userRespostas = saved;
				}
			}

			// Load posicao respostas from DB if logged in
			if (userPosicaoRespostas.length === 0 && get(authUser)) {
				const savedPos = await carregarRespostasPosicoes();
				if (savedPos.length > 0) {
					respostasPosicoes.set(savedPos);
					userPosicaoRespostas = savedPos;
				}
			}

			if (userRespostas.length === 0 && userPosicaoRespostas.length === 0) {
				goto('/vote');
				return;
			}

			const directCount = userRespostas.filter((r) => r.voto !== 'pular').length;
		const posCount = userPosicaoRespostas.filter((r) => r.voto !== 'pular').length;
		totalRespostas = directCount + posCount;

			const user = get(authUser);
			if (user?.uf) {
				ufSelecionada = user.uf;
			} else {
				const storeUf = get(selectedUf);
				if (storeUf) ufSelecionada = storeUf;
			}
			if (ufSelecionada) escopo = 'estado';

			await loadMatching();
		}

		if (!get(authLoading)) { init(); return; }
		const unsub = authLoading.subscribe((l) => {
			if (!l) { unsub(); init(); }
		});
	});
</script>

<svelte:head>
	<title>Meu Perfil — voto.vc</title>
</svelte:head>

{#if showUfPicker}
	<div class="uf-selector">
		<h1>De qual estado?</h1>
		<p class="uf-subtitle">Filtrar parlamentares e partidos por estado</p>
		<div class="uf-grid">
			{#each UF_SIGLAS as sigla}
				<button class="uf-btn" onclick={() => escolherUf(sigla)}>
					{sigla}
				</button>
			{/each}
		</div>
		<button class="uf-cancel" onclick={() => showUfPicker = false}>Cancelar</button>
	</div>
{:else if isLoading && parlResults.length === 0}
	<div class="loading">Calculando seu alinhamento...</div>
{:else if parlResults.length === 0 && partidoResults.length === 0}
	<div class="empty">
		<p>Não foi possível calcular o alinhamento.</p>
		<a href="/vote">Tentar novamente</a>
	</div>
{:else}
	<div class="perfil-page">
		<h1>Seu alinhamento político</h1>
		<p class="subtitle">Baseado nos seus {totalRespostas} votos</p>

		<div class="tabs">
			<button class="tab" class:active={tab === 'partidos'} onclick={() => selectTab('partidos')}>
				Partidos
			</button>
			<button class="tab" class:active={tab === 'parlamentares'} onclick={() => selectTab('parlamentares')}>
				Parlamentares
			</button>
			<button class="tab" class:active={tab === 'votos'} onclick={() => selectTab('votos')}>
				Votos
			</button>
		</div>

		{#if tab !== 'votos'}
			<div class="escopo-toggle">
				<button
					class="escopo-btn"
					class:active={escopo === 'brasil'}
					onclick={() => setEscopo('brasil')}
				>Brasil</button>
				<button
					class="escopo-btn"
					class:active={escopo === 'estado'}
					onclick={() => setEscopo('estado')}
				>Meu estado{ufSelecionada ? ` (${ufSelecionada})` : ''}</button>
			</div>
		{/if}

		{#if tab === 'parlamentares'}
			<div class="casa-filter">
				<button class="casa-btn" class:active={casaFilter === 'todos'} onclick={() => casaFilter = 'todos'}>
					Todos ({parlResults.length})
				</button>
				<button class="casa-btn" class:active={casaFilter === 'camara'} onclick={() => casaFilter = 'camara'}>
					Câmara ({countCamara})
				</button>
				<button class="casa-btn" class:active={casaFilter === 'senado'} onclick={() => casaFilter = 'senado'}>
					Senado ({countSenado})
				</button>
			</div>
			<div class="lista">
				{#each parlFiltered as result, i}
					<a href="/parlamentar/{result.parlamentar_id}" class="result-card">
						<span class="rank">#{i + 1}</span>
						<div class="info">
							<div class="nome">{result.nome}</div>
							<div class="meta">
								{result.partido ?? 'Sem partido'} · {result.uf} · {result.casa === 'camara' ? (result.sexo === 'F' ? 'Deputada' : 'Deputado') : (result.sexo === 'F' ? 'Senadora' : 'Senador')} · {result.concordou}/{result.votos_comparados} votos em comum
							</div>
						</div>
						<div class="score" class:high={!scopeLoading && result.score >= 70} class:mid={!scopeLoading && result.score >= 40 && result.score < 70} class:low={!scopeLoading && result.score < 40}>
							{#if scopeLoading}<span class="spinner"></span>{:else}{fmtPct(result.score)}{/if}
						</div>
					</a>
				{/each}
			</div>
		{:else if tab === 'partidos'}
			<div class="lista">
				{#each partidoResults as result, i}
					<a href="/partido/{result.partido_id}" class="result-card">
						<span class="rank">#{i + 1}</span>
						<div class="info">
							<div class="nome">{result.sigla}</div>
							<div class="meta">{result.nome} · {result.concordou}/{result.votos_comparados} votos em comum</div>
						</div>
						{#if scopeLoading}
							<div class="score"><span class="spinner"></span></div>
						{:else if result.score != null}
							<div class="score" class:high={result.score >= 70} class:mid={result.score >= 40 && result.score < 70} class:low={result.score < 40}>
								{fmtPct(result.score)}
							</div>
						{:else}
							<div class="score score-na" title="Dados insuficientes">N/A</div>
						{/if}
					</a>
				{/each}
			</div>
		{:else}
			<div class="votos-lista">
				{#each meusVotos as item}
					{@const prop = item.prop}
					{@const isExpanded = expandedVotoId === item.proposicao_id}
					{#if prop}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div
							class="voto-card"
							class:expanded={isExpanded}
							onclick={() => toggleVotoExpand(item.proposicao_id)}
							onkeydown={(e) => e.key === 'Enter' && toggleVotoExpand(item.proposicao_id)}
							role="button"
							tabindex="0"
						>
							<div class="voto-main">
								<span class="voto-badge" class:voto-sim={item.voto === 'sim' && item.peso > 0} class:voto-nao={item.voto === 'nao'} class:voto-neutro={item.peso === 0}>
									{voteLabel(item.voto, item.peso)}
								</span>
								<div class="voto-info">
									<div class="voto-top">
										<span class="voto-tipo">{prop.tipo} {prop.numero}/{prop.ano}</span>
										<span class="tema-tag" style="background: {getTema(prop.tema).cor}1a; color: {getTema(prop.tema).cor}; border-color: {getTema(prop.tema).cor}33">{getTema(prop.tema).label}</span>
									</div>
									<p class="voto-resumo">{prop.resumo ?? 'Sem descrição'}</p>
								</div>
								<span class="expand-icon" class:open={isExpanded}>&#9662;</span>
							</div>

							{#if isExpanded}
								<div class="voto-details">
									{#if prop.descricao_detalhada}
										<p class="detail-descricao">{prop.descricao_detalhada}</p>
									{/if}
									{#if prop.casas?.length > 0}
										<div class="casa-pills">
											{#each prop.casas as info}
												<a href={info.url} target="_blank" rel="noopener" class="casa-pill" class:camara={info.casa === 'camara'} class:senado={info.casa === 'senado'} onclick={(e) => e.stopPropagation()}>{info.casa === 'camara' ? 'Câmara' : 'Senado'}</a>
											{/each}
										</div>
									{/if}
									<!-- svelte-ignore a11y_no_static_element_interactions -->
								<div class="revote-actions" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()}>
									<span class="revote-label">Mudar voto:</span>
									<VoteSlider
										compact
										value={voteToPosition(item.voto, item.peso)}
										onvote={(voto, peso) => reVotar(item.proposicao_id, voto, peso)}
									/>
								</div>
								</div>
							{/if}
						</div>
					{/if}
				{/each}
			</div>
		{/if}

		{#if !$authUser}
			<div class="cta-section">
				<p>Quer salvar suas respostas e acompanhar novas votações?</p>
				<a href="/login" class="cta">Entrar com Google</a>
			</div>
		{/if}
	</div>
{/if}

<style>
	.perfil-page {
		max-width: 700px;
		margin: 0 auto;
	}

	h1 {
		text-align: center;
		color: var(--text-primary);
	}

	.subtitle {
		text-align: center;
		color: var(--text-secondary);
		margin-bottom: 1rem;
	}

	/* Escopo toggle */
	.escopo-toggle {
		display: flex;
		gap: 0;
		margin-bottom: 1rem;
		border-bottom: 2px solid var(--border);
	}

	.escopo-btn {
		flex: 1;
		padding: 0.625rem 1rem;
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		margin-bottom: -2px;
		font-size: 0.938rem;
		font-weight: 600;
		color: var(--text-secondary);
		cursor: pointer;
		transition: color 0.2s, border-color 0.2s;
	}

	.escopo-btn:hover {
		color: var(--text-primary);
	}

	.escopo-btn.active {
		color: var(--link);
		border-bottom-color: var(--link);
	}

	/* Tabs */
	.tabs {
		display: flex;
		gap: 0;
		margin-bottom: 1.5rem;
		border-bottom: 2px solid var(--border);
	}

	.tab {
		flex: 1;
		padding: 0.75rem 1rem;
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		margin-bottom: -2px;
		font-size: 1rem;
		font-weight: 600;
		color: var(--text-secondary);
		cursor: pointer;
		transition: color 0.2s, border-color 0.2s;
	}

	.tab:hover {
		color: var(--text-primary);
	}

	.tab.active {
		color: var(--link);
		border-bottom-color: var(--link);
	}

	/* Casa filter */
	.casa-filter {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.casa-btn {
		padding: 0.4rem 0.875rem;
		border: 1px solid var(--border);
		border-radius: 20px;
		background: var(--bg-card);
		font-size: 0.813rem;
		font-weight: 600;
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.2s;
	}

	.casa-btn:hover {
		border-color: var(--link);
		color: var(--text-primary);
	}

	.casa-btn.active {
		background: var(--link);
		border-color: var(--link);
		color: white;
	}

	/* Result cards */
	.result-card {
		display: flex;
		align-items: center;
		gap: 1rem;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1rem 1.5rem;
		margin-bottom: 0.75rem;
		text-decoration: none;
		color: inherit;
		transition: border-color 0.2s;
	}

	.result-card:hover {
		border-color: var(--border-hover);
	}

	.rank {
		color: var(--text-secondary);
		font-weight: 700;
		font-size: 1.125rem;
		min-width: 2.5rem;
	}

	.info {
		flex: 1;
	}

	.nome {
		font-weight: 600;
		color: var(--text-primary);
	}

	.meta {
		font-size: 0.875rem;
		color: var(--text-secondary);
		margin-top: 0.25rem;
	}

	.score {
		font-size: 1.5rem;
		font-weight: 700;
	}

	.high { color: #16a34a; }
	.mid { color: #ca8a04; }
	.low { color: #dc2626; }

	.score-na {
		color: var(--text-secondary) !important;
		font-style: italic;
		font-size: 0.875rem;
		cursor: help;
	}

	/* Votos tab */
	.voto-card {
		display: block;
		width: 100%;
		text-align: left;
		font: inherit;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1rem;
		margin-bottom: 0.5rem;
		cursor: pointer;
		transition: border-color 0.2s;
	}

	.voto-card:hover {
		border-color: var(--border-hover);
	}

	.voto-card.expanded {
		border-color: var(--link);
	}

	.voto-main {
		display: flex;
		gap: 1rem;
		align-items: flex-start;
	}

	.voto-badge {
		font-size: 0.75rem;
		font-weight: 700;
		padding: 0.25rem 0.75rem;
		border-radius: 20px;
		white-space: nowrap;
	}

	.voto-badge.voto-sim { background: #16a34a1a; color: #16a34a; }
	.voto-badge.voto-nao { background: #dc26261a; color: #dc2626; }
	.voto-badge.voto-neutro { background: #a3a3a31a; color: #737373; }

	.voto-info { flex: 1; }

	.voto-top {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		flex-wrap: wrap;
	}

	.voto-tipo {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--link);
		background: #2563eb1a;
		padding: 0.1rem 0.5rem;
		border-radius: 4px;
	}

	.tema-tag {
		padding: 0.1rem 0.5rem;
		border-radius: 20px;
		font-size: 0.7rem;
		font-weight: 600;
		border: 1px solid;
	}

	.voto-resumo {
		margin: 0.5rem 0 0;
		font-size: 0.9rem;
		color: var(--text-primary);
		line-height: 1.4;
	}

	.expand-icon {
		color: var(--text-secondary);
		font-size: 1rem;
		transition: transform 0.2s;
		flex-shrink: 0;
		margin-top: 0.25rem;
	}

	.expand-icon.open {
		transform: rotate(180deg);
	}

	.voto-details {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--border);
	}

	.detail-descricao {
		font-size: 0.9rem;
		color: var(--text-secondary);
		line-height: 1.6;
		margin: 0 0 0.75rem;
	}

	.casa-pills {
		display: flex;
		gap: 0.25rem;
		margin-bottom: 1rem;
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

	.revote-actions {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.revote-label {
		font-size: 0.8rem;
		color: var(--text-secondary);
	}

	/* CTA */
	.cta-section {
		text-align: center;
		margin-top: 3rem;
		padding: 2rem;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 16px;
	}

	.cta-section p {
		color: var(--text-secondary);
		margin-bottom: 1rem;
	}

	.cta {
		display: inline-block;
		background: #2563eb;
		color: white;
		padding: 0.75rem 2rem;
		border-radius: 8px;
		text-decoration: none;
		font-weight: 600;
	}

	.loading, .empty {
		text-align: center;
		padding: 4rem;
		color: var(--text-secondary);
		font-size: 1.125rem;
	}

	/* UF picker */
	.uf-selector {
		max-width: 500px;
		margin: 0 auto;
		text-align: center;
	}

	.uf-selector h1 {
		color: var(--text-primary);
		margin-bottom: 0.25rem;
	}

	.uf-subtitle {
		color: var(--text-secondary);
		margin-bottom: 1.5rem;
	}

	.uf-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(60px, 1fr));
		gap: 0.5rem;
	}

	.uf-btn {
		padding: 0.625rem;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 8px;
		cursor: pointer;
		font-weight: 700;
		color: var(--link);
		font-size: 0.938rem;
		transition: border-color 0.2s;
	}

	.uf-btn:hover {
		border-color: var(--link);
	}

	.uf-cancel {
		margin-top: 1.5rem;
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		font-size: 0.875rem;
	}

	.uf-cancel:hover {
		color: var(--text-primary);
	}

	.spinner {
		display: inline-block;
		width: 1em;
		height: 1em;
		border: 2px solid var(--border);
		border-top-color: var(--link);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
		vertical-align: middle;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
