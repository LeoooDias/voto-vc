"""Export top divisive proposições to JSON for AI summarization."""
import asyncio
import json

from sqlalchemy import text

from app.database import async_session


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
                GROUP BY p.id
                HAVING count(vp.id) >= 100
            )
            SELECT id, tipo, numero, ano, sim, nao, total_votos,
                   ROUND(ABS(sim - nao)::numeric / NULLIF(sim + nao, 0) * 100, 1) as margem_pct,
                   ementa
            FROM prop_votos
            ORDER BY margem_pct ASC, total_votos DESC
            LIMIT 150
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
        with open("/tmp/proposicoes_divisivas.json", "w") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(items)} proposições to /tmp/proposicoes_divisivas.json")

        # Also print a summary
        print(f"\nTop 20 mais divididas:")
        for i, item in enumerate(items[:20]):
            print(
                f"  {i+1:>2}. [{item['margem_pct']:>5}%] "
                f"{item['tipo']} {item['numero']}/{item['ano']} "
                f"({item['sim']}×{item['nao']}) "
                f"{item['ementa'][:100]}"
            )


asyncio.set_event_loop_policy(None)
asyncio.run(export())
