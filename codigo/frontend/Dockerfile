# 1) Compila el sitio estático con Next.js. Corre en la arquitectura de quien construye (el resultado son archivos
#    estáticos, iguales para amd64 y arm64), así la imagen multiarquitectura no compila Next.js dos veces.
FROM --platform=$BUILDPLATFORM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# 2) Lo sirve nginx SIN privilegios (usuario 101, puerto 8080) y reenvía /api al backend.
#    La dirección del backend llega por variable de entorno, así la misma imagen sirve en Compose y Kubernetes.
# Rama estable 1.30 de nginx: la etiqueta se reconstruye con cada parche de nginx y de Alpine.
FROM nginxinc/nginx-unprivileged:1.30-alpine
# Parches de seguridad de Alpine publicados despues de la imagen base (p. ej. brotli-libs, CVE-2026-111497).
# Se hace como root y al final se vuelve al usuario 101 (sin privilegios).
USER root
RUN apk upgrade --no-cache
ENV API_UPSTREAM=http://bf-api:8000 \
    DNS_RESOLVER=127.0.0.11 \
    NGINX_ENVSUBST_FILTER="^(API_UPSTREAM|DNS_RESOLVER)$"
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/out /usr/share/nginx/html
EXPOSE 8080
USER 101
