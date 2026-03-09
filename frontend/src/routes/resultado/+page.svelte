<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { respostas } from '$lib/stores/questionario';
	import { resultados, loading } from '$lib/stores/resultado';
	import type { MatchResult } from '$lib/types';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';

	let results: MatchResult[] = $state([]);
	let isLoading = $state(true);

	resultados.subscribe((v) => (results = v));
	loading.subscribe((v) => (isLoading = v));

	onMount(async () => {
		const userRespostas = get(respostas);
		if (userRespostas.length === 0) {
			goto('/questionario');
			return;
		}

		loading.set(true);
		try {
			const data = await api.post<MatchResult[]>('/matching/calcular', {
				respostas: userRespostas
			});
			resultados.set(data);
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
{:else if results.length === 0}
	<div class="empty">
		<p>Não foi possível calcular o alinhamento.</p>
		<a href="/questionario">Tentar novamente</a>
	</div>
{:else}
	<div class="resultado">
		<h1>Seus parlamentares mais alinhados</h1>
		<p class="subtitle">Baseado nas suas {get(respostas).length} respostas</p>

		<div class="lista">
			{#each results as result, i}
				<a href="/parlamentar/{result.parlamentar_id}" class="parlamentar-card">
					<span class="rank">#{i + 1}</span>
					<div class="info">
						<div class="nome">{result.nome}</div>
						<div class="meta">
							{result.partido ?? 'Sem partido'} · {result.uf} · {result.casa === 'camara' ? 'Deputado(a)' : 'Senador(a)'}
						</div>
					</div>
					<div class="score" class:high={result.score >= 70} class:mid={result.score >= 40 && result.score < 70} class:low={result.score < 40}>
						{result.score}%
					</div>
				</a>
			{/each}
		</div>

		<div class="cta-section">
			<p>Quer acompanhar novas votações e atualizar seu perfil?</p>
			<a href="/conta/registrar" class="cta">Criar conta</a>
		</div>
	</div>
{/if}

<style>
	.resultado {
		max-width: 700px;
		margin: 0 auto;
	}

	h1 {
		text-align: center;
		color: #1a1a2e;
	}

	.subtitle {
		text-align: center;
		color: #9ca3af;
		margin-bottom: 2rem;
	}

	.parlamentar-card {
		display: flex;
		align-items: center;
		gap: 1rem;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 12px;
		padding: 1rem 1.5rem;
		margin-bottom: 0.75rem;
		text-decoration: none;
		color: inherit;
		transition: border-color 0.2s;
	}

	.parlamentar-card:hover {
		border-color: #2563eb;
	}

	.rank {
		color: #9ca3af;
		font-weight: 700;
		font-size: 1.125rem;
		min-width: 2.5rem;
	}

	.info {
		flex: 1;
	}

	.nome {
		font-weight: 600;
		color: #1a1a2e;
	}

	.meta {
		font-size: 0.875rem;
		color: #6b7280;
		margin-top: 0.25rem;
	}

	.score {
		font-size: 1.5rem;
		font-weight: 700;
	}

	.high {
		color: #16a34a;
	}

	.mid {
		color: #ca8a04;
	}

	.low {
		color: #dc2626;
	}

	.cta-section {
		text-align: center;
		margin-top: 3rem;
		padding: 2rem;
		background: #eff6ff;
		border-radius: 16px;
	}

	.cta-section p {
		color: #4b5563;
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

	.loading,
	.empty {
		text-align: center;
		padding: 4rem;
		color: #6b7280;
		font-size: 1.125rem;
	}
</style>
