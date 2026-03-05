"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.config import settings
from server.db import close_pool, execute, init_pool
from server.routes import admin, analysis, auth, health, leads, verify

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    pool = await init_pool()
    if pool:
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            sql = schema_path.read_text(encoding="utf-8")
            await execute(sql)
            logger.info("Database schema applied")
    yield
    # Shutdown
    await close_pool()


app = FastAPI(
    title="AI Compatible v3",
    description="AI Compatibility Analyzer for Car Dealership Websites",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://ai-detect.savvydealer.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(health.router)
app.include_router(analysis.router)
app.include_router(leads.router)
app.include_router(verify.router)
app.include_router(auth.router)
app.include_router(admin.router)

# Serve React static files in production
static_dir = Path(__file__).parent.parent / "client" / "dist"
if static_dir.exists():
    from fastapi.responses import FileResponse

    # Static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    # SPA catch-all: serve index.html for any non-API route
    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        file_path = static_dir / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.main:app", host=settings.host, port=settings.port, reload=settings.debug)
