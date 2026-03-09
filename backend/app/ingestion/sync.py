"""Orchestrates data ingestion from Câmara and Senado APIs."""

import argparse
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.ingestion.camara import CamaraClient
from app.ingestion.normalize import normalize_deputado, normalize_senador
from app.ingestion.senado import SenadoClient
from app.models.parlamentar import Parlamentar
from app.models.partido import Partido

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def sync_partidos(db: AsyncSession, parlamentares_data: list[dict]) -> dict[str, int]:
    """Ensure all partidos exist and return sigla->id mapping."""
    siglas = {p.get("partido_sigla", "") for p in parlamentares_data if p.get("partido_sigla")}
    mapping = {}

    for sigla in siglas:
        result = await db.execute(select(Partido).where(Partido.sigla == sigla))
        partido = result.scalar_one_or_none()
        if not partido:
            partido = Partido(sigla=sigla, nome=sigla)
            db.add(partido)
            await db.flush()
        mapping[sigla] = partido.id

    return mapping


async def sync_parlamentares(db: AsyncSession, parlamentares_data: list[dict]):
    """Upsert parlamentares."""
    partido_mapping = await sync_partidos(db, parlamentares_data)

    for data in parlamentares_data:
        result = await db.execute(
            select(Parlamentar).where(Parlamentar.id_externo == data["id_externo"])
        )
        parlamentar = result.scalar_one_or_none()

        partido_id = partido_mapping.get(data.get("partido_sigla"))

        if parlamentar:
            parlamentar.nome_parlamentar = data["nome_parlamentar"]
            parlamentar.uf = data["uf"]
            parlamentar.partido_id = partido_id
            parlamentar.foto_url = data.get("foto_url")
            parlamentar.dados_brutos = data.get("dados_brutos")
        else:
            parlamentar = Parlamentar(
                id_externo=data["id_externo"],
                casa=data["casa"],
                nome_civil=data["nome_civil"],
                nome_parlamentar=data["nome_parlamentar"],
                cpf=data.get("cpf"),
                sexo=data.get("sexo"),
                uf=data["uf"],
                foto_url=data.get("foto_url"),
                email=data.get("email"),
                partido_id=partido_id,
                legislatura_atual=data.get("legislatura_atual", False),
                dados_brutos=data.get("dados_brutos"),
            )
            db.add(parlamentar)

    await db.commit()


async def run_full_sync():
    """Full sync: fetch all current parlamentares from both houses."""
    logger.info("Starting full sync...")

    camara = CamaraClient()
    senado = SenadoClient()

    try:
        # Fetch deputados
        logger.info("Fetching deputados from Câmara...")
        deputados_raw = await camara.fetch_deputados()
        deputados = [normalize_deputado(d) for d in deputados_raw]
        logger.info(f"Fetched {len(deputados)} deputados")

        # Fetch senadores
        logger.info("Fetching senadores from Senado...")
        senadores_raw = await senado.fetch_senadores()
        senadores = [normalize_senador(s) for s in senadores_raw]
        logger.info(f"Fetched {len(senadores)} senadores")

        # Save to DB
        async with async_session() as db:
            await sync_parlamentares(db, deputados + senadores)
            logger.info("Parlamentares synced successfully")

    finally:
        await camara.close()
        await senado.close()


async def run_incremental_sync():
    """Incremental sync: recent votações only."""
    logger.info("Incremental sync not yet implemented — running full sync")
    await run_full_sync()


def main():
    parser = argparse.ArgumentParser(description="Sync legislative data")
    parser.add_argument("--full", action="store_true", help="Full sync")
    parser.add_argument("--incremental", action="store_true", help="Incremental sync")
    args = parser.parse_args()

    if args.full:
        asyncio.run(run_full_sync())
    elif args.incremental:
        asyncio.run(run_incremental_sync())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
