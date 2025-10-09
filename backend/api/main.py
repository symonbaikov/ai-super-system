from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import close_database, init_database
from .dependencies import close_queue, connect_queue
from .routes import alerts, apify, helius, parser, trade, advice, integration, signals

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_database()
    await connect_queue()
    try:
        yield
    finally:
        await close_queue()
        await close_database()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    debug=settings.api_debug,
    docs_url=settings.api_docs_url,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parser.router)
app.include_router(apify.router)
app.include_router(helius.router)
app.include_router(alerts.router)
app.include_router(trade.router)
app.include_router(advice.router)
app.include_router(integration.router)
app.include_router(signals.router)


@app.get("/api/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "super-parser-api"}
