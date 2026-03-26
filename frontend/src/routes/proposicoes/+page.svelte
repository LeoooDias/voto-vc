<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { TEMAS, getTema } from '$lib/constants';

	interface CasaInfo {
		casa: string;
		url: string | null;
	}

	interface Proposicao {
		id: number;
		id_externo: string | null;
		tipo: string;
		numero: number;
		ano: number;
		ementa: string | null;
		resumo_cidadao: string | null;
		descricao_detalhada: string | null;
		tema: string | null;
		substantiva: boolean;
		casas: CasaInfo[];
	}

	interface ProposicoesResponse {
		total: number;
		paginas: number;
		items: Proposicao[];
	}

	interface Filtros {
		temas: { valor: string; count: number }[];
		tipos: { valor: string; count: number }[];
		anos: number[];
	}

	let proposicoes: Proposicao[] = $state([]);
	let totalPaginas = $state(0);
	let filtros: Filtros | null = $state(null);
	let loading = $state(true);
	let pagina = $state(1);
	let expandedId: number | null = $state(null);

	let filtroTema = $state('');
	let filtroTipo = $state('');
	let filtroAno = $state('');
	let soSubstantivas = $state(false);
	let busca = $state('');
	let buscaDebounced = $state('');
	let debounceTimer: ReturnType<typeof setTimeout>;

	function onBuscaInput(e: Event) {
		busca = (e.target as HTMLInputElement).value;
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			buscaDebounced = busca;
			pagina = 1;
			loadProposicoes();
		}, 400);
	}

	async function loadProposicoes() {
		loading = true;
		try {
			const params = new URLSearchParams();
			params.set('pagina', String(pagina));
			params.set('itens', '50');
			if (filtroTema) params.set('tema', filtroTema);
			if (filtroTipo) params.set('tipo', filtroTipo);
			if (filtroAno) params.set('ano', filtroAno);
			if (soSubstantivas) params.set('substantiva', 'true');
			if (buscaDebounced) params.set('busca', buscaDebounced);
			const res = await api.get<ProposicoesResponse>(`/proposicoes/?${params}`);
			proposicoes = res.items;
			totalPaginas = res.paginas;
		} catch (e) {
			console.error('Failed to load proposicoes:', e);
		} finally {
			loading = false;
		}
	}

	function applyFilter() {
		pagina = 1;
		loadProposicoes();
	}

	function toggleSubstantivas() {
		soSubstantivas = !soSubstantivas;
		applyFilter();
	}

	function nextPage() {
		pagina++;
		loadProposicoes();
	}

	function prevPage() {
		if (pagina > 1) {
			pagina--;
			loadProposicoes();
		}
	}

	function toggleExpand(id: number) {
		expandedId = expandedId === id ? null : id;
	}

	onMount(async () => {
		const [, f] = await Promise.all([
			loadProposicoes(),
			api.get<Filtros>('/proposicoes/filtros')
		]);
		filtros = f;
	});

</script>

<svelte:head>
	<title>Proposições — voto.vc</title>
</svelte:head>

<div class="page">
	<div class="page-header">
		<h1>Proposições</h1>
		<label class="filter-toggle">
			<input type="checkbox" checked={soSubstantivas} onchange={toggleSubstantivas} />
			Só substantivas
			<span class="filter-hint" title="Proposições com impacto legislativo direto: PL, PEC, MPV, PLP, PDL">?</span>
		</label>
	</div>

	<div class="filters">
		<input
			type="text"
			placeholder="Buscar por texto..."
			value={busca}
			oninput={onBuscaInput}
			class="search-input"
		/>
		<div class="filter-row">
			{#if filtros}
				<select bind:value={filtroTema} onchange={applyFilter}>
					<option value="">Todos os temas</option>
					{#each filtros.temas.toSorted((a, b) => (TEMAS[a.valor]?.label ?? a.valor).localeCompare(TEMAS[b.valor]?.label ?? b.valor, 'pt-BR')) as t}
						{@const info = getTema(t.valor)}
						<option value={t.valor}>{info?.label ?? t.valor} ({t.count})</option>
					{/each}
				</select>
				<select bind:value={filtroTipo} onchange={applyFilter}>
					<option value="">Todos os tipos</option>
					{#each filtros.tipos.toSorted((a, b) => a.valor.localeCompare(b.valor)) as t}
						<option value={t.valor}>{t.valor} ({t.count})</option>
					{/each}
				</select>
				<select bind:value={filtroAno} onchange={applyFilter}>
					<option value="">Todos os anos</option>
					{#each filtros.anos as a}
						<option value={a}>{a}</option>
					{/each}
				</select>
			{/if}
		</div>
	</div>

	{#if loading}
		<div class="status">Carregando...</div>
	{:else if proposicoes.length === 0}
		<div class="status">Nenhuma proposição encontrada.</div>
	{:else}
		<div class="list">
			{#each proposicoes as p}
				{@const hasDetails = p.substantiva && (p.resumo_cidadao || p.descricao_detalhada)}
				{@const isExpanded = expandedId === p.id}
				<button
					type="button"
					class="prop-card"
					class:expandable={hasDetails}
					class:expanded={isExpanded}
					onclick={() => hasDetails && toggleExpand(p.id)}
				>
					<div class="prop-main">
						<div class="prop-info">
							<div class="prop-top">
								<span class="prop-tipo">{p.tipo} {p.numero}/{p.ano}</span>
								{#each p.casas as c}
									{#if c.url}
										<a href={c.url} target="_blank" rel="noopener" class="casa-pill {c.casa}" onclick={(e) => e.stopPropagation()}>{c.casa === 'camara' ? 'Câmara' : 'Senado'}</a>
									{:else}
										<span class="casa-pill {c.casa}">{c.casa === 'camara' ? 'Câmara' : 'Senado'}</span>
									{/if}
								{/each}
								{#if p.tema}
									{@const info = getTema(p.tema)}
									<span class="tema-tag" style="background: {info.cor}1a; color: {info.cor}; border-color: {info.cor}33">{info.label}</span>
								{/if}
								{#if p.substantiva}
									<span class="prop-badge">Substantiva</span>
								{/if}
							</div>
							<p class="prop-text">{p.resumo_cidadao ?? p.ementa ?? 'Sem descrição'}</p>
						</div>
						{#if hasDetails}
							<span class="expand-icon" class:open={isExpanded}>▾</span>
						{/if}
					</div>

					{#if isExpanded && p.descricao_detalhada}
						<div class="prop-details">
							<p class="detail-descricao">{p.descricao_detalhada}</p>
						</div>
					{/if}
				</button>
			{/each}
		</div>

		<div class="pagination">
			<button onclick={prevPage} disabled={pagina <= 1}>Anterior</button>
			<span>Página {pagina} de {totalPaginas}</span>
			<button onclick={nextPage} disabled={pagina >= totalPaginas}>Próxima</button>
		</div>
	{/if}
</div>

<style>
	.page {
		max-width: 700px;
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
		color: var(--text-primary);
		margin: 0;
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
		accent-color: #2563eb;
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

	.filters {
		margin-bottom: 1.5rem;
	}

	.search-input {
		width: 100%;
		padding: 0.625rem 1rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-card);
		color: var(--text-primary);
		font-size: 0.938rem;
		margin-bottom: 0.75rem;
		box-sizing: border-box;
	}

	.search-input::placeholder {
		color: var(--text-secondary);
	}

	.filter-row {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	select {
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-card);
		color: var(--text-primary);
		font-size: 0.875rem;
		cursor: pointer;
	}

	.prop-card {
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

	.prop-card.expandable {
		cursor: pointer;
	}

	.prop-card.expandable:hover {
		border-color: var(--border-hover);
	}

	.prop-card.expanded {
		border-color: var(--link);
	}

	.prop-main {
		display: flex;
		gap: 1rem;
		align-items: flex-start;
	}

	.prop-info {
		flex: 1;
	}

	.prop-top {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		flex-wrap: wrap;
	}

	.prop-tipo {
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

	.prop-badge {
		font-size: 0.7rem;
		font-weight: 600;
		color: #16a34a;
		background: #dcfce71a;
		border: 1px solid #16a34a33;
		padding: 0.1rem 0.4rem;
		border-radius: 10px;
	}

	.prop-text {
		margin: 0.5rem 0 0;
		color: var(--text-primary);
		font-size: 0.9rem;
		line-height: 1.4;
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

	.prop-details {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--border);
	}

	.detail-descricao {
		font-size: 0.9rem;
		color: var(--text-primary);
		line-height: 1.6;
		margin: 0 0 0.75rem;
	}

	.casa-pill {
		display: inline-block;
		font-size: 0.7rem;
		font-weight: 700;
		padding: 0.15rem 0.5rem;
		border-radius: 10px;
		text-decoration: none;
		line-height: 1.4;
	}

	.casa-pill.camara {
		background: #2563eb1a;
		color: #2563eb;
		border: 1px solid #2563eb33;
	}

	.casa-pill.senado {
		background: #db27781a;
		color: #db2778;
		border: 1px solid #db277833;
	}

	a.casa-pill:hover {
		filter: brightness(0.85);
	}

	@media (prefers-color-scheme: dark) {
		.casa-pill.camara {
			background: #2563eb33;
			color: #60a5fa;
			border-color: #2563eb55;
		}
		.casa-pill.senado {
			background: #db277833;
			color: #f472b6;
			border-color: #db277855;
		}
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

	.status {
		text-align: center;
		padding: 4rem;
		color: var(--text-secondary);
	}
</style>
