#!/bin/bash
cd "$(dirname "$0")"
PYTHONPATH=. python3 -m uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import async_session
async def c():
    async with async_session() as db:
        for q,l in [
            ('SELECT count(*) FROM votacoes','Votacoes'),
            ('SELECT count(*) FROM votos_parlamentares','Votos individuais'),
            ('SELECT count(*) FROM parlamentares','Parlamentares'),
            ('SELECT count(*) FROM votacoes WHERE proposicao_id IS NOT NULL','Com proposicao'),
            ('SELECT count(*) FROM votacoes WHERE proposicao_id IS NULL','Sem proposicao'),
        ]:
            r = await db.execute(text(q)); print(f'{l}: {r.scalar()}')
asyncio.set_event_loop_policy(None)
asyncio.run(c())
" 2>&1 | grep -v -E '(warning|sqlalchemy)'
