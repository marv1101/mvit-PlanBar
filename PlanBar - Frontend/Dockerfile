# Multi-stage Dockerfile: build mit pnpm, ausliefern mit nginx
FROM node:18-alpine AS build
WORKDIR /app
# Verwende npm, da im Repo `package-lock.json` vorhanden ist
COPY package*.json ./
RUN npm ci --legacy-peer-deps
COPY . .
RUN npm run build

FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
