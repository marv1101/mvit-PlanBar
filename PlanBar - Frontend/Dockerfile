FROM node:22-alpine AS build
ENV CI=true
ENV TZ=UTC
WORKDIR /app
RUN npm install -g pnpm
COPY pnpm-lock.yaml package.json pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm run build

FROM nginx:stable-alpine

# Install su-exec for privilege dropping
RUN apk add --no-cache su-exec

# Create non-root user
RUN addgroup -S appuser && adduser -S -G appuser appuser

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Set ownership for nginx files
RUN chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/run

EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
