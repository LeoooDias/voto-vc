"""Export remaining substantive proposições (100+ votes, no resumo) for processing."""
import asyncio
import json

from app.database import async_session
from sqlalchemy import text


async def export():
    async with async_session() as db:
        r = await db.execute(text("""
            WITH prop_votos AS (
                SELECT
                    p.id, p.tipo, p.numero, p.ano, p.ementa,
                    SUM(CASE WHEN vp.voto = 'SIM' THEN 1 ELSE 0 END) as sim,
                    SUM(CASE WHEN vp.voto = 'NAO' THEN 1 ELSE 0 END) as nao,
                    count(vp.id) as total_votos
                FROM proposicoes p
                JOIN votacoes v ON v.proposicao_id = p.id
                JOIN votos_parlamentares vp ON vp.votacao_id = v.id
                WHERE p.tipo IN ('PL','PEC','MPV','PLP','PDL','MIP','PLC','PLV','PLS')
                AND p.resumo_cidadao IS NULL
                GROUP BY p.id
                HAVING count(vp.id) >= 100
            )
            SELECT id, tipo, numero, ano, sim, nao, total_votos,
                   ROUND(LEAST(sim, nao)::numeric / NULLIF(sim + nao, 0) * 200, 1) as divisiveness,
                   ementa
            FROM prop_votos
            ORDER BY divisiveness DESC, total_votos DESC
        """))
        rows = r.all()
        items = []
        for row in rows:
            items.append({
                "id": row[0],
                "tipo": row[1],
                "numero": row[2],
                "ano": row[3],
                "sim": row[4],
                "nao": row[5],
                "total_votos": row[6],
                "margem_pct": float(row[7]) if row[7] else 0,
                "ementa": row[8],
            })
        with open("/tmp/proposicoes_restantes.json", "w") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"Exported {len(items)} proposições to /tmp/proposicoes_restantes.json")


asyncio.run(export())
