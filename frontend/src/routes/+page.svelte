<svelte:head>
	<title>voto.vc — Descubra seu perfil político</title>
</svelte:head>

<div class="hero">
	<h1>Descubra quais políticos votam como você</h1>
	<p class="subtitle">
		Responda a proposições reais do Congresso Nacional e veja quais parlamentares
		mais se alinham com seus pontos de vista. Baseado em dados públicos, com
		total transparência.
	</p>
	<a href="/questionario" class="cta">Começar questionário</a>

	<div class="features">
		<div class="feature">
			<h3>Dados reais</h3>
			<p>Baseado em votações nominais da Câmara e do Senado Federal</p>
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
		color: #1a1a2e;
		margin-bottom: 1rem;
		line-height: 1.2;
	}

	.subtitle {
		font-size: 1.25rem;
		color: #6b7280;
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
		background: white;
		padding: 1.5rem;
		border-radius: 12px;
		border: 1px solid #e5e7eb;
	}

	.feature h3 {
		color: #2563eb;
		margin: 0 0 0.5rem;
	}

	.feature p {
		color: #6b7280;
		margin: 0;
		line-height: 1.5;
	}
</style>
