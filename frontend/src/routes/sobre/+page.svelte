<script lang="ts">
	import { _ } from 'svelte-i18n';
</script>

<svelte:head>
	<title>{$_('sobre.title')}</title>
</svelte:head>

<div class="sobre">
	<h1>{$_('sobre.h1')}</h1>

	<section>
		<h2>{$_('sobre.oQueE')}</h2>
		<p>{$_('sobre.oQueEDesc')}</p>
	</section>

	<section>
		<h2>{$_('sobre.comoFunciona')}</h2>
		<ol>
			<li>{$_('sobre.comoFunciona1')}</li>
			<li>{$_('sobre.comoFunciona2')}</li>
			<li>{$_('sobre.comoFunciona3')}</li>
		</ol>
	</section>

	<section>
		<h2>{$_('sobre.fontes')}</h2>
		<ul>
			<li>{$_('sobre.fonteCamara')}</li>
			<li>{$_('sobre.fonteSenado')}</li>
		</ul>
		<p>{$_('sobre.fontesDesc')}</p>
	</section>

	<section id="metodologia">
		<h2>{$_('sobre.metodologia')}</h2>
		<p>{$_('sobre.metodologiaDesc')}</p>

		<h3>{$_('sobre.alinhamentoParlamentar')}</h3>
		<p>{$_('sobre.alinhamentoParlamentarDesc1')}</p>
		<p>{$_('sobre.alinhamentoParlamentarDesc2')}</p>

		<h3>{$_('sobre.ajusteConfianca')}</h3>
		<p>{$_('sobre.ajusteConfiancaDesc1')}</p>
		<p>{$_('sobre.ajusteConfiancaDesc2')}</p>

		<h3>{$_('sobre.alinhamentoPartido')}</h3>
		<p>{$_('sobre.alinhamentoPartidoDesc1')}</p>
		<p>{$_('sobre.alinhamentoPartidoDesc2')}</p>

		<h3>{$_('sobre.classificacaoTema')}</h3>
		<p>{$_('sobre.classificacaoTemaDesc')}</p>
	</section>

	<section>
		<h2>{$_('sobre.compromisso')}</h2>
		<p>{$_('sobre.compromissoDesc')}</p>
	</section>

	<section>
		<h2>{$_('sobre.quemSomos')}</h2>
		<p>{$_('sobre.quemSomosP1')}</p>
		<p>{$_('sobre.quemSomosP2')}</p>
		<p>{$_('sobre.quemSomosP3')}</p>
		<p>{$_('sobre.quemSomosP4')}</p>
	</section>
</div>

<style>
	.sobre {
		max-width: 700px;
		margin: 0 auto;
	}

	h1 {
		color: var(--text-primary);
		margin-bottom: 2rem;
	}

	h2 {
		color: var(--link);
		margin-top: 2rem;
	}

	h3 {
		color: var(--text-primary);
		font-size: 1rem;
		margin-top: 1.25rem;
		margin-bottom: 0.25rem;
	}

	p, li {
		color: var(--text-secondary);
		line-height: 1.7;
	}

	section {
		margin-bottom: 1.5rem;
		scroll-margin-top: 2rem;
	}
</style>
