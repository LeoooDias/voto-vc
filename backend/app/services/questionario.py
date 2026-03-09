from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposicao import Proposicao


async def montar_questionario(
    db: AsyncSession,
    n_items: int = 25,
) -> list[dict]:
    """Select proposições for the questionnaire.

    Prioritizes by: relevancia_score (divisive votes), topic diversity, recency.
    """
    query = (
        select(Proposicao)
        .where(Proposicao.resumo_cidadao.is_not(None))
        .where(Proposicao.relevancia_score.is_not(None))
        .order_by(Proposicao.relevancia_score.desc())
        .limit(n_items)
    )
    result = await db.execute(query)
    proposicoes = result.scalars().all()

    return [
        {
            "proposicao_id": p.id,
            "tipo": p.tipo,
            "numero": p.numero,
            "ano": p.ano,
            "resumo": p.resumo_cidadao,
            "ementa_simplificada": p.ementa_simplificada,
        }
        for p in proposicoes
    ]
