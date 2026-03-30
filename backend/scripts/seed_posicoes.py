"""
Seed das 20 posições temáticas e seus mapeamentos para proposições.
Idempotente via upsert por slug.

Executar: cd backend && uv run python scripts/seed_posicoes.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.database import async_session
from app.models.posicao import Posicao, PosicaoProposicao

POSICOES = [
    {
        "slug": "privatizacao-estatais",
        "titulo": "Privatização de estatais",
        "titulo_en": "Privatization of state-owned companies",
        "descricao": (
            "Venda de empresas públicas para a iniciativa privada, como Eletrobras, Correios e BNB."
        ),
        "descricao_en": (
            "Sale of state-owned companies to private entities,"
            " such as Eletrobras, Correios, and BNB."
        ),
        "tema": "economia",
        "ordem": 1,
        "proposicoes": [
            (1195, "sim"),  # Eletrobras
            (1244, "sim"),  # Correios
            (1368, "sim"),  # BNB
            (1653, "sim"),  # Novo Marco do Saneamento (abre para privatização) [Senado]
            (1508, "sim"),  # Novo Modelo do Mercado de Energia Elétrica [Senado]
        ],
    },
    {
        "slug": "austeridade-fiscal",
        "titulo": "Austeridade fiscal",
        "titulo_en": "Fiscal austerity",
        "descricao": "Redução de gastos públicos e controle rigoroso do orçamento federal.",
        "descricao_en": "Reduction of public spending and strict control of the federal budget.",
        "tema": "economia",
        "ordem": 2,
        "proposicoes": [
            (1288, "sim"),  # Arcabouço fiscal
            (1482, "sim"),  # Corte benefícios
            (1269, "sim"),  # Precatórios
        ],
    },
    {
        "slug": "reforma-tributaria",
        "titulo": "Reforma tributária",
        "titulo_en": "Tax reform",
        "descricao": (
            "Simplificação do sistema de impostos e mudanças na tributação de renda e consumo."
        ),
        "descricao_en": (
            "Simplification of the tax system and changes to income and consumption taxation."
        ),
        "tema": "tributacao",
        "ordem": 3,
        "proposicoes": [
            (1316, "sim"),  # PLP 68
            (1430, "sim"),  # IR Justo
            (1243, "sim"),  # IR PF/PJ
            (1433, "sim"),  # Investimentos
        ],
    },
    {
        "slug": "regulacao-apostas",
        "titulo": "Regulação de apostas online",
        "titulo_en": "Online gambling regulation",
        "descricao": "Regulamentação das apostas esportivas e jogos online (bets) no Brasil.",
        "descricao_en": "Regulation of sports betting and online gambling in Brazil.",
        "tema": "economia",
        "ordem": 4,
        "proposicoes": [
            (1309, "sim"),  # Bets
        ],
    },
    {
        "slug": "incentivos-fiscais-industria",
        "titulo": "Incentivos fiscais para a indústria",
        "titulo_en": "Tax incentives for industry",
        "descricao": (
            "Benefícios tributários para setores industriais como datacenters e indústria química."
        ),
        "descricao_en": (
            "Tax benefits for industrial sectors such as data centers and the chemical industry."
        ),
        "tema": "tributacao",
        "ordem": 5,
        "proposicoes": [
            (1494, "sim"),  # Datacenter
            (1489, "sim"),  # Química
        ],
    },
    {
        "slug": "endurecimento-penal",
        "titulo": "Endurecimento penal",
        "titulo_en": "Harsher criminal penalties",
        "descricao": (
            "Aumento de penas, combate a facções criminosas e maior rigor no sistema penal."
        ),
        "descricao_en": (
            "Increased sentences, crackdown on criminal gangs, and stricter criminal justice."
        ),
        "tema": "seguranca",
        "ordem": 6,
        "proposicoes": [
            (1473, "sim"),  # Antifacções
            (1302, "sim"),  # Penas furto
            (1224, "sim"),  # Psicológico
            (1862, "sim"),  # Endurecimento da Execução Penal [Senado]
        ],
    },
    {
        "slug": "controle-armas",
        "titulo": "Controle de armas",
        "titulo_en": "Gun control",
        "descricao": "Restrição ao acesso e porte de armas de fogo pela população civil.",
        "descricao_en": "Restrictions on civilian access to and carrying of firearms.",
        "tema": "seguranca",
        "ordem": 7,
        "proposicoes": [
            (584, "sim"),  # Armas
            (1285, "sim"),  # Agentes
            (1632, "sim"),  # Anulação do Decreto das Armas de Bolsonaro [Senado]
        ],
    },
    {
        "slug": "combate-corrupcao",
        "titulo": "Combate à corrupção",
        "titulo_en": "Anti-corruption measures",
        "descricao": (
            "Medidas para aumentar a transparência e punir crimes contra a administração pública."
        ),
        "descricao_en": (
            "Measures to increase transparency and punish crimes against public administration."
        ),
        "tema": "corrupcao",
        "ordem": 8,
        "proposicoes": [
            (1225, "sim"),  # Inelegibilidade
            (1144, "sim"),  # Gastos campanha
            (1395, "sim"),  # Fundo MP
        ],
    },
    {
        "slug": "protecao-ambiental",
        "titulo": "Proteção ambiental rigorosa",
        "titulo_en": "Strict environmental protection",
        "descricao": "Regras mais rígidas de licenciamento ambiental e proteção de biomas.",
        "descricao_en": "Stricter environmental licensing rules and biome protection.",
        "tema": "meio-ambiente",
        "ordem": 9,
        "proposicoes": [
            (1192, "nao"),  # Licenciamento (flexibiliza, então contra = proteção)
            (1477, "nao"),  # Simplificado (flexibiliza)
            (1416, "sim"),  # Pantanal
            (1655, "sim"),  # Nova Lei de Segurança de Barragens [Senado]
            (1611, "nao"),  # Redução de Áreas Protegidas no Pará (reduz proteção) [Senado]
            (1871, "nao"),  # Marco Temporal Terras Indígenas (restringe proteção) [Senado]
        ],
    },
    {
        "slug": "compromissos-climaticos",
        "titulo": "Compromissos climáticos",
        "titulo_en": "Climate commitments",
        "descricao": (
            "Adesão a metas internacionais de redução de emissões e políticas de sustentabilidade."
        ),
        "descricao_en": (
            "Adherence to international emission reduction targets and sustainability policies."
        ),
        "tema": "meio-ambiente",
        "ordem": 10,
        "proposicoes": [
            (1427, "sim"),  # COP30
            (1449, "sim"),  # Sustentável
            (1456, "sim"),  # Educação Clima
            (175, "sim"),  # Animais
            (1837, "sim"),  # Marco da Energia Eólica no Mar [Senado]
            (1892, "sim"),  # Mercado de Carbono Brasileiro [Senado]
            (1882, "sim"),  # Marco Legal do Hidrogênio Verde [Senado]
        ],
    },
    {
        "slug": "igualdade-genero-politica",
        "titulo": "Igualdade de gênero na política",
        "titulo_en": "Gender equality in politics",
        "descricao": "Cotas e medidas para aumentar a participação feminina na política.",
        "descricao_en": "Quotas and measures to increase women's participation in politics.",
        "tema": "direitos-humanos",
        "ordem": 11,
        "proposicoes": [
            (1268, "sim"),  # Cotas
            (1852, "sim"),  # Programa Emprega + Mulheres e Jovens [Senado]
            (1884, "sim"),  # PEC do Financiamento Racial nas Eleições [Senado]
            (1798, "sim"),  # Cota de Recursos para Candidaturas Negras e Femininas [Senado]
        ],
    },
    {
        "slug": "protecao-infancia",
        "titulo": "Proteção à infância",
        "titulo_en": "Child protection",
        "descricao": (
            "Políticas públicas para a primeira infância, autismo e direitos das crianças."
        ),
        "descricao_en": ("Public policies for early childhood, autism, and children's rights."),
        "tema": "direitos-humanos",
        "ordem": 12,
        "proposicoes": [
            (1434, "sim"),  # 1ª Infância
            (1298, "sim"),  # Autismo
            (1463, "nao"),  # CONANDA (enfraquece, então contra = proteção)
            (1897, "sim"),  # Lei do Celular nas Escolas [Senado]
            (1819, "sim"),  # Saúde Mental nas Escolas [Senado]
        ],
    },
    {
        "slug": "criminalizacao-violencia-digital",
        "titulo": "Criminalização da violência digital",
        "titulo_en": "Criminalization of digital violence",
        "descricao": "Tipificação de crimes digitais como estupro virtual e golpes online.",
        "descricao_en": (
            "Criminalization of digital offenses such as virtual rape and online scams."
        ),
        "tema": "seguranca",
        "ordem": 13,
        "proposicoes": [
            (1297, "sim"),  # Estupro Virtual
            (1468, "sim"),  # Falso Advogado
            (1720, "sim"),  # Lei das Fake News [Senado]
            (1765, "sim"),  # Penas Mais Duras para Crimes Digitais [Senado]
        ],
    },
    {
        "slug": "protecao-trabalhadores-apps",
        "titulo": "Direitos dos trabalhadores vulneráveis",
        "titulo_en": "Vulnerable workers' rights",
        "descricao": (
            "Proteção trabalhista para categorias vulneráveis:"
            " entregadores de apps, gestantes e trabalhadores informais."
        ),
        "descricao_en": (
            "Labor protections for vulnerable categories:"
            " app delivery workers, pregnant women, and informal workers."
        ),
        "tema": "trabalho",
        "ordem": 14,
        "proposicoes": [
            (1419, "sim"),  # Alimentação
            (1471, "sim"),  # Mototáxi
            (1240, "sim"),  # Gestantes
            (1851, "sim"),  # Novas Regras do Vale-Alimentação [Senado]
            (1175, "sim"),  # Programa Emergencial de Suporte a Empregos [Senado]
            (1852, "sim"),  # Programa Emprega + Mulheres e Jovens [Senado]
        ],
    },
    {
        "slug": "valorizacao-servico-publico",
        "titulo": "Valorização do serviço público",
        "titulo_en": "Public service appreciation",
        "descricao": (
            "Melhores condições para servidores públicos, incluindo carreiras e remuneração."
        ),
        "descricao_en": (
            "Better conditions for civil servants, including career paths and compensation."
        ),
        "tema": "trabalho",
        "ordem": 15,
        "proposicoes": [
            (1442, "sim"),  # Carreiras Judiciário
            (1443, "sim"),  # Carreiras Judiciário 2
            (1360, "sim"),  # Servidores
            (1417, "sim"),  # TCU
            (1626, "sim"),  # Salários dos Servidores dos Ex-Territórios [Senado]
        ],
    },
    {
        "slug": "reforma-previdencia",
        "titulo": "Reforma da previdência",
        "titulo_en": "Pension reform",
        "descricao": "Mudanças nas regras de aposentadoria e contribuição previdenciária.",
        "descricao_en": "Changes to retirement rules and social security contributions.",
        "tema": "previdencia",
        "ordem": 16,
        "proposicoes": [
            (919, "sim"),  # Aposentadoria
            (898, "sim"),  # Contribuição
            (503, "sim"),  # Benefícios
            (1119, "sim"),  # Reforma da Previdência 2019 [Senado: 891 votos]
            (1506, "sim"),  # Reforma da Previdência 2003 [Senado: 729 votos]
            (1503, "sim"),  # PEC Paralela da Previdência 2003 [Senado: 972 votos]
        ],
    },
    {
        "slug": "fortalecimento-sus",
        "titulo": "Fortalecimento do SUS",
        "titulo_en": "Strengthening public healthcare (SUS)",
        "descricao": (
            "Investimento no Sistema Único de Saúde, acesso a especialistas e medicamentos."
        ),
        "descricao_en": (
            "Investment in the public healthcare system (SUS),"
            " access to specialists and medications."
        ),
        "tema": "saude",
        "ordem": 17,
        "proposicoes": [
            (1426, "sim"),  # Especialistas
            (1218, "sim"),  # Medicamentos
            (1204, "sim"),  # Indígena
            (1420, "sim"),  # Educação e Saúde Fora do Teto de Gastos [Senado]
            (1500, "sim"),  # Regulação do Preço de Medicamentos [Senado]
        ],
    },
    {
        "slug": "quebra-patentes",
        "titulo": "Quebra de patentes de medicamentos",
        "titulo_en": "Compulsory licensing of drug patents",
        "descricao": "Licenciamento compulsório de patentes para baratear medicamentos essenciais.",
        "descricao_en": (
            "Compulsory patent licensing to make essential medications more affordable."
        ),
        "tema": "saude",
        "ordem": 18,
        "proposicoes": [
            (1487, "sim"),  # Remédio Barato
            (1226, "sim"),  # Quebra de Patentes em Emergências de Saúde [Senado]
        ],
    },
    {
        "slug": "investimento-educacao",
        "titulo": "Investimento em educação",
        "titulo_en": "Investment in education",
        "descricao": (
            "Ampliação de programas educacionais, formação profissional e alimentação escolar."
        ),
        "descricao_en": (
            "Expansion of educational programs, vocational training, and school meals."
        ),
        "tema": "educacao",
        "ordem": 19,
        "proposicoes": [
            (713, "sim"),  # PRONATEC
            (1300, "sim"),  # Semana Cultural
            (862, "sim"),  # Política escolar
            (623, "sim"),  # Merenda
            (1541, "sim"),  # Criação do FUNDEB [Senado: 243 votos]
            (1050, "sim"),  # Reforma do FIES [Senado]
            (1784, "sim"),  # Renovação das Cotas em Universidades [Senado]
        ],
    },
    {
        "slug": "incentivo-cultura",
        "titulo": "Incentivo à cultura",
        "titulo_en": "Cultural promotion",
        "descricao": (
            "Fomento a atividades culturais, vale-cultura"
            " e apoio a instituições como a Caixa Cultural."
        ),
        "descricao_en": (
            "Support for cultural activities, culture vouchers,"
            " and backing for institutions like Caixa Cultural."
        ),
        "tema": "cultura",
        "ordem": 20,
        "proposicoes": [
            (649, "sim"),  # Vale-Cultura
            (1354, "sim"),  # Fomento
            (1421, "sim"),  # Caixa Cultural
            (1814, "sim"),  # Lei Aldir Blanc de Apoio Emergencial à Cultura [Senado]
            (1823, "sim"),  # Política Nacional Aldir Blanc [Senado]
            (1510, "sim"),  # Plano Nacional de Cultura [Senado]
        ],
    },
]


async def seed():
    async with async_session() as db:
        for pos_data in POSICOES:
            # Upsert posição
            stmt = (
                insert(Posicao)
                .values(
                    slug=pos_data["slug"],
                    titulo=pos_data["titulo"],
                    titulo_en=pos_data.get("titulo_en"),
                    descricao=pos_data["descricao"],
                    descricao_en=pos_data.get("descricao_en"),
                    tema=pos_data["tema"],
                    ordem=pos_data["ordem"],
                    ativo=True,
                )
                .on_conflict_do_update(
                    index_elements=["slug"],
                    set_={
                        "titulo": pos_data["titulo"],
                        "titulo_en": pos_data.get("titulo_en"),
                        "descricao": pos_data["descricao"],
                        "descricao_en": pos_data.get("descricao_en"),
                        "tema": pos_data["tema"],
                        "ordem": pos_data["ordem"],
                        "ativo": True,
                    },
                )
                .returning(Posicao.id)
            )
            result = await db.execute(stmt)
            posicao_id = result.scalar_one()

            # Upsert proposições mapeadas
            for prop_id, direcao in pos_data["proposicoes"]:
                prop_stmt = (
                    insert(PosicaoProposicao)
                    .values(
                        posicao_id=posicao_id,
                        proposicao_id=prop_id,
                        direcao=direcao.upper(),
                    )
                    .on_conflict_do_update(
                        constraint="uq_posicao_proposicao",
                        set_={"direcao": direcao.upper()},
                    )
                )
                await db.execute(prop_stmt)

        await db.commit()
        print(f"Seeded {len(POSICOES)} posições com sucesso!")

        # Verify
        result = await db.execute(select(Posicao).order_by(Posicao.ordem))
        for p in result.scalars().unique().all():
            n = len(p.proposicoes_rel)
            print(f"  {p.ordem:2d}. {p.titulo} ({p.tema}) — {n} proposições")


if __name__ == "__main__":
    asyncio.run(seed())
