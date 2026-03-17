<svelte:head>
	<title>voto.vc — seja representado</title>
</svelte:head>

<div class="hero">
	<h1>Descubra quem vota como você.</h1>
	<p class="subtitle">
		Responda a proposições reais votadas no Congresso Nacional e veja quais
		deputados, senadores e partidos mais se alinham com seus pontos de vista.
		Baseado em dados públicos, com total transparência.
	</p>
	<a href="/vote" class="cta">Vote</a>

	<div class="features">
		<div class="feature">
			<h3>Dados reais</h3>
			<p>Baseado em votações nominais da Câmara e do Senado</p>
		</div>
		<div class="feature">
			<h3>Neutro</h3>
			<p>Sem viés partidário. Metodologia aberta e transparente</p>
		</div>
		<div class="feature">
			<h3>Seu controle</h3>
			<p>Vote como se estivesse no Congresso e veja quem te representa</p>
		</div>
	</div>
</div>

<style>
	.hero {
		text-align: center;
		padding: 4rem 0;
	}

	h1 {
		font-size: 2.5rem;
		color: var(--text-primary);
		margin-bottom: 1rem;
		line-height: 1.2;
	}

	.subtitle {
		font-size: 1.25rem;
		color: var(--text-secondary);
		max-width: 600px;
		margin: 0 auto 2rem;
		line-height: 1.6;
	}

	.cta {
		display: inline-block;
		background: #2563eb;
		color: white;
		padding: 1rem 2.5rem;
		border-radius: 8px;
		text-decoration: none;
		font-size: 1.125rem;
		font-weight: 600;
		transition: background 0.2s;
	}

	.cta:hover {
		background: #1d4ed8;
	}

	.features {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
		gap: 2rem;
		margin-top: 4rem;
		text-align: left;
	}

	.feature {
		background: var(--bg-card);
		padding: 1.5rem;
		border-radius: 12px;
		border: 1px solid var(--border);
	}

	.feature h3 {
		color: var(--link);
		margin: 0 0 0.5rem;
	}

	.feature p {
		color: var(--text-secondary);
		margin: 0;
		line-height: 1.5;
	}
</style>
