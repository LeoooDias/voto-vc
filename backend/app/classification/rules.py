"""Keyword/regex rules for mapping proposição ementas to topics.

Each topic has a list of keywords. The classifier scores by keyword density.
Rules are fully transparent and versionable.
"""

TOPIC_RULES: dict[str, list[str]] = {
    "economia": [
        "econom", "PIB", "crescimento economico", "inflacao", "juros", "Selic",
        "banco central", "politica monetaria", "divida publica", "orcamento",
        "superavit", "deficit", "cambio", "investimento publico",
    ],
    "tributacao": [
        "tribut", "imposto", "taxa", "contribuicao", "ICMS", "ISS", "IPI",
        "reforma tributaria", "isencao fiscal", "aliquota", "sonegacao",
        "simples nacional", "nota fiscal",
    ],
    "saude": [
        "saude", "SUS", "hospital", "medic", "vacina", "pandemia", "epidemia",
        "farmac", "plano de saude", "vigilancia sanitaria", "Anvisa",
        "atencao basica", "leito", "UBS",
    ],
    "educacao": [
        "educa", "ensino", "escola", "universidade", "professor", "aluno",
        "Fundeb", "vestibular", "Enem", "pesquisa cientifica", "bolsa de estudo",
        "creche", "alfabetizacao", "MEC",
    ],
    "meio-ambiente": [
        "ambiental", "meio ambiente", "desmatamento", "carbono", "clima",
        "fauna", "flora", "saneamento", "poluicao", "reciclagem", "Ibama",
        "licenciamento ambiental", "energia renovavel", "biodiversidade",
        "area de preservacao", "rio", "agua",
    ],
    "seguranca": [
        "seguranca publica", "policia", "arma", "penal", "crime", "violencia",
        "trafico", "drogas", "presidio", "sistema penitenciario", "homicidio",
        "feminicidio", "legítima defesa",
    ],
    "direitos-humanos": [
        "direitos humanos", "direitos civis", "igualdade", "discriminacao",
        "racismo", "genero", "LGBTQ", "indigena", "quilombo", "deficiente",
        "acessibilidade", "refugiad", "crianca e adolescente", "idoso",
    ],
    "trabalho": [
        "trabalh", "emprego", "CLT", "carteira assinada", "salario minimo",
        "ferias", "FGTS", "sindicato", "terceirizacao", "trabalho escravo",
        "desemprego", "seguro desemprego", "jornada de trabalho",
    ],
    "agricultura": [
        "agri", "agroneg", "rural", "reforma agraria", "MST", "agrotox",
        "transgenic", "Embrapa", "financiamento rural", "safra", "pecuaria",
        "irrigacao", "alimento",
    ],
    "defesa": [
        "defesa nacional", "forcas armadas", "exercito", "marinha", "aeronautica",
        "fronteira", "soberania", "militar", "seguranca nacional",
    ],
    "tecnologia": [
        "tecnologia", "internet", "dados pessoais", "LGPD", "inovacao",
        "inteligencia artificial", "startup", "telecomunicacao", "digital",
        "ciberseg", "5G", "marco civil",
    ],
    "corrupcao": [
        "corrupcao", "transparencia", "lava jato", "propina", "peculato",
        "improbidade", "acesso a informacao", "lei anticorrupcao",
        "tribunal de contas", "CGU", "fiscalizacao",
    ],
    "previdencia": [
        "previdencia", "aposentadoria", "INSS", "reforma previdenciaria",
        "pensao", "beneficio social", "idade minima", "tempo de contribuicao",
    ],
    "habitacao": [
        "habitacao", "moradia", "minha casa", "aluguel", "imovel",
        "programa habitacional", "sem teto", "regularizacao fundiaria",
    ],
    "transporte": [
        "transporte", "mobilidade", "rodovia", "ferrovia", "aeroporto",
        "porto", "metro", "onibus", "pedagio", "infraestrutura",
        "concessao rodoviaria",
    ],
    "cultura": [
        "cultura", "arte", "patrimonio cultural", "esporte", "museu",
        "cinema", "musica", "lei rouanet", "incentivo cultural", "olimpiad",
    ],
}
