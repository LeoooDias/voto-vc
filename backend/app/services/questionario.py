import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposicao import Proposicao


async def montar_questionario(
    db: AsyncSession,
    n_items: int = 25,
) -> list[dict]:
    """Select proposições for the questionnaire.

    Fetches all available proposições, then selects n_items ensuring
    topic diversity: picks round-robin from each topic before filling
    remaining slots with the most divisive ones.
    """
    substantive_types = ["PL", "PEC", "MPV", "PLP", "PDL", "MIP"]
    query = (
        select(Proposicao)
        .where(Proposicao.resumo_cidadao.is_not(None))
        .where(Proposicao.relevancia_score.is_not(None))
        .where(Proposicao.tipo.in_(substantive_types))
        .order_by(Proposicao.relevancia_score.desc())
    )
    result = await db.execute(query)
    all_props = result.scalars().all()

    # Group by topic (from DB column, fallback to "geral")
    by_topic: dict[str, list] = {}
    for p in all_props:
        topic = p.tema or "geral"
        by_topic.setdefault(topic, []).append(p)

    # Shuffle within each topic
    for props in by_topic.values():
        random.shuffle(props)

    # Round-robin: pick one from each topic until we have enough
    selected: list = []
    selected_ids: set[int] = set()
    topics = list(by_topic.keys())
    random.shuffle(topics)

    # Phase 1: round-robin across topics (ensures diversity)
    round_idx = 0
    while len(selected) < n_items:
        added_any = False
        for topic in topics:
            if len(selected) >= n_items:
                break
            pool = by_topic[topic]
            if round_idx < len(pool):
                p = pool[round_idx]
                if p.id not in selected_ids:
                    selected.append(p)
                    selected_ids.add(p.id)
                    added_any = True
        round_idx += 1
        if not added_any:
            break

    # Phase 2: fill remaining slots with most divisive not yet selected
    if len(selected) < n_items:
        for p in all_props:
            if len(selected) >= n_items:
                break
            if p.id not in selected_ids:
                selected.append(p)
                selected_ids.add(p.id)

    # Shuffle final order so user doesn't see topic clustering
    random.shuffle(selected)

    return [
        {
            "proposicao_id": p.id,
            "tipo": p.tipo,
            "numero": p.numero,
            "ano": p.ano,
            "resumo": p.resumo_cidadao,
            "descricao_detalhada": p.descricao_detalhada,
            "tema": p.tema or "geral",
            "url_camara": f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={p.id_externo.replace('camara_prop_', '')}" if p.id_externo else None,
        }
        for p in selected
    ]
