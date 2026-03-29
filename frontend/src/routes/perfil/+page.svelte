<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { respostas, selectedUf, carregarRespostas } from '$lib/stores/questionario';
	import { respostasPosicoes, carregarRespostasPosicoes } from '$lib/stores/posicoes';
	import type { RespostaPosicaoItem } from '$lib/types/posicao';
	import { authUser, authLoading } from '$lib/stores/auth';
	import { resultados, resultadosPartidos, loading } from '$lib/stores/resultado';
	import type { MatchResult, PartidoMatchResult, MatchResponse, RespostaItem } from '$lib/types';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { UF_SIGLAS, getTema } from '$lib/constants';
	import ScoreDots from '$lib/components/ScoreDots.svelte';

	let parlResults: MatchResult[] = $state([]);
	let partidoResults: PartidoMatchResult[] = $state([]);
	let isLoading = $state(true);
	let scopeLoading = $state(false);
	let totalRespostas = $state(0);
	let tab: 'parlamentares' | 'partidos' = $state('partidos');
	let searchQuery = $state('');
	let casaFilter: 'todos' | 'camara' | 'senado' = $state('todos');
	let apenasAtivos = $state(false);
	let ultimaDecada = $state(false);

	let parlFiltered = $derived.by(() => {
		let list = casaFilter === 'todos' ? parlResults : parlResults.filter((r) => r.casa === casaFilter);
		if (searchQuery.trim()) {
			const q = searchQuery.trim().toLowerCase();
			list = list.filter((r) => r.nome.toLowerCase().includes(q) || (r.partido ?? '').toLowerCase().includes(q));
		}
		return list;
	});
	let partidoFiltered = $derived.by(() => {
		if (!searchQuery.trim()) return partidoResults;
		const q = searchQuery.trim().toLowerCase();
		return partidoResults.filter((r) => r.sigla.toLowerCase().includes(q) || r.nome.toLowerCase().includes(q));
	});
	let countCamara = $derived(parlResults.filter((r) => r.casa === 'camara').length);
	let countSenado = $derived(parlResults.filter((r) => r.casa === 'senado').length);

	// Escopo
	let escopo: 'brasil' | 'estado' = $state('brasil');
	let ufSelecionada = $state('');
	let showUfPicker = $state(false);

	let userRespostas: RespostaItem[] = $state([]);
	let userPosicaoRespostas: RespostaPosicaoItem[] = $state([]);

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
				uf: escopo === 'estado' && ufSelecionada ? ufSelecionada : undefined,
				apenas_ativos: apenasAtivos || undefined,
				ultima_decada: ultimaDecada || undefined
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
				<button class="uf-btn" aria-label="Selecionar estado {sigla}" onclick={() => escolherUf(sigla)}>
					{sigla}
				</button>
			{/each}
		</div>
		<button class="uf-cancel" onclick={() => showUfPicker = false}>Cancelar</button>
	</div>
{:else if isLoading && parlResults.length === 0}
	<div class="loading">
		<div class="loading-spinner"></div>
		<p>Calculando seu alinhamento...</p>
		<p class="loading-sub">Comparando seus votos com os parlamentares</p>
	</div>
{:else if parlResults.length === 0 && partidoResults.length === 0}
	<div class="empty">
		<p>Não foi possível calcular o alinhamento.</p>
		<a href="/vote">Tentar novamente</a>
	</div>
{:else}
	<div class="perfil-page">
		<p class="result-eyebrow">Resultado</p>
		<h1>Seu alinhamento político</h1>
		<p class="subtitle">Baseado nos seus {totalRespostas} votos · <a href="/sobre#metodologia" class="methodology-link">como é calculado?</a></p>

		<div class="tabs" role="tablist">
			<button class="tab" class:active={tab === 'partidos'} role="tab" aria-selected={tab === 'partidos'} onclick={() => tab = 'partidos'}>
				Partidos
			</button>
			<button class="tab" class:active={tab === 'parlamentares'} role="tab" aria-selected={tab === 'parlamentares'} onclick={() => tab = 'parlamentares'}>
				Parlamentares
			</button>
		</div>

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

		<div class="filter-toggles">
			<label class="filter-toggle">
				<input type="checkbox" bind:checked={apenasAtivos} onchange={() => loadMatching()} />
				<span class="toggle-label">Só ativos (legislatura atual)</span>
			</label>
			<label class="filter-toggle">
				<input type="checkbox" bind:checked={ultimaDecada} onchange={() => loadMatching()} />
				<span class="toggle-label">Última década (2016–hoje)</span>
			</label>
		</div>

		<div class="search-row">
			<input
				class="search-input"
				type="text"
				placeholder="Buscar por nome ou partido..."
				aria-label="Buscar por nome ou partido"
				bind:value={searchQuery}
			/>
		</div>

		{#if tab === 'parlamentares'}
			<div role="tabpanel">
			<div class="casa-filter">
				<button class="casa-btn" class:active={casaFilter === 'todos'} aria-label="Filtrar por todas as casas" onclick={() => casaFilter = 'todos'}>
					Todos ({parlResults.length})
				</button>
				<button class="casa-btn" class:active={casaFilter === 'camara'} aria-label="Filtrar pela Câmara dos Deputados" onclick={() => casaFilter = 'camara'}>
					Câmara ({countCamara})
				</button>
				<button class="casa-btn" class:active={casaFilter === 'senado'} aria-label="Filtrar pelo Senado Federal" onclick={() => casaFilter = 'senado'}>
					Senado ({countSenado})
				</button>
			</div>
			<div class="lista">
				{#each parlFiltered as result, i}
					<a href="/parlamentar/{result.parlamentar_id}" class="result-card" style="animation-delay: {Math.min(i * 30, 300)}ms">
						<span class="rank">#{i + 1}</span>
						<div class="info">
							<div class="nome">{result.nome}</div>
							<div class="meta">
								{result.partido ?? 'Sem partido'} · {result.uf} · {result.casa === 'camara' ? (result.sexo === 'F' ? 'Deputada' : 'Deputado') : (result.sexo === 'F' ? 'Senadora' : 'Senador')} · {result.concordou}/{result.votos_comparados} votos em comum
							</div>
						</div>
						<div class="score">
							<ScoreDots score={result.score} votos_comparados={result.votos_comparados} loading={scopeLoading} />
						</div>
					</a>
				{/each}
			</div>
			</div>
		{:else if tab === 'partidos'}
			<div role="tabpanel">
			<div class="lista">
				{#each partidoFiltered as result, i}
					<a href="/partido/{result.partido_id}" class="result-card" style="animation-delay: {Math.min(i * 30, 300)}ms">
						<span class="rank">#{i + 1}</span>
						<div class="info">
							<div class="nome">{result.sigla}</div>
							<div class="meta">{result.nome} · {result.concordou}/{result.votos_comparados} votos em comum</div>
						</div>
						<div class="score">
							<ScoreDots score={result.score} votos_comparados={result.votos_comparados} loading={scopeLoading} />
						</div>
					</a>
				{/each}
			</div>
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

	.result-eyebrow {
		text-align: center;
		font-family: var(--font-heading);
		font-size: 0.625rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.25em;
		color: var(--text-secondary);
		margin: 0 0 0.75rem;
	}

	h1 {
		text-align: center;
		color: var(--text-primary);
		font-family: var(--font-heading);
		font-size: 2.5rem;
		font-weight: 900;
		letter-spacing: -0.04em;
		margin: 0 0 0.75rem;
	}

	.subtitle {
		text-align: center;
		color: var(--text-secondary);
		margin-bottom: 2.5rem;
		font-size: 0.875rem;
	}

	.methodology-link {
		color: var(--link);
		text-decoration: none;
		font-size: 0.813rem;
	}

	.methodology-link:hover {
		text-decoration: underline;
	}

	/* Escopo toggle */
	.escopo-toggle {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1.5rem;
	}

	.escopo-btn {
		flex: none;
		padding: 0.5rem 1rem;
		background: none;
		border: 1.5px solid var(--border);
		border-radius: 0;
		font-family: var(--font-heading);
		font-size: 0.688rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.15s;
	}

	.escopo-btn:hover {
		color: var(--text-primary);
		border-color: var(--text-primary);
	}

	.escopo-btn.active {
		color: var(--bg-page);
		background: var(--text-primary);
		border-color: var(--text-primary);
	}

	/* Tabs */
	.tabs {
		display: flex;
		gap: 0;
		margin-bottom: 2rem;
		border-bottom: 1px solid var(--border);
	}

	.tab {
		flex: 1;
		padding: 1rem 1rem;
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
		font-family: var(--font-heading);
		font-size: 0.75rem;
		font-weight: 800;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-secondary);
		cursor: pointer;
		transition: color 0.2s, border-color 0.2s;
	}

	.tab:hover {
		color: var(--text-primary);
	}

	.tab.active {
		color: var(--text-primary);
		border-bottom-color: var(--text-primary);
	}

	/* Casa filter */
	.casa-filter {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.casa-btn {
		padding: 0.375rem 0.75rem;
		border: 1.5px solid var(--border);
		border-radius: 0;
		background: transparent;
		font-size: 0.688rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.15s;
	}

	.casa-btn:hover {
		border-color: var(--text-primary);
		color: var(--text-primary);
	}

	.casa-btn.active {
		background: var(--text-primary);
		border-color: var(--text-primary);
		color: var(--bg-page);
	}

	/* Filter toggles */
	.filter-toggles {
		display: flex;
		gap: 1rem;
		margin-bottom: 1rem;
		flex-wrap: wrap;
	}

	.filter-toggle {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
		font-size: 0.813rem;
		color: var(--text-secondary);
	}

	.filter-toggle input[type="checkbox"] {
		accent-color: var(--link);
		width: 16px;
		height: 16px;
		cursor: pointer;
	}

	.toggle-label {
		user-select: none;
	}

	/* Search */
	.search-row {
		margin-bottom: 1rem;
	}

	.search-input {
		width: 100%;
		padding: 0.75rem 0;
		border: none;
		border-bottom: 1.5px solid var(--border);
		border-radius: 0;
		background: transparent;
		color: var(--text-primary);
		font-size: 0.875rem;
		font-family: var(--font-heading);
		font-weight: 500;
		outline: none;
		transition: border-color 0.2s;
		box-sizing: border-box;
	}

	.search-input:focus {
		border-color: var(--text-primary);
	}

	.search-input::placeholder {
		color: var(--text-secondary);
		font-weight: 400;
	}

	/* Result cards */
	.result-card {
		display: flex;
		align-items: center;
		gap: 1.25rem;
		background: transparent;
		border: none;
		border-bottom: 1px solid var(--border);
		border-radius: 0;
		padding: 1.25rem 0;
		margin-bottom: 0;
		text-decoration: none;
		color: inherit;
		transition: padding-left 0.2s;
	}

	.result-card:first-child {
		border-top: none;
	}

	.result-card:hover {
		padding-left: 0.5rem;
	}

	.rank {
		color: var(--text-secondary);
		font-family: var(--font-heading);
		font-weight: 900;
		font-size: 0.75rem;
		min-width: 2rem;
		letter-spacing: -0.02em;
	}

	.result-card:first-child .rank {
		color: var(--text-primary);
		font-size: 1.125rem;
	}

	.info {
		flex: 1;
	}

	.nome {
		font-family: var(--font-heading);
		font-weight: 800;
		color: var(--text-primary);
		letter-spacing: -0.02em;
	}

	.meta {
		font-size: 0.75rem;
		color: var(--text-secondary);
		margin-top: 0.25rem;
	}

	.score {
		display: flex;
		align-items: center;
	}

	/* CTA */
	.cta-section {
		text-align: center;
		margin-top: 4rem;
		padding: 3rem 2rem;
		background: transparent;
		border: none;
		border-top: 1px solid var(--border);
		border-radius: 0;
	}

	.cta-section p {
		color: var(--text-secondary);
		margin-bottom: 1.5rem;
		font-size: 0.875rem;
	}

	.cta {
		display: inline-block;
		background: var(--text-primary);
		color: var(--bg-page);
		padding: 0.875rem 2.5rem;
		border-radius: 0;
		text-decoration: none;
		font-family: var(--font-heading);
		font-weight: 800;
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		transition: opacity 0.2s;
	}

	.cta:hover {
		background: var(--text-primary);
		opacity: 0.85;
	}

	.loading, .empty {
		text-align: center;
		padding: 4rem;
		color: var(--text-secondary);
		font-size: 1.125rem;
	}

	.loading p {
		margin: 0;
	}

	.loading-spinner {
		width: 32px;
		height: 32px;
		border: 3px solid var(--border);
		border-top-color: var(--link);
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
		margin: 0 auto 1.25rem;
	}

	.loading-sub {
		font-size: 0.85rem;
		color: var(--text-secondary);
		opacity: 0.7;
		margin-top: 0.375rem !important;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Staggered card entrance */
	.result-card {
		animation: cardEntrance 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;
	}

	@keyframes cardEntrance {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
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

	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
