#!/bin/bash
# Daily database backup for all PlanBar customer databases.
#
# Environment:
#   PLANBAR_BASE  - Base deployment directory (default: /opt/planbar)
#
# Configure cron:
#   0 3 * * * PLANBAR_BASE=/opt/planbar /opt/planbar/scripts/backup.sh
#
# Optional: sync to S3-compatible storage via rclone:
#   30 3 * * * rclone sync /opt/planbar/backups/ remote:planbar-backups/

set -euo pipefail

BACKUP_DIR="${PLANBAR_BASE:-/opt/planbar}/backups"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d-%H%M)
LOG_FILE="${BACKUP_DIR}/backup-${DATE}.log"

mkdir -p "${BACKUP_DIR}"
exec 2>&1 > "${LOG_FILE}"

echo "[$(date)] Starting PlanBar backup..."

# Backup PlanBar databases
PLANBAR_DBS=$(docker exec db_planbar psql -U planbar -t -A -c \
    "SELECT datname FROM pg_database WHERE datname NOT IN ('postgres', 'template0', 'template1', 'planbar');")

for db in $PLANBAR_DBS; do
    if [ -n "$db" ]; then
        echo "Backing up PlanBar database: ${db}..."
        docker exec db_planbar pg_dump -U planbar -d "$db" \
            --format=custom \
            --compress=9 \
            --file="/tmp/${db}.dump"
        docker cp "db_planbar:/tmp/${db}.dump" "${BACKUP_DIR}/${db}-${DATE}.dump"
        docker exec db_planbar rm "/tmp/${db}.dump"
        echo "  -> ${BACKUP_DIR}/${db}-${DATE}.dump ($(du -h "${BACKUP_DIR}/${db}-${DATE}.dump" | cut -f1))"
    fi
done

# Backup TiTO databases
TITO_DBS=$(docker exec db_tito psql -U tito -t -A -c \
    "SELECT datname FROM pg_database WHERE datname NOT IN ('postgres', 'template0', 'template1', 'tito');")

for db in $TITO_DBS; do
    if [ -n "$db" ]; then
        echo "Backing up TiTO database: ${db}..."
        docker exec db_tito pg_dump -U tito -d "$db" \
            --format=custom \
            --compress=9 \
            --file="/tmp/${db}.dump"
        docker cp "db_tito:/tmp/${db}.dump" "${BACKUP_DIR}/${db}-${DATE}.dump"
        docker exec db_tito rm "/tmp/${db}.dump"
        echo "  -> ${BACKUP_DIR}/${db}-${DATE}.dump ($(du -h "${BACKUP_DIR}/${db}-${DATE}.dump" | cut -f1))"
    fi
done

# Rotate old backups
OLD_COUNT=$(find "${BACKUP_DIR}" -name "*.dump" -mtime +${RETENTION_DAYS} -print -delete | wc -l)
find "${BACKUP_DIR}" -name "*.log" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup complete."
echo "  Databases backed up: $(echo $PLANBAR_DBS $TITO_DBS | wc -w)"
echo "  Old backups removed: ${OLD_COUNT}"

# Print summary to stdout
cat "${LOG_FILE}"
