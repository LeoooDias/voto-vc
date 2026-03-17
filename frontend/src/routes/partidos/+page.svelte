<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { respostas, selectedUf, carregarRespostas } from '$lib/stores/questionario';
	import { authUser, authLoading } from '$lib/stores/auth';
	import type { PartidoMatchResult, MatchResponse } from '$lib/types';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { UF_SIGLAS, fmtPct } from '$lib/constants';

	let results: PartidoMatchResult[] = $state([]);
	let isLoading = $state(true);
	let sortKey: 'sigla' | 'score' | 'parlamentares_comparados' | 'votos_comparados' | 'concordou' = $state('score');
	let sortAsc = $state(false);
	let perPage = $state(25);
	let currentPage = $state(1);
	let escopo: 'brasil' | 'estado' = $state('brasil');
	let ufSelecionada = $state('');
	let showUfPicker = $state(false);
	let scopeLoading = $state(false);

	let sorted = $derived(
		[...results].sort((a, b) => {
			const va = a[sortKey];
			const vb = b[sortKey];
			if (va == null && vb == null) return 0;
			if (va == null) return 1;
			if (vb == null) return -1;
			if (typeof va === 'string' && typeof vb === 'string') {
				return sortAsc ? va.localeCompare(vb, 'pt-BR') : vb.localeCompare(va, 'pt-BR');
			}
			return sortAsc ? (va as number) - (vb as number) : (vb as number) - (va as number);
		})
	);

	let totalPages = $derived(Math.ceil(sorted.length / perPage));
	let paged = $derived(sorted.slice((currentPage - 1) * perPage, currentPage * perPage));

	function toggleSort(key: typeof sortKey) {
		if (sortKey === key) {
			sortAsc = !sortAsc;
		} else {
			sortKey = key;
			sortAsc = key === 'sigla';
		}
		currentPage = 1;
	}

	function sortIndicator(key: string): string {
		if (sortKey !== key) return '';
		return sortAsc ? ' ▲' : ' ▼';
	}

	$effect(() => {
		perPage;
		currentPage = 1;
	});

	let userRespostas: { proposicao_id: number; voto: string; peso: number }[] = [];

	async function loadData() {
		const isInitial = results.length === 0;
		if (isInitial) isLoading = true;
		scopeLoading = true;
		try {
			const data = await api.post<MatchResponse>('/matching/calcular', {
				respostas: userRespostas,
				uf: escopo === 'estado' ? (ufSelecionada || undefined) : undefined,
				limit: 1000
			});
			results = data.partidos;
		} catch (e) {
			console.error('Failed to load:', e);
		} finally {
			isLoading = false;
			scopeLoading = false;
		}
	}

	function setEscopo(novo: 'brasil' | 'estado') {
		if (novo === 'estado' && !ufSelecionada) {
			showUfPicker = true;
			return;
		}
		escopo = novo;
		loadData();
	}

	function escolherUf(sigla: string) {
		ufSelecionada = sigla;
		selectedUf.set(sigla);
		showUfPicker = false;
		escopo = 'estado';
		loadData();
	}

	async function init() {
		userRespostas = get(respostas) as typeof userRespostas;
		if (userRespostas.length === 0 && get(authUser)) {
			const saved = await carregarRespostas();
			if (saved.length > 0) {
				respostas.set(saved);
				userRespostas = saved;
			}
		}
		if (userRespostas.length === 0) {
			goto('/vote');
			return;
		}
		const user = get(authUser);
		if (user?.uf) {
			ufSelecionada = user.uf;
		} else {
			const storeUf = get(selectedUf);
			if (storeUf) ufSelecionada = storeUf;
		}
		if (ufSelecionada) escopo = 'estado';
		await loadData();
	}

	onMount(() => {
		if (!get(authLoading)) { init(); return; }
		const unsub = authLoading.subscribe((l) => {
			if (!l) { unsub(); init(); }
		});
	});
</script>

<svelte:head>
	<title>Partidos — voto.vc</title>
</svelte:head>

{#if showUfPicker}
	<div class="uf-selector">
		<h1>De qual estado?</h1>
		<p class="uf-subtitle">Filtrar partidos por estado</p>
		<div class="uf-grid">
			{#each UF_SIGLAS as sigla}
				<button class="uf-btn" onclick={() => escolherUf(sigla)}>{sigla}</button>
			{/each}
		</div>
		<button class="uf-cancel" onclick={() => showUfPicker = false}>Cancelar</button>
	</div>
{:else if isLoading}
	<div class="loading">Calculando alinhamento...</div>
{:else}
	<div class="page">
		<div class="page-header">
			<h1>Partidos</h1>
			<div class="controls">
				<label class="per-page-label">
					<select bind:value={perPage}>
						<option value={10}>10</option>
						<option value={25}>25</option>
						<option value={50}>50</option>
						<option value={1000}>Todos</option>
					</select>
					partidos por página
				</label>
			</div>
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

		<div class="table-wrap">
			<table>
				<thead>
					<tr>
						<th class="col-rank">#</th>
						<th class="col-name sortable" onclick={() => toggleSort('sigla')}>Partido{sortIndicator('sigla')}</th>
						<th class="col-num sortable" onclick={() => toggleSort('parlamentares_comparados')}>Parlamentares{sortIndicator('parlamentares_comparados')}</th>
						<th class="col-num sortable" onclick={() => toggleSort('votos_comparados')}>Votos Comparados{sortIndicator('votos_comparados')}</th>
						<th class="col-num sortable" onclick={() => toggleSort('concordou')}>Votos Em Comum{sortIndicator('concordou')}</th>
						<th class="col-score sortable" onclick={() => toggleSort('score')}>Alinhamento{sortIndicator('score')}</th>
					</tr>
				</thead>
				<tbody>
					{#each paged as result, i}
						<tr>
							<td class="col-rank">{(currentPage - 1) * perPage + i + 1}</td>
							<td class="col-name">
								<a href="/partido/{result.partido_id}">{result.sigla}</a>
								<span class="nome-full">{result.nome}</span>
							</td>
							<td class="col-num">{#if scopeLoading}<span class="spinner"></span>{:else}{result.parlamentares_comparados}{/if}</td>
							<td class="col-num">{#if scopeLoading}<span class="spinner"></span>{:else}{result.votos_comparados}{/if}</td>
							<td class="col-num">{#if scopeLoading}<span class="spinner"></span>{:else}{result.concordou}{/if}</td>
							<td class="col-score">
								{#if scopeLoading}
									<span class="spinner"></span>
								{:else if result.score != null}
									<span class="score" class:high={result.score >= 70} class:mid={result.score >= 40 && result.score < 70} class:low={result.score < 40}>
										{fmtPct(result.score)}
									</span>
								{:else}
									<span class="score-na" title="Dados insuficientes">N/A</span>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		{#if totalPages > 1}
			<div class="pagination">
				<button onclick={() => currentPage--} disabled={currentPage <= 1}>Anterior</button>
				<span>Página {currentPage} de {totalPages}</span>
				<button onclick={() => currentPage++} disabled={currentPage >= totalPages}>Próxima</button>
			</div>
		{/if}
	</div>
{/if}

<style>
	.page {
		max-width: 800px;
		margin: 0 auto;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	h1 {
		margin: 0;
		color: var(--text-primary);
	}

	.controls {
		display: flex;
		align-items: center;
	}

	.per-page-label {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.813rem;
		color: var(--text-secondary);
	}

	select {
		padding: 0.3rem 1.5rem 0.3rem 0.5rem;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--bg-card);
		color: var(--text-primary);
		font-size: 0.813rem;
		cursor: pointer;
		min-width: 4.5rem;
	}

	.escopo-toggle {
		display: flex;
		gap: 0;
		margin-bottom: 1.5rem;
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

	.escopo-btn:hover { color: var(--text-primary); }
	.escopo-btn.active { color: var(--link); border-bottom-color: var(--link); }

	.table-wrap { overflow-x: auto; }

	table { width: 100%; border-collapse: collapse; }
	thead { border-bottom: 2px solid var(--border); }

	th {
		text-align: left;
		padding: 0.625rem 0.75rem;
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--text-secondary);
		white-space: nowrap;
	}

	th.sortable { cursor: pointer; user-select: none; }
	th.sortable:hover { color: var(--link); }

	td {
		padding: 0.625rem 0.75rem;
		border-bottom: 1px solid var(--border);
		font-size: 0.938rem;
		color: var(--text-primary);
	}

	tr:hover td { background: var(--bg-page); }

	.col-rank {
		width: 3rem;
		color: var(--text-secondary);
		font-weight: 600;
	}

	.col-name a {
		color: var(--link);
		text-decoration: none;
		font-weight: 600;
	}

	.col-name a:hover { text-decoration: underline; }

	.nome-full {
		display: block;
		font-size: 0.75rem;
		color: var(--text-secondary);
		font-weight: 400;
	}

	.col-num { text-align: center; }
	.col-score { text-align: right; }

	.score { font-weight: 700; }
	.high { color: #16a34a; }
	.mid { color: #ca8a04; }
	.low { color: #dc2626; }

	.score-na {
		color: var(--text-secondary);
		font-style: italic;
		font-size: 0.813rem;
		cursor: help;
	}

	.pagination {
		display: flex;
		justify-content: center;
		align-items: center;
		gap: 1rem;
		margin-top: 1.5rem;
		padding-bottom: 2rem;
	}

	.pagination button {
		padding: 0.5rem 1rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-card);
		color: var(--text-primary);
		cursor: pointer;
		font-weight: 500;
	}

	.pagination button:disabled { opacity: 0.4; cursor: default; }
	.pagination button:not(:disabled):hover { border-color: var(--link); }

	.pagination span {
		color: var(--text-secondary);
		font-size: 0.875rem;
	}

	.loading {
		text-align: center;
		padding: 4rem;
		color: var(--text-secondary);
		font-size: 1.125rem;
	}

	.uf-selector { max-width: 500px; margin: 0 auto; text-align: center; }
	.uf-selector h1 { color: var(--text-primary); margin-bottom: 0.25rem; }
	.uf-subtitle { color: var(--text-secondary); margin-bottom: 1.5rem; }

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

	.uf-btn:hover { border-color: var(--link); }

	.uf-cancel {
		margin-top: 1.5rem;
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		font-size: 0.875rem;
	}

	.uf-cancel:hover { color: var(--text-primary); }

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
