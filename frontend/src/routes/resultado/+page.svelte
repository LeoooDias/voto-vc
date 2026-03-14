<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { respostas, selectedUf, carregarRespostas } from '$lib/stores/questionario';
	import { authUser } from '$lib/stores/auth';
	import { resultados, resultadosPartidos, loading } from '$lib/stores/resultado';
	import type { MatchResult, PartidoMatchResult, MatchResponse } from '$lib/types';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';

	let parlResults: MatchResult[] = $state([]);
	let partidoResults: PartidoMatchResult[] = $state([]);
	let isLoading = $state(true);
	let totalRespostas = $state(0);
	let tab: 'parlamentares' | 'partidos' = $state('parlamentares');

	resultados.subscribe((v) => (parlResults = v));
	resultadosPartidos.subscribe((v) => (partidoResults = v));
	loading.subscribe((v) => (isLoading = v));

	onMount(async () => {
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

		totalRespostas = userRespostas.filter((r) => r.voto !== 'pular').length;

		loading.set(true);
		try {
			const uf = get(selectedUf);
			const data = await api.post<MatchResponse>('/matching/calcular', {
				respostas: userRespostas,
				uf: uf || undefined
			});
			resultados.set(data.parlamentares);
			resultadosPartidos.set(data.partidos);
		} catch (e) {
			console.error('Failed to calculate matching:', e);
		} finally {
			loading.set(false);
		}
	});
</script>

<svelte:head>
	<title>Seu resultado — voto.vc</title>
</svelte:head>

{#if isLoading}
	<div class="loading">Calculando seu alinhamento...</div>
{:else if parlResults.length === 0 && partidoResults.length === 0}
	<div class="empty">
		<p>Não foi possível calcular o alinhamento.</p>
		<a href="/questionario">Tentar novamente</a>
	</div>
{:else}
	<div class="resultado">
		<h1>Seu alinhamento político</h1>
		<p class="subtitle">Baseado nos seus {totalRespostas} votos</p>

		<div class="tabs">
			<button
				class="tab"
				class:active={tab === 'parlamentares'}
				onclick={() => tab = 'parlamentares'}
			>
				Parlamentares
			</button>
			<button
				class="tab"
				class:active={tab === 'partidos'}
				onclick={() => tab = 'partidos'}
			>
				Partidos
			</button>
		</div>

		{#if tab === 'parlamentares'}
			<div class="lista">
				{#each parlResults as result, i}
					<a href="/parlamentar/{result.parlamentar_id}" class="parlamentar-card">
						<span class="rank">#{i + 1}</span>
						<div class="info">
							<div class="nome">{result.nome}</div>
							<div class="meta">
								{result.partido ?? 'Sem partido'} · {result.uf} · {result.casa === 'camara' ? (result.sexo === 'F' ? 'Deputada' : 'Deputado') : (result.sexo === 'F' ? 'Senadora' : 'Senador')}
							</div>
						</div>
						<div class="score" class:high={result.score >= 70} class:mid={result.score >= 40 && result.score < 70} class:low={result.score < 40}>
							{result.score}%
						</div>
					</a>
				{/each}
			</div>
		{:else}
			<div class="lista">
				{#each partidoResults as result, i}
					<a href="/partido/{result.partido_id}" class="partido-card">
						<span class="rank">#{i + 1}</span>
						<div class="info">
							<div class="nome">{result.sigla}</div>
							<div class="meta">{result.nome} · {result.parlamentares_comparados} parlamentar{result.parlamentares_comparados !== 1 ? 'es' : ''}</div>
						</div>
						<div class="score" class:high={result.score >= 70} class:mid={result.score >= 40 && result.score < 70} class:low={result.score < 40}>
							{result.score}%
						</div>
					</a>
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
	.resultado {
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
		margin-bottom: 1.5rem;
	}

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

	.parlamentar-card, .partido-card {
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

	.parlamentar-card:hover, .partido-card:hover {
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
</style>
