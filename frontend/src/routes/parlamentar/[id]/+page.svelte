<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { get } from 'svelte/store';
	import { api } from '$lib/api';
	import { getTema, fmtPct, POSICAO_CATEGORIAS } from '$lib/constants';
	import { stanceLabel, stanceColor } from '$lib/utils/position';
	import type { PosicaoInferida } from '$lib/types/posicao';
	import { respostas, carregarRespostas } from '$lib/stores/questionario';
	import { authUser, authLoading } from '$lib/stores/auth';

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
		casas: Array<{ casa: string; url: string }>;
		substantiva: boolean;
	}

	let parlamentar = $state<ParlamentarDetail | null>(null);
	let error = $state(false);
	let expandedIdx: number | null = $state(null);
	let soSubstantivas = $state(false);
	let soMeusVotos = $state(false);
	let showLimit = $state(100);
	let userVotoMap = $state<Map<number, 'sim' | 'nao'>>(new Map());

	let allVotos = $derived((parlamentar?.votos ?? []) as VotoHistory[]);

	let votosFiltrados = $derived.by(() => {
		let v = allVotos;
		if (soSubstantivas) v = v.filter((x: VotoHistory) => x.substantiva);
		if (soMeusVotos) v = v.filter((x: VotoHistory) => x.proposicao_id && userVotoMap.has(x.proposicao_id));
		return v;
	});

	let votosVisiveis = $derived(votosFiltrados.slice(0, showLimit));
	let hasMore = $derived(votosFiltrados.length > showLimit);

	let countSubstantivas = $derived(
		allVotos.filter((v: VotoHistory) => v.substantiva).length
	);

	let comparacao = $state<{ concordou: number; discordou: number; total: number; score: number | null }>({ concordou: 0, discordou: 0, total: 0, score: null });
	let posicoes = $state<PosicaoInferida[]>([]);

	function buildUserVotoMap(lista: Array<{ proposicao_id: number; voto: string; peso: number }>) {
		const map = new Map<number, 'sim' | 'nao'>();
		for (const r of lista) {
			if (r.voto === 'sim' || r.voto === 'nao') {
				map.set(r.proposicao_id, r.voto);
			}
		}
		userVotoMap = map;
	}

	async function loadComparacao(lista: Array<{ proposicao_id: number; voto: string; peso: number }>) {
		if (lista.length === 0) return;
		try {
			comparacao = await api.post(`/parlamentares/${page.params.id}/comparacao`, { respostas: lista });
		} catch (e) {
			console.error('Failed to load comparação:', e);
		}
	}

	onMount(async () => {
		// Load user votes
		let userRespostas = get(respostas);
		if (userRespostas.length === 0) {
			// Try loading from DB for logged-in users
			async function tryLoadRespostas() {
				const user = get(authUser);
				if (user) {
					const r = await carregarRespostas();
					if (r.length > 0) {
						respostas.set(r);
						userRespostas = r;
						buildUserVotoMap(r);
						loadComparacao(r);
					}
				}
			}
			if (!get(authLoading)) {
				await tryLoadRespostas();
			} else {
				const unsub = authLoading.subscribe((loading) => {
					if (!loading) {
						unsub();
						tryLoadRespostas();
					}
				});
			}
		} else {
			buildUserVotoMap(userRespostas);
			loadComparacao(userRespostas);
		}

		// Load parlamentar + posições
		try {
			parlamentar = await api.get<ParlamentarDetail>(`/parlamentares/${page.params.id}`);
		} catch (e) {
			console.error('Failed to load parlamentar:', e);
			error = true;
		}

		try {
			posicoes = await api.get<PosicaoInferida[]>(`/parlamentares/${page.params.id}/posicoes`);
		} catch (e) {
			console.error('Failed to load posições:', e);
		}
	});

	function toggleExpand(idx: number) {
		expandedIdx = expandedIdx === idx ? null : idx;
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

	function statTooltip(voto: string): string {
		const map: Record<string, string> = {
			sim: 'Vezes que votou a favor da proposta',
			nao: 'Vezes que votou contra a proposta',
			abstencao: 'Vezes que se absteve de votar',
			obstrucao: 'Vezes que obstruiu a votação como estratégia política',
			ausente: 'Vezes que não compareceu à votação',
			presente_sem_voto: 'Esteve presente na sessão mas não registrou voto'
		};
		return map[voto] || '';
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
						<div class="stat-item {votoClass(voto)}" title={statTooltip(voto)}>
							<span class="stat-count">{count}</span>
							<span class="stat-label">{votoLabel(voto)}</span>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		{#if comparacao.total > 0}
			<div class="comparacao">
				<h2>Comparação com seus votos</h2>
				<div class="comparacao-stats">
					{#if comparacao.score != null}
						<div class="comp-item alinhamento" class:high={comparacao.score >= 70} class:mid={comparacao.score >= 40 && comparacao.score < 70} class:low={comparacao.score < 40} title="Quanto esse parlamentar votou parecido com você nas proposições em comum">
							<span class="comp-count">{fmtPct(comparacao.score)}</span>
							<span class="comp-label">Alinhamento</span>
						</div>
					{/if}
					<div class="comp-item concordou" title="Proposições em que vocês dois votaram igual">
						<span class="comp-count">{comparacao.concordou}</span>
						<span class="comp-label">Concordaram</span>
					</div>
					<div class="comp-item discordou" title="Proposições em que vocês dois votaram diferente">
						<span class="comp-count">{comparacao.discordou}</span>
						<span class="comp-label">Discordaram</span>
					</div>
					<div class="comp-item total" title="Total de proposições em que ambos votaram">
						<span class="comp-count">{comparacao.total}</span>
						<span class="comp-label">Comparados</span>
					</div>
				</div>
			</div>
		{/if}

		{#if posicoes.length > 0}
			<div class="posicionamentos">
				<h2>Posicionamentos</h2>
				{#each POSICAO_CATEGORIAS as cat}
					{@const catPosicoes = posicoes.filter(p => p.stance !== 'sem_dados' && cat.ordens.includes(p.ordem))}
					{#if catPosicoes.length > 0}
						<div class="posicao-cat">
							<h3 class="posicao-cat-label" style="color: {cat.cor}">
								<span class="posicao-cat-dot" style="background: {cat.cor}"></span>
								{cat.label}
							</h3>
							<div class="posicoes-grid">
								{#each catPosicoes as pos}
									<div class="posicao-card">
										<div class="posicao-info">
											<span class="posicao-titulo">{pos.titulo}</span>
											<span class="posicao-stance" style="color: {stanceColor(pos.stance)}">{stanceLabel(pos.stance)}</span>
										</div>
										{#if pos.score_pct != null}
											<div class="posicao-bar">
												<div class="posicao-fill" style="width: {pos.score_pct}%; background: {stanceColor(pos.stance)}"></div>
											</div>
										{/if}
									</div>
								{/each}
							</div>
						</div>
					{/if}
				{/each}
			</div>
		{/if}

		{#if parlamentar.votos.length > 0}
			<div class="historico">
				<div class="historico-header">
					<h2>Histórico de votações</h2>
					<div class="filter-toggles">
						{#if countSubstantivas > 0 && countSubstantivas < parlamentar.votos.length}
							<label class="filter-toggle">
								<input type="checkbox" bind:checked={soSubstantivas} />
								Só substantivas ({countSubstantivas})
							</label>
						{/if}
						{#if userVotoMap.size > 0}
							<label class="filter-toggle">
								<input type="checkbox" bind:checked={soMeusVotos} />
								Só proposições que votei
							</label>
						{/if}
					</div>
				</div>

				{#each votosVisiveis as voto, idx}
					{@const hasDetails = voto.substantiva && (voto.resumo_cidadao || voto.descricao_detalhada)}
					{@const isExpanded = expandedIdx === idx}
					{@const meuVoto = voto.proposicao_id ? userVotoMap.get(voto.proposicao_id) : undefined}
					{@const parlVotou = voto.voto === 'sim' || voto.voto === 'nao'}
					{@const comparavel = meuVoto && parlVotou}
					{@const concordou = comparavel && meuVoto === voto.voto}
					{@const naoVotou = meuVoto && !parlVotou}
					<button
						type="button"
						class="voto-card"
						class:expandable={hasDetails}
						class:expanded={isExpanded}
						class:card-concordou={comparavel && concordou}
						class:card-discordou={(comparavel && !concordou) || naoVotou}
						onclick={() => hasDetails && toggleExpand(idx)}
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
								{#if meuVoto}
									<div class="meu-voto-row">
										<span class="meu-voto-label">Seu voto: {meuVoto === 'sim' ? 'A favor' : 'Contra'}</span>
										{#if comparavel}
											<span class="match-badge {concordou ? 'match-concordou' : 'match-discordou'}">
												{concordou ? 'Concordou' : 'Discordou'}
											</span>
										{:else if naoVotou}
											<span class="match-badge match-naovotou">Não votou</span>
										{/if}
									</div>
								{/if}
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
								{#if voto.casas.length > 0}
									<div class="casa-pills">
										{#each voto.casas as info}
											<a href={info.url} target="_blank" rel="noopener" class="casa-pill" class:camara={info.casa === 'camara'} class:senado={info.casa === 'senado'} onclick={(e) => e.stopPropagation()}>{info.casa === 'camara' ? 'Câmara' : 'Senado'}</a>
										{/each}
									</div>
								{/if}
							</div>
						{/if}
					</button>
				{/each}
				{#if hasMore}
					<button class="btn-more" onclick={() => showLimit += 100}>
						Mostrar mais ({votosFiltrados.length - showLimit} restantes)
					</button>
				{/if}
			</div>
		{:else}
			<p class="empty-votos">Nenhum voto registrado.</p>
		{/if}

		<a href="/perfil" class="back">Voltar ao perfil</a>
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

	.casa-pills {
		display: flex;
		gap: 0.25rem;
		margin-top: 0.5rem;
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

	.back {
		display: inline-block;
		margin-top: 2rem;
		color: var(--link);
		text-decoration: none;
	}

	.back:hover { text-decoration: underline; }

	.btn-more {
		display: block;
		width: 100%;
		padding: 0.75rem;
		background: var(--bg-card);
		border: 1px dashed var(--border);
		border-radius: 12px;
		color: var(--link);
		font-weight: 600;
		font-size: 0.875rem;
		cursor: pointer;
		transition: border-color 0.2s;
	}

	.btn-more:hover {
		border-color: var(--link);
	}

	/* Comparação */
	.comparacao {
		margin-bottom: 2rem;
	}

	.comparacao h2 {
		margin-bottom: 1rem;
	}

	.comparacao-stats {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.comp-item {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1rem 1.25rem;
		text-align: center;
		min-width: 80px;
	}

	.comp-count {
		display: block;
		font-size: 1.5rem;
		font-weight: 700;
	}

	.comp-label {
		font-size: 0.8rem;
		color: var(--text-secondary);
	}

	.comp-item.concordou .comp-count { color: #16a34a; }
	.comp-item.discordou .comp-count { color: #dc2626; }
	.comp-item.total .comp-count { color: var(--link); }
	.comp-item.alinhamento .comp-count { font-size: 1.75rem; }
	.comp-item.alinhamento.high .comp-count { color: #16a34a; }
	.comp-item.alinhamento.mid .comp-count { color: #ca8a04; }
	.comp-item.alinhamento.low .comp-count { color: #dc2626; }

	.filter-toggles {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
	}

	/* User vote on cards */
	.voto-card.card-concordou {
		border-left: 3px solid #16a34a;
	}

	.voto-card.card-discordou {
		border-left: 3px solid #dc2626;
	}

	.meu-voto-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-top: 0.4rem;
	}

	.meu-voto-label {
		font-size: 0.8rem;
		color: var(--text-secondary);
		font-weight: 500;
	}

	.match-badge {
		font-size: 0.7rem;
		font-weight: 700;
		padding: 0.1rem 0.5rem;
		border-radius: 20px;
	}

	.match-concordou {
		background: #16a34a1a;
		color: #16a34a;
	}

	.match-discordou {
		background: #dc26261a;
		color: #dc2626;
	}

	.match-naovotou {
		background: #6b72801a;
		color: var(--text-secondary);
	}

	.posicionamentos {
		margin-bottom: 2rem;
	}

	.posicionamentos h2 {
		margin-bottom: 1rem;
	}

	.posicao-cat {
		margin-bottom: 1rem;
	}

	.posicao-cat-label {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.85rem;
		font-weight: 700;
		margin: 0 0 0.5rem;
	}

	.posicao-cat-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.posicoes-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.5rem;
	}

	@media (max-width: 600px) {
		.posicoes-grid {
			grid-template-columns: 1fr;
		}
	}

	.posicao-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 10px;
		padding: 0.75rem;
	}

	.posicao-info {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 0.5rem;
	}

	.posicao-titulo {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	.posicao-stance {
		font-size: 0.7rem;
		font-weight: 700;
		white-space: nowrap;
	}

	.posicao-bar {
		height: 4px;
		border-radius: 2px;
		background: var(--border);
		margin-top: 0.4rem;
		overflow: hidden;
	}

	.posicao-fill {
		height: 100%;
		border-radius: 2px;
		transition: width 0.3s;
	}

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
