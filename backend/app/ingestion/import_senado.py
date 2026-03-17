"""Bulk import of Senado Federal voting data.

Fetches votações nominais from the Senado's new API (/votacao?ano=),
links them to existing proposições via (tipo, numero, ano), and creates
VotoParlamentar records for each senator's vote.

Imports historical senators from legislatures 52-57 (2003-2027) to ensure
all voters are in the DB.

Usage:
    python -m app.ingestion.import_senado [--start-year 2003] [--end-year 2026]
"""

import argparse
import asyncio
import logging
from datetime import datetime

from sqlalchemy import select

from app.classification.classifier import classify_proposicao
from app.database import async_session
from app.ingestion.constants import PARTIDO_NOMES
from app.ingestion.normalize import (
    normalize_senador,
    normalize_votacao_senado,
    normalize_voto_senado,
)
from app.ingestion.senado import SenadoClient
from app.ingestion.sync import compute_relevancia, ensure_topicos, sync_partidos
from app.models.parlamentar import Parlamentar
from app.models.partido import Partido
from app.models.proposicao import Proposicao
from app.models.topico import ProposicaoTopico
from app.models.votacao import Votacao, VotoParlamentar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

SUBSTANTIVE_TYPES = {"PL", "PEC", "MPV", "PLP", "PDL"}

# Legislaturas que cobrem 2003-2027
LEGISLATURAS_HISTORICAS = [52, 53, 54, 55, 56, 57]


async def import_senadores_historicos(db, senado: SenadoClient, parl_map: dict[str, int]) -> int:
    """Import senators from historical legislatures (52-57)."""
    created = 0
    for leg in LEGISLATURAS_HISTORICAS:
        logger.info(f"Fetching senadores da legislatura {leg}...")
        try:
            senadores_raw = await senado.fetch_senadores(legislatura=leg)
        except Exception as e:
            logger.warning(f"Failed to fetch legislatura {leg}: {e}")
            continue

        senadores_data = [normalize_senador(s) for s in senadores_raw]
        logger.info(f"  Legislatura {leg}: {len(senadores_data)} senadores")

        # Ensure partidos exist
        partido_mapping = await sync_partidos(db, senadores_data)

        for data in senadores_data:
            id_ext = data["id_externo"]
            if id_ext in parl_map:
                continue

            partido_id = partido_mapping.get(data.get("partido_sigla"))

            parlamentar = Parlamentar(
                id_externo=id_ext,
                casa="senado",
                nome_civil=data["nome_civil"],
                nome_parlamentar=data["nome_parlamentar"],
                sexo=data.get("sexo"),
                uf=data["uf"],
                foto_url=data.get("foto_url"),
                email=data.get("email"),
                partido_id=partido_id,
                legislatura_atual=(leg == 57),
                dados_brutos=data.get("dados_brutos"),
            )
            db.add(parlamentar)
            await db.flush()
            parl_map[id_ext] = parlamentar.id
            created += 1

        await db.commit()

    logger.info(f"Historical senators: {created} created, {len(parl_map)} total parlamentares")
    return created


async def ensure_senador(
    db, voto_raw: dict, parl_map: dict[str, int], partido_map: dict[str, int]
) -> int | None:
    """Create a senator on-the-fly from vote data (for suplentes etc)."""
    codigo = voto_raw.get("codigoParlamentar")
    if not codigo:
        return None

    id_ext = f"senado_{codigo}"

    # Double-check DB
    result = await db.execute(select(Parlamentar.id).where(Parlamentar.id_externo == id_ext))
    existing = result.one_or_none()
    if existing:
        parl_map[id_ext] = existing[0]
        return existing[0]

    nome = voto_raw.get("nomeParlamentar", "")
    if not nome:
        return None

    # Ensure partido exists
    sigla = voto_raw.get("siglaPartidoParlamentar", "")
    partido_id = None
    if sigla:
        if sigla not in partido_map:
            result = await db.execute(select(Partido).where(Partido.sigla == sigla))
            partido = result.scalar_one_or_none()
            if not partido:
                partido = Partido(sigla=sigla, nome=PARTIDO_NOMES.get(sigla, sigla))
                db.add(partido)
                await db.flush()
            partido_map[sigla] = partido.id
        partido_id = partido_map[sigla]

    parlamentar = Parlamentar(
        id_externo=id_ext,
        casa="senado",
        nome_civil=nome,
        nome_parlamentar=nome,
        sexo=voto_raw.get("sexoParlamentar"),
        uf=voto_raw.get("siglaUFParlamentar", ""),
        partido_id=partido_id,
        legislatura_atual=False,
    )
    db.add(parlamentar)
    await db.flush()
    parl_map[id_ext] = parlamentar.id
    return parlamentar.id


async def import_senado(start_year: int = 2003, end_year: int = 2026):
    """Import Senado votações for a range of years."""
    logger.info(f"Senado import: years {start_year}-{end_year}")

    senado = SenadoClient()

    try:
        async with async_session() as db:
            # Pre-load parlamentar mapping
            result = await db.execute(select(Parlamentar.id_externo, Parlamentar.id))
            parl_map = {row[0]: row[1] for row in result.all()}
            logger.info(f"Loaded {len(parl_map)} parlamentares")

            # Import historical senators (52ª-57ª legislaturas)
            logger.info("Importing historical senators...")
            await import_senadores_historicos(db, senado, parl_map)

            # Pre-load partido mapping for on-the-fly creation
            result = await db.execute(select(Partido.sigla, Partido.id))
            partido_map = {row[0]: row[1] for row in result.all()}

            # Proposição lookup by (tipo, numero, ano)
            result = await db.execute(
                select(Proposicao.id, Proposicao.tipo, Proposicao.numero, Proposicao.ano)
            )
            prop_map: dict[tuple[str, str, str], int] = {}
            for row in result.all():
                key = (str(row[1]).upper(), str(row[2]), str(row[3]))
                prop_map[key] = row[0]
            logger.info(f"Loaded {len(prop_map)} proposições for linkage")

            # Existing votação id_externos
            result = await db.execute(select(Votacao.id_externo))
            existing_vot_ids = {row[0] for row in result.all()}

            # Existing proposição id_externos (to avoid duplicates)
            result = await db.execute(select(Proposicao.id_externo))
            existing_prop_ids = {row[0] for row in result.all()}

            topico_mapping = await ensure_topicos(db)

            total_vot = 0
            total_votos = 0
            total_props_created = 0
            total_linked = 0
            total_skipped = 0
            total_created_onthefly = 0

            for ano in range(start_year, end_year + 1):
                logger.info(f"\n{'=' * 50}")
                logger.info(f"Fetching Senado votações for {ano}...")
                try:
                    votacoes_raw = await senado.fetch_votacoes_ano(ano)
                except Exception as e:
                    logger.warning(f"Failed to fetch votações for {ano}: {e}")
                    continue
                logger.info(f"Found {len(votacoes_raw)} votações in {ano}")

                year_vot = 0
                year_votos = 0

                for raw in votacoes_raw:
                    # Filter: only substantive, non-secret votações
                    sigla = raw.get("sigla", "")
                    if sigla not in SUBSTANTIVE_TYPES:
                        continue
                    if raw.get("votacaoSecreta") == "S":
                        continue

                    vot_data = normalize_votacao_senado(raw)
                    id_externo = vot_data["id_externo"]

                    if id_externo in existing_vot_ids:
                        total_skipped += 1
                        continue

                    # Resolve proposição by (tipo, numero, ano)
                    proposicao_id = None
                    tipo = vot_data.get("sigla_tipo", "")
                    numero = vot_data.get("numero", "")
                    prop_ano = vot_data.get("ano", "")
                    prop_key = (str(tipo).upper(), str(numero), str(prop_ano))

                    if prop_key[0] and prop_key[1] and prop_key[2]:
                        proposicao_id = prop_map.get(prop_key)

                    if proposicao_id:
                        total_linked += 1
                    else:
                        # Create new proposição (Senado-originated)
                        codigo_materia = vot_data.get("codigo_materia")
                        if codigo_materia:
                            prop_id_ext = f"senado_mat_{codigo_materia}"
                            if prop_id_ext not in existing_prop_ids:
                                ementa = vot_data.get("ementa", "")
                                if ementa:
                                    topics = classify_proposicao(ementa, tipo)

                                    proposicao = Proposicao(
                                        id_externo=prop_id_ext,
                                        casa_origem="senado",
                                        tipo=tipo,
                                        numero=int(numero) if str(numero).isdigit() else 0,
                                        ano=int(prop_ano) if str(prop_ano).isdigit() else ano,
                                        ementa=ementa,
                                        ementa_simplificada=(
                                            ementa[:200] if len(ementa) > 200 else None
                                        ),
                                        resumo_cidadao=ementa,  # placeholder
                                    )
                                    db.add(proposicao)
                                    await db.flush()

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

                                    proposicao_id = proposicao.id
                                    existing_prop_ids.add(prop_id_ext)
                                    prop_map[prop_key] = proposicao.id
                                    total_props_created += 1
                            else:
                                # Proposição already exists by senado id_externo
                                result = await db.execute(
                                    select(Proposicao.id).where(
                                        Proposicao.id_externo == prop_id_ext
                                    )
                                )
                                row = result.one_or_none()
                                if row:
                                    proposicao_id = row[0]

                    # Parse datetime
                    data_str = vot_data.get("data")
                    try:
                        data_dt = (
                            datetime.fromisoformat(data_str) if data_str else datetime(ano, 1, 1)
                        )
                    except (ValueError, TypeError):
                        data_dt = datetime(ano, 1, 1)

                    # Create Votacao
                    votacao = Votacao(
                        id_externo=id_externo,
                        proposicao_id=proposicao_id,
                        casa="senado",
                        data=data_dt,
                        descricao=vot_data.get("descricao"),
                        resultado=vot_data.get("resultado"),
                        total_sim=vot_data.get("total_sim", 0) or 0,
                        total_nao=vot_data.get("total_nao", 0) or 0,
                        total_abstencao=vot_data.get("total_abstencao", 0) or 0,
                        dados_brutos=vot_data.get("dados_brutos"),
                    )
                    db.add(votacao)
                    await db.flush()
                    existing_vot_ids.add(id_externo)

                    # Process inline votes
                    votos_raw = raw.get("votos", [])
                    for vr in votos_raw:
                        voto_data = normalize_voto_senado(vr, id_externo)
                        parl_db_id = parl_map.get(voto_data["parlamentar_id_externo"])

                        if not parl_db_id:
                            # Create senator on-the-fly (suplente, etc)
                            parl_db_id = await ensure_senador(db, vr, parl_map, partido_map)
                            if parl_db_id:
                                total_created_onthefly += 1
                            else:
                                continue

                        db.add(
                            VotoParlamentar(
                                votacao_id=votacao.id,
                                parlamentar_id=parl_db_id,
                                voto=voto_data["voto"],
                                partido_na_epoca=voto_data.get("partido_na_epoca"),
                                dados_brutos=voto_data.get("dados_brutos"),
                            )
                        )
                        year_votos += 1

                    year_vot += 1
                    if year_vot % 10 == 0:
                        await db.commit()
                        logger.info(f"  [{ano}] {year_vot} votações, {year_votos} votos...")

                await db.commit()
                total_vot += year_vot
                total_votos += year_votos
                logger.info(f"  {ano} done: {year_vot} votações, {year_votos} votos")

            # Recompute relevância scores
            logger.info("Computing relevância scores...")
            await compute_relevancia(db)

            logger.info(f"\n{'=' * 50}")
            logger.info(
                f"SENADO IMPORT COMPLETE: {total_vot} votações, {total_votos} votos, "
                f"{total_props_created} novas proposições, {total_linked} vinculadas, "
                f"{total_skipped} já existentes, "
                f"{total_created_onthefly} senadores criados on-the-fly"
            )

    finally:
        await senado.close()


def main():
    parser = argparse.ArgumentParser(description="Import Senado Federal voting data")
    parser.add_argument("--start-year", type=int, default=2003)
    parser.add_argument("--end-year", type=int, default=2026)
    args = parser.parse_args()

    asyncio.set_event_loop_policy(None)
    asyncio.run(import_senado(args.start_year, args.end_year))


if __name__ == "__main__":
    main()
