<svelte:head>
	<title>voto.vc — seja representado</title>
</svelte:head>

<div class="hero">
	<p class="eyebrow">Eleições 2026</p>
	<h1>Descubra quem<br />vota como você.</h1>
	<p class="subtitle">
		Vote em proposições reais do Congresso Nacional e descubra
		quais parlamentares e partidos mais se alinham com seus valores.
	</p>
	<a href="/vote" class="cta">
		Comece a votar
		<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
	</a>
	<p class="cta-sub">10 perguntas · 5 minutos · sem criar conta</p>

	<section class="como-funciona">
		<h2>Como funciona</h2>
		<div class="steps">
			<div class="step">
				<span class="step-number">1</span>
				<h3>Escolha seu estado</h3>
				<p>Selecione sua UF para ver parlamentares da sua região</p>
			</div>
			<div class="step step-center">
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
	</section>

	<section class="features">
		<div class="feature">
			<div class="feature-icon">
				<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
			</div>
			<h3>Dados reais</h3>
			<p>Baseado em votações nominais da Câmara dos Deputados e do Senado Federal</p>
		</div>
		<div class="feature">
			<div class="feature-icon">
				<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
			</div>
			<h3>Neutro e transparente</h3>
			<p>Sem viés partidário. Metodologia aberta e código-fonte público</p>
		</div>
		<div class="feature">
			<div class="feature-icon">
				<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
			</div>
			<h3>Rápido e anônimo</h3>
			<p>Responda em minutos. Não precisa criar conta para ver resultados</p>
		</div>
	</section>
</div>

<style>
	.hero {
		text-align: center;
		padding: 5rem 0 3rem;
		max-width: 720px;
		margin: 0 auto;
	}

	.eyebrow {
		font-family: var(--font-heading);
		font-size: 0.8rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.15em;
		color: var(--accent);
		margin: 0 0 1rem;
	}

	h1 {
		font-family: var(--font-heading);
		font-size: 3.5rem;
		font-weight: 800;
		color: var(--text-primary);
		margin: 0 0 1.25rem;
		line-height: 1.1;
		letter-spacing: -0.03em;
	}

	.subtitle {
		font-size: 1.2rem;
		color: var(--text-secondary);
		max-width: 520px;
		margin: 0 auto 2.5rem;
		line-height: 1.6;
	}

	.cta {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		background: var(--accent);
		color: white;
		padding: 1rem 2.5rem;
		border-radius: 10px;
		text-decoration: none;
		font-family: var(--font-heading);
		font-size: 1.125rem;
		font-weight: 700;
		transition: background 0.2s, transform 0.15s;
		box-shadow: 0 4px 14px color-mix(in srgb, var(--accent) 35%, transparent);
	}

	.cta:hover {
		background: var(--accent-hover);
		transform: translateY(-1px);
	}

	.cta:active {
		transform: translateY(0);
	}

	.cta-sub {
		font-size: 0.8rem;
		color: var(--text-secondary);
		margin: 1rem 0 0;
		letter-spacing: 0.02em;
	}

	/* Features */
	.features {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: 1.5rem;
		margin-top: 4rem;
		text-align: left;
	}

	.feature {
		background: var(--bg-card);
		padding: 1.75rem;
		border-radius: 14px;
		border: 1px solid var(--border);
		transition: border-color 0.2s;
	}

	.feature:hover {
		border-color: var(--border-hover);
	}

	.feature-icon {
		width: 44px;
		height: 44px;
		border-radius: 10px;
		background: color-mix(in srgb, var(--link) 10%, transparent);
		color: var(--link);
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 1rem;
	}

	.feature h3 {
		font-family: var(--font-heading);
		color: var(--text-primary);
		margin: 0 0 0.5rem;
		font-size: 1.05rem;
		font-weight: 700;
	}

	.feature p {
		color: var(--text-secondary);
		margin: 0;
		line-height: 1.6;
		font-size: 0.9rem;
	}

	/* How it works */
	.como-funciona {
		margin-top: 5rem;
		text-align: center;
	}

	.como-funciona h2 {
		font-family: var(--font-heading);
		color: var(--text-primary);
		font-size: 1.75rem;
		font-weight: 800;
		letter-spacing: -0.02em;
		margin-bottom: 2.5rem;
	}

	.steps {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 2rem;
		text-align: center;
		position: relative;
	}

	.step {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
	}

	.step-number {
		width: 48px;
		height: 48px;
		border-radius: 50%;
		background: var(--text-primary);
		color: var(--bg-page);
		font-family: var(--font-heading);
		font-weight: 800;
		font-size: 1.25rem;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 0.5rem;
	}

	.step h3 {
		font-family: var(--font-heading);
		color: var(--text-primary);
		margin: 0;
		font-size: 1.05rem;
		font-weight: 700;
	}

	.step p {
		color: var(--text-secondary);
		margin: 0;
		line-height: 1.5;
		font-size: 0.9rem;
	}

	@media (max-width: 600px) {
		h1 {
			font-size: 2.5rem;
		}

		.hero {
			padding: 3rem 0 2rem;
		}

		.subtitle {
			font-size: 1.05rem;
		}
	}
</style>
