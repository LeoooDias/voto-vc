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
			em dados públicos de votações nominais da Câmara dos Deputados e do Senado Federal.
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
		<p>
			O voto.vc cobre votações nominais da Câmara dos Deputados e do Senado Federal,
			incluindo dados históricos desde 2003.
		</p>
	</section>

	<section id="metodologia">
		<h2>Metodologia</h2>
		<p>
			A métrica de alinhamento mede o quanto um parlamentar ou partido vota de forma
			parecida com você. Veja como funciona em detalhes:
		</p>

		<h3>Alinhamento de parlamentar</h3>
		<p>
			Para cada proposição que você e o parlamentar votaram, comparamos os votos.
			Concordância (ambos SIM ou ambos NÃO) soma pontos; discordância subtrai.
			A importância que você atribui a cada voto (peso) é levada em conta —
			votos que você marcou como mais importantes pesam mais no cálculo.
		</p>
		<p>
			O resultado é normalizado em uma escala de 0 a 100, onde 100 = concordância
			total, 50 = neutro, e 0 = discordância total. Abstenções, ausências e votos
			marcados como "Neutro" ou "Pular" são ignorados.
		</p>

		<h3>Ajuste de confiança</h3>
		<p>
			Para evitar que parlamentares com poucos votos em comum dominem o ranking,
			aplicamos um ajuste estatícstico ajusta resultados com poucas comparações
			em direção ao neutro (50). Na prática, isso significa que um parlamentar
			precisa de várias votações em comum com você para alcançar alinhamento alto
			ou baixo. Quanto mais votos em comum, mais confiável o alinhamento.
		</p>
		<p>
			Os 5 pontos exibidos no resultado refletem esse resultado ajustado —
			o mesmo valor usado para ordenar o ranking.
		</p>

		<h3>Alinhamento de partido</h3>
		<p>
			Partidos são avaliados com uma abordagem híbrida. Primeiro, verificamos
			se o partido emitiu uma orientação oficial de bancada (SIM, NÃO ou
			LIBERADO) para a votação. Se a orientação é LIBERADO, a proposição é
			ignorada para aquele partido.
		</p>
		<p>
			Quando não há orientação oficial, usamos o voto majoritário dos
			parlamentares do partido como alternativa — mas somente se pelo menos 60%
			dos membros votaram na mesma direção. O peso desse voto majoritário é
			ponderado pela unanimidade (quanto mais unânime, mais peso).
		</p>

		<h3>Classificação por tema</h3>
		<p>
			As proposições são classificadas em temas por inteligência artificial
			com base na ementa e no resumo de cada proposição. O questionário
			seleciona proposições de forma diversa entre os temas para cobrir o maior
			espectro de pautas possível.
		</p>
	</section>

	<section>
		<h2>Compromisso com neutralidade</h2>
		<p>
			O voto.vc não tem filiação partidária. A seleção de proposições para o
			questionário busca diversidade temática e relevância, não favorecimento de
			qualquer posição.
		</p>
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
