<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { respostas, selectedUf, carregarRespostas } from '$lib/stores/questionario';
	import { authUser, authLoading } from '$lib/stores/auth';
	import type { PartidoMatchResult, MatchResponse } from '$lib/types';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';

	let results: PartidoMatchResult[] = $state([]);
	let isLoading = $state(true);
	let sortKey: 'sigla' | 'score' | 'parlamentares_comparados' = $state('score');
	let sortAsc = $state(false);
	let perPage = $state(25);
	let currentPage = $state(1);

	let sorted = $derived(
		[...results].sort((a, b) => {
			const va = a[sortKey];
			const vb = b[sortKey];
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

	async function load() {
		let userRespostas = get(respostas);
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
		try {
			const uf = get(selectedUf);
			const data = await api.post<MatchResponse>('/matching/calcular', {
				respostas: userRespostas,
				uf: uf || undefined,
				limit: 1000
			});
			results = data.partidos;
		} catch (e) {
			console.error('Failed to load:', e);
		} finally {
			isLoading = false;
		}
	}

	onMount(() => {
		if (!get(authLoading)) { load(); return; }
		const unsub = authLoading.subscribe((l) => {
			if (!l) { unsub(); load(); }
		});
	});
</script>

<svelte:head>
	<title>Partidos — voto.vc</title>
</svelte:head>

{#if isLoading}
	<div class="loading">Calculando alinhamento...</div>
{:else}
	<div class="page">
		<div class="page-header">
			<h1>Partidos</h1>
			<div class="controls">
				<select bind:value={perPage} onchange={() => currentPage = 1}>
					<option value={10}>10</option>
					<option value={25}>25</option>
					<option value={50}>50</option>
					<option value={1000}>Todos</option>
				</select>
			</div>
		</div>

		<div class="table-wrap">
			<table>
				<thead>
					<tr>
						<th class="col-rank">#</th>
						<th class="col-name sortable" onclick={() => toggleSort('sigla')}>Partido{sortIndicator('sigla')}</th>
						<th class="col-full-name">Nome</th>
						<th class="col-num sortable" onclick={() => toggleSort('parlamentares_comparados')}>Parlamentares{sortIndicator('parlamentares_comparados')}</th>
						<th class="col-score sortable" onclick={() => toggleSort('score')}>Alinhamento{sortIndicator('score')}</th>
					</tr>
				</thead>
				<tbody>
					{#each paged as result, i}
						<tr>
							<td class="col-rank">{(currentPage - 1) * perPage + i + 1}</td>
							<td class="col-name"><a href="/partido/{result.partido_id}">{result.sigla}</a></td>
							<td class="col-full-name">{result.nome}</td>
							<td class="col-num">{result.parlamentares_comparados}</td>
							<td class="col-score">
								<span class="score" class:high={result.score >= 70} class:mid={result.score >= 40 && result.score < 70} class:low={result.score < 40}>
									{result.score}%
								</span>
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
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	h1 {
		margin: 0;
		color: var(--text-primary);
	}

	.controls {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}

	select {
		padding: 0.375rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-card);
		color: var(--text-primary);
		font-size: 0.875rem;
		cursor: pointer;
	}

	.table-wrap {
		overflow-x: auto;
	}

	table {
		width: 100%;
		border-collapse: collapse;
	}

	thead {
		border-bottom: 2px solid var(--border);
	}

	th {
		text-align: left;
		padding: 0.625rem 0.75rem;
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--text-secondary);
		white-space: nowrap;
	}

	th.sortable {
		cursor: pointer;
		user-select: none;
	}

	th.sortable:hover {
		color: var(--link);
	}

	td {
		padding: 0.625rem 0.75rem;
		border-bottom: 1px solid var(--border);
		font-size: 0.938rem;
		color: var(--text-primary);
	}

	tr:hover td {
		background: var(--bg-page);
	}

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

	.col-name a:hover {
		text-decoration: underline;
	}

	.col-full-name {
		color: var(--text-secondary);
		font-size: 0.875rem;
	}

	td.col-full-name {
		color: var(--text-secondary);
		font-size: 0.875rem;
	}

	.col-num {
		text-align: center;
	}

	.col-score {
		text-align: right;
	}

	.score {
		font-weight: 700;
	}

	.high { color: #16a34a; }
	.mid { color: #ca8a04; }
	.low { color: #dc2626; }

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

	.pagination button:disabled {
		opacity: 0.4;
		cursor: default;
	}

	.pagination button:not(:disabled):hover {
		border-color: var(--link);
	}

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
</style>
