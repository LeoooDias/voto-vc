from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.base import Casa, Orientacao, TipoVoto
from app.models.parlamentar import Parlamentar
from app.models.partido import BlocoParlamentar, OrientacaoBancada, Partido, bloco_partido
from app.models.votacao import Votacao, VotoParlamentar

# Bayesian confidence dampening: blends raw score toward 50% (neutral prior)
# when few votes are compared, preventing high-score-low-data from dominating rankings.
_CONFIDENCE_K = 5


def _confidence_score(raw_score: float, n_compared: int) -> float:
    """Adjust score for ranking: penalizes low sample sizes."""
    return (raw_score * n_compared + 50 * _CONFIDENCE_K) / (n_compared + _CONFIDENCE_K)


def _min_compared(n_opinionated: int) -> int:
    """Minimum props required for a meaningful score."""
    return max(3, n_opinionated // 4)


def _confianca_label(effective_compared: int) -> str:
    """Classify confidence based on number of effective comparisons."""
    if effective_compared >= 8:
        return "alta"
    if effective_compared >= 4:
        return "media"
    return "baixa"


def _count_opinionated(user_votes: dict) -> int:
    """Count user votes that are neither pular nor Neutro (peso=0)."""
    return sum(1 for v, p in user_votes.values() if v.value in ("sim", "nao") and p > 0)


def _score_parlamentar(
    user_votes: dict,
    prop_votes: dict[int, list[TipoVoto]],
    min_compared: int,
) -> tuple[float, int, int] | None:
    """Score a single parlamentar. Returns (normalized_score, props_compared, concordou) or None."""
    total_score = 0.0
    total_weight = 0.0
    props_compared = 0
    concordou = 0

    for prop_id, votos_for_prop in prop_votes.items():
        if prop_id not in user_votes:
            continue
        user_voto, peso = user_votes[prop_id]
        if user_voto.value == "pular" or peso == 0:
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
            concordou += 1
        elif (user_voto.value == "sim" and parl_vote == TipoVoto.NAO) or (
            user_voto.value == "nao" and parl_vote == TipoVoto.SIM
        ):
            total_score -= peso

    if total_weight > 0 and props_compared >= min_compared:
        normalized = ((total_score / total_weight) + 1) * 50
        return normalized, props_compared, concordou
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
) -> tuple[str | None, float]:
    """Get majority vote direction and strength for a party's parlamentares.

    Returns (direction, strength) where strength = majority_count / total.
    Returns (None, 0.0) when no votes, tie, or margin < 60%.
    """
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
        return None, 0.0
    majority = max(sim_count, nao_count)
    ratio = majority / total
    if ratio < 0.6:
        return None, 0.0
    direction = "sim" if sim_count > nao_count else "nao"
    return direction, ratio


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
        if user_voto.value not in ("sim", "nao") or peso == 0:
            continue

        votacoes_prop = prop_to_votacoes.get(prop_id, [])
        if not votacoes_prop:
            continue

        # Try orientation first
        orientacao = _resolve_orientacao(
            sigla_partido, votacoes_prop, orientacoes, partido_para_blocos
        )

        party_position = None
        source_is_majority = False
        if orientacao is not None:
            if orientacao == Orientacao.LIBERADO:
                continue
            if orientacao in (Orientacao.SIM, Orientacao.NAO):
                party_position = orientacao.value

        # Fallback: majority vote (weighted by unanimity)
        if party_position is None:
            party_position, vote_strength = _majority_vote(prop_id, parl_ids, parlamentar_votos)
            source_is_majority = True

        if party_position is None:
            continue

        effective_peso = peso * vote_strength if source_is_majority else peso
        total_weight += effective_peso
        if user_voto.value == party_position:
            concordou += 1
            total_score += effective_peso
        else:
            discordou += 1
            total_score -= effective_peso

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

    n_opinionated = _count_opinionated(user_votes)

    concordou = 0
    discordou = 0
    total_score = 0.0
    total_weight = 0.0

    for prop_id, votes_for_prop in prop_votes.items():
        if prop_id not in user_votes:
            continue
        user_voto, peso = user_votes[prop_id]
        if user_voto.value == "pular" or peso == 0:
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
    presenca = round(total / n_opinionated, 2) if n_opinionated > 0 else 0.0
    return {
        "score": score,
        "concordou": concordou,
        "discordou": discordou,
        "total": total,
        "presenca": presenca,
        "confianca": _confianca_label(total),
    }


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
    n_opinionated = _count_opinionated(user_votes)
    proposicao_ids = [pid for pid, (v, p) in user_votes.items() if v.value != "pular" and p > 0]
    empty = {
        "score": None,
        "concordou": 0,
        "discordou": 0,
        "total": 0,
        "parlamentares_comparados": 0,
        "confianca": "baixa",
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
    min_compared = _min_compared(n_opinionated)
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

    total = concordou + discordou
    return {
        "score": score,
        "concordou": concordou,
        "discordou": discordou,
        "total": total,
        "parlamentares_comparados": n_comparados,
        "confianca": _confianca_label(total) if score is not None else "baixa",
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
    n_opinionated = _count_opinionated(user_votes)
    proposicao_ids = [pid for pid, (v, p) in user_votes.items() if v.value != "pular" and p > 0]
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

    min_compared = _min_compared(n_opinionated)

    # Score all parlamentares
    parl_scores: list[tuple[int, float, int]] = []
    partido_parl_ids: dict[int, set[int]] = defaultdict(set)

    for parl_id, prop_votes in parlamentar_votos.items():
        result = _score_parlamentar(user_votes, prop_votes, min_compared)
        if result:
            parl_scores.append((parl_id, result[0], result[1], result[2]))
        partido_id = parl_to_partido.get(parl_id)
        if partido_id:
            partido_parl_ids[partido_id].add(parl_id)

    # --- Parlamentar results ---
    # Sort by confidence-adjusted score (penalizes low sample sizes)
    parl_scores.sort(key=lambda x: (-_confidence_score(x[1], x[2]), -x[1], x[0]))
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

        for parl_id, score, n_votos, n_concordou in parl_scores[:limit]:
            p = parlamentares.get(parl_id)
            if not p:
                continue
            presenca = round(n_votos / n_opinionated, 2) if n_opinionated > 0 else 0.0
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
                    "concordou": n_concordou,
                    "presenca": presenca,
                    "confianca": _confianca_label(n_votos),
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
    for parl_id, score, *_ in parl_scores:
        pid = parl_to_partido.get(parl_id)
        if pid:
            partido_n_comparados[pid] += 1

    partido_results = []
    for partido_id, p in partidos.items():
        if p.sigla == "S/Partido":
            continue
        p_parl_ids = partido_parl_ids.get(partido_id, set())
        if not p_parl_ids:
            partido_results.append(
                {
                    "partido_id": p.id,
                    "sigla": p.sigla,
                    "nome": p.nome,
                    "score": None,
                    "parlamentares_comparados": 0,
                    "votos_comparados": 0,
                    "concordou": 0,
                    "confianca": "baixa",
                }
            )
            continue

        n_comparados = partido_n_comparados.get(partido_id, 0)

        if n_comparados == 0:
            # No parlamentares met comparison threshold — score not meaningful
            score = None
            p_concordou = 0
            p_discordou = 0
        else:
            score, p_concordou, p_discordou = _score_partido_hybrid(
                user_votes,
                proposicao_ids,
                p.sigla,
                p_parl_ids,
                parlamentar_votos,
                prop_to_votacoes,
                orientacoes,
                partido_para_blocos,
            )

        p_votos_comparados = p_concordou + p_discordou
        partido_results.append(
            {
                "partido_id": p.id,
                "sigla": p.sigla,
                "nome": p.nome,
                "score": score,
                "parlamentares_comparados": n_comparados,
                "votos_comparados": p_votos_comparados,
                "concordou": p_concordou,
                "confianca": _confianca_label(p_votos_comparados) if score is not None else "baixa",
            }
        )

    def _partido_sort_key(x: dict) -> tuple:
        if x["score"] is not None:
            return (
                -_confidence_score(x["score"], x["votos_comparados"]),
                -x["score"],
                x["sigla"],
                x["partido_id"],
            )
        return (float("inf"), float("inf"), x["sigla"], x["partido_id"])

    partido_results.sort(key=_partido_sort_key)

    return {"parlamentares": parlamentar_results, "partidos": partido_results}
