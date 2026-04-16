<script lang="ts">
	import { _ } from 'svelte-i18n';

	const amounts = [5, 20, 100];
	let selectedAmount: number | null = $state(20);
	let customAmount = $state('');
	let isCustom = $state(false);

	function selectAmount(value: number) {
		selectedAmount = value;
		customAmount = '';
		isCustom = false;
	}

	function selectCustom() {
		selectedAmount = null;
		isCustom = true;
	}

	let donationAmount = $derived(
		isCustom ? parseFloat(customAmount.replace(',', '.')) || 0 : (selectedAmount ?? 0)
	);

	function handleDonate() {
		if (donationAmount <= 0) return;
		// TODO: redirect to payment (Pix / Stripe)
	}
</script>

<svelte:head>
	<title>{$_('contribuir.title')}</title>
</svelte:head>

<div class="contribuir">
	<p class="eyebrow">voto.vc</p>
	<h1>{$_('contribuir.h1')}</h1>
	<p class="hero-desc">{$_('contribuir.heroDesc')}</p>

	<section class="doar-section">
		<h2>{$_('contribuir.escolhaValor')}</h2>
		<div class="amounts">
			{#each amounts as value}
				<button
					class="amount-btn"
					class:active={selectedAmount === value && !isCustom}
					onclick={() => selectAmount(value)}
				>
					R$ {value}
				</button>
			{/each}
		</div>

		<p class="ou">{$_('contribuir.ou')}</p>

		<div class="custom-row">
			<label class="custom-label" for="custom-amount">{$_('contribuir.valorPersonalizado')}</label>
			<div class="custom-input-wrap">
				<span class="custom-prefix">R$</span>
				<input
					id="custom-amount"
					class="custom-input"
					type="text"
					inputmode="decimal"
					placeholder={$_('contribuir.valorPlaceholder')}
					bind:value={customAmount}
					onfocus={() => selectCustom()}
				/>
			</div>
		</div>

		<button
			class="doar-btn"
			disabled={donationAmount <= 0}
			onclick={handleDonate}
		>
			{$_('contribuir.doar')}
		</button>
		<p class="doar-sub">{$_('contribuir.doarSub')}</p>
	</section>

	<section>
		<h2>{$_('contribuir.comoFuncionaTitulo')}</h2>
		<div class="como-funciona">
			<div class="como-step">
				<span class="step-num">1</span>
				<p>{$_('contribuir.comoFuncionaP1')}</p>
			</div>
			<div class="como-step">
				<span class="step-num">2</span>
				<p>{$_('contribuir.comoFuncionaP2')}</p>
			</div>
			<div class="como-step">
				<span class="step-num">3</span>
				<p>{$_('contribuir.comoFuncionaP3')}</p>
			</div>
		</div>
	</section>

	<section>
		<h2>{$_('contribuir.transparenciaTitulo')}</h2>
		<p class="transparencia-desc">{$_('contribuir.transparenciaDesc')}</p>
		<div class="transparencia-card">
			<p class="sem-dados">{$_('contribuir.semDados')}</p>
		</div>
	</section>

	<section class="lar-section">
		<h2>{$_('contribuir.larCasaBelaTitulo')}</h2>
		<div class="lar-content">
			<div class="lar-logo-wrap">
				<img src="/lar-casa-bela-logo.svg" alt={$_('contribuir.logoAlt')} class="lar-logo" />
			</div>
			<div class="lar-text">
				<p>{$_('contribuir.larCasaBelaP1')}</p>
				<p>{$_('contribuir.larCasaBelaP2')}</p>
				<p class="lar-destaque">{$_('contribuir.larCasaBelaP3')}</p>
				<a href="https://larcasabela.org.br" target="_blank" rel="noopener noreferrer" class="lar-link">
					{$_('contribuir.visitarSite')}
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
				</a>
			</div>
		</div>
	</section>
</div>

<style>
	.contribuir {
		max-width: 700px;
		margin: 0 auto;
	}

	.eyebrow {
		text-align: center;
		font-family: var(--font-heading);
		font-size: 0.625rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.25em;
		color: var(--text-secondary);
		margin: 0 0 0.75rem;
	}

	h1 {
		text-align: center;
		color: var(--text-primary);
		font-family: var(--font-heading);
		font-size: 2.5rem;
		font-weight: 900;
		letter-spacing: -0.04em;
		margin: 0 0 1rem;
	}

	.hero-desc {
		text-align: center;
		color: var(--text-secondary);
		font-size: 1rem;
		line-height: 1.7;
		margin: 0 auto 3rem;
		max-width: 540px;
	}

	h2 {
		color: var(--link);
		font-family: var(--font-heading);
		font-size: 1.125rem;
		font-weight: 800;
		letter-spacing: -0.02em;
		margin: 0 0 1.25rem;
	}

	section {
		margin-bottom: 3rem;
	}

	/* Donation amounts */
	.doar-section {
		background: var(--bg-card);
		border: 1px solid var(--border);
		padding: 2rem;
	}

	.amounts {
		display: flex;
		gap: 0.75rem;
	}

	.amount-btn {
		flex: 1;
		padding: 1.125rem 1rem;
		border: 2px solid var(--border);
		border-radius: 0;
		background: transparent;
		color: var(--text-primary);
		font-family: var(--font-heading);
		font-weight: 800;
		font-size: 1.25rem;
		letter-spacing: -0.02em;
		cursor: pointer;
		transition: border-color 0.15s, background 0.15s, color 0.15s;
	}

	.amount-btn:hover {
		border-color: var(--text-primary);
	}

	.amount-btn.active {
		border-color: var(--text-primary);
		background: var(--text-primary);
		color: var(--bg-page);
	}

	.ou {
		text-align: center;
		color: var(--text-secondary);
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		margin: 1rem 0;
	}

	.custom-row {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.custom-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.custom-input-wrap {
		display: flex;
		align-items: center;
		border: 2px solid var(--border);
		transition: border-color 0.15s;
	}

	.custom-input-wrap:focus-within {
		border-color: var(--text-primary);
	}

	.custom-prefix {
		padding: 0.875rem 0 0.875rem 1rem;
		font-family: var(--font-heading);
		font-weight: 800;
		font-size: 1.125rem;
		color: var(--text-secondary);
		user-select: none;
	}

	.custom-input {
		flex: 1;
		padding: 0.875rem 1rem 0.875rem 0.375rem;
		border: none;
		border-radius: 0;
		background: transparent;
		color: var(--text-primary);
		font-family: var(--font-heading);
		font-size: 1.125rem;
		font-weight: 800;
		outline: none;
		box-sizing: border-box;
		width: 100%;
	}

	.custom-input::placeholder {
		color: var(--text-secondary);
		font-weight: 400;
		opacity: 0.5;
	}

	.doar-btn {
		display: block;
		width: 100%;
		padding: 1.125rem;
		background: var(--text-primary);
		color: var(--bg-page);
		border: none;
		border-radius: 0;
		font-family: var(--font-heading);
		font-size: 0.875rem;
		font-weight: 800;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		cursor: pointer;
		transition: opacity 0.15s;
		margin-top: 1.5rem;
	}

	.doar-btn:hover:not(:disabled) {
		opacity: 0.85;
	}

	.doar-btn:disabled {
		opacity: 0.35;
		cursor: default;
	}

	.doar-sub {
		text-align: center;
		color: var(--text-secondary);
		font-size: 0.75rem;
		margin-top: 0.75rem;
	}

	/* How it works */
	.como-funciona {
		display: flex;
		flex-direction: column;
		gap: 0;
	}

	.como-step {
		display: flex;
		gap: 1.25rem;
		align-items: baseline;
		padding: 1rem 0;
		border-bottom: 1px solid var(--border);
	}

	.como-step:last-child {
		border-bottom: none;
	}

	.step-num {
		font-family: var(--font-heading);
		font-weight: 900;
		font-size: 1.5rem;
		color: var(--text-primary);
		min-width: 1.5rem;
		letter-spacing: -0.02em;
	}

	.como-step p {
		margin: 0;
		color: var(--text-secondary);
		line-height: 1.7;
		font-size: 0.938rem;
	}

	/* Transparency */
	.transparencia-desc {
		color: var(--text-secondary);
		font-size: 0.875rem;
		line-height: 1.6;
		margin: 0 0 1rem;
	}

	.transparencia-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		padding: 2rem;
	}

	.sem-dados {
		color: var(--text-secondary);
		font-size: 0.875rem;
		line-height: 1.6;
		margin: 0;
		text-align: center;
		font-style: italic;
	}

	/* Lar Casa Bela */
	.lar-content {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 2rem;
		align-items: start;
	}

	.lar-logo-wrap {
		background: #fff;
		border: 1px solid var(--border);
		padding: 1.25rem;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.lar-logo {
		width: 120px;
		height: auto;
		display: block;
	}

	.lar-text p {
		color: var(--text-secondary);
		line-height: 1.7;
		margin: 0 0 0.75rem;
		font-size: 0.938rem;
	}

	.lar-destaque {
		color: var(--text-primary) !important;
		font-weight: 600;
	}

	.lar-link {
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		color: var(--link);
		text-decoration: none;
		font-weight: 700;
		font-size: 0.875rem;
		margin-top: 0.5rem;
		transition: color 0.15s;
	}

	.lar-link:hover {
		color: var(--link-hover, var(--link));
		text-decoration: underline;
	}

	/* Mobile */
	@media (max-width: 560px) {
		h1 {
			font-size: 2rem;
		}

		.amounts {
			flex-direction: column;
		}

		.doar-section {
			padding: 1.5rem;
		}

		.lar-content {
			grid-template-columns: 1fr;
			justify-items: center;
		}

		.lar-logo-wrap {
			width: fit-content;
		}
	}
</style>
