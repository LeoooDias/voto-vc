#!/bin/bash
# Overnight import script - imports all historical Câmara votações and links them
# Run from backend directory with: bash run_overnight.sh

set -e
cd "$(dirname "$0")"
export PYTHONPATH=.

LOG=/tmp/votovc_overnight.log
echo "=== OVERNIGHT IMPORT STARTED $(date) ===" | tee $LOG

# Wait for any running import to finish
while pgrep -f "historical_import" > /dev/null 2>&1; do
    echo "$(date): Waiting for current 2020-2026 import to finish..." | tee -a $LOG
    sleep 60
done
echo "$(date): 2020-2026 import finished" | tee -a $LOG

# Phase 2: Import 2015-2019
echo "" | tee -a $LOG
echo "=== PHASE 2: 2015-2019 ===" | tee -a $LOG
python3 -m uv run python -m app.ingestion.historical_import --start-year 2015 --end-year 2019 2>&1 | tee -a $LOG

# Phase 3: Import 2010-2014
echo "" | tee -a $LOG
echo "=== PHASE 3: 2010-2014 ===" | tee -a $LOG
python3 -m uv run python -m app.ingestion.historical_import --start-year 2010 --end-year 2014 2>&1 | tee -a $LOG

# Phase 4: Import 2003-2009
echo "" | tee -a $LOG
echo "=== PHASE 4: 2003-2009 ===" | tee -a $LOG
python3 -m uv run python -m app.ingestion.historical_import --start-year 2003 --end-year 2009 2>&1 | tee -a $LOG

# Phase 5: Link all unlinked votações to proposições via API
echo "" | tee -a $LOG
echo "=== PHASE 5: LINKING VOTAÇÕES ===" | tee -a $LOG
python3 -m uv run python -m app.ingestion.link_unlinked 2>&1 | tee -a $LOG

# Phase 6: Final stats
echo "" | tee -a $LOG
echo "=== FINAL STATS ===" | tee -a $LOG
python3 -m uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import async_session
async def stats():
    async with async_session() as db:
        for q,l in [
            ('SELECT count(*) FROM parlamentares','Parlamentares'),
            ('SELECT count(*) FROM proposicoes','Proposicoes'),
            ('SELECT count(*) FROM votacoes','Votacoes'),
            ('SELECT count(*) FROM votos_parlamentares','Votos individuais'),
            ('SELECT count(*) FROM votacoes WHERE proposicao_id IS NOT NULL','Com proposicao'),
            ('SELECT count(*) FROM votacoes WHERE proposicao_id IS NULL','Sem proposicao'),
        ]:
            r = await db.execute(text(q)); print(f'{l}: {r.scalar()}')
        r = await db.execute(text('''
            SELECT EXTRACT(YEAR FROM data)::int as ano, count(*) as n
            FROM votacoes GROUP BY ano ORDER BY ano
        '''))
        print('Votacoes por ano:')
        for row in r.all(): print(f'  {row[0]}: {row[1]}')
asyncio.set_event_loop_policy(None)
asyncio.run(stats())
" 2>&1 | grep -v -E "(warning|sqlalchemy)" | tee -a $LOG

echo "" | tee -a $LOG
echo "=== OVERNIGHT IMPORT COMPLETED $(date) ===" | tee -a $LOG
