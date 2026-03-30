<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { api } from '$lib/api';
	import { authUser, authLoading } from '$lib/stores/auth';
	import { selectedUf, respostas, carregarRespostas } from '$lib/stores/questionario';
	import { respostasPosicoes, carregarRespostasPosicoes, posicaoItems, overridesPosicoes } from '$lib/stores/posicoes';
	import { get } from 'svelte/store';
	import { UF_SIGLAS, getTema, fmtPct, POSICAO_CATEGORIAS } from '$lib/constants';
	import ScoreDots from '$lib/components/ScoreDots.svelte';
	import { stanceLabelKey, stanceColor, stanceConcorda, userResponseToStance, expandPositions } from '$lib/utils/position';
	import type { PosicaoInferida, RespostaPosicaoItem } from '$lib/types/posicao';
	import { _ } from 'svelte-i18n';

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
		casas: Array<{ casa: string; url: string }>;
		data: string | null;
		descricao_votacao: string | null;
		substantiva: boolean;
		breakdown: VotoBreakdown;
		orientacao: 'sim' | 'nao' | 'abstencao' | 'obstrucao' | 'liberado' | null;
	}

	interface PartidoDetail {
		id: number;
		sigla: string;
		nome: string;
		total_parlamentares: number;
		deputados: number;
		senadores: number;
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
	let scopeLoading = $state(false);
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

	let comparacao = $state<{ concordou: number; discordou: number; total: number; score: number | null; parlamentares_comparados?: number }>({ concordou: 0, discordou: 0, total: 0, score: null });

	interface DisciplinaResult {
		disciplina: number | null;
		votacoes_analisadas: number;
		votacoes_liberadas: number;
	}

	let disciplina = $state<DisciplinaResult | null>(null);
	let posicoes = $state<PosicaoInferida[]>([]);
	let posicionamentosOpen = $state(true);
	let posicaoFiltro: 'todos' | 'concordantes' | 'discordantes' = $state('todos');
	let openCatIds: Set<string> = $state(new Set());
	let catsInitialized = $state(false);
	let userPosRespostas: Map<number, RespostaPosicaoItem> = $state(new Map());

	function toggleCat(catId: string) {
		const next = new Set(openCatIds);
		if (next.has(catId)) next.delete(catId);
		else next.add(catId);
		openCatIds = next;
	}

	// Auto-open all categories when posições load (once)
	$effect(() => {
		if (posicoes.length > 0 && !catsInitialized) {
			catsInitialized = true;
			openCatIds = new Set(POSICAO_CATEGORIAS.map(c => c.id));
		}
	});

	function getUserStance(posicaoId: number) {
		const r = userPosRespostas.get(posicaoId);
		if (!r || r.voto === 'pular') return null;
		return userResponseToStance(r.voto, r.peso);
	}

	function buildUserVotoMap(lista: Array<{ proposicao_id: number; voto: string; peso: number }>) {
		const map = new Map<number, 'sim' | 'nao'>();
		for (const r of lista) {
			if (r.voto === 'sim' || r.voto === 'nao') {
				map.set(r.proposicao_id, r.voto);
			}
		}
		userVotoMap = map;
	}

	let userRespostas: Array<{ proposicao_id: number; voto: string; peso: number }> = [];

	async function loadComparacao() {
		if (userRespostas.length === 0) return;
		try {
			const ufParam = escopo === 'estado' && ufSelecionada ? ufSelecionada : undefined;
			comparacao = await api.post(`/partidos/${page.params.id}/comparacao`, { respostas: userRespostas, uf: ufParam });
		} catch (e) {
			console.error('Failed to load comparação:', e);
		}
	}

	async function loadDisciplina() {
		try {
			const ufParam = escopo === 'estado' && ufSelecionada ? `?uf=${ufSelecionada}` : '';
			disciplina = await api.get<DisciplinaResult>(`/partidos/${page.params.id}/disciplina${ufParam}`);
		} catch (e) {
			console.error('Failed to load disciplina:', e);
		}
	}

	async function loadPosicoes() {
		try {
			const ufParam = escopo === 'estado' && ufSelecionada ? `?uf=${ufSelecionada}` : '';
			posicoes = await api.get<PosicaoInferida[]>(`/partidos/${page.params.id}/posicoes${ufParam}`);
		} catch (e) {
			console.error('Failed to load posições:', e);
		}
	}

	async function loadPartido() {
		try {
			const ufParam = escopo === 'estado' && ufSelecionada ? `?uf=${ufSelecionada}` : '';
			showLimit = 100;
			scopeLoading = true;
			partido = await api.get<PartidoDetail>(`/partidos/${page.params.id}${ufParam}`);
			await Promise.all([loadComparacao(), loadDisciplina(), loadPosicoes()]);
		} catch (e) {
			console.error('Failed to load partido:', e);
			error = true;
		} finally {
			scopeLoading = false;
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

	async function loadAllUserRespostas(): Promise<Array<{ proposicao_id: number; voto: string; peso: number }>> {
		let directResps = get(respostas);
		if (directResps.length === 0 && get(authUser)) {
			const r = await carregarRespostas();
			if (r.length > 0) {
				respostas.set(r);
				directResps = r;
			}
		}

		let posResps = get(respostasPosicoes);
		if (posResps.length === 0 && get(authUser)) {
			posResps = await carregarRespostasPosicoes();
			if (posResps.length > 0) respostasPosicoes.set(posResps);
		}
		userPosRespostas = new Map(posResps.map((r) => [r.posicao_id, r]));

		if (posResps.length > 0) {
			let items = get(posicaoItems);
			if (items.length === 0) {
				try {
					items = await api.get('/posicoes/items');
					posicaoItems.set(items);
				} catch { /* ignore */ }
			}
			if (items.length > 0) {
				const overrides = get(overridesPosicoes);
				const expanded = expandPositions(posResps, items, overrides);
				const seen = new Set(directResps.map((r) => r.proposicao_id));
				const merged = [...directResps];
				for (const e of expanded) {
					if (!seen.has(e.proposicao_id)) {
						seen.add(e.proposicao_id);
						merged.push(e);
					}
				}
				return merged;
			}
		}
		return directResps;
	}

	onMount(() => {
		async function init() {
			const user = get(authUser);
			if (user?.uf) {
				ufSelecionada = user.uf;
			} else {
				const storeUf = get(selectedUf);
				if (storeUf) ufSelecionada = storeUf;
			}
			if (ufSelecionada) escopo = 'estado';

			const allRespostas = await loadAllUserRespostas();
			if (allRespostas.length > 0) {
				buildUserVotoMap(allRespostas);
				userRespostas = allRespostas;
			}

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
			sim: $_('partido.favor'),
			nao: $_('partido.contra'),
			abstencao: $_('partido.abstencao'),
			obstrucao: $_('partido.obstrucao'),
			ausente: $_('partido.ausente'),
			presente_sem_voto: $_('partido.presenteSemVoto')
		};
		return map[key] || key;
	}

	function breakdownClass(key: string): string {
		if (key === 'sim') return 'bd-sim';
		if (key === 'nao') return 'bd-nao';
		return 'bd-outro';
	}

	function mainVotoFromBreakdown(bd: VotoBreakdown): string {
		const sim = bd.sim ?? 0;
		const nao = bd.nao ?? 0;
		const abs = (bd.abstencao ?? 0) + (bd.obstrucao ?? 0) + (bd.ausente ?? 0) + (bd.presente_sem_voto ?? 0);
		if (sim > nao && sim > abs) return 'sim';
		if (nao > sim && nao > abs) return 'nao';
		return 'dividido';
	}

	function posicaoPartido(voto: PartidoVoto): string {
		if (voto.orientacao === 'sim' || voto.orientacao === 'nao') return voto.orientacao;
		if (voto.orientacao === 'liberado') return 'liberado';
		if (voto.orientacao === 'abstencao' || voto.orientacao === 'obstrucao') return 'outro';
		return mainVotoFromBreakdown(voto.breakdown);
	}

	function posicaoLabel(voto: PartidoVoto): string {
		const p = posicaoPartido(voto);
		if (voto.orientacao && voto.orientacao !== 'liberado') {
			if (p === 'sim') return $_('partido.favor');
			if (p === 'nao') return $_('partido.contra');
			return $_('partido.abstencao');
		}
		if (p === 'liberado') return $_('partido.liberado');
		if (p === 'sim') return $_('partido.favor');
		if (p === 'nao') return $_('partido.contra');
		return $_('partido.dividido');
	}

	function posicaoClass(voto: PartidoVoto): string {
		const p = posicaoPartido(voto);
		if (p === 'sim') return 'voto-sim';
		if (p === 'nao') return 'voto-nao';
		return 'voto-outro';
	}

	function bancadaDivergiu(voto: PartidoVoto): boolean {
		if (!voto.orientacao || voto.orientacao === 'liberado') return false;
		if (voto.orientacao !== 'sim' && voto.orientacao !== 'nao') return false;
		const maioria = mainVotoFromBreakdown(voto.breakdown);
		return maioria !== voto.orientacao && maioria !== 'dividido';
	}

	function temOrientacao(voto: PartidoVoto): boolean {
		return voto.orientacao != null && voto.orientacao !== 'liberado';
	}

	function votoLabel(voto: string): string {
		const map: Record<string, string> = {
			sim: $_('partido.favor'),
			nao: $_('partido.contra'),
			abstencao: $_('partido.abstencao'),
			obstrucao: $_('partido.obstrucao'),
			ausente: $_('partido.ausente'),
			presente_sem_voto: $_('partido.presenteSemVoto')
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
			sim: $_('partido.tooltipSim'),
			nao: $_('partido.tooltipNao'),
			abstencao: $_('partido.tooltipAbstencao'),
			obstrucao: $_('partido.tooltipObstrucao'),
			ausente: $_('partido.tooltipAusente'),
			presente_sem_voto: $_('partido.tooltipPresenteSemVoto')
		};
		return map[voto] || '';
	}

</script>

<svelte:head>
	<title>{partido?.nome ? $_('partido.title', { values: { nome: partido.nome } }) : 'Partido — voto.vc'}</title>
</svelte:head>

{#if showUfPicker}
	<div class="uf-selector">
		<h1>{$_('partido.deQualEstado')}</h1>
		<p class="uf-subtitle">{$_('partido.filtrarPorEstado')}</p>
		<div class="uf-grid">
			{#each UF_SIGLAS as sigla}
				<button class="uf-btn" onclick={() => escolherUf(sigla)}>
					{sigla}
				</button>
			{/each}
		</div>
		<button class="uf-cancel" onclick={() => showUfPicker = false}>{$_('partido.cancelar')}</button>
	</div>
{:else if error}
	<div class="empty">{$_('partido.semDados')}</div>
{:else if !partido}
	<div class="loading">{$_('partido.carregando')}</div>
{:else}
	<div class="perfil">
		<div class="header">
			<div class="header-info">
				<h1>{partido.nome}</h1>
				<p class="meta">{partido.sigla}</p>
				<p class="meta-count">
					{#if scopeLoading}<span class="spinner"></span>{:else}
						{#if partido.deputados > 0 && partido.senadores > 0}
							{partido.deputados !== 1 ? $_('partido.deputadosCountPlural', { values: { count: partido.deputados } }) : $_('partido.deputadosCount', { values: { count: partido.deputados } })} {$_('partido.eConj')} {partido.senadores !== 1 ? $_('partido.senadoresCountPlural', { values: { count: partido.senadores } }) : $_('partido.senadoresCount', { values: { count: partido.senadores } })}
						{:else if partido.senadores > 0}
							{partido.senadores !== 1 ? $_('partido.senadoresCountPlural', { values: { count: partido.senadores } }) : $_('partido.senadoresCount', { values: { count: partido.senadores } })}
						{:else}
							{partido.deputados !== 1 ? $_('partido.deputadosCountPlural', { values: { count: partido.deputados } }) : $_('partido.deputadosCount', { values: { count: partido.deputados } })}
						{/if}
					{/if}
					{#if escopo === 'estado' && ufSelecionada}
						{$_('partido.em')} {ufSelecionada}
					{/if}
				</p>
			</div>
		</div>

		<div class="escopo-toggle">
			<button
				class="escopo-btn"
				class:active={escopo === 'brasil'}
				onclick={() => setEscopo('brasil')}
			>{$_('partido.brasil')}</button>
			<button
				class="escopo-btn"
				class:active={escopo === 'estado'}
				onclick={() => setEscopo('estado')}
			>{$_('partido.meuEstado')}{ufSelecionada ? ` (${ufSelecionada})` : ''}</button>
		</div>

		{#if comparacao.score != null || disciplina?.disciplina != null}
			<div class="metricas">
				<div class="metricas-grid">
					{#if comparacao.score != null}
						<div class="metrica-card" title={$_('partido.tooltipAlinhamento')}>
							<span class="metrica-valor">
								<ScoreDots score={comparacao.score} votos_comparados={comparacao.total} loading={scopeLoading} size="lg" />
							</span>
							<span class="metrica-nome">{$_('partido.alinhamento')}</span>
							<span class="metrica-detalhe">
								{#if !scopeLoading}{$_('partido.proposicoesEmComum', { values: { concordou: comparacao.concordou, total: comparacao.total } })}{/if}
							</span>
						</div>
					{/if}
					{#if disciplina?.disciplina != null}
						<div class="metrica-card" class:high={!scopeLoading && disciplina.disciplina >= 80} class:mid={!scopeLoading && disciplina.disciplina >= 60 && disciplina.disciplina < 80} class:low={!scopeLoading && disciplina.disciplina < 60} title={$_('partido.tooltipDisciplina')}>
							<span class="metrica-valor">{#if scopeLoading}<span class="spinner lg"></span>{:else}{fmtPct(disciplina.disciplina)}{/if}</span>
							<span class="metrica-nome">{$_('partido.disciplina')}</span>
							<span class="metrica-detalhe" title={$_('partido.tooltipDisciplinaDetalhe')}>
								{#if !scopeLoading}{$_('partido.votacoesAnalisadas', { values: { count: disciplina.votacoes_analisadas } })}{/if}
							</span>
						</div>
					{/if}
				</div>
			</div>
		{/if}

		{#if posicoes.length > 0}
			<div class="posicionamentos">
				<button class="section-toggle" onclick={() => posicionamentosOpen = !posicionamentosOpen}>
					<h2>{$_('partido.posicionamentos')}</h2>
					<svg class="section-chevron" class:open={posicionamentosOpen} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
				</button>
				{#if posicionamentosOpen}
					{#if userPosRespostas.size > 0}
						<div class="posicao-filtros">
							<button class="posicao-filtro-btn" class:active={posicaoFiltro === 'todos'} onclick={() => posicaoFiltro = 'todos'}>{$_('partido.todos')}</button>
							<button class="posicao-filtro-btn concordante" class:active={posicaoFiltro === 'concordantes'} onclick={() => posicaoFiltro = 'concordantes'}>{$_('partido.concordantes')}</button>
							<button class="posicao-filtro-btn discordante" class:active={posicaoFiltro === 'discordantes'} onclick={() => posicaoFiltro = 'discordantes'}>{$_('partido.discordantes')}</button>
						</div>
					{/if}
					{#each POSICAO_CATEGORIAS as cat}
						{@const catPosicoes = posicoes.filter(p => {
							if (p.stance === 'sem_dados' || !cat.ordens.includes(p.ordem)) return false;
							if (posicaoFiltro === 'todos') return true;
							const us = getUserStance(p.posicao_id);
							if (!us) return false;
							const concorda = stanceConcorda(p.stance, us.stance);
							if (concorda === null) return false;
							return posicaoFiltro === 'concordantes' ? concorda : !concorda;
						})}
						{#if catPosicoes.length > 0}
							<div class="posicao-cat">
								<button class="posicao-cat-toggle" onclick={() => toggleCat(cat.id)}>
									<h3 class="posicao-cat-label" style="color: {cat.cor}">
										<span class="posicao-cat-dot" style="background: {cat.cor}"></span>
										{cat.label}
									</h3>
									<svg class="cat-chevron" class:open={openCatIds.has(cat.id)} style="color: {cat.cor}" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
								</button>
								{#if openCatIds.has(cat.id)}
									<div class="posicoes-grid">
										{#each catPosicoes as pos}
											{@const userStance = getUserStance(pos.posicao_id)}
											<div class="posicao-card">
												<div class="posicao-info">
													<span class="posicao-titulo">{pos.titulo}</span>
													<span class="posicao-stance" style="color: {stanceColor(pos.stance)}">{$_(stanceLabelKey(pos.stance))}</span>
												</div>
												{#if pos.score_pct != null}
													<div class="posicao-bar">
														<div class="posicao-fill" style="width: {pos.score_pct}%; background: {stanceColor(pos.stance)}"></div>
													</div>
												{/if}
												{#if userStance}
													<div class="posicao-user">
														<span class="posicao-user-label">{$_('partido.voce')}</span>
														<span class="posicao-user-stance" style="color: {stanceColor(userStance.stance)}">{$_(stanceLabelKey(userStance.stance))}</span>
													</div>
													<div class="posicao-bar user">
														<div class="posicao-fill" style="width: {userStance.score_pct}%; background: {stanceColor(userStance.stance)}"></div>
													</div>
												{/if}
											</div>
										{/each}
									</div>
								{/if}
							</div>
						{/if}
					{/each}
				{/if}
			</div>
		{/if}

		{#if Object.keys(partido.stats).length > 0}
			<div class="stats">
				<h2>{$_('partido.comoVotaram')}</h2>
				<div class="stats-grid">
					{#each Object.entries(partido.stats) as [voto, count]}
						<div class="stat-item {votoClass(voto)}" title={statTooltip(voto)}>
							<span class="stat-count">{#if scopeLoading}<span class="spinner"></span>{:else}{count}{/if}</span>
							<span class="stat-label">{votoLabel(voto)}</span>
						</div>
					{/each}
				</div>
				{#if comparacao.total > 0}
					<div class="comparacao-resumo">
						{#if scopeLoading}
							<span class="spinner"></span>
						{:else}
							<span class="comparacao-concordou" title={$_('partido.tooltipConcordou')}>{$_('partido.concordaram', { values: { count: comparacao.concordou } })}</span>
							<span class="comparacao-sep">·</span>
							<span class="comparacao-discordou" title={$_('partido.tooltipDiscordou')}>{$_('partido.discordaram', { values: { count: comparacao.discordou } })}</span>
							<span class="comparacao-sep">·</span>
							<span class="comparacao-total" title={$_('partido.tooltipTotal')}>{$_('partido.comparados', { values: { count: comparacao.total } })}</span>
						{/if}
					</div>
				{/if}
			</div>
		{/if}

		{#if partido.votos.length > 0}
			<div class="historico">
				<div class="historico-header">
					<h2>{$_('partido.historicoVotacoes')}</h2>
					<div class="filter-toggles">
						{#if countSubstantivas > 0 && countSubstantivas < partido.votos.length}
							<label class="filter-toggle">
								<input type="checkbox" bind:checked={soSubstantivas} />
								{$_('partido.soSubstantivas')} ({countSubstantivas})
								<span class="filter-hint" title={$_('partido.tooltipSubstantivas')}>?</span>
							</label>
						{/if}
						{#if userVotoMap.size > 0}
							<label class="filter-toggle">
								<input type="checkbox" bind:checked={soMeusVotos} />
								{$_('partido.soProposicoesQueVotei')}
							</label>
						{/if}
					</div>
				</div>

				{#each votosVisiveis as voto, idx}
					{@const hasDetails = voto.substantiva && (voto.resumo_cidadao || voto.descricao_detalhada)}
					{@const isExpanded = expandedIdx === idx}
					{@const meuVoto = userVotoMap.get(voto.proposicao_id)}
					{@const pos = posicaoPartido(voto)}
					{@const comparavel = meuVoto && (pos === 'sim' || pos === 'nao')}
					{@const concordou = comparavel && meuVoto === pos}
					{@const divergiu = bancadaDivergiu(voto)}
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
							<span class="voto-badge {posicaoClass(voto)}">{posicaoLabel(voto)}</span>
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
									{voto.proposicao_ementa ?? voto.descricao_votacao ?? $_('partido.semDescricao')}
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
								{#if divergiu}
									<span class="legend-divergencia" title={$_('partido.tooltipBancadaDivergiu')}>{$_('partido.bancadaDivergiu')}</span>
								{/if}
								</div>
								{#if meuVoto}
									<div class="meu-voto-row">
										<span class="meu-voto-label">{$_('partido.seuVoto', { values: { voto: meuVoto === 'sim' ? $_('partido.favor') : $_('partido.contra') } })}</span>
										{#if comparavel}
											<span class="match-badge {concordou ? 'match-concordou' : 'match-discordou'}">
												{concordou ? $_('partido.concordou') : $_('partido.discordou')}
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
								{#if voto.casas.length > 0}
									<div class="casa-pills">
										{#each voto.casas as info}
											<a href={info.url} target="_blank" rel="noopener" class="casa-pill" class:camara={info.casa === 'camara'} class:senado={info.casa === 'senado'} onclick={(e) => e.stopPropagation()}>{info.casa === 'camara' ? $_('partido.camara') : $_('partido.senado')}</a>
										{/each}
									</div>
								{/if}
							</div>
						{/if}
					</button>
				{/each}
				{#if hasMore}
					<button class="btn-more" onclick={() => showLimit += 100}>
						{$_('partido.mostrarMais', { values: { count: votosFiltrados.length - showLimit } })}
					</button>
				{/if}
			</div>
		{:else}
			<p class="empty-votos">{escopo === 'estado' && ufSelecionada ? $_('partido.nenhumVotoPara', { values: { uf: ufSelecionada } }) : $_('partido.nenhumVoto') + '.'}</p>
		{/if}

		<a href="/perfil" class="back">{$_('partido.voltarPerfil')}</a>
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
		gap: 0.5rem;
		margin-bottom: 1.5rem;
	}

	.escopo-btn {
		flex: none;
		padding: 0.5rem 1rem;
		background: none;
		border: 1.5px solid var(--border);
		border-radius: 0;
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
		background: transparent;
		border: 1px solid var(--border);
		border-radius: 0;
		padding: 1rem 1.25rem;
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

	.stat-item.voto-sim .stat-count { color: var(--color-favor); }
	.stat-item.voto-nao .stat-count { color: var(--color-contra); }
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

	.filter-hint {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		background: var(--border);
		color: var(--text-secondary);
		font-size: 0.6rem;
		font-weight: 700;
		cursor: help;
		flex-shrink: 0;
	}

	.voto-card {
		display: block;
		width: 100%;
		text-align: left;
		font: inherit;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 0;
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

	.voto-badge.voto-sim { background: color-mix(in srgb, var(--color-favor) 10%, transparent); color: var(--color-favor); }
	.voto-badge.voto-nao { background: color-mix(in srgb, var(--color-contra) 10%, transparent); color: var(--color-contra); }
	.voto-badge.voto-outro { background: color-mix(in srgb, var(--text-secondary) 10%, transparent); color: var(--text-secondary); }

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
		background: color-mix(in srgb, var(--link) 10%, transparent);
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

	.bar-seg.bd-sim { background: var(--color-favor); }
	.bar-seg.bd-nao { background: var(--color-contra); }
	.bar-seg.bd-outro { background: var(--color-neutro); }

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

	.legend-item.bd-sim { color: var(--color-favor); }
	.legend-item.bd-nao { color: var(--color-contra); }
	.legend-item.bd-outro { color: var(--text-secondary); }

	.legend-divergencia {
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--color-warning);
		background: color-mix(in srgb, var(--color-warning) 10%, transparent);
		padding: 0.05rem 0.4rem;
		border-radius: 4px;
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
		border-radius: 0;
		border: 1px solid;
		text-decoration: none;
		transition: opacity 0.2s;
	}

	a.casa-pill:hover {
		opacity: 0.8;
	}

	.casa-pill.camara {
		background: color-mix(in srgb, var(--link) 12%, transparent);
		color: var(--link-hover);
		border-color: color-mix(in srgb, var(--link) 30%, transparent);
	}

	.casa-pill.senado {
		background: #fce7f3;
		color: #be185d;
		border-color: #f9a8d4;
	}

	:global([data-theme='escuro']) .casa-pill.camara {
		background: color-mix(in srgb, var(--link) 20%, transparent);
		color: var(--link-hover);
		border-color: color-mix(in srgb, var(--link) 25%, transparent);
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
		padding: 0.875rem;
		background: transparent;
		border: 1.5px solid var(--border);
		border-radius: 0;
		color: var(--text-secondary);
		font-weight: 700;
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		cursor: pointer;
		transition: border-color 0.15s, color 0.15s;
	}

	.btn-more:hover {
		border-color: var(--text-primary);
		color: var(--text-primary);
	}

	/* Métricas (alinhamento + disciplina) */
	.metricas {
		margin-bottom: 2rem;
	}

	.metricas-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
		gap: 0.75rem;
	}

	.metrica-card {
		background: transparent;
		border: 1px solid var(--border);
		border-radius: 0;
		padding: 1.25rem 1rem;
		text-align: center;
	}

	.metrica-valor {
		display: block;
		font-size: 2rem;
		font-weight: 700;
		line-height: 1;
	}

	.metrica-nome {
		display: block;
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-top: 0.25rem;
	}

	.metrica-detalhe {
		display: block;
		font-size: 0.7rem;
		color: var(--text-secondary);
		margin-top: 0.25rem;
	}

	.metrica-card.high .metrica-valor { color: var(--color-favor); }
	.metrica-card.mid .metrica-valor { color: var(--color-warning); }
	.metrica-card.low .metrica-valor { color: var(--color-contra); }

	.metricas-footnote {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
		margin-top: 0.5rem;
		font-size: 0.7rem;
		color: var(--text-secondary);
	}

	/* Comparação inline (dentro de stats) */
	.comparacao-resumo {
		margin-top: 0.75rem;
		font-size: 0.8rem;
		color: var(--text-secondary);
	}

	.comparacao-concordou { color: var(--color-favor); font-weight: 600; }
	.comparacao-discordou { color: var(--color-contra); font-weight: 600; }
	.comparacao-total { color: var(--text-secondary); }
	.comparacao-sep { color: var(--border); margin: 0 0.15rem; }

	.filter-toggles {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
	}

	/* User vote on cards */
	.voto-card.card-concordou {
		border-left: 3px solid var(--color-favor);
	}

	.voto-card.card-discordou {
		border-left: 3px solid var(--color-contra);
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
		background: color-mix(in srgb, var(--color-favor) 10%, transparent);
		color: var(--color-favor);
	}

	.match-discordou {
		background: color-mix(in srgb, var(--color-contra) 10%, transparent);
		color: var(--color-contra);
	}

	.posicionamentos {
		margin-bottom: 2rem;
	}

	.posicao-filtros {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.posicao-filtro-btn {
		padding: 0.3rem 0.75rem;
		border-radius: 999px;
		border: 1px solid var(--border);
		background: transparent;
		color: var(--text-secondary);
		font-size: 0.8rem;
		cursor: pointer;
		transition: all 0.15s;
	}

	.posicao-filtro-btn:hover {
		border-color: var(--text-secondary);
	}

	.posicao-filtro-btn.active {
		background: var(--text-primary);
		color: var(--bg-card);
		border-color: var(--text-primary);
	}

	.posicao-filtro-btn.concordante.active {
		background: #16a34a;
		border-color: #16a34a;
		color: #fff;
	}

	.posicao-filtro-btn.discordante.active {
		background: #dc2626;
		border-color: #dc2626;
		color: #fff;
	}

	.section-toggle {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
		font: inherit;
		text-align: left;
		margin-bottom: 1rem;
	}

	.section-toggle h2 {
		margin: 0;
		color: var(--text-primary);
	}

	.section-chevron {
		color: var(--text-secondary);
		transition: transform 0.2s;
		flex-shrink: 0;
	}

	.section-chevron.open {
		transform: rotate(180deg);
	}

	.posicao-cat {
		margin-bottom: 1rem;
	}

	.posicao-cat-toggle {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		background: none;
		border: none;
		padding: 0.25rem 0;
		cursor: pointer;
		font: inherit;
		text-align: left;
	}

	.posicao-cat-toggle:hover .posicao-cat-label {
		opacity: 0.8;
	}

	.cat-chevron {
		transition: transform 0.2s;
		flex-shrink: 0;
	}

	.cat-chevron.open {
		transform: rotate(180deg);
	}

	.posicao-cat-label {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.85rem;
		font-weight: 700;
		margin: 0;
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
		margin-top: 0.5rem;
	}

	@media (max-width: 600px) {
		.posicoes-grid {
			grid-template-columns: 1fr;
		}
	}

	.posicao-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 0;
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

	.posicao-user {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 0.5rem;
		margin-top: 0.35rem;
	}

	.posicao-user-label {
		font-size: 0.65rem;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.posicao-user-stance {
		font-size: 0.65rem;
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

	.posicao-bar.user {
		margin-top: 0.2rem;
		height: 3px;
		opacity: 0.6;
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
		background: transparent;
		border: 1.5px solid var(--border);
		border-radius: 0;
		cursor: pointer;
		font-weight: 900;
		color: var(--text-primary);
		font-size: 0.938rem;
		transition: border-color 0.15s;
	}

	.uf-btn:hover {
		border-color: var(--text-primary);
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

	/* Spinner */
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

	.spinner.lg {
		width: 1.5em;
		height: 1.5em;
		border-width: 3px;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
