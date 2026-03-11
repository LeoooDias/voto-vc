"""Normalize parlamentar names in the database to proper title case."""
import asyncio

from sqlalchemy import select, update
from app.database import async_session
from app.models.parlamentar import Parlamentar
from app.ingestion.normalize import normalize_nome


async def main():
    async with async_session() as db:
        result = await db.execute(select(Parlamentar))
        parlamentares = result.scalars().all()

        updated = 0
        for p in parlamentares:
            new_civil = normalize_nome(p.nome_civil)
            new_parl = normalize_nome(p.nome_parlamentar)

            if new_civil != p.nome_civil or new_parl != p.nome_parlamentar:
                await db.execute(
                    update(Parlamentar)
                    .where(Parlamentar.id == p.id)
                    .values(nome_civil=new_civil, nome_parlamentar=new_parl)
                )
                updated += 1
                if updated <= 10:
                    print(f"  {p.nome_parlamentar} -> {new_parl}")

        await db.commit()
        print(f"\nDone: {updated} names normalized out of {len(parlamentares)} total.")


if __name__ == "__main__":
    asyncio.run(main())
