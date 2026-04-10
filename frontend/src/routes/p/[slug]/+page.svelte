<script lang="ts">
	import { _ } from 'svelte-i18n';
	import type { PerfilCompartilhado } from '$lib/types';
	import ScoreDots from '$lib/components/ScoreDots.svelte';

	const { data } = $props();
	let perfil = $derived(data.perfil as PerfilCompartilhado);
	let slug = $derived(data.slug as string);

	let tab: 'partidos' | 'parlamentares' | 'votos' = $state('partidos');

	let ogImageUrl = $derived(`https://voto.vc/api/perfil/${slug}/og.png`);
</script>

<svelte:head>
	<title>{$_('perfilCompartilhado.title')}</title>
	<meta property="og:title" content={$_('perfilCompartilhado.seuAlinhamento') + ' — voto.vc'} />
	<meta property="og:description" content={`Top: ${perfil.partidos[0]?.sigla ?? '?'} · ${$_('perfilCompartilhado.baseadoNos', { values: { count: perfil.total_respostas } })}`} />
	<meta property="og:image" content={ogImageUrl} />
	<meta property="og:image:width" content="1200" />
	<meta property="og:image:height" content="630" />
	<meta property="og:type" content="website" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:image" content={ogImageUrl} />
</svelte:head>

<div class="shared-page">
	<a href="/vote" class="cta-top">{$_('perfilCompartilhado.cta')}</a>

	<p class="result-eyebrow">voto.vc</p>
	<h1>{$_('perfilCompartilhado.seuAlinhamento')}</h1>
	<p class="subtitle">{$_('perfilCompartilhado.baseadoNos', { values: { count: perfil.total_respostas } })}</p>

	<div class="tabs" role="tablist">
		<button class="tab" class:active={tab === 'partidos'} role="tab" aria-selected={tab === 'partidos'} onclick={() => tab = 'partidos'}>
			{$_('perfilCompartilhado.partidos')}
		</button>
		<button class="tab" class:active={tab === 'parlamentares'} role="tab" aria-selected={tab === 'parlamentares'} onclick={() => tab = 'parlamentares'}>
			{$_('perfilCompartilhado.parlamentares')}
		</button>
		<button class="tab" class:active={tab === 'votos'} role="tab" aria-selected={tab === 'votos'} onclick={() => tab = 'votos'}>
			{$_('perfilCompartilhado.votos')}
		</button>
	</div>

	{#if tab === 'partidos'}
		<div role="tabpanel" class="lista">
			{#each perfil.partidos as result, i (result.partido_id)}
				<a href="/partido/{result.partido_id}" class="result-card" style="animation-delay: {Math.min(i * 30, 300)}ms">
					<span class="rank">#{i + 1}</span>
					<div class="info">
						<div class="nome">{result.sigla}</div>
						<div class="meta">{result.nome} · {$_('perfilCompartilhado.votosEmComum', { values: { concordou: result.concordou, total: result.votos_comparados } })}</div>
					</div>
					<div class="score">
						<ScoreDots score={result.score} votos_comparados={result.votos_comparados} />
					</div>
				</a>
			{/each}
		</div>
	{:else if tab === 'parlamentares'}
		<div role="tabpanel" class="lista">
			{#each perfil.parlamentares as result, i (result.parlamentar_id)}
				<a href="/parlamentar/{result.parlamentar_id}" class="result-card" style="animation-delay: {Math.min(i * 30, 300)}ms">
					<span class="rank">#{i + 1}</span>
					<div class="info">
						<div class="nome">{result.nome}</div>
						<div class="meta">
							{result.partido ?? $_('perfilCompartilhado.semPartido')} · {result.uf} · {result.casa === 'camara' ? (result.sexo === 'F' ? $_('perfilCompartilhado.deputada') : $_('perfilCompartilhado.deputado')) : (result.sexo === 'F' ? $_('perfilCompartilhado.senadora') : $_('perfilCompartilhado.senador'))} · {$_('perfilCompartilhado.votosEmComum', { values: { concordou: result.concordou, total: result.votos_comparados } })}
						</div>
					</div>
					<div class="score">
						<ScoreDots score={result.score} votos_comparados={result.votos_comparados} />
					</div>
				</a>
			{/each}
		</div>
	{:else if tab === 'votos'}
		<div role="tabpanel" class="lista votos-lista">
			{#each perfil.votos_detalhados as voto, i (voto.proposicao_id)}
				<div class="voto-card" style="animation-delay: {Math.min(i * 20, 300)}ms">
					<span class="voto-badge" class:sim={voto.voto === 'sim'} class:nao={voto.voto === 'nao'}>
						{voto.voto === 'sim' ? $_('perfilCompartilhado.sim') : $_('perfilCompartilhado.nao')}
					</span>
					<div class="voto-info">
						<div class="voto-titulo">{voto.tipo} {voto.numero}/{voto.ano}</div>
						<div class="voto-resumo">{voto.resumo}</div>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	<div class="cta-bottom">
		<a href="/vote" class="cta-link">{$_('perfilCompartilhado.ctaRodape')}</a>
	</div>
</div>

<style>
	.shared-page {
		max-width: 700px;
		margin: 0 auto;
	}

	.cta-top {
		display: block;
		text-align: center;
		padding: 0.875rem;
		background: var(--text-primary);
		color: var(--bg-page);
		font-family: var(--font-heading);
		font-size: 0.75rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		text-decoration: none;
		margin-bottom: 2.5rem;
		transition: opacity 0.15s;
	}

	.cta-top:hover {
		opacity: 0.85;
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

	/* Tabs */
	.tabs {
		display: flex;
		gap: 0;
		margin-bottom: 2rem;
		border-bottom: 1px solid var(--border);
	}

	.tab {
		flex: 1;
		padding: 1rem;
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
		text-decoration: none;
		color: inherit;
		transition: padding-left 0.2s;
		animation: cardEntrance 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;
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

	/* Votos tab */
	.voto-card {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		padding: 1rem 0;
		border-bottom: 1px solid var(--border);
		animation: cardEntrance 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;
	}

	.voto-badge {
		flex-shrink: 0;
		padding: 0.25rem 0.625rem;
		font-family: var(--font-heading);
		font-size: 0.625rem;
		font-weight: 800;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		border: 1.5px solid;
		min-width: 2.5rem;
		text-align: center;
	}

	.voto-badge.sim {
		color: var(--vote-sim);
		border-color: var(--vote-sim);
	}

	.voto-badge.nao {
		color: var(--vote-nao);
		border-color: var(--vote-nao);
	}

	.voto-info {
		flex: 1;
	}

	.voto-titulo {
		font-family: var(--font-heading);
		font-size: 0.75rem;
		font-weight: 700;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.voto-resumo {
		font-size: 0.875rem;
		color: var(--text-primary);
		margin-top: 0.25rem;
		line-height: 1.4;
	}

	/* CTA bottom */
	.cta-bottom {
		text-align: center;
		padding: 3rem 0;
	}

	.cta-link {
		padding: 1rem 3rem;
		background: var(--text-primary);
		color: var(--bg-page);
		font-family: var(--font-heading);
		font-size: 0.875rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		text-decoration: none;
		transition: opacity 0.15s;
	}

	.cta-link:hover {
		opacity: 0.85;
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
</style>
