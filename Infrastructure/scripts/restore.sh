#!/bin/bash
# Restore a PlanBar customer database from a backup dump.
#
# Usage:
#   ./restore.sh <customer-id> <backup-file>
#
# Example:
#   ./restore.sh kunde1 /opt/planbar/backups/kunde1_planbar-20260601-030000.dump

set -euo pipefail

CUSTOMER="${1:?Usage: $0 <customer-id> <backup-file>}"
BACKUP_FILE="${2:?Usage: $0 <customer-id> <backup-file>}"
DB_NAME="${CUSTOMER}_planbar"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "Restoring ${DB_NAME} from ${BACKUP_FILE}..."

# Copy backup into the container
docker cp "${BACKUP_FILE}" "db_planbar:/tmp/restore.dump"

# Drop and recreate the database
docker exec db_planbar psql -U planbar -c "DROP DATABASE IF EXISTS ${DB_NAME};"
docker exec db_planbar psql -U planbar -c "CREATE DATABASE ${DB_NAME} OWNER planbar;"

# Restore
docker exec db_planbar pg_restore -U planbar -d "${DB_NAME}" \
    --clean --if-exists \
    /tmp/restore.dump

docker exec db_planbar rm /tmp/restore.dump

echo "Restore complete. Restarting customer stack..."
docker compose -f /opt/planbar/docker-compose.customer.yaml \
    --env-file "/opt/planbar/customers/${CUSTOMER}/.env" \
    -p "planbar-${CUSTOMER}" \
    restart planbar_backend

echo "Customer ${CUSTOMER} restored successfully."
