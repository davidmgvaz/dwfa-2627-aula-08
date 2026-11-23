# syntax=docker/dockerfile:1
# Imagem do frontend · frontend image (Aula 08): o Node só existe no build;
# o que corre em produção é um Nginx com ficheiros estáticos.
# Node exists only at build time; what runs in production is Nginx with static files.

# ---- 1 · build: npm ci + vite build → dist/ ----
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci
COPY . .
# mesma origem em produção: a SPA chama /api/… e o Nginx encaminha · same origin in production
ENV VITE_API_URL=""
RUN npm run build

# ---- 2 · runtime: Nginx + dist/ ----
FROM nginx:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
