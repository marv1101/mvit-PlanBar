#!/bin/bash
# Deploy a new PlanBar customer stack or update an existing one.
#
# Usage:
#   ./deploy-customer.sh [--no-caddy] <customer-id> [frontend-port] [tito-port] [backend-port]
#
# Example:
#   ./deploy-customer.sh --no-caddy kunde1 8081 5001 8001
#   ./deploy-customer.sh kunde1 8081 5001 8001
#
# Prerequisites:
#   - docker-compose.infra.yaml must be running
#   - Caddy must be installed on the host for SSL termination (optional)
#   - The network planbar_shared must exist
#
# Environment variables (all optional):
#   PLANBAR_BASE    - Base deployment directory (default: /opt/planbar)
#   INFRA_ENV_FILE  - Path to infrastructure .env file with DB superuser passwords
#                     (default: <PLANBAR_BASE>/Infrastructure/.env.infra)
#   CADDYFILE       - Caddyfile path for automatic reverse proxy entry
#                     (default: /etc/caddy/Caddyfile; set empty to skip)
#   CADDY_RELOAD_CMD- Command to reload Caddy after config change
#                     (default: "systemctl reload caddy"; set empty to skip)

set -euo pipefail

SKIP_CADDY=false
POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-caddy|-n)
            SKIP_CADDY=true
            shift
            ;;
        --)
            shift
            POSITIONAL_ARGS+=("$@")
            break
            ;;
        -*)
            echo "Unknown option: $1"
            exit 1
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done
set -- "${POSITIONAL_ARGS[@]}"

CUSTOMER="${1:?Usage: $0 [--no-caddy] <customer-id> [frontend-port] [tito-port] [backend-port]}"
FRONTEND_PORT="${2:-8080}"
TITO_PORT="${3:-5000}"
BACKEND_PORT="${4:-8000}"
DOMAIN="planbar-${CUSTOMER}.mphion.de"

BASE_DIR="${PLANBAR_BASE:-/opt/planbar}"
CUSTOMER_DIR="${BASE_DIR}/customers/${CUSTOMER}"
COMPOSE_FILE="${BASE_DIR}/docker-compose.customer.yaml"

echo "=== Deploying customer: ${CUSTOMER} ==="
echo "  Domain:      ${DOMAIN}"
echo "  Frontend:    port ${FRONTEND_PORT}"
echo "  Backend:     port ${BACKEND_PORT}"
echo "  TiTO:        port ${TITO_PORT}"

# Create customer directory and secrets if new
if [ ! -d "${CUSTOMER_DIR}" ]; then
    echo "Creating new customer ${CUSTOMER}..."

    mkdir -p "${CUSTOMER_DIR}"

    # Read DB superuser passwords from infrastructure env file.
    # The customer apps connect to the shared PostgreSQL instances using the
    # same PostgreSQL user (planbar / tito) whose password is set in the infra env.
    INFRA_ENV_FILE="${INFRA_ENV_FILE:-${BASE_DIR}/Infrastructure/.env.infra}"
    if [ -f "${INFRA_ENV_FILE}" ]; then
        echo "Reading DB passwords from ${INFRA_ENV_FILE}..."
        set -a
        source "${INFRA_ENV_FILE}"
        set +a
    else
        echo "Warning: ${INFRA_ENV_FILE} not found. DB passwords must be set manually or via environment."
    fi

    PLANBAR_DB_NAME="${CUSTOMER}_planbar"
    TITO_DB_NAME="${CUSTOMER}_tito"
PLANBAR_DB_PASSWORD="${PLANBAR_DB_PASSWORD:?PLANBAR_DB_PASSWORD not set. Set it in ${INFRA_ENV_FILE} or pass as env var.}"
TITO_DB_PASSWORD="${TITO_DB_PASSWORD:?TITO_DB_PASSWORD not set. Set it in ${INFRA_ENV_FILE} or pass as env var.}"
    SECRET_KEY=$(openssl rand -hex 32)
    TITO_API_KEY=$(openssl rand -hex 16)
    TITO_JWT_SECRET=$(openssl rand -hex 32)

    cat > "${CUSTOMER_DIR}/.env" << EOF
FRONTEND_PORT=${FRONTEND_PORT}
TITO_PORT=${TITO_PORT}
BACKEND_PORT=${BACKEND_PORT}
DOMAIN=${DOMAIN}
PLANBAR_DB_NAME=${PLANBAR_DB_NAME}
TITO_DB_NAME=${TITO_DB_NAME}
PLANBAR_DB_PASSWORD=${PLANBAR_DB_PASSWORD}
TITO_DB_PASSWORD=${TITO_DB_PASSWORD}
SECRET_KEY=${SECRET_KEY}
TITO_API_KEY=${TITO_API_KEY}
TITO_JWT_SECRET=${TITO_JWT_SECRET}
ENVIRONMENT=production
EOF

    chmod 600 "${CUSTOMER_DIR}/.env"

    # Create databases
    echo "Creating databases..."
    docker exec -i db_planbar psql -U planbar -c "CREATE DATABASE ${PLANBAR_DB_NAME};"
    docker exec -i db_tito psql -U tito -c "CREATE DATABASE ${TITO_DB_NAME};"

    # Initialize TiTO schema
    if [ -f "${BASE_DIR}/Infrastructure/init-db.sql" ]; then
        docker exec -i db_tito psql -U tito -d "${TITO_DB_NAME}" < "${BASE_DIR}/Infrastructure/init-db.sql"
    fi

    # Add Caddy entry (skip with --no-caddy, CADDYFILE empty, or env var)
    if [ "${SKIP_CADDY}" = true ]; then
        echo "Skipping Caddy config (--no-caddy). Configure reverse proxy manually."
    else
        CADDYFILE="${CADDYFILE:-/etc/caddy/Caddyfile}"
        if [ -n "${CADDYFILE}" ]; then
            echo "Adding Caddy entry for ${DOMAIN} to ${CADDYFILE}..."
            mkdir -p "$(dirname "${CADDYFILE}")"
            cat >> "${CADDYFILE}" << EOF

${DOMAIN} {
    handle /api/* {
        reverse_proxy localhost:${BACKEND_PORT}
    }
    handle {
        reverse_proxy localhost:${FRONTEND_PORT}
    }
}
EOF
            CADDY_RELOAD_CMD="${CADDY_RELOAD_CMD:-systemctl reload caddy}"
            if [ -n "${CADDY_RELOAD_CMD}" ]; then
                ${CADDY_RELOAD_CMD} || echo "Warning: could not reload Caddy"
            fi
        else
            echo "Skipping Caddy config (CADDYFILE is empty). Configure reverse proxy manually."
        fi
    fi

    echo "Customer ${CUSTOMER} initialized."
else
    echo "Customer ${CUSTOMER} already exists, updating..."
fi

# Deploy or update the stack
docker compose \
    -f "${COMPOSE_FILE}" \
    --env-file "${CUSTOMER_DIR}/.env" \
    -p "planbar-${CUSTOMER}" \
    pull

docker compose \
    -f "${COMPOSE_FILE}" \
    --env-file "${CUSTOMER_DIR}/.env" \
    -p "planbar-${CUSTOMER}" \
    up -d

echo "=== Customer ${CUSTOMER} deployed successfully ==="
echo "  URL: https://${DOMAIN}"
echo "  Stack: planbar-${CUSTOMER}"
