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
        "descricao": (
            "Venda de empresas públicas para a iniciativa privada, como Eletrobras, Correios e BNB."
        ),
        "tema": "economia",
        "ordem": 1,
        "proposicoes": [
            (1195, "sim"),  # Eletrobras
            (1244, "sim"),  # Correios
            (1368, "sim"),  # BNB
        ],
    },
    {
        "slug": "austeridade-fiscal",
        "titulo": "Austeridade fiscal",
        "descricao": "Redução de gastos públicos e controle rigoroso do orçamento federal.",
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
        "descricao": (
            "Simplificação do sistema de impostos e mudanças na tributação de renda e consumo."
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
        "descricao": "Regulamentação das apostas esportivas e jogos online (bets) no Brasil.",
        "tema": "economia",
        "ordem": 4,
        "proposicoes": [
            (1309, "sim"),  # Bets
        ],
    },
    {
        "slug": "incentivos-fiscais-industria",
        "titulo": "Incentivos fiscais para a indústria",
        "descricao": (
            "Benefícios tributários para setores industriais como datacenters e indústria química."
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
        "descricao": (
            "Aumento de penas, combate a facções criminosas e maior rigor no sistema penal."
        ),
        "tema": "seguranca",
        "ordem": 6,
        "proposicoes": [
            (1473, "sim"),  # Antifacções
            (1302, "sim"),  # Penas furto
            (1224, "sim"),  # Psicológico
        ],
    },
    {
        "slug": "controle-armas",
        "titulo": "Controle de armas",
        "descricao": "Restrição ao acesso e porte de armas de fogo pela população civil.",
        "tema": "seguranca",
        "ordem": 7,
        "proposicoes": [
            (584, "sim"),  # Armas
            (1285, "sim"),  # Agentes
        ],
    },
    {
        "slug": "combate-corrupcao",
        "titulo": "Combate à corrupção",
        "descricao": (
            "Medidas para aumentar a transparência e punir crimes contra a administração pública."
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
        "descricao": "Regras mais rígidas de licenciamento ambiental e proteção de biomas.",
        "tema": "meio-ambiente",
        "ordem": 9,
        "proposicoes": [
            (1192, "nao"),  # Licenciamento (flexibiliza, então contra = proteção)
            (1477, "nao"),  # Simplificado (flexibiliza)
            (1416, "sim"),  # Pantanal
        ],
    },
    {
        "slug": "compromissos-climaticos",
        "titulo": "Compromissos climáticos",
        "descricao": (
            "Adesão a metas internacionais de redução de emissões e políticas de sustentabilidade."
        ),
        "tema": "meio-ambiente",
        "ordem": 10,
        "proposicoes": [
            (1427, "sim"),  # COP30
            (1449, "sim"),  # Sustentável
            (1456, "sim"),  # Educação Clima
            (175, "sim"),  # Animais
        ],
    },
    {
        "slug": "igualdade-genero-politica",
        "titulo": "Igualdade de gênero na política",
        "descricao": "Cotas e medidas para aumentar a participação feminina na política.",
        "tema": "direitos-humanos",
        "ordem": 11,
        "proposicoes": [
            (1268, "sim"),  # Cotas
        ],
    },
    {
        "slug": "protecao-infancia",
        "titulo": "Proteção à infância",
        "descricao": (
            "Políticas públicas para a primeira infância, autismo e direitos das crianças."
        ),
        "tema": "direitos-humanos",
        "ordem": 12,
        "proposicoes": [
            (1434, "sim"),  # 1ª Infância
            (1298, "sim"),  # Autismo
            (1463, "nao"),  # CONANDA (enfraquece, então contra = proteção)
        ],
    },
    {
        "slug": "criminalizacao-violencia-digital",
        "titulo": "Criminalização da violência digital",
        "descricao": "Tipificação de crimes digitais como estupro virtual e golpes online.",
        "tema": "seguranca",
        "ordem": 13,
        "proposicoes": [
            (1297, "sim"),  # Estupro Virtual
            (1468, "sim"),  # Falso Advogado
        ],
    },
    {
        "slug": "protecao-trabalhadores-apps",
        "titulo": "Direitos dos trabalhadores vulneráveis",
        "descricao": (
            "Proteção trabalhista para categorias vulneráveis:"
            " entregadores de apps, gestantes e trabalhadores informais."
        ),
        "tema": "trabalho",
        "ordem": 14,
        "proposicoes": [
            (1419, "sim"),  # Alimentação
            (1471, "sim"),  # Mototáxi
            (1240, "sim"),  # Gestantes
        ],
    },
    {
        "slug": "valorizacao-servico-publico",
        "titulo": "Valorização do serviço público",
        "descricao": (
            "Melhores condições para servidores públicos, incluindo carreiras e remuneração."
        ),
        "tema": "trabalho",
        "ordem": 15,
        "proposicoes": [
            (1442, "sim"),  # Carreiras Judiciário
            (1443, "sim"),  # Carreiras Judiciário 2
            (1360, "sim"),  # Servidores
            (1417, "sim"),  # TCU
        ],
    },
    {
        "slug": "reforma-previdencia",
        "titulo": "Reforma da previdência",
        "descricao": "Mudanças nas regras de aposentadoria e contribuição previdenciária.",
        "tema": "previdencia",
        "ordem": 16,
        "proposicoes": [
            (919, "sim"),  # Aposentadoria
            (898, "sim"),  # Contribuição
            (503, "sim"),  # Benefícios
        ],
    },
    {
        "slug": "fortalecimento-sus",
        "titulo": "Fortalecimento do SUS",
        "descricao": (
            "Investimento no Sistema Único de Saúde, acesso a especialistas e medicamentos."
        ),
        "tema": "saude",
        "ordem": 17,
        "proposicoes": [
            (1426, "sim"),  # Especialistas
            (1218, "sim"),  # Medicamentos
            (1204, "sim"),  # Indígena
        ],
    },
    {
        "slug": "quebra-patentes",
        "titulo": "Quebra de patentes de medicamentos",
        "descricao": "Licenciamento compulsório de patentes para baratear medicamentos essenciais.",
        "tema": "saude",
        "ordem": 18,
        "proposicoes": [
            (1487, "sim"),  # Remédio Barato
        ],
    },
    {
        "slug": "investimento-educacao",
        "titulo": "Investimento em educação",
        "descricao": (
            "Ampliação de programas educacionais, formação profissional e alimentação escolar."
        ),
        "tema": "educacao",
        "ordem": 19,
        "proposicoes": [
            (713, "sim"),  # PRONATEC
            (1300, "sim"),  # Semana Cultural
            (862, "sim"),  # Política escolar
            (623, "sim"),  # Merenda
        ],
    },
    {
        "slug": "incentivo-cultura",
        "titulo": "Incentivo à cultura",
        "descricao": (
            "Fomento a atividades culturais, vale-cultura"
            " e apoio a instituições como a Caixa Cultural."
        ),
        "tema": "cultura",
        "ordem": 20,
        "proposicoes": [
            (649, "sim"),  # Vale-Cultura
            (1354, "sim"),  # Fomento
            (1421, "sim"),  # Caixa Cultural
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
                    descricao=pos_data["descricao"],
                    tema=pos_data["tema"],
                    ordem=pos_data["ordem"],
                    ativo=True,
                )
                .on_conflict_do_update(
                    index_elements=["slug"],
                    set_={
                        "titulo": pos_data["titulo"],
                        "descricao": pos_data["descricao"],
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
        for p in result.scalars().all():
            n = len(p.proposicoes_rel)
            print(f"  {p.ordem:2d}. {p.titulo} ({p.tema}) — {n} proposições")


if __name__ == "__main__":
    asyncio.run(seed())
