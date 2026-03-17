"""Bulk import from downloaded Câmara JSON files.

Reads from ~/Downloads/camara-json/ directory (dadosabertos.camara.leg.br bulk files).
Much faster than API-based import — processes all data locally.

Usage:
    python -m app.ingestion.bulk_import [--start-year 2003] [--end-year 2026] [--data-dir PATH]
"""

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.classification.classifier import classify_proposicao
from app.database import async_session
from app.ingestion.constants import PARTIDO_NOMES
from app.models.parlamentar import Parlamentar
from app.models.partido import Partido
from app.models.proposicao import Proposicao
from app.models.topico import ProposicaoTopico, Topico
from app.models.votacao import Votacao, VotoParlamentar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = os.path.expanduser("~/Downloads/camara-json")

VOTO_MAP = {
    "Sim": "sim",
    "Não": "nao",
    "Abstenção": "abstencao",
    "Obstrução": "obstrucao",
    "Art. 17": "presente_sem_voto",
    "-": "ausente",
}

SUBSTANTIVE_TYPES = {"PL", "PEC", "MPV", "PLP", "PDL", "PLC", "MIP", "PLV", "PLS"}


def load_json(path: str) -> list[dict]:
    """Load a JSON file, returning the 'dados' array."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return []
    with open(path) as f:
        return json.load(f).get("dados", [])


async def import_deputados(db: AsyncSession, data_dir: str) -> dict[str, int]:
    """Import all historical deputados. Returns id_externo -> db_id mapping."""
    path = os.path.join(data_dir, "deputados.json")
    deps = load_json(path)
    if not deps:
        logger.warning("No deputados.json found")
        return {}

    # Load existing
    result = await db.execute(select(Parlamentar.id_externo, Parlamentar.id))
    mapping = {row[0]: row[1] for row in result.all()}
    logger.info(f"Existing parlamentares: {len(mapping)}")

    # Ensure partidos exist
    result = await db.execute(select(Partido.sigla, Partido.id))
    {row[0]: row[1] for row in result.all()}

    created = 0
    for dep in deps:
        uri = dep.get("uri", "")
        dep_id = uri.rstrip("/").split("/")[-1] if "/deputados/" in uri else None
        if not dep_id:
            continue

        id_ext = f"camara_{dep_id}"
        if id_ext in mapping:
            continue

        nome = dep.get("nomeCivil") or dep.get("nome", "")
        if not nome:
            continue

        parlamentar = Parlamentar(
            id_externo=id_ext,
            casa="camara",
            nome_civil=dep.get("nomeCivil", dep.get("nome", "")),
            nome_parlamentar=dep.get("nome", dep.get("nomeCivil", "")),
            sexo=dep.get("siglaSexo"),
            uf=dep.get("ufNascimento", ""),
            legislatura_atual=(dep.get("idLegislaturaFinal", 0) == 57),
        )
        db.add(parlamentar)
        await db.flush()
        mapping[id_ext] = parlamentar.id
        created += 1

        if created % 500 == 0:
            await db.commit()
            logger.info(f"  Created {created} parlamentares...")

    await db.commit()
    logger.info(f"Deputados: {created} created, {len(mapping)} total")
    return mapping


async def import_year(
    db: AsyncSession,
    ano: int,
    data_dir: str,
    parl_mapping: dict[str, int],
    topico_mapping: dict[str, int],
    existing_vot_ids: set[str],
    existing_prop_ids: set[str],
):
    """Import all data for a single year from JSON files."""
    logger.info(f"\n{'=' * 60}")
    logger.info(f"IMPORTING {ano}")

    # Load files
    votacoes_raw = load_json(os.path.join(data_dir, f"votacoes-{ano}.json"))
    votos_raw = load_json(os.path.join(data_dir, f"votacoesVotos-{ano}.json"))
    links_raw = load_json(os.path.join(data_dir, f"votacoesProposicoes-{ano}.json"))
    props_raw = load_json(os.path.join(data_dir, f"proposicoes-{ano}.json"))

    logger.info(
        f"  Files: {len(votacoes_raw)} votações, {len(votos_raw)} votos, "
        f"{len(links_raw)} links, {len(props_raw)} proposições"
    )

    # Index proposições by id for quick lookup
    props_by_id = {p["id"]: p for p in props_raw if p.get("id")}

    # Index votos by votação id
    votos_by_votacao: dict[str, list[dict]] = {}
    for v in votos_raw:
        vid = v.get("idVotacao", "")
        votos_by_votacao.setdefault(vid, []).append(v)

    # Index links: votação id -> list of proposição records
    links_by_votacao: dict[str, list[dict]] = {}
    for link in links_raw:
        vid = link.get("idVotacao", "")
        links_by_votacao.setdefault(vid, []).append(link)

    # Ensure partidos exist
    result = await db.execute(select(Partido.sigla, Partido.id))
    partido_map = {row[0]: row[1] for row in result.all()}

    imported_vot = 0
    imported_votos = 0
    imported_props = 0
    skipped = 0

    for vot in votacoes_raw:
        vot_api_id = str(vot.get("id", ""))
        id_externo = f"camara_{vot_api_id}"

        if id_externo in existing_vot_ids:
            skipped += 1
            continue

        # Check if this votação has individual votes
        individual_votos = votos_by_votacao.get(vot_api_id, [])
        if len(individual_votos) < 50:
            continue

        # Count votes
        sim = sum(1 for v in individual_votos if v.get("voto") == "Sim")
        nao = sum(1 for v in individual_votos if v.get("voto") == "Não")
        abst = sum(1 for v in individual_votos if v.get("voto") == "Abstenção")

        # Find linked proposição
        proposicao_id = None
        prop_links = links_by_votacao.get(vot_api_id, [])

        for link in prop_links:
            prop_data = link.get("proposicao_", {})
            prop_api_id = prop_data.get("id")
            if not prop_api_id:
                continue

            prop_id_ext = f"camara_prop_{prop_api_id}"

            if prop_id_ext in existing_prop_ids:
                # Look up DB id
                result = await db.execute(
                    select(Proposicao.id).where(Proposicao.id_externo == prop_id_ext)
                )
                row = result.one_or_none()
                if row:
                    proposicao_id = row[0]
                    break
                continue

            # Create proposição from bulk data
            full_prop = props_by_id.get(prop_api_id, {})
            ementa = full_prop.get("ementa") or prop_data.get("ementa", "")
            tipo = full_prop.get("siglaTipo") or ""
            numero = full_prop.get("numero", 0)
            prop_ano = full_prop.get("ano", ano)

            if not ementa:
                continue

            # Also check tipo_numero_ano format
            alt_id = f"camara_prop_{tipo}_{numero}_{prop_ano}"
            if alt_id in existing_prop_ids:
                result = await db.execute(
                    select(Proposicao.id).where(Proposicao.id_externo == alt_id)
                )
                row = result.one_or_none()
                if row:
                    proposicao_id = row[0]
                    existing_prop_ids.add(prop_id_ext)
                    break
                continue

            # Classify and create
            topics = classify_proposicao(ementa, tipo)
            total = sim + nao
            relevancia = round(min(sim, nao) / total * 2, 3) if total > 0 else 0

            situacao = None
            status = full_prop.get("ultimoStatus") or {}
            if isinstance(status, dict):
                situacao = status.get("descricaoSituacao")

            proposicao = Proposicao(
                id_externo=prop_id_ext,
                casa_origem="camara",
                tipo=tipo,
                numero=numero,
                ano=prop_ano,
                ementa=ementa,
                ementa_simplificada=ementa[:200] if len(ementa) > 200 else None,
                resumo_cidadao=ementa,
                url_inteiro_teor=full_prop.get("urlInteiroTeor"),
                situacao=situacao,
                relevancia_score=relevancia,
                dados_brutos=full_prop or None,
            )
            db.add(proposicao)
            await db.flush()
            existing_prop_ids.add(prop_id_ext)
            proposicao_id = proposicao.id
            imported_props += 1

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
            break

        # Create votação
        data_str = vot.get("dataHoraRegistro") or vot.get("data", "")
        try:
            data_dt = datetime.fromisoformat(data_str)
        except (ValueError, TypeError):
            data_dt = datetime(ano, 1, 1)

        votacao = Votacao(
            id_externo=id_externo,
            proposicao_id=proposicao_id,
            casa="camara",
            data=data_dt,
            descricao=vot.get("descricao"),
            resultado=str(vot.get("aprovacao", "")) if vot.get("aprovacao") is not None else None,
            total_sim=vot.get("votosSim") or sim,
            total_nao=vot.get("votosNao") or nao,
            total_abstencao=abst,
        )
        db.add(votacao)
        await db.flush()
        existing_vot_ids.add(id_externo)

        # Save individual votes
        for vr in individual_votos:
            dep = vr.get("deputado_", {})
            dep_id = dep.get("id") or ""
            if not dep_id:
                # Try extracting from uri
                uri = dep.get("uri", "")
                if "/deputados/" in uri:
                    dep_id = uri.rstrip("/").split("/")[-1]
            if not dep_id:
                continue

            parl_ext = f"camara_{dep_id}"
            parl_db_id = parl_mapping.get(parl_ext)

            if not parl_db_id:
                # Create on the fly
                nome = dep.get("nome", "")
                if not nome:
                    continue

                sigla = dep.get("siglaPartido", "")
                partido_id = None
                if sigla:
                    if sigla not in partido_map:
                        partido = Partido(sigla=sigla, nome=PARTIDO_NOMES.get(sigla, sigla))
                        db.add(partido)
                        await db.flush()
                        partido_map[sigla] = partido.id
                    partido_id = partido_map[sigla]

                parlamentar = Parlamentar(
                    id_externo=parl_ext,
                    casa="camara",
                    nome_civil=nome,
                    nome_parlamentar=nome,
                    uf=dep.get("siglaUf", ""),
                    foto_url=dep.get("urlFoto"),
                    partido_id=partido_id,
                    legislatura_atual=False,
                )
                db.add(parlamentar)
                await db.flush()
                parl_mapping[parl_ext] = parlamentar.id
                parl_db_id = parlamentar.id

            voto_str = VOTO_MAP.get(vr.get("voto", ""), "ausente")
            db.add(
                VotoParlamentar(
                    votacao_id=votacao.id,
                    parlamentar_id=parl_db_id,
                    voto=voto_str,
                    partido_na_epoca=dep.get("siglaPartido"),
                )
            )
            imported_votos += 1

        imported_vot += 1

        if imported_vot % 50 == 0:
            await db.commit()
            logger.info(
                f"  [{imported_vot} votações, {imported_votos} votos, {imported_props} props] "
                f"prop={'yes' if proposicao_id else 'no'}"
            )

    await db.commit()
    logger.info(
        f"  Year {ano} done: {imported_vot} votações, {imported_votos} votos, "
        f"{imported_props} proposições ({skipped} skipped)"
    )
    return imported_vot, imported_votos, imported_props


async def bulk_import(
    start_year: int = 2003, end_year: int = 2026, data_dir: str = DEFAULT_DATA_DIR
):
    """Import all years from bulk JSON files."""
    logger.info(f"Bulk import from {data_dir}, years {start_year}-{end_year}")

    async with async_session() as db:
        # Import deputados first
        parl_mapping = await import_deputados(db, data_dir)

        # Load topic mapping
        topico_mapping = {}
        result = await db.execute(select(Topico))
        for t in result.scalars().all():
            topico_mapping[t.slug] = t.id
        logger.info(f"Loaded {len(topico_mapping)} topics")

        # Load existing IDs
        result = await db.execute(select(Votacao.id_externo))
        existing_vot_ids = {row[0] for row in result.all()}
        logger.info(f"Existing votações: {len(existing_vot_ids)}")

        result = await db.execute(select(Proposicao.id_externo))
        existing_prop_ids = {row[0] for row in result.all()}
        logger.info(f"Existing proposições: {len(existing_prop_ids)}")

        total_vot = total_votos = total_props = 0

        for ano in range(start_year, end_year + 1):
            v, vo, p = await import_year(
                db,
                ano,
                data_dir,
                parl_mapping,
                topico_mapping,
                existing_vot_ids,
                existing_prop_ids,
            )
            total_vot += v
            total_votos += vo
            total_props += p

        logger.info(f"\n{'=' * 60}")
        logger.info(
            f"BULK IMPORT COMPLETE: {total_vot} votações, "
            f"{total_votos} votos, {total_props} proposições"
        )


def main():
    parser = argparse.ArgumentParser(description="Bulk import from Câmara JSON files")
    parser.add_argument("--start-year", type=int, default=2003)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    args = parser.parse_args()

    asyncio.set_event_loop_policy(None)
    asyncio.run(bulk_import(args.start_year, args.end_year, args.data_dir))


if __name__ == "__main__":
    main()
