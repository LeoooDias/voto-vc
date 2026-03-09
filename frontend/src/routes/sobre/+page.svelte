<svelte:head>
	<title>Sobre — voto.vc</title>
</svelte:head>

<div class="sobre">
	<h1>Sobre o voto.vc</h1>

	<section>
		<h2>O que é</h2>
		<p>
			O voto.vc ajuda eleitores brasileiros a encontrar os políticos e partidos
			que mais se alinham com seus pontos de vista, baseando-se exclusivamente
			em dados públicos de votações do Congresso Nacional.
		</p>
	</section>

	<section>
		<h2>Como funciona</h2>
		<ol>
			<li>Você responde a proposições reais que foram votadas no Congresso</li>
			<li>Comparamos suas respostas com os votos reais de cada parlamentar</li>
			<li>Mostramos quem mais vota como você votaria</li>
		</ol>
	</section>

	<section>
		<h2>Fontes de dados</h2>
		<ul>
			<li>Câmara dos Deputados — Dados Abertos (dadosabertos.camara.leg.br)</li>
			<li>Senado Federal — Dados Abertos (legis.senado.leg.br/dadosabertos)</li>
		</ul>
	</section>

	<section>
		<h2>Metodologia</h2>
		<p>
			As proposições são classificadas em tópicos usando regras transparentes
			baseadas em palavras-chave das ementas. O score de alinhamento é calculado
			comparando diretamente o voto do usuário com o voto nominal do parlamentar
			em cada proposição. Abstenções e ausências não contam positiva nem negativamente.
		</p>
		<p>
			A metodologia completa, incluindo as regras de classificação, é aberta e
			disponível no código-fonte do projeto.
		</p>
	</section>

	<section>
		<h2>Compromisso com neutralidade</h2>
		<p>
			O voto.vc não tem filiação partidária. A seleção de proposições para o
			questionário busca diversidade temática e relevância, não favorecimento de
			qualquer posição. Toda a lógica é transparente e auditável.
		</p>
	</section>
</div>

<style>
	.sobre {
		max-width: 700px;
		margin: 0 auto;
	}

	h1 {
		color: #1a1a2e;
		margin-bottom: 2rem;
	}

	h2 {
		color: #2563eb;
		margin-top: 2rem;
	}

	p, li {
		color: #4b5563;
		line-height: 1.7;
	}

	section {
		margin-bottom: 1.5rem;
	}
</style>
