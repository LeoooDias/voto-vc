"""Alinhamento usuário–partido via orientações de bancada.

Usa orientações oficiais como âncora principal, com fallback para
distribuição de votos quando não há orientação ou há divergência.
"""

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Orientacao
from app.models.parlamentar import Parlamentar
from app.models.partido import BlocoParlamentar, OrientacaoBancada, Partido, bloco_partido
from app.models.votacao import Votacao, VotoParlamentar


async def _carregar_mapa_bloco_partido(db: AsyncSession) -> dict[str, list[str]]:
    """Retorna {sigla_csv_do_bloco: [sigla_partido, ...]}."""
    query = (
        select(BlocoParlamentar.sigla_csv, Partido.sigla)
        .join(bloco_partido, BlocoParlamentar.id == bloco_partido.c.bloco_id)
        .join(Partido, Partido.id == bloco_partido.c.partido_id)
        .where(BlocoParlamentar.sigla_csv.isnot(None))
    )
    result = await db.execute(query)
    mapa: dict[str, list[str]] = defaultdict(list)
    for sigla_csv, sigla_partido in result.all():
        mapa[sigla_csv].append(sigla_partido)
    return dict(mapa)


async def _orientacao_efetiva_batch(
    db: AsyncSession,
    sigla_partido: str,
    id_votacoes: list[str],
) -> dict[str, Orientacao | None]:
    """Retorna {id_votacao: orientacao_normalizada} para um partido em várias votações.

    Busca primeiro orientação direta do partido, depois via bloco/federação.
    Retorna None para votações sem orientação disponível.
    """
    if not id_votacoes:
        return {}

    # Buscar todas as orientações para essas votações de uma vez
    orient_query = select(
        OrientacaoBancada.id_votacao,
        OrientacaoBancada.sigla_bancada,
        OrientacaoBancada.orientacao,
    ).where(OrientacaoBancada.id_votacao.in_(id_votacoes))
    orient_result = await db.execute(orient_query)

    # Agrupar por votação
    orientacoes_por_votacao: dict[str, dict[str, Orientacao]] = defaultdict(dict)
    for id_votacao, sigla_bancada, orientacao in orient_result.all():
        orientacoes_por_votacao[id_votacao][sigla_bancada] = orientacao

    # Carregar mapa bloco → partidos
    mapa_bloco = await _carregar_mapa_bloco_partido(db)
    # Inverter: sigla_partido → [sigla_csv_do_bloco]
    partido_para_blocos: dict[str, list[str]] = defaultdict(list)
    for sigla_csv, partidos in mapa_bloco.items():
        for p in partidos:
            partido_para_blocos[p].append(sigla_csv)

    resultado: dict[str, Orientacao | None] = {}
    for id_votacao in id_votacoes:
        bancadas = orientacoes_por_votacao.get(id_votacao, {})

        # 1. Orientação direta do partido
        if sigla_partido in bancadas:
            resultado[id_votacao] = bancadas[sigla_partido]
            continue

        # 2. Orientação via bloco/federação
        found = None
        for sigla_csv in partido_para_blocos.get(sigla_partido, []):
            if sigla_csv in bancadas:
                found = bancadas[sigla_csv]
                break
        resultado[id_votacao] = found

    return resultado


async def _parlamentar_ids_by_uf(db: AsyncSession, sigla_partido: str, uf: str) -> set[int]:
    """Retorna IDs de parlamentares do partido filtrados por UF."""
    partido_id_subq = select(Partido.id).where(Partido.sigla == sigla_partido).scalar_subquery()
    query = select(Parlamentar.id).where(
        Parlamentar.partido_id == partido_id_subq,
        Parlamentar.uf == uf.upper(),
    )
    result = await db.execute(query)
    return {row[0] for row in result.all()}


def _apply_uf_filter(query, parl_ids: set[int] | None):
    """Adiciona filtro de parlamentar_id à query se parl_ids fornecido."""
    if parl_ids is not None:
        return query.where(VotoParlamentar.parlamentar_id.in_(parl_ids))
    return query


async def _detectar_divergencia_batch(
    db: AsyncSession,
    sigla_partido: str,
    orientacoes: dict[str, Orientacao | None],
    threshold: float = 0.3,
    parl_ids: set[int] | None = None,
) -> set[str]:
    """Retorna set de id_votacao onde há divergência significativa
    entre orientação e comportamento real da bancada.
    """
    # Filtrar apenas votações com orientação efetiva (não None, não liberado)
    votacoes_com_orientacao = {
        id_v: o for id_v, o in orientacoes.items() if o is not None and o != Orientacao.LIBERADO
    }
    if not votacoes_com_orientacao:
        return set()

    # Buscar id_externo → votacao.id
    votacao_query = select(Votacao.id, Votacao.id_externo).where(
        Votacao.id_externo.in_(list(votacoes_com_orientacao.keys()))
    )
    votacao_result = await db.execute(votacao_query)
    externo_to_id = {row[1]: row[0] for row in votacao_result.all()}

    votacao_ids = list(externo_to_id.values())
    if not votacao_ids:
        return set()

    # Buscar votos dos parlamentares do partido nessas votações
    votos_query = (
        select(
            VotoParlamentar.votacao_id,
            VotoParlamentar.voto,
            func.count(VotoParlamentar.id),
        )
        .where(
            VotoParlamentar.votacao_id.in_(votacao_ids),
            VotoParlamentar.partido_na_epoca == sigla_partido,
        )
        .group_by(VotoParlamentar.votacao_id, VotoParlamentar.voto)
    )
    votos_query = _apply_uf_filter(votos_query, parl_ids)
    votos_result = await db.execute(votos_query)

    # Agrupar por votação
    votos_por_votacao: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for votacao_id, voto, count in votos_result.all():
        votos_por_votacao[votacao_id][voto.value] = count

    # Mapear de volta para id_externo e checar divergência
    id_to_externo = {v: k for k, v in externo_to_id.items()}
    divergentes: set[str] = set()

    for votacao_id, dist_votos in votos_por_votacao.items():
        id_externo = id_to_externo.get(votacao_id)
        if not id_externo:
            continue
        orientacao = votacoes_com_orientacao.get(id_externo)
        if not orientacao:
            continue

        total = sum(dist_votos.values())
        if total == 0:
            continue

        # Contar votos que divergem da orientação (excluindo abstenção/obstrução)
        n_divergentes = 0
        for voto_val, count in dist_votos.items():
            if voto_val in ("abstencao", "obstrucao", "ausente", "presente_sem_voto"):
                continue
            if voto_val != orientacao.value:
                n_divergentes += count

        # Total de votos substantivos (sim + nao)
        total_substantivo = sum(c for v, c in dist_votos.items() if v in ("sim", "nao"))
        if total_substantivo > 0 and (n_divergentes / total_substantivo) > threshold:
            divergentes.add(id_externo)

    return divergentes


async def _distribuicao_votos_partido_batch(
    db: AsyncSession,
    sigla_partido: str,
    id_votacoes: list[str],
    threshold: float = 0.7,
    parl_ids: set[int] | None = None,
) -> dict[str, Orientacao | None]:
    """Infere orientação a partir da distribuição de votos do partido.

    Para cada votação, se >= threshold dos votos substantivos (sim+nao) forem
    numa direção, retorna essa direção como orientação inferida.
    Retorna None se não houver maioria clara.
    """
    if not id_votacoes:
        return {}

    votacao_query = select(Votacao.id, Votacao.id_externo).where(
        Votacao.id_externo.in_(id_votacoes)
    )
    votacao_result = await db.execute(votacao_query)
    externo_to_id = {row[1]: row[0] for row in votacao_result.all()}

    votacao_ids = list(externo_to_id.values())
    if not votacao_ids:
        return {}

    votos_query = (
        select(
            VotoParlamentar.votacao_id,
            VotoParlamentar.voto,
            func.count(VotoParlamentar.id),
        )
        .where(
            VotoParlamentar.votacao_id.in_(votacao_ids),
            VotoParlamentar.partido_na_epoca == sigla_partido,
        )
        .group_by(VotoParlamentar.votacao_id, VotoParlamentar.voto)
    )
    votos_query = _apply_uf_filter(votos_query, parl_ids)
    votos_result = await db.execute(votos_query)

    votos_por_votacao: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for votacao_id, voto, count in votos_result.all():
        votos_por_votacao[votacao_id][voto.value] = count

    id_to_externo = {v: k for k, v in externo_to_id.items()}
    resultado: dict[str, Orientacao | None] = {}

    for votacao_id, dist in votos_por_votacao.items():
        id_externo = id_to_externo.get(votacao_id)
        if not id_externo:
            continue
        n_sim = dist.get("sim", 0)
        n_nao = dist.get("nao", 0)
        total = n_sim + n_nao
        if total < 2:
            resultado[id_externo] = None
            continue
        if n_sim / total >= threshold:
            resultado[id_externo] = Orientacao.SIM
        elif n_nao / total >= threshold:
            resultado[id_externo] = Orientacao.NAO
        else:
            resultado[id_externo] = None

    return resultado


async def alinhamento_por_orientacao(
    db: AsyncSession,
    sigla_partido: str,
    respostas: list,
    divergencia_threshold: float = 0.3,
    fallback_threshold: float = 0.7,
    uf: str | None = None,
) -> dict:
    """Calcula alinhamento usuário–partido usando orientações de bancada.

    Usa orientações oficiais como âncora principal, com fallback para
    distribuição de votos quando não há orientação disponível.
    Quando uf é fornecido, o fallback considera apenas parlamentares daquele estado.
    Retorna dict com score, contadores e detalhamento.
    """
    user_votes = {r.proposicao_id: (r.voto, r.peso) for r in respostas}
    proposicao_ids = [pid for pid, (v, _) in user_votes.items() if v.value != "pular"]
    if not proposicao_ids:
        return _resultado_vazio(sigla_partido)

    # Buscar votações ligadas às proposições do usuário
    votacao_query = select(Votacao.id, Votacao.id_externo, Votacao.proposicao_id).where(
        Votacao.proposicao_id.in_(proposicao_ids)
    )
    votacao_result = await db.execute(votacao_query)
    votacao_rows = votacao_result.all()
    if not votacao_rows:
        return _resultado_vazio(sigla_partido)

    # Mapear: id_externo → proposicao_id (pegar a votação mais recente por proposição)
    prop_to_votacoes: dict[int, list[str]] = defaultdict(list)
    for _, id_externo, prop_id in votacao_rows:
        prop_to_votacoes[prop_id].append(id_externo)

    # Pegar todos os id_externo
    all_id_externo = [row[1] for row in votacao_rows]

    # Resolver parlamentar IDs se filtro UF ativo
    parl_ids = await _parlamentar_ids_by_uf(db, sigla_partido, uf) if uf else None

    # Buscar orientações (nacionais — orientação é do partido, não do estado)
    orientacoes = await _orientacao_efetiva_batch(db, sigla_partido, all_id_externo)

    # Detectar divergências (filtra por UF se aplicável)
    divergencias = await _detectar_divergencia_batch(
        db, sigla_partido, orientacoes, divergencia_threshold, parl_ids
    )

    # Carregar fallback por distribuição de votos (filtra por UF se aplicável)
    fallback_dist = await _distribuicao_votos_partido_batch(
        db, sigla_partido, all_id_externo, fallback_threshold, parl_ids
    )

    # Calcular alinhamento
    total_score = 0.0
    total_weight = 0.0
    concordou = 0
    discordou = 0
    votacoes_liberadas = 0
    votacoes_sem_orientacao = 0
    votacoes_com_divergencia = len(divergencias)
    votacoes_fallback = 0

    for prop_id in proposicao_ids:
        user_voto, peso = user_votes[prop_id]
        if user_voto.value == "pular":
            continue

        votacoes_prop = prop_to_votacoes.get(prop_id, [])
        if not votacoes_prop:
            votacoes_sem_orientacao += 1
            continue

        # Buscar orientação efetiva (primeira votação com orientação disponível)
        orientacao_usada = None
        usou_fallback = False
        for id_ext in votacoes_prop:
            o = orientacoes.get(id_ext)
            if o is not None and id_ext not in divergencias:
                orientacao_usada = o
                break

        if orientacao_usada is None:
            # Verificar se todas são liberadas
            todas_liberadas = all(
                orientacoes.get(v) == Orientacao.LIBERADO
                for v in votacoes_prop
                if orientacoes.get(v)
            )
            if todas_liberadas and any(orientacoes.get(v) for v in votacoes_prop):
                votacoes_liberadas += 1
                continue

            # Fallback: inferir pela distribuição de votos do partido
            for id_ext in votacoes_prop:
                fb = fallback_dist.get(id_ext)
                if fb is not None:
                    orientacao_usada = fb
                    usou_fallback = True
                    break

            if orientacao_usada is None:
                votacoes_sem_orientacao += 1
                continue

        if orientacao_usada == Orientacao.LIBERADO:
            votacoes_liberadas += 1
            continue

        # Comparar voto do usuário com orientação
        total_weight += peso
        if usou_fallback:
            votacoes_fallback += 1
        if user_voto.value == orientacao_usada.value:
            concordou += 1
            total_score += peso
        elif (user_voto.value == "sim" and orientacao_usada == Orientacao.NAO) or (
            user_voto.value == "nao" and orientacao_usada == Orientacao.SIM
        ):
            discordou += 1
            total_score -= peso
        # abstencao/obstrucao da bancada: não conta

    votacoes_consideradas = concordou + discordou
    score = round(((total_score / total_weight) + 1) * 50, 1) if total_weight > 0 else None

    return {
        "sigla_partido": sigla_partido,
        "alinhamento_score": score,
        "metodo": (
            "orientacao" if votacoes_fallback < concordou + discordou else "fallback_distribuicao"
        ),
        "votacoes_consideradas": votacoes_consideradas,
        "votacoes_liberadas": votacoes_liberadas,
        "votacoes_sem_orientacao": votacoes_sem_orientacao,
        "votacoes_com_divergencia": votacoes_com_divergencia,
        "votacoes_fallback_distribuicao": votacoes_fallback,
    }


async def orientacoes_por_proposicao(
    db: AsyncSession,
    proposicao_id: int,
) -> dict:
    """Retorna orientações e distribuição de votos por partido para uma proposição."""
    # Buscar votações da proposição
    votacao_query = (
        select(Votacao.id, Votacao.id_externo, Votacao.descricao, Votacao.data)
        .where(Votacao.proposicao_id == proposicao_id)
        .order_by(Votacao.data.desc())
    )
    votacao_result = await db.execute(votacao_query)
    votacoes = votacao_result.all()
    if not votacoes:
        return {"proposicao_id": proposicao_id, "votacoes": []}

    votacao_ids = [v[0] for v in votacoes]
    id_externos = [v[1] for v in votacoes]

    # Buscar orientações
    orient_query = select(
        OrientacaoBancada.id_votacao,
        OrientacaoBancada.sigla_bancada,
        OrientacaoBancada.orientacao,
        OrientacaoBancada.orientacao_raw,
    ).where(OrientacaoBancada.id_votacao.in_(id_externos))
    orient_result = await db.execute(orient_query)
    orient_rows = orient_result.all()

    # Agrupar orientações por votação
    orient_por_votacao: dict[str, list[dict]] = defaultdict(list)
    for id_votacao, sigla_bancada, orientacao, orientacao_raw in orient_rows:
        orient_por_votacao[id_votacao].append(
            {
                "sigla_bancada": sigla_bancada,
                "orientacao": orientacao.value,
                "orientacao_raw": orientacao_raw,
            }
        )

    # Buscar distribuição de votos por partido
    votos_query = (
        select(
            VotoParlamentar.votacao_id,
            VotoParlamentar.partido_na_epoca,
            VotoParlamentar.voto,
            func.count(VotoParlamentar.id),
        )
        .where(
            VotoParlamentar.votacao_id.in_(votacao_ids),
            VotoParlamentar.partido_na_epoca.isnot(None),
        )
        .group_by(
            VotoParlamentar.votacao_id,
            VotoParlamentar.partido_na_epoca,
            VotoParlamentar.voto,
        )
    )
    votos_result = await db.execute(votos_query)

    # Agrupar distribuição
    dist_por_votacao: dict[int, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    for votacao_id, partido, voto, count in votos_result.all():
        dist_por_votacao[votacao_id][partido][voto.value] = count

    # Carregar mapa bloco → partidos para resolver orientação via
    mapa_bloco = await _carregar_mapa_bloco_partido(db)
    partido_para_blocos: dict[str, list[str]] = defaultdict(list)
    for sigla_csv, partidos_list in mapa_bloco.items():
        for p in partidos_list:
            partido_para_blocos[p].append(sigla_csv)

    # Montar resposta
    resultado_votacoes = []
    for votacao_id, id_externo, descricao, data in votacoes:
        orientacoes_votacao = orient_por_votacao.get(id_externo, [])
        dist_votacao = dist_por_votacao.get(votacao_id, {})

        # Coletar todos os partidos que votaram
        partidos_info = []
        for sigla_partido, votos_dist in sorted(dist_votacao.items()):
            total = sum(votos_dist.values())
            if total == 0:
                continue

            # Resolver orientação para este partido
            orientacao_partido = None
            orientacao_via = None
            sigla_bloco = None

            # Buscar direto
            for o in orientacoes_votacao:
                if o["sigla_bancada"] == sigla_partido:
                    orientacao_partido = o["orientacao"]
                    orientacao_via = "partido"
                    break

            # Buscar via bloco
            if orientacao_partido is None:
                for sigla_csv in partido_para_blocos.get(sigla_partido, []):
                    for o in orientacoes_votacao:
                        if o["sigla_bancada"] == sigla_csv:
                            orientacao_partido = o["orientacao"]
                            orientacao_via = "bloco"
                            sigla_bloco = sigla_csv
                            break
                    if orientacao_partido:
                        break

            # Calcular percentuais
            sim_pct = round(votos_dist.get("sim", 0) / total, 2)
            nao_pct = round(votos_dist.get("nao", 0) / total, 2)
            outros_pct = round(1 - sim_pct - nao_pct, 2)

            # Detectar divergência simples
            divergencia = False
            if orientacao_partido in ("sim", "nao"):
                n_substantivo = votos_dist.get("sim", 0) + votos_dist.get("nao", 0)
                if n_substantivo > 0:
                    n_divergentes = (
                        votos_dist.get("nao", 0)
                        if orientacao_partido == "sim"
                        else votos_dist.get("sim", 0)
                    )
                    divergencia = (n_divergentes / n_substantivo) > 0.3

            partidos_info.append(
                {
                    "sigla": sigla_partido,
                    "orientacao": orientacao_partido,
                    "orientacao_via": orientacao_via,
                    "sigla_bloco": sigla_bloco,
                    "votos_sim_pct": sim_pct,
                    "votos_nao_pct": nao_pct,
                    "votos_outros_pct": outros_pct,
                    "divergencia_detectada": divergencia,
                }
            )

        resultado_votacoes.append(
            {
                "id_votacao": id_externo,
                "descricao": descricao,
                "data": data.isoformat() if data else None,
                "partidos": partidos_info,
            }
        )

    return {"proposicao_id": proposicao_id, "votacoes": resultado_votacoes}


async def calcular_disciplina(
    db: AsyncSession,
    sigla_partido: str,
    uf: str | None = None,
) -> dict:
    """Calcula a disciplina partidária: % de vezes que os parlamentares
    votaram de acordo com a orientação oficial da bancada.

    Quando uf é fornecido, considera apenas parlamentares daquele estado.
    Considera apenas votações com orientação sim/nao (exclui liberado/abstencao/obstrucao).
    """
    # Buscar todas as orientações do partido
    # Primeiro: orientações diretas com sigla do partido
    orient_query = select(
        OrientacaoBancada.id_votacao,
        OrientacaoBancada.orientacao,
    ).where(OrientacaoBancada.sigla_bancada == sigla_partido)
    orient_result = await db.execute(orient_query)
    orientacoes_diretas = {row[0]: row[1] for row in orient_result.all()}

    # Segundo: orientações via bloco
    mapa_bloco = await _carregar_mapa_bloco_partido(db)
    blocos_do_partido = [
        sigla_csv for sigla_csv, partidos in mapa_bloco.items() if sigla_partido in partidos
    ]

    orientacoes_bloco: dict[str, Orientacao] = {}
    if blocos_do_partido:
        bloco_query = select(
            OrientacaoBancada.id_votacao,
            OrientacaoBancada.orientacao,
        ).where(OrientacaoBancada.sigla_bancada.in_(blocos_do_partido))
        bloco_result = await db.execute(bloco_query)
        orientacoes_bloco = {row[0]: row[1] for row in bloco_result.all()}

    # Merge: direta prevalece sobre bloco
    all_orientacoes: dict[str, Orientacao] = {**orientacoes_bloco, **orientacoes_diretas}

    # Filtrar apenas sim/nao (orientações que geram expectativa clara de voto)
    orientacoes_efetivas = {
        id_v: o for id_v, o in all_orientacoes.items() if o in (Orientacao.SIM, Orientacao.NAO)
    }

    if not orientacoes_efetivas:
        return {
            "disciplina": None,
            "votacoes_analisadas": 0,
            "votacoes_liberadas": sum(
                1 for o in all_orientacoes.values() if o == Orientacao.LIBERADO
            ),
        }

    # Buscar votacao.id para os id_externo
    votacao_query = select(Votacao.id, Votacao.id_externo).where(
        Votacao.id_externo.in_(list(orientacoes_efetivas.keys()))
    )
    votacao_result = await db.execute(votacao_query)
    externo_to_id = {row[1]: row[0] for row in votacao_result.all()}

    votacao_ids = list(externo_to_id.values())
    if not votacao_ids:
        return {"disciplina": None, "votacoes_analisadas": 0, "votacoes_liberadas": 0}

    # Resolver parlamentar IDs se filtro UF ativo
    parl_ids = await _parlamentar_ids_by_uf(db, sigla_partido, uf) if uf else None

    # Buscar votos dos parlamentares do partido
    votos_query = (
        select(
            VotoParlamentar.votacao_id,
            VotoParlamentar.voto,
            func.count(VotoParlamentar.id),
        )
        .where(
            VotoParlamentar.votacao_id.in_(votacao_ids),
            VotoParlamentar.partido_na_epoca == sigla_partido,
        )
        .group_by(VotoParlamentar.votacao_id, VotoParlamentar.voto)
    )
    votos_query = _apply_uf_filter(votos_query, parl_ids)
    votos_result = await db.execute(votos_query)

    votos_por_votacao: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for votacao_id, voto, count in votos_result.all():
        votos_por_votacao[votacao_id][voto.value] = count

    id_to_externo = {v: k for k, v in externo_to_id.items()}

    total_alinhados = 0
    total_substantivos = 0
    votacoes_analisadas = 0

    for votacao_id, dist_votos in votos_por_votacao.items():
        id_externo = id_to_externo.get(votacao_id)
        if not id_externo:
            continue
        orientacao = orientacoes_efetivas.get(id_externo)
        if not orientacao:
            continue

        n_sim = dist_votos.get("sim", 0)
        n_nao = dist_votos.get("nao", 0)
        n_substantivo = n_sim + n_nao
        if n_substantivo == 0:
            continue

        votacoes_analisadas += 1
        alinhados = n_sim if orientacao == Orientacao.SIM else n_nao
        total_alinhados += alinhados
        total_substantivos += n_substantivo

    disciplina = (
        round((total_alinhados / total_substantivos) * 100, 1) if total_substantivos > 0 else None
    )
    votacoes_liberadas = sum(1 for o in all_orientacoes.values() if o == Orientacao.LIBERADO)

    return {
        "disciplina": disciplina,
        "votacoes_analisadas": votacoes_analisadas,
        "votacoes_liberadas": votacoes_liberadas,
    }


def _resultado_vazio(sigla_partido: str) -> dict:
    return {
        "sigla_partido": sigla_partido,
        "alinhamento_score": None,
        "metodo": "orientacao",
        "votacoes_consideradas": 0,
        "votacoes_liberadas": 0,
        "votacoes_sem_orientacao": 0,
        "votacoes_com_divergencia": 0,
        "votacoes_fallback_distribuicao": 0,
    }
