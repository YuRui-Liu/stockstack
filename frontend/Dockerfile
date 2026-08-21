FROM node:22.18.0-alpine3.22 AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.29.1-alpine3.22 AS runtime
COPY --chown=101:101 nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder --chown=101:101 /app/dist /usr/share/nginx/html
USER 101
EXPOSE 8080
