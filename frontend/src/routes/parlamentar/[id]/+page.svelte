<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { api } from '$lib/api';

	interface ParlamentarDetail {
		id: number;
		nome_parlamentar: string;
		nome_civil: string;
		casa: string;
		uf: string;
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
	}

	let parlamentar: ParlamentarDetail | null = $state(null);
	let error = $state(false);

	onMount(async () => {
		try {
			parlamentar = await api.get<ParlamentarDetail>(`/parlamentares/${page.params.id}`);
		} catch (e) {
			console.error('Failed to load parlamentar:', e);
			error = true;
		}
	});

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
					{parlamentar.casa === 'camara' ? 'Deputado(a) Federal' : 'Senador(a)'}
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
				<h2>Histórico de votações</h2>
				{#each parlamentar.votos as voto}
					<div class="voto-card">
						<span class="voto-badge {votoClass(voto.voto)}">{votoLabel(voto.voto)}</span>
						<div class="voto-info">
							{#if voto.proposicao_tipo}
								<span class="voto-tipo">{voto.proposicao_tipo} {voto.proposicao_numero}/{voto.proposicao_ano}</span>
							{/if}
							<p class="voto-ementa">
								{voto.proposicao_ementa ?? voto.descricao_votacao ?? 'Sem descrição'}
							</p>
							{#if voto.data}
								<span class="voto-data">{formatDate(voto.data)}</span>
							{/if}
						</div>
					</div>
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
		border: 3px solid #e5e7eb;
	}

	h1 {
		margin: 0;
		color: #1a1a2e;
	}

	.meta {
		color: #6b7280;
		margin: 0.25rem 0 0;
	}

	.nome-civil {
		color: #9ca3af;
		font-size: 0.875rem;
		margin: 0.25rem 0 0;
	}

	h2 {
		color: #1a1a2e;
		font-size: 1.125rem;
		margin-bottom: 1rem;
	}

	.stats {
		margin-bottom: 2rem;
	}

	.stats-grid {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.stat-item {
		background: white;
		border: 1px solid #e5e7eb;
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
		color: #6b7280;
	}

	.stat-item.voto-sim .stat-count { color: #16a34a; }
	.stat-item.voto-nao .stat-count { color: #dc2626; }
	.stat-item.voto-outro .stat-count { color: #6b7280; }

	.voto-card {
		display: flex;
		gap: 1rem;
		align-items: flex-start;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 12px;
		padding: 1rem;
		margin-bottom: 0.5rem;
	}

	.voto-badge {
		font-size: 0.75rem;
		font-weight: 700;
		padding: 0.25rem 0.75rem;
		border-radius: 20px;
		white-space: nowrap;
	}

	.voto-badge.voto-sim { background: #dcfce7; color: #166534; }
	.voto-badge.voto-nao { background: #fef2f2; color: #991b1b; }
	.voto-badge.voto-outro { background: #f3f4f6; color: #6b7280; }

	.voto-info { flex: 1; }

	.voto-tipo {
		font-size: 0.8rem;
		font-weight: 600;
		color: #2563eb;
		background: #eff6ff;
		padding: 0.1rem 0.5rem;
		border-radius: 4px;
	}

	.voto-ementa {
		margin: 0.5rem 0 0;
		font-size: 0.9rem;
		color: #374151;
		line-height: 1.4;
	}

	.voto-data {
		font-size: 0.8rem;
		color: #9ca3af;
	}

	.back {
		display: inline-block;
		margin-top: 2rem;
		color: #2563eb;
		text-decoration: none;
	}

	.back:hover { text-decoration: underline; }

	.loading, .empty {
		text-align: center;
		padding: 4rem;
		color: #6b7280;
	}

	.empty-votos {
		color: #9ca3af;
		text-align: center;
		padding: 2rem;
	}
</style>
