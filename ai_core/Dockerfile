# syntax=docker/dockerfile:1.4
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/ai_core

ARG AI_CORE_SRC=.
COPY ${AI_CORE_SRC}/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ${AI_CORE_SRC}/ ./ai_core

EXPOSE 9500

CMD ["uvicorn", "ai_core.server.app:app", "--host", "0.0.0.0", "--port", "9500"]
