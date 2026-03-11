"""Inventory of proposições and what's left to process."""
import asyncio
from app.database import async_session
from sqlalchemy import text

TIPOS_CLAUSE = "('PL','PEC','MPV','PLP','PDL','MIP','PLC','PLV','PLS')"

async def inventory():
    async with async_session() as db:
        r = await db.execute(text("SELECT COUNT(*) FROM proposicoes"))
        print(f"Total proposições no banco: {r.scalar()}")

        r = await db.execute(text("SELECT tipo, COUNT(*) as n FROM proposicoes GROUP BY tipo ORDER BY n DESC"))
        print(f"\nPor tipo:")
        for row in r.all():
            print(f"  {row[0] or '(vazio)':10s} {row[1]:>5d}")

        r = await db.execute(text(f"""
            WITH prop_votos AS (
                SELECT p.id, p.tipo, p.numero, p.ano, p.ementa,
                    p.resumo_cidadao IS NOT NULL as tem_resumo,
                    SUM(CASE WHEN vp.voto = 'SIM' THEN 1 ELSE 0 END) as sim,
                    SUM(CASE WHEN vp.voto = 'NAO' THEN 1 ELSE 0 END) as nao,
                    COUNT(vp.id) as total_votos
                FROM proposicoes p
                JOIN votacoes v ON v.proposicao_id = p.id
                JOIN votos_parlamentares vp ON vp.votacao_id = v.id
                WHERE p.tipo IN {TIPOS_CLAUSE}
                GROUP BY p.id
            )
            SELECT
                CASE
                    WHEN total_votos >= 200 THEN '200+ votos'
                    WHEN total_votos >= 100 THEN '100-199 votos'
                    WHEN total_votos >= 50  THEN '50-99 votos'
                    WHEN total_votos >= 20  THEN '20-49 votos'
                    ELSE '<20 votos'
                END as faixa,
                COUNT(*) as total,
                SUM(CASE WHEN tem_resumo THEN 1 ELSE 0 END) as com_resumo,
                SUM(CASE WHEN NOT tem_resumo THEN 1 ELSE 0 END) as sem_resumo
            FROM prop_votos
            GROUP BY 1
            ORDER BY MIN(total_votos) DESC
        """))
        print(f"\nSubstantivas com votação nominal, por faixa de votos:")
        print(f"  {'Faixa':20s} {'Total':>6s} {'C/resumo':>9s} {'S/resumo':>9s}")
        for row in r.all():
            print(f"  {row[0]:20s} {row[1]:>6d} {row[2]:>9d} {row[3]:>9d}")

        r = await db.execute(text(f"""
            WITH prop_votos AS (
                SELECT p.id, p.tipo, p.numero, p.ano, p.ementa,
                    SUM(CASE WHEN vp.voto = 'SIM' THEN 1 ELSE 0 END) as sim,
                    SUM(CASE WHEN vp.voto = 'NAO' THEN 1 ELSE 0 END) as nao,
                    COUNT(vp.id) as total_votos
                FROM proposicoes p
                JOIN votacoes v ON v.proposicao_id = p.id
                JOIN votos_parlamentares vp ON vp.votacao_id = v.id
                WHERE p.tipo IN {TIPOS_CLAUSE}
                AND p.resumo_cidadao IS NULL
                GROUP BY p.id
                HAVING COUNT(vp.id) >= 100
            )
            SELECT tipo, numero, ano, sim, nao, total_votos,
                   ROUND(LEAST(sim,nao)::numeric / NULLIF(sim+nao,0) * 200, 1) as divisiveness,
                   LEFT(ementa, 120) as ementa
            FROM prop_votos
            ORDER BY divisiveness DESC, total_votos DESC
            LIMIT 30
        """))
        rows = r.all()
        print(f"\nTop 30 sem resumo, mais divisivas (100+ votos):")
        for row in rows:
            div = f"{row[6]}%" if row[6] is not None else "  N/A"
            print(f"  [{div:>6}] {row[0]} {row[1]}/{row[2]} ({row[3]}x{row[4]}, {row[5]} votos)")
            print(f"         {row[7]}")

        r = await db.execute(text(f"""
            SELECT COUNT(*) FROM (
                SELECT p.id
                FROM proposicoes p
                JOIN votacoes v ON v.proposicao_id = p.id
                JOIN votos_parlamentares vp ON vp.votacao_id = v.id
                WHERE p.tipo IN {TIPOS_CLAUSE}
                AND p.resumo_cidadao IS NULL
                GROUP BY p.id
                HAVING COUNT(vp.id) >= 100
            ) x
        """))
        print(f"\nTotal sem resumo com 100+ votos: {r.scalar()}")

        r = await db.execute(text(f"""
            SELECT COUNT(*) FROM proposicoes p
            WHERE p.tipo IN {TIPOS_CLAUSE}
            AND NOT EXISTS (SELECT 1 FROM votacoes v WHERE v.proposicao_id = p.id)
        """))
        print(f"Substantivas sem votação linkada: {r.scalar()}")

        r = await db.execute(text("SELECT COUNT(*) FROM votacoes WHERE proposicao_id IS NULL"))
        print(f"Votações sem proposição linkada: {r.scalar()}")

asyncio.run(inventory())
