# Web build of the ChitBook app, served by nginx. Build context = repo root (see docker-compose.yml).

# ---------- build the static web export ----------
FROM node:22-alpine AS build
WORKDIR /app
COPY apps/mobile/package.json apps/mobile/package-lock.json ./
RUN npm ci
COPY apps/mobile/ ./
# Empty = same origin: nginx below proxies /api to the API container
ARG EXPO_PUBLIC_API_BASE_URL=""
ENV EXPO_PUBLIC_API_BASE_URL=${EXPO_PUBLIC_API_BASE_URL}
RUN npx expo export --platform web

# ---------- serve ----------
FROM nginx:1.27-alpine
RUN apk add --no-cache tzdata
COPY infra/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
