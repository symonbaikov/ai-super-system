# syntax=docker/dockerfile:1.4
ARG VITE_API_URL=https://api.localhost
ARG VITE_STREAM_URL=https://api.localhost/stream

FROM node:20-alpine AS build

WORKDIR /srv/web

COPY package*.json ./
RUN npm ci

COPY . .

ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_STREAM_URL=${VITE_STREAM_URL}

RUN npm run build

FROM nginx:1.27-alpine AS runtime

RUN apk add --no-cache curl

COPY --from=build /srv/web/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
