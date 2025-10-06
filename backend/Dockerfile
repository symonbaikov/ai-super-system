# syntax=docker/dockerfile:1.4
ARG PYTHON_IMAGE=python:3.11-slim
ARG NODE_IMAGE=node:20-alpine

FROM ${PYTHON_IMAGE} AS api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv

WORKDIR /srv

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend-requirements.txt
RUN pip install --no-cache-dir -r backend-requirements.txt

COPY backend ./backend
COPY ai_core ./ai_core

WORKDIR /srv/backend

EXPOSE 9000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "9000"]


FROM ${NODE_IMAGE} AS worker

ENV NODE_ENV=production

WORKDIR /srv/backend

COPY backend/package*.json ./
RUN npm ci --omit=dev
RUN apk add --no-cache curl

COPY backend ./

CMD ["node", "src/index.js"]
