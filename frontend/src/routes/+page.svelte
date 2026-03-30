<script lang="ts">
	import { _ } from 'svelte-i18n';
</script>

<svelte:head>
	<title>{$_('home.title')}</title>
</svelte:head>

<div class="hero">
	<p class="eyebrow">{$_('home.eyebrow')}</p>
	<h1>{@html $_('home.h1')}</h1>
	<p class="subtitle">
		{$_('home.subtitle')}
	</p>
	<a href="/vote" class="cta">
		{$_('home.cta')}
		<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
	</a>
	<p class="cta-sub">{$_('home.ctaSub')}</p>

	<section class="como-funciona">
		<h2>{$_('home.comoFunciona')}</h2>
		<div class="steps">
			<div class="step">
				<span class="step-number">1</span>
				<h3>{$_('home.step1Title')}</h3>
				<p>{$_('home.step1Desc')}</p>
			</div>
			<div class="step step-center">
				<span class="step-number">2</span>
				<h3>{$_('home.step2Title')}</h3>
				<p>{$_('home.step2Desc')}</p>
			</div>
			<div class="step">
				<span class="step-number">3</span>
				<h3>{$_('home.step3Title')}</h3>
				<p>{$_('home.step3Desc')}</p>
			</div>
		</div>
	</section>

	<section class="features">
		<div class="feature">
			<div class="feature-icon">
				<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
			</div>
			<h3>{$_('home.dadosReais')}</h3>
			<p>{$_('home.dadosReaisDesc')}</p>
		</div>
		<div class="feature">
			<div class="feature-icon">
				<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
			</div>
			<h3>{$_('home.neutro')}</h3>
			<p>{$_('home.neutroDesc')}</p>
		</div>
		<div class="feature">
			<div class="feature-icon">
				<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
			</div>
			<h3>{$_('home.rapido')}</h3>
			<p>{$_('home.rapidoDesc')}</p>
		</div>
	</section>
</div>

<style>
	.hero {
		text-align: center;
		padding: 8rem 0 4rem;
		max-width: 800px;
		margin: 0 auto;
		animation: heroEntrance 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
	}

	@keyframes heroEntrance {
		from { opacity: 0; transform: translateY(24px); }
		to { opacity: 1; transform: translateY(0); }
	}

	.eyebrow {
		font-family: var(--font-heading);
		font-size: 0.688rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.25em;
		color: var(--text-secondary);
		margin: 0 0 1.5rem;
	}

	h1 {
		font-family: var(--font-heading);
		font-size: 4.5rem;
		font-weight: 900;
		color: var(--text-primary);
		margin: 0 0 2rem;
		line-height: 1.0;
		letter-spacing: -0.05em;
	}

	.subtitle {
		font-size: 1.125rem;
		color: var(--text-secondary);
		max-width: 440px;
		margin: 0 auto 3.5rem;
		line-height: 1.7;
		font-weight: 400;
	}

	.cta {
		display: inline-flex;
		align-items: center;
		gap: 0.625rem;
		background: var(--text-primary);
		color: var(--bg-page);
		padding: 1.125rem 3rem;
		border-radius: 0;
		text-decoration: none;
		font-family: var(--font-heading);
		font-size: 0.875rem;
		font-weight: 800;
		letter-spacing: -0.01em;
		text-transform: uppercase;
		transition: opacity 0.2s;
	}

	.cta:hover {
		background: var(--text-primary);
		opacity: 0.85;
	}

	.cta:active {
		opacity: 0.7;
	}

	.cta-sub {
		font-size: 0.688rem;
		color: var(--text-secondary);
		margin: 1.5rem 0 0;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		font-weight: 500;
	}

	/* Features */
	.features {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0;
		margin-top: 6rem;
		text-align: left;
		border-top: 1px solid var(--border);
	}

	.feature {
		background: transparent;
		padding: 2.5rem 2rem;
		border-radius: 0;
		border: none;
		border-right: 1px solid var(--border);
		transition: background 0.2s;
	}

	.feature:last-child {
		border-right: none;
	}

	.feature:hover {
		background: var(--bg-card);
	}

	.feature-icon {
		width: 40px;
		height: 40px;
		border-radius: 0;
		background: none;
		color: var(--text-primary);
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 1.5rem;
	}

	.feature h3 {
		font-family: var(--font-heading);
		color: var(--text-primary);
		margin: 0 0 0.75rem;
		font-size: 0.938rem;
		font-weight: 800;
		letter-spacing: -0.02em;
	}

	.feature p {
		color: var(--text-secondary);
		margin: 0;
		line-height: 1.6;
		font-size: 0.813rem;
	}

	/* How it works */
	.como-funciona {
		margin-top: 8rem;
		text-align: center;
	}

	.como-funciona h2 {
		font-family: var(--font-heading);
		color: var(--text-primary);
		font-size: 0.688rem;
		font-weight: 700;
		letter-spacing: 0.25em;
		text-transform: uppercase;
		margin-bottom: 4rem;
	}

	.steps {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 4rem;
		text-align: center;
		position: relative;
	}

	.step {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.75rem;
	}

	.step-number {
		width: 56px;
		height: 56px;
		border-radius: 0;
		background: none;
		color: var(--text-primary);
		border: 2px solid var(--text-primary);
		font-family: var(--font-heading);
		font-weight: 900;
		font-size: 1.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 0.75rem;
	}

	.step h3 {
		font-family: var(--font-heading);
		color: var(--text-primary);
		margin: 0;
		font-size: 1rem;
		font-weight: 800;
		letter-spacing: -0.02em;
	}

	.step p {
		color: var(--text-secondary);
		margin: 0;
		line-height: 1.5;
		font-size: 0.813rem;
	}

	@media (max-width: 768px) {
		.features {
			grid-template-columns: 1fr;
			border-top: none;
		}

		.feature {
			border-right: none;
			border-bottom: 1px solid var(--border);
			padding: 2rem 0;
		}

		.feature:last-child {
			border-bottom: none;
		}

		.steps {
			grid-template-columns: 1fr;
			gap: 2.5rem;
		}
	}

	@media (max-width: 600px) {
		h1 {
			font-size: 3rem;
		}

		.hero {
			padding: 2rem 0 3rem;
		}

		.subtitle {
			font-size: 1rem;
		}
	}
</style>
