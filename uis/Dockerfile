# Imagen oficial de Node (Alpine)
# El .dockerignore de esta carpeta (uis/.dockerignore) se aplica porque el
# CONTEXTO de build es uis/:
#   docker build -f uis/Dockerfile -t healthcore-uis:latest uis/
# Arranque (CMD por defecto -> start.sh, ambas apps Next.js):
#   docker run --rm -p 3000:3000 -p 3001:3001 healthcore-uis:latest
#
# Puertos: website -> 3000, backoffice -> 3001 (WEBSITE_PORT / BACKOFFICE_PORT)

# ---------------------------------------------------------------------------
# 1) Dependencias de website (instalacion separada, capa cacheable)
# ---------------------------------------------------------------------------
FROM node:24-alpine AS deps-website
WORKDIR /app/uis/website
COPY website/package.json ./
RUN npm install

# ---------------------------------------------------------------------------
# 1b) Build de website (Next.js)
# ---------------------------------------------------------------------------
FROM node:24-alpine AS build-website
WORKDIR /app/uis/website
COPY --from=deps-website /app/uis/website/node_modules ./node_modules
COPY website/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# 2) Dependencias de backoffice (instalacion separada, capa cacheable)
# ---------------------------------------------------------------------------
FROM node:24-alpine AS deps-backoffice
WORKDIR /app/uis/backoffice
COPY backoffice/package.json ./
RUN npm install

# ---------------------------------------------------------------------------
# 2c) dev: ambas apps con sus dependencias instaladas (docker compose)
#     Los bind mounts de compose tapan el codigo; node_modules se sirve de los
#     volumenes named, que se siembran con estas capas.
# ---------------------------------------------------------------------------
FROM node:24-alpine AS dev
WORKDIR /app/website
COPY --from=deps-website /app/uis/website/node_modules ./node_modules
WORKDIR /app/backoffice
COPY --from=deps-backoffice /app/uis/backoffice/node_modules ./node_modules

# ---------------------------------------------------------------------------
# 2b) Build de backoffice (Next.js)
# ---------------------------------------------------------------------------
FROM node:24-alpine AS build-backoffice
WORKDIR /app/uis/backoffice
COPY --from=deps-backoffice /app/uis/backoffice/node_modules ./node_modules
COPY backoffice/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# 3) Runtime: ambas aplicaciones Next.js, arrancadas por start.sh (CMD)
# ---------------------------------------------------------------------------
FROM node:24-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app/uis

# Dependencias de cada aplicacion, instaladas por separado
COPY --from=deps-website    /app/uis/website/node_modules    ./website/node_modules
COPY --from=deps-backoffice /app/uis/backoffice/node_modules ./backoffice/node_modules

# Build de Next.js de cada aplicacion
COPY --from=build-website    /app/uis/website/.next           ./website/.next
COPY --from=build-website    /app/uis/website/package.json    ./website/package.json
COPY --from=build-backoffice /app/uis/backoffice/.next         ./backoffice/.next
COPY --from=build-backoffice /app/uis/backoffice/package.json  ./backoffice/package.json

# Fuentes (app router) necesarias en runtime
COPY website/   ./website/
COPY backoffice/ ./backoffice/

# Script de arranque: levanta website en 3000 y backoffice en 3001
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

EXPOSE 3000 3001
USER node
CMD ["sh", "/app/uis/start.sh"]