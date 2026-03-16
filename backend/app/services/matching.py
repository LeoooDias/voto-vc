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

        if (user_voto.value == "sim" and parl_vote == TipoVoto.SIM) or (
            user_voto.value == "nao" and parl_vote == TipoVoto.NAO
        ):
            total_score += peso
        elif (user_voto.value == "sim" and parl_vote == TipoVoto.NAO) or (
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
    """Load votes grouped by parlamentar -> proposicao -> [TipoVoto].

    Uses raw tuples and filters parlamentar_id in SQL for performance.
    """
    # Get votacao_id -> proposicao_id mapping
    votacao_query = select(Votacao.id, Votacao.proposicao_id).where(
        Votacao.proposicao_id.in_(proposicao_ids)
    )
    votacao_result = await db.execute(votacao_query)
    votacao_rows = votacao_result.all()
    if not votacao_rows:
        return {}

    votacao_ids = [row[0] for row in votacao_rows]
    votacao_to_prop = {row[0]: row[1] for row in votacao_rows}

    # Load only needed columns, filter parlamentar_id in SQL
    # Order by votacao_id DESC so most recent vote per proposição comes first
    votos_query = (
        select(
            VotoParlamentar.parlamentar_id,
            VotoParlamentar.votacao_id,
            VotoParlamentar.voto,
        )
        .where(
            VotoParlamentar.votacao_id.in_(votacao_ids),
            VotoParlamentar.parlamentar_id.in_(valid_parl_ids),
        )
        .order_by(VotoParlamentar.votacao_id.desc())
    )
    votos_result = await db.execute(votos_query)

    parlamentar_votos: dict[int, dict[int, list[TipoVoto]]] = {}
    for parl_id, votacao_id, voto in votos_result.all():
        prop_id = votacao_to_prop.get(votacao_id)
        if prop_id:
            parlamentar_votos.setdefault(parl_id, {}).setdefault(prop_id, []).append(voto)

    return parlamentar_votos


async def _load_parlamentar_ids(
    db: AsyncSession,
    casa: str | None = None,
    uf: str | None = None,
) -> list[tuple[int, int | None]]:
    """Load parlamentar (id, partido_id) tuples with optional filters."""
    query = select(Parlamentar.id, Parlamentar.partido_id).select_from(Parlamentar)
    if casa:
        query = query.where(Parlamentar.casa == Casa(casa))
    if uf:
        query = query.where(Parlamentar.uf == uf.upper())
    result = await db.execute(query)
    return result.all()


async def comparar_parlamentar(
    db: AsyncSession,
    parlamentar_id: int,
    respostas: list,
) -> dict:
    """Compare a single parlamentar against user votes. Same logic as matching."""
    user_votes = {r.proposicao_id: (r.voto, r.peso) for r in respostas}
    proposicao_ids = [pid for pid, (v, _) in user_votes.items() if v.value != "pular"]
    if not proposicao_ids:
        return {"score": None, "concordou": 0, "discordou": 0, "total": 0}

    votos = await _load_votes(db, proposicao_ids, {parlamentar_id})
    prop_votes = votos.get(parlamentar_id, {})

    concordou = 0
    discordou = 0
    total_score = 0.0
    total_weight = 0.0

    for prop_id, votes_for_prop in prop_votes.items():
        if prop_id not in user_votes:
            continue
        user_voto, peso = user_votes[prop_id]
        if user_voto.value == "pular":
            continue
        parl_vote = None
        for v in votes_for_prop:
            if v in (TipoVoto.SIM, TipoVoto.NAO):
                parl_vote = v
                break
        if parl_vote is None:
            continue

        total_weight += peso
        match = (user_voto.value == "sim" and parl_vote == TipoVoto.SIM) or (
            user_voto.value == "nao" and parl_vote == TipoVoto.NAO
        )
        if match:
            concordou += 1
            total_score += peso
        else:
            discordou += 1
            total_score -= peso

    total = concordou + discordou
    score = round(((total_score / total_weight) + 1) * 50, 1) if total_weight > 0 else None
    return {"score": score, "concordou": concordou, "discordou": discordou, "total": total}


async def comparar_partido(
    db: AsyncSession,
    partido_id: int,
    respostas: list,
    uf: str | None = None,
) -> dict:
    """Compare a partido against user votes. Same logic as matching (avg of parlamentar scores)."""
    user_votes = {r.proposicao_id: (r.voto, r.peso) for r in respostas}
    proposicao_ids = [pid for pid, (v, _) in user_votes.items() if v.value != "pular"]
    if not proposicao_ids:
        return {
            "score": None,
            "concordou": 0,
            "discordou": 0,
            "total": 0,
            "parlamentares_comparados": 0,
        }

    # Get parlamentar IDs for this party
    from app.models.parlamentar import Parlamentar as ParlModel

    parl_query = select(ParlModel.id).where(ParlModel.partido_id == partido_id)
    if uf:
        parl_query = parl_query.where(ParlModel.uf == uf.upper())
    parl_result = await db.execute(parl_query)
    parl_ids = {r[0] for r in parl_result.all()}
    if not parl_ids:
        return {
            "score": None,
            "concordou": 0,
            "discordou": 0,
            "total": 0,
            "parlamentares_comparados": 0,
        }

    parlamentar_votos = await _load_votes(db, proposicao_ids, parl_ids)
    min_compared = max(3, len(proposicao_ids) // 4)

    scores = []
    # Aggregate concordou/discordou across all parlamentares per proposição
    prop_concordou: dict[int, int] = {}
    prop_discordou: dict[int, int] = {}

    for parl_id, prop_votes in parlamentar_votos.items():
        result = _score_parlamentar(user_votes, prop_votes, min_compared)
        if result:
            scores.append(result[0])

        # Per-proposition breakdown (for all parlamentares, regardless of threshold)
        for prop_id, votes_for_prop in prop_votes.items():
            if prop_id not in user_votes:
                continue
            user_voto, _ = user_votes[prop_id]
            if user_voto.value == "pular":
                continue
            parl_vote = None
            for v in votes_for_prop:
                if v in (TipoVoto.SIM, TipoVoto.NAO):
                    parl_vote = v
                    break
            if parl_vote is None:
                continue
            match = (user_voto.value == "sim" and parl_vote == TipoVoto.SIM) or (
                user_voto.value == "nao" and parl_vote == TipoVoto.NAO
            )
            if match:
                prop_concordou[prop_id] = prop_concordou.get(prop_id, 0) + 1
            else:
                prop_discordou[prop_id] = prop_discordou.get(prop_id, 0) + 1

    # Per proposition: majority agrees or disagrees
    concordou = 0
    discordou = 0
    all_props = set(prop_concordou.keys()) | set(prop_discordou.keys())
    for prop_id in all_props:
        c = prop_concordou.get(prop_id, 0)
        d = prop_discordou.get(prop_id, 0)
        if c >= d:
            concordou += 1
        else:
            discordou += 1

    avg_score = round(sum(scores) / len(scores), 1) if scores else None
    return {
        "score": avg_score,
        "concordou": concordou,
        "discordou": discordou,
        "total": concordou + discordou,
        "parlamentares_comparados": len(scores),
    }


async def calcular_matching(
    db: AsyncSession,
    respostas: list,
    casa: str | None = None,
    uf: str | None = None,
    limit: int = 50,
) -> dict:
    """Calculate both parlamentar and partido rankings with shared vote data."""
    user_votes = {r.proposicao_id: (r.voto, r.peso) for r in respostas}
    proposicao_ids = list(user_votes.keys())
    if not proposicao_ids:
        return {"parlamentares": [], "partidos": []}

    # Load parlamentar IDs once
    parl_rows = await _load_parlamentar_ids(db, casa, uf)
    valid_parl_ids = {row[0] for row in parl_rows}
    parl_to_partido = {row[0]: row[1] for row in parl_rows if row[1]}

    if not valid_parl_ids:
        return {"parlamentares": [], "partidos": []}

    # Load votes ONCE — shared between parlamentar and partido rankings
    parlamentar_votos = await _load_votes(db, proposicao_ids, valid_parl_ids)
    if not parlamentar_votos:
        return {"parlamentares": [], "partidos": []}

    min_compared = max(3, len(user_votes) // 4)

    # Score all parlamentares
    parl_scores: list[tuple[int, float, int]] = []
    partido_scores: dict[int, list[tuple[float, int]]] = defaultdict(list)

    for parl_id, prop_votes in parlamentar_votos.items():
        result = _score_parlamentar(user_votes, prop_votes, min_compared)
        if result:
            parl_scores.append((parl_id, result[0], result[1]))
            partido_id = parl_to_partido.get(parl_id)
            if partido_id:
                partido_scores[partido_id].append(result)

    # --- Parlamentar results ---
    parl_scores.sort(key=lambda x: (-x[1], x[0]))
    top_ids = [s[0] for s in parl_scores[:limit]]

    parlamentar_results = []
    if top_ids:
        parl_query = (
            select(Parlamentar)
            .options(joinedload(Parlamentar.partido))
            .where(Parlamentar.id.in_(top_ids))
        )
        parl_result = await db.execute(parl_query)
        parlamentares = {p.id: p for p in parl_result.scalars().unique().all()}

        for parl_id, score, n_votos in parl_scores[:limit]:
            p = parlamentares.get(parl_id)
            if not p:
                continue
            parlamentar_results.append(
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

    # --- Partido results ---
    partido_scored: dict[int, tuple[float, int]] = {}
    for partido_id, individual_scores in partido_scores.items():
        avg_score = sum(s[0] for s in individual_scores) / len(individual_scores)
        partido_scored[partido_id] = (avg_score, len(individual_scores))

    all_partido_ids = set(parl_to_partido.values())
    partido_query = select(Partido).where(Partido.id.in_(all_partido_ids))
    partido_result = await db.execute(partido_query)
    partidos = {p.id: p for p in partido_result.scalars().all()}

    partido_results = []
    for partido_id, p in partidos.items():
        scored = partido_scored.get(partido_id)
        partido_results.append(
            {
                "partido_id": p.id,
                "sigla": p.sigla,
                "nome": p.nome,
                "score": round(scored[0], 1) if scored else None,
                "parlamentares_comparados": scored[1] if scored else 0,
            }
        )

    partido_results.sort(
        key=lambda x: (
            -x["score"] if x["score"] is not None else float("inf"),
            x["sigla"],
            x["partido_id"],
        )
    )

    return {"parlamentares": parlamentar_results, "partidos": partido_results}
