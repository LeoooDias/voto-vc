from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.base import TipoVoto
from app.models.parlamentar import Parlamentar
from app.models.posicao import Posicao, PosicaoProposicao
from app.models.proposicao import Proposicao
from app.models.votacao import Votacao, VotoParlamentar


def _t(obj: object, field: str, lang: str) -> str:
    """Return translated field if lang=en and translation exists, else original."""
    if lang == "en":
        val = getattr(obj, f"{field}_en", None)
        if val:
            return val
    return getattr(obj, field)


async def listar_posicoes(db: AsyncSession, lang: str = "pt-BR") -> list[dict]:
    """Lista posições ativas com suas proposições."""
    result = await db.execute(
        select(Posicao)
        .where(Posicao.ativo.is_(True))
        .options(joinedload(Posicao.proposicoes_rel).joinedload(PosicaoProposicao.posicao))
        .order_by(Posicao.ordem)
    )
    posicoes = result.scalars().unique().all()

    # Load proposicao details for all mapped proposicoes
    all_prop_ids = set()
    for pos in posicoes:
        for pp in pos.proposicoes_rel:
            all_prop_ids.add(pp.proposicao_id)

    props_map: dict[int, Proposicao] = {}
    if all_prop_ids:
        prop_result = await db.execute(select(Proposicao).where(Proposicao.id.in_(all_prop_ids)))
        for p in prop_result.scalars().all():
            props_map[p.id] = p

    items = []
    for pos in posicoes:
        props = []
        for pp in pos.proposicoes_rel:
            prop = props_map.get(pp.proposicao_id)
            if prop:
                resumo = _t(prop, "resumo_cidadao", lang) if prop.resumo_cidadao else prop.ementa
                props.append(
                    {
                        "proposicao_id": prop.id,
                        "tipo": prop.tipo,
                        "numero": prop.numero,
                        "ano": prop.ano,
                        "resumo": resumo,
                        "direcao": pp.direcao.value,
                        "casa_origem": prop.casa_origem.value.lower(),
                    }
                )
        items.append(
            {
                "id": pos.id,
                "slug": pos.slug,
                "titulo": _t(pos, "titulo", lang),
                "descricao": _t(pos, "descricao", lang),
                "tema": pos.tema,
                "ordem": pos.ordem,
                "proposicoes": props,
            }
        )
    return items


def expandir_posicoes_para_respostas(
    posicao_respostas: list[dict],
    posicoes_map: dict[int, list[dict]],
    overrides: dict[int, dict] | None = None,
) -> list[dict]:
    """Expande posição-respostas em respostas por proposição com normalização P/N.

    Args:
        posicao_respostas: [{"posicao_id": int, "voto": str, "peso": float}]
        posicoes_map: {posicao_id: [{"proposicao_id": int, "direcao": str}]}
        overrides: {proposicao_id: {"voto": str, "peso": float}} — overrides diretos
    """
    if overrides is None:
        overrides = {}

    result = []
    seen_props = set()

    for pr in posicao_respostas:
        posicao_id = pr["posicao_id"]
        voto = pr["voto"]
        peso = pr["peso"]

        props = posicoes_map.get(posicao_id, [])
        n = len(props)
        if n == 0:
            continue

        peso_por_prop = peso / n

        for pp in props:
            prop_id = pp["proposicao_id"]
            direcao = pp["direcao"]

            # Override takes precedence, but use diluted peso
            if prop_id in overrides:
                if prop_id not in seen_props:
                    seen_props.add(prop_id)
                    ov = overrides[prop_id].copy()
                    ov["peso"] = ov["peso"] / n
                    result.append(ov)
                continue

            if prop_id in seen_props:
                continue
            seen_props.add(prop_id)

            if voto == "pular":
                result.append({"proposicao_id": prop_id, "voto": "pular", "peso": peso_por_prop})
                continue

            # Map voto through direcao
            if voto == "sim":
                prop_voto = "sim" if direcao == "sim" else "nao"
            else:  # voto == "nao"
                prop_voto = "nao" if direcao == "sim" else "sim"

            result.append({"proposicao_id": prop_id, "voto": prop_voto, "peso": peso_por_prop})

    return result


async def _load_posicoes_map(db: AsyncSession) -> dict[int, list[dict]]:
    """Load all active posicoes with their proposition mappings."""
    result = await db.execute(
        select(Posicao).where(Posicao.ativo.is_(True)).options(joinedload(Posicao.proposicoes_rel))
    )
    posicoes = result.scalars().unique().all()
    return {
        pos.id: [
            {"proposicao_id": pp.proposicao_id, "direcao": pp.direcao.value}
            for pp in pos.proposicoes_rel
        ]
        for pos in posicoes
    }


async def inferir_posicoes_parlamentar(
    db: AsyncSession, parlamentar_id: int, lang: str = "pt-BR"
) -> list[dict]:
    """Infer a parlamentar's stance on each position based on their votes."""
    posicoes_map = await _load_posicoes_map(db)

    # Load posicao metadata
    result = await db.execute(
        select(Posicao).where(Posicao.ativo.is_(True)).order_by(Posicao.ordem)
    )
    posicoes = result.scalars().unique().all()

    # Collect all proposition IDs across all positions
    all_prop_ids = set()
    for props in posicoes_map.values():
        for pp in props:
            all_prop_ids.add(pp["proposicao_id"])

    if not all_prop_ids:
        return []

    # Load parlamentar's votes on these propositions
    votacao_query = select(Votacao.id, Votacao.proposicao_id).where(
        Votacao.proposicao_id.in_(all_prop_ids)
    )
    votacao_result = await db.execute(votacao_query)
    votacao_rows = votacao_result.all()
    votacao_to_prop = {row[0]: row[1] for row in votacao_rows}
    votacao_ids = [row[0] for row in votacao_rows]

    if not votacao_ids:
        return []

    votos_query = select(VotoParlamentar.votacao_id, VotoParlamentar.voto).where(
        VotoParlamentar.parlamentar_id == parlamentar_id,
        VotoParlamentar.votacao_id.in_(votacao_ids),
    )
    votos_result = await db.execute(votos_query)

    # Map prop_id -> TipoVoto (first SIM/NAO found)
    parl_votes: dict[int, str] = {}
    for votacao_id, voto in votos_result.all():
        prop_id = votacao_to_prop.get(votacao_id)
        if prop_id and prop_id not in parl_votes:
            if voto in (TipoVoto.SIM, TipoVoto.NAO):
                parl_votes[prop_id] = voto.value

    # Score each position
    results = []
    for pos in posicoes:
        props = posicoes_map.get(pos.id, [])
        n_total = len(props)
        favor = 0
        contra = 0
        n_voted = 0

        for pp in props:
            parl_voto = parl_votes.get(pp["proposicao_id"])
            if parl_voto is None:
                continue
            n_voted += 1
            # "favor" means aligned with the position
            if pp["direcao"] == "sim":
                if parl_voto == "sim":
                    favor += 1
                else:
                    contra += 1
            else:  # direcao == "nao"
                if parl_voto == "nao":
                    favor += 1
                else:
                    contra += 1

        if n_voted < 2:
            stance = "sem_dados"
            score_pct = None
        else:
            score_pct = round(favor / n_voted * 100, 1)
            if score_pct > 75:
                stance = "fortemente_favor"
            elif score_pct > 50:
                stance = "levemente_favor"
            elif score_pct > 25:
                stance = "levemente_contra"
            elif score_pct == 50:
                stance = "misto"
            else:
                stance = "fortemente_contra"

        results.append(
            {
                "posicao_id": pos.id,
                "slug": pos.slug,
                "titulo": _t(pos, "titulo", lang),
                "tema": pos.tema,
                "ordem": pos.ordem,
                "stance": stance,
                "score_pct": score_pct,
                "n_voted": n_voted,
                "n_total": n_total,
            }
        )

    return results


async def inferir_posicoes_partido(
    db: AsyncSession, partido_id: int, uf: str | None = None, lang: str = "pt-BR"
) -> list[dict]:
    """Infer a partido's stance on each position based on majority votes."""
    posicoes_map = await _load_posicoes_map(db)

    result = await db.execute(
        select(Posicao).where(Posicao.ativo.is_(True)).order_by(Posicao.ordem)
    )
    posicoes = result.scalars().unique().all()

    # Get party's parlamentar IDs
    parl_query = select(Parlamentar.id).where(Parlamentar.partido_id == partido_id)
    if uf:
        parl_query = parl_query.where(Parlamentar.uf == uf.upper())
    parl_result = await db.execute(parl_query)
    parl_ids = {r[0] for r in parl_result.all()}

    if not parl_ids:
        return [
            {
                "posicao_id": pos.id,
                "slug": pos.slug,
                "titulo": _t(pos, "titulo", lang),
                "tema": pos.tema,
                "ordem": pos.ordem,
                "stance": "sem_dados",
                "score_pct": None,
                "n_voted": 0,
                "n_total": len(posicoes_map.get(pos.id, [])),
            }
            for pos in posicoes
        ]

    all_prop_ids = set()
    for props in posicoes_map.values():
        for pp in props:
            all_prop_ids.add(pp["proposicao_id"])

    if not all_prop_ids:
        return []

    # Load votes
    votacao_query = select(Votacao.id, Votacao.proposicao_id).where(
        Votacao.proposicao_id.in_(all_prop_ids)
    )
    votacao_result = await db.execute(votacao_query)
    votacao_rows = votacao_result.all()
    votacao_to_prop = {row[0]: row[1] for row in votacao_rows}
    votacao_ids = [row[0] for row in votacao_rows]

    if not votacao_ids:
        return []

    votos_query = select(
        VotoParlamentar.parlamentar_id,
        VotoParlamentar.votacao_id,
        VotoParlamentar.voto,
    ).where(
        VotoParlamentar.parlamentar_id.in_(parl_ids),
        VotoParlamentar.votacao_id.in_(votacao_ids),
    )
    votos_result = await db.execute(votos_query)

    # Aggregate: prop_id -> {sim: count, nao: count}
    prop_counts: dict[int, dict[str, int]] = defaultdict(lambda: {"sim": 0, "nao": 0})
    for parl_id, votacao_id, voto in votos_result.all():
        prop_id = votacao_to_prop.get(votacao_id)
        if prop_id and voto in (TipoVoto.SIM, TipoVoto.NAO):
            prop_counts[prop_id][voto.value] += 1

    # Score each position
    results = []
    for pos in posicoes:
        props = posicoes_map.get(pos.id, [])
        n_total = len(props)
        favor = 0
        contra = 0
        n_voted = 0

        for pp in props:
            counts = prop_counts.get(pp["proposicao_id"])
            if not counts or (counts["sim"] + counts["nao"]) == 0:
                continue
            n_voted += 1
            majority = "sim" if counts["sim"] > counts["nao"] else "nao"

            if pp["direcao"] == "sim":
                if majority == "sim":
                    favor += 1
                else:
                    contra += 1
            else:
                if majority == "nao":
                    favor += 1
                else:
                    contra += 1

        if n_voted < 2:
            stance = "sem_dados"
            score_pct = None
        else:
            score_pct = round(favor / n_voted * 100, 1)
            if score_pct > 75:
                stance = "fortemente_favor"
            elif score_pct > 50:
                stance = "levemente_favor"
            elif score_pct > 25:
                stance = "levemente_contra"
            elif score_pct == 50:
                stance = "misto"
            else:
                stance = "fortemente_contra"

        results.append(
            {
                "posicao_id": pos.id,
                "slug": pos.slug,
                "titulo": _t(pos, "titulo", lang),
                "tema": pos.tema,
                "ordem": pos.ordem,
                "stance": stance,
                "score_pct": score_pct,
                "n_voted": n_voted,
                "n_total": n_total,
            }
        )

    return results
