#!/bin/bash
set -euo pipefail

BACKUP_DIR="${1:-/opt/votovc/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="votovc_${TIMESTAMP}.sql.gz"
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting database backup..."

docker exec votovc-db-1 pg_dump -U votovc votovc | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

echo "[$(date)] Backup created: ${BACKUP_DIR}/${BACKUP_FILE} ($(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1))"

echo "[$(date)] Removing backups older than ${KEEP_DAYS} days..."
find "$BACKUP_DIR" -name "votovc_*.sql.gz" -type f -mtime +${KEEP_DAYS} -print -delete

echo "[$(date)] Backup complete."
