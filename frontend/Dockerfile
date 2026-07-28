# syntax=docker/dockerfile:1.7
FROM node:24.10.0-alpine3.22 AS dependencies

ARG PNPM_VERSION=11.9.0
WORKDIR /app
RUN corepack enable && corepack prepare "pnpm@${PNPM_VERSION}" --activate
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM dependencies AS development
COPY . .
EXPOSE 5173
CMD ["pnpm", "dev", "--host", "0.0.0.0"]

FROM dependencies AS build
ARG VITE_API_BASE_URL=""
ARG VITE_APP_VERSION="0.1.0"
ARG VITE_GIT_COMMIT="unknown"
ARG VITE_BUILD_TIME="unknown"
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_APP_VERSION=${VITE_APP_VERSION} \
    VITE_GIT_COMMIT=${VITE_GIT_COMMIT} \
    VITE_BUILD_TIME=${VITE_BUILD_TIME}
COPY . .
RUN pnpm build

FROM nginx:1.28.0-alpine AS production
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
