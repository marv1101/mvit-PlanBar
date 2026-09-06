#!/bin/sh
# Startup script to configure nginx with environment variables

# Default values
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

# Replace placeholders in nginx config (needs root access)
sed -i "s|%BACKEND_URL%|${BACKEND_URL}|g" /etc/nginx/conf.d/default.conf

# Drop privileges and start nginx as appuser
exec su-exec appuser nginx -g "daemon off;"
