<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { api } from '$lib/api';
	import { authUser, authLoading } from '$lib/stores/auth';
	import { selectedUf, respostas, carregarRespostas } from '$lib/stores/questionario';
	import { get } from 'svelte/store';
	import { UF_SIGLAS, getTema } from '$lib/constants';

	interface VotoBreakdown {
		sim?: number;
		nao?: number;
		abstencao?: number;
		obstrucao?: number;
		ausente?: number;
		presente_sem_voto?: number;
	}

	interface PartidoVoto {
		proposicao_id: number;
		proposicao_tipo: string | null;
		proposicao_numero: number | null;
		proposicao_ano: number | null;
		proposicao_ementa: string | null;
		resumo_cidadao: string | null;
		descricao_detalhada: string | null;
		tema: string | null;
		url_camara: string | null;
		data: string | null;
		descricao_votacao: string | null;
		substantiva: boolean;
		breakdown: VotoBreakdown;
	}

	interface PartidoDetail {
		id: number;
		sigla: string;
		nome: string;
		total_parlamentares: number;
		stats: Record<string, number>;
		votos: PartidoVoto[];
	}

	let partido = $state<PartidoDetail | null>(null);
	let error = $state(false);
	let expandedIdx: number | null = $state(null);
	let soSubstantivas = $state(false);
	let soMeusVotos = $state(false);
	let escopo: 'brasil' | 'estado' = $state('brasil');
	let ufSelecionada = $state('');
	let showUfPicker = $state(false);
	let userVotoMap = $state<Map<number, 'sim' | 'nao'>>(new Map());

	let showLimit = $state(100);

	let allVotos = $derived((partido?.votos ?? []) as PartidoVoto[]);
	let votosFiltrados = $derived.by(() => {
		let v = allVotos;
		if (soSubstantivas) v = v.filter((x) => x.substantiva);
		if (soMeusVotos) v = v.filter((x) => userVotoMap.has(x.proposicao_id));
		return v;
	});
	let votosVisiveis = $derived(votosFiltrados.slice(0, showLimit));
	let hasMore = $derived(votosFiltrados.length > showLimit);
	let countSubstantivas = $derived(allVotos.filter((v) => v.substantiva).length);

	let comparacao = $derived.by(() => {
		let concordou = 0;
		let discordou = 0;
		for (const voto of allVotos) {
			const meuVoto = userVotoMap.get(voto.proposicao_id);
			if (!meuVoto) continue;
			const mv = mainVoto(voto.breakdown);
			if (mv !== 'sim' && mv !== 'nao') continue;
			if (meuVoto === mv) concordou++;
			else discordou++;
		}
		const total = concordou + discordou;
		const score = total > 0 ? Math.round(((concordou - discordou) / total + 1) * 50 * 10) / 10 : null;
		return { concordou, discordou, total, score };
	});

	function buildUserVotoMap(lista: Array<{ proposicao_id: number; voto: string; peso: number }>) {
		const map = new Map<number, 'sim' | 'nao'>();
		for (const r of lista) {
			if (r.voto === 'sim' || r.voto === 'nao') {
				map.set(r.proposicao_id, r.voto);
			}
		}
		userVotoMap = map;
	}

	async function loadPartido() {
		try {
			const ufParam = escopo === 'estado' && ufSelecionada ? `?uf=${ufSelecionada}` : '';
			showLimit = 100;
			partido = await api.get<PartidoDetail>(`/partidos/${page.params.id}${ufParam}`);
		} catch (e) {
			console.error('Failed to load partido:', e);
			error = true;
		}
	}

	function setEscopo(novo: 'brasil' | 'estado') {
		if (novo === 'estado' && !ufSelecionada) {
			showUfPicker = true;
			return;
		}
		escopo = novo;
		loadPartido();
	}

	function escolherUf(sigla: string) {
		ufSelecionada = sigla;
		selectedUf.set(sigla);
		showUfPicker = false;
		escopo = 'estado';
		loadPartido();
	}

	onMount(() => {
		// Load user votes
		const storeRespostas = get(respostas);
		if (storeRespostas.length > 0) {
			buildUserVotoMap(storeRespostas);
		}

		// Esperar auth resolver para ter UF do perfil
		function init() {
			const user = get(authUser);
			if (user?.uf) {
				ufSelecionada = user.uf;
			} else {
				const storeUf = get(selectedUf);
				if (storeUf) ufSelecionada = storeUf;
			}
			// Load respostas from DB if store was empty and user logged in
			if (storeRespostas.length === 0 && user) {
				carregarRespostas().then((r) => {
					if (r.length > 0) {
						respostas.set(r);
						buildUserVotoMap(r);
					}
				});
			}
			if (ufSelecionada) escopo = 'estado';
			loadPartido();
		}

		if (!get(authLoading)) {
			init();
			return;
		}
		const unsub = authLoading.subscribe((loading) => {
			if (!loading) {
				unsub();
				init();
			}
		});
	});

	function toggleExpand(idx: number) {
		expandedIdx = expandedIdx === idx ? null : idx;
	}

	function formatDate(iso: string | null): string {
		if (!iso) return '';
		try {
			return new Date(iso).toLocaleDateString('pt-BR');
		} catch {
			return '';
		}
	}

	function breakdownLabel(key: string): string {
		const map: Record<string, string> = {
			sim: 'A favor',
			nao: 'Contra',
			abstencao: 'Abstenção',
			obstrucao: 'Obstrução',
			ausente: 'Ausente',
			presente_sem_voto: 'Presente s/ voto'
		};
		return map[key] || key;
	}

	function breakdownClass(key: string): string {
		if (key === 'sim') return 'bd-sim';
		if (key === 'nao') return 'bd-nao';
		return 'bd-outro';
	}

	function mainVoto(bd: VotoBreakdown): string {
		const sim = bd.sim ?? 0;
		const nao = bd.nao ?? 0;
		const abs = (bd.abstencao ?? 0) + (bd.obstrucao ?? 0) + (bd.ausente ?? 0) + (bd.presente_sem_voto ?? 0);
		if (sim > nao && sim > abs) return 'sim';
		if (nao > sim && nao > abs) return 'nao';
		return 'dividido';
	}

	function mainVotoLabel(bd: VotoBreakdown): string {
		const v = mainVoto(bd);
		if (v === 'sim') return 'A favor';
		if (v === 'nao') return 'Contra';
		return 'Dividido';
	}

	function mainVotoClass(bd: VotoBreakdown): string {
		const v = mainVoto(bd);
		if (v === 'sim') return 'voto-sim';
		if (v === 'nao') return 'voto-nao';
		return 'voto-outro';
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

</script>

<svelte:head>
	<title>{partido?.sigla ?? 'Partido'} — voto.vc</title>
</svelte:head>

{#if showUfPicker}
	<div class="uf-selector">
		<h1>De qual estado?</h1>
		<p class="uf-subtitle">Filtrar parlamentares do partido por estado</p>
		<div class="uf-grid">
			{#each UF_SIGLAS as sigla}
				<button class="uf-btn" onclick={() => escolherUf(sigla)}>
					{sigla}
				</button>
			{/each}
		</div>
		<button class="uf-cancel" onclick={() => showUfPicker = false}>Cancelar</button>
	</div>
{:else if error}
	<div class="empty">Partido não encontrado.</div>
{:else if !partido}
	<div class="loading">Carregando...</div>
{:else}
	<div class="perfil">
		<div class="header">
			<div class="header-info">
				<h1>{partido.sigla}</h1>
				<p class="meta">{partido.nome}</p>
				<p class="meta-count">
					{partido.total_parlamentares} parlamentar{partido.total_parlamentares !== 1 ? 'es' : ''}
					{#if escopo === 'estado' && ufSelecionada}
						em {ufSelecionada}
					{/if}
				</p>
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

		{#if Object.keys(partido.stats).length > 0}
			<div class="stats">
				<h2>Resumo de votações</h2>
				<div class="stats-grid">
					{#each Object.entries(partido.stats) as [voto, count]}
						<div class="stat-item {votoClass(voto)}">
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
						<div class="comp-item alinhamento" class:high={comparacao.score >= 70} class:mid={comparacao.score >= 40 && comparacao.score < 70} class:low={comparacao.score < 40}>
							<span class="comp-count">{comparacao.score}%</span>
							<span class="comp-label">Alinhamento</span>
						</div>
					{/if}
					<div class="comp-item concordou">
						<span class="comp-count">{comparacao.concordou}</span>
						<span class="comp-label">Concordaram</span>
					</div>
					<div class="comp-item discordou">
						<span class="comp-count">{comparacao.discordou}</span>
						<span class="comp-label">Discordaram</span>
					</div>
					<div class="comp-item total">
						<span class="comp-count">{comparacao.total}</span>
						<span class="comp-label">Comparados</span>
					</div>
				</div>
			</div>
		{/if}

		{#if partido.votos.length > 0}
			<div class="historico">
				<div class="historico-header">
					<h2>Histórico de votações</h2>
					<div class="filter-toggles">
						{#if countSubstantivas > 0 && countSubstantivas < partido.votos.length}
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
					{@const meuVoto = userVotoMap.get(voto.proposicao_id)}
					{@const mv = mainVoto(voto.breakdown)}
					{@const comparavel = meuVoto && (mv === 'sim' || mv === 'nao')}
					{@const concordou = comparavel && meuVoto === mv}
					<button
						type="button"
						class="voto-card"
						class:expandable={hasDetails}
						class:expanded={isExpanded}
						class:card-concordou={comparavel && concordou}
						class:card-discordou={comparavel && !concordou}
						onclick={() => hasDetails && toggleExpand(idx)}
					>
						<div class="voto-main">
							<span class="voto-badge {mainVotoClass(voto.breakdown)}">{mainVotoLabel(voto.breakdown)}</span>
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
								<div class="breakdown-bar">
									{#each Object.entries(voto.breakdown) as [tipo, n]}
										{@const total = Object.values(voto.breakdown).reduce((a, b) => a + b, 0)}
										{#if n > 0}
											<div class="bar-seg {breakdownClass(tipo)}" style="width: {(n / total) * 100}%" title="{breakdownLabel(tipo)}: {n}"></div>
										{/if}
									{/each}
								</div>
								<div class="breakdown-legend">
									{#each Object.entries(voto.breakdown) as [tipo, n]}
										{#if n > 0}
											<span class="legend-item {breakdownClass(tipo)}">{breakdownLabel(tipo)}: {n}</span>
										{/if}
									{/each}
								</div>
								{#if meuVoto}
									<div class="meu-voto-row">
										<span class="meu-voto-label">Seu voto: {meuVoto === 'sim' ? 'A favor' : 'Contra'}</span>
										{#if comparavel}
											<span class="match-badge {concordou ? 'match-concordou' : 'match-discordou'}">
												{concordou ? 'Concordou' : 'Discordou'}
											</span>
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
								{#if voto.url_camara}
									<a href={voto.url_camara} target="_blank" rel="noopener" class="link-camara" onclick={(e) => e.stopPropagation()}>Ver na Câmara</a>
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
			<p class="empty-votos">Nenhum voto registrado{escopo === 'estado' && ufSelecionada ? ` para ${ufSelecionada}` : ''}.</p>
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
		margin-bottom: 1.5rem;
	}

	h1 {
		margin: 0;
		color: var(--text-primary);
		font-size: 2rem;
	}

	.meta {
		color: var(--text-secondary);
		margin: 0.25rem 0 0;
	}

	.meta-count {
		color: var(--text-secondary);
		font-size: 0.875rem;
		margin: 0.25rem 0 0;
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

	.escopo-btn:hover {
		color: var(--text-primary);
	}

	.escopo-btn.active {
		color: var(--link);
		border-bottom-color: var(--link);
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
		gap: 0.75rem;
		flex-wrap: wrap;
	}

	.stat-item {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 0.75rem 1rem;
		text-align: center;
		min-width: 70px;
	}

	.stat-count {
		display: block;
		font-size: 1.25rem;
		font-weight: 700;
	}

	.stat-label {
		font-size: 0.75rem;
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
		cursor: default;
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

	.breakdown-bar {
		display: flex;
		height: 6px;
		border-radius: 3px;
		overflow: hidden;
		margin-top: 0.5rem;
		background: var(--border);
	}

	.bar-seg {
		height: 100%;
		transition: width 0.3s;
	}

	.bar-seg.bd-sim { background: #16a34a; }
	.bar-seg.bd-nao { background: #dc2626; }
	.bar-seg.bd-outro { background: #9ca3af; }

	.breakdown-legend {
		display: flex;
		gap: 0.75rem;
		flex-wrap: wrap;
		margin-top: 0.35rem;
	}

	.legend-item {
		font-size: 0.7rem;
		font-weight: 500;
	}

	.legend-item.bd-sim { color: #16a34a; }
	.legend-item.bd-nao { color: #dc2626; }
	.legend-item.bd-outro { color: var(--text-secondary); }

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
		gap: 0.75rem;
		flex-wrap: wrap;
	}

	.comp-item {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 0.75rem 1rem;
		text-align: center;
		min-width: 70px;
	}

	.comp-count {
		display: block;
		font-size: 1.25rem;
		font-weight: 700;
	}

	.comp-label {
		font-size: 0.75rem;
		color: var(--text-secondary);
	}

	.comp-item.concordou .comp-count { color: #16a34a; }
	.comp-item.discordou .comp-count { color: #dc2626; }
	.comp-item.total .comp-count { color: var(--link); }
	.comp-item.alinhamento .comp-count { font-size: 1.5rem; }
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
</style>
