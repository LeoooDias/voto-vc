from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.base import Casa, TipoVoto
from app.models.parlamentar import Parlamentar
from app.models.partido import Partido
from app.models.votacao import Votacao, VotoParlamentar


def _score_parlamentar(
    user_votes: dict,
    prop_votes: dict[int, list[TipoVoto]],
    min_compared: int,
) -> tuple[float, int] | None:
    """Score a single parlamentar. Returns (normalized_score, props_compared) or None."""
    total_score = 0.0
    total_weight = 0.0
    props_compared = 0

    for prop_id, votos_for_prop in prop_votes.items():
        if prop_id not in user_votes:
            continue
        user_voto, peso = user_votes[prop_id]
        if user_voto.value == "pular":
            continue

        parl_vote = None
        for v in votos_for_prop:
            if v in (TipoVoto.SIM, TipoVoto.NAO):
                parl_vote = v
                break
        if parl_vote is None:
            continue

        total_weight += peso
        props_compared += 1

        if (
            user_voto.value == "sim" and parl_vote == TipoVoto.SIM
        ) or (
            user_voto.value == "nao" and parl_vote == TipoVoto.NAO
        ):
            total_score += peso
        elif (
            user_voto.value == "sim" and parl_vote == TipoVoto.NAO
        ) or (
            user_voto.value == "nao" and parl_vote == TipoVoto.SIM
        ):
            total_score -= peso

    if total_weight > 0 and props_compared >= min_compared:
        normalized = ((total_score / total_weight) + 1) * 50
        return normalized, props_compared
    return None


async def _load_votes(
    db: AsyncSession,
    proposicao_ids: list[int],
    valid_parl_ids: set[int],
) -> dict[int, dict[int, list[TipoVoto]]]:
    """Load votes grouped by parlamentar -> proposicao -> [TipoVoto]."""
    votacao_query = select(Votacao).where(
        Votacao.proposicao_id.in_(proposicao_ids)
    )
    votacao_result = await db.execute(votacao_query)
    votacoes = votacao_result.scalars().all()
    votacao_ids = [v.id for v in votacoes]
    votacao_to_prop = {v.id: v.proposicao_id for v in votacoes}

    if not votacao_ids:
        return {}

    votos_query = select(VotoParlamentar).where(
        VotoParlamentar.votacao_id.in_(votacao_ids)
    )
    votos_result = await db.execute(votos_query)
    votos = votos_result.scalars().all()

    parlamentar_votos: dict[int, dict[int, list[TipoVoto]]] = {}
    for vp in votos:
        if vp.parlamentar_id not in valid_parl_ids:
            continue
        prop_id = votacao_to_prop.get(vp.votacao_id)
        if prop_id:
            parlamentar_votos.setdefault(vp.parlamentar_id, {}).setdefault(
                prop_id, []
            ).append(vp.voto)

    return parlamentar_votos


async def ranking_parlamentares(
    db: AsyncSession,
    respostas: list,
    casa: str | None = None,
    uf: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Calculate alignment scores between user responses and all parlamentares."""
    user_votes = {r.proposicao_id: (r.voto, r.peso) for r in respostas}
    proposicao_ids = list(user_votes.keys())
    if not proposicao_ids:
        return []

    parl_filter_query = select(
        Parlamentar.id, Parlamentar.partido_id
    ).select_from(Parlamentar)
    if casa:
        parl_filter_query = parl_filter_query.where(
            Parlamentar.casa == Casa(casa)
        )
    if uf:
        parl_filter_query = parl_filter_query.where(
            Parlamentar.uf == uf.upper()
        )
    parl_filter_result = await db.execute(parl_filter_query)
    parl_rows = parl_filter_result.all()
    valid_parl_ids = {row[0] for row in parl_rows}

    if not valid_parl_ids:
        return []

    parlamentar_votos = await _load_votes(db, proposicao_ids, valid_parl_ids)
    if not parlamentar_votos:
        return []

    min_compared = max(3, len(user_votes) // 4)

    scores: list[tuple[int, float, int]] = []
    for parl_id, prop_votes in parlamentar_votos.items():
        result = _score_parlamentar(user_votes, prop_votes, min_compared)
        if result:
            scores.append((parl_id, result[0], result[1]))

    scores.sort(key=lambda x: x[1], reverse=True)

    top_ids = [s[0] for s in scores[:limit]]
    if not top_ids:
        return []

    parl_query = (
        select(Parlamentar)
        .options(joinedload(Parlamentar.partido))
        .where(Parlamentar.id.in_(top_ids))
    )
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
                "sexo": p.sexo,
                "foto_url": p.foto_url,
                "score": round(score, 1),
                "votos_comparados": n_votos,
            }
        )

    return results


async def ranking_partidos(
    db: AsyncSession,
    respostas: list,
    casa: str | None = None,
    uf: str | None = None,
) -> list[dict]:
    """Calculate party alignment by averaging individual parlamentar scores."""
    user_votes = {r.proposicao_id: (r.voto, r.peso) for r in respostas}
    proposicao_ids = list(user_votes.keys())
    if not proposicao_ids:
        return []

    # Load parlamentares with partido info
    parl_filter_query = select(
        Parlamentar.id, Parlamentar.partido_id
    ).select_from(Parlamentar)
    if casa:
        parl_filter_query = parl_filter_query.where(
            Parlamentar.casa == Casa(casa)
        )
    if uf:
        parl_filter_query = parl_filter_query.where(
            Parlamentar.uf == uf.upper()
        )
    parl_filter_result = await db.execute(parl_filter_query)
    parl_rows = parl_filter_result.all()
    valid_parl_ids = {row[0] for row in parl_rows}
    parl_to_partido = {row[0]: row[1] for row in parl_rows if row[1]}

    if not valid_parl_ids:
        return []

    parlamentar_votos = await _load_votes(db, proposicao_ids, valid_parl_ids)
    if not parlamentar_votos:
        return []

    min_compared = max(3, len(user_votes) // 4)

    # Aggregate scores by partido
    partido_scores: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for parl_id, prop_votes in parlamentar_votos.items():
        partido_id = parl_to_partido.get(parl_id)
        if not partido_id:
            continue
        result = _score_parlamentar(user_votes, prop_votes, min_compared)
        if result:
            partido_scores[partido_id].append(result)

    if not partido_scores:
        return []

    # Average score per partido
    partido_avg: list[tuple[int, float, int]] = []
    for partido_id, individual_scores in partido_scores.items():
        avg_score = sum(s[0] for s in individual_scores) / len(individual_scores)
        total_parlamentares = len(individual_scores)
        partido_avg.append((partido_id, avg_score, total_parlamentares))

    partido_avg.sort(key=lambda x: x[1], reverse=True)

    # Fetch partido details
    partido_ids = [p[0] for p in partido_avg]
    partido_query = select(Partido).where(Partido.id.in_(partido_ids))
    partido_result = await db.execute(partido_query)
    partidos = {p.id: p for p in partido_result.scalars().all()}

    results = []
    for partido_id, score, n_parlamentares in partido_avg:
        p = partidos.get(partido_id)
        if not p:
            continue
        results.append(
            {
                "partido_id": p.id,
                "sigla": p.sigla,
                "nome": p.nome,
                "score": round(score, 1),
                "parlamentares_comparados": n_parlamentares,
            }
        )

    return results
