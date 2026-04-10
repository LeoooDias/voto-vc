<script lang="ts">
	import { _ } from 'svelte-i18n';
</script>

<svelte:head>
	<title>{$_('privacidade.title')}</title>
</svelte:head>

<div class="privacidade">
	<h1>{$_('privacidade.h1')}</h1>
	<p class="updated">{$_('privacidade.ultimaAtualizacao')}</p>

	<section>
		<h2>{$_('privacidade.resumoTitulo')}</h2>
		<p>{$_('privacidade.resumoDesc')}</p>
	</section>

	<section>
		<h2>{$_('privacidade.quaisColetamosTitulo')}</h2>
		<p>{$_('privacidade.naoColetamos')}</p>
		<ul>
			<li>{$_('privacidade.naoColetamos1')}</li>
			<li>{$_('privacidade.naoColetamos2')}</li>
			<li>{$_('privacidade.naoColetamos3')}</li>
			<li>{$_('privacidade.naoColetamos4')}</li>
		</ul>
	</section>

	<section>
		<h2>{$_('privacidade.armazenamentoLocalTitulo')}</h2>
		<p>{$_('privacidade.armazenamentoLocalDesc')}</p>
	</section>

	<section>
		<h2>{$_('privacidade.perfilCompartilhadoTitulo')}</h2>
		<p>{$_('privacidade.perfilCompartilhadoDesc')}</p>
		<ul>
			<li>{$_('privacidade.perfilCompartilhado1')}</li>
			<li>{$_('privacidade.perfilCompartilhado2')}</li>
			<li>{$_('privacidade.perfilCompartilhado3')}</li>
		</ul>
		<p>{$_('privacidade.perfilCompartilhadoNota')}</p>
	</section>

	<section>
		<h2>{$_('privacidade.calculoAlinhamentoTitulo')}</h2>
		<p>{$_('privacidade.calculoAlinhamentoDesc')}</p>
	</section>

	<section>
		<h2>{$_('privacidade.chatTitulo')}</h2>
		<p>{$_('privacidade.chatDesc')}</p>
	</section>

	<section>
		<h2>{$_('privacidade.terceirosTitulo')}</h2>
		<p>{$_('privacidade.terceirosDesc')}</p>
		<ul>
			<li>{$_('privacidade.terceiros1')}</li>
			<li>{$_('privacidade.terceiros2')}</li>
		</ul>
		<p>{$_('privacidade.terceirosNota')}</p>
	</section>

	<section>
		<h2>{$_('privacidade.direitosTitulo')}</h2>
		<p>{$_('privacidade.direitosDesc')}</p>
	</section>

	<section>
		<h2>{$_('privacidade.contatoTitulo')}</h2>
		<p>{$_('privacidade.contatoDesc')}</p>
	</section>

	<section>
		<h2>{$_('privacidade.alteracoesTitulo')}</h2>
		<p>{$_('privacidade.alteracoesDesc')}</p>
	</section>
</div>

<style>
	.privacidade {
		max-width: 700px;
		margin: 0 auto;
	}

	h1 {
		color: var(--text-primary);
		margin-bottom: 0.5rem;
	}

	.updated {
		color: var(--text-secondary);
		font-size: 0.813rem;
		margin-bottom: 2rem;
	}

	h2 {
		color: var(--link);
		margin-top: 2rem;
	}

	p, li {
		color: var(--text-secondary);
		line-height: 1.7;
	}

	section {
		margin-bottom: 1.5rem;
	}

	ul {
		padding-left: 1.25rem;
	}

	li {
		margin-bottom: 0.25rem;
	}
</style>
