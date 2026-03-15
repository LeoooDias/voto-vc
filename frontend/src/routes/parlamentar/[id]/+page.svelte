<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { api } from '$lib/api';
	import { getTema } from '$lib/constants';

	interface ParlamentarDetail {
		id: number;
		nome_parlamentar: string;
		nome_civil: string;
		casa: string;
		uf: string;
		sexo: string | null;
		foto_url: string | null;
		partido: { sigla: string; nome: string } | null;
		legislatura_atual: boolean;
		stats: Record<string, number>;
		votos: VotoHistory[];
	}

	interface VotoHistory {
		voto: string;
		partido_na_epoca: string | null;
		data: string | null;
		descricao_votacao: string | null;
		proposicao_id: number | null;
		proposicao_tipo: string | null;
		proposicao_numero: number | null;
		proposicao_ano: number | null;
		proposicao_ementa: string | null;
		resumo_cidadao: string | null;
		descricao_detalhada: string | null;
		tema: string | null;
		url_camara: string | null;
		substantiva: boolean;
	}

	let parlamentar = $state<ParlamentarDetail | null>(null);
	let error = $state(false);
	let expandedId: number | null = $state(null);
	let soSubstantivas = $state(false);

	let allVotos = $derived((parlamentar?.votos ?? []) as VotoHistory[]);

	let votosVisiveis = $derived<VotoHistory[]>(
		soSubstantivas
			? allVotos.filter((v: VotoHistory) => v.substantiva)
			: allVotos
	);

	let countSubstantivas = $derived(
		allVotos.filter((v: VotoHistory) => v.substantiva).length
	);

	onMount(async () => {
		try {
			parlamentar = await api.get<ParlamentarDetail>(`/parlamentares/${page.params.id}`);
		} catch (e) {
			console.error('Failed to load parlamentar:', e);
			error = true;
		}
	});

	function toggleExpand(proposicaoId: number | null) {
		if (!proposicaoId) return;
		expandedId = expandedId === proposicaoId ? null : proposicaoId;
	}

	function votoLabel(voto: string): string {
		const map: Record<string, string> = {
			sim: 'A favor',
			nao: 'Contra',
			abstencao: 'Abstenção',
			obstrucao: 'Obstrução',
			ausente: 'Ausente',
			presente_sem_voto: 'Presente s/ voto'
		};
		return map[voto] || voto;
	}

	function votoClass(voto: string): string {
		if (voto === 'sim') return 'voto-sim';
		if (voto === 'nao') return 'voto-nao';
		return 'voto-outro';
	}

	function formatDate(iso: string | null): string {
		if (!iso) return '';
		try {
			return new Date(iso).toLocaleDateString('pt-BR');
		} catch {
			return '';
		}
	}

</script>

<svelte:head>
	<title>{parlamentar?.nome_parlamentar ?? 'Parlamentar'} — voto.vc</title>
</svelte:head>

{#if error}
	<div class="empty">Parlamentar não encontrado.</div>
{:else if !parlamentar}
	<div class="loading">Carregando...</div>
{:else}
	<div class="perfil">
		<div class="header">
			{#if parlamentar.foto_url}
				<img src={parlamentar.foto_url} alt={parlamentar.nome_parlamentar} class="foto" />
			{/if}
			<div class="header-info">
				<h1>{parlamentar.nome_parlamentar}</h1>
				<p class="meta">
					{parlamentar.partido?.sigla ?? 'Sem partido'} · {parlamentar.uf} ·
					{parlamentar.casa === 'camara' ? (parlamentar.sexo === 'F' ? 'Deputada Federal' : 'Deputado Federal') : (parlamentar.sexo === 'F' ? 'Senadora' : 'Senador')}
				</p>
				{#if parlamentar.nome_civil !== parlamentar.nome_parlamentar}
					<p class="nome-civil">{parlamentar.nome_civil}</p>
				{/if}
			</div>
		</div>

		{#if Object.keys(parlamentar.stats).length > 0}
			<div class="stats">
				<h2>Resumo de votações</h2>
				<div class="stats-grid">
					{#each Object.entries(parlamentar.stats) as [voto, count]}
						<div class="stat-item {votoClass(voto)}">
							<span class="stat-count">{count}</span>
							<span class="stat-label">{votoLabel(voto)}</span>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		{#if parlamentar.votos.length > 0}
			<div class="historico">
				<div class="historico-header">
					<h2>Histórico de votações</h2>
					{#if countSubstantivas > 0 && countSubstantivas < parlamentar.votos.length}
						<label class="filter-toggle">
							<input type="checkbox" bind:checked={soSubstantivas} />
							Só proposições substantivas ({countSubstantivas})
						</label>
					{/if}
				</div>

				{#each votosVisiveis as voto}
					{@const hasDetails = voto.substantiva && (voto.resumo_cidadao || voto.descricao_detalhada)}
					{@const isExpanded = expandedId === voto.proposicao_id}
					<button
						type="button"
						class="voto-card"
						class:expandable={hasDetails}
						class:expanded={isExpanded}
						onclick={() => hasDetails && toggleExpand(voto.proposicao_id)}
					>
						<div class="voto-main">
							<span class="voto-badge {votoClass(voto.voto)}">{votoLabel(voto.voto)}</span>
							<div class="voto-info">
								<div class="voto-top">
									{#if voto.proposicao_tipo}
										<span class="voto-tipo">{voto.proposicao_tipo} {voto.proposicao_numero}/{voto.proposicao_ano}</span>
									{/if}
									{#if voto.tema}
										{@const info = getTema(voto.tema)}
										<span class="tema-tag" style="background: {info.cor}1a; color: {info.cor}; border-color: {info.cor}33">{info.label}</span>
									{/if}
								</div>
								<p class="voto-ementa">
									{voto.proposicao_ementa ?? voto.descricao_votacao ?? 'Sem descrição'}
								</p>
								{#if voto.data}
									<span class="voto-data">{formatDate(voto.data)}</span>
								{/if}
							</div>
							{#if hasDetails}
								<span class="expand-icon" class:open={isExpanded}>▾</span>
							{/if}
						</div>

						{#if isExpanded}
							<div class="voto-details">
								{#if voto.resumo_cidadao}
									<p class="detail-resumo">{voto.resumo_cidadao}</p>
								{/if}
								{#if voto.descricao_detalhada}
									<p class="detail-descricao">{voto.descricao_detalhada}</p>
								{/if}
								{#if voto.url_camara}
									<a href={voto.url_camara} target="_blank" rel="noopener" class="link-camara" onclick={(e) => e.stopPropagation()}>Ver na Câmara</a>
								{/if}
							</div>
						{/if}
					</button>
				{/each}
			</div>
		{:else}
			<p class="empty-votos">Nenhum voto registrado.</p>
		{/if}

		<a href="/resultado" class="back">Voltar ao resultado</a>
	</div>
{/if}

<style>
	.perfil {
		max-width: 700px;
		margin: 0 auto;
	}

	.header {
		display: flex;
		gap: 1.5rem;
		align-items: center;
		margin-bottom: 2rem;
	}

	.foto {
		width: 100px;
		height: 100px;
		border-radius: 50%;
		object-fit: cover;
		border: 3px solid var(--border);
	}

	h1 {
		margin: 0;
		color: var(--text-primary);
	}

	.meta {
		color: var(--text-secondary);
		margin: 0.25rem 0 0;
	}

	.nome-civil {
		color: var(--text-secondary);
		font-size: 0.875rem;
		margin: 0.25rem 0 0;
	}

	h2 {
		color: var(--text-primary);
		font-size: 1.125rem;
		margin: 0;
	}

	.stats {
		margin-bottom: 2rem;
	}

	.stats h2 {
		margin-bottom: 1rem;
	}

	.stats-grid {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.stat-item {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1rem 1.25rem;
		text-align: center;
		min-width: 80px;
	}

	.stat-count {
		display: block;
		font-size: 1.5rem;
		font-weight: 700;
	}

	.stat-label {
		font-size: 0.8rem;
		color: var(--text-secondary);
	}

	.stat-item.voto-sim .stat-count { color: #16a34a; }
	.stat-item.voto-nao .stat-count { color: #dc2626; }
	.stat-item.voto-outro .stat-count { color: var(--text-secondary); }

	.historico-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.filter-toggle {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.8rem;
		color: var(--text-secondary);
		cursor: pointer;
		user-select: none;
	}

	.filter-toggle input {
		accent-color: var(--link);
	}

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
		transition: border-color 0.2s;
	}

	.voto-card.expandable {
		cursor: pointer;
	}

	.voto-card.expandable:hover {
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
	.voto-badge.voto-outro { background: #6b72801a; color: var(--text-secondary); }

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

	.voto-ementa {
		margin: 0.5rem 0 0;
		font-size: 0.9rem;
		color: var(--text-primary);
		line-height: 1.4;
	}

	.voto-data {
		font-size: 0.8rem;
		color: var(--text-secondary);
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

	.detail-resumo {
		font-size: 1rem;
		color: var(--text-primary);
		line-height: 1.6;
		margin: 0 0 0.75rem;
		font-weight: 500;
	}

	.detail-descricao {
		font-size: 0.9rem;
		color: var(--text-secondary);
		line-height: 1.6;
		margin: 0 0 0.75rem;
	}

	.link-camara {
		color: var(--link);
		font-size: 0.8rem;
		text-decoration: none;
	}

	.link-camara:hover {
		text-decoration: underline;
	}

	.back {
		display: inline-block;
		margin-top: 2rem;
		color: var(--link);
		text-decoration: none;
	}

	.back:hover { text-decoration: underline; }

	.loading, .empty {
		text-align: center;
		padding: 4rem;
		color: var(--text-secondary);
	}

	.empty-votos {
		color: var(--text-secondary);
		text-align: center;
		padding: 2rem;
	}
</style>
