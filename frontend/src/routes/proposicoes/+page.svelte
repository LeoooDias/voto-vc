<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';

	interface Proposicao {
		id: number;
		tipo: string;
		numero: number;
		ano: number;
		ementa: string | null;
		resumo_cidadao: string | null;
		tema: string | null;
		substantiva: boolean;
	}

	interface Filtros {
		temas: { valor: string; count: number }[];
		tipos: { valor: string; count: number }[];
		anos: number[];
	}

	let proposicoes: Proposicao[] = $state([]);
	let filtros: Filtros | null = $state(null);
	let loading = $state(true);
	let pagina = $state(1);

	let filtroTema = $state('');
	let filtroTipo = $state('');
	let filtroAno = $state('');
	let filtroSubstantiva = $state('');
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
			if (filtroSubstantiva === 'sim') params.set('substantiva', 'true');
			if (filtroSubstantiva === 'nao') params.set('substantiva', 'false');
			if (buscaDebounced) params.set('busca', buscaDebounced);
			proposicoes = await api.get<Proposicao[]>(`/proposicoes/?${params}`);
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

	onMount(async () => {
		const [, f] = await Promise.all([
			loadProposicoes(),
			api.get<Filtros>('/proposicoes/filtros')
		]);
		filtros = f;
	});

	const temaInfo: Record<string, string> = {
		economia: 'Economia',
		tributacao: 'Tributação',
		saude: 'Saúde',
		educacao: 'Educação',
		'meio-ambiente': 'Meio Ambiente',
		seguranca: 'Segurança',
		'direitos-humanos': 'Direitos Humanos',
		trabalho: 'Trabalho',
		agricultura: 'Agricultura',
		defesa: 'Defesa',
		tecnologia: 'Tecnologia',
		corrupcao: 'Transparência',
		previdencia: 'Previdência',
		habitacao: 'Habitação',
		transporte: 'Transporte',
		cultura: 'Cultura',
		geral: 'Legislação'
	};
</script>

<svelte:head>
	<title>Proposições — voto.vc</title>
</svelte:head>

<div class="page">
	<h1>Proposições</h1>

	<div class="filters">
		<input
			type="text"
			placeholder="Buscar por texto..."
			value={busca}
			oninput={onBuscaInput}
			class="search-input"
		/>
		<div class="filter-row">
			<select bind:value={filtroSubstantiva} onchange={applyFilter}>
				<option value="">Todas</option>
				<option value="sim">Substantivas</option>
				<option value="nao">Não substantivas</option>
			</select>
			{#if filtros}
				<select bind:value={filtroTema} onchange={applyFilter}>
					<option value="">Todos os temas</option>
					{#each filtros.temas as t}
						<option value={t.valor}>{temaInfo[t.valor] ?? t.valor} ({t.count})</option>
					{/each}
				</select>
				<select bind:value={filtroTipo} onchange={applyFilter}>
					<option value="">Todos os tipos</option>
					{#each filtros.tipos as t}
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
				<div class="prop-card">
					<div class="prop-header">
						<span class="prop-tipo">{p.tipo} {p.numero}/{p.ano}</span>
						{#if p.tema}
							<span class="prop-tema">{temaInfo[p.tema] ?? p.tema}</span>
						{/if}
						{#if p.substantiva}
							<span class="prop-badge">Substantiva</span>
						{/if}
					</div>
					<p class="prop-text">{p.resumo_cidadao ?? p.ementa ?? 'Sem descrição'}</p>
				</div>
			{/each}
		</div>

		<div class="pagination">
			<button onclick={prevPage} disabled={pagina <= 1}>Anterior</button>
			<span>Página {pagina}</span>
			<button onclick={nextPage} disabled={proposicoes.length < 50}>Próxima</button>
		</div>
	{/if}
</div>

<style>
	.page {
		max-width: 800px;
		margin: 0 auto;
	}

	h1 {
		color: var(--text-primary);
		margin-bottom: 1.5rem;
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
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1rem 1.25rem;
		margin-bottom: 0.5rem;
	}

	.prop-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		margin-bottom: 0.5rem;
	}

	.prop-tipo {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--link);
		background: var(--bg-page);
		padding: 0.125rem 0.5rem;
		border-radius: 4px;
	}

	.prop-tema {
		font-size: 0.75rem;
		color: var(--text-secondary);
		background: var(--bg-page);
		padding: 0.125rem 0.5rem;
		border-radius: 10px;
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
		margin: 0;
		color: var(--text-primary);
		font-size: 0.938rem;
		line-height: 1.5;
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
