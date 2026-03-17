#!/bin/bash
# Wait for both rewrite jobs, merge results, and apply to production DB.
set -e

RAW_FILE="/tmp/proposicoes_reescritas.json"
IMPROVE_FILE="/tmp/proposicoes_melhoradas.json"
MERGED_FILE="/tmp/proposicoes_todas_reescritas.json"
SERVER="ec2-user@44.216.159.100"
SSH_KEY="$HOME/.ssh/votovc_deploy"

echo "=== Waiting for rewrite jobs to finish ==="

# Wait for raw rewrites (PID passed as $1)
if [ -n "$1" ]; then
    echo "Waiting for raw rewrites (PID $1)..."
    while kill -0 "$1" 2>/dev/null; do sleep 30; done
    echo "Raw rewrites done."
fi

# Wait for improvement rewrites (PID passed as $2)
if [ -n "$2" ]; then
    echo "Waiting for improvement rewrites (PID $2)..."
    while kill -0 "$2" 2>/dev/null; do sleep 30; done
    echo "Improvement rewrites done."
fi

echo ""
echo "=== Merging results ==="
python3 -c "
import json

merged = {}

for f in ['$RAW_FILE', '$IMPROVE_FILE']:
    try:
        with open(f) as fh:
            for item in json.load(fh):
                if item.get('novo_titulo'):
                    merged[item['id']] = item
    except FileNotFoundError:
        print(f'  Skipping {f} (not found)')

items = list(merged.values())
with open('$MERGED_FILE', 'w') as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f'  Merged: {len(items)} proposições')
"

echo ""
echo "=== Generating SQL ==="
python3 -c "
import json

with open('$MERGED_FILE') as f:
    items = json.load(f)

sql_lines = []
for item in items:
    titulo = item['novo_titulo'].replace(\"'\", \"''\")
    descricao = item['nova_descricao'].replace(\"'\", \"''\") if item.get('nova_descricao') else ''
    pid = item['id']
    if descricao:
        sql_lines.append(f\"UPDATE proposicoes SET resumo_cidadao = '{titulo}', descricao_detalhada = '{descricao}' WHERE id = {pid};\")
    else:
        sql_lines.append(f\"UPDATE proposicoes SET resumo_cidadao = '{titulo}' WHERE id = {pid};\")

with open('/tmp/update_proposicoes.sql', 'w') as f:
    f.write('BEGIN;\n')
    for line in sql_lines:
        f.write(line + '\n')
    f.write('COMMIT;\n')

print(f'  Generated {len(sql_lines)} UPDATE statements')
"

echo ""
echo "=== Uploading SQL to production ==="
scp -i "$SSH_KEY" /tmp/update_proposicoes.sql "$SERVER":/tmp/update_proposicoes.sql

echo ""
echo "=== Applying to production DB ==="
ssh -i "$SSH_KEY" "$SERVER" 'docker exec -i votovc-db-1 psql -U votovc -d votovc < /tmp/update_proposicoes.sql'

echo ""
echo "=== Done! ==="
ssh -i "$SSH_KEY" "$SERVER" "docker exec votovc-db-1 psql -U votovc -d votovc -t -c \"
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE resumo_cidadao != ementa) AS custom
FROM proposicoes
WHERE resumo_cidadao IS NOT NULL
  AND relevancia_score IS NOT NULL
  AND tipo IN ('PL','PEC','MPV','PLP','PDL','MIP');
\""
