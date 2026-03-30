import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposicao import Proposicao
from app.models.votacao import Votacao
from app.utils import urls_por_casa

# 25 proposições âncora — sempre apresentadas primeiro a novos usuários.
# Selecionadas manualmente por relevância pública e cobertura de votações nominais.
ANCHOR_IDS: set[int] = {
    173,  # PEC 18/2025 — PEC da Segurança Pública
    174,  # PL 6139/2023 — Marco do Crédito à Exportação
    1192,  # PL 2159/2021 — Lei do Licenciamento Ambiental
    1285,  # PL 4015/2023 — Proteção a Agentes Públicos
    1288,  # PLP 93/2023 — Novo Arcabouço Fiscal
    1297,  # PL 1891/2023 — Estupro Virtual
    1298,  # PL 3050/2023 — Inclusão Escolar do Autismo
    1300,  # PL 1825/2023 — Semana Cultural nas Escolas
    1309,  # PL 3626/2023 — Lei das Apostas (Bets)
    1316,  # PLP 68/2024 — Reforma Tributária do Consumo
    1336,  # PLP 121/2024 — Renegociação das Dívidas dos Estados
    1416,  # PL 4392/2025 — Estatuto do Pantanal
    1426,  # MPV 1301/2025 — Programa Agora Tem Especialistas
    1427,  # PL 358/2025 — Regras da COP30
    1430,  # PL 1087/2025 — IR Mais Justo
    1433,  # MPV 1303/2025 — Tributação de Investimentos
    1434,  # PL 1924/2025 — Lei da Primeira Infância
    1449,  # PL 420/2025 — Infraestrutura Sustentável
    1456,  # PL 2947/2025 — Educação Climática nas Empresas
    1468,  # PL 4709/2025 — Golpe do Falso Advogado
    1473,  # PL 5582/2025 — Lei Antifacções
    1477,  # MPV 1308/2025 — Licenciamento Simplificado
    1482,  # PLP 128/2025 — Corte de Benefícios Fiscais
    1487,  # PL 68/2026 — Remédio Mais Barato (Quebra de Patente)
    1494,  # PL 278/2026 — Lei do Datacenter
}


def _serialize(p: Proposicao, casas: list[str] | None = None, lang: str = "pt-BR") -> dict:
    urls = urls_por_casa(p.id_externo, p.tipo, p.numero, p.ano)
    casas_list = [{"casa": c, "url": urls.get(c)} for c in (casas or [])]
    resumo = p.resumo_cidadao
    descricao = p.descricao_detalhada
    if lang == "en":
        resumo = p.resumo_cidadao_en or resumo
        descricao = p.descricao_detalhada_en or descricao
    return {
        "proposicao_id": p.id,
        "tipo": p.tipo,
        "numero": p.numero,
        "ano": p.ano,
        "ementa": p.ementa,
        "resumo": resumo,
        "descricao_detalhada": descricao,
        "tema": p.tema or "geral",
        "casas": casas_list,
    }


async def montar_questionario(
    db: AsyncSession,
    n_items: int = 50,
    exclude_ids: set[int] | None = None,
    lang: str = "pt-BR",
) -> list[dict]:
    """Select proposições for the questionnaire.

    Phase 1: all anchor proposições (shuffled).
    Phase 2: round-robin by tema, ordered by relevancia_score DESC.
    """
    substantive_types = ["PL", "PEC", "MPV", "PLP", "PDL", "MIP"]

    # Only select proposições that have at least one votação (so they can participate in matching)
    props_with_votacao = (
        select(Votacao.proposicao_id).where(Votacao.proposicao_id.is_not(None)).distinct()
    )

    query = (
        select(Proposicao)
        .where(Proposicao.resumo_cidadao.is_not(None))
        .where(Proposicao.relevancia_score.is_not(None))
        .where(Proposicao.tipo.in_(substantive_types))
        .where(Proposicao.id.in_(props_with_votacao))
        .order_by(Proposicao.relevancia_score.desc())
    )
    result = await db.execute(query)
    all_props = result.scalars().all()

    # Remove already-answered proposições
    if exclude_ids:
        all_props = [p for p in all_props if p.id not in exclude_ids]

    # Build mapping of proposição → list of casas that voted on it
    casas_query = (
        select(Votacao.proposicao_id, func.array_agg(func.distinct(Votacao.casa)))
        .where(Votacao.proposicao_id.is_not(None))
        .group_by(Votacao.proposicao_id)
    )
    casas_result = await db.execute(casas_query)
    casas_by_prop: dict[int, list[str]] = {
        row[0]: sorted(c.lower() for c in row[1]) for row in casas_result.all()
    }

    # Identify bicameral proposições (voted in both Câmara and Senado)
    bicameral_ids = {pid for pid, casas in casas_by_prop.items() if len(casas) > 1}

    # Phase 1: anchors first (shuffled, bicameral anchors before the rest)
    anchors_bicameral = [p for p in all_props if p.id in ANCHOR_IDS and p.id in bicameral_ids]
    anchors_other = [p for p in all_props if p.id in ANCHOR_IDS and p.id not in bicameral_ids]
    random.shuffle(anchors_bicameral)
    random.shuffle(anchors_other)
    anchors = anchors_bicameral + anchors_other

    selected: list = list(anchors)
    selected_ids: set[int] = {p.id for p in anchors}

    if len(selected) >= n_items:
        return [_serialize(p, casas_by_prop.get(p.id), lang=lang) for p in selected[:n_items]]

    # Phase 2: round-robin by tema
    # Within each tema, bicameral proposições come first (sorted by relevancia_score DESC),
    # then single-house proposições. This strongly prioritizes bicameral coverage.
    by_topic: dict[str, list] = {}
    for p in all_props:
        if p.id in selected_ids:
            continue
        topic = p.tema or "geral"
        by_topic.setdefault(topic, []).append(p)

    # Sort each topic: bicameral first, then by relevancia_score DESC (already ordered from query)
    for topic in by_topic:
        by_topic[topic].sort(
            key=lambda p: (0 if p.id in bicameral_ids else 1, -(p.relevancia_score or 0))
        )

    topics = sorted(by_topic.keys())
    round_idx = 0
    while len(selected) < n_items:
        added_any = False
        for topic in topics:
            if len(selected) >= n_items:
                break
            pool = by_topic[topic]
            if round_idx < len(pool):
                selected.append(pool[round_idx])
                added_any = True
        round_idx += 1
        if not added_any:
            break

    return [_serialize(p, casas_by_prop.get(p.id), lang=lang) for p in selected]
