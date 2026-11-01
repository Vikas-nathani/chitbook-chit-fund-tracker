# Stage 1: build the static site
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: serve with nginx (also proxies /api to the backend)
FROM nginx:1.27-alpine
RUN apk add --no-cache tzdata
# nginx image renders *.template with env vars (BACKEND_HOST/BACKEND_PORT) into conf.d at start
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
