"""Find substantive, divisive votações from the Câmara API.

Strategy: fetch proposições by type (PL, PEC, MPV, PLP), check their votações,
and identify the ones with the most divided votes (closest to 50/50 split).
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select

from app.classification.classifier import classify_proposicao
from app.database import async_session
from app.ingestion.base import BaseAPIClient
from app.models.parlamentar import Parlamentar
from app.models.proposicao import Proposicao
from app.models.topico import ProposicaoTopico, Topico
from app.models.votacao import Votacao, VotoParlamentar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2"


async def find_and_import_divisive_votes():
    client = BaseAPIClient(CAMARA_API, delay_between_requests=1.0)

    async with async_session() as db:
        # Load parlamentar mapping
        result = await db.execute(select(Parlamentar.id_externo, Parlamentar.id))
        parl_mapping = {row[0]: row[1] for row in result.all()}
        logger.info(f"Loaded {len(parl_mapping)} parlamentares")

        # Load topic mapping
        from app.classification.topics import TOPICS

        topico_mapping = {}
        for t in TOPICS:
            result = await db.execute(select(Topico).where(Topico.slug == t.slug))
            topico = result.scalar_one_or_none()
            if topico:
                topico_mapping[t.slug] = topico.id

        found = 0
        target = 50  # We want at least 50 good proposições

        for ano in [2025, 2024, 2023, 2026]:
            if found >= target:
                break
            for tipo in ["PL", "PEC", "MPV", "PLP"]:
                if found >= target:
                    break
                logger.info(f"Scanning {tipo}s from {ano}...")

                try:
                    props = await client.get_paginated(
                        "proposicoes",
                        params={"siglaTipo": tipo, "ano": ano, "ordem": "DESC", "ordenarPor": "id"},
                        max_pages=3,
                    )
                except Exception as e:
                    logger.warning(f"Failed to fetch {tipo} {ano}: {e}")
                    continue

                logger.info(f"  Found {len(props)} {tipo}s for {ano}")

                for prop in props:
                    if found >= target:
                        break

                    prop_id = prop["id"]
                    prop_id_externo = f"camara_prop_{prop_id}"

                    # Skip if already imported
                    existing = await db.execute(
                        select(Proposicao).where(Proposicao.id_externo == prop_id_externo)
                    )
                    if existing.scalar_one_or_none():
                        continue

                    # Get votações for this proposição
                    try:
                        vots_data = await client.get(f"proposicoes/{prop_id}/votacoes")
                        votacoes = vots_data.get("dados", [])
                    except Exception:
                        continue

                    if not votacoes:
                        continue

                    # Check each votação for divisiveness
                    best_votacao = None
                    best_divisiveness = 0
                    best_votos = []

                    for vot in votacoes:
                        try:
                            votos_data = await client.get(f"votacoes/{vot['id']}/votos")
                            votos = votos_data.get("dados", [])
                        except Exception:
                            continue

                        if len(votos) < 100:
                            continue

                        sim = sum(1 for v in votos if v.get("tipoVoto") == "Sim")
                        nao = sum(1 for v in votos if v.get("tipoVoto") == "Não")
                        total = sim + nao
                        if total < 50:
                            continue

                        divisiveness = min(sim, nao) / total
                        if divisiveness > best_divisiveness:
                            best_divisiveness = divisiveness
                            best_votacao = vot
                            best_votos = votos

                    if best_divisiveness < 0.15 or not best_votacao:
                        continue

                    # This is a good one! Fetch full proposição details
                    try:
                        prop_detail = await client.get(f"proposicoes/{prop_id}")
                        prop_raw = prop_detail.get("dados", {})
                    except Exception:
                        continue

                    ementa = prop_raw.get("ementa", prop.get("ementa", ""))
                    if not ementa:
                        continue

                    # Classify
                    topics = classify_proposicao(ementa, tipo)

                    # Compute vote totals
                    sim = sum(1 for v in best_votos if v.get("tipoVoto") == "Sim")
                    nao = sum(1 for v in best_votos if v.get("tipoVoto") == "Não")
                    abst = sum(1 for v in best_votos if v.get("tipoVoto") == "Abstenção")
                    relevancia = round(min(sim, nao) / (sim + nao) * 2, 3) if (sim + nao) > 0 else 0

                    # Save proposição
                    proposicao = Proposicao(
                        id_externo=prop_id_externo,
                        casa_origem="camara",
                        tipo=tipo,
                        numero=prop_raw.get("numero", prop.get("numero", 0)),
                        ano=prop_raw.get("ano", ano),
                        ementa=ementa,
                        resumo_cidadao=ementa,  # placeholder
                        url_inteiro_teor=prop_raw.get("urlInteiroTeor"),
                        situacao=prop_raw.get("statusProposicao", {}).get("descricaoSituacao")
                        if isinstance(prop_raw.get("statusProposicao"), dict)
                        else None,
                        relevancia_score=relevancia,
                        dados_brutos=prop_raw,
                    )
                    db.add(proposicao)
                    await db.flush()

                    # Save topic classifications
                    for tc in topics:
                        if tc.slug in topico_mapping:
                            db.add(
                                ProposicaoTopico(
                                    proposicao_id=proposicao.id,
                                    topico_id=topico_mapping[tc.slug],
                                    confianca=tc.confianca,
                                    metodo="heuristic",
                                )
                            )

                    # Save votação
                    vot_id_externo = f"camara_{best_votacao['id']}"
                    existing_vot = await db.execute(
                        select(Votacao).where(Votacao.id_externo == vot_id_externo)
                    )
                    if not existing_vot.scalar_one_or_none():
                        data_str = best_votacao.get("dataHoraRegistro") or best_votacao.get(
                            "data", ""
                        )
                        try:
                            data_dt = datetime.fromisoformat(data_str)
                        except (ValueError, TypeError):
                            data_dt = datetime.now()

                        votacao = Votacao(
                            id_externo=vot_id_externo,
                            proposicao_id=proposicao.id,
                            casa="camara",
                            data=data_dt,
                            descricao=best_votacao.get("descricao"),
                            resultado=str(best_votacao.get("aprovacao", ""))
                            if best_votacao.get("aprovacao") is not None
                            else None,
                            total_sim=sim,
                            total_nao=nao,
                            total_abstencao=abst,
                            dados_brutos=best_votacao,
                        )
                        db.add(votacao)
                        await db.flush()

                        # Save individual votes
                        for vr in best_votos:
                            dep = vr.get("deputado_", {})
                            parl_ext = f"camara_{dep.get('id', '')}"
                            parl_db_id = parl_mapping.get(parl_ext)
                            if not parl_db_id:
                                continue

                            voto_str = {
                                "Sim": "sim",
                                "Não": "nao",
                                "Abstenção": "abstencao",
                                "Obstrução": "obstrucao",
                            }.get(vr.get("tipoVoto", ""), "ausente")

                            db.add(
                                VotoParlamentar(
                                    votacao_id=votacao.id,
                                    parlamentar_id=parl_db_id,
                                    voto=voto_str,
                                    partido_na_epoca=dep.get("siglaPartido"),
                                )
                            )

                    found += 1
                    logger.info(
                        f"  [{found}/{target}] {tipo} {prop_raw.get('numero', '?')}/{ano} "
                        f"({sim} sim / {nao} nao, div={round(best_divisiveness * 100, 1)}%) "
                        f"topics={[t.slug for t in topics[:3]]}"
                    )
                    await db.commit()

        logger.info(f"Done! Imported {found} divisive proposições")


if __name__ == "__main__":
    asyncio.set_event_loop_policy(None)
    asyncio.run(find_and_import_divisive_votes())
