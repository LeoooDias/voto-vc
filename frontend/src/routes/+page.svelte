<svelte:head>
	<title>voto.vc — seja representado</title>
</svelte:head>

<div class="hero">
	<h1>Descubra quem vota como você.</h1>
	<p class="subtitle">
		Vote em proposições reais do Congresso Nacional e descubra
		quais parlamentares e partidos mais se alinham com seus valores.
	</p>
	<a href="/vote" class="cta">Comece a votar</a>

	<!-- TODO: Adicionar aqui uma imagem/mockup mostrando um exemplo de resultado
	     (screenshot da página de perfil com ranking de parlamentares + scores).
	     Sugestão: imagem 800x500px, com bordas arredondadas e sombra sutil.
	     Formatos: PNG para screenshot, SVG para ilustração estilizada.
	     Alternativa: GIF animado curto mostrando o fluxo votação → resultado. -->

	<div class="como-funciona">
		<h2>Como funciona</h2>
		<div class="steps">
			<div class="step">
				<span class="step-number">1</span>
				<h3>Escolha seu estado</h3>
				<p>Selecione sua UF para ver parlamentares da sua região</p>
			</div>
			<div class="step">
				<span class="step-number">2</span>
				<h3>Vote nas proposições</h3>
				<p>Diga se é a favor ou contra propostas reais votadas no Congresso</p>
			</div>
			<div class="step">
				<span class="step-number">3</span>
				<h3>Veja seu alinhamento</h3>
				<p>Descubra quais políticos e partidos votam como você votaria</p>
			</div>
		</div>
	</div>

	<div class="features">
		<div class="feature">
			<h3>Dados reais</h3>
			<p>Baseado em votações nominais da Câmara dos Deputados e do Senado Federal</p>
		</div>
		<div class="feature">
			<h3>Neutro e transparente</h3>
			<p>Sem viés partidário. Metodologia aberta e código-fonte público</p>
		</div>
		<div class="feature">
			<h3>Rápido e anônimo</h3>
			<p>Responda 10 perguntas em minutos. Não precisa criar conta</p>
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

	.como-funciona {
		margin-top: 4rem;
		text-align: center;
	}

	.como-funciona h2 {
		color: var(--text-primary);
		font-size: 1.5rem;
		margin-bottom: 2rem;
	}

	.steps {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 2rem;
		text-align: center;
	}

	.step {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
	}

	.step-number {
		width: 40px;
		height: 40px;
		border-radius: 50%;
		background: #2563eb;
		color: white;
		font-weight: 700;
		font-size: 1.125rem;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 0.25rem;
	}

	.step h3 {
		color: var(--text-primary);
		margin: 0;
		font-size: 1.05rem;
	}

	.step p {
		color: var(--text-secondary);
		margin: 0;
		line-height: 1.5;
		font-size: 0.9rem;
	}
</style>
