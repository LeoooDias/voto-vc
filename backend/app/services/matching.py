from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.base import Casa, Orientacao, TipoVoto
from app.models.parlamentar import Parlamentar
from app.models.partido import BlocoParlamentar, OrientacaoBancada, Partido, bloco_partido
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
    """Load votes grouped by parlamentar -> proposicao -> [TipoVoto]."""
    votacao_query = select(Votacao.id, Votacao.proposicao_id).where(
        Votacao.proposicao_id.in_(proposicao_ids)
    )
    votacao_result = await db.execute(votacao_query)
    votacao_rows = votacao_result.all()
    if not votacao_rows:
        return {}

    votacao_ids = [row[0] for row in votacao_rows]
    votacao_to_prop = {row[0]: row[1] for row in votacao_rows}

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


# --- Orientação helpers for hybrid partido scoring ---


async def _load_orientacoes_bulk(
    db: AsyncSession,
    id_votacoes: list[str],
) -> tuple[dict[str, dict[str, Orientacao]], dict[str, list[str]]]:
    """Load all orientações and bloco mappings for given votações.

    Returns:
        orientacoes: {id_votacao: {sigla_bancada: orientacao}}
        partido_para_blocos: {sigla_partido: [sigla_csv_bloco]}
    """
    orient_query = select(
        OrientacaoBancada.id_votacao,
        OrientacaoBancada.sigla_bancada,
        OrientacaoBancada.orientacao,
    ).where(OrientacaoBancada.id_votacao.in_(id_votacoes))
    orient_result = await db.execute(orient_query)

    orientacoes: dict[str, dict[str, Orientacao]] = defaultdict(dict)
    for id_votacao, sigla_bancada, orientacao in orient_result.all():
        orientacoes[id_votacao][sigla_bancada] = orientacao

    bloco_query = (
        select(BlocoParlamentar.sigla_csv, Partido.sigla)
        .join(bloco_partido, BlocoParlamentar.id == bloco_partido.c.bloco_id)
        .join(Partido, Partido.id == bloco_partido.c.partido_id)
        .where(BlocoParlamentar.sigla_csv.isnot(None))
    )
    bloco_result = await db.execute(bloco_query)
    partido_para_blocos: dict[str, list[str]] = defaultdict(list)
    for sigla_csv, sigla_partido in bloco_result.all():
        partido_para_blocos[sigla_partido].append(sigla_csv)

    return dict(orientacoes), dict(partido_para_blocos)


def _resolve_orientacao(
    sigla_partido: str,
    id_votacoes: list[str],
    orientacoes: dict[str, dict[str, Orientacao]],
    partido_para_blocos: dict[str, list[str]],
) -> Orientacao | None:
    """Resolve orientation for a party across votações of a proposition."""
    for id_ext in id_votacoes:
        bancadas = orientacoes.get(id_ext, {})
        if sigla_partido in bancadas:
            return bancadas[sigla_partido]
        for sigla_csv in partido_para_blocos.get(sigla_partido, []):
            if sigla_csv in bancadas:
                return bancadas[sigla_csv]
    return None


def _majority_vote(
    prop_id: int,
    parl_ids: set[int],
    parlamentar_votos: dict[int, dict[int, list[TipoVoto]]],
) -> str | None:
    """Get majority vote direction for a party's parlamentares on a proposition."""
    sim_count = 0
    nao_count = 0
    for parl_id in parl_ids:
        votes = parlamentar_votos.get(parl_id, {}).get(prop_id, [])
        for v in votes:
            if v == TipoVoto.SIM:
                sim_count += 1
                break
            elif v == TipoVoto.NAO:
                nao_count += 1
                break
    total = sim_count + nao_count
    if total == 0:
        return None
    if sim_count > nao_count:
        return "sim"
    if nao_count > sim_count:
        return "nao"
    return None  # tie


def _score_partido_hybrid(
    user_votes: dict,
    proposicao_ids: list[int],
    sigla_partido: str,
    parl_ids: set[int],
    parlamentar_votos: dict[int, dict[int, list[TipoVoto]]],
    prop_to_votacoes: dict[int, list[str]],
    orientacoes: dict[str, dict[str, Orientacao]],
    partido_para_blocos: dict[str, list[str]],
) -> tuple[float | None, int, int]:
    """Score partido using hybrid approach: orientation when available, vote majority as fallback.

    Returns (score, concordou, discordou).
    """
    concordou = 0
    discordou = 0
    total_score = 0.0
    total_weight = 0.0

    for prop_id in proposicao_ids:
        user_voto, peso = user_votes[prop_id]
        if user_voto.value not in ("sim", "nao"):
            continue

        votacoes_prop = prop_to_votacoes.get(prop_id, [])
        if not votacoes_prop:
            continue

        # Try orientation first
        orientacao = _resolve_orientacao(
            sigla_partido, votacoes_prop, orientacoes, partido_para_blocos
        )

        party_position = None
        if orientacao is not None:
            if orientacao == Orientacao.LIBERADO:
                continue
            if orientacao in (Orientacao.SIM, Orientacao.NAO):
                party_position = orientacao.value

        # Fallback: majority vote
        if party_position is None:
            party_position = _majority_vote(prop_id, parl_ids, parlamentar_votos)

        if party_position is None:
            continue

        total_weight += peso
        if user_voto.value == party_position:
            concordou += 1
            total_score += peso
        else:
            discordou += 1
            total_score -= peso

    score = round(((total_score / total_weight) + 1) * 50, 1) if total_weight > 0 else None
    return score, concordou, discordou


# --- Public API ---


async def comparar_parlamentar(
    db: AsyncSession,
    parlamentar_id: int,
    respostas: list,
) -> dict:
    """Compare a single parlamentar against user votes."""
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
    """Compare a partido against user votes using hybrid approach:
    orientation when available, parlamentar vote majority as fallback.
    """
    user_votes = {r.proposicao_id: (r.voto, r.peso) for r in respostas}
    proposicao_ids = [pid for pid, (v, _) in user_votes.items() if v.value != "pular"]
    empty = {
        "score": None,
        "concordou": 0,
        "discordou": 0,
        "total": 0,
        "parlamentares_comparados": 0,
    }
    if not proposicao_ids:
        return empty

    # Get partido info
    partido = await db.get(Partido, partido_id)
    if not partido:
        return empty

    # Get parlamentar IDs
    parl_query = select(Parlamentar.id).where(Parlamentar.partido_id == partido_id)
    if uf:
        parl_query = parl_query.where(Parlamentar.uf == uf.upper())
    parl_result = await db.execute(parl_query)
    parl_ids = {r[0] for r in parl_result.all()}
    if not parl_ids:
        return empty

    # Load votações and build prop → id_externo mapping
    votacao_query = select(Votacao.id, Votacao.id_externo, Votacao.proposicao_id).where(
        Votacao.proposicao_id.in_(proposicao_ids)
    )
    votacao_result = await db.execute(votacao_query)
    votacao_rows = votacao_result.all()
    if not votacao_rows:
        return empty

    prop_to_votacoes: dict[int, list[str]] = defaultdict(list)
    for _, id_ext, prop_id in votacao_rows:
        prop_to_votacoes[prop_id].append(id_ext)

    all_id_externo = list({row[1] for row in votacao_rows})

    # Load orientações and parlamentar votes
    orientacoes, partido_para_blocos = await _load_orientacoes_bulk(db, all_id_externo)
    parlamentar_votos = await _load_votes(db, proposicao_ids, parl_ids)

    # Count parlamentares with vote overlap
    min_compared = max(3, len(proposicao_ids) // 4)
    n_comparados = sum(
        1
        for parl_id in parl_ids
        if parl_id in parlamentar_votos
        and _score_parlamentar(user_votes, parlamentar_votos[parl_id], min_compared) is not None
    )

    if n_comparados == 0:
        return empty

    score, concordou, discordou = _score_partido_hybrid(
        user_votes,
        proposicao_ids,
        partido.sigla,
        parl_ids,
        parlamentar_votos,
        prop_to_votacoes,
        orientacoes,
        partido_para_blocos,
    )

    return {
        "score": score,
        "concordou": concordou,
        "discordou": discordou,
        "total": concordou + discordou,
        "parlamentares_comparados": n_comparados,
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
    partido_parl_ids: dict[int, set[int]] = defaultdict(set)

    for parl_id, prop_votes in parlamentar_votos.items():
        result = _score_parlamentar(user_votes, prop_votes, min_compared)
        if result:
            parl_scores.append((parl_id, result[0], result[1]))
        partido_id = parl_to_partido.get(parl_id)
        if partido_id:
            partido_parl_ids[partido_id].add(parl_id)

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

    # --- Partido results (hybrid: orientation + vote fallback) ---

    # Load votação id_externo mapping for orientações
    votacao_query = select(Votacao.id, Votacao.id_externo, Votacao.proposicao_id).where(
        Votacao.proposicao_id.in_(proposicao_ids)
    )
    votacao_result = await db.execute(votacao_query)
    votacao_rows = votacao_result.all()

    prop_to_votacoes: dict[int, list[str]] = defaultdict(list)
    for _, id_ext, prop_id in votacao_rows:
        prop_to_votacoes[prop_id].append(id_ext)

    all_id_externo = list({row[1] for row in votacao_rows})
    orientacoes, partido_para_blocos = await _load_orientacoes_bulk(db, all_id_externo)

    # Load all partido info
    all_partido_ids = set(parl_to_partido.values())
    partido_query = select(Partido).where(Partido.id.in_(all_partido_ids))
    partido_result = await db.execute(partido_query)
    partidos = {p.id: p for p in partido_result.scalars().all()}

    # Count parlamentares_comparados per partido (parlamentares meeting threshold)
    partido_n_comparados: dict[int, int] = defaultdict(int)
    for parl_id, score, _ in parl_scores:
        pid = parl_to_partido.get(parl_id)
        if pid:
            partido_n_comparados[pid] += 1

    partido_results = []
    for partido_id, p in partidos.items():
        p_parl_ids = partido_parl_ids.get(partido_id, set())
        if not p_parl_ids:
            partido_results.append(
                {
                    "partido_id": p.id,
                    "sigla": p.sigla,
                    "nome": p.nome,
                    "score": None,
                    "parlamentares_comparados": 0,
                }
            )
            continue

        n_comparados = partido_n_comparados.get(partido_id, 0)

        if n_comparados == 0:
            # No parlamentares met comparison threshold — score not meaningful
            score = None
        else:
            score, _, _ = _score_partido_hybrid(
                user_votes,
                proposicao_ids,
                p.sigla,
                p_parl_ids,
                parlamentar_votos,
                prop_to_votacoes,
                orientacoes,
                partido_para_blocos,
            )

        partido_results.append(
            {
                "partido_id": p.id,
                "sigla": p.sigla,
                "nome": p.nome,
                "score": score,
                "parlamentares_comparados": n_comparados,
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
