from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.base import Casa, TipoVoto
from app.models.parlamentar import Parlamentar
from app.models.votacao import VotoParlamentar, Votacao


async def ranking_parlamentares(
    db: AsyncSession,
    respostas: list,
    casa: str | None = None,
    uf: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Calculate alignment scores between user responses and all parlamentares."""

    # Map proposicao_id -> (voto, peso) from user responses
    user_votes = {r.proposicao_id: (r.voto, r.peso) for r in respostas}
    proposicao_ids = list(user_votes.keys())

    if not proposicao_ids:
        return []

    # Get all votacoes linked to the proposicoes the user voted on
    votacao_query = select(Votacao).where(Votacao.proposicao_id.in_(proposicao_ids))
    votacao_result = await db.execute(votacao_query)
    votacoes = votacao_result.scalars().all()
    votacao_ids = [v.id for v in votacoes]
    # Map votacao_id -> proposicao_id
    votacao_to_prop = {v.id: v.proposicao_id for v in votacoes}

    if not votacao_ids:
        return []

    # Get all individual votes for those votacoes
    votos_query = select(VotoParlamentar).where(VotoParlamentar.votacao_id.in_(votacao_ids))
    votos_result = await db.execute(votos_query)
    votos = votos_result.scalars().all()

    # Group votes by parlamentar
    parlamentar_votos: dict[int, list[tuple[int, TipoVoto]]] = {}
    for vp in votos:
        prop_id = votacao_to_prop.get(vp.votacao_id)
        if prop_id:
            parlamentar_votos.setdefault(vp.parlamentar_id, []).append((prop_id, vp.voto))

    # Calculate scores
    scores: list[tuple[int, float, int]] = []
    for parl_id, voto_list in parlamentar_votos.items():
        total_score = 0.0
        total_weight = 0.0

        for prop_id, tipo_voto in voto_list:
            if prop_id not in user_votes:
                continue
            user_voto, peso = user_votes[prop_id]

            if user_voto.value == "pular":
                continue

            total_weight += peso

            # Agreement: both sim or both nao
            if (user_voto.value == "sim" and tipo_voto == TipoVoto.SIM) or (
                user_voto.value == "nao" and tipo_voto == TipoVoto.NAO
            ):
                total_score += peso
            # Disagreement
            elif (user_voto.value == "sim" and tipo_voto == TipoVoto.NAO) or (
                user_voto.value == "nao" and tipo_voto == TipoVoto.SIM
            ):
                total_score -= peso
            # Abstention/absence: neutral (0)

        if total_weight > 0:
            # Normalize to 0-100
            normalized = ((total_score / total_weight) + 1) * 50
            scores.append((parl_id, normalized, len(voto_list)))

    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)

    # Fetch parlamentar details for top results
    top_ids = [s[0] for s in scores[:limit]]
    if not top_ids:
        return []

    parl_query = (
        select(Parlamentar)
        .options(joinedload(Parlamentar.partido))
        .where(Parlamentar.id.in_(top_ids))
    )
    if casa:
        parl_query = parl_query.where(Parlamentar.casa == Casa(casa))
    if uf:
        parl_query = parl_query.where(Parlamentar.uf == uf.upper())

    parl_result = await db.execute(parl_query)
    parlamentares = {p.id: p for p in parl_result.scalars().unique().all()}

    results = []
    for parl_id, score, n_votos in scores[:limit]:
        p = parlamentares.get(parl_id)
        if not p:
            continue
        results.append(
            {
                "parlamentar_id": p.id,
                "nome": p.nome_parlamentar,
                "partido": p.partido.sigla if p.partido else None,
                "uf": p.uf,
                "casa": p.casa.value,
                "foto_url": p.foto_url,
                "score": round(score, 1),
                "votos_comparados": n_votos,
            }
        )

    return results
